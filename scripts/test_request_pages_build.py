"""Exercise the Pages refresh command without contacting GitHub."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


class PagesBuildTests(unittest.TestCase):
    script = Path(__file__).with_name('request_pages_build.sh')

    def run_script(self, *, token='test-only-token', exit_code=0,
                   latest='old-commit built', read_exit=0, event='schedule'):
        with tempfile.TemporaryDirectory() as tmp:
            calls = Path(tmp) / 'calls'
            gh = Path(tmp) / 'gh'
            gh.write_text('''#!/bin/sh
printf '%s\\n' "$*" >> "$TEST_CALLS"
if [ "$2" = '--method' ]; then
  printf 'queued\\n'
  exit "$TEST_POST_EXIT"
fi
printf '%s\\n' "$TEST_LATEST"
exit "$TEST_READ_EXIT"
''')
            gh.chmod(0o700)
            git = Path(tmp) / 'git'
            git.write_text('#!/bin/sh\nprintf "current-commit\\n"\n')
            git.chmod(0o700)
            env = {**os.environ, 'PATH': tmp + os.pathsep + os.environ['PATH'],
                   'GITHUB_REPOSITORY': 'example/catalog', 'GH_TOKEN': token,
                   'GITHUB_EVENT_NAME': event,
                   'TEST_CALLS': str(calls), 'TEST_LATEST': latest,
                   'TEST_POST_EXIT': str(exit_code), 'TEST_READ_EXIT': str(read_exit)}
            result = subprocess.run(['bash', str(self.script)], env=env,
                                    text=True, capture_output=True)
            return result, calls.read_text().splitlines() if calls.exists() else []

    def test_requests_build_when_hosted_commit_is_behind_without_logging_token(self):
        result, calls = self.run_script()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(calls, ['api repos/example/catalog/pages/builds/latest --jq [.commit, .status] | join(" ")',
                                 'api --method POST repos/example/catalog/pages/builds --jq .status'])
        self.assertNotIn('test-only-token', result.stdout + result.stderr + str(calls))

    def test_reports_api_failure(self):
        result, _ = self.run_script(exit_code=17)
        self.assertEqual(result.returncode, 17, result.stderr)

    def test_does_not_request_without_token(self):
        result, calls = self.run_script(token='')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(calls, [])
        self.assertIn('GH_TOKEN', result.stderr)

    def test_skips_unchanged_successful_or_in_progress_build(self):
        for status in ['built', 'building', 'queued']:
            with self.subTest(status=status):
                result, calls = self.run_script(latest='current-commit ' + status)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(len(calls), 1)
                self.assertNotIn('--method POST', calls[0])

    def test_retries_unchanged_failed_build(self):
        result, calls = self.run_script(latest='current-commit errored')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('--method POST', calls[-1])

    def test_requests_when_latest_build_is_unavailable(self):
        result, calls = self.run_script(latest='', read_exit=1)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('--method POST', calls[-1])

    def test_workflow_checks_pages_after_unchanged_refreshes_too(self):
        workflow = self.script.parent.parent / '.github/workflows/unified-source.yml'
        step = workflow.read_text().split('- name: Refresh the public storefront after publication\n')[1].split('      - name:')[0]
        self.assertNotIn('if:', step)
        self.assertIn('bash scripts/request_pages_build.sh', step)

    def test_manual_refresh_can_request_a_fresh_build(self):
        result, calls = self.run_script(latest='current-commit built', event='workflow_dispatch')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('--method POST', calls[-1])


if __name__ == '__main__':
    unittest.main()
