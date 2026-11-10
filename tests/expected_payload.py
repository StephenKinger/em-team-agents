"""Frozen expected payload texts for revision A2-R (RED contract).

Captured ONCE from the approved sources at design time: the three standalone
command wrappers, the current frontmatter blocks of the four modified profiles,
the required body snippets of those profiles and the minimal opencode.json.
No test reads the user global opencode configuration at run time; this module
is frozen in hard and is the single source of truth for the expected bytes.
"""

STANDALONE_COMMAND_NAMES = ("review", "doc", "security")
MODIFIED_PROFILE_NAMES = (
    "EngineeringManager",
    "Reviewer",
    "Documentalist",
    "SecurityOfficer",
)

# Full expected text of each new standalone command wrapper.
EXPECTED_COMMAND_TEXT = {
    "review": "---\ndescription: Ask EM to delegate immediately to Reviewer without checking completion of the mandatory cycle.\nagent: EngineeringManager\nsubagent: false\n---\n\nI explicitly request a standalone Reviewer review through EngineeringManager,\nwithin the scope below if specified, otherwise using the current session's\nclearly established scope.\n\nDelegate immediately to Reviewer with the supplied scope, relevant available\ncontext, reference version and response_language. Identify this handoff as\noptional_agent_path: standalone. Do not require, reconstruct or verify completion\nof the mandatory cycle. Do not launch Explorer, Architect, Tester, Developer or\nany other agent; launch only Reviewer.\n\nReviewer is read-only. No functional code change is authorized by this request.\nSummarize the report, evidence, coverage and limitations. Proposed functional\ncorrections must return to EM's mandatory workflow; do not initiate that workflow\nor apply fixes automatically.\n\nIf the target scope or human language is genuinely unclear, ask only the minimum\nclarification needed; do not turn clarification into a workflow-history check.\nIf delegation is unavailable, report the blocker rather than replacing Reviewer.\n\nLanguage: the language of the user arguments takes priority over this English\nwrapper, unless the human explicitly requests another response language. Derive\nand transmit `response_language` accordingly. With no arguments, keep the known\nhuman preference or ask; do not default to English because of this template.\n\nBEGIN USER ARGUMENTS (scope and details)\n$ARGUMENTS\nEND USER ARGUMENTS\n",
    "doc": "---\ndescription: Ask EM to delegate immediately to Documentalist without checking completion of the mandatory cycle.\nagent: EngineeringManager\nsubagent: false\n---\n\nI explicitly request standalone documentation work by Documentalist through\nEngineeringManager, within the scope below if specified, otherwise using the\ncurrent session's clearly established scope.\n\nDelegate immediately to Documentalist with the supplied scope, relevant available\ncontext, reference version and response_language. Identify this handoff as\noptional_agent_path: standalone. Do not require, reconstruct or verify completion\nof the mandatory cycle. Do not launch Explorer, Architect, Tester, Developer or\nany other agent; launch only Documentalist.\n\nHave modules and functions in scope documented, including complex sections,\nwithout paraphrasing code. Only documentation, comments and docstrings with no\nfunctional effect may be changed. No functional code change is authorized by this\nrequest. Summarize the report, documentation changes, verification and\nlimitations. Proposed functional corrections must return to EM's mandatory\nworkflow; do not initiate that workflow or apply functional fixes automatically.\n\nIf the target scope or human language is genuinely unclear, ask only the minimum\nclarification needed; do not turn clarification into a workflow-history check.\nIf delegation is unavailable, report the blocker rather than replacing Documentalist.\n\nLanguage: the language of the user arguments takes priority over this English\nwrapper, unless the human explicitly requests another response language. Derive\nand transmit `response_language` accordingly. With no arguments, keep the known\nhuman preference or ask; do not default to English because of this template.\nDocumentation itself follows the target project's language and conventions.\n\nBEGIN USER ARGUMENTS (scope and details)\n$ARGUMENTS\nEND USER ARGUMENTS\n",
    "security": "---\ndescription: Ask EM to delegate immediately to SecurityOfficer without checking completion of the mandatory cycle.\nagent: EngineeringManager\nsubagent: false\n---\n\nI explicitly request a standalone SecurityOfficer audit through EngineeringManager,\nwithin the scope below if specified, otherwise using the current session's\nclearly established scope.\n\nDelegate immediately to SecurityOfficer with the supplied scope, relevant available\ncontext, reference version and response_language. Identify this handoff as\noptional_agent_path: standalone. Do not require, reconstruct or verify completion\nof the mandatory cycle. Do not launch Explorer, Architect, Tester, Developer or\nany other agent; launch only SecurityOfficer.\n\nHave attack surfaces analyzed and current advisories checked against actual\nresolved versions. SecurityOfficer is read-only: no automatic fixes, dependency\nupdates or active exploitation. No functional code change is authorized by this\nrequest. Summarize sourced findings, coverage, limitations and proposed\ncorrections. Proposed functional corrections must return to EM's mandatory\nworkflow; do not initiate that workflow or apply fixes automatically.\n\nIf the target scope or human language is genuinely unclear, ask only the minimum\nclarification needed; do not turn clarification into a workflow-history check.\nIf delegation is unavailable, report the blocker rather than replacing SecurityOfficer.\n\nLanguage: the language of the user arguments takes priority over this English\nwrapper, unless the human explicitly requests another response language. Derive\nand transmit `response_language` accordingly. With no arguments, keep the known\nhuman preference or ask; do not default to English because of this template.\n\nBEGIN USER ARGUMENTS (scope and details)\n$ARGUMENTS\nEND USER ARGUMENTS\n",
}

