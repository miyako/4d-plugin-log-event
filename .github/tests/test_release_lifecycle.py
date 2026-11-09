import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import yaml


ROOT = Path(__file__).resolve().parents[2]
FIXTURES = Path(__file__).parent / "fixtures"
SPEC = importlib.util.spec_from_file_location(
    "lifecycle", ROOT / ".github/scripts/release_lifecycle.py"
)
life = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(life)
REPO = "example/log-event"
SHA = "a" * 40


def git(root, *args):
    return life.run("git", *args, cwd=root)


def release(tag, draft=False):
    return {"id": 123, "tag_name": tag, "draft": draft, "prerelease": False}


class SourceFixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / life.PROJECT).parent.mkdir()
        shutil.copyfile(FIXTURES / "project.pbxproj", self.root / life.PROJECT)
        shutil.copyfile(FIXTURES / "Info.plist", self.root / life.PLIST)

    def replace(self, path, old, new):
        target = self.root / path
        target.write_text(target.read_text().replace(old, new))


class SourceTests(SourceFixture):
    def test_patch_minor_major(self):
        for mode, expected in (("patch", "7.8.10"), ("minor", "7.9.0"), ("major", "8.0.0")):
            with self.subTest(mode=mode):
                shutil.copyfile(FIXTURES / "project.pbxproj", self.root / life.PROJECT)
                shutil.copyfile(FIXTURES / "Info.plist", self.root / life.PLIST)
                self.assertEqual(life.bump_source(self.root, mode), expected)
                self.assertEqual(life.read_version(self.root), expected)
                self.assertIn("objectVersion = 46;", (self.root / life.PROJECT).read_text())
                data = plistlib.loads((self.root / life.PLIST).read_bytes())
                self.assertEqual(data["DependencyVersion"], "2.3.4")
                self.assertEqual(data["CFBundleInfoDictionaryVersion"], "6.0")

    def test_invalid_versions_fail_without_writes(self):
        for invalid in ("01.2.3", "1.2", "v1.2.3", "1.2.3-beta", "-1.2.3", "1.2.3junk"):
            with self.subTest(invalid=invalid):
                (self.root / life.PROJECT).write_text(
                    (FIXTURES / "project.pbxproj").read_text().replace("7.8.9", invalid)
                )
                before = (self.root / life.PROJECT).read_bytes()
                with self.assertRaises(ValueError):
                    life.bump_source(self.root, "patch")
                self.assertEqual((self.root / life.PROJECT).read_bytes(), before)

    def test_each_coordinated_field_rejects_drift(self):
        for key in life.KEYS:
            shutil.copyfile(FIXTURES / "project.pbxproj", self.root / life.PROJECT)
            self.replace(life.PROJECT, f"{key} = 7.8.9;", f"{key} = 7.8.8;")
            with self.subTest(key=key), self.assertRaises(ValueError):
                life.read_version(self.root)
        shutil.copyfile(FIXTURES / "project.pbxproj", self.root / life.PROJECT)
        for key in ("CFBundleVersion", "CFBundleShortVersionString"):
            data = plistlib.loads((FIXTURES / "Info.plist").read_bytes())
            data[key] = "7.8.8"
            (self.root / life.PLIST).write_bytes(plistlib.dumps(data))
            with self.subTest(key=key), self.assertRaises(ValueError):
                life.read_version(self.root)

    def test_single_configuration_drift_rejected(self):
        target = self.root / life.PROJECT
        target.write_text(target.read_text().replace("7.8.9", "7.8.8", 1))
        with self.assertRaises(ValueError):
            life.read_version(self.root)

    def test_references_preserved_and_validated(self):
        self.replace(life.PROJECT, "CURRENT_PROJECT_VERSION = 7.8.9;",
                     'CURRENT_PROJECT_VERSION = "$(MARKETING_VERSION)";')
        self.replace(life.PLIST, "<string>7.8.9</string>",
                     "<string>${CURRENT_PROJECT_VERSION}</string>")
        self.assertEqual(life.bump_source(self.root, "major"), "8.0.0")
        self.assertEqual((self.root / life.PROJECT).read_text().count('"$(MARKETING_VERSION)"'), 2)
        self.assertEqual((self.root / life.PLIST).read_text().count("${CURRENT_PROJECT_VERSION}"), 2)

    def test_unknown_and_cyclic_references_rejected(self):
        self.replace(life.PLIST, "7.8.9", "$(UNKNOWN_VERSION)")
        with self.assertRaises(ValueError):
            life.read_version(self.root)
        shutil.copyfile(FIXTURES / "Info.plist", self.root / life.PLIST)
        self.replace(life.PROJECT, "CURRENT_PROJECT_VERSION = 7.8.9;",
                     "CURRENT_PROJECT_VERSION = $(MARKETING_VERSION);")
        self.replace(life.PROJECT, "MARKETING_VERSION = 7.8.9;",
                     "MARKETING_VERSION = $(CURRENT_PROJECT_VERSION);")
        with self.assertRaises(ValueError):
            life.read_version(self.root)

    def test_missing_and_malformed_source_rejected(self):
        for old, new in (("MARKETING_VERSION", "IGNORED_VERSION"),
                         ("CURRENT_PROJECT_VERSION = 7.8.9;", "CURRENT_PROJECT_VERSION = ;")):
            shutil.copyfile(FIXTURES / "project.pbxproj", self.root / life.PROJECT)
            self.replace(life.PROJECT, old, new)
            with self.subTest(new=new), self.assertRaises(ValueError):
                life.read_version(self.root)

    def test_absent_optional_plist_build_version_stays_absent(self):
        self.replace(life.PLIST, "    <key>CFBundleVersion</key>\n    <string>7.8.9</string>\n", "")
        self.assertEqual(life.bump_source(self.root, "patch"), "7.8.10")
        self.assertNotIn("CFBundleVersion", (self.root / life.PLIST).read_text())


