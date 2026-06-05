# Local Ollama Model Sweep

Issue: [#36](https://github.com/tmestery/SIEGE/issues/36)

This runbook captures the local model sweep used to collect SEIGE reports for
dataset curation. Raw outputs stay under `artifacts/` and should not be
committed.

## Model Set

Target a practical local set under 70B parameters:

- `ollama/gemma3:4b-it-qat`
- `ollama/gemma3:12b`
- `ollama/gemma4:31b`
- `ollama/codellama:13b`
- `ollama/devstral-small-2:latest`
- `ollama/llama3.2:3b`
- `ollama/llama3.1:8b`
- `ollama/mistral:7b`
- `ollama/qwen2.5:7b`
- `ollama/qwen2.5:14b`
- `ollama/phi4:14b`
- `ollama/deepseek-r1:8b`

## Output Layout

Use a dated artifact root:

```text
artifacts/local-ollama-sweep/YYYY-MM-DD/
  manifest.json
  reports/<safe-model-name>/*.json
  datasets/local-ollama-sweep.jsonl
```

## Commands

Pull missing models first:

```sh
ollama pull llama3.2:3b
ollama pull llama3.1:8b
ollama pull mistral:7b
ollama pull qwen2.5:7b
ollama pull qwen2.5:14b
ollama pull phi4:14b
ollama pull deepseek-r1:8b
```

To resume or rerun a single model manually:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m siege.ci_eval \
  --models "ollama/<model-tag>" \
  --output-dir "artifacts/local-ollama-sweep/YYYY-MM-DD/reports/<safe-model-name>"
```

To run all default models, write per-model reports, export JSONL, and generate a
manifest:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/run_local_ollama_sweep.py \
  --run-id local-ollama-sweep-YYYY-MM-DD
```

The script continues across individual model failures and records them in
`manifest.json`.
