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
import expected_payload as ep

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
            "RED: package contract files missing (design A2-R: config/opencode.json, "
            "config/agents/<8>.md, config/commands/<8>.md, MULTI-AGENTS.md (repo root, "
            "NOT installed), README.md, INSTALL.md, .gitignore, scripts/install.py, "
            "tests/): %s" % missing,
        )

    def test_agents_dir_has_exactly_the_8_expected_names(self):
        adir = sp.REPO_ROOT / "config" / "agents"
        if not adir.is_dir():
            self.fail("RED: config/agents/ is missing; expected the 8 profiles " + ", ".join(sp.AGENT_NAMES))
        names = sorted(p.stem for p in adir.glob("*.md"))
        self.assertEqual(sorted(sp.AGENT_NAMES), names)
        self.assertNotIn("Concepteur", names, "Concepteur must be renamed to Architect inside the package")

    def test_commands_dir_has_exactly_the_8_expected_names(self):
        cdir = sp.REPO_ROOT / "config" / "commands"
        if not cdir.is_dir():
            self.fail("RED: config/commands/ is missing; expected " + ", ".join(sp.COMMAND_NAMES))
        names = sorted(p.stem for p in cdir.glob("*.md"))
        self.assertEqual(sorted(sp.COMMAND_NAMES), names)
        self.assertEqual(
            8,
            len(names),
            "RED: A2-R expects 8 commands (5 /em* + review/doc/security), got %d" % len(names),
        )


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

    def test_standalone_wrappers_have_the_frozen_approved_content(self):
        # A2-R: review/doc/security wrappers exist and their FULL text is frozen
        # in tests/expected_payload.py (captured once from the approved source;
        # the test never reads the user's global config at run time).
        self.assertEqual(sorted(sp.STANDALONE_COMMAND_NAMES), sorted(ep.STANDALONE_COMMAND_NAMES))
        for name in ep.STANDALONE_COMMAND_NAMES:
            with self.subTest(command=name):
                self.assertIn(name, sp.COMMAND_NAMES)
                path = sp.REPO_ROOT / "config" / "commands" / (name + ".md")
                if not path.is_file():
                    self.fail("RED: config/commands/%s.md is missing (standalone wrapper)" % name)
                text = path.read_text(encoding="utf-8")
                fields, _perms, body = sp.parse_frontmatter(text)
                self.assertEqual("EngineeringManager", fields.get("agent"), "wrapper must select EM")
                self.assertEqual("false", fields.get("subagent"), "wrapper must stay in the current session")
                self.assertNotIn("model", fields, "wrapper must NOT carry its own model field")
                self.assertTrue(fields.get("description"), "description must be non-empty")
                norm = " ".join(body.split())
                self.assertIn("$ARGUMENTS", body, "wrapper must keep the $ARGUMENTS block")
                self.assertIn("optional_agent_path: standalone", norm)
                self.assertIn(
                    "Do not require, reconstruct or verify completion of the mandatory cycle",
                    norm,
                    "wrapper must not check the mandatory cycle",
                )
                self.assertEqual(
                    ep.EXPECTED_COMMAND_TEXT[name],
                    text,
                    "RED: config/commands/%s.md must be byte-identical to the frozen approved wrapper "
                    "(sha256 %s)" % (name, ep.FROZEN_SHA256["commands/%s.md" % name]),
                )


