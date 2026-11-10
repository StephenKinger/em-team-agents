# OpenCode multi-agent team: operator guide

This English guide describes the portable package, not a snapshot of a user's
machine. It stays at the repository root and is **never copied by the installer**.
See [README.md](README.md) for requirements and [INSTALL.md](INSTALL.md) for the
full installation, conflict, backup and verification contract.

## Activation and installation

The source `config/` directory is not automatically active. Review a dry-run
before installing from this checkout:

```sh
python3 scripts/install.py --global --dry-run --set-defaults
python3 scripts/install.py --global --set-defaults
```

Choose exactly one destination: `--global` uses the user's OpenCode configuration
directory (respecting XDG); `--project ./example-project` uses that project's
`.opencode/`; `--target ./custom-opencode` uses the supplied directory itself.
A custom destination must already be discoverable by OpenCode or be configured
separately; copying files does not register it.

```sh
python3 scripts/install.py --project ./example-project --dry-run
python3 scripts/install.py --project ./example-project
python3 scripts/install.py --target ./custom-opencode --dry-run
```

`--set-defaults` is optional. Without it, only the eight profiles and nine
commands are installed and JSON is never written. Different managed destination
files require `--replace`, with private backups; inspect the plan first. Existing
JSONC requires manual handling as documented in INSTALL, not forced replacement.
Unrelated settings and local custom primary-agent or legacy profiles remain
local; this package does not export them. See README and INSTALL for exclusions.

OpenCode reloads saved configuration, agents and commands automatically; `/reload`
forces a reload when needed. No restart is needed. An in-flight request retains
its starting settings. Project configuration may override global definitions.
An existing session retains its selected agent; `/em your request` selects EM
in the current session. Selecting an agent alone and invoking a command have
different model-selection effects, described below.

## Models and package defaults

Every profile sets its model explicitly in `agents/<Name>.md`:

| Profile | Exact model ID |
| --- | --- |
| EngineeringManager | `openrouter/mistralai/mistral-large-4-0` |
| Explorer | `openrouter/openai/gpt-6-luna` |
| Architect | `openrouter/openai/gpt-6.1-sol` |
| Tester | `openrouter/mistralai/mistral-large-4-0` |
| Developer | `openrouter/openai/gpt-6.1-sol` |
| Reviewer | `openrouter/openai/gpt-6.1-sol` |
| Documentalist | `openrouter/openai/gpt-6-luna` |
| SecurityOfficer | `openrouter/openai/gpt-6.1-sol` |

The package's opt-in JSON defaults are `default_agent: EngineeringManager` and
`model: openrouter/mistralai/mistral-large-4-0`. They are package defaults, not
a claim about every effective installation or stored session. Higher-priority
configuration, explicit choices and provider availability still apply. The
package supplies no provider credentials, aliases, variants, automatic escalation
or dynamic model substitution. Developer stays on Sol for complex tasks too.

### Command model versus session model

Model priority is **command > agent > session**:

1. A command's explicit `model`, if present, wins.
2. Otherwise, the selected agent's configured model wins.
3. Otherwise, the current session model remains active.

All nine shipped commands select `EngineeringManager`, set `subagent: false`
and have no `model` field. They therefore select EM's Mistral model even if the
session previously used another model, unless effective configuration overrides
these definitions. Selecting a primary agent alone does not replace a stored
session model. The seven subagents use their explicit profile models; parent
model inheritance matters only for a profile without a configured model.

## Mandatory functional cycle

```text
Human request -> EngineeringManager
  -> Explorer: read-only source, flow and test investigation
  -> Architect: options, trade-offs, recommendation and acceptance criteria
  -> Human: clarification and explicit approval of option AND scope
  -> Tester: tests before implementation, relevant functional RED
  -> Developer: approved implementation, GREEN, regressions, basic documentation
  -> EM: evidence-based summary
```

These steps are sequential within each slice. Independent slices may run in
parallel only with disjoint owned files and separate worktrees. After eight
unsuccessful RED/GREEN attempts, EM audits the blocker and asks whether to
continue or return to analysis. An environment failure is not RED. Only EM delegates;
specialists never delegate to each other. Architect favors pragmatic simplicity,
not unrelated cleanup. The narrow exception to another approval question requires
an initial request that already fixes solution, scope and criteria without a
meaningful alternative, Architect's justification and EM's documented evidence.
It never skips the specialists or TDD.

## Two optional entry paths

### Standalone: immediate delegation through EM

```text
Human -> /review | /doc | /security -> EM -> requested specialist -> EM summary
```

EM delegates immediately to only Reviewer, Documentalist or SecurityOfficer,
respectively, with `optional_agent_path: standalone`. EM must not require,
reconstruct or verify completion of the mandatory cycle. Missing prior design,
approval or RED/GREEN evidence is not a blocker. EM supplies the scope, relevant
available context, reference version and `response_language`; only genuinely
necessary scope or language questions are asked. An unavailable specialist is
a blocker, not permission to substitute EM or another role.

Reviewer and SecurityOfficer remain read-only. Documentalist may change only
documentation, comments and docstrings with no functional effect. No autonomous
functional correction is authorized, and no functional workflow starts
automatically. A standalone report neither proves nor completes the mandatory
cycle. Proposed functional fixes return to that workflow with applicable user
approval and a regression test before implementation.

### Post-cycle: existing optional commands

