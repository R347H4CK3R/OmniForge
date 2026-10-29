"""Constrained Windows process runner for the OmniForge private agent.

Never executes command strings through a shell. Every invocation has a fixed executable,
bounded arguments, workspace confinement, duration and output limits.
"""
import pathlib
import subprocess
import sys

COMMANDS={
    "git_status": ["git","status","--short"],
    "git_diff": ["git","diff","--stat"],
    "python_tests": [sys.executable,"-m","unittest","discover","-s","tests"],
    "python_compile": [sys.executable,"-m","compileall","-q","."],
    "node_version": ["node","--version"],
    "git_version": ["git","--version"],
}
def run(name,workspace,timeout=60):
    if name not in COMMANDS: raise ValueError("Command not authorized")
    if not 1<=timeout<=120: raise ValueError("Invalid timeout")
    root=pathlib.Path(workspace).resolve(strict=True)
    if not root.is_dir(): raise ValueError("Workspace is not a directory")
    try:
        p=subprocess.run(COMMANDS[name],cwd=str(root),stdin=subprocess.DEVNULL,
             shell=False,capture_output=True,text=True,timeout=timeout)
        return {"command":name,"exit_code":p.returncode,"stdout":p.stdout[-12000:],
                "stderr":p.stderr[-6000:],"timed_out":False}
    except subprocess.TimeoutExpired:
        return {"command":name,"exit_code":None,"stdout":"","stderr":"Timed out","timed_out":True}
    except OSError as exc:
        return {"command":name,"exit_code":None,"stdout":"","stderr":str(exc)[:500],"timed_out":False}
