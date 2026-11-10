---
description: Ask EM to delegate immediately to Documentalist without checking completion of the mandatory cycle.
agent: EngineeringManager
subagent: false
---

I explicitly request standalone documentation work by Documentalist through
EngineeringManager, within the scope below if specified, otherwise using the
current session's clearly established scope.

Delegate immediately to Documentalist with the supplied scope, relevant available
context, reference version and response_language. Identify this handoff as
optional_agent_path: standalone. Do not require, reconstruct or verify completion
of the mandatory cycle. Do not launch Explorer, Architect, Tester, Developer or
any other agent; launch only Documentalist.

Have modules and functions in scope documented, including complex sections,
without paraphrasing code. Only documentation, comments and docstrings with no
functional effect may be changed. No functional code change is authorized by this
request. Summarize the report, documentation changes, verification and
limitations. Proposed functional corrections must return to EM's mandatory
workflow; do not initiate that workflow or apply functional fixes automatically.

If the target scope or human language is genuinely unclear, ask only the minimum
clarification needed; do not turn clarification into a workflow-history check.
If delegation is unavailable, report the blocker rather than replacing Documentalist.

Language: the language of the user arguments takes priority over this English
wrapper, unless the human explicitly requests another response language. Derive
and transmit `response_language` accordingly. With no arguments, keep the known
human preference or ask; do not default to English because of this template.
Documentation itself follows the target project's language and conventions.

BEGIN USER ARGUMENTS (scope and details)
$ARGUMENTS
END USER ARGUMENTS
