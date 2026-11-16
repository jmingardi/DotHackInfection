"""Pack/restore only private generated C++ inputs, with hashes and codegen pins."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import zipfile

ROOT = Path(__file__).resolve().parents[1]
GENERATED = Path("third_party/ps2-native-recomp/generated/dothack-infection")
MANIFEST = "manifest.json"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def fingerprints(root=ROOT):
    lock = json.loads((root / "dependencies.lock.json").read_text())
    names = ["dependencies.lock.json", *lock["framework"]["patches"]]
    return {name: sha((root / name).read_bytes() if name.endswith('.patch') else
                      (root / name).read_bytes().replace(b'\r\n', b'\n')) for name in names}


def allowed(name):
    path = PurePosixPath(name)
    return (path.parent.as_posix() == GENERATED.as_posix()
            and re.fullmatch(r"[A-Za-z0-9_]+\.(cpp|hpp)", path.name) is not None)


def validate(archive, expected, root=ROOT):
    if not re.fullmatch(r"[0-9a-f]{64}", expected) or sha(archive.read_bytes()) != expected:
        raise ValueError("Private input ZIP SHA-256 mismatch")
    with zipfile.ZipFile(archive) as bundle:
        names = bundle.namelist()
        if len(names) != len(set(names)):
            raise ValueError("Duplicate ZIP entries")
        if sum(i.file_size for i in bundle.infolist()) > 100_000_000:
            raise ValueError("Private input archive is too large")
        metadata = json.loads(bundle.read(MANIFEST))
        if metadata.get("schema") != 1 or metadata.get("private") is not True:
            raise ValueError("Not a private generated-source bundle")
        if metadata.get("codegen_inputs_sha256") != fingerprints(root):
            raise ValueError("Dependencies/patches changed: regenerate private inputs locally")
        files = metadata["files"]
        if not files or set(names) != set(files) | {MANIFEST} or not all(map(allowed, files)):
            raise ValueError("Unexpected private input path")
        if not any(PurePosixPath(n).name == "units.hpp" for n in files):
            raise ValueError("Generated API header is missing")
        contents = {name: bundle.read(name) for name in files}
        if any(sha(data) != files[name] for name, data in contents.items()):
            raise ValueError("Private input file hash mismatch")
        return contents


def pack(archive, root=ROOT):
    files = {}
    for item in sorted((root / GENERATED).iterdir()):
        name = item.relative_to(root).as_posix()
        if not item.is_file() or item.is_symlink() or not allowed(name):
            raise ValueError(f"Unexpected generated file: {name}")
        files[name] = item.read_bytes()
    archive.parent.mkdir(parents=True, exist_ok=True)
    manifest = {"schema": 1, "private": True, "codegen_inputs_sha256": fingerprints(root),
                "files": {name: sha(data) for name, data in files.items()}}
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as bundle:
        for name, data in files.items():
            bundle.writestr(name, data)
        bundle.writestr(MANIFEST, json.dumps(manifest, indent=2) + "\n")
    digest = sha(archive.read_bytes())
    validate(archive, digest, root)
    archive.with_suffix(".zip.sha256").write_text(f"{digest}  {archive.name}\n", encoding="ascii")
    print(json.dumps({"path": str(archive), "bytes": archive.stat().st_size,
                      "generated_files": len(files), "sha256": digest}))


def restore(archive, expected, root=ROOT):
    contents = validate(archive, expected, root)
    # Validate all destinations before writing anything; never overwrite a local build.
    for name in contents:
        target = root / name
        if not target.resolve().is_relative_to(root.resolve()) or target.exists():
            raise ValueError(f"Refusing existing or unsafe output: {name}")
    directory = root / GENERATED
    if directory.exists() and any(directory.iterdir()):
        raise ValueError("Generated directory must be empty")
    for name, data in contents.items():
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    print(f"Restored {len(contents)} private generated source files")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=["pack", "restore"])
    parser.add_argument("archive", type=Path)
    parser.add_argument("--sha256")
    args = parser.parse_args()
    if args.operation == "pack":
        pack(args.archive)
    else:
        restore(args.archive, args.sha256 or "")
