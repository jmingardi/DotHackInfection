"""Privacy and integrity regressions for public releases and private restores."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

import private_inputs as inputs
import release


class ReleaseSafety(unittest.TestCase):
    def test_versions(self):
        self.assertEqual(release.version("0.1.123"), "0.1.123")
        for value in ("1.0.0", "v0.1.1", "0.1.1;echo bad", "0.1.1\n", "../main"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                release.version(value)

    def test_public_source_excludes_private_material(self):
        for name in ("disc.iso", "saves/card1.ps2", "evidence/private.json", "downloads/tool.zip",
                     "third_party/ps2-native-recomp/generated/dothack-infection/unit_0000.cpp",
                     "_private-build-inputs/inputs.zip", "scripts/__pycache__/test.pyc"):
            with self.subTest(name=name):
                self.assertFalse(release.public_source(name))
        for name in ("launcher/LauncherCore.cs", "scripts/private_inputs.py", "docs/WINDOWS_README.txt", ".github/CODEOWNERS"):
            self.assertTrue(release.public_source(name))

    def test_windows_excludes_game_data_and_shader_redistribution(self):
        for name in ("disc.iso", "saves/card1.ps2", "cache/ee-live/private.dll",
                     release.NATIVE + "dxcompiler.dll", release.NATIVE + "dxil.dll",
                     "third_party/ps2-native-recomp/generated/dothack-infection/unit_0000.cpp"):
            self.assertFalse(release.windows_file(name))
        for name in (release.NATIVE + "ps2run.exe", "launcher-bin/dh_controls.dll"):
            self.assertTrue(release.windows_file(name))

    def test_unsafe_paths(self):
        for name in ("../file", "scripts/../../private.py", "C:/file", "/file", "scripts\\file.py", "scripts//file.py"):
            self.assertFalse(release.safe(name))
            self.assertFalse(release.public_source(name))
            self.assertFalse(release.windows_file(name))


class PrivateRestore(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        (self.root / "dependencies.lock.json").write_bytes(b'{"framework":{"patches":["patches/test.patch"]}}\n')
        (self.root / "patches").mkdir()
        (self.root / "patches/test.patch").write_bytes(b"literal patch\n")
        self.files = {f"{inputs.GENERATED.as_posix()}/units.hpp": b"// generated header\n",
                      f"{inputs.GENERATED.as_posix()}/unit_0000.cpp": b"// generated source\n"}
        self.archive = self.root / "inputs.zip"

    def bundle(self, files=None, hashes=None, extra=None):
        files = self.files if files is None else files
        metadata = {"schema": 1, "private": True, "codegen_inputs_sha256": inputs.fingerprints(self.root),
                    "files": hashes or {name: inputs.sha(data) for name, data in files.items()}}
        with zipfile.ZipFile(self.archive, "w") as bundle:
            for name, data in files.items():
                bundle.writestr(name, data)
            bundle.writestr(inputs.MANIFEST, json.dumps(metadata))
            if extra:
                bundle.writestr(extra, b"unexpected")
        return inputs.sha(self.archive.read_bytes())

    def test_restores_checked_sources(self):
        inputs.restore(self.archive, self.bundle(), self.root)
        for name, data in self.files.items():
            self.assertEqual((self.root / name).read_bytes(), data)

    def test_rejects_wrong_archive_checksum(self):
        self.bundle()
        with self.assertRaises(ValueError):
            inputs.validate(self.archive, "0" * 64, self.root)

    def test_rejects_changed_patch(self):
        digest = self.bundle()
        (self.root / "patches/test.patch").write_bytes(b"changed patch\n")
        with self.assertRaises(ValueError):
            inputs.validate(self.archive, digest, self.root)

    def test_lock_line_endings_are_portable(self):
        digest = self.bundle()
        path = self.root / "dependencies.lock.json"
        path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))
        self.assertEqual(inputs.validate(self.archive, digest, self.root), self.files)

    def test_rejects_unlisted_payload(self):
        with self.assertRaises(ValueError):
            inputs.validate(self.archive, self.bundle(extra="retail.elf"), self.root)

    def test_rejects_unsafe_listed_payload(self):
        with self.assertRaises(ValueError):
            inputs.validate(self.archive, self.bundle({"../retail.elf": b"data"}), self.root)

    def test_rejects_modified_member(self):
        with self.assertRaises(ValueError):
            inputs.validate(self.archive, self.bundle(hashes={name: "0" * 64 for name in self.files}), self.root)

    def test_preserves_existing_outputs(self):
        digest = self.bundle()
        path = self.root / next(iter(self.files))
        path.parent.mkdir(parents=True)
        path.write_bytes(b"existing user work")
        with self.assertRaises(ValueError):
            inputs.restore(self.archive, digest, self.root)
        self.assertEqual(path.read_bytes(), b"existing user work")


if __name__ == "__main__":
    unittest.main()
