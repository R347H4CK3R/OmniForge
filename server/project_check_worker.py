"""Trusted Windows check wrapper. Run only by project_workspace, never repo code.

Join a kill-on-close Job Object before starting any repository Python code.
No project-configurable command, arguments, environment or imports are accepted.
This provides descendant cleanup, NOT a filesystem/network/security sandbox.
"""
import ctypes
from ctypes import wintypes
import os
import subprocess
import sys


def _contain_windows_process():
    if sys.platform != 'win32':
        raise RuntimeError('Windows containment wrapper requires Windows')
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)

    class BasicLimits(ctypes.Structure):
        _fields_ = [('PerProcessUserTimeLimit', ctypes.c_longlong),
                    ('PerJobUserTimeLimit', ctypes.c_longlong),
                    ('LimitFlags', wintypes.DWORD),
                    ('MinimumWorkingSetSize', ctypes.c_size_t),
                    ('MaximumWorkingSetSize', ctypes.c_size_t),
                    ('ActiveProcessLimit', wintypes.DWORD),
                    ('Affinity', ctypes.c_size_t),
                    ('PriorityClass', wintypes.DWORD),
                    ('SchedulingClass', wintypes.DWORD)]

    class IOCounts(ctypes.Structure):
        _fields_ = [(name, ctypes.c_ulonglong) for name in
                    ('ReadOperationCount', 'WriteOperationCount', 'OtherOperationCount',
                     'ReadTransferCount', 'WriteTransferCount', 'OtherTransferCount')]

    class ExtendedLimits(ctypes.Structure):
        _fields_ = [('BasicLimitInformation', BasicLimits), ('IoInfo', IOCounts),
                    ('ProcessMemoryLimit', ctypes.c_size_t), ('JobMemoryLimit', ctypes.c_size_t),
                    ('PeakProcessMemoryUsed', ctypes.c_size_t), ('PeakJobMemoryUsed', ctypes.c_size_t)]

    kernel.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
    kernel.CreateJobObjectW.restype = wintypes.HANDLE
    kernel.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
    kernel.SetInformationJobObject.restype = wintypes.BOOL
    kernel.GetCurrentProcess.argtypes = []
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    kernel.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    kernel.AssignProcessToJobObject.restype = wintypes.BOOL
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.CloseHandle.restype = wintypes.BOOL
    # NULL security attributes make the handle non-inheritable. A private unnamed
    # job cannot be reopened by repository code using a public job name.
    job = kernel.CreateJobObjectW(None, None)
    if not job: raise ctypes.WinError(ctypes.get_last_error())
    limits = ExtendedLimits()
    limits.BasicLimitInformation.LimitFlags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    if not kernel.SetInformationJobObject(job, 9, ctypes.byref(limits), ctypes.sizeof(limits)):
        error = ctypes.get_last_error(); kernel.CloseHandle(job); raise ctypes.WinError(error)
    if not kernel.AssignProcessToJobObject(job, kernel.GetCurrentProcess()):
        error = ctypes.get_last_error(); kernel.CloseHandle(job); raise ctypes.WinError(error)
    # Keep the raw, non-inheritable handle open until ExitProcess. Closing it
    # explicitly would kill this wrapper before preserving the child's exit code.
    return job


def main():
    try:
        job = _contain_windows_process()
    except Exception:
        print('Windows check containment unavailable; no repository code started.', file=sys.stderr, flush=True)
        return 125
    try:
        result = subprocess.run([sys.executable, '-I', '-B', '-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_*.py'], close_fds=True)
        code = result.returncode
    except Exception:
        code = 126
    # ExitProcess closes the last job handle, terminating surviving descendants.
    # Parent timeout TerminateProcess also closes it. No finally closes it early.
    assert job
    sys.stdout.flush(); sys.stderr.flush()
    os._exit(code)


if __name__ == '__main__':
    sys.exit(main())
