# Deploying Resident

Resident runs as three containers on one host: Postgres, the server, and a Tailscale sidecar.
Nothing publishes a port on the host; the server is reachable only over your tailnet at
`https://<TS_HOSTNAME>.<TS_TAILNET>`. See [docs/SECURITY.md](../docs/SECURITY.md) for why.

## 1. Prepare your tailnet

In the [Tailscale admin console](https://login.tailscale.com/admin):

1. **DNS:** enable MagicDNS and HTTPS certificates.
2. **Access controls:** add a tag owner and restrict who can reach the server. If your policy
   still has the default allow-all rule, replace it, otherwise every device in the tailnet can
   connect:

   ```jsonc
   {
     "tagOwners": {
       "tag:resident": ["autogroup:admin"]
     },
     "grants": [
       // Only your own devices may reach Resident, and only over HTTPS.
       { "src": ["you@github"], "dst": ["tag:resident"], "ip": ["tcp:443"] }
       // ...keep your other rules here
     ]
   }
   ```

3. **Keys:** generate an auth key with the `tag:resident` tag (reusable off, ephemeral off).

## 2. Configure and start

On the host, from the repository:

```bash
cp deploy/.env.example deploy/.env   # fill in every value
docker compose -f deploy/compose.yaml up -d --build
```

The server runs migrations on start. Check that everything is healthy:

```bash
docker compose -f deploy/compose.yaml ps
```

## 3. Pair devices

Tokens are created on the host and shown once:

```bash
# iPhone: can send data, can't read it back
docker compose -f deploy/compose.yaml exec server resident devices add iphone --scope ingest

# A local AI agent: read-only
docker compose -f deploy/compose.yaml exec server resident devices add agent --scope read

docker compose -f deploy/compose.yaml exec server resident devices list
docker compose -f deploy/compose.yaml exec server resident devices revoke iphone
```

## What's protected and how

| Layer | Setting |
|---|---|
| Network | `server` and `db` are only on the `internal` network, which has no internet access. Only the sidecar joins `egress`. No published ports. |
| Access | Tailscale ACLs, then a scoped token or an allowlisted Tailscale login on every request |
| Containers | Server runs as a non-root user with a read-only filesystem, all capabilities dropped and `no-new-privileges` |
| Host headers | The server only accepts its proxy target and your MagicDNS name, blocking DNS rebinding |
