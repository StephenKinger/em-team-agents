"""Static and conditional integration tests for the Gitleaks fail-closed
integration (approved design A).

Static contract (RED until the production files exist): the repo root must
ship .pre-commit-config.yaml (official gitleaks hook, pinned rev, staged /
git-index scan), .gitleaks.toml (extends the default rules, no undemonstrated
exception) and .github/workflows/secrets.yml (fail-closed Actions workflow:
unittest suite first, then BOTH `gitleaks git --log-opts=--all` and
`gitleaks dir` with --redact; the job fails if either scan fails). These tests
assert robust motifs only: no hash, tag or action SHA is invented here.

Integration tests: run the real gitleaks binary against temp directories and
are skipped unless the binary is available (skipUnless), so the suite stays
runnable on a gitless clone or a machine without gitleaks. Every secret
fixture is assembled at runtime by concatenation, so this source file never
contains a contiguous scannable key literal: both the repo's own hygiene scan
and the CI `gitleaks dir` scan must stay clean on this file.

Stdlib only. English only. Python 3.10+.
"""

from __future__ import annotations

import random
import re
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import support_pkg as sp

PRE_COMMIT_CONFIG = ".pre-commit-config.yaml"
GITLEAKS_CONFIG = ".gitleaks.toml"
WORKFLOW_PATH = ".github/workflows/secrets.yml"

SHA_PIN = re.compile(r"^[0-9a-f]{40}$")
VERSION_TAG = re.compile(r"^v?\d+(\.\d+)*$")
REV_LINE = re.compile(r"(?m)^\s*rev:\s*(\S+)\s*$")

GITLEAKS_BIN = shutil.which("gitleaks")
GIT_BIN = shutil.which("git")

# Charset accepted by the default `aws-access-token` rule of gitleaks v8
# ([A-Z2-7]{16} after the AKIA prefix): no 0, 1, 8 or 9. The bare alphabet
# string matches no rule; only the runtime-assembled full key does.
_AWS_KEY_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"


def _synthetic_aws_key():
    """Return a synthetic AWS-shaped key assembled at runtime.

    "AKIA" + 16 chars drawn only from [A-Z2-7], the charset the default
    aws-access-token rule of gitleaks v8.30.1 accepts after the AKIA prefix,
    so the REAL binary detects it (verified: rule aws-access-token, exit 1,
    "leaks found"). Assembled by concatenation so this source file never
    contains a contiguous scannable literal. Seeded Random: reproducible,
    and the seeded value was verified detected against gitleaks v8.30.1.
    """
    rng = random.Random(0xA11CE)
    return "AKIA" + "".join(rng.choice(_AWS_KEY_ALPHABET) for _ in range(16))


def _read_repo_file(rel):
    path = sp.REPO_ROOT / rel
    if not path.is_file():
        return None
    return path.read_text(encoding="utf-8")


def _yaml_block(text, key):
    """Return the raw YAML block of a top-level key (block or flow style)."""
    lines = text.splitlines()
    pat = re.compile(r'^(?:["\']?)' + re.escape(key) + r'(?:["\']?)\s*:(.*)$')
    for i, line in enumerate(lines):
        m = pat.match(line)
        if m:
            block = [m.group(1)]
            for j in range(i + 1, len(lines)):
                if lines[j].strip() == "" or lines[j][0] in " \t":
                    block.append(lines[j])
                else:
                    break
            return "\n".join(block)
    return ""


