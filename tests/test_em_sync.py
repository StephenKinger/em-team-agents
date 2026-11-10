"""Regression checks for the synchronized EM workflow and installed command."""

import re
import shutil
import unittest

import support_pkg as sp


def effect(rules, action, value):
    """Resolve simple V2 wildcard rules in their declared order."""
    result = None
    for rule_action, resource, rule_effect in rules:
        def matches(pattern, text):
            if pattern.endswith(" *") and text == pattern[:-2]:
                return True
            regex = re.escape(pattern).replace(r"\*", ".*").replace(r"\?", ".")
            return re.fullmatch(regex, text) is not None
        if matches(rule_action, action) and matches(resource, value):
            result = rule_effect
    return result


class SynchronizedWorkflowTest(unittest.TestCase):
    def test_agents_keep_package_models_and_new_shell_contract(self):
        for name in sp.AGENT_NAMES:
            with self.subTest(agent=name):
                text = (sp.REPO_ROOT / "config" / "agents" / (name + ".md")).read_text()
                fields, rules, _body = sp.parse_frontmatter(text)
                self.assertEqual(sp.EXPECTED_MODELS[name], fields["model"])
                for command, expected in (
                    ("python -V", "allow"), ("pytest -q", "allow"),
                    ("grep x file", "allow"), ("ls -la", "allow"),
                    ("git status", "allow"), ("git remote -v", "allow"),
                    ("git -C repo status", "ask"), ("git --version", "deny"),
                    ("git push origin main", "deny"),
                    ("git -C repo push origin main", "deny"),
                    ("npm test", "ask"),
                ):
                    self.assertEqual(expected, effect(rules, "shell", command), command)

    def test_em_supports_slices_escalation_verbatim_and_worktrees(self):
        text = " ".join((sp.REPO_ROOT / "config/agents/EngineeringManager.md").read_text().split()).lower()
        for term in ("eight unsuccessful attempts", "verbatim", "session_move", "worktree", "local commits per slice"):
            self.assertIn(term, text)

    def test_tester_and_developer_local_and_remote_boundaries(self):
        for name in ("Tester", "Developer"):
            with self.subTest(agent=name):
                text = (sp.REPO_ROOT / "config" / "agents" / (name + ".md")).read_text()
                _fields, rules, body = sp.parse_frontmatter(text)
                self.assertEqual("allow", effect(rules, "edit", "src/app.py"))
                normalized = " ".join(body.split()).lower()
                for term in ("never run git push", "publish a remote branch", "modify a remote repository", "never bypass git permissions", "curl", "ssh", "local commits and merges"):
                    self.assertIn(term, normalized)

    def test_save_command_is_installed_in_a_fresh_target(self):
        tmp = sp.make_temp("emt-sync-")
        try:
            home = tmp / "home"
            home.mkdir()
            target = tmp / "target"
            result = sp.run_installer(["--target", str(target)], home=home)
            self.assertEqual(0, result.returncode, sp.sanitize(result.stderr))
            command = target / "commands/em-save.md"
            self.assertTrue(command.is_file())
            fields, _, body = sp.parse_frontmatter(command.read_text())
            self.assertEqual("EngineeringManager", fields["agent"])
            self.assertIn("$ARGUMENTS", body)
            self.assertIn(".opencode/em/", body)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
