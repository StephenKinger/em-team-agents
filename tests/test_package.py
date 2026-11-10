"""Static package contract tests for em-team-agents (RED, before production).

These tests pin the approved design of the public package payload:
layout, agent frontmatter (mode/color/model/ordered permissions preserved from
the 8 source profiles, Concepteur renamed to Architect inside the package only),
prompts with the response-language contract, the 5 command templates with
$ARGUMENTS language priority, the minimal config/opencode.json, README /
INSTALL install commands, .gitignore, a stdlib-only installer entrypoint, and
secret/portability hygiene.

English is enforced by (a) the static language clauses asserted below on agent
prompts and command templates and (b) a separate HUMAN prose review (checklist
kept in the temp evidence dir). No ASCII-only test is imposed here: that is not
a proof of English and would forbid valid accented English or multilingual
fixtures. These are static contract checks, not LLM proofs.
"""

from __future__ import annotations

import ast
import json
import re
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import support_pkg as sp

# Prompt language contract (static, not an LLM proof): every agent prompt must
# state that it answers in the language of the latest human request unless an
# explicit user preference overrides it, and must honor the response_language
# transmitted by EM.
LANG_RULE = re.compile(r"respond[^.\n]{0,120}language of the latest human (request|message)", re.I)
OVERRIDE_RULE = re.compile(r"explicit[^.\n]{0,80}preference|unless[^.\n]{0,120}explicit|override", re.I)
RESPONSE_LANGUAGE_TOKEN = "response_language"
# Command templates: the language of the user arguments wins over the wrapper
# language; $ARGUMENTS blocks stay explicit.
ARG_LANG = re.compile(r"language of (the )?(user('s)? )?arguments|arguments[^.\n]{0,100}language", re.I)
# EM is the only delegator; the three optional audits run only on request.
DELEGATE_ONLY = re.compile(
    r"only (engineeringmanager|em)[^.\n]{0,120}delegat|subagents?[^.\n]{0,120}(cannot|do not|may not|never)[^.\n]{0,60}delegat",
    re.I,
)
OPTIONAL_ONLY = re.compile(r"optional|only (when|if|after)[^.\n]{0,140}(request|asked|demanded)", re.I)

INSTALL_FLAGS = ["--global", "--project", "--target", "--dry-run", "--set-defaults", "--replace"]


class LayoutTest(unittest.TestCase):
    def test_expected_package_files_exist(self):
        missing = [f for f in sp.EXPECTED_PACKAGE_FILES if not (sp.REPO_ROOT / f).is_file()]
        self.assertEqual(
            [],
            missing,
            "RED: package contract files missing (design: config/opencode.json, "
            "config/agents/<8>.md, config/commands/<5>.md, README.md, INSTALL.md, "
            ".gitignore, scripts/install.py, tests/): %s" % missing,
        )

    def test_agents_dir_has_exactly_the_8_expected_names(self):
        adir = sp.REPO_ROOT / "config" / "agents"
        if not adir.is_dir():
            self.fail("RED: config/agents/ is missing; expected the 8 profiles " + ", ".join(sp.AGENT_NAMES))
        names = sorted(p.stem for p in adir.glob("*.md"))
        self.assertEqual(sorted(sp.AGENT_NAMES), names)
        self.assertNotIn("Concepteur", names, "Concepteur must be renamed to Architect inside the package")

    def test_commands_dir_has_exactly_the_5_expected_names(self):
        cdir = sp.REPO_ROOT / "config" / "commands"
        if not cdir.is_dir():
            self.fail("RED: config/commands/ is missing; expected " + ", ".join(sp.COMMAND_NAMES))
        names = sorted(p.stem for p in cdir.glob("*.md"))
        self.assertEqual(sorted(sp.COMMAND_NAMES), names)


