# Candidate Template

Copy this directory shape into a real candidate directory under `.artifacts` for
full artifacts, and archive lightweight evidence under `docs/research/...` when
a gate closes.

This template is for production working state. Do not copy a filled candidate
directory into Git. Git should receive only the reduced gate evidence, manifests,
reviews, issue summaries, and lightweight source records that prove what
happened.

```text
<candidate-id>/
  candidate-manifest.json
  artifact-manifest.json
  prompt-manifest.json
  gate-status.json
  source-manifest.json
  evidence/
    material_preview_board.png
    clay_board.png
    wireframe_board.png
    ...
  reviews/
    <role>-review.json
```

Use:

```bash
node tools/blender-harness/src/check-artifacts.mjs <candidate-dir> --json
node tools/blender-harness/src/check-gate-status.mjs <candidate-dir> --json
```

`check-artifacts` verifies the required evidence and review prompts exist for the profile and gate.
`check-gate-status` verifies the required reviews and downstream status.

## Storage Rules

| Put here | Do not put here |
|---|---|
| local `.blend` work files | source-of-truth docs that belong in `_assets-src/<asset-id>/` |
| Hunyuan/raw imported models | mini program runtime assets |
| full frame sequences/videos | long-lived archive without SHA256/URL |
| all intermediate boards | the only copy of an approved source |
| failed candidate evidence | secrets, credentials, private keys |

When a gate closes, copy only reduced evidence to Git, for example:

```text
docs/research/<domain>/<asset-id>/<candidate-id>/
  board.png
  audit.json
  reviews/<role>-review.json
  gate-status.json
  README.md
```

If a heavy file must be preserved beyond the local machine, upload it to
CloudBase/COS or GitHub Release and record URL, size, SHA256, provenance, and
runtime/source purpose in the source or asset manifest.
