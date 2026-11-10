# Installation, updates and verification

## Supported environment

Use Python 3.10+ with its standard library and OpenCode V2. Validation targets
Python 3.13, OpenCode 2.2.6 and Linux. Windows/macOS are not validated or
guaranteed; in particular POSIX backup modes and atomic replacement assumptions
are not cross-platform assurances. No dependencies need installing for this
script or its tests. Configure OpenRouter through OpenCode's native provider
authentication interface and check access, pricing and limits for the exact
model IDs in [README.md](README.md). Never place credentials in the payload.

## CLI contract

Run from this checkout (or invoke the script by its path):

```text
python3 scripts/install.py (--global | --project DIR | --target DIR) [--dry-run] [--set-defaults] [--replace]
```

Exactly one destination selector is required:

| Flag | Destination / behavior |
| --- | --- |
| `--global` | `$XDG_CONFIG_HOME/opencode` if set and nonempty, otherwise `~/.config/opencode` |
| `--project DIR` | `DIR/.opencode`, creating missing directories for a real install |
| `--target DIR` | `DIR` itself, a custom OpenCode configuration directory |
| `--dry-run` | Full read-only preflight; no directories, files, backups or lock created |
| `--set-defaults` | Opt in to creating/updating `model` and `default_agent` in strict JSON |
| `--replace` | Permit replacement of different managed files, with private backups first |

