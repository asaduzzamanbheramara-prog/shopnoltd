# Remote Device Access Model

## Roles

The gateway is the authorization boundary. The Registry is private infrastructure and accepts management requests only when the gateway supplies the configured `REGISTRY_CONTROL_TOKEN`.

- **Platform admin**: can list and manage every registered device, including devices owned by other users.
- **Regular user**: can create and enroll devices for their own verified Keycloak subject; can list and manage only devices they own; can access devices explicitly shared with them.
- **Shared user**: can view/use only the device explicitly shared with their verified Keycloak subject. Shared access does not transfer ownership or grant device deletion, re-sharing, token regeneration, or MeshCentral relinking.
- **Device agent**: can authenticate only as its enrolled device using its per-device HMAC credential; it cannot call user or admin management APIs.

## Enforcement rules

1. The gateway derives `owner_id` from the verified JWT `sub`; browser-supplied ownership is ignored.
2. Admin status is derived from the verified `platform_admin` role, including the realm role claim.
3. Device list, connect, share, share revocation, enrollment-token regeneration, MeshCentral linking, and deletion are authorized by the gateway against owner/shared/admin scope.
4. The Registry is not a public user API. Destructive operations require the gateway control token. Registry network policy must continue to prevent public ingress.
5. Enrollment and sharing are separate operations: enrollment registers a new device to its owner; sharing grants a second user scoped access to an existing device.
6. Browser profiles are limited to browser-session capabilities. A website cannot silently install an OS agent or bypass browser/device permission prompts.
7. Remote screen/control is only exposed where the device platform and its local consent model support it. Enrollment alone does not grant screen capture or input control.

## Verification

The registry security tests cover expiring, hashed, single-use enrollment tokens and now also verify that direct unauthenticated Registry deletion is rejected while authenticated gateway deletion succeeds.

Production rollout must update the Registry ConfigMap and Deployment using the repository's normal GitOps path, then verify the gateway-to-registry control token and run the tests before enabling user-facing changes. Do not rotate production credentials or apply changes directly to the live database as part of this patch.
