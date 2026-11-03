# Bundled private noVNC startup

Android Chrome and OmniForge both reported a noVNC Loading screen before credentials. The host returned the page and main modules successfully, but the exact tablet-side exception was unavailable. This repair reduces startup from many module requests to a single bundled script and adds bounded initialization errors. It does not claim the original tablet failure has been reproduced.

The owner's host currently uses noVNC 1.7.0 in %LOCALAPPDATA%\\OmniForge\\noVNC. Preserve that source and its licenses. Copy the two CJS scripts beside that folder. Run prepare-vnc-bundle.cjs with Node, then from the noVNC folder run:

```powershell
npm exec --yes --package=esbuild@0.25.11 -- esbuild omniforge-bootstrap.js --bundle --format=iife --target=chrome90,safari15 --outfile=omniforge-bundle.js --legal-comments=eof
Copy-Item vnc.bundled.html vnc.html -Force
```

The original HTML remains in vnc.original.html. Roll back by copying it to vnc.html. No service restart is needed. The existing private HTTPS address and VNC authentication are unchanged; credentials are never embedded in generated public files.

Verification uses a separate headless Chrome profile on debugging port 9228 and the host's existing ws Node dependency. Set VNC_TEST_PASSWORD privately, then run verify-vnc-bundle.cjs; it requires a visible password form and authenticated connected canvas and closes its test browser. The owner-host run passed Android user-agent startup, password UI and a 1920x1080 desktop through private HTTPS. That is desktop Chromium with mobile emulation, not physical Android hardware. The same deployed asset serves iOS and Android, with ES syntax targeted to Chrome 90 and Safari 15. Mobile-device confirmation remains required.
