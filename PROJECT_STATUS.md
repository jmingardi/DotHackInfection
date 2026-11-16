# .hack//INFECTION project status

Updated 2026-11-16. Windows x64 early-game native test build. A continuous
power-on replay passed registration, ALTIMIT, The World login, Mac Anu and
Orca's field tutorial, including combat, healing and party commands. Free
movement and additional field victories have been inspected. First-dungeon entry,
treasure interactions, Aura's scene and subsequent corridor movement passed.
Full campaign compatibility is not established.

Launch **DotHackInfection.exe** for the new Windows GUI (launcher version 0.1.0).
The CMD shortcut and `project.py run` now open that same GUI. Personal cards and preferences remain in
`saves/`; QA uses separate cards. All project files remain in `.Hack Infection/`.
The Resident Evil project is unchanged.

GitHub repositories and access are configured: public
`jmingardi/DotHackInfection` for development/PR merges and private
`jmingardi/DotHackInfection-build-inputs` for the explicitly approved 1.5 MB,
98-file generated C++ snapshot. A read-only, single-repository deploy key is
stored in the public repository's encrypted Actions secrets. Input commit and
ZIP SHA-256 are pinned. Private Actions are disabled. Public main requires PRs,
code-owner review and Linux/Windows source checks; owner bypass is limited to PR
merges. Force pushes/deletion are blocked. Pinned official Actions only, default
read-only tokens, external-contributor workflow approval, no outside collaborators
or self-hosted runners. `RELEASE_PUBLISH_ENABLED=false`: no public binary release.

