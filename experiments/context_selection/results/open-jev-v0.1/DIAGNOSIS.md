# Open Jev v0.1 input-packing diagnosis

The first Open Jev v0.1 provider run (#43) returned identical probability
distributions for all three cases. The follow-up diagnostic from GitHub Actions
run `35582218463` confirms why.

## Finding

All three cases were truncated to the exact same 1,024-token model input.

| case | state tokens | question tail | state budget | dropped state | task survived | input hash |
| --- | ---: | ---: | ---: | ---: | --- | --- |
| ctx-001 | 13,968 | 581 | 441 | 13,527 | no | `fde2ffb4…35e8` |
| ctx-002 | 13,985 | 581 | 441 | 13,544 | no | `fde2ffb4…35e8` |
| ctx-003 | 13,974 | 581 | 441 | 13,533 | no | `fde2ffb4…35e8` |

The adapter state was serialized with sorted JSON keys:

`instruction -> pddr_records -> task`

The pinned upstream encoder preserves the question tail and truncates the state
to the remaining prefix. With seven full PDDR records in state, only 441 state
tokens remained. The case-specific `task` field was at the end and did not
survive in any case.

The retained state also only reached the beginning of PDDR-0001. Therefore the
three requests became identical before model inference, which explains the
identical probability distributions observed in #43.

## Classification

Open Jev v0.1 is preserved as valid raw run evidence, but it is **not a valid
provider-quality comparison**. The failure is classified as an adapter/context-
packing failure.

A corrected packing strategy must use a new experiment version (v0.2). Do not
rewrite or replace the v0.1 evidence.
