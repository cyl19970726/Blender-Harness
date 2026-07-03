# v01 Regression Result — blender-harness gate-status checker

**运行日期**: 2026-07-03 01:13:46 CST (`date` 命令输出)
**运行目录**: `/Users/hhh0x/ai-luodi/jieyanggucheng-blender-harness/tools/blender-harness`
**node**: v22.13.0

## 1. `npm test`

命令:

```
npm test
```

完整输出:

```
> blender-harness@0.1.0 test
> node src/run-regression.mjs

blender-harness gate-status regression
======================================
  ok   (a) golden negative fixture (gate-d-v01-negative) -> exit 1
  ok   (b) synthetic-accepted-control -> exit 0
  ok   (c) tamper: delete a required review -> exit 1
  ok   (d) tamper: downstream_allowed=true with rejected status -> exit 2
======================================
All 4 regression assertions passed.
```

**Exit code**: `0`

All 4 regression assertions (golden negative, synthetic-accepted-control, tamper: missing required review, tamper: downstream_allowed/status contract violation) passed.

## 2. Golden negative fixture: `fixtures/gate-d-v01-negative`

命令:

```
node src/check-gate-status.mjs fixtures/gate-d-v01-negative; echo exit=$?
```

关键输出:

```
────────────────────────────────────────────────────────────────────────
Gate status check: gate-d-reduced-animation-candidate-v01  [Gate D]
Candidate dir: /Users/hhh0x/ai-luodi/jieyanggucheng-blender-harness/tools/blender-harness/fixtures/gate-d-v01-negative
Declared status: visual_rejected   downstream_allowed: false
────────────────────────────────────────────────────────────────────────
Judgment basis (one line per rule evaluated):
  [PASS] rule3_status_downstream_consistency: status 'visual_rejected' is consistent with downstream_allowed=false
  [FAIL] rule2_required_review_verdict: required review 'fresh_visual' verdict=reject (hard_reject_hits: 龙proxy在高覆盖帧读成低模球/管)
  [PASS] rule1_required_review_present: 1 required review role(s) declared; all present: true
  [PASS] rule5_forbidden_next_outputs: none of 4 forbidden_next_outputs pattern(s) matched an existing file
────────────────────────────────────────────────────────────────────────
RESULT: REJECTED / BLOCKED  (exit 1)
Blockers:
  - rule2_required_review_verdict: required review 'fresh_visual' verdict=reject (hard_reject_hits: 龙proxy在高覆盖帧读成低模球/管)
────────────────────────────────────────────────────────────────────────
```

**Exit code**: `1` (必须为 1 — 符合预期)

## 3. Synthetic control fixture: `fixtures/synthetic-accepted-control`

命令:

```
node src/check-gate-status.mjs fixtures/synthetic-accepted-control; echo exit=$?
```

关键输出:

```
────────────────────────────────────────────────────────────────────────
Gate status check: synthetic-accepted-control  [Gate D]
Candidate dir: /Users/hhh0x/ai-luodi/jieyanggucheng-blender-harness/tools/blender-harness/fixtures/synthetic-accepted-control
Declared status: accepted   downstream_allowed: true
────────────────────────────────────────────────────────────────────────
Judgment basis (one line per rule evaluated):
  [PASS] rule3_status_downstream_consistency: status 'accepted' is consistent with downstream_allowed=true
  [PASS] rule2_required_review_verdict: required review 'fresh_visual' verdict=accept
  [PASS] rule1_required_review_present: 1 required review role(s) declared; all present: true
────────────────────────────────────────────────────────────────────────
RESULT: ACCEPTED  (exit 0)
NOTE: exit 0 means review records are present and all accept. It is NOT a visual
      endorsement — visual backing lives only in the referenced reviews/*.json.
────────────────────────────────────────────────────────────────────────
```

**Exit code**: `0` (必须为 0 — 符合预期)

## 结论

harness 判拒 Gate D v01 golden negative:**PASS**

- `npm test` 全部 4 条回归断言通过,exit 0。
- golden negative fixture (`gate-d-v01-negative`,对应真实 Gate D reduced-animation-candidate-v01,独立视觉评审 reject:"高覆盖帧读成低模球/管,非故事驱动的有机龙擦除") 被 checker 正确判拒,exit 1,阻断原因是 `rule2_required_review_verdict`(required review `fresh_visual` verdict=reject)。
- synthetic-accepted-control(纯人工构造的契约正例,非真实素材背书)被 checker 正确判通,exit 0,并在输出中显式声明"exit 0 仅代表评审记录齐全且全 accept,不代表视觉背书"。
- 三项命令的实际退出码与任务要求(npm test 任意、negative=1、control=0)完全一致。
