# Shopnoltd Remote Device Agent

Shopnoltd Remote Device Agent provides an outbound-only connection from a
remote Windows/Linux/macOS device to the Shopnoltd Remote Gateway.

The device never needs an inbound public port.

Architecture:

Remote Device
    |
    | outbound authenticated connection
    v
Shopnoltd Remote Gateway
    |
    v
Guacamole / guacd
    |
    v
Browser

The agent is responsible for:

- device registration
- persistent device identity
- outbound connection
- heartbeat
- online/offline status
- remote desktop transport
- reconnect
- secure device authentication

The gateway is responsible for:

- device inventory
- device ownership
- connection authorization
- session allocation
- browser access
- Guacamole integration
