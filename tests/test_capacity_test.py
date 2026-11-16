"""Capacity runner safeguards, with no HTTP traffic or application writes."""
from dataclasses import replace
import io
import json
from pathlib import Path
import ssl
import tempfile
import threading
import time
import unittest
from unittest.mock import Mock, patch

from tools.capacity_test import (
    AddressHTTPSConnection, Config, HttpClient, READ_ROUTES, Response, Sample,
    main, percentile, run_capacity_test, run_stage, summarize,
)


class FakeClient:
    def __init__(self, responder=None):
        self.responder = responder or (lambda route: Response(200))
        self.calls = []
        self.closed = False

    def get(self, route):
        self.calls.append(route)
        return self.responder(route)

    def close(self):
        self.closed = True


class CapacityTests(unittest.TestCase):
    def config(self, **overrides):
        return replace(Config(stages=(10, 20), duration=0.3, think_time=0.001,
                              cooldown=0, timeout=0.1), **overrides)

    def run_fake(self, config, responder, **options):
        clients = []
        def factory():
            client = FakeClient(responder)
            clients.append(client)
            return client
        report = run_capacity_test(
            config, "session=DO-NOT-LOG-THIS", client_factory=factory,
            emit=lambda message: None, ramp_seconds=0,
            check_interval=0.01, health_interval=0.01, **options,
        )
        self.assertTrue(all(client.closed for client in clients))
        self.assertNotIn("DO-NOT-LOG-THIS", json.dumps(report))
        return report

    def test_percentiles_use_interpolation_and_empty_is_none(self):
        self.assertIsNone(percentile([], 95))
        self.assertEqual(percentile([5], 99), 5)
        self.assertEqual(percentile([5, 1, 4, 2, 3], 50), 3)
        self.assertAlmostEqual(percentile([5, 1, 4, 2, 3], 95), 4.8)
        self.assertAlmostEqual(percentile([0, 100], 99), 99)

    def test_limits_reject_unsafe_or_nonfinite_configuration(self):
        for invalid in (
            {"stages": (201,)}, {"stages": (0,)}, {"stages": (20, 10)},
            {"stages": (10, 10)}, {"stages": ()}, {"duration": 121},
            {"duration": float("nan")}, {"think_time": 0}, {"timeout": -1},
            {"max_p95_ms": float("inf")}, {"max_error_rate": 1.1}, {"cooldown": -1},
            {"base_url": "http://example.test"}, {"base_url": "https://user:secret@example.test"},
            {"base_url": "https://example.test/path"}, {"base_url": "https://example.test?secret=x"},
            {"connect_address": "127.0.0.1\r\nHost: other"},
        ):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                self.config(**invalid).validate()
        self.config(stages=(1, 200), duration=120).validate()

    def test_errors_abort_before_next_stage(self):
        report = self.run_fake(self.config(), lambda route: Response(503))
        self.assertTrue(report["aborted"])
        self.assertEqual(report["abort_reason"], "recent_error_rate_exceeded")
        self.assertEqual(len(report["stages"]), 1)
        self.assertGreaterEqual(report["stages"][0]["requests"], 30)
        self.assertLess(report["stages"][0]["elapsed_s"], 0.25)

    def test_latency_guard_aborts_without_http_errors(self):
        def slow(route):
            time.sleep(0.006)
            return Response(200)
        report = self.run_fake(self.config(max_p95_ms=1), slow)
        self.assertEqual(report["abort_reason"], "recent_p95_exceeded")
        self.assertEqual(report["stages"][0]["errors"], 0)
        self.assertGreaterEqual(report["stages"][0]["latency_ms"]["p95"], 1)

    def test_four_consecutive_health_probe_failures_abort(self):
        def response(route):
            return Response(503) if threading.current_thread().name == "capacity-health" else Response(200)
        report = self.run_fake(self.config(), response)
        self.assertEqual(report["abort_reason"], "health_probe_failed_4_consecutive_times")
        stage = report["stages"][0]
        self.assertEqual(stage["health_probes"]["requests"], 4)
        self.assertEqual(stage["health_probes"]["max_consecutive_failures"], 4)
        self.assertEqual(stage["errors"], 0)

    def test_resource_sentinel_aborts_without_traffic_and_discards_secrets(self):
        with tempfile.TemporaryDirectory() as folder:
            sentinel = Path(folder) / "abort.json"
            sentinel.write_text(json.dumps({"mem_available_percent": 12.5,
                                            "secret": "PRIVATE-COOKIE", "load1": float("nan")}))
            report = self.run_fake(self.config(abort_file=str(sentinel)), lambda route: Response(200))
        self.assertEqual(report["abort_reason"], "resource_guard")
        self.assertEqual(report["stages"][0]["requests"], 0)
        self.assertEqual(report["stages"][0]["resource_guard_metrics"], {"mem_available_percent": 12.5})
        self.assertNotIn("PRIVATE-COOKIE", json.dumps(report))

    def test_resource_sentinel_is_checked_during_running_stage(self):
        with tempfile.TemporaryDirectory() as folder:
            sentinel = Path(folder) / "abort.json"
            lock = threading.Lock()
            requests = 0
            def response(route):
                nonlocal requests
                with lock:
                    requests += 1
                    if requests == 10:
                        sentinel.write_text('{"cpu_percent": 99}')
                return Response(200)
            report = self.run_fake(self.config(abort_file=str(sentinel)), response)
        self.assertEqual(report["abort_reason"], "resource_guard")
        self.assertGreater(report["stages"][0]["requests"], 0)
        self.assertLess(report["stages"][0]["elapsed_s"], 0.25)
        self.assertEqual(len(report["stages"]), 1)

    def test_successful_run_counts_all_routes_and_respects_concurrency(self):
        report = self.run_fake(self.config(stages=(2, 3), duration=0.05), lambda route: Response(200))
        self.assertTrue(report["completed"])
        self.assertFalse(report["aborted"])
        self.assertEqual(len(report["stages"]), 2)
        for stage in report["stages"]:
            self.assertLessEqual(stage["max_inflight"], stage["users"])
            self.assertEqual(sum(r["requests"] for r in stage["routes"].values()), stage["requests"])
            self.assertEqual(stage["errors"], 0)
            self.assertEqual(set(stage["routes"]), set(READ_ROUTES))
            self.assertNotIn("/", stage["routes"])

    def test_exception_messages_never_reach_results(self):
        def fail(route):
            raise OSError("socket cookie=session=PRIVATE-COOKIE")
        report = self.run_fake(self.config(), fail)
        self.assertNotIn("PRIVATE-COOKIE", json.dumps(report))
        self.assertEqual(set(report["stages"][0]["error_types"]), {"OSError"})

    def test_report_does_not_confuse_error_with_http_200(self):
        result = summarize([Sample(1, "/health", 10, 200, "InvalidJSON"),
                            Sample(2, "/health", 30, 401, None)], 2)
        self.assertEqual(result["errors"], 2)
        self.assertEqual(result["error_rate"], 1)
        self.assertEqual(result["rps"], 1)
        self.assertEqual(result["statuses"], {"200": 1, "401": 1})


