"""Default-deny LOCAL ONLY repository tools; never exposed through HTTP.

Trusted repository tests execute code, not an OS sandbox. External editors must
be paused during apply. See docs/project-workspace.md for the security boundary.
"""
from contextlib import contextmanager
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import signal
import stat
import subprocess
import sys
import threading
import uuid

MAX_FILE = 1024 * 1024
CHECKS = frozenset({'python-unittest'})


class WorkspaceError(ValueError):
    """Denied, invalid or conflicting local operation."""


def _parts(value):
    if not isinstance(value, str) or not value or len(value) > 1024 or any(c in value for c in ('\\', '\x00', ':')):
        raise WorkspaceError('Invalid relative path')
    parts = value.split('/')
    if any(p in ('', '.', '..') or p.endswith((' ', '.')) for p in parts) or PurePosixPath(value).is_absolute():
        raise WorkspaceError('Invalid relative path')
    for part in parts:
        lower = part.lower()
        if (lower.startswith('.') or lower in {'private', 'credentials', 'secrets', 'id_rsa', 'id_ed25519'}
                or lower.split('.')[0] in {'con', 'prn', 'aux', 'nul', *(f'com{i}' for i in range(10)), *(f'lpt{i}' for i in range(10))}
                or any(word in lower for word in ('credential', 'secret', 'password', 'token'))
                or lower.endswith(('.pem', '.key', '.p12', '.pfx', '.keystore', '.jks'))):
            raise WorkspaceError('Private, credential or special path denied')
    return parts


def _digest(data):
    return hashlib.sha256(data).hexdigest()


def _safe(path):
    """Reject symlinks and all Windows reparse points, including junctions."""
    path = Path(path).absolute()
    try:
        for item in [*reversed(path.parents), path]:
            info = item.lstat()
            if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
                raise WorkspaceError('Symlink or reparse-point path denied')
        return path
    except OSError as exc:
        raise WorkspaceError('Path unavailable') from exc


def _identity(info):
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def _read(path, limit=MAX_FILE):
    _safe(path)
    try:
        before_path = path.stat()
        flags = os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0) | getattr(os, 'O_BINARY', 0)
        fd = os.open(path, flags)
        with os.fdopen(fd, 'rb') as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                raise WorkspaceError('Only ordinary non-hardlinked files are allowed')
            data = stream.read(limit + 1)
            if len(data) > limit:
                raise WorkspaceError('File exceeds size limit')
            _safe(path)
            after_path = path.stat()
            after_handle = os.fstat(stream.fileno())
            # Windows Python versions can report creation time via stat but
            # change time via fstat. Preserve timestamps within each API; link
            # the handle to the path with stable device/inode/size identity.
            stable_path = (before_path.st_dev, before_path.st_ino, before_path.st_size)
            stable_handle = (info.st_dev, info.st_ino, info.st_size)
            if (stable_path != stable_handle or _identity(before_path) != _identity(after_path)
                    or _identity(info) != _identity(after_handle)):
                raise WorkspaceError('File changed during read')
            return data, after_path
    except OSError as exc:
        raise WorkspaceError('File unavailable or unsafe') from exc


def _validate_windows_acl(descriptor):
    """Validate extracted descriptor facts; a null/absent DACL grants everyone access."""
    try:
        current = descriptor['current_user']
        if not isinstance(current, str) or not re.fullmatch(r'S-1-(?:[0-9]+-)*[0-9]+', current):
            raise ValueError()
        allowed = {current, 'S-1-5-18', 'S-1-5-32-544'}
        if descriptor['owner'] not in allowed or descriptor['dacl_present'] is not True or descriptor['dacl_null'] is not False:
            raise ValueError()
        aces = descriptor['aces']
        if not isinstance(aces, list) or not aces:
            raise ValueError()
        for ace in aces:
            if ace['qualifier'] not in ('AccessAllowed', 'AccessDenied'):
                raise ValueError()
            if ace['qualifier'] == 'AccessAllowed':
                # OWNER RIGHTS refers only to the already-validated descriptor
                # owner; unlike Everyone it does not authorize another identity.
                principal = descriptor['owner'] if ace['sid'] == 'S-1-3-4' else ace['sid']
                if principal not in allowed: raise ValueError()
    except (ValueError, KeyError, TypeError) as exc:
        raise WorkspaceError('Private state requires an explicit restricted DACL owned by this user, SYSTEM or Administrators') from exc


