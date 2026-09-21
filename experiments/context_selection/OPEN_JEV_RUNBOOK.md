# Open Jev v0.1 runbook

This runbook freezes the first real open typed-decision run for Experiment #2
before observing its PDDR-selection output.

Provider source and training parameters are pinned in
`providers/open-jev-v0.1.json`.

## Why the dynamic JevLite model only

The upstream repository reports a fixed-schema frozen probe and probe ensemble,
but the PDDR relevance questions in this experiment are new at inference time.
The first comparison therefore uses only the upstream dynamic-schema fine-tuned
JevLite model served by `05_serve.py`.

Do not switch to the probe/ensemble after seeing the result. That would be a
different experiment version.

## Reference environment

The upstream project documents a free Colab T4 as the intended training path.
Use a GPU runtime.

### 1. Clone the exact provider revision

```bash
git clone https://github.com/intikhab49/open-jev-typed-decision-engine.git
cd open-jev-typed-decision-engine
git checkout 78d3b3a171f24d8d9a8dea18e027f9d3373fda45
pip install -r requirements.txt
```

### 2. Validate the upstream dataset path

```bash
python smoke_test.py --all
```

### 3. Train with the frozen v0.1 configuration

```bash
python 02_train.py \
  --epochs 20 \
  --patience 6 \
  --schedule cosine \
  --bs 4 \
  --accum 4 \
  --max-len 1024 \
  --lr 3e-5 \
  --head-lr 1e-3 \
  --brier 1.0 \
  --config all \
  --out jevlite.pt
```

### 4. Run the upstream calibration step

```bash
python 03_calibrate.py --ckpt jevlite.pt --bs 8 --config all
sha256sum jevlite.pt
```

Keep the resulting checkpoint SHA-256. The experiment runner records it in
`provenance.json`.

### 5. Start the local decision endpoint

```bash
python 05_serve.py --ckpt jevlite.pt --serve --port 8000
```

### 6. In a second Colab shell/session, run Semantic Decision Lab

```bash
git clone https://github.com/serevy/semantic-decision-lab.git
cd semantic-decision-lab

python experiments/context_selection/run_open_jev_experiment.py \
  experiments/context_selection/cases.v0.1.json \
  experiments/context_selection/corpus/pddr-kit-v0.1 \
  --endpoint http://127.0.0.1:8000/decide \
  --top-k 2 \
  --provider-revision 78d3b3a171f24d8d9a8dea18e027f9d3373fda45 \
  --checkpoint-path ../open-jev-typed-decision-engine/jevlite.pt \
  --output-dir experiments/context_selection/results/open-jev-v0.1
```

The run writes:

- `selections.json`
- `provider-results.json`
- `metrics.json`
- `provenance.json`

Do not edit the frozen task wording, labels, Top-2 cutoff, provider revision, or
training configuration after observing the result. A change requires a new
experiment version.