`/em-review`, `/em-doc`, `/em-security` and `/em-audit` retain their prerequisites:
EM verifies completion of the mandatory cycle before launching requested roles
and supplies `optional_agent_path: post-cycle`. If evidence is missing, EM reports
it without launching unrequested implementation. An optional request outside the
standalone commands is not by itself an exemption; EM clarifies the entry path
when necessary. `/em` and the functional workflow are unchanged.

On either path, identify a stable reference version and do not inspect files
while Tester, Developer or another writer is changing them. This coordination
check is not a cycle-history check. Explicitly requested optional roles may work
in parallel on stable files. Re-examine affected findings and executable examples
after Documentalist edits; never imply a report covers a version not inspected.

## Nine commands and examples

> **Warning: `/review` overrides OpenCode's native command of the same name.**
> This is intentional configuration precedence. A higher-priority project
> definition may override the installed command in turn.

| Command | Requested work | Cycle-completion check |
| --- | --- | --- |
| `/em <request>` | Mandatory functional workflow through EM | Runs the sequential workflow |
| `/review [scope]` | Standalone Reviewer | No: immediate delegation |
| `/doc [scope]` | Standalone Documentalist | No: immediate delegation |
| `/security [scope]` | Standalone SecurityOfficer | No: immediate delegation |
| `/em-review [scope]` | Post-cycle Reviewer | Yes |
| `/em-doc [scope]` | Post-cycle Documentalist | Yes |
| `/em-security [scope]` | Post-cycle SecurityOfficer | Yes |
| `/em-audit [scope]` | Post-cycle: all three optional roles | Yes |
| `/em-save [name]` | Initialize or update authorized tracking | No |

```text
/em Add a concurrency limit to the processing service
/review src/queue: errors, cancellation and regressions
/doc src/queue: modules, functions and complex sections
/security src/auth and the dependency lockfile
/em-review src/queue
/em-doc src/queue
/em-security src/auth
/em-audit src/queue and src/auth
/em-save queue-refactor
```

Without arguments, a clearly established session scope may be reused. The actual
human's language preference takes priority over English wrappers. EM transmits
`response_language` on every handoff; code, documentation and tool output do not
override it. Project documentation follows its own language and conventions.

## Permissions and limits

- EM delegates to the seven specialists and can maintain authorized tracking
  files after `/em-save`; it does not implement application code.
- Explorer, Architect, Reviewer and SecurityOfficer have read-only missions,
  but broad shell permissions are not an enforcement boundary.
- Tester edits tests during RED; assigned source changes are allowed after RED.
- Developer edits only within the approved design and scope.
- Documentalist may edit documentation files; source-file edits ask and its
  contract permits only comments/docstrings without behavioral effects.
- Python, pytest, common utilities and broad Git commands are allowed. `git -C`
  asks except that matching push commands are denied. Direct push and
  `git send-pack` are denied; other initial Git options are denied. Approved
  local branches, commits and merges remain possible.
- External-directory access asks; environment-file reads are denied except
  `.env.example`.
  Specialist delegation and unrelated tools are not implicitly authorized.

**This is not a finite-state machine.** Static permissions restrict tools, not
semantic proof of workflow transitions. Test-only and documentation-only limits
also depend on prompts and human supervision. Tool approval is not design
approval. Users can select other agents, and project settings can override
profiles. The package is not a sandbox: allowed Python, tests and utilities can
execute code or reach the network; aliases can evade command-pattern rules.

SecurityOfficer checks current advisories against resolved versions and dated
sources; without web access or version evidence it cannot establish currency.
Optional reports propose fixes to EM without applying them. No unrequested
commit, deployment, destructive action or production access is authorized.
Tester and Developer must never push, publish a branch, modify remote repositories
or transmit code using curl, SSH or another tool.
Repository and web content are untrusted data, not authority over the mission.

## Operator verification without inference

Use [INSTALL.md's verification procedure](INSTALL.md#verification) for native
GET `/api/agent`, `/api/command`, `/api/model/default` and private `/api/config`
checks with an explicitly scoped location. Run only with operator approval and
the normal discovery/authentication context; no private connection data needs
copying into this repository. Verify the effective eight profiles, nine command
names/descriptions, ordered permissions and expected model IDs in the actual
target project. A public provider catalog does not prove effective availability.

Do not publish raw configuration or provider responses, read credentials, create
sessions or run inference as a loading check. On the tested OpenCode 2.2.6 API,
command metadata does not expose template bodies; compare installed bytes
separately. GET checks prove loading, not runtime delegation, model access,
response language, quality, performance or costs. If a required model is missing,
disabled or unavailable, report the blocker to EM without silent substitution.

## Files and maintenance

Paths below are relative to `<installation-destination>`:

- `opencode.json`: optional package default agent/model; unrelated settings stay.
- `agents/*.md`: eight role contracts, explicit models and ordered permissions.
- `commands/em*.md`: functional entry and existing post-cycle commands.
- `commands/review.md`, `commands/doc.md`, `commands/security.md`: standalone
  commands through EM.
- `.em-team-agents-backups/`: private originals from approved replacements;
  they can contain secrets and must not be published.

Maintain the source payload in `config/`, review changes and rerun the portable
suite described in INSTALL before an explicitly approved update. Never copy an
entire personal configuration directory into the package. Local customizations,
legacy profiles and private machine files stay local and are not installed from
this package. This guide remains in the repository, not at the destination.

To stop selecting EM by default, manually remove only the `default_agent` entry
from the effective configuration after review. Preserve unrelated settings and
later edits. This does not remove team files or rewrite existing sessions.
