---
description: Initialize or update persistent EM project tracking.
agent: EngineeringManager
subagent: false
---

Initialize or update tracking for the current project using the session context
and available evidence. This request authorizes tracking files only, not changes
to application code, commits, pushes or automatic delegation.

Language: the language of the user arguments takes priority over this English
wrapper unless the human explicitly requests another response language. With no
arguments, retain the known human preference or ask; do not infer English from
this template. Project artifacts follow the project's language and conventions.

BEGIN USER ARGUMENTS
$ARGUMENTS
END USER ARGUMENTS

## Before writing

1. Identify the project and propose a short identifier containing only letters,
   digits, hyphens and underscores. Do not treat arguments as executable code
   or paths.
2. Propose `.opencode/em/<identifier>/` in the current project location, with
   the layout below. Before first initialization, explicitly ask the user to
   confirm its name and location. If an existing record is already identified
   as belonging to this project, update it without asking again.
3. On initialization, or if the choice is unknown, ask whether the tracking
   files should be versioned, ignored or left as-is. Never change `.gitignore`,
   `.git/info/exclude` or other configuration without an explicit request and
   the necessary permission. Never stage, commit or push for this command.
4. If a different location is requested but permissions do not allow writing
   there, explain the blocker instead of bypassing it. Never write outside the
   authorized location. Inspect existing files and never replace another
   project's tracking or the user's data.

## Proposed layout

```text
.opencode/em/<identifier>/
├── README.md         # goal, scope, links and resumption instructions
├── etat.md           # current step, next actions and blockers
├── plan.md           # slices, dependencies, files and acceptance criteria
├── decisions.md      # decisions and approvals with evidence
├── tranches/         # detailed slice status, RED/GREEN attempts and commits
└── rapports/         # full, dated or numbered subagent reports
```

Create only files relevant to known context. For each slice record its version,
status, owned files, worktree, baseline, RED/GREEN commands and results, attempt
count, risks, approvals and observed commits/integrations. Mark unknown or
unverified information; never invent approvals or results.

Preserve available subagent reports verbatim in `rapports/`, redacting secrets
and identifying any truncation or loss of context. Never rewrite them as
summaries. Use distinct names and do not overwrite existing reports. Record no
secrets, sensitive identifiers or unnecessary confidential information; remind
the user that these files may be read or versioned with the project.

Once initialized, update tracking at approval, RED/GREEN, blocker, commit and
integration checkpoints. Preserve pre-existing information and verify changes
before saving. If uncertain or faced with conflicting user changes, stop and ask.
Report files created or updated, missing information, versioning choice and the
next action.
