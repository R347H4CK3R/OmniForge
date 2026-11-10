# Local allowlisted repository tools

`server.project_workspace.ProjectWorkspace` is a local Python API for deliberate
file reads, explicit byte replacements, and a fixed Python unittest check. It has
**no HTTP routes or native editing controls**. Existing queue behavior is unchanged.
No registry is shipped or created automatically. Discovery in the project dashboard
does not authorize editing or running code.

## Opt-in configuration (operator action, not performed by this change)

Place an explicitly reviewed `projects.json` in the workspace's
`.omniforge-private` directory. The directory and registry must already exist.
On POSIX they must be owned by the current user and owner-only (0700/0600).
On Windows the actual ACL must grant access only to the current user, SYSTEM,
and Administrators. OWNER RIGHTS is accepted only when the resolved owner is
one of those identities. Absent/null DACLs, unknown ACEs and inherited broad ACLs
are rejected. Windows PowerShell's
built-in `Get-Acl` validates this; failure to validate denies the operation.
Do not store this registry in a repository or expose it through a web service.

Example schema, **documentation only**, not an enabled registry:

```json
{
  "version": 1,
  "projects": {
    "sample": {
      "path": "sample-repository",
      "editable_prefixes": ["src"],
      "checks": ["python-unittest"]
    }
  }
}
```

Selecting the workspace root is a trusted operator decision: its path is
canonicalized once, including system aliases such as macOS `/var`. All subsequent
repository/private/file children must remain free of symlinks and reparse points.
Paths are workspace-relative slash-separated paths. An ID is not a filesystem
path. Unknown IDs, checks, schema fields and missing registries are denied.
Prefixes constrain both reads and edits. Files must exist already; this version
does not create directories, create files, delete files or restore backups.
Dot paths, private/credential paths, Windows special names and alternate data
streams, traversal, symlinks, junctions and other reparse points are rejected.
Hardlinked files are rejected. Keep secrets outside editable prefixes, including
secrets embedded in ordinary source files: filename checks cannot detect content.

## API

```python
from server.project_workspace import ProjectWorkspace
workspace = ProjectWorkspace('/absolute/workspace')  # Windows paths also work
snapshot = workspace.read_file('sample', 'src/app.py')
# Explicit new bytes supplied by the operator; never generated or inferred here.
result = workspace.edit_file('sample', 'src/app.py', b'reviewed replacement\n',
                             snapshot['sha256'])
check = workspace.run_check('sample', 'python-unittest')
```

`read_file` returns bytes, SHA-256 and byte count. Reads and replacements are
limited to 1 MiB. Edits require the expected hash and preserve the exact old
bytes in a uniquely named private backup before using an atomic replacement.
Stale hashes and changes detected during preparation abort without replacing the
file. Backups remain on failed attempts as well, and require manual retention
management. Filesystem metadata beyond ordinary POSIX permission bits is not
preserved (for example extended attributes and custom per-file Windows ACLs).
Use a disposable worktree or other reviewed checkout, not a production tree.

### Concurrency boundary

A private cross-process lock serializes these APIs' writes/checks. Files and path
components are checked again immediately before replacement. **Pause external
editors and other writers while applying changes.** Portable filesystem APIs do
not provide atomic compare-and-swap on file contents. A non-cooperating process
can still change a file or swap a directory between validation and replacement.
This is not a hardened boundary against malicious local processes or concurrently
modified repositories. Do not expose these methods to untrusted callers. The API
does not promise that advisory locking excludes arbitrary editor writes.

## Checks and cost

Only `python-unittest` is implemented: the current Python interpreter runs
`-I -B -m unittest discover -s tests -p test_*.py` in the selected repository.
No arbitrary command, shell, argument list, remote URL or interpreter override is
accepted. The environment is rebuilt from a minimal allowlist, excluding auth
tokens, HOME, SSH agents, Python startup variables and custom secrets. A zero exit
code means this command passed, not that any app was built or device-tested;
Python discovery can also pass with zero discovered tests. Test suites requiring
extra import paths or environment variables may need a different future check.

Default timeout is 60 seconds, configurable only up to 300 seconds. Combined
stdout/stderr retention is bounded to 64 KiB (or a smaller supplied limit), and
the pipe is drained without buffering unbounded output. Invalid UTF-8 is dropped.
Timeout cleanup kills the POSIX process group. On Windows a trusted standalone
wrapper creates an unnamed, non-inheritable KillOnJobClose Job Object and assigns
itself before starting any repository code. Test descendants inherit membership.
Normal wrapper exit or parent timeout termination closes the job handle and kills
surviving descendants. Job setup/assignment failure (including an incompatible
inherited job) returns `containment_unavailable` without starting repository code.
The wrapper must remain installed alongside `project_workspace.py`.
Cleanup is best-effort, not a guarantee against deliberately detached processes.
`cleanup_failed` is never reported as success. Returned test logs can contain
private information printed by tests; do not publish them automatically.

**Repository tests are executable trusted code, not an OS or network sandbox.**
They retain the user's filesystem/network permissions and can read credentials
from disk, spawn processes, or change files outside the editable prefix. Only
explicitly allowlist reviewed trusted repositories. Environment filtering does
not make hostile tests safe. These APIs do not install tools or dependencies,
check out repositories, register runners, push, publish, deploy a host service,
create credentials, or charge for hosted compute. Tests themselves must be
reviewed to avoid network access or costs.

Android offline builds, iOS/Mac coordination, editing from the native clients,
patch proposals, and remote runners remain unavailable in this API. iOS builds
still require an actual authorized Mac with suitable Xcode; a Windows laptop
cannot act as a macOS runner. No paid service is introduced by this foundation.

## Verification

`python -m unittest server.test_project_workspace -v` uses only temporary fixture
repositories and a temporary private registry. It covers default denial, stale
hashes, exact backups, path protection, output bounds, timeout, and real passing
and failing unittest processes. The Windows junction fixture runs on Windows;
POSIX permission checks run on POSIX. Run it on the actual supported host before
enabling a registry there. No live project is opted in by tests.