class AgentContractTest(unittest.TestCase):
    def _agent_path(self, name):
        return sp.REPO_ROOT / "config" / "agents" / (name + ".md")

    def test_agent_frontmatter_matches_source_contract(self):
        for name in sp.AGENT_NAMES:
            with self.subTest(agent=name):
                path = self._agent_path(name)
                if not path.is_file():
                    self.fail("RED: config/agents/%s.md is missing" % name)
                fields, permissions, _body = sp.parse_frontmatter(path.read_text(encoding="utf-8"))
                self.assertEqual(sp.EXPECTED_MODES[name], fields.get("mode"), "mode mismatch")
                self.assertEqual(sp.EXPECTED_MODELS[name], fields.get("model"), "model mismatch")
                self.assertEqual(sp.EXPECTED_COLORS[name], fields.get("color"), "color mismatch")
                self.assertTrue(fields.get("description"), "description must be non-empty")
                self.assertEqual(
                    sp.EXPECTED_PERMISSIONS[name],
                    permissions,
                    "permissions (actions, resources, effects, ORDER) must match the source profile",
                )

    def test_agent_prompts_carry_the_language_contract_in_english(self):
        for name in sp.AGENT_NAMES:
            with self.subTest(agent=name):
                path = self._agent_path(name)
                if not path.is_file():
                    self.fail("RED: config/agents/%s.md is missing" % name)
                _fields, _perms, body = sp.parse_frontmatter(path.read_text(encoding="utf-8"))
                self.assertRegex(body, LANG_RULE, "prompt must state the latest-human-request language rule")
                self.assertRegex(body, OVERRIDE_RULE, "prompt must allow an explicit user preference override")
                self.assertIn(
                    RESPONSE_LANGUAGE_TOKEN,
                    body,
                    "prompt must honor the response_language transmitted by EM (handoff language is not a rule)",
                )

    def test_em_is_the_only_delegator_and_optional_agents_are_on_request(self):
        path = self._agent_path("EngineeringManager")
        if not path.is_file():
            self.fail("RED: config/agents/EngineeringManager.md is missing")
        _fields, perms, body = sp.parse_frontmatter(path.read_text(encoding="utf-8"))
        subagent_resources = sorted(r for (a, r, _e) in perms if a == "subagent")
        self.assertEqual(sorted(sp.SUBAGENT_NAMES), subagent_resources)
        self.assertNotIn("Concepteur", subagent_resources, "EM must reference Architect, not Concepteur")
        for name in sp.SUBAGENT_NAMES:
            self.assertIn(name, body, "EM workflow must mention " + name)
        self.assertRegex(body, DELEGATE_ONLY, "EM must state that only EM delegates")
        self.assertRegex(body, OPTIONAL_ONLY, "Reviewer/Documentalist/SecurityOfficer must be optional, on request only")
        self.assertIn(RESPONSE_LANGUAGE_TOKEN, body, "EM must deduce and transmit response_language")

    def test_no_concepteur_in_active_config_ids_or_references(self):
        # Active profile IDs and references live only under config/ (agent
        # files, command files, team JSON). English documentation (README,
        # INSTALL, scripts) MAY quote the legacy id in migration notes; the
        # old global Concepteur may remain and is cleaned up manually.
        offenders = []
        cfg_root = sp.REPO_ROOT / "config"
        if cfg_root.is_dir():
            for p in sorted(cfg_root.rglob("*")):
                if not p.is_file():
                    continue
                rel = p.relative_to(sp.REPO_ROOT).as_posix()
                text = p.read_text(encoding="utf-8", errors="replace")
                if "Concepteur" in text:
                    offenders.append(rel)
        self.assertEqual([], offenders, "active config must reference Architect only: %s" % offenders)
        self.assertFalse(
            (cfg_root / "agents" / "Concepteur.md").exists(),
            "no active Concepteur profile file may exist in the payload",
        )


class CommandContractTest(unittest.TestCase):
    def test_command_templates_contract(self):
        for name in sp.COMMAND_NAMES:
            with self.subTest(command=name):
                path = sp.REPO_ROOT / "config" / "commands" / (name + ".md")
                if not path.is_file():
                    self.fail("RED: config/commands/%s.md is missing" % name)
                fields, _perms, body = sp.parse_frontmatter(path.read_text(encoding="utf-8"))
                self.assertEqual("EngineeringManager", fields.get("agent"), "commands must select EM")
                self.assertEqual("false", fields.get("subagent"), "commands must stay in the current session")
                self.assertTrue(fields.get("description"), "description must be non-empty")
                self.assertIn("$ARGUMENTS", body, "template must keep an explicit $ARGUMENTS block")
                self.assertRegex(body, ARG_LANG, "template must give priority to the language of the user arguments")


class ConfigContractTest(unittest.TestCase):
    def test_config_opencode_json_is_minimal_and_exact(self):
        path = sp.REPO_ROOT / "config" / "opencode.json"
        if not path.is_file():
            self.fail("RED: config/opencode.json is missing (minimal template with $schema/default_agent/model)")
        raw = path.read_text(encoding="utf-8")
        cfg = json.loads(raw)  # strict JSON: comments or trailing commas must fail
        self.assertEqual({"$schema", "default_agent", "model"}, set(cfg.keys()), "config must stay minimal")
        self.assertEqual("https://opencode.ai/config.json", cfg["$schema"])
        self.assertEqual("EngineeringManager", cfg["default_agent"])
        self.assertEqual(sp.MODEL_EM, cfg["model"])


