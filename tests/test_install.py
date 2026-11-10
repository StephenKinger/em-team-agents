"""Installer CLI contract tests (RED, before scripts/install.py exists).

Contract under test (approved design):
  python3 scripts/install.py (--global | --project DIR | --target DIR)
                             [--dry-run] [--set-defaults] [--replace]

Every test runs the real script as a subprocess with a fake HOME/XDG under the
approved temp root, so the real global config is never touched. When the
script does not exist yet, each test fails with an explicit contract message
(RED), never with a bare file-not-found error.
"""

from __future__ import annotations

import json
import os
import shutil
import stat
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import support_pkg as sp

PAYLOAD_RELS = sorted(
    ["agents/" + n + ".md" for n in sp.AGENT_NAMES] + ["commands/" + c + ".md" for c in sp.COMMAND_NAMES]
)
EXPECTED_WITH_DEFAULTS = sorted(PAYLOAD_RELS + ["opencode.json"])
MARKER = "SECRET_MARKER_42"
# A2-R: 8 agents + 8 commands = 16 markdown payload files under config/.
EXPECTED_PAYLOAD_COUNT = 16
STANDALONE_RELS = ["commands/" + c + ".md" for c in sp.STANDALONE_COMMAND_NAMES]


class InstallerCliTest(unittest.TestCase):
    def setUp(self):
        self.tmp = sp.make_temp("emt-install-")
        self.home = self.tmp / "home"
        self.home.mkdir()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_cli(self, args, xdg=None, cwd=None):
        return sp.run_installer(args, home=self.home, xdg=xdg, cwd=cwd)

    def out(self, r):
        return sp.sanitize((r.stdout or "") + (r.stderr or ""))

    # -- entrypoint and CLI shape -------------------------------------------

    def test_entrypoint_exists(self):
        self.assertTrue(
            sp.installer_script().is_file(),
            "RED: scripts/install.py is missing; CLI contract not implemented",
        )

    def test_no_destination_flag_is_an_error(self):
        r = self.run_cli([])
        self.assertNotEqual(0, r.returncode, "no destination must be refused: " + self.out(r))
        self.assertEqual(set(), sp.rel_files(self.home), "refusal must not write anything")

    def test_destination_flags_are_mutually_exclusive(self):
        other = self.tmp / "other"
        r = self.run_cli(["--global", "--project", str(other)])
        self.assertNotEqual(0, r.returncode, "two destinations must be refused: " + self.out(r))
        self.assertFalse(other.exists(), "refusal must not create the project dir")
        r = self.run_cli(["--target", str(self.tmp / "t"), "--project", str(other)])
        self.assertNotEqual(0, r.returncode, "--target + --project must be refused")
        self.assertFalse((self.tmp / "t").exists())

    # -- destinations ---------------------------------------------------------

    def test_target_fresh_install_copies_allowlist_only(self):
        dest = self.tmp / "target"
        r = self.run_cli(["--target", str(dest)])
        self.assertEqual(0, r.returncode, "fresh --target install failed: " + self.out(r))
        self.assertEqual(set(PAYLOAD_RELS), sp.rel_files(dest), "payload must be exactly the allowlist")
        self.assertFalse((dest / "opencode.json").exists(), "no JSON may be written without --set-defaults")
        self.assertFalse((dest / sp.BACKUP_DIR_NAME).exists())
        self.assertFalse((dest / sp.LOCK_NAME).exists(), "no lock file may remain after a run")

    def test_target_set_defaults_creates_minimal_config(self):
        dest = self.tmp / "target"
        r = self.run_cli(["--target", str(dest), "--set-defaults"])
        self.assertEqual(0, r.returncode, self.out(r))
        self.assertEqual(set(EXPECTED_WITH_DEFAULTS), sp.rel_files(dest))
        cfg = json.loads((dest / "opencode.json").read_text(encoding="utf-8"))
        self.assertEqual({"$schema", "default_agent", "model"}, set(cfg.keys()))
        self.assertEqual("https://opencode.ai/config.json", cfg["$schema"])
        self.assertEqual("EngineeringManager", cfg["default_agent"])
        self.assertEqual(sp.MODEL_EM, cfg["model"])

    def test_project_install_uses_dot_opencode_dir(self):
        proj = self.tmp / "proj"
        r = self.run_cli(["--project", str(proj), "--set-defaults"])
        self.assertEqual(0, r.returncode, self.out(r))
        oc = proj / ".opencode"
        self.assertEqual(set(EXPECTED_WITH_DEFAULTS), sp.rel_files(oc))

    def test_project_relative_path_with_spaces(self):
        r = self.run_cli(["--project", "rel dir"], cwd=self.home)
        self.assertEqual(0, r.returncode, self.out(r))
        self.assertTrue((self.home / "rel dir" / ".opencode" / "agents").is_dir())

    def test_global_prefers_xdg_config_home(self):
        xdg = self.tmp / "xdg"
        r = self.run_cli(["--global", "--set-defaults"], xdg=xdg)
        self.assertEqual(0, r.returncode, self.out(r))
        self.assertEqual(set(EXPECTED_WITH_DEFAULTS), sp.rel_files(xdg / "opencode"))
        self.assertFalse((self.home / ".config").exists(), "XDG_CONFIG_HOME must win over HOME/.config")

    def test_global_falls_back_to_home_config(self):
        r = self.run_cli(["--global", "--set-defaults"], xdg=None)
        self.assertEqual(0, r.returncode, self.out(r))
        self.assertEqual(set(EXPECTED_WITH_DEFAULTS), sp.rel_files(self.home / ".config" / "opencode"))

    def test_target_path_with_spaces(self):
        dest = self.tmp / "dest with spaces"
        r = self.run_cli(["--target", str(dest)])
        self.assertEqual(0, r.returncode, self.out(r))
        self.assertEqual(set(PAYLOAD_RELS), sp.rel_files(dest))

    # -- dry-run --------------------------------------------------------------

    def test_dry_run_on_clean_target_writes_nothing(self):
        dest = self.tmp / "dry"
        r = self.run_cli(["--target", str(dest), "--dry-run", "--set-defaults"])
        self.assertEqual(0, r.returncode, self.out(r))
        self.assertFalse(dest.exists(), "dry-run must not even create the destination dir")

    def test_dry_run_with_collision_refuses_without_writes(self):
        dest = self.tmp / "dryc"
        (dest / "agents").mkdir(parents=True)
        (dest / "agents" / "Explorer.md").write_text("DIFFERENT\n", encoding="utf-8")
        r = self.run_cli(["--target", str(dest), "--dry-run"])
        self.assertNotEqual(0, r.returncode, "dry-run must refuse collisions: " + self.out(r))
        self.assertEqual({"agents/Explorer.md"}, sp.rel_files(dest), "dry-run must write nothing")
        self.assertEqual("DIFFERENT\n", (dest / "agents" / "Explorer.md").read_text(encoding="utf-8"))

    # -- JSON handling ----------------------------------------------------------

    def test_existing_json_untouched_without_set_defaults_even_with_replace(self):
        # V1.1: without --set-defaults the JSON is NEVER written, even when
        # --replace is given (--replace only governs payload file conflicts).
        dest = self.tmp / "nojson"
        dest.mkdir()
        cfg = dest / "opencode.json"
        original = '{ "custom" :  true, "model": "other/model" }\n'
        cfg.write_text(original, encoding="utf-8")
        r = self.run_cli(["--target", str(dest), "--replace"])
        self.assertEqual(0, r.returncode, self.out(r))
        self.assertEqual(
            original, cfg.read_text(encoding="utf-8"),
            "JSON must stay byte-identical without --set-defaults, even with --replace",
        )
        self.assertEqual(set(PAYLOAD_RELS + ["opencode.json"]), sp.rel_files(dest))
        self.assertFalse((dest / sp.BACKUP_DIR_NAME).exists(), "no JSON backup without --set-defaults")

    def test_set_defaults_alone_refused_on_different_existing_json(self):
        # V1.1: rule 3.5 covers JSON too. Changing an existing DIFFERENT JSON
        # requires BOTH --set-defaults and --replace, with a backup before the
        # write. --set-defaults alone must refuse before any write.
        dest = self.tmp / "needreplace"
        dest.mkdir()
        cfg = dest / "opencode.json"
        original = json.dumps(
            {"theme": "dark", "model": "other/model", "default_agent": "build"}, indent=1
        ) + "\n"
        cfg.write_text(original, encoding="utf-8")
        r = self.run_cli(["--target", str(dest), "--set-defaults"])
        self.assertNotEqual(
            0, r.returncode,
            "--set-defaults alone must refuse a different existing JSON (V1.1: --replace also required): "
            + self.out(r),
        )
        self.assertEqual(original, cfg.read_text(encoding="utf-8"), "refusal must happen before any write")
        self.assertEqual({"opencode.json"}, sp.rel_files(dest), "no payload write, no backup, no lock on refusal")
        self.assertFalse((dest / sp.BACKUP_DIR_NAME).exists())

    def test_set_defaults_with_replace_updates_and_backs_up_json_exactly(self):
        dest = self.tmp / "merge"
        dest.mkdir()
        cfg = dest / "opencode.json"
        original = json.dumps(
            {"theme": "dark", "model": "other/model", "default_agent": "build", "permissions": []}, indent=1
        ) + "\n"
        cfg.write_text(original, encoding="utf-8")
        r = self.run_cli(["--target", str(dest), "--set-defaults", "--replace"])
        self.assertEqual(0, r.returncode, self.out(r))
        after = json.loads(cfg.read_text(encoding="utf-8"))
        self.assertEqual("dark", after["theme"], "unrelated values must be preserved")
        self.assertEqual([], after["permissions"], "unrelated values must be preserved")
        self.assertEqual(sp.MODEL_EM, after["model"], "model must be updated")
        self.assertEqual("EngineeringManager", after["default_agent"], "default_agent must be updated")
        self.assertNotIn("$schema", after, "existing JSON must not gain $schema")
        backups = dest / sp.BACKUP_DIR_NAME
        run_dirs = [p for p in backups.iterdir() if p.is_dir()]
        self.assertEqual(1, len(run_dirs), "exactly one backup run dir expected")
        backup_json = run_dirs[0] / "opencode.json"
        self.assertTrue(backup_json.is_file(), "the pre-write JSON backup must exist")
        self.assertEqual(original, backup_json.read_text(encoding="utf-8"), "JSON backup must be byte-exact")
        if os.name == "posix":
            self.assertEqual(0o600, stat.S_IMODE(backup_json.stat().st_mode), "backup file must be 0600 on Linux")
        self.assertIn("agents/Explorer.md", sp.rel_files(dest), "payload must be installed too")

    def test_set_defaults_on_conforming_json_preserves_bytes_and_mtime(self):
        # V1.1: if the 2 target values are already conforming (any other keys,
        # any formatting), the JSON is not rewritten: bytes/mtime unchanged and
        # zero JSON backup; --replace is not required in that case.
        dest = self.tmp / "conform"
        dest.mkdir()
        cfg = dest / "opencode.json"
        original = '{"model":"' + sp.MODEL_EM + '","default_agent":"EngineeringManager","theme":"x"}'
        cfg.write_text(original, encoding="utf-8")
        before_mtime = cfg.stat().st_mtime_ns
        r = self.run_cli(["--target", str(dest), "--set-defaults"])
        self.assertEqual(0, r.returncode, self.out(r))
        self.assertEqual(original, cfg.read_text(encoding="utf-8"), "conforming JSON must keep exact bytes")
        self.assertEqual(before_mtime, cfg.stat().st_mtime_ns, "conforming JSON must not be rewritten")
        self.assertFalse((dest / sp.BACKUP_DIR_NAME).exists(), "zero JSON backup expected")
        self.assertEqual(set(PAYLOAD_RELS + ["opencode.json"]), sp.rel_files(dest))

    def test_invalid_json_refused_without_content_leak(self):
        dest = self.tmp / "badjson"
        dest.mkdir()
        cfg = dest / "opencode.json"
        cfg.write_text('{ "model": "x", broken ' + MARKER + " \n", encoding="utf-8")
        r = self.run_cli(["--target", str(dest), "--set-defaults"])
        self.assertNotEqual(0, r.returncode, "malformed JSON must be refused: " + self.out(r))
        self.assertNotIn(MARKER, self.out(r), "error output must not leak file contents")
        self.assertEqual({"opencode.json"}, sp.rel_files(dest), "refusal must happen before any write")

    def test_invalid_json_refused_even_without_set_defaults(self):
        # Without the flag the installer may still READ the strict JSON to
        # detect invalid config; malformed JSON is refused before any write.
        dest = self.tmp / "badnoflag"
        dest.mkdir()
        cfg = dest / "opencode.json"
        cfg.write_text('{ broken ' + MARKER + ' \n', encoding="utf-8")
        r = self.run_cli(["--target", str(dest)])
        self.assertNotEqual(0, r.returncode, "malformed JSON must be refused even without --set-defaults: " + self.out(r))
        self.assertNotIn(MARKER, self.out(r))
        self.assertEqual({"opencode.json"}, sp.rel_files(dest))

    def test_jsonc_destination_refused_before_any_write(self):
        dest = self.tmp / "jsonc"
        dest.mkdir()
        jc = dest / "opencode.jsonc"
        jc.write_text('{ "$schema": "https://opencode.ai/config.json" }\n', encoding="utf-8")
        r = self.run_cli(["--target", str(dest), "--set-defaults"])
        self.assertNotEqual(0, r.returncode, "an existing opencode.jsonc must be refused (manual handling): " + self.out(r))
        self.assertEqual({"opencode.jsonc"}, sp.rel_files(dest), "no write may happen next to a JSONC file")

    def test_json_and_jsonc_together_refused(self):
        dest = self.tmp / "double"
        dest.mkdir()
        (dest / "opencode.json").write_text("{}", encoding="utf-8")
        (dest / "opencode.jsonc").write_text("{}", encoding="utf-8")
        r = self.run_cli(["--target", str(dest), "--set-defaults"])
        self.assertNotEqual(0, r.returncode, self.out(r))
        self.assertEqual({"opencode.json", "opencode.jsonc"}, sp.rel_files(dest))

    def test_duplicate_keys_refused_without_leak(self):
        dest = self.tmp / "dup"
        dest.mkdir()
        cfg = dest / "opencode.json"
        # Valid JSON syntax (duplicate keys parse), but the installer must
        # refuse duplicates. The marker sits INSIDE a value so the no-leak
        # check is meaningful; malformed syntax is covered by its own test.
        cfg.write_text('{"model": "a", "model": "' + MARKER + '"}\n', encoding="utf-8")
        r = self.run_cli(["--target", str(dest), "--set-defaults", "--replace"])
        self.assertNotEqual(0, r.returncode, "duplicate keys must be refused: " + self.out(r))
        self.assertNotIn(MARKER, self.out(r), "error output must not leak file contents")
        self.assertEqual({"opencode.json"}, sp.rel_files(dest), "refusal must happen before any write")

    def test_non_object_json_refused(self):
        dest = self.tmp / "arr"
        dest.mkdir()
        (dest / "opencode.json").write_text('["not", "object"]', encoding="utf-8")
        r = self.run_cli(["--target", str(dest), "--set-defaults"])
        self.assertNotEqual(0, r.returncode, "non-object JSON must be refused: " + self.out(r))
        self.assertEqual({"opencode.json"}, sp.rel_files(dest))

    # -- collisions, idempotence, replace --------------------------------------

    def test_collision_refused_before_any_write(self):
        dest = self.tmp / "coll"
        (dest / "agents").mkdir(parents=True)
        (dest / "commands").mkdir(parents=True)
        (dest / "agents" / "Explorer.md").write_text("OLD\n", encoding="utf-8")
        (dest / "commands" / "em.md").write_text("OLD2\n", encoding="utf-8")
        r = self.run_cli(["--target", str(dest)])
        self.assertNotEqual(0, r.returncode, "differing existing files must be refused without --replace: " + self.out(r))
        self.assertEqual("OLD\n", (dest / "agents" / "Explorer.md").read_text(encoding="utf-8"))
        self.assertEqual("OLD2\n", (dest / "commands" / "em.md").read_text(encoding="utf-8"))
        self.assertEqual(
            {"agents/Explorer.md", "commands/em.md"},
            sp.rel_files(dest),
            "a refusal must leave the destination untouched (no partial writes, no backups, no lock)",
        )

    def test_identical_files_are_idempotent(self):
        fresh = self.tmp / "fresh"
        r = self.run_cli(["--target", str(fresh), "--set-defaults"])
        self.assertEqual(0, r.returncode, self.out(r))
        twin = self.tmp / "twin"
        shutil.copytree(fresh, twin)
        before = {
            rel: ((twin / rel).read_bytes(), (twin / rel).stat().st_mtime_ns)
            for rel in sp.rel_files(twin)
        }
        r = self.run_cli(["--target", str(twin), "--set-defaults"])
        self.assertEqual(0, r.returncode, self.out(r))
        self.assertFalse((twin / sp.BACKUP_DIR_NAME).exists(), "identical files must not be backed up")
        for rel, (content, mtime) in before.items():
            self.assertEqual(content, (twin / rel).read_bytes(), "identical file must not be rewritten: " + rel)
            self.assertEqual(mtime, (twin / rel).stat().st_mtime_ns, "identical file must not be rewritten: " + rel)

    def test_replace_backs_up_exact_private_copy(self):
        dest = self.tmp / "repl"
        (dest / "agents").mkdir(parents=True)
        target = dest / "agents" / "Explorer.md"
        target.write_text("OLD CONTENT\n", encoding="utf-8")
        r = self.run_cli(["--target", str(dest), "--replace"])
        self.assertEqual(0, r.returncode, self.out(r))
        self.assertNotEqual("OLD CONTENT\n", target.read_text(encoding="utf-8"))
        backups = dest / sp.BACKUP_DIR_NAME
        self.assertTrue(backups.is_dir(), "--replace must create the private backup dir")
        run_dirs = [p for p in backups.iterdir() if p.is_dir()]
        self.assertEqual(1, len(run_dirs), "exactly one backup run dir expected")
        backup_file = run_dirs[0] / "agents" / "Explorer.md"
        self.assertTrue(backup_file.is_file(), "backup must preserve the relative path")
        self.assertEqual("OLD CONTENT\n", backup_file.read_text(encoding="utf-8"), "backup must be an exact copy")
        if os.name == "posix":
            self.assertEqual(0o700, stat.S_IMODE(backups.stat().st_mode), "backup dir must be 0700 on Linux")
            self.assertEqual(0o700, stat.S_IMODE(run_dirs[0].stat().st_mode), "backup run dir must be 0700 on Linux")
            self.assertEqual(0o600, stat.S_IMODE(backup_file.stat().st_mode), "backup file must be 0600 on Linux")

    def test_replace_still_refuses_embedded_config_collision(self):
        dest = self.tmp / "emb"
        (dest / "agents").mkdir(parents=True)
        cfg = dest / "opencode.json"
        cfg.write_text(json.dumps({"agents": {"Architect": {"mode": "subagent"}}}), encoding="utf-8")
        (dest / "agents" / "Explorer.md").write_text("OLD\n", encoding="utf-8")
        original_cfg = cfg.read_text(encoding="utf-8")
        r = self.run_cli(["--target", str(dest), "--set-defaults", "--replace"])
        self.assertNotEqual(
            0, r.returncode, "embedded agent/command entries colliding with team IDs must be refused even with --replace: " + self.out(r)
        )
        self.assertEqual(original_cfg, cfg.read_text(encoding="utf-8"))
        self.assertEqual("OLD\n", (dest / "agents" / "Explorer.md").read_text(encoding="utf-8"))
        self.assertFalse((dest / sp.BACKUP_DIR_NAME).exists(), "refusal must not create backups")

    # -- filesystem guards ------------------------------------------------------

    def test_symlinked_agents_dir_refused(self):
        outside = self.tmp / "outside"
        outside.mkdir()
        dest = self.tmp / "sym"
        dest.mkdir()
        (dest / "agents").symlink_to(outside, target_is_directory=True)
        r = self.run_cli(["--target", str(dest)])
        self.assertNotEqual(0, r.returncode, "symlinked managed path must be refused: " + self.out(r))
        self.assertEqual(set(), sp.rel_files(outside), "nothing may be written through the symlink")
        self.assertTrue((dest / "agents").is_symlink())
        self.assertEqual(set(), {p.name for p in dest.iterdir()} - {"agents"})

    def test_symlinked_payload_file_refused(self):
        outside = self.tmp / "outside.txt"
        outside.write_text("ORIGINAL\n", encoding="utf-8")
        dest = self.tmp / "symf"
        (dest / "agents").mkdir(parents=True)
        (dest / "agents" / "Explorer.md").symlink_to(outside)
        r = self.run_cli(["--target", str(dest)])
        self.assertNotEqual(0, r.returncode, "symlinked payload file must be refused: " + self.out(r))
        self.assertEqual("ORIGINAL\n", outside.read_text(encoding="utf-8"), "target of symlink must stay untouched")
        link = dest / "agents" / "Explorer.md"
        self.assertTrue(link.is_symlink(), "the symlink must be left in place, not followed or replaced")
        self.assertEqual({"agents/Explorer.md"}, sp.rel_files(dest), "nothing else may be written")

    def test_type_mismatch_refused(self):
        dest = self.tmp / "type"
        (dest / "agents" / "Explorer.md").mkdir(parents=True)
        r = self.run_cli(["--target", str(dest)])
        self.assertNotEqual(0, r.returncode, "a directory where a file is expected must be refused: " + self.out(r))
        self.assertTrue((dest / "agents" / "Explorer.md").is_dir())

    # -- locking and errors -----------------------------------------------------

    def test_stale_lock_is_refused_and_not_removed(self):
        dest = self.tmp / "lock"
        dest.mkdir()
        lock = dest / sp.LOCK_NAME
        lock.write_text("999999\n", encoding="utf-8")
        r = self.run_cli(["--target", str(dest)])
        self.assertNotEqual(0, r.returncode, "a busy/stale lock must be refused, not auto-removed: " + self.out(r))
        self.assertTrue(lock.is_file(), "the old lock must not be auto-removed")
        self.assertEqual("999999\n", lock.read_text(encoding="utf-8"))
        self.assertEqual({sp.LOCK_NAME}, sp.rel_files(dest), "no other write may happen while locked")

    def test_concurrent_installs_leave_a_consistent_tree(self):
        sp.require_installer()
        dest = self.tmp / "conc"
        procs = [sp.popen_installer(["--target", str(dest), "--set-defaults"], home=self.home) for _ in range(2)]
        results = [p.communicate(timeout=120) for p in procs]
        codes = [p.returncode for p in procs]
        self.assertTrue(any(c == 0 for c in codes), "at least one install must succeed: %s" % codes)
        files = sp.rel_files(dest)
        self.assertEqual(set(EXPECTED_WITH_DEFAULTS), files, "final tree must be complete, no partial writes: %s" % sorted(files))
        for rel in files:
            self.assertGreater((dest / rel).stat().st_size, 0, "no empty/partial file: " + rel)
        cfg = json.loads((dest / "opencode.json").read_text(encoding="utf-8"))
        self.assertEqual("EngineeringManager", cfg["default_agent"])
        for p, (out, err) in zip(procs, results):
            self.assertNotIn(MARKER, sp.sanitize(out + err))

    def test_io_error_reports_failure_with_message(self):
        if hasattr(os, "geteuid") and os.geteuid() == 0:
            self.skipTest("root ignores permission bits; IO-error path not exercisable")
        dest = self.tmp / "ro"
        dest.mkdir()
        try:
            os.chmod(dest, 0o555)
            r = self.run_cli(["--target", str(dest), "--set-defaults"])
            self.assertNotEqual(0, r.returncode, "unwritable destination must fail: " + self.out(r))
            self.assertTrue(self.out(r).strip(), "failure must come with a message")
            self.assertEqual(set(), sp.rel_files(dest), "nothing may be written into a read-only dir")
        finally:
            os.chmod(dest, 0o755)


