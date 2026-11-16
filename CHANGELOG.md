# Changelog

## Release pipeline - 2026-11-16

- Add public development/private generated-input repositories and GitHub-hosted
  Windows builds, using pinned dependencies and read-only private input access.
- Protect main with owner review and Linux/Windows source checks; keep fork checks
  secret-free. Disable publication initially; main merges create draft candidates.
- Build native game/launcher, run selected regressions, verify ZIP contents and
  checksums, then attach Windows/source packages directly to a new draft.
- Bundle only the x64 compiler components needed for code translation during play;
  omit discs, extracted executables, saves, caches and DXC redistribution.
- Support both shared and directly built runtime libraries in developer tests.

## Launcher 0.1.0 - 2026-11-16

- Add a compiled Windows launcher with supported-ISO selection/verification,
  keyboard/mouse rebinding, controller detection, display preferences and Play.
- Reuse the pinned runtime keymap for validation, reserved keys, duplicate swaps,
  defaults and settings serialization. Preserve existing cards, comments and
  preferences; back up replaced settings and reject concurrent external edits.
- Start the existing native EXE directly with the current compatibility/cache
  profile, capture startup logs and return to the launcher when play ends.
- Make the project CMD shortcut and project.py run open the GUI. Retain explicit
  developer direct runs and add a reproducible build-launcher command.
- Verify 26 core checks, actual GUI capture/save/Play, 600-frame native boot,
  unchanged personal bindings and native EXE, and controller/save regressions.
