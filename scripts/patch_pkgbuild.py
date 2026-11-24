#!/usr/bin/env python3
"""Bump pkgver + per-arch sha256sums for GitHub Release -bin PKGBUILDs."""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ARCH_ASSETS = {
    "x86_64": "linux-x86_64",
    "aarch64": "linux-arm64",
}
_MANIFEST_CACHE: dict[str, dict] = {}


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
    text = re.sub(r"^resource_bundle_required=.*$", "resource_bundle_required=1", text, count=1, flags=re.M)
    checksums: dict[str, str] = {}
    for arch, platform in ARCH_ASSETS.items():
        filename = f"agent-toolkit-{version}-{platform}.tar.gz"
        url = (
            "https://github.com/ulises-jeremias/agent-toolkit/releases/"
            f"download/v{version}/{filename}"
        )
        sha = _download_manifest_sha256(url)
        print(f"{url} sha256={sha}")
        checksums[arch] = sha
        text = re.sub(
            rf"^source_{arch}=\(.*\)$",
            f'source_{arch}=("{filename}::{url}")',
            text,
            count=1,
            flags=re.M,
        )
        text = re.sub(
            rf"^sha256sums_{arch}=\('.*'\)$",
            f"sha256sums_{arch}=('{sha}')",
            text,
            count=1,
            flags=re.M,
        )
    pkgbuild.write_text(text)
    _write_srcinfo(pkgbuild, version, checksums)
    return 0


def _download_manifest_sha256(url: str) -> str:
    last_err: Exception | None = None
    for attempt in range(1, 37):
        try:
            with urllib.request.urlopen(url, timeout=60) as resp:
                data = resp.read()
            if len(data) > 100:
                tag = urllib.parse.urlsplit(url).path.split("/")[-2]
                manifest = _verified_manifest(tag)
                filename = url.rsplit("/", 1)[-1]
                platform = re.fullmatch(r"agent-toolkit-(?:\d+\.)*\d+-(linux-x86_64|linux-arm64)\.tar\.gz", filename)
                if not platform:
                    raise SystemExit(f"unsupported Agent Toolkit archive name: {filename}")
                _, arch = platform.group(1).split("-", 1)
                entry = _select_archive(manifest, filename, "linux", arch, "gnu")
                return _verified_asset_sha(entry, data)
        except urllib.error.HTTPError as exc:
            if 400 <= exc.code < 500 and exc.code != 429:
                raise SystemExit(f"{url} HTTP {exc.code}") from exc
            last_err = exc
            print(f"attempt {attempt}/36 {url}: HTTP {exc.code}")
        except (OSError, TimeoutError, urllib.error.URLError) as exc:
            last_err = exc
            print(f"attempt {attempt}/36 {url}: {exc}")
        time.sleep(15)
    raise SystemExit(f"failed to download {url}: {last_err}")


def _verified_manifest(tag: str) -> dict:
    if tag not in _MANIFEST_CACHE:
        manifest_url = f"https://github.com/ulises-jeremias/agent-toolkit/releases/download/{tag}/manifest.json"
        request = urllib.request.Request(manifest_url, headers={"User-Agent": "agent-toolkit-release-updater"})
        with urllib.request.urlopen(request, timeout=60) as resp:
            manifest = json.load(resp)
        commit_url = f"https://api.github.com/repos/ulises-jeremias/agent-toolkit/commits/{tag}"
        commit_request = urllib.request.Request(
            commit_url,
            headers={"Accept": "application/vnd.github+json", "User-Agent": "agent-toolkit-release-updater"},
        )
        with urllib.request.urlopen(commit_request, timeout=60) as resp:
            tagged_commit = json.load(resp).get("sha")
        _verify_manifest_identity(manifest, tag, tagged_commit)
        _MANIFEST_CACHE[tag] = manifest
    return _MANIFEST_CACHE[tag]


def _verify_manifest_identity(manifest: dict, tag: str, tagged_commit: str) -> None:
    source_sha = manifest.get("sourceSha", "")
    if (
        manifest.get("name") != "agent-toolkit"
        or manifest.get("version") != tag.removeprefix("v")
        or manifest.get("gitTag") != tag
        or manifest.get("channel") != "stable"
        or not re.fullmatch(r"[0-9a-f]{40}", source_sha)
    ):
        raise SystemExit(f"release manifest identity/sourceSha does not match tag {tag}")
    if tagged_commit != source_sha:
        raise SystemExit(f"manifest sourceSha {source_sha} does not match tag {tag} commit {tagged_commit}")


def _verified_asset_sha(asset: dict, data: bytes) -> str:
    actual = hashlib.sha256(data).hexdigest()
    expected = asset.get("sha256")
    if actual != expected:
        raise SystemExit(f"SHA-256 mismatch for {asset.get('filename')}: manifest={expected} downloaded={actual}")
    return expected


def _select_archive(manifest: dict, filename: str, os_name: str, arch: str, libc: str | None) -> dict:
    matches = [
        asset
        for asset in manifest.get("assets", [])
        if asset.get("filename") == filename
        and asset.get("kind") == "archive"
        and asset.get("channel") == "stable"
        and asset.get("os") == os_name
        and asset.get("arch") == arch
        and asset.get("libc") == libc
    ]
    if len(matches) != 1:
        raise SystemExit(f"manifest must contain exactly one matching archive entry for {filename}")
    return matches[0]


def _write_srcinfo(pkgbuild: Path, version: str, checksums: dict[str, str]) -> None:
    srcinfo = pkgbuild.parent / ".SRCINFO"
    if not srcinfo.is_file():
        return
    text = srcinfo.read_text()
    text = re.sub(r"^(\t?pkgver = ).*$", rf"\g<1>{version}", text, flags=re.M)
    text = re.sub(r"^(\t?pkgrel = ).*$", r"\g<1>1", text, flags=re.M)
    text = re.sub(r"/download/v[^/]+/", f"/download/v{version}/", text)
    for arch, platform in ARCH_ASSETS.items():
        filename = f"agent-toolkit-{version}-{platform}.tar.gz"
        url = f"https://github.com/ulises-jeremias/agent-toolkit/releases/download/v{version}/{filename}"
        text = re.sub(
            rf"^(\t?source_{arch} = ).*$",
            rf"\g<1>{filename}::{url}",
            text,
            flags=re.M,
        )
        text = re.sub(
            rf"^(\t?sha256sums_{arch} = ).*$",
            rf"\g<1>{checksums[arch]}",
            text,
            flags=re.M,
        )
    srcinfo.write_text(text)


if __name__ == "__main__":
    raise SystemExit(main())
