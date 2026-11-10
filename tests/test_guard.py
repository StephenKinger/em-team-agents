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
# installer: scripts/install.py manages only config/ payload files). Design A
# adds the two Gitleaks root files; the Actions workflow is allowed ONLY at the
# exact path in ALLOWED_EXACT_PATHS (never the whole .github/ tree).
ALLOWED_ROOT_FILES = {
    "LICENSE",
    "README.md",
    "INSTALL.md",
    ".gitignore",
    "MULTI-AGENTS.md",
    ".pre-commit-config.yaml",
    ".gitleaks.toml",
}
ALLOWED_DIRS = ("config/", "scripts/", "tests/")
ALLOWED_EXACT_PATHS = {".github/workflows/secrets.yml"}


def is_allowlisted(rel):
    """Publication-allowlist predicate for a repo-relative posix path."""
    return rel in ALLOWED_ROOT_FILES or rel in ALLOWED_EXACT_PATHS or rel.startswith(ALLOWED_DIRS)


def allowlist_offenders(root):
    """Files under root that are outside the publication allowlist.

    Same exclusions as the repo hygiene scan: VCS internals and generated
    bytecode are never publication offenders.
    """
    root = Path(root)
    offenders = []
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        rel_path = p.relative_to(root)
        if ".git" in rel_path.parts or "__pycache__" in rel_path.parts or p.suffix == ".pyc":
            continue
        rel = rel_path.as_posix()
        if not is_allowlisted(rel):
            offenders.append(rel)
    return offenders

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
        offenders = allowlist_offenders(sp.REPO_ROOT)
        self.assertEqual(
            [],
            offenders,
            "files outside the publication allowlist (root files %s, exact paths %s, dirs %s): %s"
            % (sorted(ALLOWED_ROOT_FILES), sorted(ALLOWED_EXACT_PATHS), ALLOWED_DIRS, offenders),
        )

    def test_05_allowlist_accepts_only_the_approved_security_paths(self):
        # Design A regression, with real temp files (never the repo itself, so
        # it passes both before and after the production files exist): the two
        # new root files and the exact workflow path are accepted, while an
        # arbitrary root file and any other file under .github/ stay rejected.
        tmp = sp.make_temp("emt-allowlist-")
        try:
            allowed = [".pre-commit-config.yaml", ".gitleaks.toml", ".github/workflows/secrets.yml"]
            refused = [
                "arbitrary-root-file.txt",
                ".github/workflows/other.yml",
                ".github/other-file.txt",
            ]
            for rel in allowed + refused:
                p = tmp / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text("placeholder\n", encoding="utf-8")
            offenders = allowlist_offenders(tmp)
            self.assertEqual(
                sorted(refused),
                sorted(offenders),
                "only the approved security paths may be allowlisted; offenders: %s" % offenders,
            )
            for rel in allowed:
                self.assertNotIn(rel, offenders, "%s must be allowlisted" % rel)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

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
