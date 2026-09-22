# Dataset v0.2 embedding input-length diagnostic analysis

PR #69 measured the exact tokenizer/model path used by the frozen
`multilingual-e5-small` embedding baseline without changing scores, Top-k,
dataset, or gold.

Source workflow:
[`35751953959`](https://github.com/serevy/semantic-decision-lab/actions/runs/35751953959)

Artifact digest:

```text
sha256:ebf57ea998fe2587199198bad79e47f233e1c5b2fe621c922dc4cab4c05201ff
```

A compact machine-readable Evidence summary is preserved in
[`results/embedding-input-diagnostics-v0.2-evidence.json`](results/embedding-input-diagnostics-v0.2-evidence.json).

## Main finding

The frozen baseline uses:

- `intfloat/multilingual-e5-small@fd1525a9...`
- `XLMRobertaTokenizer`
- tokenizer `model_max_length = 512`
- `SentenceTransformer.max_seq_length = 512`

Observed inputs:

| Input kind | Count | Truncated | Raw token range |
|---|---:|---:|---:|
| PDDR passages | 12 | **12/12** | 897–1783 |
| task queries | 12 | **0/12** | 52–100 |

Every frozen PDDR passage was therefore embedded from only the first 512 tokens.
The queries were all fully retained.

This resolves the instrumentation gap identified in PR #67 / #68.

## Severity of truncation

The two required records missed by the frozen embedding Top-2 result were among
the longest pddr-kit passages:

- **PDDR-0006**: 1783 raw tokens → 512 used, 1271 tokens truncated
- **PDDR-0007**: 1572 raw tokens → 512 used, 1060 tokens truncated

For both records, the retained character boundary occurs before the
`## Decision` section:

- PDDR-0006: retained PDDR characters end around 1286; `## Decision` begins at
  character 1996
- PDDR-0007: retained PDDR characters end around 1232; `## Decision` begins at
  character 1629

This is important input-validity evidence, but it is **not causal proof** that
truncation produced the retrieval misses. Both records still expose useful
information in their title, Summary, and early Context sections.

For comparison, broad PDDR-0001 retains its `## Decision` heading within the
512-token view, while adjacent PDDR-0003 does not. The observed attraction toward
broad records therefore cannot be reduced to one simple "Decision section
present/absent" explanation.

## What this changes about interpretation

The frozen v0.2 embedding arm should now be described as:

> multilingual-e5-small retrieval over **truncated first-512-token PDDR
> representations**

rather than full-record embedding retrieval.

The historical result remains valid for that exact condition. It should not be
used as evidence of how the same embedding model performs when the complete PDDR
content is represented.

## Next clean experiment

The next methodologically clean slice is a **versioned long-context embedding
condition** that keeps the same model and frozen dataset but represents complete
PDDR content without silent truncation.

A low-complexity first candidate is tokenizer-aware chunking with a frozen
document aggregation rule (for example, max chunk similarity), evaluated as a
new result version rather than overwriting v0.2.

The chunk size, overlap, aggregation rule, and Top-k must be frozen before
observing its output.

## PDDR checkpoint

This finding is experiment Evidence. It does not yet establish a permanent
Project / Product / Process rule or a production default.

No new PDDR is created at this checkpoint.