class GitTests(SourceFixture):
    def setUp(self):
        super().setUp()
        self.remote = self.root.parent / (self.root.name + "-remote.git")
        self.addCleanup(shutil.rmtree, self.remote)
        git(self.root, "init", "--bare", str(self.remote))
        git(self.root, "--git-dir", str(self.remote), "config", "user.name", "Remote fixture")
        git(self.root, "--git-dir", str(self.remote), "config", "user.email", "remote@example.invalid")
        git(self.root, "init", "-b", "selected")
        git(self.root, "config", "user.name", "Lifecycle fixture")
        git(self.root, "config", "user.email", "fixture@example.invalid")
        scripts = self.root / ".github/scripts"
        scripts.mkdir(parents=True)
        shutil.copyfile(ROOT / ".github/scripts/release_lifecycle.py", scripts / "release_lifecycle.py")
        hooks = self.root / ".github/hooks"
        hooks.mkdir()
        shutil.copy2(ROOT / ".github/hooks/pre-push", hooks / "pre-push")
        (hooks / "pre-push").chmod(0o755)
        (self.root / "prebuilt.plist").write_text("prebuilt 1.0; never update")
        git(self.root, "add", ".")
        git(self.root, "commit", "-m", "stable fixture")
        git(self.root, "commit", "--allow-empty", "-m", "selected tip")
        self.sha = git(self.root, "rev-parse", "HEAD")
        git(self.root, "remote", "add", "origin", str(self.remote))
        git(self.root, "push", "--no-follow-tags", "origin", "HEAD:refs/heads/selected")
        self.env = patch.dict(os.environ, {
            "GITHUB_SHA": self.sha, "GITHUB_REF": "refs/heads/selected",
            "PYTHONDONTWRITEBYTECODE": "1",
        })
        self.env.start()
        self.addCleanup(self.env.stop)

    def test_bump_pushes_only_selected_sources_without_followed_tags(self):
        git(self.root, "config", "push.followTags", "true")
        git(self.root, "tag", "-a", "unrelated", "-m", "must not follow")
        self.assertEqual(life.bump(self.root, "minor"), "7.9.0")
        head = git(self.root, "rev-parse", "HEAD")
        self.assertEqual(life.remote_ref(self.root, "refs/heads/selected"), head)
        self.assertEqual(git(self.root, "ls-remote", "--tags", "origin"), "")
        self.assertEqual(set(git(self.root, "diff-tree", "--no-commit-id", "--name-only",
                                 "-r", "HEAD").splitlines()), {str(life.PROJECT), str(life.PLIST)})
        self.assertIn(life.TRAILER, git(self.root, "log", "-1", "--format=%B"))
        self.assertEqual((self.root / "prebuilt.plist").read_text(), "prebuilt 1.0; never update")

    def advance_remote(self):
        tree = git(self.root, "rev-parse", f"{self.sha}^{{tree}}")
        commit = life.run("git", "--git-dir", str(self.remote), "commit-tree", tree, "-p", self.sha,
                          cwd=self.root, data="competing writer\n")
        git(self.root, "--git-dir", str(self.remote), "update-ref", "refs/heads/selected", commit)
        return commit

    def test_branch_moved_since_dispatch(self):
        other = self.advance_remote()
        with self.assertRaisesRegex(ValueError, "moved"):
            life.bump(self.root, "patch")
        self.assertEqual(git(self.root, "rev-parse", "HEAD"), self.sha)
        self.assertEqual(life.remote_ref(self.root, "refs/heads/selected"), other)

    def test_branch_races_before_push_negotiation(self):
        original_run = life.run
        for mutation in ("advance", "delete", "rewind", "same-head"):
            with self.subTest(mutation=mutation):
                git(self.root, "reset", "--soft", self.sha)
                # Restore fixture sources without destructive checkout/reset.
                shutil.copyfile(FIXTURES / "project.pbxproj", self.root / life.PROJECT)
                shutil.copyfile(FIXTURES / "Info.plist", self.root / life.PLIST)
                git(self.root, "add", str(life.PROJECT), str(life.PLIST))
                git(self.root, "--git-dir", str(self.remote), "update-ref",
                    "refs/heads/selected", self.sha)
                race_target = []

                def racing_run(*args, **kwargs):
                    if "push" in args and "--no-follow-tags" in args:
                        if mutation == "advance":
                            race_target.append(self.advance_remote())
                        elif mutation == "delete":
                            git(self.root, "--git-dir", str(self.remote), "update-ref",
                                "-d", "refs/heads/selected")
                            race_target.append(None)
                        elif mutation == "rewind":
                            ancestor = git(self.root, "rev-parse", f"{self.sha}^")
                            git(self.root, "--git-dir", str(self.remote), "update-ref",
                                "refs/heads/selected", ancestor)
                            race_target.append(ancestor)
                        else:
                            original_run("git", "push", "--no-follow-tags", "origin",
                                         "HEAD:refs/heads/selected", cwd=self.root)
                            race_target.append(git(self.root, "rev-parse", "HEAD"))
                    return original_run(*args, **kwargs)

                with patch.object(life, "run", side_effect=racing_run):
                    with self.assertRaises(subprocess.CalledProcessError):
                        life.bump(self.root, "patch")
                self.assertEqual(len(race_target), 1)
                self.assertEqual(life.remote_ref(self.root, "refs/heads/selected"), race_target[0])

    def test_tag_selection_and_wrong_sha_rejected(self):
        with patch.dict(os.environ, {"GITHUB_REF": "refs/tags/v7.8.9"}):
            with self.assertRaisesRegex(ValueError, "branch"):
                life.bump(self.root, "patch")
        with patch.dict(os.environ, {"GITHUB_SHA": "b" * 40}):
            with self.assertRaisesRegex(ValueError, "immutable"):
                life.bump(self.root, "patch")

    def test_real_bare_tag_collision(self):
        git(self.root, "--git-dir", str(self.remote), "update-ref", "refs/tags/v7.8.9", self.sha)
        with patch.object(life, "api") as api:
            with self.assertRaisesRegex(ValueError, "tag .* already"):
                life.available(self.root, REPO, "v7.8.9")
            api.assert_not_called()

    def test_same_sha_tag_creation_race_retains_tag_and_creates_no_release(self):
        for asset in ("fixture.zip", "fixture.dmg"):
            (self.root / asset).write_bytes(b"fixture")
        calls = []

        def fake_api(repo, method, suffix, payload=None):
            calls.append((method, suffix))
            if method == "GET":
                return []
            if suffix == "git/refs":
                # An external writer won after the final list/ref check.
                git(self.root, "--git-dir", str(self.remote), "update-ref",
                    "refs/tags/v7.8.9", self.sha)
                git(self.root, "--git-dir", str(self.remote), "update-ref",
                    "refs/tags/v7.8.9", self.sha, "0" * 40)
            self.fail("Release creation must not run after tag race")

        with patch.dict(os.environ, {"GITHUB_REPOSITORY": REPO}), \
                patch.object(life, "api", side_effect=fake_api):
            with self.assertRaises(subprocess.CalledProcessError):
                life.publish(self.root, ["fixture.zip", "fixture.dmg"])
        self.assertEqual(life.remote_ref(self.root, "refs/tags/v7.8.9"), self.sha)
        self.assertEqual(calls, [("GET", "releases?per_page=100&page=1"), ("POST", "git/refs")])


