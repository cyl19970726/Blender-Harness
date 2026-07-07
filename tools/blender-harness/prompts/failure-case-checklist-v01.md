# Failure Case Checklist Prompt v01

Use this checklist before writing any accept verdict.

## Global Failure Cases

- Candidate only looks acceptable in one camera view.
- Helper overlays, collars, sockets, guides, or UI marks hide a core asset problem.
- A source asset is unlicensed, unknown, or not traceable.
- A profile-required board is missing, cropped away, or marked unusable.
- A review cites the producer's explanation instead of visual evidence.
- A downstream artifact exists before the gate accepts.

## Long Creature Failure Cases

- Head, neck, body, belly, dorsal line, or tail root is visibly discontinuous.
- Body reads as decorated tube, slab, or path-following strip.
- Scale flow, belly flow, mane, fin, or claw placement breaks at key joins.
- S curve, coil, lunge, or head turn collapses in closeup.

## Humanoid / Historical Figure Failure Cases

- Face or silhouette reads as generic NPC instead of the intended character.
- Hands, sleeves, accessories, robe, or hair collapse in closeup.
- Gesture, costume, age, dignity, or cultural tone is inappropriate.
- Retarget motion removes character identity.

## Building / Product Failure Cases

- Building parts float or fail to structurally join.
- Hard edges, normals, or material detail fail in closeup.
- Product edge or material does not survive near-lens framing.
- Pass owner cannot be separated from accepted source.

## Output Rule

If any checklist item is visibly triggered, record it in `hard_reject_hits` and reject unless the gate explicitly permits that limitation.
