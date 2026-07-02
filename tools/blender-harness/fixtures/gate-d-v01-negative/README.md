# Gate D v01 Negative Fixture (Golden Reject)

This fixture is a **golden negative**: a real Gate D reduced-animation candidate
that was reviewed and **rejected** by independent visual review. It exists so
that any `blender-harness` gate checker can be tested against a case that must
always resolve to a rejected/blocked outcome. If a future checker implementation
ever reports this candidate as `accepted` or `downstream_allowed: true`, that is
a checker bug, not a fixture bug.

## Provenance

- Source path (full package, 461MB, still lives only in the source worktree —
  see "Source archive still at risk of loss" below):
  `/Users/hhh0x/ai-luodi/jieyanggucheng-ar-gongfucha-v0/docs/research/ar-magnet/gongfucha-v0-production/tiantan-grammar-benchmark/tiantan-replica-v03-contract/gate-d-reduced-animation-candidate-v01/`
- Source repo: `jieyanggucheng-ar-gongfucha-v0`, branch `codex/ar-gongfucha-v0-production`.
- Artifact id: `gate-d-reduced-animation-candidate-v01` (Gate D, 121-frame reduced
  Tiantan V03 animation candidate rendered from the accepted Gate C camera/dragon
  blocking scene).
- Independent visual review session: `019f0d5e-b40d-7623-b0d9-4044aaa02b32`, dated
  2026-06-30, decision **REJECT**.
  - Note: `legacy/acceptance-review.md` and `legacy/manifest.json` additionally
    record the reviewer identity as session `019f1856-0786-7171-ab25-c466e115465f`
    / reviewer "Avicenna" for the same rejection. Both ids are preserved here for
    traceability; treat them as referring to the same rejection event.

## Why it was rejected (core reasons)

Independent visual review scored this candidate:

- motion/camera: 3/5
- edge_ownership: 3/5
- asset_integration_regression: 3/5
- **high_coverage_risk: 1/5**
- source_honesty: 4/5

Core failure: the high/full-coverage alpha frames read as a **low-poly proxy
sphere/tube/blob**, not as a story-motivated organic dragon wipe or VFX
occlusion. Specifically:

- Full-coverage frames **f072, f116, f117** (frame numbers padded as
  `000072`, `000116`, `000117` in `legacy/audit.json`) are called out by name
  in the acceptance review as unacceptable: they read as "low-poly teal sphere
  / tube proxy wipes," not Tiantan-style organic dragon or VFX occlusion.
- The broader high-coverage window is frames 71-75 and 92-121 (see
  `legacy/audit.json` -> `combined.high_coverage_frames`); the dragon proxy
  dominates the image in this window (called out as f096/f121 in
  `legacy/README.md`, and f080/f112/f121 in `legacy/acceptance-review.md`).
- `high_coverage_risk` scored **1/5** — the single worst score in the rubric —
  because the dragon proxy becomes the main occluder in these windows without
  earning that visual weight.
- `source_honesty` scored 4/5 (comparatively fine): the package clearly
  discloses that the dragon is a segmented proxy, not final T05 dragon art, and
  the candidate is explicitly marked blocked pending a new accepted Gate D v02.
- Secondary failure: near-camera railing, grass/vegetation, stage, and temple
  finish are judged not strong enough to survive full 463-frame production.

Blocked as a result of this rejection (per `legacy/acceptance-review.md`):
full 463-frame animation, WeChat runtime validation, and final object-pass/SBS
acceptance. None of these may be unblocked by this candidate.

## Purpose of this fixture

Golden negative input for the Gate D checker (built in a later stage of this
package, at `tools/blender-harness/...`, not part of this fixture). The
checker must always resolve this candidate to a rejected/blocked status:
`downstream_allowed: false`, no required review with `verdict: accept`
sufficient to flip that, and no forbidden-next-output loophole. This fixture
intentionally does **not** include `gate-status.json` or `reviews/*.json` —
those are derived from the `legacy/` data by the checker's author in the next
stage; this fixture only ships the raw legacy evidence they must derive from.

## Source archive still at risk of loss

The full 461MB Gate D v01 package (including `beauty.mp4`, `pass-id.mp4`,
`combined-alpha.mp4`, `sbs-alpha.mp4`, `composite-preview.mp4`, the `frames/`
directory, and `source-scene.blend` / `source-scene.blend1`) still lives only
at:

```
/Users/hhh0x/ai-luodi/jieyanggucheng-ar-gongfucha-v0/docs/research/ar-magnet/gongfucha-v0-production/tiantan-grammar-benchmark/tiantan-replica-v03-contract/gate-d-reduced-animation-candidate-v01/
```

