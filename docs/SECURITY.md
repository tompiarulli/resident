# Security model

Resident stores some of the most sensitive data a person has. This document states what it
protects, from whom, and how. Changes that weaken any guarantee below need an explicit
discussion in the pull request.

To report a vulnerability, use GitHub's private "Report a vulnerability" form on the
repository's Security tab.

## Guarantees

1. **No public exposure.** The server has no published ports. It is reachable only through a
   Tailscale sidecar on your tailnet, never through Funnel or any public tunnel.
2. **No outbound network calls.** The server and database run on a Docker network with no
   internet egress. Resident has no telemetry, analytics, crash reporting or update checks.
3. **Every access is authenticated.** Devices and agents use scoped, revocable tokens. People
   use their Tailscale identity. There is no unauthenticated route except `/api/health`.
4. **Every read is audited.** Each read of health data records who, through what, and which
   metrics and dates. Audit entries never contain the values themselves.
5. **Least privilege.** Tokens carry only the scopes they need: the iOS app can write but not
   read, an agent can read but not write or delete.

## Assets

- Health observations, documents and anything derived from them
- Device tokens and the Tailscale node key
- Database backups

## Threats and mitigations

| Threat | Mitigation |
|---|---|
| Someone on the internet reaches the server | No published ports; tailnet-only via the Tailscale sidecar; Tailscale ACLs limit which devices can connect |
| Another device or user on the tailnet | ACLs restrict access to your own tagged devices; every request still needs a token or an allowlisted Tailscale identity |
| A stolen or lost phone | The iOS token is stored in the Keychain (this device only) and has only the `ingest` scope, so it can't read data back; revoke it from the server |
| A leaked token | Tokens are stored only as SHA-256 hashes, are individually revocable, and show last-used time |
| A compromised dependency exfiltrating data | The server container has no internet egress; dependencies are scanned in CI |
| Prompt injection through imported content (e.g. a malicious PDF) steering an AI agent | Agents get read-only tools with the `read` scope only: no writes, deletes, web or shell access |
| Data leaking through logs or error reports | Values, document contents and tokens are never logged; there is no third-party error reporting |
| Disk or backup theft | Full-disk encryption on the host; backups are encrypted before leaving it |
| Oversized requests exhausting the server | Request body size limits on every route |

## Trust boundaries

- **Tailscale identity headers.** `Tailscale-User-Login` is trusted only when
  `RESIDENT_TRUSTED_TAILSCALE_LOGINS` is set, and only because the server is reachable solely
  through the Tailscale sidecar on an internal Docker network. Never expose the server port
  any other way while this is enabled, or anyone could forge the header.
- **Cloud AI models.** Sending health data to a cloud model provider is outside the tailnet.
  It is not supported today and will only ever be an explicit, per-provider opt-in.

## Out of scope

- A fully compromised host machine or tailnet admin account
- Physical attacks on an unlocked device
- Multi-user isolation (Resident is single-person for now)
