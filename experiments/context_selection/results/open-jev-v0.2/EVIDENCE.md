# Open Jev v0.2 evidence

This directory freezes the first valid Open Jev v0.2 provider run for Experiment #2.

## Run identity

- provider repository: \`intikhab49/open-jev-typed-decision-engine\`
- provider revision: \`78d3b3a171f24d8d9a8dea18e027f9d3373fda45\`
- checkpoint SHA-256: \`c83bf11b1fdae33e42704ea4fea2e6364a4fa36684f7ad199f9a4bffb5bc7dc1\`
- inference max_len: **4096**
- packing: **independent record**
- top-k: **2**
- observed_at_utc: \`2026-09-21T14:36:49.064873+00:00\`

The checkpoint differs from the frozen v0.1 checkpoint, so this is not a same-checkpoint packing A/B.

## Input validity

The preflight checked all 21 case/record requests before inference:

- task present in question instructions: **21/21**
- full PDDR record preserved: **21/21**
- dropped state tokens: **0**
- same PDDR under different tasks produced distinct final input hashes: **all 7 records**

Therefore this run is not classified as the v0.1 adapter/context-packing failure.

## Result

| case | required PDDR | selected Top-2 | required rank | required recall |
| --- | --- | --- | ---: | ---: |
| ctx-001 | PDDR-0002 | PDDR-0005, PDDR-0001 | 5 | 0.0 |
| ctx-002 | PDDR-0006 | PDDR-0002, PDDR-0005 | 4 | 0.0 |
| ctx-003 | PDDR-0007 | PDDR-0001, PDDR-0002 | 6 | 0.0 |

Required hit rate: **0/3**.

All cases still used the shared Top-2 cutoff and therefore retained the same
71.4% context reduction ratio as the keyword and embedding Top-2 baselines.

## Uploaded ZIP integrity

Uploaded ZIP SHA-256:

\`2bb87a56b755c469a847a70f7fcc3cc20b1a23d48e5981f4b14bba70e6fb8093\`

Contained file SHA-256 values:

- \`provider-results.json\`: \`bc23f6301124be6daf09713634d9386be56cb3558b77b306d320883e2fd973e1\`
- \`provenance.json\`: \`ca6e3c50e2554c962f13cfc7a697e8255066950b0e4f1750e66614e5dd25b772\`
- \`metrics.json\`: \`24999f51a13868325fd1dddcf75adaedafb25ad638d0d4309be56f2656a22bcc\`
- \`input-preflight.json\`: \`5c2e2611834a5628c94cbf7ef236c1dc533157417b2a39ecc2c54721bfc2ca39\`
- \`selections.json\`: \`5fd1e7c4359ebf4854e1c16f6834a39ef74f9ad29ac8f37cd6ffe5ecdafaeb11\`

Do not overwrite these files. Any prompt, model, checkpoint, packing, context,
or selection-policy change requires a new experiment version.