class DocsAndScriptsContractTest(unittest.TestCase):
    def test_readme_documents_the_install_command(self):
        path = sp.REPO_ROOT / "README.md"
        if not path.is_file():
            self.fail("RED: README.md is missing")
        text = path.read_text(encoding="utf-8")
        self.assertIn("python3 scripts/install.py", text, "README must document the CLI install command")

    def test_install_md_documents_the_cli_contract(self):
        path = sp.REPO_ROOT / "INSTALL.md"
        if not path.is_file():
            self.fail("RED: INSTALL.md is missing")
        text = path.read_text(encoding="utf-8")
        self.assertIn("python3 scripts/install.py", text)
        for flag in INSTALL_FLAGS:
            self.assertIn(flag, text, "INSTALL.md must document " + flag)
        self.assertIn(sp.BACKUP_DIR_NAME, text, "INSTALL.md must document the private backup dir")
        self.assertIn("JSONC", text, "INSTALL.md must state that JSONC destinations are refused (manual handling)")
        self.assertIn("Linux", text, "INSTALL.md must state Linux-only support (no Windows/macOS promise)")

    def test_gitignore_covers_backups_and_protects_license_and_tests(self):
        path = sp.REPO_ROOT / ".gitignore"
        if not path.is_file():
            self.fail("RED: .gitignore is missing")
        text = path.read_text(encoding="utf-8")
        self.assertIn(sp.BACKUP_DIR_NAME + "/", text, ".gitignore must ignore the private backup dir")
        self.assertNotIn("LICENSE", text, ".gitignore must not ignore LICENSE")
        self.assertNotIn("tests", text, ".gitignore must not ignore tests")

    def test_gitignore_backup_pattern_effective_via_git_check_ignore(self):
        if shutil.which("git") is None:
            self.skipTest("git binary not available")
        gi = sp.REPO_ROOT / ".gitignore"
        if not gi.is_file():
            self.fail("RED: .gitignore is missing")
        tmp = sp.make_temp("emt-gitignore-")
        try:
            subprocess.run(["git", "init", "-q", str(tmp)], check=True, capture_output=True, timeout=30)
            (tmp / ".gitignore").write_text(gi.read_text(encoding="utf-8"), encoding="utf-8")
            r_backup = subprocess.run(
                ["git", "check-ignore", "-q", sp.BACKUP_DIR_NAME + "/run-1/some-file"],
                cwd=str(tmp), capture_output=True, timeout=30,
            )
            self.assertEqual(0, r_backup.returncode, "backup dir pattern must be ignored by git")
            for protected in ("LICENSE", "tests/test_package.py"):
                r = subprocess.run(
                    ["git", "check-ignore", "-q", protected],
                    cwd=str(tmp), capture_output=True, timeout=30,
                )
                self.assertNotEqual(0, r.returncode, protected + " must NOT be ignored")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_installer_script_exists_and_is_stdlib_only(self):
        path = sp.installer_script()
        if not path.is_file():
            self.fail("RED: scripts/install.py is missing (stdlib-only installer entrypoint)")
        tree = ast.parse(path.read_text(encoding="utf-8"), filename="install.py")
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.assertIn(
                        alias.name.split(".")[0], sys.stdlib_module_names,
                        "non-stdlib import: " + alias.name,
                    )
            elif isinstance(node, ast.ImportFrom):
                self.assertEqual(0, node.level, "single-file stdlib script: no relative imports")
                self.assertIn(
                    node.module.split(".")[0], sys.stdlib_module_names,
                    "non-stdlib import: " + str(node.module),
                )


class HygieneTest(unittest.TestCase):
    def test_no_secret_like_content_in_repo(self):
        findings = sp.scan_repo_hygiene()
        self.assertEqual(
            [],
            findings,
            "secret-hygiene findings (path, category only, no values): %s" % findings,
        )

    def test_no_personal_or_absolute_home_paths_in_repo_files(self):
        home = str(Path.home())
        offenders = []
        for p in sp.iter_repo_files():
            rel = p.relative_to(sp.REPO_ROOT).as_posix()
            text = p.read_text(encoding="utf-8", errors="replace")
            if home in text or re.search("/" + "home/[A-Za-z0-9._-]+", text):
                offenders.append(rel)
        self.assertEqual([], offenders, "no personal home path may appear in versioned files: %s" % offenders)


if __name__ == "__main__":
    unittest.main()
