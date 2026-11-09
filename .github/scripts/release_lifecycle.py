"""Source-only versioning and create-only publication for Log Event."""

import argparse
import json
import os
from pathlib import Path
import plistlib
import re
import subprocess
import sys
from xml.parsers.expat import ExpatError


PROJECT = Path("Log Event.xcodeproj/project.pbxproj")
PLIST = Path("Info.plist")
VERSION = re.compile(r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)")
SHA = re.compile(r"[0-9a-f]{40}")
KEYS = ("MARKETING_VERSION", "CURRENT_PROJECT_VERSION")
ASSIGNMENT = re.compile(
    r"^(\s*(MARKETING_VERSION|CURRENT_PROJECT_VERSION)\s*=\s*)([^;\n]+)(;[ \t]*)$",
    re.MULTILINE,
)
REFERENCE = re.compile(r"\$(?:\((MARKETING_VERSION|CURRENT_PROJECT_VERSION)\)|"
                       r"\{(MARKETING_VERSION|CURRENT_PROJECT_VERSION)\})")
TRAILER = "Co-authored-by: Copilot App <223556219+Copilot@users.noreply.github.com>"


def run(*args, cwd=None, data=None):
    return subprocess.run(
        args, cwd=cwd, input=data, text=True, check=True, stdout=subprocess.PIPE
    ).stdout.strip()


def unquote(value):
    return value[1:-1] if value.startswith('"') and value.endswith('"') else value


def read_version(root=Path(".")):
    project = (root / PROJECT).read_text()
    assignments = list(ASSIGNMENT.finditer(project))
    if len(assignments) != len(re.findall(
        r"^\s*(?:MARKETING_VERSION|CURRENT_PROJECT_VERSION)\s*=", project, re.MULTILINE
    )):
        raise ValueError("Malformed Xcode version assignment")
    values = {key: [unquote(m[3].strip()) for m in assignments if m[2] == key]
              for key in KEYS}

    def resolve(value, trail=()):
        if VERSION.fullmatch(value):
            return value
        ref = REFERENCE.fullmatch(value)
        if not ref:
            raise ValueError(f"Invalid source version or unrecognized reference: {value!r}")
        return resolve_key(ref[1] or ref[2], trail)

    def resolve_key(key, trail=()):
        if key in trail or not values[key]:
            raise ValueError(f"Missing or cyclic Xcode version: {key}")
        resolved = {resolve(v, (*trail, key)) for v in values[key]}
        if len(resolved) != 1:
            raise ValueError(f"Source version drift in {key}: {values[key]}")
        return resolved.pop()

    versions = {resolve_key(key) for key in KEYS}
    with (root / PLIST).open("rb") as stream:
        plist = plistlib.load(stream)
    if not isinstance(plist, dict):
        raise ValueError("Info.plist must be a dictionary")
    for key in ("CFBundleShortVersionString", "CFBundleVersion"):
        if key == "CFBundleVersion" and key not in plist:
            continue
        value = plist.get(key)
        if not isinstance(value, str):
            raise ValueError(f"Missing or invalid {key}")
        versions.add(resolve(value))
    if len(versions) != 1:
        raise ValueError(f"Source version drift: {sorted(versions)}")
    return versions.pop()


def bump_source(root, mode):
    current = read_version(root)
    parts = list(map(int, current.split(".")))
    index = {"major": 0, "minor": 1, "patch": 2}[mode]
    parts[index] += 1
    parts[index + 1:] = [0] * (2 - index)
    version = ".".join(map(str, parts))
    project = (root / PROJECT).read_text()
    project = ASSIGNMENT.sub(
        lambda m: m[1] + (m[3] if REFERENCE.fullmatch(unquote(m[3].strip()))
                         else version) + m[4], project
    )
    plist = (root / PLIST).read_text()
    for key in ("CFBundleShortVersionString", "CFBundleVersion"):
        pattern = re.compile(r"(<key>" + key + r"</key>\s*<string>)([^<]*)(</string>)")
        plist = pattern.sub(
            lambda m: m[1] + (m[2] if REFERENCE.fullmatch(m[2]) else version) + m[3],
            plist,
        )
    (root / PROJECT).write_text(project)
    (root / PLIST).write_text(plist)
    if read_version(root) != version:
        raise ValueError("Source update failed validation")
    return version


def selected_sha(root):
    sha = os.environ["GITHUB_SHA"]
    if not SHA.fullmatch(sha) or run("git", "rev-parse", "HEAD", cwd=root) != sha:
        raise ValueError("Checkout must match immutable selected GITHUB_SHA")
    return sha


def remote_ref(root, ref):
    output = run("git", "ls-remote", "--refs", "origin", ref, cwd=root)
    if not output:
        return None
    fields = output.split()
    if len(fields) != 2 or not SHA.fullmatch(fields[0]) or fields[1] != ref:
        raise ValueError(f"Malformed remote ref response for {ref}")
    return fields[0]


