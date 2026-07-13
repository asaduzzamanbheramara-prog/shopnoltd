// Deliberately empty of any privileged bridge. The window shows your own
// web-portal/admin-portal, which already handles its own auth (Keycloak
// PKCE) and API calls over HTTPS -- it doesn't need, and isn't given, any
// Node/Electron API access. Add contextBridge.exposeInMainWorld(...) here
// only if a specific desktop-only feature (native notifications, tray icon,
// etc.) is needed later, and expose the narrowest possible surface.
