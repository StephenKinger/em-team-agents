"""Portable guard tests for the em-team-agents public suite.

Contract: these tests must pass BEFORE and AFTER the production files exist,
and on any published third-party clone (where every file may be tracked and
where no personal global opencode config exists at all). They therefore never
depend on git, on the repo git index, or on the user's global config.

The one-off PRIVATE baseline of this intervention (exact LICENSE bytes plus
hashes of the 15 in-scope global source files) is captured by the runner
outside the repo, under the approved temp root; it is intentionally NOT part
of this public suite.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import support_pkg as sp

# Publication allowlist: exact root files plus these directories. Anything
# else in the repo fails - before AND after production. A2-R adds the English
# MULTI-AGENTS.md guide at the repo root (shipped, but NOT installed by the
# installer: scripts/install.py manages only config/ payload files).
ALLOWED_ROOT_FILES = {"LICENSE", "README.md", "INSTALL.md", ".gitignore", "MULTI-AGENTS.md"}
ALLOWED_DIRS = ("config/", "scripts/", "tests/")

# Tokens proving the public suite does not couple to the repo git index or to
# a personal global config. Built by concatenation so this source file does
# not contain the scanned literal itself.
FORBIDDEN_COUPLING_TOKENS = [
    "ls-" + "files",
    "porce" + "lain",
    "GLOBAL_" + "SCOPE",
    "global" + "_config_dir",
]

CHILD_ENV_FLAG = "EMT_GUARD_CHILD_RUN"


class PortableGuardTest(unittest.TestCase):
    def test_01_license_is_exact_mit_2026_keezy(self):
        lic = sp.REPO_ROOT / "LICENSE"
        self.assertTrue(lic.is_file(), "LICENSE is missing from the repo root")
        raw = lic.read_bytes()
        self.assertEqual(sp.LICENSE_SHA256, sp.sha256_file(lic), "LICENSE bytes changed")
        self.assertIn(b"MIT License", raw)
        self.assertIn(b"Copyright (c) 2026 Keezy", raw)

    def test_02_repo_contains_only_publication_allowlisted_files(self):
        offenders = []
        for p in sp.iter_repo_files():
            rel = p.relative_to(sp.REPO_ROOT).as_posix()
            if rel in ALLOWED_ROOT_FILES or rel.startswith(ALLOWED_DIRS):
                continue
            offenders.append(rel)
        self.assertEqual(
            [],
            offenders,
            "files outside the publication allowlist (root files %s, dirs %s): %s"
            % (sorted(ALLOWED_ROOT_FILES), ALLOWED_DIRS, offenders),
        )

    def test_03_public_suite_has_no_git_index_or_global_config_coupling(self):
        offenders = []
        for p in sorted((sp.REPO_ROOT / "tests").glob("*.py")):
            text = p.read_text(encoding="utf-8")
            for tok in FORBIDDEN_COUPLING_TOKENS:
                if tok in text:
                    offenders.append((p.name, tok))
        self.assertEqual(
            [],
            offenders,
            "public test sources must not couple to the git index or global config: %s" % offenders,
        )

    def test_04_guard_suite_passes_in_temp_checkout_without_git_or_global_config(self):
        # Exact scope of this proof: a temp copy of the repo WITHOUT .git,
        # with HOME and XDG_CONFIG_HOME pointing at empty dirs (no global
        # opencode config at all) must run the guard module to full success.
        # Together with test_03 (no git-index / global-config coupling in the
        # helper sources), this proves the public guards are portable to any
        # published clone. A committed temp clone is intentionally NOT
        # exercised: no commit/add authorization exists for this cycle, and
        # no other git state is claimed as tested.
        if os.environ.get(CHILD_ENV_FLAG) == "1":
            self.skipTest("child run: recursion guard, executed only by the parent")
        tmp = sp.make_temp("emt-guardcopy-")
        try:
            copy_root = tmp / "checkout"
            shutil.copytree(
                sp.REPO_ROOT, copy_root, ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc")
            )
            fake_home = tmp / "home"
            fake_xdg = tmp / "xdg"
            fake_home.mkdir()
            fake_xdg.mkdir()
            env = dict(os.environ)
            env["HOME"] = str(fake_home)
            env["XDG_CONFIG_HOME"] = str(fake_xdg)
            env[CHILD_ENV_FLAG] = "1"
            cmd = [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_guard.py"]
            r = subprocess.run(cmd, cwd=str(copy_root), capture_output=True, text=True, env=env, timeout=180)
            self.assertEqual(
                0,
                r.returncode,
                "guard suite must pass in a gitless copy without any global config:\n"
                + sp.sanitize(r.stdout + r.stderr)[-2000:],
            )
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