_WINDOWS_ACL_SCRIPT = r"""
$ErrorActionPreference = 'Stop'
$a = Get-Acl -LiteralPath $env:OF_PRIVATE_CHECK_PATH
$raw = [System.Security.AccessControl.RawSecurityDescriptor]::new($a.GetSecurityDescriptorBinaryForm(), 0)
$aces = @()
if ($null -ne $raw.DiscretionaryAcl) {
    foreach ($ace in $raw.DiscretionaryAcl) {
        if ($ace -is [System.Security.AccessControl.QualifiedAce]) {
            $aces += @{qualifier=$ace.AceQualifier.ToString(); sid=$ace.SecurityIdentifier.Value}
        } else { $aces += @{qualifier='Unknown'; sid=''} }
    }
}
$result = @{
    current_user=[System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value
    owner=$raw.Owner.Value
    dacl_present=([int]$raw.ControlFlags -band 4) -ne 0
    dacl_null=$null -eq $raw.DiscretionaryAcl
    aces=$aces
}
ConvertTo-Json -InputObject $result -Depth 5 -Compress
"""


def _private(path):
    _safe(path)
    if os.name != 'nt':
        info = path.stat()
        if info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise WorkspaceError('Private state must be owner-only (directory 0700; file 0600)')
        return
    # chmod is not NTFS privacy. Inspect the real descriptor with a fixed script,
    # then reject absent/null DACLs, unknown ACEs and broad allowed identities.
    system = Path(os.environ.get('SystemRoot', r'C:\Windows'))
    env = {'SystemRoot': str(system), 'OF_PRIVATE_CHECK_PATH': str(path)}
    try:
        result = subprocess.run([str(system / 'System32/WindowsPowerShell/v1.0/powershell.exe'), '-NoProfile', '-NonInteractive', '-Command', _WINDOWS_ACL_SCRIPT], env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=10)
        if result.returncode or len(result.stdout) > 65536:
            raise WorkspaceError('Cannot verify Windows private-state ACL')
        _validate_windows_acl(json.loads(result.stdout))
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise WorkspaceError('Cannot verify Windows private-state ACL') from exc


@contextmanager
def _lock(private):
    path = private / 'workspace.lock'
    if path.exists() or path.is_symlink(): _safe(path)
    fd = os.open(path, os.O_RDWR | os.O_CREAT | getattr(os, 'O_NOFOLLOW', 0), 0o600)
    try:
        if os.fstat(fd).st_nlink != 1: raise WorkspaceError('Unsafe lock file')
        if os.name == 'nt':
            import msvcrt
            if os.fstat(fd).st_size == 0: os.write(fd, b'0')
            os.lseek(fd, 0, os.SEEK_SET)
            msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield
    except OSError as exc:
        raise WorkspaceError('Workspace is busy or lock unavailable') from exc
    finally:
        os.close(fd)


