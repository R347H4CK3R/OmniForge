"""Optional standalone Android workbench listener; does not replace the existing Windows host."""
import os,pathlib,sys
from http.server import ThreadingHTTPServer
if __name__=='__main__':
    if not os.environ.get('OMNIFORGE_AGENT_KEY'):raise SystemExit('Set OMNIFORGE_AGENT_KEY')
    from agent_server import Handler
    ThreadingHTTPServer(('127.0.0.1',8791),Handler).serve_forever()
