"""Local-only allowlisted operations, using disposable repositories exclusively."""
import errno
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


def _process_has_exited(status):
    try:
        return status.read_text().split()[2] == 'Z'
    except OSError as exc:
        # A dead child can be reaped before or during the /proc read.
        if exc.errno in (errno.ENOENT, errno.ESRCH):
            return True
        raise


class ProcessExitAssertionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.status = Path(self.tmp.name) / 'stat'

    def test_missing_process_has_exited(self):
        self.assertTrue(_process_has_exited(self.status))

    def test_zombie_process_has_exited(self):
        self.status.write_text('123 (python) Z\n')
        self.assertTrue(_process_has_exited(self.status))

    def test_live_process_has_not_exited(self):
        for state in ['R', 'S', 'D', 'T', 't', 'I']:
            with self.subTest(state=state):
                self.status.write_text(f'123 (python) {state}\n')
                self.assertFalse(_process_has_exited(self.status))

    def test_process_reaped_during_read_has_exited(self):
        self.status.write_text('123 (python) Z\n')
        for error_number in [errno.ENOENT, errno.ESRCH]:
            with self.subTest(errno=error_number):
                with patch.object(Path, 'read_text', side_effect=OSError(error_number, 'Process reaped')):
                    self.assertTrue(_process_has_exited(self.status))

    def test_exit_check_does_not_stat_a_process_being_reaped(self):
        self.status.write_text('123 (python) Z\n')
        with patch.object(Path, 'stat', side_effect=ProcessLookupError(errno.ESRCH, 'Process reaped')):
            self.assertTrue(_process_has_exited(self.status))

    def test_unexpected_read_errors_are_not_treated_as_process_exit(self):
        self.status.write_text('123 (python) Z\n')
        for error_number in [errno.EACCES, errno.EPERM, errno.EIO, None]:
            with self.subTest(errno=error_number):
                error = OSError(error_number, 'Cannot inspect process')
                with patch.object(Path, 'read_text', side_effect=error):
                    with self.assertRaises(OSError) as caught:
                        _process_has_exited(self.status)
                self.assertIs(caught.exception, error)


