# Reference Compare Review Prompt v01

Use this prompt as a shared supplement for any Human / Agent review that compares a candidate against references.

## Role

Compare reference evidence to the candidate. Convert vague taste comments into frame- or board-specific findings.

## Comparison Method

1. State which reference image, frame, board, or marketplace asset is being compared.
2. State which candidate board or frame is being compared.
3. Compare silhouette, proportion, material, surface detail, construction logic, and motion read where relevant.
4. Cite the exact mismatch or match. Avoid general words like "better", "worse", or "ugly" unless tied to visible evidence.
5. Separate source reference from product evidence. A reference may guide taste, but it is not proof that the candidate passes.

## Required Finding Shape

Use findings like:

```text
reference: <reference id/frame>; candidate: <board/frame>; observation: <visible fact>; decision impact: <why this supports accept/reject>
```
