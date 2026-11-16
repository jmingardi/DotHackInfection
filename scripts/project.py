"""Local Windows setup for .hack//INFECTION using a pinned upstream framework."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import urllib.request
import zipfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")
ROOT = Path(__file__).resolve().parents[1]
FW = ROOT / "third_party/ps2-native-recomp"
LOCK = json.loads((ROOT / "dependencies.lock.json").read_text())
EVIDENCE = ROOT / "evidence"
NAME = "dothack-infection"
ISO = ROOT / "Dot Hack Part 1 - Infection (USA).iso"


def run(args, log=None, env=None):
    print(subprocess.list2cmdline([str(a) for a in args]), flush=True)
    if log:
        EVIDENCE.mkdir(exist_ok=True)
        with (EVIDENCE / log).open("w", encoding="utf-8") as stream:
            result = subprocess.run(args, cwd=FW, env=env, stdout=stream, stderr=subprocess.STDOUT)
        if result.returncode:
            print((EVIDENCE / log).read_text(encoding="utf-8", errors="replace")[-7000:])
        result.check_returncode()
    else:
        subprocess.run(args, cwd=FW, env=env, check=True)


def verify_framework():
    if not FW.exists():
        FW.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "clone", "--no-checkout", "--depth", "1", LOCK["framework"]["url"], str(FW)], check=True)
        subprocess.run(["git", "-C", str(FW), "fetch", "--depth", "1", "origin", LOCK["framework"]["commit"]], check=True)
        subprocess.run(["git", "-C", str(FW), "checkout", "--detach", LOCK["framework"]["commit"]], check=True)
    actual = subprocess.check_output(["git", "-C", str(FW), "rev-parse", "HEAD"], text=True).strip()
    if actual != LOCK["framework"]["commit"]:
        raise ValueError(f"Framework revision changed: {actual}")
    for relative in LOCK["framework"]["patches"]:
        patch = (ROOT / relative).resolve()
        if not patch.is_relative_to(ROOT) or not patch.is_file():
            raise ValueError(f"Invalid framework patch: {relative}")
        command = ["git", "-C", str(FW), "apply"]
        if subprocess.run(command + ["--reverse", "--check", str(patch)], capture_output=True).returncode == 0:
            continue
        subprocess.run(command + ["--check", str(patch)], check=True)
        subprocess.run(command + [str(patch)], check=True)


def compiler_root():
    return ROOT / "toolchains" / LOCK["compiler"]["version"]


def fetch(item, archive):
    archive.parent.mkdir(parents=True, exist_ok=True)
    if not archive.exists():
        partial = archive.with_suffix(archive.suffix + ".part")
        print(f"Downloading {archive.name}", flush=True)
        with urllib.request.urlopen(item["url"], timeout=60) as response, partial.open("wb") as target:
            shutil.copyfileobj(response, target, length=1 << 20)
        partial.replace(archive)
    with archive.open("rb") as source:
        digest = hashlib.file_digest(source, "sha256").hexdigest()
    if digest != item["sha256"]:
        raise ValueError(f"Archive checksum mismatch: {archive.name}")
    return digest


def bootstrap():
    verify_framework()
    item = LOCK["compiler"]
    archive = ROOT / "downloads" / (item["version"] + ".zip")
    digest = fetch(item, archive)
    marker = compiler_root() / ".verified-sha256"
    if not marker.exists() or marker.read_text().strip() != digest:
        print("Extracting verified compiler inside the project", flush=True)
        destination = (ROOT / "toolchains").resolve()
        with zipfile.ZipFile(archive) as bundle:
            for name in bundle.namelist():
                resolved = (destination / name).resolve()
                if not resolved.is_relative_to(destination):
                    raise ValueError(f"Unsafe compiler archive path: {name}")
            bundle.extractall(destination)
        marker.write_text(digest + "\n")
    print("Pinned compiler ready", flush=True)
    # Upstream's fetch scripts accept verified offline archives here. Python's
    # TLS works on hosts where curl/Schannel cannot acquire credentials.
    for asset in LOCK["archives"]:
        fetch(asset, FW / "downloads" / asset["file"])


def environment():
    env = dict(os.environ)
    git = Path(shutil.which("git")).resolve()
    git_root = git.parent.parent
    bash = git_root / "bin/bash.exe"
    if not bash.exists():
        raise ValueError("Git Bash is required")
    compiler = compiler_root() / "bin"
    temporary = ROOT / "toolchains/tmp"
    temporary.mkdir(exist_ok=True)
    env["PATH"] = str(compiler) + os.pathsep + str(git_root / "usr/bin") + os.pathsep + env["PATH"]
    env.update(CXX=(compiler / "clang++.exe").as_posix(), CC=(compiler / "clang.exe").as_posix(),
               PS2_JOBS="2", CMAKE_BUILD_PARALLEL_LEVEL="2", PYTHONUTF8="1", TMPDIR=temporary.as_posix(),
               TEMP=str(temporary), TMP=str(temporary))
    return bash, env


def runtime_environment():
    """Reuse completed, runtime-validated code across personal play and QA."""
    _, env = environment()
    cache = ROOT / "cache"
    if not cache.resolve().is_relative_to(ROOT):
        raise ValueError("Code cache escaped the project")
    imported = []
    sources = [ROOT / "saves", FW / f"games/{NAME}"]
    # Older isolated runs kept their own caches; only completed libraries move
    # into the shared cache. Cards, checkpoints, profiles and work files stay put.
    sources.extend(sorted(EVIDENCE.glob("qa-*")))
    for kind in ("ee-live", "vu1-live"):
        destination = cache / kind
        destination.mkdir(parents=True, exist_ok=True)
        for source in sources:
            folder = source / kind
            if not folder.is_dir():
                continue
            libraries = list(folder.glob("*.dll"))
            metadata = list(folder.glob("*.mark")) if kind == "ee-live" and libraries else []
            for library in sorted(libraries + metadata):
                target = destination / library.name
                if target.exists():
                    if (library.suffix == ".mark" and target.read_text().startswith("fast")
                            and not library.read_text().startswith("fast")):
                        shutil.copy2(library, target)
                    continue
                # A final library appears only after its compile/link completes.
                # The runtime independently checks its exported ABI/program stamp
                # and code bytes before use; filenames alone never authorize it.
                shutil.copy2(library, target)
                imported.append({"source":library.relative_to(ROOT).as_posix(),
                                 "destination":target.relative_to(ROOT).as_posix(),
                                 "sha256":hashlib.sha256(target.read_bytes()).hexdigest()})
    if imported:
        (cache / "last-import.json").write_text(json.dumps(imported, indent=2) + "\n")
        print(f"Reused {len(imported)} code cache files; personal saves unchanged", flush=True)
    env.update(PS2_EE_LIVE=(cache / "ee-live").as_posix(),
               PS2_VU_LIVE=(cache / "vu1-live").as_posix(),
               PS2_VU_CXX=(compiler_root() / "bin/clang++.exe").as_posix(),
               PS2_EE_LIVE_JOBS="2",
               PS2_PAD_STICK_CENTER="127",
               PS2_VU_KICK_DELAY="2",
               PS2_VU_INTERPRET_KEYS="075E2EE535A64DB5")
    return env


def build(frames=1200, rounds=2):
    verify_framework()
    if not ISO.is_file():
        raise ValueError("Expected local ISO is missing")
    bootstrap()
    # port.sh owns only these validated, private generated/build locations.
    # It never receives the original image as a writable output path.
    for relative in (f"games/{NAME}", f"games/{NAME}/patched", f"games/{NAME}/unpack",
                     f"generated/{NAME}", f"build/native-{NAME}",
                     "third_party/sdl2/SDL2-2.32.10", "third_party/dxc/unpacked"):
        if not (FW / relative).resolve().is_relative_to(FW.resolve()):
            raise ValueError("Build output escaped the framework checkout")
    bash, env = environment()
    run([str(bash), "scripts/port.sh", NAME, ISO.as_posix(), "--native-only",
         "--frames", str(frames), "--rounds", str(rounds)], log="build.log", env=env)
    build_launcher()


def build_launcher():
    subprocess.run([sys.executable, str(ROOT / "scripts/build_launcher.py")], cwd=ROOT, check=True)


def launch(direct=False):
    if not direct:
        launcher = ROOT / "DotHackInfection.exe"
        if not launcher.is_file():
            raise ValueError("Launcher is missing; run python scripts/project.py build-launcher first")
        subprocess.Popen([str(launcher)], cwd=ROOT)
        return
    executable = FW / f"build/native-{NAME}/ps2run.exe"
    if not executable.exists():
        raise ValueError("Native executable is missing; run build first")
    env = runtime_environment()
    env["PS2_WINDOW_TITLE"] = ".hack//INFECTION Recompiled (Experimental)"
    saves = ROOT / "saves"
    saves.mkdir(exist_ok=True)
    run([str(executable), "--disc", str(ISO), "--window", "--game-dir", str(saves),
         "--memcard", str(saves / "card1.ps2")], env=env)


def play(frames=1200, moves="", source=None):
    env = runtime_environment()
    command = [sys.executable, "scripts/play.py", "--game", NAME, "--frames", str(frames),
               "--headless", "--moves", moves, "--width", "512", "--shots", "8"]
    if source:
        path = Path(source).resolve()
        if not path.is_relative_to(ROOT) or not path.is_file():
            raise ValueError("QA checkpoint must be inside this project")
        command.extend(["--from", str(path)])
    try:
        run(command, env=env)
    finally:
        log = FW / f"games/{NAME}/play/last-run.log"
        if log.exists():
            history = EVIDENCE / "play-history"
            history.mkdir(parents=True, exist_ok=True)
            tag = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
            shutil.copy2(log, history / (tag + ".log"))
            (history / (tag + ".json")).write_text(json.dumps({
                "command":command, "moves":moves, "from":str(source),
                "frames_requested":frames,
                "scope":"Scripted input; visual review required; no automatic gameplay verdict"
            }, indent=2) + "\n")


def test():
    _, env = environment()
    checks = [
        [sys.executable, "scripts/test_live_image.py", "build/tools/eerecomp.exe"],
        [sys.executable, "tests/disc_py_input.py"],
        [sys.executable, "tests/elf_bss.py", "--recompiler", "build/tools/eerecomp.exe"],
    ]
    for index, command in enumerate(checks):
        name = f"checks-{index}.log"
        run(command, log=name, env=env)
        print((EVIDENCE / name).read_text(encoding="utf-8", errors="replace")[-1200:])
    targets = ("ps2vucleanuptest", "ps2savetest", "ps2padtest")
    run(["ninja", "-C", str(FW / f"build/native-{NAME}"), "-j", "2", *targets],
        log="build-selected-tests.log", env=env)
    for target in targets:
        run([str(FW / f"build/native-{NAME}/{target}.exe")], log=target + ".log", env=env)
        print(f"{target}: passed", flush=True)
    cache_text = (FW / f"build/native-{NAME}/CMakeCache.txt").read_text()
    configured_runtime = re.search(r"^PS2_RUNTIME_LIB:FILEPATH=(.*)$", cache_text, re.M)
    library = (configured_runtime.group(1).strip() if configured_runtime else "") or str(
        FW / f"build/native-{NAME}/libps2runtime.a")
    if not Path(library).is_file():
        raise FileNotFoundError(f"Build the native runtime before testing: {library}")
    wgpu = re.search(r"^PS2_WGPU_DIR:PATH=(.+)$", cache_text, re.M).group(1)
    executable = ROOT / "toolchains/tmp/overlay-test.exe"
    run([str(compiler_root() / "bin/clang++.exe"), "-std=c++20", "-O2",
         "-I" + str(FW / "runtime/include"), "-I" + str(FW / "runtime/src"),
         str(ROOT / "qa/native_overlay.cpp"), library, str(Path(wgpu) / "lib/libwgpu_native.a"),
         "-lsynchronization", "-lws2_32", "-luserenv", "-lntdll", "-lpthread", "-lm", "-o", str(executable)],
        log="build-overlay-test.log", env=env)
    run([str(executable)], log="overlay-test.log", env=env)
    negative = subprocess.run([str(executable), "without-notification"], env=env, capture_output=True, text=True)
    (EVIDENCE / "overlay-negative-control.log").write_text(negative.stdout + negative.stderr)
    if negative.returncode != 1 or "stale overlay after DMA" not in negative.stdout:
        raise RuntimeError("Overlay regression negative control did not reproduce the old failure")
    print("Overlay replacement regression and negative control passed", flush=True)
    kick_test = ROOT / "toolchains/tmp/kick-delay-test.exe"
    run([str(compiler_root() / "bin/clang++.exe"), "-std=c++20", "-O2", "-msse4.1",
         "-I" + str(FW / "runtime/include"), str(ROOT / "qa/native_kick_delay.cpp"),
         "-o", str(kick_test)], log="build-kick-delay-test.log", env=env)
    run([str(kick_test)], log="kick-delay-test.log", env=env)
    print("XGKICK delay regression and negative control passed", flush=True)


def qa(frames=1800, presses=None, card=None, axes=None):
    executable = FW / f"build/native-{NAME}/ps2run.exe"
    if not executable.exists():
        raise ValueError("Build the native executable first")
    output = EVIDENCE / datetime.now(timezone.utc).strftime("qa-%Y%m%dT%H%M%S%fZ")
    output.mkdir(parents=True)
    (output / "frames").mkdir()
    if card:
        source = Path(card).resolve()
        if not source.is_relative_to(ROOT) or not source.is_file():
            raise ValueError("QA seed card must be inside this project")
        shutil.copy2(source, output / "qa.ps2")
    env = runtime_environment()
    env["PS2_EE_LIVE_KEEP"] = "1"
    command = [str(executable), "--disc", str(ISO), "--frames", str(frames),
               "--game-dir", str(output), "--memcard", str(output / "qa.ps2"),
               "--frames-dir", str(output / "frames"), "--frame-every", "300",
               "--save-state", f"{frames-1}:{output / 'end.state'}"]
    for press in presses or ["300:start", "600:cross", "900:cross", "1200:cross", "1500:cross"]:
        command.extend(["--press", press])
    for axis in axes or []:
        command.extend(["--axis", axis])
    receipt = {"command":command, "native_sha256":hashlib.sha256(executable.read_bytes()).hexdigest(),
               "frames_requested":frames, "scope":"Isolated boot/menu/playtest; screenshots require review"}
    receipt["runtime_profile"] = {key:env.get(key) for key in
        ("PS2_WINDOW_FULL", "PS2_PAD_STICK_CENTER", "PS2_VU_INTERPRET_KEYS", "PS2_VU_KICK_DELAY", "PS2_VU_CHECK")}
    (output / "session.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(f"QA evidence: {output}", flush=True)
    started = time.monotonic()
    with (output / "runtime.log").open("w", encoding="utf-8") as stream:
        process = subprocess.Popen(command, cwd=output, env=env, stdout=stream, stderr=subprocess.STDOUT,
                                   creationflags=subprocess.CREATE_NO_WINDOW)
        receipt["pid"] = process.pid
        (output / "session.json").write_text(json.dumps(receipt, indent=2) + "\n")
        try:
            process.wait(timeout=1800)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
            receipt["timeout"] = True
    receipt.update(exit_code=process.returncode, elapsed_seconds=time.monotonic()-started,
                   screenshot_count=len(list((output / "frames").glob("*.ppm"))))
    runtime = (output / "runtime.log").read_text(encoding="utf-8", errors="replace")
    from PIL import Image
    captures = sorted((output / "frames").glob("*.ppm"))
    receipt["final_capture_nonblack"] = bool(captures and Image.open(captures[-1]).getbbox())
    receipt["invalid_memory_accesses"] = len(re.findall(r"\[mem\] (?:read|write) at unmapped", runtime))
    stops = re.findall(r"\[ee\] stopped after (\d+) frames[^\n]*: ([^\r\n]+)", runtime)
    receipt["stop"] = {"frames":int(stops[-1][0]), "reason":stops[-1][1]} if stops else None
    receipt["completed"] = bool(process.returncode == 0 and stops
                                and int(stops[-1][0]) >= frames
                                and stops[-1][1] == "frame limit reached"
                                and receipt["screenshot_count"] > 0
                                and receipt["final_capture_nonblack"]
                                and receipt["invalid_memory_accesses"] == 0)
    (output / "report.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2), flush=True)
    if not receipt["completed"]:
        raise RuntimeError("QA failed completion, blank-frame or invalid-memory checks; inspect runtime.log")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["bootstrap", "build", "build-launcher", "run", "test", "qa", "play"])
    parser.add_argument("--direct", action="store_true", help="Skip the graphical launcher for an explicit developer run")
    parser.add_argument("--frames", type=int, default=1200)
    parser.add_argument("--rounds", type=int, default=2)
    parser.add_argument("--press", action="append", help="QA input frame:button[:duration], repeatable")
    parser.add_argument("--qa-card", help="Clone this project-local card for isolated QA; source is preserved")
    parser.add_argument("--moves", default="", help="Upstream playtest moves: frame:button[:duration]")
    parser.add_argument("--from", dest="source", help="Continue a private playtest checkpoint")
    args = parser.parse_args()
    if args.command == "bootstrap":
        bootstrap()
    elif args.command == "build":
        if not 1 <= args.frames <= 36000 or not 1 <= args.rounds <= 8:
            raise ValueError("Invalid exploration limits")
        build(args.frames, args.rounds)
    elif args.command == "build-launcher":
        build_launcher()
    elif args.command == "run":
        launch(args.direct)
    elif args.command == "test":
        test()
    elif args.command == "play":
        if not 1 <= args.frames <= 36000:
            raise ValueError("Invalid playtest frame limit")
        play(args.frames, args.moves, args.source)
    else:
        if not 1 <= args.frames <= 36000:
            raise ValueError("Invalid QA frame limit")
        qa(args.frames, args.press, args.qa_card)


if __name__ == "__main__":
    main()