# Exact frontmatter block (opening fence through closing fence, inclusive) that
# the four modified profiles must keep byte-identical (model/permissions unchanged).
EXPECTED_PROFILE_FRONTMATTER = {
    "EngineeringManager": '---\ndescription: EM orchestrates Explorer, Architect, user validation, Tester then Developer; optional audits on request.\nmode: primary\nmodel: openrouter/mistralai/mistral-large-4-0\ncolor: "#2563eb"\npermissions:\n  - { action: "*", resource: "*", effect: deny }\n  - { action: read, resource: "*", effect: allow }\n  - { action: read, resource: "*.env", effect: ask }\n  - { action: read, resource: "*.env.*", effect: ask }\n  - { action: read, resource: "*.env.example", effect: allow }\n  - { action: glob, resource: "*", effect: allow }\n  - { action: grep, resource: "*", effect: allow }\n  - { action: external_directory, resource: "*", effect: ask }\n  - { action: question, resource: "*", effect: allow }\n  - { action: skill, resource: "*", effect: allow }\n  - { action: webfetch, resource: "*", effect: allow }\n  - { action: websearch, resource: "*", effect: allow }\n  - { action: subagent, resource: Explorer, effect: allow }\n  - { action: subagent, resource: Architect, effect: allow }\n  - { action: subagent, resource: Tester, effect: allow }\n  - { action: subagent, resource: Developer, effect: allow }\n  - { action: subagent, resource: Reviewer, effect: allow }\n  - { action: subagent, resource: Documentalist, effect: allow }\n  - { action: subagent, resource: SecurityOfficer, effect: allow }\n---\n',
    "Reviewer": '---\ndescription: Optional read-only review of bugs, regressions, conventions and problematic runtime flows.\nmode: subagent\nmodel: openrouter/openai/gpt-6.1-sol\ncolor: "#db2777"\npermissions:\n  - { action: "*", resource: "*", effect: deny }\n  - { action: read, resource: "*", effect: allow }\n  - { action: read, resource: "*.env", effect: ask }\n  - { action: read, resource: "*.env.*", effect: ask }\n  - { action: read, resource: "*.env.example", effect: allow }\n  - { action: glob, resource: "*", effect: allow }\n  - { action: grep, resource: "*", effect: allow }\n  - { action: external_directory, resource: "*", effect: ask }\n  - { action: skill, resource: "*", effect: allow }\n  - { action: webfetch, resource: "*", effect: allow }\n  - { action: websearch, resource: "*", effect: allow }\n  - { action: shell, resource: "git status --short", effect: allow }\n  - { action: shell, resource: "git diff", effect: allow }\n  - { action: shell, resource: "git diff --cached", effect: allow }\n  - { action: shell, resource: "git diff --stat", effect: allow }\n  - { action: shell, resource: "git diff --name-only", effect: allow }\n  - { action: shell, resource: "git diff --check", effect: allow }\n  - { action: shell, resource: "' + "git ls-" + "files" + '", effect: allow }\n---\n',
    "Documentalist": '---\ndescription: Optional module/function usage documentation; explains complex sections without paraphrasing code.\nmode: subagent\nmodel: openrouter/openai/gpt-6-luna\ncolor: "#0d9488"\npermissions:\n  - { action: "*", resource: "*", effect: deny }\n  - { action: read, resource: "*", effect: allow }\n  - { action: read, resource: "*.env", effect: ask }\n  - { action: read, resource: "*.env.*", effect: ask }\n  - { action: read, resource: "*.env.example", effect: allow }\n  - { action: glob, resource: "*", effect: allow }\n  - { action: grep, resource: "*", effect: allow }\n  - { action: external_directory, resource: "*", effect: ask }\n  - { action: skill, resource: "*", effect: allow }\n  - { action: webfetch, resource: "*", effect: allow }\n  - { action: websearch, resource: "*", effect: allow }\n  - { action: edit, resource: "*", effect: allow }\n  - { action: shell, resource: "*", effect: ask }\n---\n',
    "SecurityOfficer": '---\ndescription: Optional read-only security audit; analyzes exposed surfaces and verifies CVEs against current sources.\nmode: subagent\nmodel: openrouter/openai/gpt-6.1-sol\ncolor: "#dc2626"\npermissions:\n  - { action: "*", resource: "*", effect: deny }\n  - { action: read, resource: "*", effect: allow }\n  - { action: read, resource: "*.env", effect: ask }\n  - { action: read, resource: "*.env.*", effect: ask }\n  - { action: read, resource: "*.env.example", effect: allow }\n  - { action: glob, resource: "*", effect: allow }\n  - { action: grep, resource: "*", effect: allow }\n  - { action: external_directory, resource: "*", effect: ask }\n  - { action: skill, resource: "*", effect: allow }\n  - { action: webfetch, resource: "*", effect: allow }\n  - { action: websearch, resource: "*", effect: allow }\n  - { action: shell, resource: "git status --short", effect: allow }\n  - { action: shell, resource: "git diff", effect: allow }\n  - { action: shell, resource: "git diff --cached", effect: allow }\n  - { action: shell, resource: "git diff --stat", effect: allow }\n  - { action: shell, resource: "git diff --name-only", effect: allow }\n  - { action: shell, resource: "' + "git ls-" + "files" + '", effect: allow }\n---\n',
}

