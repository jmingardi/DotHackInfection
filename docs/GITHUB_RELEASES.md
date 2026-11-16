# GitHub development and releases

Develop and merge PRs in **[jmingardi/DotHackInfection](https://github.com/jmingardi/DotHackInfection)**.
The **private** `jmingardi/DotHackInfection-build-inputs` repository stores a
generated C++ snapshot, not a second development branch. Do not mirror public
PRs into it. Players never need access to it; they provide their own supported ISO.

`main` pushes/merges and owner-started manual runs build on disposable
GitHub-hosted Windows machines. No self-hosted PC is involved. Dependencies,
patches, official Actions, the private input commit and its ZIP checksum are
pinned. The build restores generated source, compiles the native game and GUI,
runs selected native and launcher checks, verifies public ZIP contents, and
attaches Windows/source ZIPs plus SHA-256 checksums directly to a **draft**.
Generated inputs and Windows binaries are not uploaded as public Actions artifacts.
The ISO, extracted executable, saves and gameplay caches are excluded.

Initial publication is disabled: `RELEASE_PUBLISH_ENABLED=false`. Drafts are
visible only to users with repository write access. Inspect the ZIP and smoke
test it with your own ISO before using GitHub's **Publish release** button.
To enable later automatic publication on merges, explicitly set the Actions
repository variable `RELEASE_PUBLISH_ENABLED=true`. This affects future runs,
not drafts that already exist or runs that already sampled the variable.
Each run uses a fresh `0.1.<run number>` version unless manually overridden.
Existing tags/releases/assets are never replaced. Rerun with a new version if
an earlier run already created a tag or partial draft.

The portable ZIP includes a pinned LLVM-MinGW toolchain because additional
code compiles during play. Users run **DotHackInfection.exe**, keep all files
together and install no separate Python/compiler. .NET Framework 4.8, an AVX2
CPU and compatible graphics drivers are required. The ZIP uses Windows FXC;
Microsoft's separate DXC package is not redistributed. Hosted regression checks
do not test graphics/audio or establish campaign compatibility.

## Private input access

The public repository contains only the encrypted Actions secret
`RECOMP_INPUTS_DEPLOY_KEY`. Its matching deploy key grants **read-only access to
this single private repository**. It cannot push or access other repositories.
`RECOMP_BUILD_INPUTS_COMMIT` pins its full commit and
`RECOMP_BUILD_INPUTS_SHA256` pins `inputs.zip`.
The private repository has Actions disabled. No personal access token is stored.

PR checks run on Linux and Windows with a read-only token, without this secret
or the private checkout. Only the protected main release workflow uses private
inputs. Fork workflows require approval for every external contributor;
approval of a PR test run does not merge code or grant write access.

Main requires PRs, code-owner review, fresh approvals and passing public source
checks. Force pushes and deletion are blocked. `CODEOWNERS` assigns all files
to `@jmingardi`. The owner's repository-admin bypass is limited to PR merges:
GitHub does not allow approving one's own PR. The owner can merge their own
checked PR using the admin override. Inspect workflow/build-script changes
carefully before merging: merged code is trusted to build with private inputs.
Only pinned official GitHub Actions are allowed; the default token is read-only
and Actions cannot approve PRs. No outside collaborators are added.

## Refreshing generated inputs

When dependency pins or runtime patches change, regenerate locally with your
supported ISO. The old bundle fails closed if these fingerprints differ.

```powershell
python scripts/project.py build
python scripts/private_inputs.py pack dist/private-inputs/inputs.zip
```

Keep that ZIP private. Replace `inputs.zip` and `inputs.zip.sha256` in the private
repository, commit/push, and update both public input variables to the new
commit and hash. Ordinary launcher/documentation changes can reuse the snapshot.
Do not upload the ISO, extracted executable, cards, caches or local evidence.

To reproduce the hosted build in a **fresh Windows checkout**, configure Git
Bash, Python 3.11+, CMake and Ninja, then obtain the authorized private archive
as `_private-build-inputs/inputs.zip` and set its expected checksum:

```powershell
$env:RECOMP_BUILD_INPUTS_SHA256 = '<verified ZIP SHA-256>'
python -m unittest discover -s scripts -p test_release_pipeline.py -v
python scripts/release.py build --version 0.1.999
```

This refuses to overwrite an existing generated-source directory or candidate
ZIP. It does not publish anything. Development from your own ISO instead uses
the ordinary bootstrap/build commands in README.md.