Local source/input privacy and integrity checks pass (13 tests). The first
extracted portable package passed 26 launcher checks, a bundled-compiler DLL
probe and a fresh-profile/cache 600-frame native boot on D3D12/Windows FXC,
exit 0. It produced its own live-code DLLs without an installed compiler on PATH.
A smaller 120,570,884-byte package retains only the x64 compiler, runtime headers/
libraries and notices; its separate 26-check launcher test, DLL compiler probe and
fresh 600-frame FXC boot also passed, exit 0. ISO, extracted retail
executable, saves and gameplay caches are excluded from both ZIPs. DXC is not
redistributed. Clean hosted build
[43950731680](https://github.com/jmingardi/DotHackInfection/actions/runs/43950731680)
passed source checks, native input/save/VU tests, overlay replacement and transfer
delay regressions/negative controls, launcher checks and both package verifiers.
It created **unpublished draft v0.1.2**, with a 120,570,201-byte Windows ZIP and
matching authored-source ZIP, both with SHA-256 sidecars. Build source commit:
`4f6e0881c22b70590385096e2fcf942b2a3de9b0`. The test helper supports both shared
and directly built runtime libraries. Public PR checks were also verified on
Linux/Windows and bound to the GitHub Actions app. No .hack binary release has
been published. The exact downloaded hosted v0.1.2 asset also passed all 26
launcher checks, the bundled-compiler DLL probe and a fresh-profile/cache
600-frame FXC boot, exit 0. See `qa/GITHUB_RELEASES_2026-11-16.md` for validation.

Graphical launcher added 2026-11-16. It selects and checksum-verifies the supported
ISO, captures keyboard/mouse bindings using the exact pinned runtime keymap,
detects SDL2 controllers, and saves windowed/borderless, 1x-4x resolution and
picture/text filtering preferences. Original aspect/timing and the five existing
runtime compatibility patches are preserved. Ordinary startup invokes the native
game directly without Python/CMD. Preferences persist under saves/launcher.json
and saves/keys.ini, with atomic replacements/backups and external-edit detection.
No memory cards are copied or reset by the launcher. It stays available during
play, captures logs and returns after the game exits.

Launcher QA: 26 core checks passed, covering native keymap rules, reserved keys,
duplicate-binding swaps, alternative/mouse binds, settings persistence/backups,
card preservation, argument quoting, ISO rejection and compatibility environment.
A real-window test changed Cross to G, saved 2x resolution, preserved an unrelated
INI comment and started the native game through Play on a fresh private card.
The runtime applied 2x, reached 600 frames and exited 0; the launcher returned and
closed cleanly. Personal keys.ini hash stayed unchanged. Screenshots were inspected.
Evidence: `evidence/qa-launcher-gui-20261116T173051565/`. Existing controller/save
regression executables also passed. The native game EXE hash remains exactly
`3389e49165fc75984cf917821f5834e8a56378d6634dcb37ca28940e2dd9ea43`.
This is launcher/native-boot QA, not additional campaign or physical-device coverage.
See `qa/LAUNCHER_2026-11-16.md` for reproduction and limitations.

- Framework: `exoteric33/ps2-native-recomp`, MIT, pinned commit
  `3b2b2957bfe2ae6efbe8981ae71be33da6cd4424`.
- Five reproducible runtime patches, applied by bootstrap, are recorded in
  `dependencies.lock.json`: selected VU reference execution, stick-center profile,
  overlay invalidation on bulk writes, IOP disc-error queries and delayed vector
  packet transfers.
- ISO: `Dot Hack Part 1 - Infection (USA).iso`, 2,598,567,936 bytes. SHA-256
  `86f59b3e30012f8b4650c1dc891af9e3aec1663df49120b7eb00c5ebc2672faf`.
  Rehashed after the changes; unchanged.
- Boot: `SLUS_202.67`, 19,223,388 bytes, executable CRC `38A894C6`.
- Native executable: `third_party/ps2-native-recomp/build/native-dothack-infection/ps2run.exe`,
  29,786,624 bytes, SHA-256
  `3389e49165fc75984cf917821f5834e8a56378d6634dcb37ca28940e2dd9ea43`.
  Release build with AVX2 for the current host; renderer observed: D3D12/DXC,
  NVIDIA RTX 3080. Other hosts have not been qualified.
- Pinned LLVM-MinGW, SDL2, wgpu and DXC archives are local and SHA-256 verified.
  Existing Git Bash, CMake, Ninja and Python are reused; no global compiler/PATH
  installation is required. Bootstrap uses Python TLS because Windows Schannel
  failed here; certificate validation was not disabled.
- Initial discovery linked 96 code units and four code windows. Main-processor
  code runs as translated native code; the framework supplies PS2 hardware
  behavior. Missing code can still compile during play. This is not a fully
  static translation or a complete-game support claim.
- Completed EE/VU libraries are reused under `cache/` across QA and personal play.
  Cards, checkpoints and preferences are not merged. New code can still pause on
  first use; earlier personal logs confirmed foreground compile waits around
  14 and 27 seconds. Later QA exposed a separate persistent overlay black screen.
- Cached overlays now invalidate when a bulk disc/SIF transfer overwrites their
  checked instructions. A small native regression and its failing negative
  control verify same-entry overlay replacement, including aliased partial writes.
  The costly `PS2_WINDOW_FULL=1` diagnostic is no longer required for normal play.
- VU1 key `075E2EE535A64DB5` uses reference execution after differential QA found
  incorrect compiled results. The final dungeon scene replay recorded zero
  discrepancies across 65,500 sampled compiled calls. An earlier-binary opening
  replay recorded zero across 576,200 sampled calls.
- Stick center 128 maps to 127 for this title, avoiding its original analog
  routine's cardinal-direction edge case. All four movement directions inspected.
- IOP `CDIOC_GETERROR` now fills the caller's output buffer with the actual disc
  error. This stopped the sound module rejecting successful reads and eliminated
  its repeated preload/error messages in the continuous replay.
- Current-binary continuous opening evidence:
  `evidence/qa-20261115T235251270739Z/`: 67,801 refreshes, exit 0 at the requested
  limit, 226 captures, visible final field, zero invalid-memory warnings.
- A real private-card save was formatted, created, written and loaded from a fresh
  boot. The saved point is ALTIMIT before the first World login (Kite, level 1,
  0:06:03), not a later quest save. Evidence:
  `evidence/qa-20261116T031538537176Z/` verifies the fresh load on the final binary.
- Window, F1 menu, resizing and private keyboard binding tested:
  `evidence/qa-window-20261116T031627Z/`. Input recordings confirm T/right and
  W/forward held and released. Audio reached the host device; a 26.68-second,
  48 kHz stereo capture contains nonzero samples. Two audio underruns were logged
  during this menu/input/resize run; listening quality remains open.
- Selected regression command passes: translation/rejection, malformed discs,
  executable BSS, 62 virtual-controller checks, 87 save-file checks, VU floating
  cleanup, overlay replacement and vector transfer-delay regressions/negative
  controls. An additional upstream
  `ps2vuregtest` target failed to link with duplicate symbols and is not counted.
- The earlier continuous run at `evidence/qa-20261115T175838548078Z/` failed
  visual and invalid-memory review despite reaching its frame limit. It is kept
  as failure evidence. The subsequent full-check diagnostic passed the field
  but its wrapper timing includes a watchdog hold, not just native execution.
- XGKICK transfers can use a two-cycle delay via `PS2_VU_KICK_DELAY=2`, set by the
  launcher. The game writes part of a short packet after issuing its transfer;
  copying it immediately sent stale vertices as register writes and damaged the
  numeric font. Compiled and reference execution now share the delay helper.
  This is an opt-in timing approximation, not a complete GIF FIFO model. Native
  VU libraries carry a new generator fingerprint, so old libraries are rejected.
  `evidence/qa-dungeon-delayed-kick-validation/` has the readable final HUD;
  `evidence/qa-dungeon-kick-negative-control/` reproduces corruption with the same
  binary and inputs when the delay is disabled. Temporary write tracing was removed.
- Physical controller models, completion of the first dungeon, later campaign and subjective audio are
  unverified. Widescreen and altered frame rates are deferred at the user's request.

See [QA_REPORT.md](QA_REPORT.md) for coverage and repeatable commands. Extracted
assets, raw diagnostics, screenshots, compiled code and cards stay local and are
excluded from source sharing. Public authored source and the separately approved
private generated-input snapshot are the only repository uploads;
no .hack binary release has been published.
