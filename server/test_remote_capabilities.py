"""Regression tests for the authenticated remote capability endpoint."""
import http.client
import os
import threading
import unittest
from http.server import ThreadingHTTPServer
from unittest.mock import patch
try:
    from server import agent_server
except ImportError:
    import agent_server


class RemoteCapabilitiesTests(unittest.TestCase):
    def test_capabilities_report_only_iphone_to_windows(self):
        capabilities=agent_server.remote_capabilities()
        self.assertNotIn("iphone", capabilities)
        self.assertFalse(capabilities["desktop"]["iphone_can_control_windows_verified"])
        self.assertFalse(capabilities["network"]["private_https_verified"])

    def test_requires_bearer_token(self):
        server=ThreadingHTTPServer(("127.0.0.1",0),agent_server.Handler)
        worker=threading.Thread(target=server.serve_forever,daemon=True)
        worker.start()
        try:
            with patch.object(agent_server,"KEY","test-remote-key"):
                for token,expected in ((None,401),("Bearer wrong",401),("Bearer test-remote-key",200)):
                    connection=http.client.HTTPConnection("127.0.0.1",server.server_port,timeout=3)
                    headers={} if token is None else {"Authorization":token}
                    connection.request("GET","/v1/remote/capabilities",headers=headers)
                    response=connection.getresponse()
                    self.assertEqual(response.status,expected)
                    response.read()
                    connection.close()
        finally:
            server.shutdown()
            server.server_close()
            worker.join(timeout=3)


if __name__=="__main__":
    unittest.main()
