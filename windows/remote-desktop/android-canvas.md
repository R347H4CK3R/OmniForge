# Android partial-frame rendering

The owner confirmed iOS rendered the complete desktop while the onn Android tablet rendered a truncated desktop with large gray regions after disabling H.264. Network and authentication checks passed. A browser test on the laptop rendered the full frame. These observations isolate an Android-specific render-path difference, though the physical GPU exception has not been captured.

Run patch-android-canvas.cjs beside the installed noVNC directory before rebuilding the bundle. It requests willReadFrequently:true on both visible and backing 2D canvas contexts only when the user agent contains Android. Chromium uses this hint to prefer a software-backed canvas. Other user agents retain their existing getContext calls. The script preserves the previous display.js and rejects unknown constructor source. Rebuild using the pinned esbuild command, generate runtime.html, and copy runtime.html to vnc.html.

After rebuilding, the Android-user-agent browser test authenticated, reported a 1920x1080 canvas, willReadFrequently:true, and 3571 distinct sampled RGBA colors. A complete desktop frame rendered. This is emulated browser identity on desktop Chromium; physical-tablet confirmation remains pending. Reconnect using a fresh query value, e.g. android_canvas=1, because an existing connection keeps the old renderer.
