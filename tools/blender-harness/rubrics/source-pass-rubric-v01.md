# Source-Pass Rubric v01

This rubric applies after animation acceptance.

The source-pass gate asks whether beauty, mattes, alpha, and pass ownership come
from the accepted source scene and can be audited before runtime packaging.

## Required Evidence

- Beauty contact sheet.
- Pass breakdown board.
- Owner collection manifest.
- Matte contact sheet.
- Source-pass audit.
- Runtime-boundary audit.

## Hard Rejects

- Matte is reverse-engineered from a flattened beauty render.
- SAM2, background removal, or video-generation object pass enters the final
  slot instead of guide only.
- Owner collections are empty, hand-waved, or not tied to visible source objects.
- Runtime assets are produced before source-pass acceptance.
- A technical alpha fix hides an upstream asset-art or animation failure.

## Reviewer Output

The review must name every accepted final owner and every guide-only source. It
must explicitly state whether runtime packaging remains locked or may start.
