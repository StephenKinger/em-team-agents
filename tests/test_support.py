"""Unit tests for the test-support helpers themselves (frontmatter extractor
and secret-hygiene scanner).

All fixtures are fake and built at runtime by concatenation, so this source
file contains no scannable secret-like literal and no real credentials.
"""

from __future__ import annotations

import hashlib
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import support_pkg as sp
import expected_payload as ep

VALID_FRONTMATTER = (
    "---\n"
    'description: "Example agent"\n'
    "mode: subagent\n"
    "model: openrouter/openai/gpt-6.1-sol\n"
    'color: "#7c3aed"\n'
    "permissions:\n"
    '  - { action: "*", resource: "*", effect: deny }\n'
    '  - { action: read, resource: "*", effect: allow }\n'
    "subagent: false\n"
    "---\n"
    "Body text.\n"
)


class ParseFrontmatterTest(unittest.TestCase):
    def test_parses_fields_permissions_order_and_body(self):
        fields, perms, body = sp.parse_frontmatter(VALID_FRONTMATTER)
        self.assertEqual("Example agent", fields["description"])
        self.assertEqual("subagent", fields["mode"])
        self.assertEqual("openrouter/openai/gpt-6.1-sol", fields["model"])
        self.assertEqual("#7c3aed", fields["color"])
        self.assertEqual("false", fields["subagent"])
        self.assertEqual(
            [("*", "*", "deny"), ("read", "*", "allow")],
            perms,
            "permission order must be preserved",
        )
        self.assertEqual("Body text.", body)

    def test_flow_item_values_are_stripped(self):
        text = VALID_FRONTMATTER.replace("effect: allow }", "effect: allow   }")
        _fields, perms, _body = sp.parse_frontmatter(text)
        self.assertEqual(("read", "*", "allow"), perms[1], "unquoted effect must be stripped")

    def test_duplicate_scalar_field_raises(self):
        with self.assertRaises(ValueError):
            sp.parse_frontmatter(VALID_FRONTMATTER.replace("mode: subagent", "mode: subagent\nmode: primary"))

    def test_missing_fences_raise(self):
        with self.assertRaises(ValueError):
            sp.parse_frontmatter("no frontmatter here\n")
        with self.assertRaises(ValueError):
            sp.parse_frontmatter("---\nmode: subagent\n")

    def test_unparseable_permission_item_raises(self):
        broken = VALID_FRONTMATTER.replace(
            '- { action: "*", resource: "*", effect: deny }', "- not-a-flow-item"
        )
        self.assertNotEqual(VALID_FRONTMATTER, broken, "fixture replacement must apply")
        with self.assertRaises(ValueError):
            sp.parse_frontmatter(broken)


class ScannerTest(unittest.TestCase):
    def test_prose_mentions_of_config_file_names_are_not_secrets(self):
        # Docs/.gitignore MAY name service/auth/credentials files; only a real
        # forbidden filename or a real secret shape is a finding.
        prose = (
            "The installer never reads "
            + "service" + chr(46) + "json, "
            + "auth" + chr(46) + "json or any credentials file."
        )
        self.assertEqual([], sp.scan_text(prose))

    def test_real_secret_shapes_detected_by_category_only(self):
        fake_openrouter_key = "sk-or-" + "abcdefgh1234"
        self.assertIn("openrouter-key", sp.scan_text(fake_openrouter_key))
        fake_pem = "-----" + "BEGIN " + "RSA PRIVATE KEY" + "-----"
        self.assertIn("private-key-block", sp.scan_text(fake_pem))
        fake_assignment = "api" + "_key = " + chr(34) + "abcdef" + chr(34)
        self.assertIn("api-key-assignment", sp.scan_text(fake_assignment))

    def test_home_path_shape_detected_without_literal_in_source(self):
        fake_home = "/" + "home/" + "someuser"
        self.assertIn("home-path", sp.scan_text(fake_home))

    def test_benign_english_text_has_no_findings(self):
        self.assertEqual([], sp.scan_text("Just an English sentence about installation."))


class FrozenPayloadTest(unittest.TestCase):
    """Self-consistency of the frozen A2-R expectations (tests/expected_payload.py)."""

    def test_frozen_module_shape(self):
        self.assertEqual(("review", "doc", "security"), ep.STANDALONE_COMMAND_NAMES)
        self.assertEqual(4, len(ep.MODIFIED_PROFILE_NAMES))
        self.assertEqual(sorted(ep.STANDALONE_COMMAND_NAMES), sorted(ep.EXPECTED_COMMAND_TEXT))
        self.assertEqual(sorted(ep.MODIFIED_PROFILE_NAMES), sorted(ep.EXPECTED_PROFILE_FRONTMATTER))
        self.assertEqual(sorted(ep.MODIFIED_PROFILE_NAMES), sorted(ep.PROFILE_BODY_SNIPPETS))
        for name, text in ep.EXPECTED_COMMAND_TEXT.items():
            fields, _perms, body = sp.parse_frontmatter(text)
            self.assertEqual("EngineeringManager", fields["agent"])
            self.assertEqual("false", fields["subagent"])
            self.assertNotIn("model", fields)
            self.assertIn("$ARGUMENTS", body)
        for name, block in ep.EXPECTED_PROFILE_FRONTMATTER.items():
            fields, perms, _body = sp.parse_frontmatter(block + "\nbody\n")
            self.assertEqual(sp.EXPECTED_MODELS[name], fields["model"])
            self.assertTrue(perms)
            self.assertEqual(ep.FROZEN_SHA256["agents/%s.md#frontmatter" % name],
                             hashlib.sha256(block.encode("utf-8")).hexdigest())
        cfg = json.loads(ep.EXPECTED_OPENCODE_JSON_TEXT)
        self.assertEqual({"$schema", "default_agent", "model"}, set(cfg))
        self.assertEqual(len(ep.FROZEN_SHA256), 3 + 4 + 1)

    def test_frozen_sources_contain_no_secret_or_home_path(self):
        blob = repr(ep.EXPECTED_COMMAND_TEXT) + repr(ep.EXPECTED_PROFILE_FRONTMATTER) + ep.EXPECTED_OPENCODE_JSON_TEXT
        self.assertEqual([], sp.scan_text(blob))


if __name__ == "__main__":
    unittest.main()