class ModifiedProfileContractTest(unittest.TestCase):
    """A2-R: only the BODIES of the 4 profiles change; frontmatter stays byte-identical."""

    def _agent_path(self, name):
        return sp.REPO_ROOT / "config" / "agents" / (name + ".md")

    def _frontmatter_block(self, text):
        lines = text.splitlines(keepends=True)
        self.assertEqual("---", lines[0].strip(), "agent file must open with a frontmatter fence")
        j = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
        return "".join(lines[: j + 1])

    def test_modified_profiles_exist(self):
        for name in ep.MODIFIED_PROFILE_NAMES:
            with self.subTest(agent=name):
                if not self._agent_path(name).is_file():
                    self.fail("RED: config/agents/%s.md is missing" % name)

    def test_modified_profiles_frontmatter_is_byte_identical_to_current(self):
        # Frontmatter (description/mode/model/color/ordered permissions) must be
        # strictly unchanged: byte-exact comparison with the frozen block.
        for name in ep.MODIFIED_PROFILE_NAMES:
            with self.subTest(agent=name):
                text = self._agent_path(name).read_text(encoding="utf-8")
                block = self._frontmatter_block(text)
                self.assertEqual(
                    ep.EXPECTED_PROFILE_FRONTMATTER[name],
                    block,
                    "RED: frontmatter of %s must stay byte-identical (model/permissions unchanged); "
                    "frozen sha256 %s" % (name, ep.FROZEN_SHA256["agents/%s.md#frontmatter" % name]),
                )

    def test_modified_profiles_bodies_carry_the_two_entry_paths(self):
        # New bodies must add the autonomous path: standalone commands,
        # optional_agent_path and "completion of the mandatory cycle is not a
        # prerequisite" (frozen snippets from the approved machine profiles).
        for name in ep.MODIFIED_PROFILE_NAMES:
            with self.subTest(agent=name):
                text = self._agent_path(name).read_text(encoding="utf-8")
                _fields, _perms, body = sp.parse_frontmatter(text)
                norm = " ".join(body.split())
                for snippet in ep.PROFILE_BODY_SNIPPETS[name]:
                    self.assertIn(
                        " ".join(snippet.split()),
                        norm,
                        "RED: body of %s must contain the approved snippet: %r" % (name, snippet[:80]),
                    )


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

    def test_config_opencode_json_is_byte_identical_to_the_approved_minimal(self):
        # A2-R: config/opencode.json is UNCHANGED - strictly the 3 fields, exact bytes.
        path = sp.REPO_ROOT / "config" / "opencode.json"
        if not path.is_file():
            self.fail("RED: config/opencode.json is missing")
        self.assertEqual(
            ep.EXPECTED_OPENCODE_JSON_TEXT,
            path.read_text(encoding="utf-8"),
            "RED: config/opencode.json must stay byte-identical (frozen sha256 %s); only the 3 "
            "fields $schema/default_agent/model" % ep.FROZEN_SHA256["opencode.json"],
        )


class MultiAgentsGuideTest(unittest.TestCase):
    """A2-R: English MULTI-AGENTS.md guide at the repo ROOT, never installed."""

    # Forbidden in the guide: personal paths (built by concatenation so this
    # source file itself stays free of the scanned home-path literal), the
    # legacy profile id, machine-private files, machine snapshots/backups and
    # machine build customizations.
    FORBIDDEN_TOKENS = (
        "Concepteur",
        "/" + "home/" + "steph",
        "service" + chr(46) + "json",
        "build_big",
        "opencode" + chr(46) + "json.gpt",
        "backup-multi-agents",
    )
    ALL_COMMAND_TOKENS = tuple("/" + c for c in sp.COMMAND_NAMES)

    def _guide(self):
        path = sp.REPO_ROOT / sp.ROOT_GUIDE_NAME
        if not path.is_file():
            self.fail("RED: %s is missing at the repo root (English guide, A2-R)" % sp.ROOT_GUIDE_NAME)
        return path, path.read_text(encoding="utf-8")

    def test_guide_exists_at_repo_root_and_not_inside_config(self):
        path, _text = self._guide()
        self.assertEqual(sp.REPO_ROOT / sp.ROOT_GUIDE_NAME, path)
        cfg = sp.REPO_ROOT / "config"
        inside = [p for p in cfg.rglob(sp.ROOT_GUIDE_NAME)] if cfg.is_dir() else []
        self.assertEqual(
            [],
            inside,
            "RED: the guide must live at the repo root only, never inside config/ "
            "(it is not installed by the installer): %s" % inside,
        )

    def test_guide_excludes_personal_and_machine_private_content(self):
        _path, text = self._guide()
        for token in self.FORBIDDEN_TOKENS:
            self.assertNotIn(
                token,
                text,
                "RED: guide must not contain %r (personal path / legacy id / machine-private "
                "file / machine snapshot / machine build customization)" % token,
            )
        self.assertIsNone(
            re.search("/" + "home/[A-Za-z0-9._-]+", text),
            "RED: guide must not contain any personal home path",
        )

    def test_guide_documents_the_eight_commands_and_both_entry_paths(self):
        _path, text = self._guide()
        low = text.lower()
        for token in self.ALL_COMMAND_TOKENS:
            self.assertIn(token, text, "RED: guide must list command %s (8 commands)" % token)
        for token in ("standalone", "post-cycle"):
            self.assertIn(token, low, "RED: guide must describe the %s entry path" % token)
        for name in sp.AGENT_NAMES:
            self.assertIn(name, text, "RED: guide model table must list profile %s" % name)
        self.assertIn("Architect", text, "RED: guide must use Architect (not the legacy id)")
        for model in sorted(set(sp.EXPECTED_MODELS.values())):
            self.assertIn(model, text, "RED: guide model table must pin %s" % model)
        # Model priority: command > agent > session.
        self.assertRegex(
            text,
            re.compile(r"command.{0,300}agent.{0,300}session", re.I | re.S),
            "RED: guide must state the model priority command > agent > session",
        )
        # Warning: /review overrides the native command of the same name.
        self.assertRegex(
            text,
            re.compile(r"overrid\w*|overload\w*|shadow\w*", re.I),
            "RED: guide must warn that /review overrides the native command",
        )
        self.assertIn("native", low, "RED: guide must mention the native command being overridden")
        # Operator verification refers to INSTALL.
        self.assertIn("INSTALL.md", text, "RED: guide must point operator verification to INSTALL.md")


