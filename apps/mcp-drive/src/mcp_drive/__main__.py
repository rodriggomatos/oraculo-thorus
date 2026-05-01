"""Entrypoint: `python -m mcp_drive` ou `mcp-drive` script."""

import sys

from mcp_drive.server import build_server


def main() -> int:
    if sys.platform == "win32":
        import asyncio

        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    server = build_server()
    server.run(transport="stdio")
    return 0


if __name__ == "__main__":
    sys.exit(main())
