---
description: Ask EM for module/function usage documentation after the mandatory cycle.
agent: EngineeringManager
subagent: false
---

I explicitly request Documentalist for this session's work, within the scope
below if specified. Verify the mandatory cycle completed; otherwise explain
the missing prerequisite without launching unrequested implementation. Have all
modules and functions in scope documented, including complex sections, without
paraphrasing code or changing behavior. Summarize changes and verification.

Language: the language of the user arguments takes priority over this English
wrapper, unless the human explicitly requests another response language. Derive
and transmit `response_language` accordingly. With no arguments, keep the known
human preference or ask; do not default to English because of this template.
Documentation itself follows the target project's language and conventions.

BEGIN USER ARGUMENTS (scope and details)
$ARGUMENTS
END USER ARGUMENTS
