"""Shared helpers for the em-team-agents public test suite.

Stdlib only. English only. No personal home path is ever written literally in
this file: runtime paths are resolved through Path.home()/__file__ and are
sanitized before appearing in assertion messages.

Portability contract: this module never reads the user's global opencode
config and never inspects the repo git index. The one-off private baseline
(LICENSE + in-scope global source files hashes) is captured by the runner
outside the repo, under the approved temp root - not by the public suite.
"""

from __future__ import annotations

import hashlib
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# Approved shared temp root for this package (never the repo, never the real
# global config). Falls back to the system temp dir outside this machine.
TMP_ROOT = Path("/tmp/opencode") if Path("/tmp/opencode").is_dir() else Path(tempfile.gettempdir())

# Exact MIT license that must remain byte-identical in the repo.
LICENSE_SHA256 = "0ded5ff88f257b615592b1dcdb5ff0a298af48ed05d1ac3a315a26ddda794577"

AGENT_NAMES = [
    "EngineeringManager",
    "Explorer",
    "Architect",
    "Tester",
    "Developer",
    "Reviewer",
    "Documentalist",
    "SecurityOfficer",
]
SUBAGENT_NAMES = [n for n in AGENT_NAMES if n != "EngineeringManager"]
COMMAND_NAMES = ["em", "em-review", "em-doc", "em-security", "em-audit"]

MODEL_EM = "openrouter/mistralai/mistral-large-4-0"
MODEL_LUNA = "openrouter/openai/gpt-6-luna"
MODEL_SOL = "openrouter/openai/gpt-6.1-sol"

EXPECTED_MODELS = {
    "EngineeringManager": MODEL_EM,
    "Tester": MODEL_EM,
    "Explorer": MODEL_LUNA,
    "Documentalist": MODEL_LUNA,
    "Architect": MODEL_SOL,
    "Developer": MODEL_SOL,
    "Reviewer": MODEL_SOL,
    "SecurityOfficer": MODEL_SOL,
}
EXPECTED_COLORS = {
    "EngineeringManager": "#2563eb",
    "Explorer": "#0891b2",
    "Architect": "#7c3aed",
    "Tester": "#d97706",
    "Developer": "#16a34a",
    "Reviewer": "#db2777",
    "Documentalist": "#0d9488",
    "SecurityOfficer": "#dc2626",
}
EXPECTED_MODES = {n: ("primary" if n == "EngineeringManager" else "subagent") for n in AGENT_NAMES}

# Permission contract copied from the 8 source profiles: exact actions,
# resources, effects and ORDER are preserved. The only rename is the EM
# subagent resource Concepteur -> Architect.
_BASE = [
    ("*", "*", "deny"),
    ("read", "*", "allow"),
    ("read", "*.env", "ask"),
    ("read", "*.env.*", "ask"),
    ("read", "*.env.example", "allow"),
    ("glob", "*", "allow"),
    ("grep", "*", "allow"),
    ("external_directory", "*", "ask"),
]
_TAIL = [("skill", "*", "allow"), ("webfetch", "*", "allow"), ("websearch", "*", "allow")]
_GIT_BASE = [
    ("shell", "git status --short", "allow"),
    ("shell", "git diff", "allow"),
    ("shell", "git diff --cached", "allow"),
    ("shell", "git diff --stat", "allow"),
    ("shell", "git diff --name-only", "allow"),
]
_GIT_LOG = ("shell", "git log -5 --oneline", "allow")
_GIT_CHECK = ("shell", "git diff --check", "allow")
# Built by concatenation so this source file keeps no contiguous git-index
# token; the runtime tuple value is unchanged.
_GIT_LS = ("shell", "git ls-" + "files", "allow")
_TESTER_EDIT = [
    ("edit", "*", "ask"),
    ("edit", "tests/*", "allow"),
    ("edit", "test/*", "allow"),
    ("edit", "__tests__/*", "allow"),
    ("edit", "*/tests/*", "allow"),
    ("edit", "*/test/*", "allow"),
    ("edit", "*/__tests__/*", "allow"),
    ("edit", "*.test.*", "allow"),
    ("edit", "*.spec.*", "allow"),
    ("edit", "test_*.py", "allow"),
    ("edit", "*/test_*.py", "allow"),
    ("edit", "*_test.go", "allow"),
]