class HttpTransportTests(unittest.TestCase):
    def test_success_reuses_connection_but_failed_session_discards_it(self):
        connection = Mock()
        html = Mock(status=200)
        html.read.return_value = b"<html></html>"
        html.getheader.return_value = "text/html; charset=utf-8"
        expired_session = Mock(status=200)
        expired_session.read.return_value = b'{"authenticated": false}'
        expired_session.getheader.return_value = "application/json"
        connection.getresponse.side_effect = [html, expired_session, html]
        with patch("tools.capacity_test.AddressHTTPSConnection", return_value=connection) as make:
            client = HttpClient(Config(), "session=PRIVATE", ssl.create_default_context())
            self.assertEqual(client.get("/rac"), Response(200))
            self.assertEqual(client.get("/api/session/status"), Response(200, "Unauthenticated"))
            make.assert_called_once()
            connection.close.assert_called_once()
            self.assertEqual(client.get("/rac"), Response(200))
            self.assertEqual(make.call_count, 2)
            client.close()

    def test_tcp_override_preserves_verified_tls_sni(self):
        context = ssl.create_default_context()
        self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)
        self.assertTrue(context.check_hostname)
        raw_socket = Mock()
        with patch("tools.capacity_test.socket.create_connection", return_value=raw_socket) as dial, \
                patch.object(context, "wrap_socket", return_value=Mock()) as wrap:
            connection = AddressHTTPSConnection("safetyplus.srna.co", 443,
                                                connect_address="127.0.0.1", timeout=5, context=context)
            connection.connect()
            dial.assert_called_once_with(("127.0.0.1", 443), 5, None)
            wrap.assert_called_once_with(raw_socket, server_hostname="safetyplus.srna.co")
            connection.close()

    def test_redirect_is_error_and_is_never_followed(self):
        connection = Mock()
        response = Mock(status=303)
        response.read.return_value = b""
        response.getheader.return_value = "text/html"
        connection.getresponse.return_value = response
        with patch("tools.capacity_test.AddressHTTPSConnection", return_value=connection):
            client = HttpClient(Config(connect_address="127.0.0.1"), "session=PRIVATE", ssl.create_default_context())
            result = client.get("/rac")
        self.assertEqual(result, Response(303, "UnexpectedHTTPStatus"))
        connection.request.assert_called_once()
        call = connection.request.call_args
        self.assertEqual(call.args, ("GET", "/rac"))
        self.assertEqual(call.kwargs["headers"]["Host"], "safetyplus.srna.co")
        connection.close.assert_called_once()

    def test_fixed_read_routes_cannot_be_overridden(self):
        client = HttpClient(Config(), "session=PRIVATE", ssl.create_default_context())
        for route in ("/", "/logout", "https://external.test/", "/api/session/status?cookie=PRIVATE"):
            with self.subTest(route=route), self.assertRaises(ValueError):
                client.get(route)

    def test_cli_failure_never_prints_cookie_or_exception_message(self):
        with tempfile.TemporaryDirectory() as folder:
            cookie = Path(folder) / "cookie"
            cookie.write_text("session=PRIVATE-COOKIE")
            output = Path(folder) / "report.json"
            with patch("tools.capacity_test.run_capacity_test", side_effect=OSError("PRIVATE-COOKIE")), \
                    patch("sys.stdout", new_callable=io.StringIO) as stdout:
                status = main(["--cookie-file", str(cookie), "--output", str(output)])
        self.assertEqual(status, 2)
        self.assertNotIn("PRIVATE-COOKIE", stdout.getvalue())
        self.assertIn("OSError", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