class ProjectWorkspace:
    platform_supported = os.name in ('nt', 'posix')

    def __init__(self, workspace):
        if not self.platform_supported: raise WorkspaceError('Unsupported operating system')
        # Selecting the root is a trusted operator decision. Canonicalize it
        # once (macOS /var, for example); never resolve untrusted child paths.
        try: self.workspace = Path(workspace).resolve(strict=True)
        except OSError as exc: raise WorkspaceError('Workspace unavailable') from exc

    def _project(self, project_id):
        if not isinstance(project_id, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', project_id):
            raise WorkspaceError('Invalid project ID')
        _safe(self.workspace)
        private = self.workspace / '.omniforge-private'
        registry_path = private / 'projects.json'
        _private(private)
        _private(registry_path)
        raw, _ = _read(registry_path, 65536)
        try:
            registry = json.loads(raw)
            if set(registry) != {'version', 'projects'} or registry['version'] != 1 or not isinstance(registry['projects'], dict): raise ValueError()
            project = registry['projects'][project_id]
            if set(project) != {'path', 'editable_prefixes', 'checks'}: raise ValueError()
            repo = self.workspace.joinpath(*_parts(project['path']))
            for field in ('editable_prefixes', 'checks'):
                if not isinstance(project[field], list) or len(project[field]) > 100: raise ValueError()
            prefixes = [_parts(p) for p in project['editable_prefixes']]
            if any(not isinstance(c, str) or c not in CHECKS for c in project['checks']): raise ValueError()
        except (ValueError, TypeError, KeyError) as exc:
            raise WorkspaceError('Project not explicitly allowlisted or invalid registry') from exc
        _safe(repo)
        if not repo.is_dir(): raise WorkspaceError('Repository is not a directory')
        return repo, private, project, prefixes

    def _file(self, project_id, path):
        parts = _parts(path)
        repo, private, _project, prefixes = self._project(project_id)
        if not any(parts[:len(prefix)] == prefix for prefix in prefixes): raise WorkspaceError('Path not explicitly allowed')
        return _safe(repo.joinpath(*parts)), private

    def read_file(self, project_id, path):
        target, _ = self._file(project_id, path)
        data, _ = _read(target)
        return {'content': data, 'sha256': _digest(data), 'size': len(data)}

    def edit_file(self, project_id, path, content, expected_sha256):
        """Atomic replacement with cooperative locking and last-moment recheck.

        External editors must be paused: no portable atomic filesystem CAS exists.
        """
        if not isinstance(content, bytes) or len(content) > MAX_FILE: raise WorkspaceError('Content must be bytes, at most 1 MiB')
        if not isinstance(expected_sha256, str) or not re.fullmatch('[0-9a-f]{64}', expected_sha256): raise WorkspaceError('Expected SHA-256 required')
        target, private = self._file(project_id, path)
        with _lock(private):
            old, info = _read(target)
            if _digest(old) != expected_sha256: raise WorkspaceError('File changed; reread and review before applying')
            backup = private / ('backup-' + uuid.uuid4().hex)
            fd = os.open(backup, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_BINARY', 0), 0o600)
            with os.fdopen(fd, 'wb') as stream:
                stream.write(old); stream.flush(); os.fsync(stream.fileno())
            temp = target.parent / ('.workspace-edit-' + uuid.uuid4().hex)
            try:
                fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_BINARY', 0), 0o600)
                with os.fdopen(fd, 'wb') as stream:
                    stream.write(content); stream.flush(); os.fsync(stream.fileno())
                if os.name != 'nt': temp.chmod(stat.S_IMODE(info.st_mode) & 0o777)
                self._file(project_id, path)
                current, current_info = _read(target)
                if _digest(current) != expected_sha256 or _identity(current_info) != _identity(info):
                    raise WorkspaceError('File changed during edit; no replacement performed')
                os.replace(temp, target)
            finally:
                try: temp.unlink()
                except FileNotFoundError: pass
            return {'sha256': _digest(content), 'backup': '.omniforge-private/' + backup.name}

    def run_check(self, project_id, check_id, *, timeout=60, output_limit=65536):
        """One fixed trusted Python test command; no arbitrary args or shell."""
        if not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or not 0 < timeout <= 300: raise WorkspaceError('Timeout must be 0..300 seconds')
        if not isinstance(output_limit, int) or not 1 <= output_limit <= 65536: raise WorkspaceError('Output limit must be 1..65536 bytes')
        repo, private, project, _ = self._project(project_id)
        if not isinstance(check_id, str) or check_id not in project['checks'] or check_id not in CHECKS: raise WorkspaceError('Check not explicitly allowlisted')
        # Allowlist environment, rather than trying to recognize all secret names.
        env = {'PATH': os.defpath, 'PYTHONUNBUFFERED': '1'}
        command = [sys.executable, '-I', '-B', '-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_*.py']
        if os.name == 'nt':
            env['SystemRoot'] = os.environ.get('SystemRoot', r'C:\Windows')
            worker = Path(__file__).absolute().with_name('project_check_worker.py')
            _safe(worker)
            command = [sys.executable, '-I', '-B', str(worker)]
        output = bytearray()
        truncated = [False]
        def drain(pipe):
            try:
                while True:
                    chunk = pipe.read(8192)
                    if not chunk: break
                    capacity = output_limit - len(output)
                    output.extend(chunk[:capacity])
                    truncated[0] |= len(chunk) > capacity
            finally: pipe.close()
        with _lock(private):
            _safe(repo)
            process = subprocess.Popen(command, cwd=repo, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, start_new_session=os.name != 'nt')
            reader = threading.Thread(target=drain, args=(process.stdout,), daemon=True)
            reader.start()
            timed_out = False
            try:
                process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                timed_out = True
            finally:
                if os.name != 'nt':
                    try: os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError: pass
                if process.poll() is None: process.kill()
                process.wait(timeout=5)
                reader.join(timeout=1)
            if reader.is_alive():
                return {'check': check_id, 'status': 'cleanup_failed', 'returncode': process.returncode, 'output': '', 'output_truncated': True}
        # Drop incomplete UTF-8 bytes to maintain the byte limit in the response.
        status = 'timeout' if timed_out else ('passed' if process.returncode == 0 else 'failed')
        if os.name == 'nt' and process.returncode == 125: status = 'containment_unavailable'
        return {'check': check_id, 'status': status,
                'returncode': process.returncode, 'output': bytes(output).decode('utf-8', errors='ignore'), 'output_truncated': truncated[0]}
