# agent: claude-code  2026-10-17
"""Tiny read-only server for the live demo page. It only READS runs/ and harness files; it never writes.

  python3 demo/serve.py            then open http://127.0.0.1:8765
  python3 demo/serve.py --port 9000

The loop (`uv run rah run ...`) appends one line per decision to runs/decisions.jsonl and writes
runs/<run-id>.json when it finishes. This page follows those two files.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import insights_data  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "runs"
PAGE = Path(__file__).with_name("live.html")


def _decisions() -> list[dict]:
    path, out = RUNS / "decisions.jsonl", []
    if not path.exists():
        return out
    for line in path.read_text().splitlines():
        try:
            out.append(json.loads(line))
        except ValueError:
            pass  # a half-written last line while the loop is appending
    return out


def _endpoint() -> str:
    m = re.search(r'DEFAULT_BASE_URL\s*=\s*"([^"]+)"', (ROOT / "src/rah/llm.py").read_text())
    return m.group(1) if m else ""


def _harness(run: str) -> dict:
    for p in (RUNS / "versions" / run / "v0.yaml", ROOT / "harness.yaml"):
        if p.exists():
            return yaml.safe_load(p.read_text()) or {}
    return {}


TEAM_DEFAULTS = {"self_tests": True, "verifier": False, "edge_cases": False, "max_attempts": 1}


def _final_rules(run: str) -> list[dict]:
    """Every change that survived: written rules plus team settings that differ from their defaults."""
    p = RUNS / "versions" / run / "final.yaml"
    if not p.exists():
        return []
    d = yaml.safe_load(p.read_text()) or {}
    out = list(d.get("rules", []))
    out += [{"text": f"team setting: {k} = {v}"} for k, v in (d.get("team") or {}).items()
            if k in TEAM_DEFAULTS and v != TEAM_DEFAULTS[k]]
    return out


def runs_list(show_all: bool = False) -> list[dict]:
    seen: dict[str, dict] = {}
    for d in _decisions():
        r = seen.setdefault(d["run"], {"run": d["run"], "n": 0, "first": d["at"], "last": d["at"]})
        r["n"] += 1
        r["last"] = max(r["last"], d["at"])
    for r in seen.values():
        r["done"] = (RUNS / f"{r['run']}.json").exists()
    # real runs first, then offline dry runs, then scratch runs; newest first inside each
    rank = lambda n: 2 if n.startswith("real") else 1 if n.startswith("offline") else 0
    runs = [r for r in seen.values() if show_all or rank(r["run"]) > 0]  # scratch runs hidden unless ?all=1
    return sorted(runs, key=lambda r: (rank(r["run"]), r["last"]), reverse=True)


def run_state(run: str) -> dict:
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", run) or run.startswith("."):  # the id becomes part of a file path
        return {"run": run, "decisions": [], "summary": None, "done": False, "offline": True, "models": {},
                "endpoint": "", "final_rules": []}
    ds = [d for d in _decisions() if d["run"] == run]
    summ_p = RUNS / f"{run}.json"
    summary = json.loads(summ_p.read_text()) if summ_p.exists() else None
    h = _harness(run)
    return {
        "run": run,
        "decisions": ds,
        "summary": {k: v for k, v in (summary or {}).items() if k != "decisions"} or None,
        "done": summary is not None,
        "offline": not run.startswith("real"),  # only real-* runs come from Crusoe
        "models": h.get("models", {}),
        "endpoint": _endpoint(),
        "final_rules": _final_rules(run),
    }


class Handler(BaseHTTPRequestHandler):
    def _send(self, body: bytes, ctype: str, code: int = 200):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        u = urlparse(self.path)
        if u.path in ("/", "/index.html"):
            return self._send(PAGE.read_bytes(), "text/html; charset=utf-8")
        if u.path == "/api/runs":
            show_all = parse_qs(u.query).get("all", ["0"])[0] == "1"
            return self._send(json.dumps(runs_list(show_all)).encode(), "application/json")
        if u.path == "/insights.js":
            return self._send(Path(__file__).with_name("insights.js").read_bytes(), "text/javascript; charset=utf-8")
        if u.path == "/api/insights":
            run = parse_qs(u.query).get("id", [""])[0]
            try:
                body = insights_data.build(run, _decisions())
            except Exception as e:  # show the reason on the page instead of a blank tab
                body = {"error": f"{type(e).__name__}: {e}"}
            return self._send(json.dumps(body).encode(), "application/json")
        if u.path == "/api/run":
            run = parse_qs(u.query).get("id", [""])[0]
            return self._send(json.dumps(run_state(run)).encode(), "application/json")
        self._send(b"not found", "text/plain", 404)

    def log_message(self, *a):  # keep the terminal quiet
        pass


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8765)
    a = ap.parse_args()
    print(f"live page: http://127.0.0.1:{a.port}   (reads {RUNS})")
    ThreadingHTTPServer(("127.0.0.1", a.port), Handler).serve_forever()
