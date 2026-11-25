"""Patch the checksum-verified Tailscale module selected by sing-box."""

import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess


MODULE = "github.com/sagernet/tailscale"
PR_HEAD = "c409abe7abaee51b20795b9fdb56dffe94f41b46"
ROOT = Path(__file__).resolve().parents[1]
UPDATE_REPOSITORY = "stellar-gemini/sfw-patched-builds"


def capture(*args, cwd):
    return subprocess.check_output(args, cwd=cwd, text=True, encoding="utf-8").strip()


def run(*args, cwd):
    subprocess.run(args, cwd=cwd, check=True)


def apply_patch(target, patch):
    run("git", "init", "-q", cwd=target)
    command = ["git", "-c", "apply.ignoreWhitespace=no", "apply", "--whitespace=nowarn"]
    if subprocess.run([*command, "--check", str(patch)], cwd=target).returncode == 0:
        run(*command, str(patch), cwd=target)
        return "applied"
    # Identical upstream integration is accepted only when the full patch can
    # be reversed cleanly and the same regression tests still run.
    run(*command, "--reverse", "--check", str(patch), cwd=target)
    return "already-present"


def main():
    box = ROOT / "src" / "sing-box"
    desktop = box / "clients" / "desktop"
    tag = os.environ["UPSTREAM_TAG"]
    patch = ROOT / "patches" / "tailscale-pr12.patch"
    go_mod = json.loads(capture("go", "mod", "edit", "-json", cwd=box))
    if any(entry["Old"]["Path"] == MODULE for entry in go_mod.get("Replace") or []):
        raise RuntimeError("Upstream added a Tailscale module replacement. Review the new build inputs.")
    version = next(entry["Version"] for entry in go_mod["Require"] if entry["Path"] == MODULE)
    download = json.loads(capture("go", "mod", "download", "-json", f"{MODULE}@{version}", cwd=box))
    checksum = download["Sum"]
    sum_line = f"{MODULE} {version} {checksum}"
    if sum_line not in (box / "go.sum").read_text(encoding="utf-8").splitlines():
        raise RuntimeError("Tailscale module does not match the checksum pinned in sing-box go.sum")
    target = box.parent / "tailscale"
    if target.exists():
        raise RuntimeError(f"{target} already exists. Start with a fresh source checkout.")
    shutil.copytree(download["Dir"], target)
    for file in target.rglob("*"):
        file.chmod(file.stat().st_mode | stat.S_IWUSR)
    patch_status = apply_patch(target, patch)
    run("go", "mod", "edit", f"-replace={MODULE}=../tailscale", cwd=box)

    version_file = desktop / "version.json"
    version_data = json.loads(version_file.read_text(encoding="utf-8"))
    if not re.fullmatch(r"go[0-9]+\.[0-9]+\.[0-9]+", version_data["go_version"]):
        raise RuntimeError("Invalid desktop Go version")
    version_data["version"] = tag.removeprefix("v")
    version_file.write_text(json.dumps(version_data, indent=2) + "\n", encoding="utf-8")
    updater_patch = ROOT / "patches" / "sfw-updater.patch"
    run("git", "apply", "--check", str(updater_patch), cwd=desktop)
    run("git", "apply", str(updater_patch), cwd=desktop)

    output = ROOT / "dist"
    output.mkdir(exist_ok=True)
    manifest = {
        "sing_box_tag": tag,
        "sing_box_commit": capture("git", "rev-parse", "HEAD", cwd=box),
        "desktop_commit": capture("git", "rev-parse", "HEAD", cwd=desktop),
        "dashboard_commit": capture("git", "rev-parse", "HEAD", cwd=desktop / "dashboard"),
        "tailscale_version": version,
        "tailscale_sum": checksum,
        "patch_pr": "https://github.com/SagerNet/tailscale/pull/12",
        "patch_commit": PR_HEAD,
        "patch_sha256": hashlib.sha256(patch.read_bytes()).hexdigest(),
        "patch_status": patch_status,
        "go_version": version_data["go_version"],
        "in_app_update_repository": UPDATE_REPOSITORY,
        "desktop_update_patch_sha256": hashlib.sha256(updater_patch.read_bytes()).hexdigest(),
        "architecture": "x64",
    }
    (output / "build-info.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
