# Mobile display compatibility

The physical onn Android tablet reached the viewer after using inline runtime.html, but showed a mostly gray desktop with small rendered areas. A simultaneous desktop Chromium connection rendered the complete Steam desktop, with 3499 sampled distinct canvas colors at 1920x1080. The source desktop was not blank. This points to a client rendering/decoder difference; it does not establish the exact tablet exception.

Run disable-vnc-h264.cjs beside the installed noVNC directory, rebuild omniforge-bundle.js using the pinned esbuild command in README.md, and run prepare-vnc-runtime.cjs. The patch backs up browser.js, skips the optional hardware H.264 capability probe and leaves its exported capability false so standard VNC encodings are negotiated. Copy runtime.html to vnc.html to use the inline startup for existing clients. Keep the original upstream HTML backup and license files. No passwords are embedded. The patch is idempotent and rejects unrecognized source rather than guessing.

Private HTTPS startup, password authentication, connected 1920x1080 canvas and actual rendered color content were checked after the change. Tablet confirmation is still required. Reconnect with a fresh URL query to avoid old page content.
