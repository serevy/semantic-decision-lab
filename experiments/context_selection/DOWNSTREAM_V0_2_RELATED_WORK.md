# Downstream v0.2 related-work design review

This note records external benchmark-construction ideas used to review the
PDDR-specific downstream v0.2 design. It does **not** import external benchmark
answers into the dataset. The actual cases remain grounded in the frozen PDDR
corpora in this repository.

## 1. SWE-QA-Pro — filter direct-answerable questions

Reference:
https://aclanthology.org/2026.findings-acl.837/

SWE-QA-Pro explicitly uses direct-answer baselines for difficulty calibration
and filters questions that can be solved without repository exploration.

Adopted here:

- the no-context arm is a first-class difficulty signal, not just another model arm;
- a saturated no-context score invalidates a retrieval-preservation claim;
- v0.2 cases are audited so multiple project actions remain plausible without
  the project decision context.

This directly addresses the failure observed in downstream v0.1.

## 2. SWE-QA — derive question shapes from real developer work

Reference:
https://github.com/peng-weihan/SWE-QA-Bench

SWE-QA derives a repository-question taxonomy from real GitHub developer
questions, then instantiates and human-validates repository-grounded QA.

Adopted here:

- scenarios are framed as maintainer / repository decisions rather than trivia;
- gold actions are traced to real frozen project records;
- human review remains part of the pre-output freeze instead of relying on
  synthetic generation alone.

## 3. UAEval4RAG — distinguish unanswerability from ordinary error

References:
https://arxiv.org/abs/2412.12300
https://github.com/SalesforceAIResearch/Unanswerability_RAGE

UAEval4RAG evaluates whether a RAG system appropriately rejects questions that
cannot be answered from the available knowledge base.

Adopted here:

- every v0.2 no-context case is intentionally treated as **unanswerable project
  policy** because the audit requires at least two plausible project actions;
- the expected no-context behavior is therefore `ABSTAIN`;
- a coincidentally correct A-D guess is still counted as an **unsupported
  commitment** in the answerability diagnostic;
- action accuracy and safe abstention remain separate metrics.

## 4. RGB — isolate RAG failure modes

Reference:
https://doi.org/10.1609/AAAI.V38I16.29728

RGB separates RAG behavior into noise robustness, negative rejection,
information integration, and counterfactual robustness.

Adopted here:

- do not collapse retrieval coverage, action accuracy, and abstention into one
  score;
- tag cases that deliberately put generic engineering prior in tension with the
  project-specific decision;
- keep plausible distractor selection separate from context-memory conflict.

## 5. SafeRAG / MAGIC — conflict is a separate stress family

References:
https://github.com/IAAR-Shanghai/SafeRAG
https://arxiv.org/abs/2507.21544

SafeRAG and MAGIC treat noisy/conflicting retrieved evidence as explicit test
families rather than assuming that additional context can only help.

Adopted now:

- v0.2 audit tags project-context-vs-generic-prior cases;
- retrieval arms continue to replay their frozen selections, so misses and
  distractors are observable without tuning.

Deferred:

- a future version may add an explicit **wrong/conflicting PDDR** arm or
  multi-record conflict slice. That should be versioned separately rather than
  inserted into the already-frozen v0.2 run after model output.

## Design boundary

These sources inform **test construction and diagnostics**, not the project
decision answers themselves.

Exact external benchmark questions are not copied because:

1. they do not test this project's PDDR decisions;
2. public benchmark questions can introduce memorization/contamination effects;
3. their licensing and dataset terms differ;
4. the research question here is whether *this project's* decision context is
   necessary and correctly consumed.

The reusable pattern is therefore:

```
real project evidence
  -> context-dependent question
  -> direct/no-context calibration
  -> answerability/abstention diagnostic
  -> noisy/conflicting-context stress
  -> context-bearing control
  -> preserved first-run evidence
```
