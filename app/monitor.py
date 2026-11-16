"""Monitoramento em memória (por processo) para o painel DEV: requisições, usuários online e erros."""
from __future__ import annotations
import re, threading, time
from collections import deque, Counter

_LOCK = threading.Lock()
_EVENTS: deque = deque(maxlen=30000)   # (ts, método, rota, status, ms, user_id)
_ERRORS: deque = deque(maxlen=300)     # (ts, método, rota, status, mensagem, user_id)
STARTED = time.time()
_ID = re.compile(r'/\d+(?=/|$)')


def group(path: str) -> str:
    return _ID.sub('/{id}', path)


def record(method: str, path: str, status: int, ms: float, uid, error: str = '') -> None:
    now = time.time()
    g = group(path)
    with _LOCK:
        _EVENTS.append((now, method, g, status, ms, uid))
        if status >= 500 or error:
            _ERRORS.append((now, method, path, status, error[:300], uid))


def _window(minutes: int):
    cut = time.time() - minutes * 60
    with _LOCK:
        return [e for e in _EVENTS if e[0] >= cut]


def online_users(minutes: int = 5) -> list[tuple]:
    """[(user_id, última atividade, nº de requisições)] dos últimos N minutos."""
    last: dict = {}; cnt: Counter = Counter()
    for ts, _m, _g, _s, _ms, uid in _window(minutes):
        if uid:
            last[uid] = max(last.get(uid, 0), ts); cnt[uid] += 1
    return sorted(((u, last[u], cnt[u]) for u in last), key=lambda x: -x[1])


def _pct(vals: list, p: float) -> float:
    if not vals:
        return 0.0
    vals = sorted(vals)
    return round(vals[min(len(vals) - 1, int(len(vals) * p))], 1)


def summary(minutes: int = 15) -> dict:
    ev = _window(minutes)
    durs = [e[4] for e in ev]
    codes = Counter(f'{e[3] // 100}xx' for e in ev)
    per_route: dict = {}
    for _t, m, g, s, ms, _u in ev:
        r = per_route.setdefault((m, g), {'n': 0, 'tot': 0.0, 'max': 0.0, 'err': 0})
        r['n'] += 1; r['tot'] += ms; r['max'] = max(r['max'], ms); r['err'] += s >= 500
    routes = [{'method': m, 'route': g, 'n': r['n'], 'avg': round(r['tot'] / r['n'], 1), 'max': round(r['max'], 1), 'err': r['err']}
              for (m, g), r in per_route.items()]
    # série por minuto
    now = int(time.time() // 60)
    buckets = Counter(int(e[0] // 60) for e in ev)
    series = [(now - i, buckets.get(now - i, 0)) for i in range(minutes - 1, -1, -1)]
    return {'total': len(ev), 'per_min': round(len(ev) / minutes, 1), 'p50': _pct(durs, .5), 'p95': _pct(durs, .95),
            'p99': _pct(durs, .99), 'codes': dict(codes), 'slowest': sorted(routes, key=lambda r: -r['avg'])[:12],
            'busiest': sorted(routes, key=lambda r: -r['n'])[:12], 'series': series,
            'uptime': int(time.time() - STARTED)}


def errors(limit: int = 100) -> list[tuple]:
    with _LOCK:
        return list(_ERRORS)[-limit:][::-1]
