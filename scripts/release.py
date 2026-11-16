"""Hosted Windows builds and checked, unpublished release candidates."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import zipfile

import project
import private_inputs

ROOT = project.ROOT
FW = project.FW
DIST = ROOT / "dist"
MANIFEST = "release-manifest.json"
PUBLIC_FILES = {".gitignore", ".gitattributes", "README.md", "PROJECT_STATUS.md",
                "QA_REPORT.md", "SECURITY.md", "CHANGELOG.md", "dependencies.lock.json", "Run Dot Hack Infection.cmd"}
PUBLIC_DIRS = {"scripts", "launcher", "patches", "qa", "docs", "licenses", ".github"}
PUBLIC_SUFFIXES = {".py", ".cs", ".cpp", ".hpp", ".patch", ".md", ".txt", ".ps1", ".json", ".yml", ".manifest"}
NATIVE = "third_party/ps2-native-recomp/build/native-dothack-infection/"
TOOLS = "third_party/ps2-native-recomp/build/tools/"


def version(value):
    if not re.fullmatch(r"0\.[0-9]+\.[0-9]+", value):
        raise ValueError("Use an experimental version such as 0.1.1")
    return value


def safe(name):
    p = PurePosixPath(name)
    return (bool(name) and not name.startswith("/") and "\\" not in name and ":" not in name
            and all(part not in {"", ".", ".."} for part in name.split("/"))
            and p.as_posix() == name)


def public_source(name):
    p = PurePosixPath(name)
    return safe(name) and (name in PUBLIC_FILES or
                          (p.parts[0] in PUBLIC_DIRS and
                           (p.suffix in PUBLIC_SUFFIXES or name == ".github/CODEOWNERS")))


def compiler_file(name):
    """Only the x64 live compiler, headers/libraries and original notices."""
    if not safe(name):
        return False
    p = PurePosixPath(name)
    return (name == "LICENSE.TXT" or name.startswith(("include/", "lib/clang/",
            "x86_64-w64-mingw32/", "share/libc++/")) or
            (p.parent.as_posix() == "bin" and
             (p.name in {"clang++.exe", "clang.exe", "ld.lld.exe", "libclang-cpp.dll", "libc++.dll",
                         "libunwind.dll", "libwinpthread-1.dll"} or p.suffix == ".cfg"
              or re.fullmatch(r"clang-[0-9]+\.exe|libLLVM-[0-9]+\.dll", p.name) is not None)))


def windows_file(name):
    if not safe(name):
        return False
    p = PurePosixPath(name)
    if set(p.parts) & {"saves", "cache", "evidence", "games", "generated", "_private-build-inputs", ".git"}:
        return False
    if p.suffix.lower() in {".iso", ".elf", ".ps2", ".state", ".bin"}:
        return False
    prefix = "toolchains/" + project.LOCK["compiler"]["version"] + "/"
    return (name in {"DotHackInfection.exe", "DotHackInfection.exe.config", "dependencies.lock.json", "README.txt"}
            or name in {NATIVE + "ps2run.exe", NATIVE + "SDL2.dll", TOOLS + "eerecomp.exe",
                        "launcher-bin/dh_controls.dll", "launcher-bin/SDL2.dll"}
            or name.startswith("licenses/") or name.startswith("launcher-bin/licenses/")
            or (name.startswith(prefix) and compiler_file(name[len(prefix):])))


def archive_path(kind, number):
    version(number)
    return DIST / f"DotHackInfection-{number}-{'Windows-x64' if kind == 'windows' else 'source'}.zip"


def checked_archive(path, kind, number):
    sidecar = path.with_suffix(".zip.sha256").read_text(encoding="ascii").split()
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    if sidecar != [digest, path.name]:
        raise ValueError("Release ZIP checksum mismatch")
    with zipfile.ZipFile(path) as bundle:
        names = bundle.namelist()
        if len(names) != len(set(names)) or not all(map(safe, names)):
            raise ValueError("Duplicate or unsafe ZIP entries")
        metadata = json.loads(bundle.read(MANIFEST))
        if metadata.get("schema") != 1 or metadata.get("kind") != kind or metadata.get("version") != number:
            raise ValueError("Release metadata mismatch")
        files = metadata["files"]
        allow = windows_file if kind == "windows" else public_source
        if set(names) != set(files) | {MANIFEST} or not all(map(allow, files)):
            raise ValueError("Unexpected public release contents")
        required = ({"DotHackInfection.exe", "DotHackInfection.exe.config", "dependencies.lock.json", "README.txt",
                     NATIVE + "ps2run.exe", NATIVE + "SDL2.dll", TOOLS + "eerecomp.exe",
                     "launcher-bin/dh_controls.dll", "launcher-bin/SDL2.dll",
                     "toolchains/" + project.LOCK["compiler"]["version"] + "/bin/clang++.exe",
                     "licenses/ps2-native-recomp-LICENSE.txt", "licenses/wgpu-native-LICENSE.txt"}
                    if kind == "windows" else {"README.md", "scripts/release.py", ".github/CODEOWNERS"})
        if not required <= set(files):
            raise ValueError("Required release files are missing")
        for name, expected in files.items():
            with bundle.open(name) as source:
                if hashlib.file_digest(source, "sha256").hexdigest() != expected:
                    raise ValueError(f"Release member checksum mismatch: {name}")
    print(f"Verified {kind} archive: {path.name}", flush=True)


def create_archive(kind, number):
    DIST.mkdir(exist_ok=True)
    path = archive_path(kind, number)
    if path.exists():
        raise ValueError(f"Preserving existing candidate: {path}")
    hashes = {}
    with zipfile.ZipFile(path, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as bundle:
        def add(name, data):
            allow = windows_file if kind == "windows" else public_source
            if name in hashes or not allow(name):
                raise ValueError(f"Unsafe/duplicate release file: {name}")
            hashes[name] = private_inputs.sha(data)
            bundle.writestr(name, data)
        if kind == "source":
            candidates = [ROOT / name for name in PUBLIC_FILES]
            for folder in PUBLIC_DIRS:
                candidates.extend((ROOT / folder).rglob("*"))
            for item in sorted(set(candidates)):
                name = item.relative_to(ROOT).as_posix()
                if item.is_file() and public_source(name) and not item.is_symlink():
                    add(name, item.read_bytes())
        else:
            for name in ["DotHackInfection.exe", "DotHackInfection.exe.config", "dependencies.lock.json",
                         NATIVE + "ps2run.exe", NATIVE + "SDL2.dll", TOOLS + "eerecomp.exe",
                         "launcher-bin/dh_controls.dll", "launcher-bin/SDL2.dll"]:
                add(name, (ROOT / name).read_bytes())
            for item in sorted((ROOT / "launcher-bin/licenses").glob("*.txt")):
                add(item.relative_to(ROOT).as_posix(), item.read_bytes())
            add("licenses/ps2-native-recomp-LICENSE.txt", (FW / "LICENSE").read_bytes())
            notices = sorted((ROOT / "licenses").glob("*.txt"))
            if not notices:
                raise ValueError("Missing third-party license notices")
            for item in notices:
                add(item.relative_to(ROOT).as_posix(), item.read_bytes())
            compiler = project.LOCK["compiler"]
            archive = ROOT / "downloads" / (compiler["version"] + ".zip")
            project.fetch(compiler, archive)
            # Take the x64 live-compiler subset from the checksum-verified archive,
            # never a working toolchain/cache. Keep its original notices. Debuggers,
            # Python, BusyBox, make and other-target sysroots are unnecessary.
            with zipfile.ZipFile(archive) as tools:
                for info in tools.infolist():
                    if not info.is_dir():
                        if not safe(info.filename) or not info.filename.startswith(compiler["version"] + "/"):
                            raise ValueError("Unexpected compiler archive layout")
                        relative = info.filename[len(compiler["version"]) + 1:]
                        if compiler_file(relative):
                            add("toolchains/" + info.filename, tools.read(info))
            add("README.txt", (ROOT / "docs/WINDOWS_README.txt").read_bytes())
        metadata = {"schema": 1, "kind": kind, "version": number,
                    "source_commit": os.environ.get("SOURCE_COMMIT", "local-unpublished"),
                    "framework_commit": project.LOCK["framework"]["commit"], "files": hashes}
        bundle.writestr(MANIFEST, json.dumps(metadata, indent=2) + "\n")
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    path.with_suffix(".zip.sha256").write_text(f"{digest}  {path.name}\n", encoding="ascii")
    checked_archive(path, kind, number)
    print(f"Candidate: {path.stat().st_size:,} bytes", flush=True)
    return path


def build(number):
    project.bootstrap()
    private_inputs.restore(ROOT / "_private-build-inputs/inputs.zip",
                           os.environ.get("RECOMP_BUILD_INPUTS_SHA256", ""))
    bash, env = project.environment()
    subprocess.run([str(bash), "scripts/setup.sh", "--native-only"], cwd=FW, env=env, check=True)
    native = FW / "build/native-dothack-infection"
    subprocess.run(["cmake", "-S", str(FW), "-B", str(native), "-G", "Ninja",
                    "-DCMAKE_BUILD_TYPE=Release", "-DCMAKE_CXX_COMPILER=" + str(project.compiler_root() / "bin/clang++.exe"),
                    "-DCMAKE_CXX_FLAGS=-mavx2 -ffp-contract=off",
                    "-DPS2_GENERATED=" + str(ROOT / private_inputs.GENERATED)], env=env, check=True)
    subprocess.run(["cmake", "--build", str(native), "--parallel", "2", "--target", "ps2run",
                    "ps2padtest", "ps2savetest", "ps2vucleanuptest"], env=env, check=True)
    project.test()
    project.build_launcher()
    profile = ROOT / "evidence/qa-ci-launcher"
    subprocess.run([str(ROOT / "DotHackInfection.exe"), "--profile-dir", str(profile), "--self-test"],
                   cwd=ROOT, check=True, timeout=60)
    report = json.loads((profile / "self-test.json").read_text(encoding="utf-8-sig"))
    if report["passed"] < 26:
        raise ValueError("Launcher self-test report is incomplete")
    print(f"Launcher checks passed: {report['passed']}", flush=True)
    create_archive("windows", number)
    create_archive("source", number)


def create_release(number, publish=False):
    commit = os.environ.get("SOURCE_COMMIT", "")
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("SOURCE_COMMIT must be the full workflow source SHA")
    assets = []
    for kind in ("windows", "source"):
        path = archive_path(kind, number)
        checked_archive(path, kind, number)
        assets.extend([str(path), str(path.with_suffix(".zip.sha256"))])
    tag = "v" + number
    probe = subprocess.run(["git", "ls-remote", "--exit-code", "--tags", "origin", "refs/tags/" + tag],
                           cwd=ROOT, capture_output=True, text=True)
    if probe.returncode != 2:
        raise ValueError("Tag exists or remote lookup failed; refusing to reuse a release tag")
    subprocess.run(["gh", "release", "create", tag, *assets, "--draft", "--prerelease", "--latest=false",
                    "--target", commit, "--title", f".hack//INFECTION {number} (experimental)",
                    "--notes-file", "docs/RELEASE_NOTES.md"], cwd=ROOT, check=True)
    if publish:
        subprocess.run(["gh", "release", "edit", tag, "--draft=false", "--prerelease", "--latest=false"],
                       cwd=ROOT, check=True)
    print("Published experimental prerelease" if publish else "Created unpublished draft release")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=["check", "build", "source", "windows", "create"])
    parser.add_argument("--version", default=os.environ.get("RELEASE_VERSION", ""))
    parser.add_argument("--publish", action="store_true")
    args = parser.parse_args()
    number = version(args.version or f"0.1.{os.environ.get('GITHUB_RUN_NUMBER', '0')}")
    if args.operation == "check":
        if os.environ.get("GITHUB_OUTPUT"):
            with open(os.environ["GITHUB_OUTPUT"], "a") as stream:
                stream.write(f"version={number}\n")
        print(number)
    elif args.operation == "build":
        build(number)
    elif args.operation == "create":
        create_release(number, args.publish)
    else:
        create_archive(args.operation, number)
