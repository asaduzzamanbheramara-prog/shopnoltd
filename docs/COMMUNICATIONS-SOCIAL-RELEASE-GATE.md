# Shopnoltd Communications + Social Release Gate

This release keeps all existing Shopnoltd communication and social capabilities and adds the missing functional control-plane pieces.

## Messaging

- authenticated direct, group, and channel conversations
- persisted messages and attachments
- client message IDs for idempotent-capable clients
- replies
- edit/delete lifecycle
- reactions
- read state
- authenticated realtime WebSocket events through Redis pub/sub
- typing and presence event transport

## Calling

- authenticated audio/video call-session lifecycle
- ringing, accept, reject, and end states
- durable call history
- existing Jitsi room/JWT integration remains the media/session layer

## Social

- existing posts/feed/likes/shares/follows/views retained
- post editing
- threaded comments
- typed post reactions
- external sharing is never reported as successful without a configured provider

## API contract

The browser-facing API facade fronts Messaging, Calling, Live, and Social from the unified Shopnoltd API service. Internal service DNS names are not exposed to browser clients.

## Kubernetes

Messaging, Meet, and Live have platform-scoped Deployment/Service/ConfigMap/NetworkPolicy resources. Runtime database, Redis, Jitsi, and Owncast credentials are cluster-secret inputs and are not committed to Git.

The existing ingress files remain preserved for compatibility/documentation, but the service Kustomizations intentionally render the internal service resources only; public browser routing remains owned by the unified API/gateway contract.

## Required runtime validation

CI/source validation alone does not prove a production call or realtime session. The final release gate must verify authenticated message delivery, reconnect, receipts, call lifecycle, Jitsi media connectivity, live streaming, social interactions, and notification delivery in the deployed environment.
