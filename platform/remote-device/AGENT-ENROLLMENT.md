# Shopnoltd Remote Device Enrollment

The Shopnoltd device page manages two separate capabilities. They must not be
confused or presented as one credential:

1. **Shopnoltd Executor** — outbound-only heartbeat, device/network inventory
   and a fixed allowlist of approved diagnostics.
2. **MeshCentral remote desktop** — interactive screen/control for desktop
   platforms where the official MeshCentral agent is supported and the device
   owner has explicitly installed and authorized it.

## Executor enrollment

1. User signs in and opens the Shopnoltd **My Devices** page.
2. User selects **Add device**, enters a device name and chooses its platform.
3. Shopnoltd creates an account-owned pending record and one-time enrollment
   token. The token is shown once and is never embedded in a setup command.
4. User chooses **Auto Connect**. The website copies the setup command for the
   selected platform.
5. On the target Windows PC, run the PowerShell installer as Administrator.
   On Android, install/open Termux and run the generated Termux command.
6. The installer requests the one-time token through a hidden prompt, stores
   the resulting long-lived credential with restricted local permissions,
   and starts the outbound agent.
7. The device reports heartbeat, OS/platform, memory/disk and network profile.
   Refresh the device page to confirm that it is online.

The Windows installer registers a per-user logon task. The experimental Android
Termux installer uses a low-frequency heartbeat and diagnostics poll. Install
Termux:Boot separately for restart-after-reboot and allow Termux background
activity in Android battery settings.

Android Termux support is limited to inventory, heartbeat and approved
diagnostics. It does not capture the screen, send remote input, bypass Android
permissions or run arbitrary shell commands. iOS native-agent support is not
available yet.

## MeshCentral desktop remote-control enrollment

1. The device owner opens the authorized MeshCentral portal and downloads the
   official agent generated for the correct device group.
2. The owner installs the agent on the desktop device and confirms that it
   appears online in MeshCentral.
3. An authorized Shopnoltd user links the MeshCentral node ID to the matching
   Shopnoltd device record.
4. The **Connect** action becomes available and opens the MeshCentral session.

Supported MeshCentral desktop operating systems include Windows, Linux and
macOS. Do not assume Android screen-control support. Do not distribute a static
hard-coded MeshCentral agent token.

## Security requirements

- OIDC/Keycloak authentication and account ownership on every device action.
- One-time enrollment token exchanged for a per-agent HMAC credential.
- Outbound HTTPS only; no inbound shell or arbitrary command endpoint.
- Fixed operation allowlist, bounded execution and replay protection.
- Credential files restricted to the device owner/admin or OS service account.
- Device revocation immediately invalidates its runtime credential.