class A2RInstallerContractTest(unittest.TestCase):
    """A2-R RED contract: 16-file payload (8 commands), MULTI-AGENTS.md never
    installed, standalone wrapper collisions, embedded commands.* collisions,
    build/plan JSON keys preserved, idempotent second run."""

    def setUp(self):
        self.tmp = sp.make_temp("emt-a2r-")
        self.home = self.tmp / "home"
        self.home.mkdir()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_cli(self, args, xdg=None, cwd=None):
        return sp.run_installer(args, home=self.home, xdg=xdg, cwd=cwd)

    def out(self, r):
        return sp.sanitize((r.stdout or "") + (r.stderr or ""))

    def test_payload_allowlist_is_exactly_16_markdown_files(self):
        self.assertEqual(EXPECTED_PAYLOAD_COUNT, len(PAYLOAD_RELS))
        self.assertTrue(all(rel.endswith(".md") for rel in PAYLOAD_RELS))
        for rel in STANDALONE_RELS:
            self.assertIn(rel, PAYLOAD_RELS, "standalone wrapper must be in the closed payload list: " + rel)

    def test_fresh_install_copies_16_markdown_files_byte_identical(self):
        dest = self.tmp / "fresh16"
        r = self.run_cli(["--target", str(dest)])
        self.assertEqual(0, r.returncode, "fresh --target install failed: " + self.out(r))
        files = sp.rel_files(dest)
        self.assertEqual(set(PAYLOAD_RELS), files)
        self.assertEqual(EXPECTED_PAYLOAD_COUNT, len(files), "RED: 16 markdown files expected (8 commands)")
        for rel in PAYLOAD_RELS:
            src = sp.REPO_ROOT / "config" / rel
            self.assertEqual(
                src.read_bytes(), (dest / rel).read_bytes(),
                "installed bytes must be identical to the payload: " + rel,
            )
        self.assertFalse((dest / "opencode.json").exists())

    def test_fresh_install_with_set_defaults_writes_17_files(self):
        dest = self.tmp / "fresh17"
        r = self.run_cli(["--target", str(dest), "--set-defaults"])
        self.assertEqual(0, r.returncode, self.out(r))
        files = sp.rel_files(dest)
        self.assertEqual(set(EXPECTED_WITH_DEFAULTS), files)
        self.assertEqual(EXPECTED_PAYLOAD_COUNT + 1, len(files), "RED: 16 markdown + 1 JSON = 17 files")

    def test_multi_agents_guide_is_never_installed(self):
        dest = self.tmp / "noguide"
        r = self.run_cli(["--target", str(dest), "--set-defaults", "--replace"])
        self.assertEqual(0, r.returncode, self.out(r))
        leaked = [p for p in dest.rglob(sp.ROOT_GUIDE_NAME)]
        self.assertEqual([], leaked, "RED: MULTI-AGENTS.md must NOT be installed into the destination")
        self.assertNotIn(sp.ROOT_GUIDE_NAME, sp.rel_files(dest))

    def test_preexisting_multi_agents_md_preserved_even_with_replace(self):
        dest = self.tmp / "keepguide"
        dest.mkdir()
        guide = dest / sp.ROOT_GUIDE_NAME
        original = "# my own notes\n\nDo not touch.\n"
        guide.write_text(original, encoding="utf-8")
        before_mtime = guide.stat().st_mtime_ns
        r = self.run_cli(["--target", str(dest), "--replace", "--set-defaults"])
        self.assertEqual(0, r.returncode, self.out(r))
        self.assertEqual(original, guide.read_text(encoding="utf-8"), "pre-existing guide must keep exact bytes")
        self.assertEqual(before_mtime, guide.stat().st_mtime_ns, "pre-existing guide must not be rewritten")
        self.assertEqual(set(PAYLOAD_RELS) | {sp.ROOT_GUIDE_NAME, "opencode.json"}, sp.rel_files(dest))
        backups = dest / sp.BACKUP_DIR_NAME
        if backups.is_dir():
            self.assertEqual(
                [], [p for p in backups.rglob(sp.ROOT_GUIDE_NAME)],
                "the guide must never be backed up (it is not a managed file)",
            )

    def test_standalone_wrapper_collisions_refused_without_replace_before_any_write(self):
        dest = self.tmp / "coll3"
        (dest / "commands").mkdir(parents=True)
        originals = {}
        for rel in STANDALONE_RELS:
            target = dest / rel
            content = "OLD %s\n" % rel
            target.write_text(content, encoding="utf-8")
            originals[rel] = content
        r = self.run_cli(["--target", str(dest)])
        self.assertNotEqual(
            0, r.returncode,
            "RED: collisions on review/doc/security must be refused without --replace: " + self.out(r),
        )
        for rel, content in originals.items():
            self.assertEqual(content, (dest / rel).read_text(encoding="utf-8"))
        self.assertEqual(
            set(STANDALONE_RELS), sp.rel_files(dest),
            "refusal must happen before ANY write (no partial payload, no backups, no lock)",
        )
        self.assertFalse((dest / sp.BACKUP_DIR_NAME).exists())

    def test_standalone_wrapper_collisions_replaced_with_exact_backup_with_replace(self):
        dest = self.tmp / "repl3"
        (dest / "commands").mkdir(parents=True)
        originals = {}
        for rel in STANDALONE_RELS:
            target = dest / rel
            content = "OLD %s\n" % rel
            target.write_text(content, encoding="utf-8")
            originals[rel] = content
        r = self.run_cli(["--target", str(dest), "--replace"])
        self.assertEqual(0, r.returncode, self.out(r))
        for rel in STANDALONE_RELS:
            src = sp.REPO_ROOT / "config" / rel
            if not src.is_file():
                self.fail("RED: payload source %s is missing (standalone wrapper not created yet)" % rel)
            self.assertEqual(
                src.read_bytes(), (dest / rel).read_bytes(),
                "with --replace the wrapper must be replaced by the payload bytes: " + rel,
            )
        backups = dest / sp.BACKUP_DIR_NAME
        run_dirs = [p for p in backups.iterdir() if p.is_dir()]
        self.assertEqual(1, len(run_dirs), "exactly one backup run dir expected")
        for rel, content in originals.items():
            backup_file = run_dirs[0] / rel
            self.assertTrue(backup_file.is_file(), "backup must preserve the relative path: " + rel)
            self.assertEqual(content, backup_file.read_text(encoding="utf-8"), "backup must be byte-exact: " + rel)

    def test_embedded_commands_collision_refused_even_with_replace(self):
        dest = self.tmp / "embcmd"
        (dest / "commands").mkdir(parents=True)
        cfg = dest / "opencode.json"
        cfg.write_text(
            json.dumps({"commands": {"review": {"description": "x"}, "doc": {}, "security": {}}}),
            encoding="utf-8",
        )
        (dest / "commands" / "em.md").write_text("OLD\n", encoding="utf-8")
        original_cfg = cfg.read_text(encoding="utf-8")
        r = self.run_cli(["--target", str(dest), "--set-defaults", "--replace"])
        self.assertNotEqual(
            0, r.returncode,
            "RED: embedded commands.review/doc/security entries must be refused even with --replace: "
            + self.out(r),
        )
        self.assertEqual(original_cfg, cfg.read_text(encoding="utf-8"))
        self.assertEqual("OLD\n", (dest / "commands" / "em.md").read_text(encoding="utf-8"))
        self.assertEqual({"opencode.json", "commands/em.md"}, sp.rel_files(dest), "refusal before any write")
        self.assertFalse((dest / sp.BACKUP_DIR_NAME).exists())

    def test_local_json_build_plan_keys_preserved(self):
        # Without --set-defaults: exact bytes untouched even with --replace.
        dest = self.tmp / "bp1"
        dest.mkdir()
        cfg = dest / "opencode.json"
        original = json.dumps(
            {"build": {"custom": True}, "plan": {"custom": True}, "model": "other/model",
             "default_agent": "build"}, indent=1
        ) + "\n"
        cfg.write_text(original, encoding="utf-8")
        r = self.run_cli(["--target", str(dest), "--replace"])
        self.assertEqual(0, r.returncode, self.out(r))
        self.assertEqual(original, cfg.read_text(encoding="utf-8"), "build/plan JSON must stay byte-identical")
        # With --set-defaults --replace: semantics preserved, only the 2 defaults change.
        r = self.run_cli(["--target", str(dest), "--set-defaults", "--replace"])
        self.assertEqual(0, r.returncode, self.out(r))
        after = json.loads(cfg.read_text(encoding="utf-8"))
        self.assertEqual({"custom": True}, after["build"], "build key must be preserved semantically")
        self.assertEqual({"custom": True}, after["plan"], "plan key must be preserved semantically")
        self.assertEqual(sp.MODEL_EM, after["model"])
        self.assertEqual("EngineeringManager", after["default_agent"])

    def test_second_run_on_same_target_is_idempotent(self):
        dest = self.tmp / "twice"
        r = self.run_cli(["--target", str(dest), "--set-defaults"])
        self.assertEqual(0, r.returncode, self.out(r))
        before = {
            rel: ((dest / rel).read_bytes(), (dest / rel).stat().st_mtime_ns)
            for rel in sp.rel_files(dest)
        }
        r = self.run_cli(["--target", str(dest), "--set-defaults"])
        self.assertEqual(0, r.returncode, "second run must succeed: " + self.out(r))
        self.assertEqual(set(before), sp.rel_files(dest), "second run must not add/remove files")
        for rel, (content, mtime) in before.items():
            self.assertEqual(content, (dest / rel).read_bytes(), "idempotent bytes: " + rel)
            self.assertEqual(mtime, (dest / rel).stat().st_mtime_ns, "idempotent mtime: " + rel)
        self.assertFalse((dest / sp.BACKUP_DIR_NAME).exists(), "no backups on an idempotent second run")


if __name__ == "__main__":
    unittest.main()
