from __future__ import annotations

import hashlib
import unittest

import patch_pkgbuild


class ReleaseManifestTests(unittest.TestCase):
    def test_manifest_must_match_tag_and_resolved_commit(self) -> None:
        source_sha = "0123456789abcdef0123456789abcdef01234567"
        manifest = {
            "name": "agent-toolkit",
            "version": "1.50.0",
            "gitTag": "v1.50.0",
            "sourceSha": source_sha,
            "channel": "stable",
        }
        patch_pkgbuild._verify_manifest_identity(manifest, "v1.50.0", source_sha)
        with self.assertRaises(SystemExit):
            patch_pkgbuild._verify_manifest_identity(manifest, "v1.50.0", "f" * 40)

    def test_archive_digest_must_match_manifest(self) -> None:
        data = b"verified archive bytes"
        asset = {"filename": "archive.tar.gz", "sha256": hashlib.sha256(data).hexdigest()}
        self.assertEqual(patch_pkgbuild._verified_asset_sha(asset, data), asset["sha256"])
        with self.assertRaises(SystemExit):
            patch_pkgbuild._verified_asset_sha(asset, b"tampered archive")

    def test_archive_asset_must_match_linux_architecture_and_libc(self) -> None:
        asset = {
            "filename": "agent-toolkit-1.50.0-linux-x86_64.tar.gz",
            "kind": "archive",
            "channel": "stable",
            "os": "linux",
            "arch": "x86_64",
            "libc": "gnu",
        }
        manifest = {"assets": [asset]}
        self.assertEqual(
            patch_pkgbuild._select_archive(
                manifest, asset["filename"], "linux", "x86_64", "gnu"
            ),
            asset,
        )
        with self.assertRaises(SystemExit):
            patch_pkgbuild._select_archive(
                manifest, asset["filename"], "linux", "x86_64", "musl"
            )


if __name__ == "__main__":
    unittest.main()
