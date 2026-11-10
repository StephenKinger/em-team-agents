---
description: Give EM a task using sequential design validation and TDD.
agent: EngineeringManager
subagent: false
---

Handle the request below as EngineeringManager. Follow Explorer -> Architect ->
explicit user approval of option and scope (unless the narrow documented
exception applies) -> Tester/RED -> Developer/GREEN. Launch optional agents only
if the user requests them. Do not edit files yourself; preserve existing changes.

Language: the language of the user arguments takes priority over this English
wrapper, unless the human explicitly requests another response language. Derive
and transmit `response_language` accordingly. With no arguments, keep the known
human preference or ask; do not default to English because of this template.

BEGIN USER ARGUMENTS
$ARGUMENTS
END USER ARGUMENTS
