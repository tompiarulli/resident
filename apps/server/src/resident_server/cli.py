"""Admin command line: ``resident devices add|list|revoke``.

Runs on the server host (e.g. ``docker compose exec server resident devices list``), so it
talks to the database directly rather than through the API.
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from resident_core.models import Scope
from resident_server import devices
from resident_server.db import get_sessionmaker


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="resident")
    commands = parser.add_subparsers(dest="command", required=True)

    device_parser = commands.add_parser("devices", help="manage device tokens")
    device_commands = device_parser.add_subparsers(dest="action", required=True)

    add = device_commands.add_parser("add", help="pair a new device and print its token")
    add.add_argument("name")
    add.add_argument(
        "--scope",
        dest="scopes",
        action="append",
        required=True,
        choices=[s.value for s in Scope],
        help="repeat for multiple scopes",
    )
    device_commands.add_parser("list", help="list devices")
    revoke = device_commands.add_parser("revoke", help="revoke a device's token")
    revoke.add_argument("name")

    args = parser.parse_args(argv)
    try:
        return asyncio.run(_run(args))
    except devices.DeviceError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


async def _run(args: argparse.Namespace) -> int:
    async with get_sessionmaker()() as session:
        match args.action:
            case "add":
                token = await devices.create_device(
                    session, args.name, (Scope(s) for s in args.scopes)
                )
                print(f"Created {args.name} with scopes: {', '.join(sorted(set(args.scopes)))}")
                print("Token (shown once, store it now):")
                print(token)
            case "list":
                for device in await devices.list_devices(session):
                    status = "revoked" if device.revoked_at else "active"
                    last_used = device.last_used_at.isoformat() if device.last_used_at else "never"
                    print(
                        f"{device.name:<24} {device.token_prefix}…  {status:<8} "
                        f"scopes={','.join(device.scopes)}  last_used={last_used}"
                    )
            case "revoke":
                await devices.revoke_device(session, args.name)
                print(f"Revoked {args.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
