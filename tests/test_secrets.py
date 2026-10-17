# agent: claude-code  2026-10-17
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATTERNS = [re.compile(p) for p in (r"sk-[A-Za-z0-9]{20,}", r"CRUSOE_API_KEY\s*=\s*(?!paste-|os\.)\S{12,}",
                                    r"Bearer\s+[A-Za-z0-9_\-\.]{20,}")]


def _tracked_candidates():
    out = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard"], cwd=ROOT,
                         capture_output=True, text=True).stdout.split()
    return [ROOT / f for f in out if (ROOT / f).is_file() and not f.endswith((".lock", ".pyc"))]


def test_no_keys_in_files_git_would_include():
    for f in _tracked_candidates():
        text = f.read_text(errors="ignore")
        for p in PATTERNS:
            assert not p.search(text), f"possible secret in {f.name}"


def test_env_is_ignored():
    r = subprocess.run(["git", "check-ignore", ".env"], cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0