class PublicationTests(SourceFixture):
    def setUp(self):
        super().setUp()
        self.environment = patch.dict(os.environ, {"GITHUB_SHA": SHA, "GITHUB_REPOSITORY": REPO})
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def test_paginated_draft_collision_and_valid_pages(self):
        first = [release(f"v0.0.{i}") for i in range(100)]
        for second in ([release("v7.8.9", draft=True)], [], [release("v0.1.0")]):
            with self.subTest(second=second), patch.object(life, "remote_ref", return_value=None), \
                    patch.object(life, "api", side_effect=[first, second]) as api:
                if second and second[0]["draft"]:
                    with self.assertRaisesRegex(ValueError, "including drafts"):
                        life.available(self.root, REPO, "v7.8.9")
                else:
                    life.available(self.root, REPO, "v7.8.9")
                self.assertEqual(api.call_args_list[-1].args,
                                 (REPO, "GET", "releases?per_page=100&page=2"))

    def test_malformed_pages_fail_closed(self):
        bad_pages = ({}, None, "[]", [None], [{}], [{"tag_name": "v0.0.1"}],
                     [{**release("v0.0.1"), "draft": "false"}],
                     [{**release("v0.0.1"), "id": True}])
        for page in bad_pages:
            with self.subTest(page=page), patch.object(life, "remote_ref", return_value=None), \
                    patch.object(life, "api", return_value=page):
                with self.assertRaises(ValueError):
                    life.available(self.root, REPO, "v7.8.9")
        with patch.object(life, "remote_ref", return_value=None), \
                patch.object(life, "api", side_effect=[
                    [release(f"v0.0.{i}") for i in range(100)], {},
                ]):
            with self.assertRaisesRegex(ValueError, "page 2"):
                life.available(self.root, REPO, "v7.8.9")

    def test_api_404_auth_network_and_page2_errors_fail_closed(self):
        first = [release(f"v0.0.{i}") for i in range(100)]
        for message in ("HTTP 404", "HTTP 401", "HTTP 403", "network timeout"):
            for pages in ([], [first]):
                error = subprocess.CalledProcessError(1, ["gh", "api"], stderr=message)
                with self.subTest(message=message, page=len(pages) + 1), \
                        patch.object(life, "remote_ref", return_value=None), \
                        patch.object(life, "api", side_effect=[*pages, error]):
                    with self.assertRaises(subprocess.CalledProcessError):
                        life.available(self.root, REPO, "v7.8.9")
        with patch.object(life, "run", return_value="not json"):
            with self.assertRaises(json.JSONDecodeError):
                life.api(REPO, "GET", "releases?per_page=100&page=1")

    def test_api_uses_explicit_methods_and_json_post(self):
        with patch.object(life, "run", return_value="[]") as command:
            life.api(REPO, "GET", "releases?per_page=100&page=2")
            self.assertEqual(command.call_args.args,
                             ("gh", "api", "--method", "GET",
                              f"repos/{REPO}/releases?per_page=100&page=2"))
        with patch.object(life, "run", return_value='{"id":123}') as command:
            life.api(REPO, "POST", "releases", {"draft": False})
            self.assertIn("--input", command.call_args.args)
            self.assertEqual(json.loads(command.call_args.kwargs["data"]), {"draft": False})

    def test_missing_asset_prevents_remote_mutation(self):
        with patch.object(life, "preflight") as preflight:
            with self.assertRaisesRegex(ValueError, "asset"):
                life.publish(self.root, ["missing.zip", "missing.dmg"])
            preflight.assert_not_called()

    def test_cli_failure_has_recovery_diagnostic_and_nonzero_status(self):
        with patch.object(sys, "argv", ["release_lifecycle.py", "publish", "a.zip", "a.dmg"]), \
                patch.object(life, "publish", side_effect=ValueError("injected upload failure")), \
                contextlib.redirect_stderr(io.StringIO()) as errors:
            self.assertEqual(life.main(), 1)
        self.assertIn("injected upload failure", errors.getvalue())
        self.assertIn("tag, release and assets are retained", errors.getvalue())
        self.assertIn("Do not retry or delete automatically", errors.getvalue())

    def publish_case(self, fail=None):
        for asset in ("fixture.zip", "fixture.dmg"):
            (self.root / asset).write_bytes(b"fixture")
        events = []
        state = {"tag": None, "release": None, "assets": []}

        def fake_api(repo, method, suffix, payload=None):
            events.append((method, suffix, payload))
            if method == "GET":
                if fail == "collision":
                    return [release("v7.8.9", draft=True)]
                return []
            if suffix == "git/refs":
                state["tag"] = payload["sha"]
                return {"ref": payload["ref"], "object": {"sha": SHA, "type": "commit"}}
            if suffix == "releases":
                if fail == "post":
                    raise subprocess.CalledProcessError(1, ["gh", "api"])
                state["release"] = payload
                return {**release("v7.8.9"), **payload}
            self.fail(f"Unexpected mutation: {method} {suffix}")

        def remote(root, ref):
            if fail == "verify" and state["tag"]:
                return "b" * 40
            return state["tag"]

        def command(*args, **kwargs):
            events.append(args)
            self.assertEqual(args, ("gh", "release", "upload", "v7.8.9",
                                    "fixture.zip", "fixture.dmg", "--repo", REPO))
            state["assets"].append("fixture.zip")
            if fail == "upload":
                raise subprocess.CalledProcessError(1, args)
            state["assets"].append("fixture.dmg")
            return ""

        with patch.object(life, "selected_sha", return_value=SHA), \
                patch.object(life, "remote_ref", side_effect=remote), \
                patch.object(life, "api", side_effect=fake_api), \
                patch.object(life, "run", side_effect=command):
            if fail:
                with self.assertRaises((ValueError, subprocess.CalledProcessError)):
                    life.publish(self.root, ["fixture.zip", "fixture.dmg"])
            else:
                self.assertEqual(life.publish(self.root, ["fixture.zip", "fixture.dmg"]), "7.8.9")
        return events, state

    def test_create_only_post_and_upload_order_original_empty_notes(self):
        events, state = self.publish_case()
        self.assertEqual([e[:2] for e in events],
                         [("GET", "releases?per_page=100&page=1"), ("POST", "git/refs"),
                          ("POST", "releases"), ("gh", "release")])
        self.assertEqual(state["release"], {
            "tag_name": "v7.8.9", "target_commitish": SHA, "name": "v7.8.9",
            "draft": False, "prerelease": False, "body": "",
        })
        self.assertEqual(state["assets"], ["fixture.zip", "fixture.dmg"])

    def test_recheck_blocks_new_collision(self):
        events, state = self.publish_case("collision")
        self.assertEqual(len(events), 1)
        self.assertEqual(state, {"tag": None, "release": None, "assets": []})

    def test_verify_failure_retains_tag(self):
        _, state = self.publish_case("verify")
        self.assertEqual(state, {"tag": SHA, "release": None, "assets": []})

    def test_post_failure_retains_tag_without_rollback(self):
        _, state = self.publish_case("post")
        self.assertEqual(state, {"tag": SHA, "release": None, "assets": []})

    def test_upload_failure_retains_release_and_partial_assets(self):
        _, state = self.publish_case("upload")
        self.assertEqual(state["tag"], SHA)
        self.assertIsNotNone(state["release"])
        self.assertEqual(state["assets"], ["fixture.zip"])

    def test_selected_sha_enforced(self):
        with patch.object(life, "run", return_value="b" * 40):
            with self.assertRaisesRegex(ValueError, "immutable"):
                life.preflight(self.root)

    def test_remote_errors_fail_closed(self):
        for response in ("not-a-sha refs/tags/v7.8.9", f"{SHA}\trefs/tags/wrong"):
            with patch.object(life, "run", return_value=response):
                with self.assertRaises(ValueError):
                    life.remote_ref(self.root, "refs/tags/v7.8.9")
        with patch.object(life, "run", side_effect=subprocess.CalledProcessError(1, ["git"])):
            with self.assertRaises(subprocess.CalledProcessError):
                life.remote_ref(self.root, "refs/tags/v7.8.9")


class LiveContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.build = yaml.safe_load((ROOT / ".github/workflows/release.yml").read_text())
        cls.bump = yaml.safe_load((ROOT / ".github/workflows/bump-version.yml").read_text())

    def trigger(self, workflow):
        # PyYAML's YAML 1.1 parser treats the Actions key "on" as True.
        return workflow.get("on", workflow.get(True))

    def test_zero_input_manual_only_build_and_bump_modes(self):
        self.assertEqual(self.build["name"], "Build")
        self.assertEqual(self.trigger(self.build), {"workflow_dispatch": None})
        modes = self.trigger(self.bump)["workflow_dispatch"]["inputs"]
        self.assertEqual(list(modes), ["mode"])
        self.assertEqual(modes["mode"]["options"], ["patch", "minor", "major"])
        self.assertEqual(set(self.trigger(self.bump)), {"workflow_dispatch"})

    def test_selected_sha_all_checkouts_and_repository_wide_serialization(self):
        for workflow in (self.build, self.bump):
            for job in workflow["jobs"].values():
                for step in job["steps"]:
                    if step.get("uses", "").startswith("actions/checkout@"):
                        self.assertEqual(step["with"]["ref"], "${{ github.sha }}")
        self.assertEqual(self.build["concurrency"],
                         {"group": "release-publication", "cancel-in-progress": False})
        self.assertEqual(set(self.build["jobs"]), {"version", "build-windows", "build-macos"})
        self.assertEqual(self.build["jobs"]["build-windows"]["needs"], "version")
        self.assertEqual(self.build["jobs"]["build-macos"]["needs"], ["version", "build-windows"])

    def test_native_gates_and_secret_names_preserved(self):
        jobs = self.build["jobs"]
        self.assertEqual(jobs["build-windows"]["runs-on"], "windows-latest")
        self.assertEqual(jobs["build-macos"]["runs-on"], "macos-latest")
        steps = jobs["build-macos"]["steps"]
        self.assertEqual([s.get("name") for s in steps[1:]], [
            "download windows binaries", "import Developer ID certificate",
            "store notarytool credentials", "build macOS plugin (universal)",
            "verify universal binary", "merge Windows binaries into the bundle",
            "codesign", "package, notarize & staple",
            "recheck and create publication (never replace or roll back)",
        ])
        self.assertFalse(any(s.get("continue-on-error") or s.get("if") == "always()"
                             for j in jobs.values() for s in j["steps"]))
        text = (ROOT / ".github/workflows/release.yml").read_text()
        for command in ('ARCHS="arm64 x86_64"', 'grep -q "arm64"', 'grep -q "x86_64"',
                        "codesign --verify --deep --strict", 'xcrun stapler staple "$DMG_PATH"',
                        'xcrun notarytool submit "$ZIP_PATH"', 'xcrun notarytool submit "$DMG_PATH"',
                        "/p:Platform=x64", "/p:PlatformToolset=v143",
                        "/p:WindowsTargetPlatformVersion=10.0", "if-no-files-found: error"):
            self.assertIn(command, text)
        import re
        self.assertEqual(set(re.findall(r"secrets\.([A-Z_]+)", text)), {
            "APPLE_DEVELOPER_ID_CERTIFICATE", "APPLE_DEVELOPER_ID_CERTIFICATE_PASSWORD",
            "KEYCHAIN_PASSWORD", "NOTARYTOOL_APPLE_ID", "NOTARYTOOL_TEAM_ID", "NOTARYTOOL_PASSWORD",
        })
        self.assertEqual(self.build["env"],
                         {"PRODUCT_NAME": "Log Event", "MACOS_DEPLOYMENT_TARGET": "11.0"})
        self.assertEqual(steps[1]["with"]["name"], "windows-binaries")

    def test_preflight_and_final_recheck_wiring(self):
        version_step = self.build["jobs"]["version"]["steps"][-1]
        self.assertEqual(version_step["run"],
                         "python3 .github/scripts/release_lifecycle.py check")
        final = self.build["jobs"]["build-macos"]["steps"][-1]
        self.assertEqual(final["run"],
                         'python3 .github/scripts/release_lifecycle.py publish "$ZIP_PATH" "$DMG_PATH"')
        for step in (version_step, final):
            self.assertEqual(step["env"]["GH_TOKEN"], "${{ github.token }}")
        bump_steps = self.bump["jobs"]["bump"]["steps"]
        self.assertIn('release_lifecycle.py bump "$MODE"', bump_steps[1]["run"])
        self.assertEqual(bump_steps[1]["env"]["MODE"], "${{ inputs.mode }}")

    def test_no_destructive_publication_or_legacy_typed_tag(self):
        helper = (ROOT / ".github/scripts/release_lifecycle.py").read_text()
        build = (ROOT / ".github/workflows/release.yml").read_text()
        for forbidden in ('"DELETE"', '"PATCH"', "--clobber", '"create",',
                          "--force", "generate-notes", "releases/tags/"):
            self.assertNotIn(forbidden, helper)
        for forbidden in ("inputs.tag", "softprops/", "needs.version.outputs.tag", "tags:"):
            self.assertNotIn(forbidden, build)
        self.assertNotIn('run("git", "tag"', helper)

    def test_live_source_derived_version_and_bump_preserves_non_sources(self):
        current = life.read_version(ROOT)
        self.assertRegex(current, r"^[0-9]+\.[0-9]+\.[0-9]+$")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / life.PROJECT).parent.mkdir()
            shutil.copyfile(ROOT / life.PROJECT, root / life.PROJECT)
            shutil.copyfile(ROOT / life.PLIST, root / life.PLIST)
            before = plistlib.loads((root / life.PLIST).read_bytes())
            bumped = life.bump_source(root, "patch")
            parts = list(map(int, current.split(".")))
            parts[2] += 1
            self.assertEqual(bumped, ".".join(map(str, parts)))
            after = plistlib.loads((root / life.PLIST).read_bytes())
            for key, value in before.items():
                if key not in ("CFBundleShortVersionString", "CFBundleVersion"):
                    self.assertEqual(after[key], value)
            self.assertEqual("CFBundleVersion" in before, "CFBundleVersion" in after)


if __name__ == "__main__":
    unittest.main()
