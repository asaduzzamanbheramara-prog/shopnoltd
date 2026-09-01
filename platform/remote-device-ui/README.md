# Shopnoltd Remote Devices UI

The UI must expose:

REMOTE DEVICES

[ + Add Device ]

Device
Platform
Status
Last Seen
Actions

Shopnoltd-PC-1
Windows
ONLINE
Just now

[ Connect ]

Add Device flow:

1. Click Add Device.
2. Enter device name.
3. Select platform.
4. Generate one-time enrollment token.
5. Show installation command/download.
6. Agent installs on target device.
7. Agent connects outbound.
8. UI changes Pending -> Online.
9. Click Connect.
10. Browser opens remote desktop session.

No inbound router port is required on the target device.
