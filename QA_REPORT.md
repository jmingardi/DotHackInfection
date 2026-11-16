# .hack//INFECTION baseline QA

Updated 2026-11-16, Windows x64, Direct3D 12/DXC on the local RTX 3080.
Scripted PS2-pad input and posted keyboard messages were used; captures were
inspected. This is early-game coverage, not a complete campaign certification.
Widescreen and altered frame rates are deferred.

| Check | Result and evidence |
| --- | --- |
| Continuous opening from power-on | Final binary passed 67,801 refreshes through registration, ALTIMIT, Mac Anu and Orca's field tutorial. `evidence/qa-20261115T235251270739Z/`: 226 captures, final field inspected, zero invalid-memory warnings. The run was headless and unpaced; its elapsed time is not a display frame-rate measurement. |
| Combat and skills | Basic attacks, Repth healing, party commands, field battle completion and experience awards inspected. |
| Movement | Four cardinal-direction replays inspected after the stick-center fix. |
| Normal memory card | A private card was formatted, game data created and Data01 saved (Kite level 1, 0:06:03). A fresh boot on the final binary loaded that file and returned to ALTIMIT: `evidence/qa-20261116T031538537176Z/`. This save precedes the first World login. |
| Native window | Final binary at `evidence/qa-window-20261116T031627Z/`: normal frame-limit exit, F1 menu opened/closed, resize accepted with a 984 × 721 client area. |
| Keyboard customization | Private `left_right = T` binding loaded with zero configuration errors. Recording shows rightward left-stick input from T for 48 refreshes, then neutral; W produced forward input for 47 refreshes, then neutral. Only the QA process's window received messages. |
| Audio transport | Window run wrote 26.68 seconds of 48 kHz stereo audio with nonzero samples and sent sound to the audio device. Two underruns (about 0.80 seconds total silence) occurred during the menu/input/resize run, with zero samples dropped. Listening quality and long-session synchronization are not verified. |
| Controller protocol | 62 SDL virtual-controller checks passed, including buttons, sticks, trigger pressure, rumble, unplug/replug and a second port. Physical devices remain untested. |
| Selected regressions | Live-image translation/rejection, 10 malformed-disc cases, executable BSS, 87 save-file checks, vector floating-point cleanup, overlay replacement and XGKICK delay passed. Negative controls reproduce stale overlays and reads of a packet before its following store. Delay checks include ordering, boundary draining, cycle wrap and host floating-point mode. |
| Additional upstream target | `ps2vuregtest` failed to link with duplicate symbols; it is not counted as passed. |
| First dungeon | Entry, normal/trapped treasure tutorial, Aura's scene and subsequent corridor movement inspected. `evidence/qa-dungeon-delayed-kick-validation/` passed the scene with readable HP/SP and zero mismatches in 65,500 sampled compiled vector calls. The same binary and route reproduce corrupted digits with the delay disabled at `evidence/qa-dungeon-kick-negative-control/`. |
| Later progression | Completion of the first dungeon and later campaign remain unverified. |

Five framework patches and shared caching address the compatibility issues found
in QA. Patch files and their order are recorded in `dependencies.lock.json`:

- Completed EE/VU caches are shared between QA and normal play. Cards and
  preferences remain separate. New areas can still pause for code compilation.
- VU1 program `075E2EE535A64DB5` uses the framework's reference path after a
  differential replay found mismatches. Other programs retain compiled execution.
- The host maps central stick byte 128 to 127 for this title. The original
  `SetAnalogStick` routine special-cases exactly 128, which otherwise made
  keyboard left/right select the downward direction.
- Bulk SIF/disc writes invalidate cached overlay instances when their checked
  instructions are overwritten. A regression switches two images with a common
  entry instruction, including an aliased partial write. This fixes a persistent
  desktop-to-World black screen reproduced with the prior rotating checks.
- IOP `devctl(CDIOC_GETERROR)` now writes the actual disc error to the caller's
  output buffer. The sound module had successfully read its bytes but rejected
  them because the unimplemented query left stale stack data. Its preload/error
  messages disappeared in the continuous replay. The command identifier was
  checked against the [PS2SDK header](https://ps2dev.github.io/ps2sdk/cdvd-ioctl_8h_source.html).
- The title profile sets `PS2_VU_KICK_DELAY=2`. Original microcode kicks a short
  packet and then writes part of it in the following instruction pair. The prior
  immediate copy consumed old vertex data as A+D writes, changing ZBUF2 and
  overwriting the numeric font during Aura's scene. Both compiled and reference
  execution now share a delayed-copy helper. This is an opt-in approximation of
  concurrent PATH1 reads, not full FIFO timing. See the [XGKICK pipeline reference](https://psi-rockin.github.io/ps2tek/#vu).
  The generator fingerprint changed to reject older native VU caches. Temporary
  write tracing was removed. Local visual comparison: `evidence/dungeon-hud-comparison.png`.

Final executable SHA-256:
`3389e49165fc75984cf917821f5834e8a56378d6634dcb37ca28940e2dd9ea43`.
An earlier binary's continuous opening at `evidence/qa-20261115T221345865038Z/`
also recorded zero mismatches in 576,200 sampled compiled vector calls; that
measurement is retained as earlier evidence, not attributed to the final replay.

The failed continuous run is retained at
`evidence/qa-20261115T175838548078Z/`; its frame-limit exit was not a gameplay
pass: output stayed black after the overlay switch and invalid reads appeared.
A full-validation diagnostic run at `evidence/qa-20261115T180258807274Z/` reached
the field, but was slow. Its wrapper was held beyond the original watchdog
deadline; the report's elapsed time includes that hold and is not a performance
measurement. Normal play uses write invalidation, not that diagnostic override.

Run selected regressions with `python scripts/project.py test` and the fresh-card
opening with `python scripts/qa_opening.py`. A nonblack last capture, expected
frame-limit stop and zero invalid-memory warnings are required by the QA wrapper;
visual review remains necessary. Raw evidence, code caches, extracted game
diagnostics and cards stay local.
