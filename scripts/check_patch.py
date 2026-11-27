"""Run one patch variant's recovery tests on its pinned dependency."""

import argparse
import json
from pathlib import Path
import shutil
import stat
import subprocess
import tempfile

from prepare import apply_patch
from tailscale_patch import MODULE, ROOT, VARIANTS


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("variant", choices=VARIANTS)
    args = parser.parse_args()
    variant = VARIANTS[args.variant]
    download = subprocess.check_output(
        ["go", "mod", "download", "-json", f"{MODULE}@{variant['base']}"],
        text=True, encoding="utf-8",
    )
    with tempfile.TemporaryDirectory(prefix="tailscale-patch-check-") as temporary:
        source = Path(temporary) / "tailscale"
        shutil.copytree(json.loads(download)["Dir"], source)
        source.chmod(source.stat().st_mode | stat.S_IWUSR)
        for file in source.rglob("*"):
            file.chmod(file.stat().st_mode | stat.S_IWUSR)
        apply_patch(source, ROOT / variant["file"])
        command = [
            "go", "test", "-p", "4", "-race", "-json", "-count=3", "-timeout=120s",
            "-run", "^TestBindRetry", "./wgengine/magicsock",
        ]
        result = subprocess.run(command, cwd=source, capture_output=True, text=True, encoding="utf-8")
        report = ROOT / f"recovery-tests-{variant['name']}.jsonl"
        report.write_text(result.stdout, encoding="utf-8")
        if result.returncode:
            print(result.stderr)
            print(result.stdout)
            raise SystemExit(result.returncode)
        passed = {}
        for line in result.stdout.splitlines():
            entry = json.loads(line)
            name = entry.get("Test", "")
            if entry.get("Action") == "pass" and name.startswith("TestBindRetry") and "/" not in name:
                passed[name] = passed.get(name, 0) + 1
        if len(passed) < variant["minimum_tests"] or any(count != 3 for count in passed.values()):
            raise RuntimeError(f"Incomplete recovery test coverage: {passed}")
        print(f"{variant['name']}: {len(passed)} recovery tests each passed three times with race detection.")


if __name__ == "__main__":
    main()
