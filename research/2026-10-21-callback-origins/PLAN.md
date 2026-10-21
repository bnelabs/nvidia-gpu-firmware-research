# Callback assignment and value provenance

Recover assignments feeding GPU object +0x41c0 (internal control callback) and
table object +0x38 (entry getter reached by firmware 0x167de40), then trace entry
+0x34 writers. Separate a proven constructor/dataflow chain from raw displacement
matches. Retain unknown indirects, variant selection and runtime state explicitly.
Use copied 615.71.09 RM ELF, exact-release NVIDIA source, retained comparison
sources and bounded CPU-only analysis/emulation. No GPU activity or native target
execution. Do not revisit rejected REA RISC-V lanes or change their ABI gates.

Before edits, full non-Git workspace and diff/ref/status evidence were preserved:
`../nvidia-callback-preserve-20261021-09cClt/workspace.tar.gz`, 234850129 bytes,
SHA-256 `fcbd4bed118a5b22c1b4bad52f7216f3b7fdcb05cf355a8fc32ffe841b73c1d9`.
Starting HEAD/origin/main: d42161f2d6c0531eab3ed0b8c9c539ed52051e7d (includes PR #4).
No reset, clean, stash, commit or push. Earlier packets stay unchanged.
