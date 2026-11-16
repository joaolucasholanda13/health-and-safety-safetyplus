#!/usr/bin/env python3
"""Bounded, authenticated GET benchmark using only the Python standard library.

One persistent connection per virtual user, no redirects, no document writes.
The dashboard is deliberately excluded: GET / can close expired permits.
Percentiles use linear interpolation between ordered observed latencies.
"""
from __future__ import annotations

import argparse
from collections import Counter, deque
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone
import http.client
import json
import math
from pathlib import Path
import random
import socket
import ssl
import threading
import time
from typing import Callable, Protocol
from urllib.parse import urlsplit


READ_ROUTES = (
    "/inspection/drill/new", "/rac", "/api/notifications/unread?limit=10",
    "/api/session/status", "/health",
)
# Ten requests: form 40%, RAC 20%, notifications 20%, session 10%, health 10%.
ROUTE_SCHEDULE = (
    READ_ROUTES[0], READ_ROUTES[1], READ_ROUTES[2], READ_ROUTES[0],
    READ_ROUTES[3], READ_ROUTES[0], READ_ROUTES[1], READ_ROUTES[2],
    READ_ROUTES[0], READ_ROUTES[4],
)
MAX_RESPONSE_BYTES = 8 * 1024 * 1024


@dataclass(frozen=True)
class Config:
    base_url: str = "https://safetyplus.srna.co"
    connect_address: str | None = None
    ca_file: str | None = None
    abort_file: str | None = None
    stages: tuple[int, ...] = (1, 10, 25, 50, 100, 150, 200)
    duration: float = 30.0
    think_time: float = 1.0
    cooldown: float = 5.0
    timeout: float = 5.0
    max_p95_ms: float = 5000.0
    max_error_rate: float = 0.01

    def validate(self) -> None:
        parsed = urlsplit(self.base_url)
        if (parsed.scheme != "https" or not parsed.hostname or parsed.username
                or parsed.password or parsed.path not in ("", "/")
                or parsed.query or parsed.fragment
                or any(c in self.base_url for c in "\r\n")):
            raise ValueError("base-url must be an HTTPS origin without credentials, path or query")
        # Force malformed ports to fail before starting any requests.
        if parsed.port is not None and not 1 <= parsed.port <= 65535:
            raise ValueError("invalid HTTPS port")
        if self.connect_address and any(c.isspace() or c in "/?#" for c in self.connect_address):
            raise ValueError("connect-address must be a host or IP address")
        if (not self.stages or any(type(n) is not int or not 1 <= n <= 200 for n in self.stages)
                or tuple(sorted(set(self.stages))) != tuple(self.stages)):
            raise ValueError("stages must be strictly increasing integers from 1 to 200")
        for name in ("duration", "think_time", "timeout", "max_p95_ms"):
            value = getattr(self, name)
            if not math.isfinite(value) or value <= 0:
                raise ValueError(f"{name} must be finite and greater than zero")
        if self.duration > 120:
            raise ValueError("duration must not exceed 120 seconds per stage")
        if not math.isfinite(self.cooldown) or self.cooldown < 0:
            raise ValueError("cooldown must be finite and nonnegative")
        if not math.isfinite(self.max_error_rate) or not 0 <= self.max_error_rate <= 1:
            raise ValueError("max-error-rate must be between zero and one")


@dataclass(frozen=True)
class Response:
    status: int | None
    error: str | None = None


class Client(Protocol):
    def get(self, route: str) -> Response: ...
    def close(self) -> None: ...


class AddressHTTPSConnection(http.client.HTTPSConnection):
    """Override only the TCP destination; HTTPSConnection retains real TLS SNI."""

    def __init__(self, host: str, port: int, *, connect_address: str | None,
                 timeout: float, context: ssl.SSLContext):
        super().__init__(host, port, timeout=timeout, context=context)
        self.connect_address = connect_address or host
        self._create_connection = self._connect_address

    def _connect_address(self, address, timeout=socket._GLOBAL_DEFAULT_TIMEOUT,
                         source_address=None):
        return socket.create_connection((self.connect_address, address[1]), timeout, source_address)


