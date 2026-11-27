import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import plan
import tailscale_patch


def release(tag, *, prerelease=None, draft=False, installer=True):
    return {
        "tag_name": tag,
        "prerelease": "-" in tag if prerelease is None else prerelease,
        "draft": draft,
        "assets": [{"name": f"SFW-{tag[1:]}-x64.exe"}] if installer else [],
    }


class ReleasePlanTest(unittest.TestCase):
    def test_stable_uses_numeric_version_and_requires_published_installer(self):
        releases = [release("v1.14.9"), release("v1.14.10"),
                    release("v1.15.0-alpha.14"), release("v1.16.0", draft=True),
                    release("v1.15.0", installer=False)]
        self.assertEqual(plan.select_release(releases, "stable")["tag_name"], "v1.14.10")

    def test_preview_numbers_and_stages_use_semantic_order(self):
        for tags, expected in [
            (["v1.15.0-alpha.9", "v1.15.0-alpha.14", "v1.15.0-alpha.13"],
             "v1.15.0-alpha.14"),
            (["v1.15.0-alpha.99", "v1.15.0-rc.1", "v1.15.0-beta.12"],
             "v1.15.0-rc.1"),
            (["v1.15.0-rc.99", "v1.16.0-alpha.1"], "v1.16.0-alpha.1"),
        ]:
            with self.subTest(tags=tags):
                releases = [release(tag) for tag in tags]
                releases += [release("v1.16.0-alpha.2", installer=False),
                             release("v1.16.0-alpha.3", draft=True), release("v1.17.0")]
                self.assertEqual(plan.select_release(releases, "preview")["tag_name"], expected)

    def test_channels_do_not_fall_back_to_each_other(self):
        self.assertIsNone(plan.select_release([release("v1.15.0-alpha.14")], "stable"))
        self.assertIsNone(plan.select_release([release("v1.14.5")], "preview"))
        self.assertIsNone(plan.select_release(
            [release("v1.15.0-alpha.14", prerelease=False)], "stable"))
        self.assertIsNone(plan.select_release([release("v1.14.5", prerelease=True)], "preview"))

    def test_manual_tag_selects_only_that_release(self):
        releases = [release("v1.15.0-alpha.14"), release("v1.16.0"), release("v1.14.5")]
        for tag in ("v1.15.0-alpha.14", "v1.14.5"):
            with self.subTest(tag=tag):
                selected = plan.select_release(releases, "manual", tag)
                self.assertEqual(selected["tag_name"], tag)
                self.assertEqual(selected["prerelease"], "-" in tag)
        with self.assertRaises(ValueError):
            plan.select_release(releases, "manual")
        with self.assertRaises(ValueError):
            plan.select_release(releases, "manual", "main")
        with self.assertRaises(RuntimeError):
            plan.select_release(releases, "manual", "v1.14.4")

    def test_existing_build_is_skipped_for_each_dependency_variant(self):
        for tag, version, family in [
            ("v1.14.5", "v1.102.1-sing-box-1.14-mod.5.0.20261019070639-79c1732442a9", "1.102"),
            ("v1.15.0-alpha.14", "v1.106.1-sing-box-1.15-mod.1", "1.106"),
        ]:
            with self.subTest(tag=tag):
                sha = "a" * 40
                fingerprint = tailscale_patch.build_fingerprint(tailscale_patch.VARIANTS[family])
                existing = f"sfw-{tag}-pr12-{fingerprint}-{sha[:8]}-auto1"
                module = f"require (\n\tgithub.com/sagernet/tailscale {version}\n)\n".encode()
                with patch.object(plan, "upstream", return_value={"sha": sha}), patch.object(
                    plan, "urlopen", side_effect=lambda *args, **kwargs: io.BytesIO(module)
                ):
                    skipped = plan.plan_release(release(tag), [existing])
                    fresh = plan.plan_release(release(tag), [])
                self.assertEqual(skipped["build"], "false")
                self.assertEqual(fresh["build"], "true")
                self.assertEqual(skipped["release_tag"], existing)
                self.assertEqual(skipped["patch_variant"], f"ts{family}")
                self.assertEqual(skipped["prerelease"], str("-" in tag).lower())

    def test_absent_channel_skips_without_resolving_or_building(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "output"
            with patch.dict(os.environ, {
                "REQUESTED_TAG": "", "RELEASE_CHANNEL": "preview", "GITHUB_OUTPUT": str(output),
            }), patch.object(plan, "upstream", return_value=[release("v1.14.5")]), patch.object(
                plan, "gh"
            ) as gh, patch("sys.stdout", new_callable=io.StringIO) as stdout:
                plan.main()
            gh.assert_not_called()
            self.assertEqual(json.loads(stdout.getvalue())["build"], "false")
            self.assertIn("channel=preview\n", output.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