class ProjectWorkspaceTests(unittest.TestCase):
    def setUp(self):
        from server.project_workspace import ProjectWorkspace, WorkspaceError
        self.Error = WorkspaceError
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.repo = self.root / 'sample'
        (self.repo / 'src').mkdir(parents=True)
        (self.repo / 'tests').mkdir()
        self.file = self.repo / 'src/app.py'
        self.file.write_bytes(b'old\r\n')
        private = self.root / '.omniforge-private'
        private.mkdir(mode=0o700)
        self.registry = private / 'projects.json'
        self.registry.write_text(json.dumps({'version': 1, 'projects': {'demo': {
            'path': 'sample', 'editable_prefixes': ['src'], 'checks': ['python-unittest']}}}))
        self.registry.chmod(0o600)
        self.ws = ProjectWorkspace(self.root)

    def test_explicit_workspace_root_is_canonicalized(self):
        from server.project_workspace import ProjectWorkspace
        alias = self.root / 'selected-root'
        try: alias.symlink_to(self.root, target_is_directory=True)
        except OSError: self.skipTest('Symlink privilege unavailable')
        workspace = ProjectWorkspace(alias)
        self.assertEqual(workspace.read_file('demo', 'src/app.py')['content'], b'old\r\n')

    def test_default_deny_and_unknown_project_or_check(self):
        with self.assertRaises(self.Error): self.ws.read_file('missing', 'src/app.py')
        with self.assertRaises(self.Error): self.ws.run_check('demo', 'shell')
        self.registry.unlink()
        with self.assertRaises(self.Error): self.ws.read_file('demo', 'src/app.py')

    def test_read_and_hash_checked_edit_backup_exact_bytes(self):
        old = self.ws.read_file('demo', 'src/app.py')
        self.assertEqual(old['sha256'], hashlib.sha256(b'old\r\n').hexdigest())
        result = self.ws.edit_file('demo', 'src/app.py', b'new\n', old['sha256'])
        self.assertEqual(self.file.read_bytes(), b'new\n')
        backup = self.root / result['backup']
        self.assertEqual(backup.read_bytes(), b'old\r\n')
        if os.name != 'nt': self.assertEqual(backup.stat().st_mode & 0o777, 0o600)

    def test_stat_and_fstat_timestamp_semantics_can_differ(self):
        import server.project_workspace as module
        from types import SimpleNamespace
        original = os.fstat
        def fstat(fd):
            info = original(fd)
            fields = {name: getattr(info, name) for name in
                      ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns', 'st_mode', 'st_nlink')}
            fields['st_ctime_ns'] += 1000000  # Python 3.13 Windows handle/path semantics.
            return SimpleNamespace(**fields)
        with patch.object(module.os, 'fstat', side_effect=fstat):
            data, info = module._read(self.file)
        self.assertEqual(data, b'old\r\n')
        self.assertEqual(module._identity(info), module._identity(self.file.stat()))

    def test_stale_hash_preserves_user_changes(self):
        old = self.ws.read_file('demo', 'src/app.py')['sha256']
        self.file.write_bytes(b'user edit')
        with self.assertRaises(self.Error): self.ws.edit_file('demo', 'src/app.py', b'new', old)
        self.assertEqual(self.file.read_bytes(), b'user edit')

    def test_forbidden_paths_and_symlinks(self):
        try:
            (self.repo / 'src/link').symlink_to(self.root)
        except OSError:
            pass  # Windows may deny symlink creation; missing path still denies reads.
        for path in ['../outside', '/etc/passwd', 'src/../tests/a', 'src/link/a', '.git/config',
                     'src/.env', 'src/credentials.json', 'src/private/key', 'tests/a', 'src/a\\b']:
            with self.subTest(path=path), self.assertRaises(self.Error): self.ws.read_file('demo', path)
        try:
            (self.root / 'alias').symlink_to(self.repo, target_is_directory=True)
        except OSError:
            return  # Junction coverage below works without symlink privileges.
        data = json.loads(self.registry.read_text()); data['projects']['demo']['path'] = 'alias'
        self.registry.write_text(json.dumps(data))
        with self.assertRaises(self.Error): self.ws.read_file('demo', 'src/app.py')

    @unittest.skipUnless(os.name == 'nt', 'Windows junction test')
    def test_windows_junction_is_denied(self):
        import subprocess
        junction = self.repo / 'src/junction'
        result = subprocess.run(['cmd.exe', '/d', '/c', 'mklink', '/J', str(junction), str(self.root)], capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.addCleanup(lambda: os.rmdir(junction))
        with self.assertRaises(self.Error): self.ws.read_file('demo', 'src/junction/sample/src/app.py')

    def test_changes_during_preparation_are_not_overwritten(self):
        import server.project_workspace as module
        digest = self.ws.read_file('demo', 'src/app.py')['sha256']
        original = module._read
        calls = [0]
        def read(path, *args, **kwargs):
            if path == self.file:
                calls[0] += 1
                if calls[0] == 2: self.file.write_bytes(b'concurrent user edit')
            return original(path, *args, **kwargs)
        with patch.object(module, '_read', side_effect=read):
            with self.assertRaises(self.Error): self.ws.edit_file('demo', 'src/app.py', b'new', digest)
        self.assertEqual(self.file.read_bytes(), b'concurrent user edit')

    def test_windows_acl_validator_denies_null_missing_and_broad_dacls(self):
        from server.project_workspace import _validate_windows_acl
        safe = {'current_user': 'S-1-5-21-123-456-789-1001', 'owner': 'S-1-5-21-123-456-789-1001',
                'dacl_present': True, 'dacl_null': False,
                'aces': [{'qualifier': 'AccessAllowed', 'sid': 'S-1-5-21-123-456-789-1001'}]}
        _validate_windows_acl(safe)
        owner_rights = dict(safe, owner='S-1-5-32-544', aces=[{'qualifier': 'AccessAllowed', 'sid': 'S-1-3-4'}])
        _validate_windows_acl(owner_rights)
        with self.assertRaises(self.Error):
            _validate_windows_acl(dict(owner_rights, owner='S-1-5-21-999-999-999-1001'))
        for change in [{'dacl_present': False}, {'dacl_null': True}, {'aces': []},
                       {'owner': None}, {'aces': [{'qualifier': 'AccessAllowed', 'sid': 'S-1-1-0'}]},
                       {'aces': [{'qualifier': 'Unknown', 'sid': 'S-1-5-18'}]}]:
            with self.subTest(change=change), self.assertRaises(self.Error):
                _validate_windows_acl(dict(safe, **change))
        with self.assertRaises(self.Error): _validate_windows_acl({})

    def test_native_windows_ace_parser_fails_closed(self):
        import struct
        from server.project_workspace import _decode_windows_ace
        sid = bytes([1, 1]) + (5).to_bytes(6, 'big') + struct.pack('<I', 18)
        ace = struct.pack('<BBHI', 0, 0, 8 + len(sid), 0x1f01ff) + sid
        self.assertEqual(_decode_windows_ace(ace), {'qualifier': 'AccessAllowed', 'sid': 'S-1-5-18'})
        self.assertEqual(_decode_windows_ace(bytes([1]) + ace[1:])['qualifier'], 'AccessDenied')
        for invalid in [b'', ace[:-1], bytes([5]) + ace[1:], ace[:8] + bytes([2]) + ace[9:]]:
            with self.subTest(invalid=invalid), self.assertRaises(self.Error):
                _decode_windows_ace(invalid)

    @unittest.skipUnless(os.name == 'nt', 'Native Windows ACL inspection')
    def test_native_windows_acl_read_never_starts_subprocess(self):
        from server.project_workspace import _private, _native_windows_acl
        with patch('subprocess.run', side_effect=AssertionError('ACL inspection must not start a process')):
            _private(self.registry)
            facts = _native_windows_acl(self.registry)
        self.assertTrue(facts['dacl_present'])
        self.assertFalse(facts['dacl_null'])
        self.assertTrue(facts['aces'])
        with self.assertRaises(self.Error): _native_windows_acl(self.root / 'missing')

    def test_registry_private_and_strict(self):
        if os.name != 'nt':
            self.registry.chmod(0o644)
            with self.assertRaises(self.Error): self.ws.read_file('demo', 'src/app.py')
            self.registry.chmod(0o600)
        data = json.loads(self.registry.read_text()); data['projects']['demo']['command'] = 'echo hi'
        self.registry.write_text(json.dumps(data))
        with self.assertRaises(self.Error): self.ws.read_file('demo', 'src/app.py')

    def test_edit_bounds_and_hardlinks(self):
        digest = self.ws.read_file('demo', 'src/app.py')['sha256']
        for content, expected in [(b'x' * (1024 * 1024 + 1), digest), ('not bytes', digest), (b'x', 'bad')]:
            with self.assertRaises(self.Error): self.ws.edit_file('demo', 'src/app.py', content, expected)
        os.link(self.file, self.repo / 'src/alias')
        with self.assertRaises(self.Error): self.ws.edit_file('demo', 'src/app.py', b'x', digest)

    def fixture(self, body):
        (self.repo / 'tests/test_fixture.py').write_text('import unittest, os, time\nclass Fixture(unittest.TestCase):\n    def test_fixture(self):\n' + ''.join('        ' + s + '\n' for s in body.splitlines()))

    def test_check_success_failure_and_clean_environment(self):
        self.fixture("self.assertNotIn('GITHUB_TOKEN', os.environ)\nself.assertNotIn('CUSTOM_SECRET', os.environ)\nself.assertNotIn('PYTHONPATH', os.environ)")
        with patch.dict(os.environ, {'GITHUB_TOKEN': 'secret', 'CUSTOM_SECRET': 'secret', 'PYTHONPATH': '/untrusted'}):
            result = self.ws.run_check('demo', 'python-unittest')
        self.assertEqual(result['status'], 'passed')
        self.fixture('self.fail("expected fixture failure")')
        self.assertEqual(self.ws.run_check('demo', 'python-unittest')['status'], 'failed')

    def test_portable_backend_read_edit_and_check(self):
        self.assertTrue(self.ws.platform_supported)
        digest = self.ws.read_file('demo', 'src/app.py')['sha256']
        result = self.ws.edit_file('demo', 'src/app.py', b'portable', digest)
        self.assertEqual(self.file.read_bytes(), b'portable')
        self.assertEqual((self.root / result['backup']).read_bytes(), b'old\r\n')
        self.fixture('self.assertTrue(True)')
        self.assertEqual(self.ws.run_check('demo', 'python-unittest')['status'], 'passed')

    def test_failed_containment_never_starts_repository_code(self):
        from server import project_check_worker
        with patch.object(project_check_worker, '_contain_windows_process', side_effect=OSError('denied')):
            with patch.object(project_check_worker.subprocess, 'run') as launch:
                with patch('sys.stderr'):
                    self.assertEqual(project_check_worker.main(), 125)
                launch.assert_not_called()

    def test_child_process_is_cleaned_up_when_test_parent_exits(self):
        self.fixture('import subprocess, sys\np = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])\nwith open("child-pid", "w") as f: f.write(str(p.pid))')
        result = self.ws.run_check('demo', 'python-unittest', timeout=5)
        self.assertEqual(result['status'], 'passed', result)
        pid = int((self.repo / 'child-pid').read_text())
        if os.name == 'nt':
            import ctypes
            kernel = ctypes.WinDLL('kernel32', use_last_error=True)
            kernel.OpenProcess.restype = ctypes.c_void_p
            kernel.OpenProcess.argtypes = [ctypes.c_ulong, ctypes.c_int, ctypes.c_ulong]
            kernel.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
            kernel.CloseHandle.argtypes = [ctypes.c_void_p]
            handle = kernel.OpenProcess(0x100000, False, pid)
            if handle:
                try: self.assertEqual(kernel.WaitForSingleObject(handle, 2000), 0)
                finally: kernel.CloseHandle(handle)
        else:
            status = Path(f'/proc/{pid}/stat')
            self.assertTrue(_process_has_exited(status), f'Child process {pid} is still running')

    def test_timeout_and_output_bounds(self):
        self.fixture('time.sleep(5)')
        self.assertEqual(self.ws.run_check('demo', 'python-unittest', timeout=0.2)['status'], 'timeout')
        self.fixture('print("x" * 100000)')
        result = self.ws.run_check('demo', 'python-unittest', output_limit=1024)
        self.assertLessEqual(len(result['output'].encode()), 1024)
        self.assertTrue(result['output_truncated'])
        for timeout in [0, -1, 1000, float('nan')]:
            with self.assertRaises(self.Error): self.ws.run_check('demo', 'python-unittest', timeout=timeout)


if __name__ == '__main__': unittest.main()