class GitleaksIntegrationStaticTest(unittest.TestCase):
    """Static contract of design A on the three integration files."""

    def test_01_integration_files_exist_at_repo_root(self):
        missing = [
            rel
            for rel in (PRE_COMMIT_CONFIG, GITLEAKS_CONFIG, WORKFLOW_PATH)
            if not (sp.REPO_ROOT / rel).is_file()
        ]
        self.assertEqual(
            [],
            missing,
            "RED: Gitleaks fail-closed integration files missing at the repo root: %s" % missing,
        )

    def test_02_pre_commit_config_pins_official_gitleaks_hook(self):
        text = _read_repo_file(PRE_COMMIT_CONFIG)
        if text is None:
            self.fail("RED: %s is missing at the repo root" % PRE_COMMIT_CONFIG)
        self.assertRegex(
            text,
            re.compile(r"(?m)^\s*repo:\s*\S*gitleaks/gitleaks\S*\s*$"),
            "pre-commit config must use the official gitleaks/gitleaks repository",
        )
        self.assertRegex(
            text,
            re.compile(r"(?m)^\s*id:\s*gitleaks\b"),
            "the gitleaks hook id must be present",
        )
        revs = REV_LINE.findall(text)
        self.assertTrue(revs, "RED: a pinned 'rev:' is required (no floating hook)")
        for rev in revs:
            self.assertTrue(
                SHA_PIN.match(rev) or VERSION_TAG.match(rev),
                "rev must be pinned (commit SHA or version tag), got %r" % rev,
            )
        # Staged / git-index scan variant (protect --staged) and system language.
        self.assertRegex(
            text,
            re.compile(r"(?i)protect|staged"),
            "the gitleaks hook must scan the staged index (protect/staged)",
        )
        self.assertRegex(
            text,
            re.compile(r"(?m)^\s*language:\s*system\s*$"),
            "the gitleaks hook must use the system language variant",
        )

    def test_03_gitleaks_toml_extends_defaults_without_test_allowlist(self):
        text = _read_repo_file(GITLEAKS_CONFIG)
        if text is None:
            self.fail("RED: %s is missing at the repo root" % GITLEAKS_CONFIG)
        self.assertRegex(
            text,
            re.compile(r"\[extend\]\s*\n\s*useDefault\s*=\s*true"),
            ".gitleaks.toml must extend the default rules ([extend] useDefault = true)",
        )
        self.assertIsNone(
            re.search(r"(?m)^\s*\[allowlist\]", text),
            "no global [allowlist] section: no undemonstrated exception is allowed",
        )
        self.assertNotIn(
            "tests/",
            text,
            "no allowlist of tests/ is allowed in .gitleaks.toml",
        )

    def test_04_workflow_secrets_yml_fail_closed_contract(self):
        text = _read_repo_file(WORKFLOW_PATH)
        if text is None:
            self.fail("RED: %s is missing at the repo root" % WORKFLOW_PATH)
        # Triggers: push + pull_request (workflow_dispatch optional).
        on_block = _yaml_block(text, "on")
        self.assertTrue(on_block, "workflow must declare its triggers (on:)")
        self.assertIsNotNone(re.search(r"\bpush\b", on_block), "workflow must trigger on push")
        self.assertIsNotNone(
            re.search(r"\bpull_request\b", on_block), "workflow must trigger on pull_request"
        )
        # Full-history checkout without stored credentials.
        self.assertIn("actions/checkout", text, "workflow must use actions/checkout")
        self.assertRegex(text, re.compile(r"(?m)fetch-depth:\s*0\b"), "checkout must use fetch-depth: 0")
        self.assertRegex(
            text,
            re.compile(r"(?im)persist-credentials:\s*false\b"),
            "checkout must set persist-credentials: false",
        )
        # Minimal top-level permissions.
        perm_block = _yaml_block(text, "permissions")
        self.assertRegex(
            perm_block,
            re.compile(r"(?m)contents:\s*read\b"),
            "workflow permissions must be contents: read",
        )
        # Every used action pinned by SHA (40 hex), never by a floating tag.
        uses = re.findall(r"(?m)^\s*-?\s*uses:\s*(\S+)", text)
        self.assertTrue(uses, "workflow must use actions (at least actions/checkout)")
        for u in uses:
            _repo, sep, ref = u.rpartition("@")
            self.assertTrue(sep, "action %r must be pinned with @<ref>" % u)
            self.assertTrue(
                SHA_PIN.match(ref),
                "action %r must be pinned by a 40-hex SHA (approved contract prefers SHA), got %r" % (u, ref),
            )
        # The unittest suite runs first, then BOTH gitleaks scans, redacted, with
        # the repo config; the job fails if either scan fails (no `|| true`, no
        # fallback to a homemade scanner).
        i_unit = text.find("python3 -m unittest discover -s tests")
        i_git = text.find("gitleaks git")
        i_dir = text.find("gitleaks dir")
        self.assertNotEqual(-1, i_unit, "workflow must run the unittest suite (python3 -m unittest discover -s tests)")
        self.assertNotEqual(-1, i_git, "workflow must run a `gitleaks git` scan step")
        self.assertNotEqual(-1, i_dir, "workflow must run a `gitleaks dir` scan step")
        self.assertLess(i_unit, i_git, "the unittest suite must run before the gitleaks git scan")
        self.assertLess(i_unit, i_dir, "the unittest suite must run before the gitleaks dir scan")
        self.assertIn("--log-opts=--all", text, "gitleaks git must scan the full history (--log-opts=--all)")
        self.assertGreaterEqual(
            len(re.findall(r"--redact\b", text)), 2, "both gitleaks scans must use --redact"
        )
        self.assertGreaterEqual(
            len(re.findall(r"--config\s+\.gitleaks\.toml", text)),
            2,
            "both gitleaks scans must use --config .gitleaks.toml",
        )
        self.assertNotIn(
            "|| true",
            text,
            "fail-closed: no scan step may be masked with '|| true'",
        )


