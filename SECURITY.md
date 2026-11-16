# Reporting security issues

Use GitHub's private vulnerability reporting feature when available to report
security issues to the repository owner. Do not include disc images, generated
game source, personal saves, credentials or exploit instructions in public issues.

Public PRs use isolated GitHub-hosted runners and read-only tokens. They do not
receive private build inputs or release secrets. Main merges are owner-controlled.
Review Actions, dependency pins, build scripts and packaging changes before merging:
merged code can run in the trusted release workflow with private input access.

No self-hosted runner or personal access token is required by the pipeline.
The private repository deploy key is read-only and scoped to that repository.
Revoke its deploy key and matching encrypted Actions secret if compromise is
suspected, then generate a replacement and verify the pinned inputs before use.