class HttpClient:
    def __init__(self, config: Config, cookie: str, context: ssl.SSLContext):
        target = urlsplit(config.base_url)
        self._host = target.hostname
        self._port = target.port or 443
        self._config = config
        self._context = context
        self._cookie = cookie
        self._connection: AddressHTTPSConnection | None = None
        host = f"[{self._host}]" if ":" in self._host else self._host
        self._host_header = host if self._port == 443 else f"{host}:{self._port}"

    def close(self) -> None:
        if self._connection is not None:
            self._connection.close()
            self._connection = None

    def get(self, route: str) -> Response:
        if route not in READ_ROUTES:
            raise ValueError("only fixed read routes are allowed")
        if self._connection is None:
            self._connection = AddressHTTPSConnection(
                self._host, self._port, connect_address=self._config.connect_address,
                timeout=self._config.timeout, context=self._context,
            )
        try:
            self._connection.request("GET", route, headers={
                "Host": self._host_header, "Cookie": self._cookie,
                "User-Agent": "SafetyPlus-CapacityTest/1.0",
                "Accept": "application/json" if route.startswith("/api/") or route == "/health"
                else "text/html", "Cache-Control": "no-cache",
            })
            response = self._connection.getresponse()
            # Drain the body for keep-alive, while bounding memory for unusual replies.
            body = response.read(MAX_RESPONSE_BYTES + 1)
            status = response.status
            if len(body) > MAX_RESPONSE_BYTES:
                self.close()
                return Response(status, "ResponseTooLarge")
            if status != 200:
                self.close()
                return Response(status, "UnexpectedHTTPStatus")
            content_type = response.getheader("Content-Type", "").split(";", 1)[0].strip().lower()
            expected_json = route.startswith("/api/") or route == "/health"
            if content_type != ("application/json" if expected_json else "text/html"):
                self.close()
                return Response(status, "UnexpectedContentType")
            if route in ("/health", "/api/session/status"):
                try:
                    payload = json.loads(body)
                except (ValueError, UnicodeError):
                    self.close()
                    return Response(status, "InvalidJSON")
                key = "ok" if route == "/health" else "authenticated"
                if not isinstance(payload, dict) or payload.get(key) is not True:
                    self.close()
                    return Response(status, "HealthNotOK" if route == "/health" else "Unauthenticated")
            return Response(status)
        except Exception:
            # The caller records only the exception class, never its message or request headers.
            self.close()
            raise


@dataclass(frozen=True)
class Sample:
    completed_at: float
    route: str
    latency_ms: float
    status: int | None
    error: str | None

    @property
    def failed(self) -> bool:
        return self.status != 200 or self.error is not None


