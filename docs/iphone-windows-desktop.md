# OmniForge Windows desktop control from iPhone

This feature has ONE direction: the OmniForge iPhone app views and controls the Windows laptop. The reverse direction is out of scope.

## Architecture

The iPhone's **Desktop** tab embeds an ephemeral WebKit client for an authenticated noVNC site. noVNC translates touch input to VNC pointer operations and forwards keyboard input. It needs a running, user-authorized VNC server on Windows plus a websockify gateway; the iPhone app alone does not install these services.

## Windows prerequisites

1. Install and configure a reputable VNC server on the Windows laptop with a strong, unique password. Restrict its listener to the loopback interface when supported; otherwise use the Windows firewall to prevent LAN and public inbound VNC exposure.
2. Install noVNC and websockify from the official open-source projects. Run the gateway locally, pointing at the Windows VNC listener, e.g. `websockify --web <path-to-noVNC> 127.0.0.1:6081 127.0.0.1:5900`. Check installed websockify syntax and the server's actual port.
3. Install Tailscale on the laptop and iPhone, connect both to the same trusted tailnet, and publish the localhost:6081 web gateway via Tailscale Serve over tailnet-only HTTPS. Do not use Funnel or forward port 5900 or 6081 from the internet.
4. Open the resulting private HTTPS noVNC URL in OmniForge's **Desktop** tab. Authenticate with the VNC server, enable input, and try a harmless click and a typed character.
5. Test on Wi-Fi, then cellular. Use the **Disconnect** button to close the WebKit session. Stop the VNC server and gateway if no longer needed.

## Verification required before marking it complete

- Confirm the noVNC HTML page loads in the app.
- Confirm the WebSocket handshake remains on the private HTTPS hostname.
- Confirm fresh remote desktop frames, mouse movement, touch-to-click, keyboard input and disconnect, using actual devices.
- Confirm invalid credentials and lost connectivity fail closed.
- Confirm the Windows firewall does not expose the VNC listener publicly.

**Current status:** Viewer source added, but Windows VNC installation, the private HTTPS gateway and physical-device tests have NOT been performed. A passing GitHub iOS build does not establish a working remote-control session.

Official documentation: https://github.com/novnc/noVNC and https://github.com/novnc/websockify
