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

The no-defaults variant installs only eight profiles and five commands; it never
creates or modifies JSON, even with `--replace`. The script uses an explicit
allowlist, not an export of the user's global directory. It never copies
provider configuration, build/plan customization, auth.json, service.json,
credentials, logs or machine-specific backups.

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
reviewed files from `config/agents/` and five from `config/commands/` into the
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
permissions, Architect delegation, five command names/descriptions and default
model. On the tested API, `/api/command` exposes names/descriptions, not template
bodies: check installed template bytes against the payload separately. If
necessary read `/api/config` with the same location query privately to verify
the loaded project's `default_agent`; **do not publish raw config or provider
responses**, which can include personal settings. Do not start a
session, execute `/em` or send an inference request for this loading check.
Static checks, English prose review and GET loading do not prove LLM response
language behavior. No French/English/German inference verification is claimed.

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

The installer never stages, commits, configures remotes, pushes or deploys.
