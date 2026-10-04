# Provider portability experiments

This directory contains cross-provider typed-decision experiments tracked by
Issue #81. It is intentionally separate from the frozen PDDR context-selection
backend evidence under `experiments/context_selection/`.

Rules:

- freeze request fixtures before observing scored provider output;
- distinguish wire/API compatibility from semantic/calibration parity;
- treat provider `confidence` as a separate field from option probabilities unless
  that provider/version explicitly defines a derivation;
- record provider/model/runtime provenance separately;
- do not silently truncate input;
- keep hosted aliases and immutable local model revisions distinct;
- preserve raw first-run evidence;
- do not turn upstream benchmark claims into Lab results without reproduction.

## Cloudflare Clef

Issue #118 is the first dedicated provider/runtime validation slice.

The first phase freezes:

- official-source discovery facts;
- one System One request covering `noul`, `choice`, and `score`;
- provider-neutral request/response validation;
- a credential-free Workers AI dry run;
- an exact local Clef-Flash execution path using the released joint decision head.

No provider quality result is produced by this phase.

The first hosted Clef-Flash smoke later confirmed that `confidence` must not be
derived generically from the top option probability: the hosted response exposed
both values independently, matching the broader System One/Jev contract shape.
Provider-specific derivation is therefore a parity observation, not a shared
schema invariant.
