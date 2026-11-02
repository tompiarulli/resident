# Contributing to Resident

Thanks for helping build Resident. This page covers how to get set up and how changes land.
The detailed conventions (code, data handling, commit format, git practices) live in
[AGENTS.md](AGENTS.md), which applies to human and AI contributors alike.

## Getting set up

You'll need [uv](https://docs.astral.sh/uv/), [pnpm](https://pnpm.io/),
[just](https://just.systems/) and Docker. For the iOS app you'll also need Xcode (with the iOS
platform installed) and [XcodeGen](https://github.com/yonaskolb/XcodeGen).

```bash
cp .env.example .env
just setup          # Python, web and iOS project generation
just db && just migrate   # local Postgres on 127.0.0.1:5432
just device-add dev-dashboard read   # put the token in .env as RESIDENT_DEV_TOKEN
just server         # API + MCP on http://localhost:8000
just web            # dashboard on http://localhost:5173
```

Run `just` to see every recipe.

## Making a change

1. **Open an issue first** for anything bigger than a small fix, so we can agree on the approach.
2. **Branch from `main`** using `<type>/<short-description>`, e.g. `feat/lab-pdf-extraction`.
3. **Keep the PR to one logical change.** PRs are squash-merged, so each one becomes a single
   commit on `main`. Commit however you like on your branch; only the PR title and description
   end up in history.
4. **Check your work** with `just lint` and `just test`. If you changed the API, run
   `just openapi` and commit the regenerated spec and client.
5. **Open a pull request.** Its title becomes the commit subject on `main`, so it must be a
   Conventional Commit with a scope, e.g. `fix(ingest): skip records with unknown units` (a
   required check verifies this; see [AGENTS.md](AGENTS.md#git) for types and scopes). Its description becomes
   the commit body: explain what changed and why, and link the issue it addresses.

## Security

Read [docs/SECURITY.md](docs/SECURITY.md) before changing anything that touches the network,
authentication, logging or the deployment. Pull requests that weaken one of its guarantees need
to say so explicitly.

## Health data

Resident handles some of the most sensitive data people have, so:

- **Never commit real health data**, exports, lab reports or screenshots that contain them.
  Fixtures must be synthetic.
- Don't log observation values or document contents, and don't add telemetry or third-party
  calls without an explicit opt-in.
- Formulas and reference ranges need a cited source.

## Reporting security issues

Please don't open a public issue for security problems. Report them privately through
GitHub's "Report a vulnerability" option on the repository's Security tab.

## License

By contributing, you agree that your contributions are licensed under the
[AGPL-3.0](LICENSE).
