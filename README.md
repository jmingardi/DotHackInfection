# .hack//INFECTION native recomp investigation

Windows x64 project for the USA PS2 release, `SLUS-20267`, using the local
`Dot Hack Part 1 - Infection (USA).iso`. Actual compatibility and QA outcomes
are recorded in [PROJECT_STATUS.md](PROJECT_STATUS.md).

Double-click **DotHackInfection.exe** to open the graphical launcher. Select
your own supported ISO, configure keyboard/mouse bindings and display settings,
then press **Play**. The launcher is a compiled Windows application; ordinary
startup does not need Python or a command prompt. Keep it in this project folder
with `launcher-bin/`, the runtime and the bundled toolchain. Portable release
ZIPs keep this layout together and need no separate Python/compiler installation.
Windows x64, .NET Framework 4.8, an AVX2 CPU and compatible graphics drivers are
required. Additional code can compile during play, with first-use pauses.

The public development repository is
[jmingardi/DotHackInfection](https://github.com/jmingardi/DotHackInfection).
Develop and merge PRs there. A separate private repository holds generated build
inputs for GitHub-hosted Windows builds; players supply their own supported ISO.
Publishing is initially disabled: main merges create **draft** release candidates.
See [GitHub releases and protections](docs/GITHUB_RELEASES.md).

The Game tab verifies the supported USA SLUS-20267 image before enabling Play.
Controls provides key/mouse capture, alternative bindings and controller detection.
SDL2 controllers connect automatically using their standard layout. Display offers
windowed/borderless fullscreen, 1x-4x internal resolution and picture/text filters.
**Save settings** applies preferences without starting the game; Play saves them
and launches the existing native EXE. Existing cards and key bindings are preserved;
settings replacements keep backups. F1 settings remain available during play.
The launcher returns when the game closes; **Open last log** shows startup details.
The existing `Run Dot Hack Infection.cmd` shortcut now opens this same launcher.

A continuous
opening replay has passed through Mac Anu, Orca's field tutorial and combat.
Further playtests reached the first dungeon, its treasure tutorial, Aura's scene
and corridor movement after that scene, with readable HP/SP.
The normal memory-card save/load path has also been tested on a private QA card.
Full campaign compatibility remains unverified; see [QA_REPORT.md](QA_REPORT.md)
for the exact coverage and remaining checks.

The pinned [ps2-native-recomp](https://github.com/exoteric33/ps2-native-recomp)
framework supplies code generation, the hardware runtime, graphics, sound,
controller input and key configuration. Main-processor code is compiled to
native code; PS2 hardware is provided by the runtime, and missing code may be
translated during play. This does not establish complete game compatibility.

Run these commands from this folder:

```powershell
python scripts/project.py bootstrap
python scripts/project.py build
python scripts/project.py build-launcher
python scripts/project.py test
python scripts/project.py qa --frames 1800
python scripts/project.py run
```

`build` also builds the launcher; `build-launcher` only rebuilds its Windows GUI
and native controls bridge. Development builds require .NET Framework 4.8's C#
compiler (available on this PC) in addition to the pinned LLVM compiler. The GUI
reuses the framework's MIT keymap parser; notices are in `launcher-bin/licenses/`.
`python scripts/project.py run --direct` explicitly skips the GUI for developer
runs. Launcher self-tests and the real-window QA script are documented in
[qa/LAUNCHER_2026-11-16.md](qa/LAUNCHER_2026-11-16.md).

Bootstrap verifies the framework commit and downloads a pinned LLVM-MinGW
compiler and pinned dependency archives, checking their SHA-256 hashes. It
uses the existing Git Bash, CMake, Ninja and Python. No global PATH or compiler
installation is changed. Building can take several minutes. No game files or
reports are uploaded by local development commands. The hosted release pipeline
reads a separately authorized private generated-source snapshot; disc images,
extracted retail executables, saves and local QA evidence are never uploaded.

Builds, translations and framework exploration cards live inside the local
`third_party/ps2-native-recomp` checkout. Ordinary play stores its memory card
and preferences under `saves/`. QA uses new private directories under
`evidence/qa-*/`; its inputs are scripted, and screenshots must be inspected.
The original ISO is read in place. Upstream may create a local hard link to it;
patches operate on extracted executables, not the original image.

The framework's window supports SDL2 controllers and keyboard controls. **F1**
opens the key card/quick menu; bindings are stored in `keys.ini`. Keyboard rebinding, the F1 menu and window resizing have been exercised in the
SDL window. Controller coverage includes 62 checks with virtual SDL controllers;
physical Xbox, PlayStation and Nintendo devices still need hands-on verification.

The framework is MIT licensed; its license and third-party notices remain in
the pinned checkout. This is a local development project, not a public release.

Default keyboard controls: **WASD** moves, **arrow keys** select menu entries,
**Space/Enter** confirms or attacks, **E** cancels, **right mouse** opens the
personal menu (Triangle), **left mouse** opens party commands (Square), **Shift/F**
rotates the camera, **I/K** zooms, **R** resets the camera, **Esc** is Start.
F1 opens the runtime menu and key card. Edit `saves/keys.ini` to customize keys;
the launcher preserves existing preferences. The runtime's mouse labels in the
key card are generic; in-game tutorial instructions use PS2 button names.

Completed translations are reused under `cache/`, including those discovered in
QA. First visits to new code can still pause for compilation. A persistent black
screen caused by stale overlay code was reproduced and fixed by invalidating the
cached overlay when a disc/SIF transfer overwrites its checked instructions.
The launcher also applies a stick-center compatibility profile and uses reference
execution for one vector program that failed differential checks. A two-cycle
vector transfer-delay profile fixes HP/SP corruption after Aura's scene; this is
a title compatibility approximation of concurrent transfers. These five patches
are listed in `dependencies.lock.json`; none modifies the ISO.

To repeat the selected regressions and the continuous opening test:

```powershell
python scripts/project.py test
python scripts/qa_opening.py
```

QA uses fresh cards. `qa/opening-route.json` contains scripted button timings,
not game assets. Logs, extracted diagnostics, screenshots, generated code,
compiled caches and private cards stay local and are excluded from source files.
Use normal DATA saves for durable progress. Experimental runtime checkpoints made
before the compatibility fixes may already contain incorrect game state.
Widescreen and altered frame rates are deferred.
