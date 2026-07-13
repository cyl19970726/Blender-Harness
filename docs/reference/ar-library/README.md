# AR reference card library

This directory stores accepted, lightweight reference cards for Jieyang Gucheng AR decisions. It does not store downloaded source videos, frame dumps, or product assets.

Raw research belongs in gitignored `.artifacts/research/lapian/`. A committed card must contain:

- title, source URL or stable source identifier, and capture date;
- runtime assumption and tracking mode, with `unknown` used when evidence is missing;
- the exact visual or interaction mechanic worth reusing;
- delivery risks for WeChat mini program XR;
- decision: `reuse`, `adapt`, `art-reference-only`, or `reject`;
- current Target Brief or route to which the decision applies;
- provenance and SHA256 for any locally retained source artifact.

Do not promote a native-app or H5 reference into XR-Frame implementation proof. Do not infer that an old issue is still the product mainline. Cards inform RouteHypothesis and probe design; they never approve an asset or route by themselves.

The library currently has no accepted cards. Add an `index.md` together with the first card rather than maintaining an empty index.