class DocsAndScriptsContractTest(unittest.TestCase):
    def test_readme_documents_the_install_command(self):
        path = sp.REPO_ROOT / "README.md"
        if not path.is_file():
            self.fail("RED: README.md is missing")
        text = path.read_text(encoding="utf-8")
        self.assertIn("python3 scripts/install.py", text, "README must document the CLI install command")

    def test_readme_and_install_describe_8_commands_two_paths_and_exclusions(self):
        # A2-R: both docs must document the 8 commands (5 /em* + review/doc/security),
        # the two entry paths (standalone vs post-cycle), the /review native-command
        # override warning, the link to MULTI-AGENTS.md and the local exclusions; the
        # old "optional specialists only after the mandatory cycle" claim must go.
        docs = {}
        for doc in ("README.md", "INSTALL.md"):
            path = sp.REPO_ROOT / doc
            if not path.is_file():
                self.fail("RED: %s is missing" % doc)
            docs[doc] = path.read_text(encoding="utf-8")
        all_commands = tuple("/" + c for c in sp.COMMAND_NAMES)
        for doc, text in docs.items():
            with self.subTest(doc=doc):
                norm = " ".join(text.split())
                for token in all_commands:
                    self.assertIn(token, text, "RED: %s must mention command %s (8 commands)" % (doc, token))
                low = norm.lower()
                for token in ("standalone", "post-cycle"):
                    self.assertIn(token, low, "RED: %s must describe the %s path" % (doc, token))
                self.assertRegex(
                    norm,
                    re.compile(r"overrid\w*|overload\w*|shadow\w*", re.I),
                    "RED: %s must warn that /review overrides the native command" % doc,
                )
                self.assertIn("native", low, "RED: %s must mention the native /review command" % doc)
                self.assertIn(
                    sp.ROOT_GUIDE_NAME, text,
                    "RED: %s must link the %s guide" % (doc, sp.ROOT_GUIDE_NAME),
                )
                self.assertIsNone(
                    re.search(r"five[^.\n]{0,40}commands?\b", norm, re.I),
                    "RED: %s must not claim five commands anymore (A2-R: eight)" % doc,
                )
                self.assertIsNone(
                    re.search(
                        r"(optional|specialist|Reviewer|Documentalist|SecurityOfficer)"
                        r"[^.\n]{0,160}only[^.\n]{0,80}after the mandatory cycle",
                        norm,
                        re.I,
                    ),
                    "RED: %s must drop the 'optional specialists only after the mandatory cycle' "
                    "claim (A2-R: the standalone path exists)" % doc,
                )
                # Local exclusions documented: legacy profile id, private machine
                # files, build/plan customizations left local.
                self.assertIn("Concepteur", text, "RED: %s must document the legacy Concepteur exclusion" % doc)
                self.assertRegex(
                    text,
                    re.compile(r"credential|service" + chr(46) + r"json|auth" + chr(46) + r"json", re.I),
                    "RED: %s must document private machine files as excluded/local" % doc,
                )
                self.assertRegex(
                    text,
                    re.compile(r"build\s*/?\s*plan", re.I),
                    "RED: %s must document build/plan customizations as left local" % doc,
                )

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