# Required snippets in the NEW body of each modified profile (two entry paths).
PROFILE_BODY_SNIPPETS = {
    "EngineeringManager": [
        '# Optional agents: only on explicit request, with two entry paths',
        '## Standalone commands through EM',
        '/review, /doc and /security are explicit requests to delegate immediately to Reviewer, Documentalist and SecurityOfficer respectively. Do not require, reconstruct or verify completion of the mandatory cycle for these commands.',
        'optional_agent_path: standalone',
        '## Existing post-cycle commands',
        '/em-review, /em-doc, /em-security and /em-audit retain their existing prerequisites: verify that the mandatory cycle completed before launching the requested roles.',
        'optional_agent_path: post-cycle',
        'Never treat a standalone report as proof that the mandatory cycle occurred.',
    ],
    "Reviewer": [
        'Completion of the mandatory cycle is not a prerequisite for your review; EM enforces any prerequisite of the selected entry command.',
        'EM may identify the handoff as optional_agent_path: standalone or post-cycle.',
        'Do not request cycle-completion evidence.',
        'When invoked through /review, /doc or /security, no autonomous functional code change is authorized.',
    ],
    "Documentalist": [
        'Completion of the mandatory cycle is not a prerequisite for your documentation work; EM enforces any prerequisite of the selected entry command.',
        'EM may identify the handoff as optional_agent_path: standalone or post-cycle.',
        'Do not request cycle-completion evidence.',
        'When invoked through /review, /doc or /security, no autonomous functional code change is authorized.',
    ],
    "SecurityOfficer": [
        'Completion of the mandatory cycle is not a prerequisite for your audit; EM enforces any prerequisite of the selected entry command.',
        'EM may identify the handoff as optional_agent_path: standalone or post-cycle.',
        'Do not request cycle-completion evidence.',
        'When invoked through /review, /doc or /security, no autonomous functional code change is authorized.',
    ],
}

# Exact expected bytes of the minimal config/opencode.json (must stay unchanged).
EXPECTED_OPENCODE_JSON_TEXT = '{\n  "$schema": "https://opencode.ai/config.json",\n  "default_agent": "EngineeringManager",\n  "model": "openrouter/mistralai/mistral-large-4-0"\n}\n'

# Frozen fingerprints for the RED report (sha256 of the frozen texts).
FROZEN_SHA256 = {
    "commands/review.md": "dfd699f1d64570abe62f55538ddcdbd5af0e71b0c9eb791376c8a0426fe7f64b",
    "commands/doc.md": "ff8baf45727a33b60e69bcd0df608ea158d156aae26179fa38c591372b7edeaf",
    "commands/security.md": "c6a63fcc45c4d7473b2af2ac7962595c840b18d9670b9501e6bf19ec6d8cde3d",
    "agents/EngineeringManager.md#frontmatter": "9cd908eab066e5448ec462a6f088d8ed22d9276de771fbb0ee3a9c6d56601b35",
    "agents/Reviewer.md#frontmatter": "8e70bf901613add08013a20c2ba4ca0eca16292f7232d27816d10bd164b8602b",
    "agents/Documentalist.md#frontmatter": "8e3cdce92f17726efc3a01f03c91ee79d24c6ee4bfd38956a8886adc4bf34332",
    "agents/SecurityOfficer.md#frontmatter": "ca537d0ceaa3445500442cec2f97fed87d5222329645e66ceb3094fabfc5b7cb",
    "opencode.json": "0936ab15f148aabba2006f9d3e1b6d7716a142f28ccc862c1b8a2fb909e65594",
}
