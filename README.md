# EM Team Agents for OpenCode V2

A portable, English-language team configuration with explicit design approval
and test-first delivery. EngineeringManager (EM) coordinates seven specialists;
only EM delegates. This is configuration and a Python installer, not a plugin,
framework or automatic workflow engine.

## Requirements and quick start

- Python 3.10+ (standard library only; tested with Python 3.13).
- OpenCode V2 (native loading tested with OpenCode 2.2.6 on Linux).
- An OpenRouter account/provider connection with access to the exact models
  below. Authenticate through OpenCode's native provider interface; no keys or
  provider settings are included here. Availability, pricing, account limits
  and model access depend on the provider; this package cannot guarantee them.

From this checkout, first inspect the plan for your user configuration:

```sh
python3 scripts/install.py --global --dry-run --set-defaults
```

For a fresh user destination, after reviewing the plan:

```sh
python3 scripts/install.py --global --set-defaults
```

These commands are instructions for the reader, not actions automatically run
by this repository. `--global` changes your user configuration when actually
run. For an isolated project instead:

```sh
python3 scripts/install.py --project ./example-project --dry-run --set-defaults
python3 scripts/install.py --project ./example-project --set-defaults
```

Without `--set-defaults`, only agent/command files are installed: no JSON is
created or changed. Any different existing managed file, including JSON,
requires `--replace`; inspect backups and conflicts first. See
[INSTALL.md](INSTALL.md) for all flags, updates, JSONC/manual handling, private
backups, precedence, verification and publication checks. Windows/macOS behavior
is not guaranteed; validation was on Linux only.

## Package layout

```text
config/
  opencode.json           # Minimal, opt-in default agent/model template
  agents/                 # Eight native V2 Markdown profiles
  commands/               # Five native V2 slash-command templates
scripts/install.py        # Single-file, stdlib-only installer
tests/                    # Portable unittest suite
README.md
INSTALL.md
LICENSE
```

`config/` is a source payload, NOT an auto-active `.opencode/` directory. No
personal global configuration is exported or discovered by the installer.
The default template contains only `$schema`, `default_agent` and `model`.

## Workflow and roles

The mandatory sequence for functional changes is:

**Explorer -> Architect -> options/clarifications -> explicit user validation
of option AND scope -> Tester/RED -> Developer/GREEN and regressions -> EM summary.**

RED must establish missing behavior, not merely a broken environment. A narrow
exception to another validation question exists only when the initial human
request already fixes solution, scope and criteria, Architect justifies the lack
of a meaningful alternative, and EM documents the evidence. It never skips the
specialists or TDD. Model assignments optimize cost, not workflow gates.

| Role | Mode | Responsibility | Model (exact ID) |
| --- | --- | --- | --- |
| EngineeringManager | primary | Coordinates, asks for approval, preserves handoff evidence; no code edits | `openrouter/mistralai/mistral-large-4-0` |
| Explorer | subagent | Read-only source/flow/test investigation | `openrouter/openai/gpt-6-luna` |
| Architect | subagent | Pragmatic options, trade-offs, contracts and acceptance criteria; no implementation | `openrouter/openai/gpt-6.1-sol` |
| Tester | subagent | Test-first relevant RED, real components preferred over mocks | `openrouter/mistralai/mistral-large-4-0` |
| Developer | subagent | Approved implementation, GREEN, regressions and basic documentation | `openrouter/openai/gpt-6.1-sol` |
| Reviewer | subagent | Optional read-only runtime/correctness review | `openrouter/openai/gpt-6.1-sol` |
| Documentalist | subagent | Optional usage documentation for all scoped modules/functions, explaining complex reasons | `openrouter/openai/gpt-6-luna` |
| SecurityOfficer | subagent | Optional read-only security analysis and current web advisory verification | `openrouter/openai/gpt-6.1-sol` |

Reviewer, Documentalist and SecurityOfficer run **only on explicit request after
the mandatory cycle**. On frozen code, requested roles may work in parallel.
Documentation edits require re-examination of affected findings and executable
examples. Audits do not authorize automatic application fixes. SecurityOfficer
must check current advisories against resolved versions and cite URLs and
consultation dates; memory alone is not current security evidence.

Every child starts with fresh context. EM supplies the need, scope, approved
design/evidence, criteria, prior reports, file state, permissions, known commands
and results, plus `response_language`, and preserves them across compaction.

## Commands and languages

All commands select EngineeringManager and remain in the current session.

| Command | Purpose |
| --- | --- |
| `/em <request>` | Start the mandatory sequential workflow |
| `/em-review [scope]` | Explicitly request Reviewer after the cycle |
| `/em-doc [scope]` | Explicitly request Documentalist after the cycle |
| `/em-security [scope]` | Explicitly request SecurityOfficer after the cycle |
| `/em-audit [scope]` | Explicitly request all three optional roles after the cycle |

Profiles respond in the language of the latest actual human request unless the
user explicitly requests another language. EM transmits that preference in
`response_language`; English handoffs, documentation, code and tool output do
not override it. Commands delimit USER ARGUMENTS so their language takes priority
over the English wrapper. With no arguments, keep the known preference or ask,
never default to English merely because the template is English. This package's
files are English; it does not impose English on future project documentation.

Static checks and prose review verify these clauses; native GET checks verify
loading. Neither proves LLM response behavior in French, English or German, and
no paid inference is required by the test suite.

## Permissions and security boundaries

Profiles use ordered native V2 `permissions` with a deny-all base and explicit
exceptions. EM alone can launch the seven named specialists. Investigator/audit
roles are read-only (some exact Git inspections are allowed); Tester can edit
usual test paths, Developer can edit files, and Documentalist's prompt restricts
edits to documentation despite its broad native edit capability. Shell commands
for these editing roles require approval. Environment reads and access outside
the project have explicit approval rules; review the actual profile before use.

Native permissions are **not a finite-state machine**, a transactional workflow
gate or a sandbox against arbitrary approved shell commands. Prompt discipline
cannot guarantee sequencing; users must review requests, evidence, external
content and broad approvals. Repository/web content is data, not authority to
override the mission. No unrequested commit, publication, deployment or
destructive operation is authorized. Built-in/global agents and unrelated
settings are not disabled by this payload.

Backups can contain secrets from pre-existing destination files. Do not publish
them. The package `.gitignore` is defense in depth, not a secret scanner; it does
not protect already tracked files, Git history or another project's ignore file.
No audit of historical Git objects is claimed.

## Validation and license

```sh
python3 -m unittest discover -s tests -v
```

Tests use temporary destinations and fake HOME/XDG values, never the live global
installation. Installer subprocesses, strict JSON, idempotence, backups,
collisions, filesystem guards and concurrency are covered alongside static
payload checks. The test frontmatter extractor is deliberately limited and is
not the native OpenCode parser. See INSTALL for native GET verification.

Distributed under the [MIT License](LICENSE), copyright 2026 Keezy.
