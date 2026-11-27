"""Select the UDP recovery patch for the upstream Tailscale dependency."""

import hashlib
from pathlib import Path
import re


MODULE = "github.com/sagernet/tailscale"
ROOT = Path(__file__).resolve().parents[1]
VARIANTS = {
    "1.102": {
        "name": "ts1.102",
        "file": "patches/tailscale-pr12.patch",
        "base": "v1.102.1-sing-box-1.14-mod.5.0.20261019070639-79c1732442a9",
        "minimum_tests": 15,
    },
    "1.106": {
        "name": "ts1.106",
        "file": "patches/tailscale-pr12-ts106.patch",
        "base": "v1.106.1-sing-box-1.15-mod.1",
        "minimum_tests": 16,
    },
}


def dependency_version(go_mod):
    versions = re.findall(
        r"^\s*github\.com/sagernet/tailscale\s+(v\S+)\s*(?://[^\n]*)?$",
        go_mod, re.MULTILINE,
    )
    if len(versions) != 1:
        raise ValueError("Expected exactly one Tailscale dependency in upstream go.mod")
    return versions[0]


def select_variant(version):
    match = re.fullmatch(r"v(1\.[0-9]+)\.[0-9]+-sing-box-[0-9A-Za-z.+-]+", version)
    if match is None or match[1] not in VARIANTS:
        raise ValueError(f"No UDP recovery patch supports Tailscale {version}. Add and validate a variant first.")
    return VARIANTS[match[1]]


def build_fingerprint(variant):
    paths = [
        variant["file"],
        "patches/sfw-updater.patch",
        "patches/sfw-sidebar-version.patch",
    ]
    contents = b"".join(hashlib.sha256((ROOT / file).read_bytes()).digest() for file in paths)
    return hashlib.sha256(contents).hexdigest()[:12]
