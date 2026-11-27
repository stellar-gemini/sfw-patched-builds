import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

import tailscale_patch


class TailscalePatchSelectionTest(unittest.TestCase):
    def test_dependency_drives_selection(self):
        for version, expected in [
            ("v1.102.1-sing-box-1.14-mod.5", "ts1.102"),
            ("v1.102.1-sing-box-1.14-mod.5.0.20261019070639-79c1732442a9", "ts1.102"),
            ("v1.106.1-sing-box-1.15-mod.1", "ts1.106"),
        ]:
            with self.subTest(version=version):
                content = f"module example\nrequire (\n\tgithub.com/sagernet/tailscale {version} // pinned\n)\n"
                resolved = tailscale_patch.dependency_version(content)
                self.assertEqual(tailscale_patch.select_variant(resolved)["name"], expected)

    def test_unknown_dependency_stops(self):
        for version in ["v1.108.0-sing-box-1.16-mod.1", "v1.1020.1-sing-box-1.14-mod.5", "v1.106.1"]:
            with self.subTest(version=version), self.assertRaises(ValueError):
                tailscale_patch.select_variant(version)

    def test_missing_or_ambiguous_dependency_stops(self):
        entry = "github.com/sagernet/tailscale v1.106.1-sing-box-1.15-mod.1\n"
        for content in ["module example\n", entry + entry]:
            with self.subTest(content=content), self.assertRaises(ValueError):
                tailscale_patch.dependency_version(content)

    def test_new_variant_does_not_rebuild_old_variant(self):
        old = tailscale_patch.VARIANTS["1.102"]
        new = tailscale_patch.VARIANTS["1.106"]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            files = [old["file"], new["file"], "patches/sfw-updater.patch", "patches/sfw-sidebar-version.patch"]
            for file in files:
                destination = root / file
                destination.parent.mkdir(exist_ok=True)
                destination.write_text(file, encoding="utf-8")
            with patch.object(tailscale_patch, "ROOT", root):
                old_hash = tailscale_patch.build_fingerprint(old)
                new_hash = tailscale_patch.build_fingerprint(new)
                (root / new["file"]).write_text("updated 106 patch", encoding="utf-8")
                self.assertEqual(tailscale_patch.build_fingerprint(old), old_hash)
                self.assertNotEqual(tailscale_patch.build_fingerprint(new), new_hash)

    def test_existing_102_build_identity_is_preserved(self):
        self.assertEqual(tailscale_patch.build_fingerprint(tailscale_patch.VARIANTS["1.102"]), "a0f19748d3b3")


if __name__ == "__main__":
    unittest.main()
