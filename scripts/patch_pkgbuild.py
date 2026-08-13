#!/usr/bin/env python3
"""Bump pkgver + per-arch sha256sums for GitHub Release -bin PKGBUILDs."""

from __future__ import annotations

import hashlib
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ARCH_ASSETS = {
    "x86_64": "agent-toolkit-linux-x86_64",
    "aarch64": "agent-toolkit-linux-arm64",
}


def main() -> int:
    pkg = os.environ["PACKAGE_NAME"]
    version = os.environ["VERSION"]
    pkgbuild = Path(pkg) / "PKGBUILD"
    text = pkgbuild.read_text()
    if "releases/download/" not in text:
        print("not a GitHub Release -bin PKGBUILD; refusing", file=sys.stderr)
        return 1
    text = re.sub(r"^pkgver=.*$", f"pkgver={version}", text, count=1, flags=re.M)
    text = re.sub(r"^pkgrel=.*$", "pkgrel=1", text, count=1, flags=re.M)
    for arch, asset in ARCH_ASSETS.items():
        url = (
            "https://github.com/ulises-jeremias/agent-toolkit/releases/"
            f"download/v{version}/{asset}"
        )
        sha = _download_sha256(url)
        print(f"{url} sha256={sha}")
        text = re.sub(
            rf"^sha256sums_{arch}=\('.*'\)$",
            f"sha256sums_{arch}=('{sha}')",
            text,
            count=1,
            flags=re.M,
        )
    pkgbuild.write_text(text)
    _write_srcinfo(pkgbuild, version)
    return 0


def _download_sha256(url: str) -> str:
    last_err: Exception | None = None
    for attempt in range(1, 37):
        try:
            with urllib.request.urlopen(url, timeout=60) as resp:
                data = resp.read()
            if len(data) > 100:
                return hashlib.sha256(data).hexdigest()
        except (OSError, TimeoutError, urllib.error.URLError) as exc:
            last_err = exc
            print(f"attempt {attempt}/36 {url}: {exc}")
        time.sleep(15)
    raise SystemExit(f"failed to download {url}: {last_err}")


def _write_srcinfo(pkgbuild: Path, version: str) -> None:
    srcinfo = pkgbuild.parent / ".SRCINFO"
    if not srcinfo.is_file():
        return
    text = srcinfo.read_text()
    text = re.sub(r"^(\t?pkgver = ).*$", rf"\g<1>{version}", text, flags=re.M)
    text = re.sub(r"^(\t?pkgrel = ).*$", r"\g<1>1", text, flags=re.M)
    text = re.sub(r"/download/v[^/]+/", f"/download/v{version}/", text)
    srcinfo.write_text(text)


if __name__ == "__main__":
    raise SystemExit(main())
