"""Select a published sing-box release that ships the x64 desktop client."""

import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
from urllib.parse import quote
from urllib.request import Request, urlopen


UPSTREAM = "SagerNet/sing-box"
PATCHES = (
    Path("patches/tailscale-pr12.patch"),
    Path("patches/sfw-updater.patch"),
    Path("patches/sfw-sidebar-version.patch"),
)
TAG = re.compile(r"v[0-9]+\.[0-9]+\.[0-9]+(?:-(?:alpha|beta|rc)\.[0-9]+)?")


def gh(*args):
    result = subprocess.run(["gh", "api", *args], text=True, encoding="utf-8", capture_output=True)
    if result.returncode:
        raise RuntimeError(result.stderr.strip())
    return result.stdout


def upstream(endpoint):
    request = Request(f"https://api.github.com/repos/{UPSTREAM}/{endpoint}", headers={
        "Accept": "application/vnd.github+json", "User-Agent": "SFW-patched-builds",
    })
    with urlopen(request, timeout=30) as response:
        return json.load(response)


def main():
    requested = os.environ.get("REQUESTED_TAG", "").strip()
    if requested and not TAG.fullmatch(requested):
        raise ValueError("Expected a tag such as v1.14.4 or v1.15.0-alpha.13")
    endpoint = f"releases/tags/{quote(requested, safe='')}" if requested else (
        "releases?per_page=100"
    )
    releases = upstream(endpoint)
    if requested:
        releases = [releases]
    qualifying = [
        release for release in releases
        if TAG.fullmatch(release["tag_name"])
        and not release["draft"]
        and (requested or not release["prerelease"])
        and any(asset["name"] == f"SFW-{release['tag_name'][1:]}-x64.exe" for asset in release["assets"])
    ]
    if not qualifying:
        raise RuntimeError("No matching release with an official SFW x64 installer")
    selected = max(qualifying, key=lambda release: tuple(map(int, release["tag_name"][1:].split("-")[0].split("."))))
    tag = selected["tag_name"]
    commit = upstream(f"commits/{tag}")["sha"]
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise RuntimeError("Could not resolve the upstream tag to a commit")
    patch_set = hashlib.sha256(b"".join(hashlib.sha256(patch.read_bytes()).digest() for patch in PATCHES))
    release_tag = f"sfw-{tag}-pr12-{patch_set.hexdigest()[:12]}-{commit[:8]}-auto1"
    published_tags = gh(
        f"repos/{os.environ['GITHUB_REPOSITORY']}/releases?per_page=100",
        "--paginate", "--jq", '.[] | select(.draft == false) | .tag_name',
    ).splitlines()
    outputs = {
        "build": str(release_tag not in published_tags).lower(),
        "tag": tag,
        "commit": commit,
        "release_tag": release_tag,
        "prerelease": str(selected["prerelease"]).lower(),
    }
    print(json.dumps(outputs))
    with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as file:
        for name, value in outputs.items():
            print(f"{name}={value}", file=file)


if __name__ == "__main__":
    main()
