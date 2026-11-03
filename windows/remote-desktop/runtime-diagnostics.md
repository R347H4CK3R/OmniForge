# Tablet runtime investigation

The physical onn Android tablet passed HTTPS, JavaScript syntax, downloads of defaults.json, CSS and the 492070-byte viewer bundle, and a VNC WebSocket banner response, as shown in the owner's diagnostic screenshot on November 3, 2026. The original page still appeared blank. These results establish network and basic browser operation, not successful noVNC runtime initialization.

Run prepare-vnc-runtime.cjs beside the installed noVNC directory after prepare-vnc-bundle.cjs and esbuild. It creates runtime.html with inline styles, the bundled viewer, and a visible runtime/error panel. It leaves vnc.html unchanged. This isolates render-blocking asset loading and captures runtime exceptions. The owner's private Tailscale Serve also exposes /desktop on HTTPS 443 to localhost:6081. Open /desktop/runtime.html?autoconnect=1&resize=scale&path=websockify. The WebSocket path is relative to this page; do not duplicate desktop in the query.

The inline runtime page was verified on desktop Chromium with Android user-agent emulation: visible password form followed by an authenticated 1920x1080 connected canvas. Physical-tablet viewer confirmation remains pending. No password is embedded in these sources.
