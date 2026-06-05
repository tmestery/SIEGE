# HuggingFace Dataset Publication

Issue: [#33](https://github.com/tmestery/SIEGE/issues/33)

This guide explains how to turn local SEIGE sweep exports into a HuggingFace-ready
dataset package and upload it to the Hub.

## Recommended Package Layout

```text
artifacts/huggingface-dataset/local_ollama_sweep/
  README.md
  data/local_ollama_sweep/eval-00000-of-00001.parquet
  manifests/local_ollama_sweep.json
  raw/local_ollama_sweep.jsonl.gz
```

Parquet is the canonical Hub format. The compressed JSONL file is kept as a raw export
backup. The manifest documents models, row counts, and schema fields.

## Prepare Locally

From a completed local sweep manifest:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/prepare_huggingface_dataset.py \
  --manifest artifacts/local-ollama-sweep/2026-06-04/manifest.json \
  --run-id local-ollama-sweep-2026-06-04 \
  --config-name local_ollama_sweep \
  --repo-id tmestery/seige-attack-evals
```

Or point directly at report JSON:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/prepare_huggingface_dataset.py \
  --reports-root artifacts/local-ollama-sweep/2026-06-04/reports \
  --run-id local-ollama-sweep-2026-06-04
```

## Upload To HuggingFace

Install Hub tooling and authenticate:

```sh
pip install huggingface_hub pyarrow
huggingface-cli login
```

Upload the prepared package:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/prepare_huggingface_dataset.py \
  --manifest artifacts/local-ollama-sweep/2026-06-04/manifest.json \
  --run-id local-ollama-sweep-2026-06-04 \
  --repo-id tmestery/seige-attack-evals \
  --upload
```

Use `--private` if you want the dataset repository to start private.

## Load From The Hub

```python
from datasets import load_dataset

dataset = load_dataset("tmestery/seige-attack-evals", "local_ollama_sweep", split="eval")
print(dataset[0]["model"], dataset[0]["attack"], dataset[0]["passed"])
```

## Grouping Model

Use one HuggingFace dataset config per curated sweep, for example
`local_ollama_sweep`. Rows from all models live in the same `eval` split and are grouped
by columns such as `model`, `attack`, and `category`.
