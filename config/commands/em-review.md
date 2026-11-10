---
description: Ask EM for a Reviewer review after the mandatory cycle.
agent: EngineeringManager
subagent: false
---

I explicitly request Reviewer for this session's work, within the scope below
if specified. First verify the mandatory cycle completed; otherwise explain
what is missing without launching unrequested implementation. Give Reviewer
the context and reference version, then summarize findings without spontaneously
fixing code.

Language: the language of the user arguments takes priority over this English
wrapper, unless the human explicitly requests another response language. Derive
and transmit `response_language` accordingly. With no arguments, keep the known
human preference or ask; do not default to English because of this template.

BEGIN USER ARGUMENTS (scope and details)
$ARGUMENTS
END USER ARGUMENTS