@unittest.skipUnless(GITLEAKS_BIN, "gitleaks binary not available: conditional integration test (skipUnless)")
class GitleaksDirIntegrationTest(unittest.TestCase):
    """Real `gitleaks dir` runs against temp dirs; fixtures are assembled at
    runtime by concatenation so this source keeps no scannable literal."""

    def setUp(self):
        self.tmp = sp.make_temp("emt-gitleaks-")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _run_dir(self, path, verbose=False):
        # gitleaks v8 invocation: `dir` scans a plain directory and has NO
        # --no-git flag (an unknown flag exits 126 = usage error, which must
        # never be mistaken for a detection). Run from a non-git cwd and pass
        # the repo config explicitly, like the CI workflow does.
        cmd = [
            GITLEAKS_BIN,
            "dir",
            "--config",
            str(sp.REPO_ROOT / GITLEAKS_CONFIG),
            "--redact",
            "--no-color",
        ]
        if verbose:
            cmd.append("-v")
        cmd.append(str(path))
        return subprocess.run(
            cmd,
            cwd=str(path),
            capture_output=True,
            text=True,
            timeout=180,
        )

    def test_dir_scan_fails_on_synthetic_aws_key(self):
        # Runtime-assembled fixture: "AKIA" + 16 chars from [A-Z2-7], proven
        # detected by the real gitleaks v8.30.1 binary (rule aws-access-token);
        # the source itself stays clean of any contiguous key literal.
        (self.tmp / "leak.txt").write_text(
            "aws_access_key_id = " + _synthetic_aws_key() + "\n", encoding="utf-8"
        )
        r = self._run_dir(self.tmp, verbose=True)
        out = sp.sanitize(r.stdout + r.stderr)
        self.assertNotEqual(
            0,
            r.returncode,
            "gitleaks dir must FAIL (non-zero exit) on a synthetic AWS-shaped key:\n" + out[-1500:],
        )
        # Prove real DETECTION, never a bare non-zero exit that could come from
        # a usage error (exit 126 prints "unknown flag", never "leaks found"):
        self.assertIn(
            "leaks found", out, "scan output must report leaks found:\n" + out[-1500:]
        )
        self.assertNotIn("no leaks found", out)
        # With -v the finding block names the rule (the secret stays redacted):
        self.assertIn(
            "aws-access-token",
            out,
            "verbose finding must name rule aws-access-token:\n" + out[-1500:],
        )

    def test_dir_scan_passes_on_clean_directory(self):
        (self.tmp / "clean.txt").write_text("nothing sensitive in this file\n", encoding="utf-8")
        r = self._run_dir(self.tmp)
        out = sp.sanitize(r.stdout + r.stderr)
        self.assertEqual(
            0,
            r.returncode,
            "gitleaks dir must PASS on a clean directory:\n" + out[-1500:],
        )
        self.assertIn(
            "no leaks found", out, "clean scan must report 'no leaks found':\n" + out[-1500:]
        )


