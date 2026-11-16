# Hosted release pipeline QA - 2026-11-16

Public development repository: https://github.com/jmingardi/DotHackInfection

Private generated inputs: `jmingardi/DotHackInfection-build-inputs`. The owner
explicitly approved the 1,484,965-byte generated C++ bundle and read-only deploy
key configuration. It contains 98 generated C++/header files and a manifest,
not the ISO, extracted game executable, cards, gameplay caches or local evidence.
Input commit `851e13ddc9340b6ec481ff19566d2f45738663a2`, ZIP SHA-256
`92f949d2bbf0038c9289a56a0f94b52ed13d2c20561f5fb591b74dddf2763aab`.

The private repository was verified private before upload. Deploy key 170096135
is read-only and scoped to that repository. Its private half was generated in
memory and sent directly to the encrypted public Actions secret; it was never
printed, committed or saved as plaintext. No personal access token was stored.
The private repository has Actions disabled. Public Actions uses GitHub-hosted
Windows runners; registered self-hosted runner count is zero.

Main ruleset 27406633 is active: PRs, one code-owner review, stale-review
dismissal, resolved review threads and strict Linux/Windows public-source checks
bound to GitHub Actions app 15368. Force pushes and branch deletion are blocked.
`* @jmingardi` owns all files. Repository-admin bypass is restricted to PR merges
because GitHub forbids self-approval. No outside collaborators were added.
The setup fix was merged in PR #1 only after both required checks passed.

Public Actions requires full-SHA-pinned official GitHub Actions. Default tokens
are read-only, Actions cannot approve PRs, and all external contributors require
fork workflow approval. PR checks receive no private inputs or release secrets.
Release jobs are restricted to this repository's main, with owner-only manual
dispatch. Checkout credentials are not persisted. The release token is supplied
only to the final release command. Windows binaries/private inputs are not
uploaded as public Actions artifacts. New releases are drafts unless the
explicit publication variable is enabled; it remains **false**.

## Verification

- Actionlint passed both workflows. Thirteen privacy/integrity tests passed
  locally and in required Linux/Windows PR checks. Coverage includes unsafe
  paths, unlisted/modified private inputs, dependency drift, portable line
  endings, existing-output preservation and public package exclusions.
- Smaller local portable ZIP: 120,570,884 bytes, SHA-256
  `c6035b27763cacd4000472f30271d5f25e7b309334bbb1cb678daebbe6857f71`.
  Its extracted launcher passed all 26 checks. Its bundled x64 compiler linked
  a C++ DLL with installed compiler directories removed from PATH. A fresh
  profile/cache boot reached 600 frames and exited 0 on D3D12/FXC, compiling two
  new live-code DLLs. Frame 600 was visually inspected (Bandai boot logo).
  Evidence: `dist/portable-slim-qa/evidence/qa-portable-smoke-20261116T202935/`.
- Clean hosted run [43950731680](https://github.com/jmingardi/DotHackInfection/actions/runs/43950731680)
  succeeded from source `4f6e0881c22b70590385096e2fcf942b2a3de9b0`.
  It fetched the pinned private inputs with read-only SSH access, compiled the
  native game and launcher, passed input/executable/save/controller/VU tests,
  overlay replacement and vector-delay regressions/negative controls, launcher
  self-tests and source/Windows ZIP verification.
- The run created **draft v0.1.2** with the 120,570,201-byte Windows ZIP, matching
  authored-source ZIP and both SHA-256 sidecars. No release was published.
  Each package has a per-file hash manifest recording the source commit.
- Downloaded that exact hosted Windows asset and verified its checksum, every
  member hash and recorded source SHA before extraction. Windows ZIP SHA-256:
  `7c9bc401817a688e7c9a3cb8287a7195441f4e6e85a7da378a6bbafa62155fcc`.
  The extracted hosted launcher passed 26 checks, its bundled compiler linked
  the DLL probe, and its native game reached 600 frames on a fresh isolated
  card/cache using D3D12/FXC, exit 0. No personal profile was used.
  Hosted native EXE SHA-256:
  `b0904a2a6359210b41e282d7f65091969dae399f880765d5ee423d4ce7387bcb`.
  Local evidence is under `dist/hosted-v0.1.2/extracted/evidence/` and summarized
  in ignored `evidence/release-pipeline-summary.json`.

Hosted tests have no game ISO or qualified interactive GPU session. Their result
does not establish gameplay or full campaign support. Existing local project QA
reaches the first dungeon; see QA_REPORT.md for actual coverage. Portable packages
use Windows FXC and omit DXC redistribution, unused toolchain utilities, game
images, extracted executables, personal saves and prefilled gameplay caches.
The required compiler subset retains its original notices and comes directly
from the SHA-256-verified pinned archive.
