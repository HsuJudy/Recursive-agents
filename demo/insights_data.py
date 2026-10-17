# agent: claude-code  2026-10-17
"""Read-only numbers for the Insights tab. Reads runs/cache.jsonl, runs/decisions.jsonl and the saved harness files;
writes nothing. Uses the loop's own fingerprint and scoring code, so the numbers match what the loop computed.

The cache holds every real attempt, keyed by the exact rules and settings (the "harness fingerprint") that produced
it. Grouping by that fingerprint gives the score of each team version without any change to the loop.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "runs"
CACHE = RUNS / "cache.jsonl"
SPLIT_ORDER = {"train": 0, "val": 1, "test": 2}

_rah = None
_stats = {"sig": None, "data": None}


def _load_rah():
    global _rah
    if _rah is None:
        sys.path.insert(0, str(ROOT / "src"))
        from rah.config import Harness
        from rah.evaluate import CODE_VERSION, harness_fingerprint, task_fingerprint
        from rah.llm import PRICES
        from rah.suite import load_suite
        from rah.team import Outcome

        by_fp, by_id = {}, {}
        for name in ("all", "dense"):
            for t in load_suite(name):
                by_fp[task_fingerprint(t)] = t
                by_id[t.id] = t
        _rah = dict(Harness=Harness, CODE_VERSION=CODE_VERSION, hfp=harness_fingerprint, PRICES=PRICES,
                    Outcome=Outcome, tasks_by_fp=by_fp, tasks_by_id=by_id)
    return _rah


def _num(x):
    return None if x is None or x != x else round(x, 4)


def _cost(PRICES, tokens: dict) -> float:
    return sum(p * PRICES.get(m, (0, 0))[0] / 1e6 + c * PRICES.get(m, (0, 0))[1] / 1e6 for m, (p, c) in tokens.items())


def _cache_stats() -> dict:
    """Per harness fingerprint: task -> sample scores, run count, 'said done but wrong' count, tokens per model."""
    sig = (CACHE.stat().st_mtime, CACHE.stat().st_size) if CACHE.exists() else None
    if _stats["sig"] == sig and _stats["data"] is not None:
        return _stats["data"]
    r = _load_rah()
    out: dict[str, dict] = {}
    if sig:
        for line in CACHE.read_text().splitlines():
            try:
                rec = json.loads(line)
                ver, hfp, tfp, _sample = rec["key"].split(":")
                if ver != r["CODE_VERSION"] or tfp not in r["tasks_by_fp"]:
                    continue
                d = dict(rec["outcome"])
                d["usage"] = [tuple(u) for u in d.get("usage", [])]
                o = r["Outcome"](**d)
            except (ValueError, KeyError, TypeError):
                continue
            if o.error:
                continue
            h = out.setdefault(hfp, {"n": 0, "over": 0, "scores": {}, "tokens": {}})
            h["n"] += 1
            h["over"] += int(o.overconfident)
            h["scores"].setdefault(r["tasks_by_fp"][tfp].id, []).append(o.score)
            for m, p, c in o.usage:
                t = h["tokens"].setdefault(m, [0, 0])
                t[0] += p
                t[1] += c
    _stats.update(sig=sig, data=out)
    return out


def _summary(stats: dict | None) -> dict:
    """Mean score per split (mean of per-task means), the same way the loop computes it."""
    r = _load_rah()
    if not stats:
        return {"has_data": False}
    per_task = {tid: mean(v) for tid, v in stats["scores"].items()}
    row = {"has_data": True, "n": stats["n"], "tasks": len(per_task),
           "over": _num(stats["over"] / stats["n"]), "scores": {k: round(v, 4) for k, v in per_task.items()}}
    for split in SPLIT_ORDER:
        vals = [v for tid, v in per_task.items() if r["tasks_by_id"][tid].split == split]
        row[split] = _num(mean(vals)) if vals else None
    return row


def _harness_files() -> list[tuple[str, Path]]:
    files = [(p.name, p) for p in sorted(ROOT.glob("*.yaml"))]
    files += [(f"runs/{p.name}", p) for p in sorted(RUNS.glob("*.yaml"))]
    files += [(f"{p.parent.name}/{p.stem}", p) for p in sorted((RUNS / "versions").glob("*/*.yaml"))]
    return files


def _lineage(run: str) -> list[tuple[str, Path]]:
    d = RUNS / "versions" / run
    if not run or not d.is_dir() or d.name != run:
        return []
    vs = sorted((p for p in d.glob("v*.yaml") if p.stem[1:].isdigit()), key=lambda p: int(p.stem[1:]))
    return [(p.stem, p) for p in vs] + ([("final", d / "final.yaml")] if (d / "final.yaml").exists() else [])


def build(run: str, decisions: list[dict]) -> dict:
    r = _load_rah()
    stats = _cache_stats()
    names: dict[str, list[str]] = {}
    harnesses = {}
    for name, path in _harness_files():
        try:
            h = r["Harness"].load(path)
        except Exception:
            continue
        fp = r["hfp"](h)
        names.setdefault(fp, []).append(name)
        harnesses[fp] = h

    # the selected run's team versions, oldest first (a "final" identical to the last version is dropped)
    lineage, seen_last = [], None
    for label, path in _lineage(run):
        try:
            h = r["Harness"].load(path)
        except Exception:
            continue
        fp = r["hfp"](h)
        if label == "final" and fp == seen_last:
            continue
        seen_last = fp
        lineage.append({"name": label, "fp": fp, "units": len(h.units()),
                        "rules": [x["text"] for x in h.rules], "team": h.team, **_summary(stats.get(fp))})

    ids = sorted({t for v in lineage for t in v.get("scores", {})},
                 key=lambda t: (SPLIT_ORDER[r["tasks_by_id"][t].split], t))
    tasks = [{"id": t, "split": r["tasks_by_id"][t].split, "family": r["tasks_by_id"][t].family} for t in ids]

    gate = [{"round": d["round"], "unit": d["unit"], "text": d["text"], "action": d["action"],
             "train": d["numbers"]["train"], "val": d["numbers"]["val"], "reason": d.get("reason", "")}
            for d in decisions if d["run"] == run and d["action"] in ("keep", "reject")
            and {"train", "val"} <= set(d.get("numbers", {}))]

    receipts = []
    if lineage:
        h = r["Harness"].load(dict(_lineage(run))[lineage[-1]["name"]])
        for u in h.units():
            rc = h.receipts.get(u, {})
            receipts.append({"unit": u, "text": h.describe(u), "round": rc.get("round"),
                             "train": rc.get("train_delta"), "val": rc.get("val_delta"),
                             "worth": rc.get("ablation_worth"), "swap": rc.get("swap_worth")})

    def spend(fps):
        tok: dict[str, list[int]] = {}
        for fp in fps:
            for m, (p, c) in stats.get(fp, {}).get("tokens", {}).items():
                t = tok.setdefault(m, [0, 0])
                t[0] += p
                t[1] += c
        return [{"model": m, "prompt": p, "completion": c, "cost": round(_cost(r["PRICES"], {m: (p, c)}), 4)}
                for m, (p, c) in sorted(tok.items(), key=lambda kv: -_cost(r["PRICES"], {kv[0]: tuple(kv[1])}))]

    run_spend = spend({v["fp"] for v in lineage})
    all_versions = sorted(
        ({"fp": fp, "names": names.get(fp, ["(file no longer on disk)"]), "units": len(harnesses[fp].units()) if fp in harnesses else None,
          **_summary(s)} for fp, s in stats.items()),
        key=lambda v: -(v.get("test") if v.get("test") is not None else -1))

    judge = []
    jp = RUNS / "judge_history.jsonl"
    if jp.exists():
        for line in jp.read_text().splitlines():
            try:
                j = json.loads(line)
                judge.append({"at": j["at"], "label": j.get("label", ""), "overall": j["overall"]})
            except (ValueError, KeyError):
                pass

    return {"run": run, "lineage": lineage, "tasks": tasks, "gate": gate, "receipts": receipts,
            "spend": run_spend, "spend_all": spend(set(stats)), "all_versions": all_versions, "judge": judge,
            "attempts_total": sum(s["n"] for s in stats.values())}