Relative paths are relative to the current working directory. Quote paths with
spaces. `--target` copies files; it does not register that directory with
OpenCode. Choose a directory OpenCode already discovers, or configure discovery
separately using the native [configuration guide](https://opencode.ai/docs/config).
The source `config/` directory is not automatically active.

### Examples to review before executing

```sh
python3 scripts/install.py --help
python3 scripts/install.py --global --dry-run --set-defaults
```

For a fresh destination, an actual user-global install is:

```sh
python3 scripts/install.py --global --set-defaults
```

For a project or custom directory instead:

```sh
python3 scripts/install.py --project "./example project" --dry-run --set-defaults
python3 scripts/install.py --project "./example project" --set-defaults
python3 scripts/install.py --target ./custom-opencode --dry-run
python3 scripts/install.py --target ./custom-opencode
```

The no-defaults variant installs only eight profiles and nine commands; it never
creates or modifies JSON, even with `--replace`. The script uses an explicit
allowlist, not an export of the user's global directory. It never copies
provider configuration, build/plan customization, auth.json, service.json,
credentials, logs or machine-specific backups. Build-prefixed variants and legacy
`Concepteur` profiles also remain local and untouched. The operator guide
[MULTI-AGENTS.md](MULTI-AGENTS.md) stays at the repository root and is never
installed; it is not part of the allowlisted payload.

## Preflight, JSON and conflicts

Preflight reads the complete plan before writes and refuses differing existing
files unless `--replace` is present. Identical files retain bytes and mtime;
reruns are idempotent and do not produce unnecessary backups. Unrelated files
are left alone. Symlinks in source payload paths, destination paths or their
ancestors, wrong file/directory types and known embedded ID collisions are
refused. The target's `opencode.json`, if present, is parsed even without
`--set-defaults`, but never displayed.

- No `--set-defaults`: never write JSON, regardless of `--replace`.
- `--set-defaults`, absent JSON: create the minimal three-key template containing
  `$schema`, `default_agent: EngineeringManager` and the README's Mistral model.
- Existing JSON already has both desired values: leave exact bytes/mtime intact,
  regardless of formatting or unrelated keys. No JSON backup is made.
- Either value is different or missing: `--set-defaults` alone refuses before
  **any** write. Both `--set-defaults --replace` are required. Save a byte-exact
  private backup, then semantically change only these two keys, preserving all
  unrelated JSON values. Do not add `$schema` to existing JSON. Reformatting may
  occur only when such a change is needed. Existing file permission bits,
  including a private configuration mode, are preserved on replacement.

Strict JSON means no comments, trailing commas, duplicate keys (at any depth),
nonstandard constants or non-object root. Invalid content is refused without
printing parser contents or values. An existing `opencode.jsonc` is always
refused, including when both JSON and JSONC exist. There is no homemade JSONC
parser. Embedded `agents` or `commands` entries colliding with the distributed
IDs are refused even with `--replace`; review and resolve them manually first.

### Manual JSONC handling

If using JSONC, do not try to force the installer. Manually copy only the eight
reviewed files from `config/agents/` and nine from `config/commands/` into the
corresponding destination directories. Back up existing files privately before
replacing anything. Merge the two defaults into your JSONC by hand only if
desired, preserving comments, unrelated settings and native permissions. Resolve
duplicate/embedded definitions yourself; do not create a competing JSON file.
Manual copying does not inherit installer locking, preflight or atomic-write
protections. Never copy your entire global directory back into this repository.

## Updating, backups and recovery

Inspect first; replacement is explicit:

```sh
python3 scripts/install.py --project ./example-project --dry-run --set-defaults --replace
python3 scripts/install.py --project ./example-project --set-defaults --replace
```

Before each replacement, the exact original bytes are backed up under:

```text
<destination>/.em-team-agents-backups/<unique-run>/<relative-path>
```

On Linux backup directories are private `0700`, backup files `0600`. Existing
nonprivate backup roots are refused rather than silently reused. Backups may
contain **credentials or other secrets from existing user configuration**. Do
not publish, attach or print their contents. The package `.gitignore` ignores
these backups, but **does not automatically protect a target project's
`.gitignore`**. The installer never changes another project's ignore file. Add
appropriate local protections yourself before staging project files; ignore
rules do not protect already tracked files or Git history.

Restore manually: stop writers, identify the run and relative path, inspect
privately and copy the chosen original back with appropriate permissions. The
installer does not delete unrelated or legacy files, including a previous
`Concepteur.md` profile. The package uses `Architect` only; review old references
and remove/rename a legacy profile yourself if desired, outside this installer.

`<destination>/.em-team-agents.lock` serializes cooperating installers. A busy
or stale lock is refused and preserved, never automatically removed. Confirm no
installer is active before manually resolving a stale lock. A dry-run creates
no lock and cannot reserve a future plan. Normal exit removes only the current
invocation's lock.

Detected changes since preflight stop the install. Checks are best effort
against unrelated editors, not a hostile TOCTOU sandbox. Writes are atomic
**per file**, not a global transaction or automatic rollback. An IO error stops
processing and reports already changed paths and available backup locations,
without contents. Earlier files/directories may remain; use the report and
private backups for recovery. Power loss or forced process termination can
leave a stale lock; atomic writes are not a claim of complete crash durability.

## OpenCode configuration and selection

Native permissions use ordered rules; the last matching rule wins. The payload
preserves each role's mode, color and permission ordering, with EM delegating to
Architect. See [agents](https://opencode.ai/docs/agents),
[permissions](https://opencode.ai/docs/permissions) and
[commands](https://opencode.ai/docs/commands). These are permissions and prompts,
not a workflow finite-state machine; approvals and human supervision still matter.

Global filesystem configuration is below discovered project configuration.
OpenCode searches the current directory and ancestors to the filesystem root:
direct `opencode.json(c)` files merge farthest-to-nearest first, then discovered
`.opencode/opencode.json(c)` files in the same order. Thus discovered `.opencode`
documents override discovered direct documents. System/managed configuration
and policies may impose higher-priority restrictions. Unrelated merged settings,
global agents and built-ins can still be visible; this package does not disable
or replace all of them. See the native config guide for the complete hierarchy.

`default_agent` affects sessions without an explicit selected agent; it does
not replace an agent already stored on a session. The configured EM model is a
preference, not a forced rewrite of every stored session model. Selecting a
primary agent alone does not change the stored model. A command's explicit
model wins; otherwise its selected agent's configured model wins, then the
current session model. The shipped commands select EM without separate model
overrides; configured subagents use their explicit models.

OpenCode hot-reloads configuration, agents and commands after saves; no restart
is needed to apply them. Use `/reload` to force a reload if needed. This package
does not alter terminal-only `cli.json` settings.

### Nine commands, two optional entry paths

All nine commands select EngineeringManager in the current session
(`subagent: false`) without their own `model` field:

| Command | Entry path and behavior |
| --- | --- |
| `/em [request]` | Mandatory functional workflow: Explorer, Architect, user validation, Tester/RED, Developer/GREEN, EM summary |
| `/review [scope]` | Standalone: immediate delegation to Reviewer |
| `/doc [scope]` | Standalone: immediate delegation to Documentalist |
| `/security [scope]` | Standalone: immediate delegation to SecurityOfficer |
| `/em-review [scope]` | Post-cycle: Reviewer after EM verifies completion |
| `/em-doc [scope]` | Post-cycle: Documentalist after EM verifies completion |
| `/em-security [scope]` | Post-cycle: SecurityOfficer after EM verifies completion |
| `/em-audit [scope]` | Post-cycle: all three optional roles after EM verifies completion |
| `/em-save [name]` | Initialize or update authorized project tracking; no functional cycle required |

**Warning: `/review` overrides the native OpenCode command of the same name.**
Review this intentional replacement before installing. More specific project
configuration may override the installed definition.

Standalone commands do not require, reconstruct or verify completion of the
mandatory cycle. EM launches only the named specialist; missing prior design,
approval or RED/GREEN does not block this path. EM asks only necessary scope or
language clarifications. Reviewer and SecurityOfficer are read-only;
Documentalist may edit only documentation, comments and docstrings with no
functional effect. No optional command authorizes automatic functional fixes.
Proposed corrections return to the mandatory workflow with applicable approval
and a regression test, without launching it automatically. A standalone report
neither proves nor completes that workflow. Stable-reference coordination still
applies on either path; the post-cycle prerequisites remain unchanged.

## Verification

Run the portable public suite:

```sh
python3 -m unittest discover -s tests -v
```

Tests use fake HOME/XDG and temporary directories, including the `--global`
cases; they do not install into your actual global configuration. Coverage
includes CLI shape, all destinations, dry-run, strict JSON, V1.1 replacement,
private backups, idempotence, lock refusal, concurrency, filesystem guards and
static payload/language/hygiene contracts. An IO-permission test is skipped when
run as root because root bypasses its permission fixture. The frontmatter
extractor is limited regex, not a substitute for native loading.

For native loading, install into a disposable project, enter that directory,
then use the native CLI's GET API with your normal OpenCode discovery and
authentication context. Explicitly encode the project location: on the tested
CLI, the working directory alone did not scope API requests to the project.

```sh
location_query="$(python3 -c 'import os, urllib.parse; print(urllib.parse.urlencode({"location[directory]": os.getcwd()}))')"
opencode api get "/api/agent?$location_query"
opencode api get "/api/command?$location_query"
opencode api get "/api/model/default?$location_query"
```

Confirm the returned location, eight IDs, English prompts, ordered role
permissions, Architect delegation, nine command names/descriptions and default
model. On the tested API, `/api/command` exposes names/descriptions, not template
bodies: check installed template bytes against the payload separately. If
necessary read `/api/config` with the same location query privately to verify
the loaded project's `default_agent`; **do not publish raw config or provider
responses**, which can include personal settings. Do not start a
session, execute `/em` or send an inference request for this loading check.
Static checks, English prose review and GET loading do not prove LLM response
language behavior. No French/English/German inference verification is claimed.

## Security scanning (contributors)

Install pre-commit and the Gitleaks binary separately, with both available on
`PATH`. Use Gitleaks 8.30.1 to match the pinned hook and CI version, then run:

```sh
pre-commit install
```

The pre-commit hook scans the staged Git index with the default Gitleaks rules
extended by `.gitleaks.toml`; a missing binary blocks the hook (fail-closed).
CI installs the pinned binary after verifying its published release checksum,
runs the public unittest suite, then scans the full available Git history
(`--log-opts=--all`, full-depth checkout) and the working tree with redacted
output. Both scans run after successful tests even if the history scan fails;
installation, test or scan failure fails the job, without a fallback scanner.
The suite's homemade hygiene scanner remains a complementary check, not a
replacement for Gitleaks. Scan capability does not establish that an audit has
actually run; review the results and scope of each execution separately.

## Manual publication checklist (not an automatic action)

Before any later, separately authorized Git publication:

1. Review only intended payload, docs, installer, tests, ignore file and unchanged
   MIT license. Check new files as well as tracked paths for secrets, private
   paths, credential/config snapshots, logs and backups.
2. Inspect `git status --short`, `git diff`, `git diff --cached` and
   `git diff --check`. Untracked files need explicit review too.
3. After explicit authorization to stage, select exact public paths instead of
   blindly staging everything; inspect the staged diff and filenames again.
4. Review applicable Git history separately before calling a repository
   secret-free. This scoped working-tree review is not a historical audit.
5. Confirm the desired hosting repository, visibility and license before any
   separately requested commit, remote setup or push. No remote URL, commit or
   publication is performed or implied by these instructions.
6. Never publish a raw archive containing `.git/`, caches (`__pycache__/`),
   bytecode (`*.pyc` or `*.pyo`) or backups. Build release archives only from an
   explicitly reviewed set of public files, and inspect the archive contents
   before sharing.

The installer never stages, commits, configures remotes, pushes or deploys.
