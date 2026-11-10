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


def _decode_windows_ace(data):
    """Decode only ordinary allow/deny ACEs; unsupported ACE layouts deny access."""
    import struct
    if len(data) < 16:
        raise WorkspaceError('Malformed Windows ACE')
    kind, _flags, size, _mask = struct.unpack_from('<BBHI', data)
    if kind not in (0, 1) or size != len(data):
        raise WorkspaceError('Unsupported or malformed Windows ACE')
    revision, count = data[8:10]
    if revision != 1 or count > 15 or len(data) != 16 + count * 4:
        raise WorkspaceError('Malformed Windows ACE SID')
    authority = int.from_bytes(data[10:16], 'big')
    subauthorities = struct.unpack_from('<' + 'I' * count, data, 16)
    sid = 'S-1-' + str(authority) + ''.join('-' + str(value) for value in subauthorities)
    return {'qualifier': 'AccessAllowed' if kind == 0 else 'AccessDenied', 'sid': sid}


def _native_windows_acl(path):
    """Read the real file descriptor and process identity without starting a shell.

    All handles/memory are released, and every failed or unsupported native call
    denies access. No API here sets ACLs, takes ownership, or enables privileges.
    """
    import ctypes
    from ctypes import wintypes
    if os.name != 'nt':
        raise WorkspaceError('Windows ACL inspection requires Windows')
    advapi = ctypes.WinDLL('advapi32', use_last_error=True)
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    pointer = ctypes.c_void_p
    ppointer = ctypes.POINTER(pointer)
    def bind(dll, name, args, result):
        function = getattr(dll, name)
        function.argtypes = args
        function.restype = result
        return function
    get_security = bind(advapi, 'GetNamedSecurityInfoW', [wintypes.LPWSTR, ctypes.c_int, wintypes.DWORD,
                        ppointer, ppointer, ppointer, ppointer, ppointer], wintypes.DWORD)
    get_dacl = bind(advapi, 'GetSecurityDescriptorDacl', [pointer, ctypes.POINTER(wintypes.BOOL), ppointer,
                    ctypes.POINTER(wintypes.BOOL)], wintypes.BOOL)
    valid_acl = bind(advapi, 'IsValidAcl', [pointer], wintypes.BOOL)
    get_ace = bind(advapi, 'GetAce', [pointer, wintypes.DWORD, ppointer], wintypes.BOOL)
    convert_sid = bind(advapi, 'ConvertSidToStringSidW', [pointer, ctypes.POINTER(wintypes.LPWSTR)], wintypes.BOOL)
    open_token = bind(advapi, 'OpenProcessToken', [wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(wintypes.HANDLE)], wintypes.BOOL)
    get_token = bind(advapi, 'GetTokenInformation', [wintypes.HANDLE, ctypes.c_int, pointer, wintypes.DWORD,
                     ctypes.POINTER(wintypes.DWORD)], wintypes.BOOL)
    current_process = bind(kernel, 'GetCurrentProcess', [], wintypes.HANDLE)
    close_handle = bind(kernel, 'CloseHandle', [wintypes.HANDLE], wintypes.BOOL)
    local_free = bind(kernel, 'LocalFree', [pointer], pointer)

    def require(success):
        if not success:
            raise WorkspaceError('Cannot verify Windows private-state ACL (Win32 error %d)' % ctypes.get_last_error())

    def sid_text(sid):
        require(sid)
        text = wintypes.LPWSTR()
        require(convert_sid(sid, ctypes.byref(text)))
        try: return text.value
        finally: local_free(ctypes.cast(text, pointer))

    descriptor = pointer()
    owner = pointer()
    token = wintypes.HANDLE()
    try:
        error = get_security(str(path), 1, 0x1 | 0x4, ctypes.byref(owner), None, None, None, ctypes.byref(descriptor))
        if error:
            raise WorkspaceError('Cannot read Windows private-state ACL (Win32 error %d)' % error)
        present, defaulted = wintypes.BOOL(), wintypes.BOOL()
        dacl = pointer()
        require(get_dacl(descriptor, ctypes.byref(present), ctypes.byref(dacl), ctypes.byref(defaulted)))
        aces = []
        if present.value and dacl.value:
            require(valid_acl(dacl))
            # ACL header: revision byte, reserved byte, size WORD, ACE count WORD.
            import struct
            _revision, _reserved, acl_size, count, _reserved2 = struct.unpack('<BBHHH', ctypes.string_at(dacl, 8))
            if acl_size < 8: raise WorkspaceError('Malformed Windows ACL')
            for index in range(count):
                ace = pointer()
                require(get_ace(dacl, index, ctypes.byref(ace)))
                if not ace.value or not dacl.value + 8 <= ace.value <= dacl.value + acl_size - 4:
                    raise WorkspaceError('Windows ACE lies outside ACL')
                size = int.from_bytes(ctypes.string_at(ace.value + 2, 2), 'little')
                if size < 4 or ace.value + size > dacl.value + acl_size:
                    raise WorkspaceError('Malformed Windows ACE size')
                aces.append(_decode_windows_ace(ctypes.string_at(ace, size)))
        require(open_token(current_process(), 0x8, ctypes.byref(token)))  # TOKEN_QUERY only
        needed = wintypes.DWORD()
        if get_token(token, 1, None, 0, ctypes.byref(needed)) or ctypes.get_last_error() != 122:
            raise WorkspaceError('Cannot size Windows identity token')
        if not 0 < needed.value <= 65536:
            raise WorkspaceError('Invalid Windows identity token size')
        buffer = ctypes.create_string_buffer(needed.value)
        require(get_token(token, 1, buffer, needed, ctypes.byref(needed)))
        user_sid = ctypes.cast(buffer, ppointer).contents.value  # TOKEN_USER begins with SID_AND_ATTRIBUTES.
        return {'current_user': sid_text(user_sid), 'owner': sid_text(owner),
                'dacl_present': bool(present.value), 'dacl_null': not bool(dacl.value), 'aces': aces}
    finally:
        if token: close_handle(token)
        if descriptor: local_free(descriptor)


def _private(path):
    _safe(path)
    if os.name != 'nt':
        info = path.stat()
        if info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise WorkspaceError('Private state must be owner-only (directory 0700; file 0600)')
        return
    # chmod is not NTFS privacy. Native read-only APIs inspect the actual DACL.
    _validate_windows_acl(_native_windows_acl(path))

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
