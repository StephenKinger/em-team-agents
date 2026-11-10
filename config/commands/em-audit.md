---
description: Ask EM for Reviewer, Documentalist and SecurityOfficer in parallel after the mandatory cycle.
agent: EngineeringManager
subagent: false
---

I explicitly request Reviewer, Documentalist and SecurityOfficer for this
session's work, within the scope below if specified. First verify the mandatory
cycle completed; otherwise explain what is missing without launching unrequested
implementation.

Once code is frozen, launch the three roles in parallel with context and a clear
reference version. Only Documentalist may edit documentation; the other audits
are read-only. Afterwards, have findings revalidated for areas changed meanwhile
and executable examples rechecked. Summarize all three reports and limitations;
do not automatically fix detected defects.

Language: the language of the user arguments takes priority over this English
wrapper, unless the human explicitly requests another response language. Derive
and transmit `response_language` accordingly. With no arguments, keep the known
human preference or ask; do not default to English because of this template.

BEGIN USER ARGUMENTS (scope and details)
$ARGUMENTS
END USER ARGUMENTS
