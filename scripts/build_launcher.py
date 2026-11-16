"""Build the .NET Framework Windows GUI and its pinned native keymap bridge."""
from pathlib import Path
import shutil
import subprocess
import os

ROOT = Path(__file__).resolve().parents[1]
FW = ROOT / "third_party/ps2-native-recomp"


def main():
    import project
    compiler = project.compiler_root() / "bin/clang++.exe"
    csc = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Microsoft.NET/Framework64/v4.0.30319/csc.exe"
    if not compiler.is_file() or not csc.is_file():
        raise FileNotFoundError("Bootstrap the pinned compiler and install .NET Framework 4.8 first")
    sdl_header = FW / "third_party/sdl2/include/SDL2/SDL.h"
    sdl_library = FW / "third_party/sdl2/lib/libSDL2.dll.a"
    output = ROOT / "launcher-bin"
    output.mkdir(exist_ok=True)
    subprocess.run([str(compiler), "-std=c++20", "-O2", "-shared", "-static", "-static-libgcc", "-static-libstdc++",
                    "-I" + str(FW / "host"), "-I" + str(FW / "runtime/include"), "-I" + str(sdl_header.parent),
                    str(ROOT / "launcher/controls_bridge.cpp"), str(FW / "host/keymap.cpp"), str(sdl_library),
                    "-o", str(output / "dh_controls.dll")], check=True)
    shutil.copy2(FW / "build/native-dothack-infection/SDL2.dll", output / "SDL2.dll")
    licenses = output / "licenses"
    licenses.mkdir(exist_ok=True)
    shutil.copy2(FW / "LICENSE", licenses / "ps2-native-recomp-LICENSE.txt")
    sdl_license = next((FW / "third_party").rglob("COPYING.txt"), None)
    if sdl_license:
        shutil.copy2(sdl_license, licenses / "SDL2-LICENSE.txt")
    else:
        # The pinned development archive retains SDL's full zlib notice in SDL.h.
        notice = sdl_header.read_text(encoding="utf-8").split("*/", 1)[0] + "*/\n"
        if "permission" not in notice.lower():
            raise ValueError("SDL license notice missing from the pinned header")
        (licenses / "SDL2-LICENSE.txt").write_text(notice, encoding="utf-8")
    sources = sorted((ROOT / "launcher").glob("*.cs"))
    subprocess.run([str(csc), "/nologo", "/target:winexe", "/platform:x64", "/optimize+",
                    "/out:" + str(ROOT / "DotHackInfection.exe"),
                    "/win32manifest:" + str(ROOT / "launcher/app.manifest"),
                    "/reference:System.Windows.Forms.dll", "/reference:System.Drawing.dll",
                    "/reference:System.Core.dll", "/reference:System.Web.Extensions.dll",
                    *map(str, sources)], check=True)
    (ROOT / "DotHackInfection.exe.config").write_text(
        '<?xml version="1.0"?><configuration><startup><supportedRuntime version="v4.0" '
        'sku=".NETFramework,Version=v4.8"/></startup>'
        '<runtime><AppContextSwitchOverrides value="Switch.UseLegacyAccessibilityFeatures=false;'
        'Switch.UseLegacyAccessibilityFeatures.2=false;Switch.UseLegacyAccessibilityFeatures.3=false"/></runtime>'
        '<System.Windows.Forms.ApplicationConfigurationSection>'
        '<add key="DpiAwareness" value="PerMonitorV2"/>'
        '</System.Windows.Forms.ApplicationConfigurationSection></configuration>\n', encoding="utf-8")
    print("Built: " + str(ROOT / "DotHackInfection.exe"))


if __name__ == "__main__":
    main()
