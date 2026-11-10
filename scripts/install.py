#!/usr/bin/env python3
"""Install the fixed team payload using Python 3.10+ and no dependencies.

Run with exactly one destination selector; see --help and INSTALL.md. Preflight
refuses unsafe paths and collisions before writes. A target-local exclusive
lock coordinates installers, not unrelated editors. Writes are atomic per file,
not a transaction; failures require manual restoration from private backups.
Configuration contents are never included in diagnostics.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import uuid
from dataclasses import dataclass


AGENTS = (
    "EngineeringManager", "Explorer", "Architect", "Tester", "Developer",
    "Reviewer", "Documentalist", "SecurityOfficer",
)
COMMANDS = ("em", "em-review", "em-doc", "em-security", "em-audit", "review", "doc", "security")
PAYLOAD = tuple(f"agents/{name}.md" for name in AGENTS) + tuple(
    f"commands/{name}.md" for name in COMMANDS
)
DEFAULTS = {
    "$schema": "https://opencode.ai/config.json",
    "default_agent": "EngineeringManager",
    "model": "openrouter/mistralai/mistral-large-4-0",
}
BACKUPS = ".em-team-agents-backups"
LOCK = ".em-team-agents.lock"


class InstallError(Exception):
    """A safe, content-free diagnostic for a refused installation."""


@dataclass(frozen=True)
class Snapshot:
    """Original file bytes and identity metadata, or None for an absent file."""

    data: bytes | None
    identity: tuple | None
    mode: int = 0o644


@dataclass(frozen=True)
class Change:
    """Relative managed path, replacement bytes, and preflight state."""

    relative: str
    data: bytes
    before: Snapshot


def check_path(path: Path, directory: bool = False) -> None:
    """Reject symlinks and wrong types at path and every existing ancestor.

    Missing paths are allowed. This is a best-effort check, not a sandbox
    against hostile concurrent filesystem mutations. Raises InstallError.
    """
    for item in reversed((path, *path.parents)):
        try:
            mode = item.lstat().st_mode
        except FileNotFoundError:
            continue
        is_dir = item != path or directory
        if stat.S_ISLNK(mode) or not (
            stat.S_ISDIR(mode) if is_dir else stat.S_ISREG(mode)
        ):
            raise InstallError(f"Unsafe path or unexpected file type: {item}")


def snapshot(path: Path) -> Snapshot:
    """Read a regular, non-symlink file with identity checks; accept absence.

    Raises InstallError on a detected concurrent change; OS errors propagate
    to the CLI's content-free handler. No file contents enter error messages.
    """
    check_path(path)
    try:
        before = path.lstat()
    except FileNotFoundError:
        return Snapshot(None, None)
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    with os.fdopen(os.open(path, flags), "rb") as stream:
        opened = os.fstat(stream.fileno())
        if not stat.S_ISREG(opened.st_mode):
            raise InstallError(f"Not a regular file: {path}")
        data = stream.read()
        after = os.fstat(stream.fileno())
    def identity(value):
        """Include identity, permissions and nanosecond timestamps in a stamp."""
        return (value.st_dev, value.st_ino, value.st_mode, value.st_size,
                value.st_mtime_ns, value.st_ctime_ns)
    stamp = identity(before)
    if stamp != identity(opened) or stamp != identity(after) or stamp != identity(path.lstat()):
        raise InstallError(f"File changed while reading: {path}")
    return Snapshot(data, stamp, stat.S_IMODE(before.st_mode))


def strict_object(data: bytes) -> dict:
    """Parse strict JSON objects, rejecting duplicates and non-JSON constants.

    Errors intentionally omit parser details, keys and values, which may be
    sensitive even when parsing fails deep inside an unrelated setting.
    """
    def pairs(items):
        """Build an object only when every key is unique."""
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError
            result[key] = value
        return result

    def invalid_constant(_value):
        """Disallow the nonstandard NaN and Infinity accepted by json.loads."""
        raise ValueError

    try:
        result = json.loads(data.decode("utf-8"), object_pairs_hook=pairs,
                            parse_constant=invalid_constant)
        if not isinstance(result, dict):
            raise ValueError
        return result
    except (ValueError, UnicodeError, RecursionError):
        raise InstallError("Invalid strict JSON object (including duplicate keys); merge manually.") from None


def encoded(config: dict) -> bytes:
    """Serialize a changed JSON object; unchanged objects are never serialized."""
    return (json.dumps(config, indent=2, ensure_ascii=True, allow_nan=False) + "\n").encode("utf-8")


def read_payload() -> dict[str, bytes]:
    """Read only the fixed repository allowlist, rejecting missing/unsafe sources."""
    root = Path(__file__).absolute().parent.parent / "config"
    check_path(root, directory=True)
    payload = {}
    for relative in (*PAYLOAD, "opencode.json"):
        value = snapshot(root / relative).data
        if value is None:
            raise InstallError(f"Missing source payload: {relative}")
        if relative == "opencode.json":
            if strict_object(value) != DEFAULTS:
                raise InstallError("Source defaults do not match the fixed package contract.")
        else:
            payload[relative] = value
    return payload


def preflight(target: Path, payload: dict[str, bytes], args) -> tuple[list[Change], dict[str, Snapshot]]:
    """Plan the entire target without writes; refuse all known conflicts first.

    Returns changes and snapshots for all managed files, including read-only
    JSON. --replace cannot authorize JSONC or embedded team-ID collisions.
    """
    check_path(target, directory=True)
    for name in ("agents", "commands", BACKUPS):
        check_path(target / name, directory=True)
    lock = target / LOCK
    check_path(lock)
    jsonc = snapshot(target / "opencode.jsonc")
    if jsonc.data is not None:
        raise InstallError("JSONC destination refused; use a manual merge as described in INSTALL.md.")
    states = {rel: snapshot(target / rel) for rel in (*PAYLOAD, "opencode.json")}
    states["opencode.jsonc"] = jsonc
    desired = dict(payload)
    config_state = states["opencode.json"]
    config = strict_object(config_state.data) if config_state.data is not None else None
    if config is not None:
        for key, names in (("agents", AGENTS), ("commands", COMMANDS)):
            entries = config.get(key, {})
            if isinstance(entries, dict) and set(entries).intersection(names):
                raise InstallError("Embedded team agent/command collision; merge manually even with --replace.")
    if args.set_defaults:
        if config is None:
            desired["opencode.json"] = encoded(DEFAULTS)
        elif any(config.get(key) != DEFAULTS[key] for key in ("model", "default_agent")):
            config.update({key: DEFAULTS[key] for key in ("model", "default_agent")})
            desired["opencode.json"] = encoded(config)
    changes = []
    for relative, data in desired.items():
        old = states[relative]
        if old.data == data:
            continue
        if old.data is not None and not args.replace:
            raise InstallError(f"Different existing file requires --replace: {target / relative}")
        changes.append(Change(relative, data, old))
    if any(change.before.data is not None for change in changes):
        backup_root = target / BACKUPS
        if backup_root.exists() and os.name == "posix" and stat.S_IMODE(backup_root.stat().st_mode) != 0o700:
            raise InstallError(f"Existing backup directory must be private (0700): {backup_root}")
    return changes, states


def verify_states(target: Path, states: dict[str, Snapshot]) -> None:
    """Refuse a detected external change since preflight, including JSONC creation."""
    for relative, before in states.items():
        if snapshot(target / relative) != before:
            raise InstallError(f"File changed since preflight: {target / relative}")


def private_directory(path: Path) -> None:
    """Create or verify a 0700 backup directory without following symlinks."""
    check_path(path, directory=True)
    path.mkdir(mode=0o700, exist_ok=True)
    check_path(path, directory=True)
    if os.name == "posix" and stat.S_IMODE(path.stat().st_mode) != 0o700:
        raise InstallError(f"Backup directory is not private (0700): {path}")


def backup_file(run: Path, relative: str, data: bytes) -> None:
    """Save exact original bytes in a new 0600 file before replacement.

    run and parent directories are private. Exclusive creation prevents
    overwriting a prior backup; errors stop the installation.
    """
    path = run / relative
    for directory in reversed(path.parent.relative_to(run).parents):
        private_directory(run / directory)
    private_directory(path.parent)
    check_path(path)
    with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "wb") as stream:
        os.fchmod(stream.fileno(), 0o600)
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def atomic_write(path: Path, data: bytes, mode: int) -> None:
    """Replace one file atomically, preserving an existing file's permissions.

    A same-directory temporary file is flushed before os.replace. Temporary
    files are removed on failure; no cross-file rollback is attempted.
    """
    check_path(path)
    fd, temporary = tempfile.mkstemp(prefix=".em-team-agents-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fchmod(stream.fileno(), mode)
            os.fsync(stream.fileno())
        check_path(path)
        os.replace(temporary, path)
    finally:
        if os.path.lexists(temporary):
            os.unlink(temporary)


def install(target: Path, payload: dict[str, bytes], args, touched: list[str], backups: list[str]) -> None:
    """Preflight, lock, recheck and apply changes; report progress through lists.

    Busy/stale locks are never removed. Only this invocation's lock is cleaned
    on exit. Progress lists let the caller report partial writes on IO failure.
    """
    if os.path.lexists(target / LOCK):
        raise InstallError(f"Busy or stale lock; inspect manually: {target / LOCK}")
    changes, _states = preflight(target, payload, args)
    if args.dry_run:
        print(f"Dry-run: {len(changes)} file change(s) planned for {target}; no writes.")
        for change in changes:
            print(f"  {'replace' if change.before.data is not None else 'create'} {change.relative}")
        return
    target.mkdir(parents=True, exist_ok=True)
    check_path(target, directory=True)
    lock = target / LOCK
    try:
        fd = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        raise InstallError(f"Busy or stale lock; inspect manually: {lock}") from None
    owner = os.fstat(fd)
    try:
        with os.fdopen(fd, "w") as stream:
            stream.write(f"{os.getpid()}\n")
        # Another installer may have completed between preflight and locking.
        changes, states = preflight(target, payload, args)
        run = None
        for change in changes:
            verify_states(target, states)
            path = target / change.relative
            check_path(path.parent, directory=True)
            path.parent.mkdir(parents=True, exist_ok=True)
            if change.before.data is not None:
                if run is None:
                    private_directory(target / BACKUPS)
                    run = target / BACKUPS / uuid.uuid4().hex
                    run.mkdir(mode=0o700)
                    backups.append(str(run))
                backup_file(run, change.relative, change.before.data)
            verify_states(target, states)
            atomic_write(path, change.data, change.before.mode if change.before.data is not None else 0o644)
            touched.append(str(path))
            states[change.relative] = snapshot(path)
        print(f"Installed: {len(changes)} file change(s) in {target}.")
        for directory in backups:
            print(f"Private backups: {directory}")
    finally:
        try:
            current = lock.lstat()
            if (current.st_dev, current.st_ino) == (owner.st_dev, owner.st_ino):
                lock.unlink()
        except FileNotFoundError:
            pass


def main(argv: list[str] | None = None) -> int:
    """Parse CLI arguments; return 0 on success, 1 on safe refusal/IO failure.

    argparse exits with 2 on invalid arguments. Diagnostics expose only paths,
    counts and OS error categories, never source/destination configuration.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    destination = parser.add_mutually_exclusive_group(required=True)
    destination.add_argument("--global", dest="global_install", action="store_true", help="Use XDG_CONFIG_HOME/opencode or ~/.config/opencode")
    destination.add_argument("--project", type=Path, metavar="DIR", help="Use DIR/.opencode")
    destination.add_argument("--target", type=Path, metavar="DIR", help="Use DIR directly")
    parser.add_argument("--dry-run", action="store_true", help="Preflight only; create no files, directories, backups or lock")
    parser.add_argument("--set-defaults", action="store_true", help="Opt in to model/default_agent JSON changes (existing differences also require --replace)")
    parser.add_argument("--replace", action="store_true", help="Back up and replace different managed files")
    args = parser.parse_args(argv)
    touched: list[str] = []
    backups: list[str] = []
    try:
        if args.global_install:
            base = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
            target = base / "opencode"
        else:
            target = args.project / ".opencode" if args.project is not None else args.target
        target = Path(os.path.abspath(target.expanduser()))
        install(target, read_payload(), args, touched, backups)
        return 0
    except (InstallError, OSError, ValueError, RecursionError, KeyboardInterrupt) as error:
        detail = str(error) if isinstance(error, InstallError) else (
            os.strerror(error.errno) if isinstance(error, OSError) and error.errno else type(error).__name__
        )
        print(f"Installation stopped: {detail}", file=sys.stderr)
        print("Files already changed: " + (", ".join(touched) or "none"), file=sys.stderr)
        print("Backup locations: " + (", ".join(backups) or "none"), file=sys.stderr)
        print("No automatic rollback; inspect the target and restore manually if needed.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
