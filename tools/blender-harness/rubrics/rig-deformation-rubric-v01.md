# Rig / Deformation Rubric v01

This rubric applies after asset-art and topology/UV acceptance.

The rig gate asks whether the rig deforms the accepted mesh under real product
poses, not whether a skeleton merely exists.

## Required Evidence

- Neutral pose board.
- Extreme pose board.
- Closeup deformation board.
- Rig hierarchy audit.
- Skin-weight audit.
- Profile-specific deformation boards from `profiles/asset-profiles.json`.

## Hard Rejects

- Candy-wrapper twisting, crushing, volume loss, or seam exposure in closeup.
- Long-body curve controls move a tube but do not preserve hero form.
- Facial, jaw, hand, claw, sleeve, accessory, tail, whisker, or hair controls are
  absent when required by the profile.
- Auto-rig output is treated as accepted without pose-board evidence.
- The rig only survives the main camera and fails top/side/profile views.

## Reviewer Output

The review must name the exact pose and closeup that proves pass/fail and state
whether animation blocking may start. A pass here does not accept final
animation, source-pass, runtime, or WeChat.