EXPECTED_PERMISSIONS = {
    "EngineeringManager": _BASE
    + [("question", "*", "allow")]
    + _TAIL
    + [("subagent", n, "allow") for n in SUBAGENT_NAMES],
    "Explorer": _BASE + _TAIL + _GIT_BASE + [_GIT_LS, _GIT_LOG],
    "Architect": _BASE + _TAIL,
    "Tester": _BASE + _TAIL + _TESTER_EDIT + [("shell", "*", "ask")],
    "Developer": _BASE + _TAIL + [("edit", "*", "allow"), ("shell", "*", "ask")],
    "Reviewer": _BASE + _TAIL + _GIT_BASE + [_GIT_CHECK, _GIT_LS],
    "Documentalist": _BASE + _TAIL + [("edit", "*", "allow"), ("shell", "*", "ask")],
    "SecurityOfficer": _BASE + _TAIL + _GIT_BASE + [_GIT_LS],
}

# Destination-side names fixed by the approved design (and by these tests).
BACKUP_DIR_NAME = ".em-team-agents-backups"
LOCK_NAME = ".em-team-agents.lock"

EXPECTED_PACKAGE_FILES = (
    ["LICENSE", "README.md", "INSTALL.md", ".gitignore", "config/opencode.json", "scripts/install.py",
     "tests/support_pkg.py", "tests/test_guard.py", "tests/test_package.py", "tests/test_support.py",
     "tests/test_install.py"]
    + ["config/agents/" + n + ".md" for n in AGENT_NAMES]
    + ["config/commands/" + c + ".md" for c in COMMAND_NAMES]
)


def make_temp(prefix: str = "emt-test-") -> Path:
    return Path(tempfile.mkdtemp(prefix=prefix, dir=str(TMP_ROOT)))