def percentile(values: list[float], percent: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * percent / 100
    lower, upper = math.floor(position), math.ceil(position)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def summarize(samples: list[Sample], elapsed: float) -> dict:
    latencies = [sample.latency_ms for sample in samples]
    errors = sum(sample.failed for sample in samples)
    return {
        "requests": len(samples), "errors": errors,
        "error_rate": errors / len(samples) if samples else 0.0,
        "rps": len(samples) / elapsed if elapsed > 0 else 0.0,
        "latency_ms": {"p50": percentile(latencies, 50), "p95": percentile(latencies, 95),
                       "p99": percentile(latencies, 99), "max": max(latencies, default=None)},
        "statuses": dict(Counter(str(sample.status) if sample.status is not None else "exception"
                                 for sample in samples)),
        "error_types": dict(Counter(sample.error or "UnexpectedHTTPStatus"
                                    for sample in samples if sample.failed)),
    }


class StageState:
    def __init__(self, window_seconds: float):
        self.lock = threading.Lock()
        self.stop = threading.Event()
        self.samples: list[Sample] = []
        self.health: list[Sample] = []
        self.recent: deque[Sample] = deque()
        self.window_seconds = window_seconds
        self.inflight = 0
        self.max_inflight = 0
        self.health_failures = 0
        self.max_health_failures = 0
        self.abort_reason: str | None = None
        self.resource_guard_metrics: dict[str, float] = {}

    def abort(self, reason: str) -> None:
        with self.lock:
            if self.abort_reason is None:
                self.abort_reason = reason
        self.stop.set()

    def record(self, sample: Sample, health: bool = False) -> None:
        health_abort = False
        with self.lock:
            if health:
                self.health.append(sample)
                self.health_failures = self.health_failures + 1 if sample.failed else 0
                self.max_health_failures = max(self.max_health_failures, self.health_failures)
                health_abort = self.health_failures > 3
            else:
                self.samples.append(sample)
                self.recent.append(sample)
        if health_abort:
            self.abort("health_probe_failed_4_consecutive_times")

    def evaluate(self, config: Config, now: float) -> None:
        if config.abort_file and Path(config.abort_file).exists():
            # The monitor file can contain arbitrary text: copy only approved numeric metrics.
            try:
                payload = json.loads(Path(config.abort_file).read_text(encoding="utf-8")[:4096])
                if isinstance(payload, dict):
                    self.resource_guard_metrics = {
                        key: value for key, value in payload.items()
                        if key in ("mem_available_percent", "cpu_percent", "load1")
                        and type(value) in (int, float) and math.isfinite(value)
                    }
            except (OSError, ValueError, UnicodeError):
                pass
            self.abort("resource_guard")
            return
        with self.lock:
            while self.recent and self.recent[0].completed_at < now - self.window_seconds:
                self.recent.popleft()
            current = list(self.recent)
        if len(current) < 30:
            return
        if sum(sample.failed for sample in current) / len(current) > config.max_error_rate:
            self.abort("recent_error_rate_exceeded")
        elif percentile([sample.latency_ms for sample in current], 95) > config.max_p95_ms:
            self.abort("recent_p95_exceeded")


def perform_request(client: Client, route: str) -> Sample:
    start = time.monotonic()
    try:
        response = client.get(route)
    except Exception as exc:
        # Reset a fake/custom transport too. Exception text may contain secrets.
        try:
            client.close()
        except Exception:
            pass
        response = Response(None, type(exc).__name__)
    return Sample(time.monotonic(), route, (time.monotonic() - start) * 1000,
                  response.status, response.error)


def run_stage(config: Config, users: int, factory: Callable[[], Client], *,
              check_interval: float = 2.0, health_interval: float = 2.0,
              window_seconds: float = 10.0, ramp_seconds: float = 1.0) -> dict:
    config.validate()
    if type(users) is not int or not 1 <= users <= 200:
        raise ValueError("stage users must be an integer from 1 to 200")
    state = StageState(window_seconds)
    started = time.monotonic()
    deadline = started + config.duration

    def worker(number: int) -> None:
        client = factory()
        rng = random.Random(8128 + number)
        delay = min(ramp_seconds, config.duration) * (number + rng.random()) / users
        try:
            if state.stop.wait(delay):
                return
            index = number
            while not state.stop.is_set() and time.monotonic() < deadline:
                route = ROUTE_SCHEDULE[index % len(ROUTE_SCHEDULE)]
                with state.lock:
                    state.inflight += 1
                    state.max_inflight = max(state.max_inflight, state.inflight)
                try:
                    sample = perform_request(client, route)
                finally:
                    with state.lock:
                        state.inflight -= 1
                state.record(sample)
                index += 1
                pause = min(config.think_time * rng.uniform(0.5, 1.5),
                            max(0.0, deadline - time.monotonic()))
                state.stop.wait(pause)
        finally:
            client.close()

    def probe() -> None:
        client = None
        try:
            client = factory()
            while not state.stop.is_set() and time.monotonic() < deadline:
                probe_started = time.monotonic()
                state.record(perform_request(client, "/health"), health=True)
                pause = min(max(0.0, health_interval - (time.monotonic() - probe_started)),
                            max(0.0, deadline - time.monotonic()))
                state.stop.wait(pause)
        except Exception:
            state.abort("health_probe_worker_failed")
        finally:
            if client is not None:
                client.close()

    probe_thread = threading.Thread(target=probe, name="capacity-health")
    executor = ThreadPoolExecutor(max_workers=users, thread_name_prefix="capacity-user")
    futures = []
    try:
        state.evaluate(config, time.monotonic())
        probe_thread.start()
        if not state.stop.is_set():
            futures = [executor.submit(worker, number) for number in range(users)]
        while not state.stop.wait(min(check_interval, max(0.0, deadline - time.monotonic()))):
            state.evaluate(config, time.monotonic())
            if time.monotonic() >= deadline:
                break
    except KeyboardInterrupt:
        state.abort("interrupted")
    finally:
        state.stop.set()
        executor.shutdown(wait=True, cancel_futures=True)
        probe_thread.join()
    # Include replies that were in flight when the last monitor tick occurred.
    state.evaluate(config, time.monotonic())
    if any(future.done() and not future.cancelled() and future.exception() for future in futures):
        state.abort("client_worker_failed")
    elapsed = time.monotonic() - started
    result = summarize(state.samples, elapsed)
    result.update({
        "users": users, "duration_requested_s": config.duration,
        "elapsed_s": elapsed, "max_inflight": state.max_inflight,
        "aborted": state.abort_reason is not None, "abort_reason": state.abort_reason,
        "resource_guard_metrics": state.resource_guard_metrics,
        "routes": {route: summarize([s for s in state.samples if s.route == route], elapsed)
                   for route in READ_ROUTES},
        "health_probes": {**summarize(state.health, elapsed),
                          "max_consecutive_failures": state.max_health_failures},
    })
    return result


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_capacity_test(config: Config, cookie: str, *,
                      client_factory: Callable[[], Client] | None = None,
                      emit: Callable[[str], None] | None = None,
                      on_update: Callable[[dict], None] | None = None,
                      **stage_options) -> dict:
    config.validate()
    if not cookie or any(c in cookie for c in "\r\n"):
        raise ValueError("cookie must contain one nonempty Cookie header value")
    if client_factory is None:
        context = ssl.create_default_context(cafile=config.ca_file)
        client_factory = lambda: HttpClient(config, cookie, context)
    emit = emit or (lambda message: print(message, flush=True))
    report = {
        "started_at": utc_now(), "finished_at": None, "completed": False,
        "aborted": False, "abort_reason": None,
        "scope": "authenticated GET navigation; no document creation, signing or finalization",
        "limitations": ["virtual clients share one dedicated test account",
                        "does not measure distinct user data or simultaneous PDF generation"],
        "target": config.base_url.rstrip("/"), "planned_users": list(config.stages),
        "duration_per_stage_s": config.duration, "think_time_s": config.think_time,
        "cooldown_s": config.cooldown, "timeout_s": config.timeout,
        "thresholds": {"max_p95_ms": config.max_p95_ms, "max_error_rate": config.max_error_rate,
                       "min_recent_samples": 30, "recent_window_s": stage_options.get("window_seconds", 10.0),
                       "health_consecutive_failures_to_abort": 4},
        "stages": [],
    }
    for index, users in enumerate(config.stages):
        emit(json.dumps({"event": "stage_start", "users": users, "duration_s": config.duration}))
        stage = run_stage(config, users, client_factory, **stage_options)
        report["stages"].append(stage)
        emit(json.dumps({"event": "stage_end", **{key: stage[key] for key in
                        ("users", "requests", "errors", "error_rate", "rps", "latency_ms",
                         "max_inflight", "aborted", "abort_reason")}}))
        if stage["aborted"]:
            report.update(aborted=True, abort_reason=stage["abort_reason"])
        if on_update:
            on_update(report)
        if report["aborted"]:
            break
        if index < len(config.stages) - 1:
            try:
                time.sleep(config.cooldown)
            except KeyboardInterrupt:
                report.update(aborted=True, abort_reason="interrupted")
                break
    report["completed"] = not report["aborted"] and len(report["stages"]) == len(config.stages)
    report["finished_at"] = utc_now()
    if on_update:
        on_update(report)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="https://safetyplus.srna.co")
    parser.add_argument("--connect-address")
    parser.add_argument("--ca-file")
    parser.add_argument("--abort-file", help="stop if this local resource monitor sentinel exists")
    parser.add_argument("--cookie-file", required=True)
    parser.add_argument("--stages", default="1,10,25,50,100,150,200")
    for flag, default in (("duration", 30), ("think-time", 1), ("cooldown", 5),
                          ("timeout", 5), ("max-p95-ms", 5000), ("max-error-rate", 0.01)):
        parser.add_argument(f"--{flag}", type=float, default=default)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    try:
        config = Config(base_url=args.base_url, connect_address=args.connect_address,
                        ca_file=args.ca_file, abort_file=args.abort_file,
                        stages=tuple(int(n) for n in args.stages.split(",")),
                        duration=args.duration, think_time=args.think_time, cooldown=args.cooldown,
                        timeout=args.timeout, max_p95_ms=args.max_p95_ms,
                        max_error_rate=args.max_error_rate)
        config.validate()
    except ValueError as exc:
        # Configuration errors do not include Cookie contents.
        parser.error(str(exc))
    try:
        cookie = Path(args.cookie_file).read_text(encoding="utf-8").strip()
        output = Path(args.output)
        # Test output access before generating load; never serialize arguments or cookies.
        def save(report: dict) -> None:
            temporary = output.with_name(output.name + ".partial")
            temporary.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
            temporary.replace(output)
        save({"completed": False, "status": "starting"})
        report = run_capacity_test(config, cookie, on_update=save)
    except Exception as exc:
        print(json.dumps({"event": "runner_error", "error_type": type(exc).__name__}), flush=True)
        return 2
    print(json.dumps({"event": "test_end", "completed": report["completed"],
                      "aborted": report["aborted"], "abort_reason": report["abort_reason"]}), flush=True)
    return 0 if report["completed"] else 130 if report["abort_reason"] == "interrupted" else 1


if __name__ == "__main__":
    raise SystemExit(main())