@unittest.skipUnless(
    GITLEAKS_BIN and GIT_BIN,
    "gitleaks and git binaries required: conditional integration test (skipUnless)",
)
class GitleaksGitIntegrationTest(unittest.TestCase):
    """Real `gitleaks git --log-opts=--all` runs against a temp git repo."""

    def setUp(self):
        self.tmp = sp.make_temp("emt-gitleaks-git-")
        subprocess.run([GIT_BIN, "init", "-q", str(self.tmp)], check=True, capture_output=True, timeout=60)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _git(self, *args):
        return subprocess.run(
            [GIT_BIN, "-C", str(self.tmp), "-c", "user.email=test@example.com", "-c", "user.name=test"]
            + list(args),
            capture_output=True,
            text=True,
            timeout=60,
        )

    def _run_git_scan(self, verbose=False):
        cmd = [
            GITLEAKS_BIN,
            "git",
            "--config",
            str(sp.REPO_ROOT / GITLEAKS_CONFIG),
            "--redact",
            "--no-color",
            "--log-opts=--all",
        ]
        if verbose:
            cmd.append("-v")
        cmd.append(".")
        return subprocess.run(
            cmd,
            cwd=str(self.tmp),
            capture_output=True,
            text=True,
            timeout=180,
        )

    def test_git_scan_clean_history_passes_then_secret_commit_fails(self):
        (self.tmp / "clean.txt").write_text("nothing sensitive\n", encoding="utf-8")
        self._git("add", "clean.txt")
        self._git("commit", "-q", "-m", "clean baseline")
        r_clean = self._run_git_scan()
        out_clean = sp.sanitize(r_clean.stdout + r_clean.stderr)
        self.assertEqual(
            0,
            r_clean.returncode,
            "gitleaks git --log-opts=--all must PASS on a clean history:\n" + out_clean[-1500:],
        )
        self.assertIn(
            "no leaks found",
            out_clean,
            "clean history scan must report 'no leaks found':\n" + out_clean[-1500:],
        )
        # Same runtime-assembled, proven-detectable fixture as the dir test.
        (self.tmp / "leak.txt").write_text(
            "aws_access_key_id = " + _synthetic_aws_key() + "\n", encoding="utf-8"
        )
        self._git("add", "leak.txt")
        self._git("commit", "-q", "-m", "add config file")
        r_leak = self._run_git_scan(verbose=True)
        out_leak = sp.sanitize(r_leak.stdout + r_leak.stderr)
        self.assertNotEqual(
            0,
            r_leak.returncode,
            "gitleaks git --log-opts=--all must FAIL once a synthetic key is committed:\n"
            + out_leak[-1500:],
        )
        # Prove real DETECTION (leaks found + named rule), never a bare
        # non-zero exit that could come from a usage error:
        self.assertIn(
            "leaks found", out_leak, "scan output must report leaks found:\n" + out_leak[-1500:]
        )
        self.assertNotIn("no leaks found", out_leak)
        self.assertIn(
            "aws-access-token",
            out_leak,
            "verbose finding must name rule aws-access-token:\n" + out_leak[-1500:],
        )


if __name__ == "__main__":
    unittest.main()
