"""Select the newest stable or preview release with an x64 desktop installer."""

import json
import os
import re
import subprocess
from urllib.parse import quote
from urllib.request import Request, urlopen

from tailscale_patch import build_fingerprint, dependency_version, select_variant

UPSTREAM = "SagerNet/sing-box"
TAG = re.compile(r"v([0-9]+)\.([0-9]+)\.([0-9]+)(?:-(alpha|beta|rc)\.([0-9]+))?")


def version_key(tag):
    match = TAG.fullmatch(tag)
    if not match:
        raise ValueError(f"Unsupported release tag: {tag}")
    major, minor, patch, stage, number = match.groups()
    return (int(major), int(minor), int(patch),
            {"alpha": 0, "beta": 1, "rc": 2, None: 3}[stage], int(number or 0))


def select_release(releases, channel, requested=""):
    if channel not in ("stable", "preview", "manual"):
        raise ValueError(f"Unsupported release channel: {channel}")
    if requested and not TAG.fullmatch(requested):
        raise ValueError("Expected a tag such as v1.14.5 or v1.15.0-alpha.14")
    if channel == "manual" and not requested:
        raise ValueError("The manual channel requires an explicit tag")
    qualifying = []
    for release in releases:
        tag = release["tag_name"]
        if not TAG.fullmatch(tag) or release["draft"]:
            continue
        if requested:
            if tag != requested:
                continue
        elif channel == "stable":
            if release["prerelease"] or "-" in tag:
                continue
        elif not release["prerelease"] or "-" not in tag:
            continue
        if any(asset["name"] == f"SFW-{tag[1:]}-x64.exe" for asset in release["assets"]):
            qualifying.append(release)
    if not qualifying:
        if requested:
            raise RuntimeError("No matching release with an official SFW x64 installer")
        return None
    return max(qualifying, key=lambda release: version_key(release["tag_name"]))


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


def plan_release(selected, published_tags):
    tag = selected["tag_name"]
    commit = upstream(f"commits/{tag}")["sha"]
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise RuntimeError("Could not resolve the upstream tag to a commit")
    request = Request(
        f"https://raw.githubusercontent.com/{UPSTREAM}/{commit}/go.mod",
        headers={"User-Agent": "SFW-patched-builds"},
    )
    with urlopen(request, timeout=30) as response:
        tailscale_version = dependency_version(response.read().decode("utf-8"))
    variant = select_variant(tailscale_version)
    release_tag = f"sfw-{tag}-pr12-{build_fingerprint(variant)}-{commit[:8]}-auto1"
    return {
        "build": str(release_tag not in published_tags).lower(),
        "tag": tag,
        "commit": commit,
        "release_tag": release_tag,
        "prerelease": str(selected["prerelease"]).lower(),
        "tailscale_version": tailscale_version,
        "patch_variant": variant["name"],
    }


def main():
    requested = os.environ.get("REQUESTED_TAG", "").strip()
    channel = os.environ.get("RELEASE_CHANNEL", "stable")
    if requested and not TAG.fullmatch(requested):
        raise ValueError("Expected a tag such as v1.14.5 or v1.15.0-alpha.14")
    endpoint = f"releases/tags/{quote(requested, safe='')}" if requested else (
        "releases?per_page=100"
    )
    releases = upstream(endpoint)
    selected = select_release([releases] if requested else releases, channel, requested)
    if selected is None:
        outputs = {"build": "false", "reason": "No matching published SFW x64 installer"}
    else:
        published_tags = gh(
            f"repos/{os.environ['GITHUB_REPOSITORY']}/releases?per_page=100",
            "--paginate", "--jq", '.[] | select(.draft == false) | .tag_name',
        ).splitlines()
        outputs = plan_release(selected, published_tags)
    outputs["channel"] = channel
    print(json.dumps(outputs))
    with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as file:
        for name, value in outputs.items():
            print(f"{name}={value}", file=file)


if __name__ == "__main__":
    main()