This path is **untracked** in the `jieyanggucheng-ar-gongfucha-v0` git repo
(`git status` reports it as `??`, not gitignored) and is not otherwise
archived. It is easily lost to worktree cleanup, `git clean`, or macOS
`/tmp`-style pruning if that worktree is ever removed. This fixture only
copies ~1MB of lightweight judgment evidence (JSON + markdown + jpg boards);
it does **not** back up the videos, frame sequence, or `.blend` scene files.
If those are needed later (e.g. to re-render or re-audit), copy them out of
that path before the source worktree is deleted.

## What was imported

All files below were copied into `legacy/` unmodified except
`legacy-README.md`, which is the source package's `README.md` renamed to avoid
colliding with this file.

| File | Bytes | SHA-256 |
| --- | --- | --- |
| `legacy/manifest.json` | 79259 | `2df32121b1e6bae7527e5f16612de6d381e53b9a8a2ee840ab38daa5c232bb48` |
| `legacy/audit.json` | 58246 | `96b05bd868387073527964814134d3ac05d80b5d7ced140d33408bb5f1210b3d` |
| `legacy/acceptance-review.md` | 1843 | `a1d18fe54ce30dca116703887b4c45d63ef8ec57c0976734878f025f5bc8b78e` |
| `legacy/legacy-README.md` | 1582 | `48700598b65aced91f3ee5dba61dff297679447bf2fddb3fe9a9c73a24499098` |
| `legacy/review-board.jpg` | 250164 | `9a8bd8bc6cea283ece4ccc889cb71ee55ee214024a91d54661ecd2cc84608605` |
| `legacy/touchdown-integration-diagnosis-board.jpg` | 219304 | `49cd5d5b6cbb6b31dab33bc7fbd7f78a1d93b1384b05006c9bac8cf15ea5aba7` |
| `legacy/gap-board.jpg` | 113971 | `2885800af6e0ed3754990a9e33d3f5a8cd4845994f8fef909d4a96be628d51c4` |
| `legacy/pass-breakdown-board.jpg` | 88233 | `8cb9c60eb9a66b60d3f6798a0a61a423a26e6c4a706d0cc4d9e530cc2b1f7f5e` |
| `legacy/beauty-filmstrip.jpg` | 83683 | `2625a5fe6aba6b3153b42c98732ea69bd2e0d4f89edad963e23fb05b78e3eac1` |
| `legacy/alpha-filmstrip.jpg` | 36776 | `a0dc7d24a7b274adf78510fb25a3b8b8c50d9a78f1789979b867bc50c11740f9` |
| `legacy/pass-id-filmstrip.jpg` | 63977 | `0bd4bd01d8718c25c5a06857022a0c2d94803942fc07182978c728c1d10f863c` |
| `legacy/sbs-filmstrip.jpg` | 50857 | `468d080b9688d5d9b37dd4442c2d5784421900599bbabfb74ee4b5477b7e5ce5` |

**Total: 12 files, ~1.0MB** (`du -sh` reports `1.0M`).

Verify with:

```
cd tools/blender-harness/fixtures/gate-d-v01-negative/legacy
shasum -a 256 -c <(cat <<'EOF'
2df32121b1e6bae7527e5f16612de6d381e53b9a8a2ee840ab38daa5c232bb48  manifest.json
96b05bd868387073527964814134d3ac05d80b5d7ced140d33408bb5f1210b3d  audit.json
a1d18fe54ce30dca116703887b4c45d63ef8ec57c0976734878f025f5bc8b78e  acceptance-review.md
48700598b65aced91f3ee5dba61dff297679447bf2fddb3fe9a9c73a24499098  legacy-README.md
9a8bd8bc6cea283ece4ccc889cb71ee55ee214024a91d54661ecd2cc84608605  review-board.jpg
49cd5d5b6cbb6b31dab33bc7fbd7f78a1d93b1384b05006c9bac8cf15ea5aba7  touchdown-integration-diagnosis-board.jpg
2885800af6e0ed3754990a9e33d3f5a8cd4845994f8fef909d4a96be628d51c4  gap-board.jpg
8cb9c60eb9a66b60d3f6798a0a61a423a26e6c4a706d0cc4d9e530cc2b1f7f5e  pass-breakdown-board.jpg
2625a5fe6aba6b3153b42c98732ea69bd2e0d4f89edad963e23fb05b78e3eac1  beauty-filmstrip.jpg
a0dc7d24a7b274adf78510fb25a3b8b8c50d9a78f1789979b867bc50c11740f9  alpha-filmstrip.jpg
0bd4bd01d8718c25c5a06857022a0c2d94803942fc07182978c728c1d10f863c  pass-id-filmstrip.jpg
468d080b9688d5d9b37dd4442c2d5784421900599bbabfb74ee4b5477b7e5ce5  sbs-filmstrip.jpg
EOF
)
```

Excluded from import (per import instructions, not copied here): `beauty.mp4`,
`pass-id.mp4`, `combined-alpha.mp4`, `sbs-alpha.mp4`, `composite-preview.mp4`,
`frames/`, `source-scene.blend`, `source-scene.blend1`.