def bump(root, mode):
    sha = selected_sha(root)
    ref = os.environ["GITHUB_REF"]
    if not ref.startswith("refs/heads/"):
        raise ValueError("Bump version requires a selected branch")
    run("git", "check-ref-format", ref, cwd=root)
    if run("git", "status", "--porcelain", cwd=root):
        raise ValueError("Bump requires a clean checkout")
    if remote_ref(root, ref) != sha:
        raise ValueError("Selected branch moved since dispatch; dispatch again")
    version = bump_source(root, mode)
    run("git", "add", "--", str(PROJECT), str(PLIST), cwd=root)
    run("git", "commit", "-m", f"chore: bump version to {version}\n\n{TRAILER}", cwd=root)
    if remote_ref(root, ref) != sha:
        raise ValueError("Selected branch moved while bumping; no push attempted")
    # Check the server-advertised old SHA as well as fast-forward ancestry.
    # This rejects rewinds/deletions between ls-remote and push negotiation.
    run("git", "-c", "push.followTags=false",
        "-c", f"core.hooksPath={root.resolve() / '.github/hooks'}",
        "push", "--no-follow-tags", "origin", f"HEAD:{ref}", cwd=root)
    return version


def guard_push(root):
    expected = os.environ["GITHUB_SHA"]
    ref = os.environ["GITHUB_REF"]
    updates = [line.split() for line in sys.stdin if line.strip()]
    if (not SHA.fullmatch(expected) or not ref.startswith("refs/heads/")
            or len(updates) != 1 or len(updates[0]) != 4
            or updates[0][1] != run("git", "rev-parse", "HEAD", cwd=root)
            or updates[0][2:] != [ref, expected]):
        raise ValueError("Selected branch raced during push negotiation; push rejected")


def api(repo, method, suffix, payload=None):
    args = ["gh", "api", "--method", method, f"repos/{repo}/{suffix}"]
    if payload is not None:
        args += ["--input", "-"]
    return json.loads(run(*args, data=json.dumps(payload) if payload is not None else None))


def available(root, repo, tag):
    if remote_ref(root, f"refs/tags/{tag}") is not None:
        raise ValueError(f"Remote tag {tag} already exists")
    page = 1
    while True:
        releases = api(repo, "GET", f"releases?per_page=100&page={page}")
        if not isinstance(releases, list) or len(releases) > 100:
            raise ValueError(f"Malformed releases page {page}")
        for release in releases:
            if (not isinstance(release, dict)
                    or type(release.get("id")) is not int or release["id"] <= 0
                    or not isinstance(release.get("tag_name"), str) or not release["tag_name"]
                    or type(release.get("draft")) is not bool
                    or type(release.get("prerelease")) is not bool):
                raise ValueError(f"Malformed release on page {page}")
            if release["tag_name"] == tag:
                raise ValueError(f"Release {tag} already exists (including drafts)")
        if len(releases) < 100:
            break
        page += 1


def preflight(root):
    sha = selected_sha(root)
    version = read_version(root)
    repo = os.environ["GITHUB_REPOSITORY"]
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
        raise ValueError("Invalid repository")
    available(root, repo, f"v{version}")
    return sha, version, repo


def publish(root, assets):
    for asset in assets:
        if not (root / asset).is_file() or (root / asset).stat().st_size == 0:
            raise ValueError(f"Missing or empty release asset: {asset}")
    sha, version, repo = preflight(root)
    tag = f"v{version}"
    # Create-only refs API is atomic and rejects even a same-SHA creation race.
    created = api(repo, "POST", "git/refs", {"ref": f"refs/tags/{tag}", "sha": sha})
    if (not isinstance(created, dict) or created.get("ref") != f"refs/tags/{tag}"
            or not isinstance(created.get("object"), dict)
            or created["object"].get("sha") != sha or created["object"].get("type") != "commit"):
        raise ValueError("Malformed created-tag response")
    if remote_ref(root, f"refs/tags/{tag}") != sha:
        raise ValueError("Remote tag does not point exactly to the selected SHA")
    release = api(repo, "POST", "releases", {
        "tag_name": tag, "target_commitish": sha, "name": tag,
        "draft": False, "prerelease": False, "body": "",
    })
    if (not isinstance(release, dict) or type(release.get("id")) is not int
            or release["id"] <= 0 or release.get("tag_name") != tag
            or release.get("draft") is not False or release.get("prerelease") is not False):
        raise ValueError("Malformed created-release response")
    run("gh", "release", "upload", tag, *assets, "--repo", repo, cwd=root)
    return version


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("version")
    commands.add_parser("check")
    commands.add_parser("guard-push")
    commands.add_parser("bump").add_argument("mode", choices=("patch", "minor", "major"))
    commands.add_parser("publish").add_argument("assets", nargs=2)
    args = parser.parse_args()
    root = Path(".")
    try:
        if args.command == "version":
            version = read_version(root)
        elif args.command == "check":
            _, version, _ = preflight(root)
        elif args.command == "bump":
            version = bump(root, args.mode)
        elif args.command == "publish":
            version = publish(root, args.assets)
        else:
            guard_push(root)
            return 0
        print(version)
        if os.environ.get("GITHUB_OUTPUT"):
            with open(os.environ["GITHUB_OUTPUT"], "a") as output:
                output.write(f"version={version}\n")
    except (ValueError, KeyError, OSError, subprocess.CalledProcessError,
            plistlib.InvalidFileException, ExpatError) as error:
        print(f"::error::{error}", file=sys.stderr)
        if args.command == "publish":
            print("::error::Publication stopped. Any created tag, release and assets are retained. "
                  "Do not retry or delete automatically; follow README recovery guidance.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