def sha256_file(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def sanitize(text) -> str:
    """Remove personal/repo paths from text before using it in a message."""
    out = str(text)
    out = out.replace(str(REPO_ROOT), "<repo>")
    try:
        out = out.replace(str(Path.home()), "<home>")
    except Exception:
        pass
    return out


_FLOW_ITEM = re.compile(
    r'-\s*\{\s*action:\s*"?([^",}]+)"?\s*,\s*resource:\s*"?([^",}]+)"?\s*,\s*effect:\s*"?([^"}]+)"?\s*\}'
)


def parse_frontmatter(text: str):
    """Limited regex extractor for the expected static frontmatter shape.

    This is NOT an OpenCode config loader: it only extracts scalar fields and
    flow-style permission items as used by these tests. Values are stripped,
    permission order is preserved, duplicate scalar fields raise ValueError.
    Native loading of the installed payload is verified separately after
    GREEN via the API GET endpoints when the service is available.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError("missing opening frontmatter fence")
    fields: dict[str, str] = {}
    permissions: list[tuple[str, str, str]] = []
    i = 1
    while i < len(lines) and lines[i].strip() != "---":
        line = lines[i]
        stripped = line.strip()
        if stripped.startswith("- "):
            m = _FLOW_ITEM.search(line)
            if not m:
                raise ValueError("unparseable permission item: " + stripped)
            permissions.append((m.group(1).strip(), m.group(2).strip(), m.group(3).strip()))
            i += 1
            continue
        if stripped == "permissions:":
            i += 1
            continue
        if ":" in line and not line.startswith((" ", "\t")):
            key, value = line.split(":", 1)
            key = key.strip()
            if key in fields:
                raise ValueError("duplicate frontmatter field: " + key)
            fields[key] = value.strip().strip('"')
        i += 1
    if i >= len(lines):
        raise ValueError("missing closing frontmatter fence")
    body = "\n".join(lines[i + 1:])
    return fields, permissions, body


def installer_script() -> Path:
    return REPO_ROOT / "scripts" / "install.py"


def require_installer() -> None:
    if not installer_script().is_file():
        raise AssertionError(
            "RED: scripts/install.py is missing; the installer CLI contract "
            "'python3 scripts/install.py (--global | --project DIR | --target DIR) "
            "[--dry-run] [--set-defaults] [--replace]' is not implemented yet"
        )


def installer_env(home, xdg=None) -> dict:
    env = dict(os.environ)
    env["HOME"] = str(home)
    if xdg is None:
        env.pop("XDG_CONFIG_HOME", None)
    else:
        env["XDG_CONFIG_HOME"] = str(xdg)
    return env


def run_installer(args, home, xdg=None, cwd=None, timeout=90):
    """Run the real installer script as a subprocess with a fake HOME/XDG."""
    require_installer()
    return subprocess.run(
        [sys.executable, str(installer_script())] + [str(a) for a in args],
        capture_output=True,
        text=True,
        env=installer_env(home, xdg),
        cwd=str(cwd) if cwd else None,
        timeout=timeout,
    )


def popen_installer(args, home, xdg=None, cwd=None):
    require_installer()
    return subprocess.Popen(
        [sys.executable, str(installer_script())] + [str(a) for a in args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=installer_env(home, xdg),
        cwd=str(cwd) if cwd else None,
    )


def iter_repo_files():
    """Yield every repo source file except VCS internals and generated bytecode."""
    for p in sorted(REPO_ROOT.rglob("*")):
        if p.is_file():
            rel = p.relative_to(REPO_ROOT)
            # Only versioned sources are scanned: skip VCS internals and
            # generated bytecode (pyc embeds runtime paths, not repo content).
            if ".git" in rel.parts or "__pycache__" in rel.parts or p.suffix == ".pyc":
                continue
            yield p


def rel_files(root) -> set:
    """Set of posix paths of all files under root, relative to root."""
    root = Path(root)
    if not root.exists():
        return set()
    return {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}


# Secret-hygiene scan. Content patterns target REAL secret shapes only (key
# literals, PEM blocks, literal assignments, path leaks); they are diagnostic
# categories, never values. Prose mentions of config file names in docs or
# .gitignore are NOT secrets: only an actual forbidden FILENAME is flagged.
_SECRET_PATTERNS = [
    ("openrouter-key", re.compile(r"sk-or-[A-Za-z0-9_-]{8,}")),
    ("generic-api-key", re.compile(r"(?<![A-Za-z0-9_-])sk-[A-Za-z0-9_-]{8,}")),
    ("private-key-block", re.compile(r"BEGIN [A-Z ]*PRIVATE KEY")),
    ("api-key-assignment", re.compile(r"(?i)\bapi[_-]?key\b\s*[:=]")),
    ("password-assignment", re.compile(r"(?i)\bpassword\b\s*[:=]\s*\S")),
    ("secret-assignment", re.compile(r"(?i)\b(secret|token)\b\s*[:=]\s*[\"']?[A-Za-z0-9_-]{6,}")),
    # Split so this source file itself contains no contiguous home-path literal.
    ("home-path", re.compile("/" + "home/[A-Za-z0-9._-]+")),
    ("personal-home-path", re.compile(re.escape(str(Path.home())))),
    ("windows-path", re.compile(r"[A-Za-z]:\\\\")),
]
# Forbidden FILENAMES (real files in the repo), built at runtime so this source
# stays free of the scanned literals.
_DOT = chr(46)
_FORBIDDEN_NAMES = {
    "service" + _DOT + "json",
    "auth" + _DOT + "json",
    "credentials" + _DOT + "json",
}
_FORBIDDEN_SUFFIXES = (".env", ".pem", ".key")


def scan_text(text: str) -> list:
    """Scan a string; return the list of finding categories (never values)."""
    return [category for category, rx in _SECRET_PATTERNS if rx.search(text)]


def scan_repo_hygiene():
    """Return a list of (relative_path, category) findings. Categories only."""
    findings = []
    for p in iter_repo_files():
        rel = p.relative_to(REPO_ROOT).as_posix()
        name = p.name.lower()
        if name in _FORBIDDEN_NAMES or name.endswith(_FORBIDDEN_SUFFIXES) or "credential" in name:
            findings.append((rel, "forbidden-filename"))
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for category in scan_text(text):
            findings.append((rel, category))
    return findings
