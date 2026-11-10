"""Actual-source ownership regression; never invokes project/release build phases."""
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
BASELINE = "baa08dc02adcf753cfb4eaa3d795679c7d4f05d1"
SDK_BLOB = "478081f0238f6bc5393222f574bc2656f010b67b"
PICTURE = "4D Plugin API/Classes/C_PICTURE.cpp"
FIXTURES = ("ASCII", "\u65e5", "\U0001f600", "")


def git_blob(data):
    return hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()


def build(source, binary):
    api = source / "4D Plugin API"
    if git_blob((api / "4DPluginAPI.c").read_bytes()) != SDK_BLOB:
        raise AssertionError("Re-audit the bundled SDK before changing the pinned hash")
    subprocess.run([
        "clang++", "-std=c++14", "-x", "objective-c++",
        "-include", "Carbon/Carbon.h", "-I", str(api), "-I", str(api / "Classes"),
        "-fsanitize=address,undefined", "-fno-sanitize=alignment",
        "-fno-omit-frame-pointer", "-g", "-Wno-deprecated-declarations",
        "-Wno-return-type-c-linkage", "-Wno-ignored-attributes", "-Wno-writable-strings",
        str(api / "4DPluginAPI.c"), str(source / "4DPlugin.cpp"),
        *map(str, sorted((api / "Classes").glob("*.cpp"))),
        str(ROOT / ".github/tests/ownership_host.mm"),
        "-framework", "Cocoa", "-framework", "Carbon", "-o", str(binary),
    ], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    symbols = subprocess.check_output(["nm", "-u", str(binary)], text=True)
    for boundary in ("RegisterEventSource", "DeregisterEventSource", "ReportEvent",
                     "RegCreateKey", "RegSetValue", "RegCloseKey", "syslog",
                     "openlog", "os_log", "asl_log"):
        if boundary in symbols:
            raise AssertionError(f"Forbidden platform boundary linked: {boundary}")


def cases():
    for empty in ("allocated", "null"):
        for case in ("path", "copy", "scalar", "dispatch"):
            for text in FIXTURES:
                yield case, text, empty
        for case in ("bytes", "gray", "size", "thumbnail", "arrays"):
            yield case, "", empty
        for case in ("path", "copy", "gray", "size", "thumbnail"):
            yield case + "-handle-failure", "", empty


@unittest.skipUnless(sys.platform == "darwin", "macOS synthetic engine host only")
class OwnershipTests(unittest.TestCase):
    def test_final_sources_and_immutable_baseline(self):
        with tempfile.TemporaryDirectory(prefix="log-event-ownership-") as directory:
            scratch = Path(directory)
            baseline = scratch / "baseline"
            baseline.mkdir()
            archive = scratch / "baseline.tar"
            with archive.open("wb") as stream:
                subprocess.run(["git", "archive", BASELINE], cwd=ROOT, stdout=stream, check=True)
            with tarfile.open(archive) as source:
                source.extractall(baseline, filter="data")
            exemptions = {PICTURE, "README.md"}
            entries = subprocess.check_output(
                ["git", "ls-tree", "-r", "-z", BASELINE], cwd=ROOT,
            ).decode().split("\0")
            for entry in filter(None, entries):
                metadata, name = entry.split("\t", 1)
                mode = metadata.split()[0]
                if name not in exemptions:
                    self.assertEqual((baseline / name).read_bytes(), (ROOT / name).read_bytes(), name)
                self.assertEqual(bool((ROOT / name).stat().st_mode & 0o111), mode == "100755", name)
            results = {"fixed": [0, 0], "baseline": [0, 0]}
            named = {}
            for label, source in (("fixed", ROOT), ("baseline", baseline)):
                binary = scratch / label
                if label == "baseline":
                    binary = scratch / "baseline-host"
                try:
                    build(source, binary)
                except subprocess.CalledProcessError as error:
                    self.fail(error.stdout + error.stderr)
                for case, text, empty in cases():
                    with self.subTest(source=label, case=case, text=text, empty=empty):
                        result = subprocess.run(
                            [str(binary), case, text, empty], capture_output=True, text=True,
                            env={**os.environ, "ASAN_OPTIONS": "detect_leaks=0",
                                 "UBSAN_OPTIONS": "halt_on_error=1"},
                        )
                        output = result.stdout + result.stderr
                        expected_failure = label == "baseline" and case not in ("arrays", "scalar", "dispatch")
                        self.assertEqual(bool(result.returncode), expected_failure, output)
                        if expected_failure:
                            if case.startswith("path") and (text or empty == "allocated"):
                                markers = ("duplicate/unowned string disposal",)
                            elif case.startswith("path") or case == "bytes":
                                markers = ("return must independently retain",)
                            elif case == "copy" and text == "ASCII":
                                markers = ("AddressSanitizer: heap-buffer-overflow",)
                            else:
                                markers = ("unbalanced string allocations", "unbalanced picture references")
                            self.assertTrue(any(marker in output for marker in markers), output)
                            results[label][1] += 1
                            named[case] = named.get(case, 0) + 1
                        else:
                            self.assertIn("strings=0 pictures=0 handles=0", output)
                            results[label][0] += 1
            print(f"Ownership differential: {results}", flush=True)
            print(f"Named baseline failures: {named}", flush=True)
            self.assertEqual(results, {"fixed": [52, 0], "baseline": [18, 34]})


if __name__ == "__main__":
    unittest.main()
