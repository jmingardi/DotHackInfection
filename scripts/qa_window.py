"""Exercise the owned SDL window, a private key binding, resize and audio output."""
import argparse
import ctypes as ct
from ctypes import wintypes as wt
from datetime import datetime, timezone
import json
import subprocess
import time
from pathlib import Path
import project

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("checkpoint")
args = parser.parse_args()
checkpoint = Path(args.checkpoint).resolve()
if not checkpoint.is_relative_to(project.ROOT) or not checkpoint.is_file():
    raise ValueError("Use a checkpoint inside the project")
folder = project.EVIDENCE / datetime.now(timezone.utc).strftime("qa-window-%Y%m%dT%H%M%SZ")
folder.mkdir()
(folder / "frames").mkdir()
(folder / "keys.ini").write_text("left_right = T\n")
env = project.runtime_environment()
env.pop("PS2_WINDOW_FULL", None)  # exercise write invalidation, not the slow diagnostic override
env.update(PS2_WINDOW_TITLE=".hack input/audio QA", PS2_DUMP_AUDIO=str(folder / "chip.wav"))
# Opening fixture checkpoints are at frame 67800. This test intentionally uses
# that fixture, a private card and a finite run; it never closes another process.
command = [str(project.FW / f"build/native-{project.NAME}/ps2run.exe"), "--disc", str(project.ISO),
           "--window", "--load-state", str(checkpoint), "--frames", "69401",
           "--game-dir", str(folder), "--memcard", str(folder / "qa.ps2"),
           "--record", str(folder / "keyboard.inputs"), "--frames-dir", str(folder / "frames"),
           "--frame-every", "150"]
user = ct.WinDLL("user32", use_last_error=True)
user.GetWindowThreadProcessId.argtypes = [wt.HWND, ct.POINTER(wt.DWORD)]
user.IsWindowVisible.argtypes = [wt.HWND]
user.PostMessageW.argtypes = [wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM]
user.SetWindowPos.argtypes = [wt.HWND, wt.HWND, ct.c_int, ct.c_int, ct.c_int, ct.c_int, wt.UINT]
user.GetClientRect.argtypes = [wt.HWND, ct.POINTER(wt.RECT)]
callback_type = ct.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
user.EnumWindows.argtypes = [callback_type, wt.LPARAM]
receipt = {"command":command, "events":[], "scope":"Posted messages to the QA process's own HWND; no physical controller test"}
started = time.monotonic()
with (folder / "runtime.log").open("w", encoding="utf8") as log:
    process = subprocess.Popen(command, cwd=folder, env=env, stdout=log, stderr=subprocess.STDOUT,
                               creationflags=subprocess.CREATE_NO_WINDOW)
    receipt["pid"] = process.pid
    found = []
    @callback_type
    def find_window(handle, _):
        owner = wt.DWORD()
        user.GetWindowThreadProcessId(handle, ct.byref(owner))
        if owner.value == process.pid and user.IsWindowVisible(handle):
            found.append(handle)
        return True
    try:
        deadline = time.monotonic() + 20
        while not found and process.poll() is None and time.monotonic() < deadline:
            user.EnumWindows(find_window, 0)
            time.sleep(0.1)
        if not found:
            raise RuntimeError("QA window did not appear")
        handle = found[0]
        receipt["hwnd"] = int(handle)
        def key(vk, scan, seconds):
            if process.poll() is not None:
                raise RuntimeError("QA process exited before input checks")
            down = bool(user.PostMessageW(handle, 0x100, vk, (scan << 16) | 1))
            time.sleep(seconds)
            up = bool(user.PostMessageW(handle, 0x101, vk, (scan << 16) | 0xC0000001))
            receipt["events"].append({"virtual_key":vk, "held_seconds":seconds, "queued":down and up})
        ready_deadline = time.monotonic() + 20
        while "[state] loaded frame 67800" not in (folder / "runtime.log").read_text(errors="replace"):
            if process.poll() is not None or time.monotonic() > ready_deadline:
                raise RuntimeError("QA checkpoint did not become ready for keyboard input")
            time.sleep(0.1)
        time.sleep(1)
        key(0x54, 0x14, 0.8)  # T: the private binding for right
        time.sleep(1)
        key(0x57, 0x11, 0.8)  # W: default forward
        time.sleep(1)
        key(0x70, 0x3B, 0.1)  # F1: quick menu
        time.sleep(1)
        key(0x70, 0x3B, 0.1)
        resized = bool(user.SetWindowPos(handle, None, 0, 0, 1000, 760, 0x0002 | 0x0004 | 0x0010))
        time.sleep(0.3)
        rect = wt.RECT()
        user.GetClientRect(handle, ct.byref(rect))
        receipt["resize"] = {"accepted":resized, "client_width":rect.right, "client_height":rect.bottom}
        process.wait(timeout=90)
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()
        receipt.update(exit_code=process.returncode, elapsed_seconds=time.monotonic()-started)
        (folder / "report.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(folder)
print(json.dumps(receipt, indent=2))
if process.returncode:
    raise SystemExit(process.returncode)
