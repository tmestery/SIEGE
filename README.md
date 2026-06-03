# SEIGE

**Security Evaluation and Integrity of Generative Engines**

SEIGE is a small, reproducible framework for evaluating LLM security. It runs
structured adversarial attacks against model providers, scores the results on a
deterministic 0-10 risk scale, and writes JSON reports that can be checked into
eval pipelines or compared across models.

## Current Status

SEIGE is early and intentionally minimal. The first implemented attack is direct
prompt injection. The framework already includes:

- A shared `Attack` base class and `AttackResult` schema
- A deterministic `Scorer`
- A JSON `ReportWriter`
- Provider clients for Groq, OpenAI, Anthropic, and Ollama
- Example output in `examples/`

## Installation

```sh
git clone https://github.com/tmestery/seige.git
cd seige
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Configure provider credentials with environment variables or a local `.env`
file. See `.env.example` for the supported keys:

```sh
GROQ_API_KEY=
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
OLLAMA_BASE_URL=http://localhost:11434
```

Ollama does not require an API key, but it does require a running local Ollama
server.

## CLI Usage

The CLI accepts model names in `provider/model` format:

```sh
python3 -m siege.cli --model ollama/mistral --prompt "Say hello in one sentence."
```

Hosted provider examples:

```sh
python3 -m siege.cli --model groq/llama3 --prompt "Say hello in one sentence."
python3 -m siege.cli --model openai/gpt-4o --prompt "Say hello in one sentence."
python3 -m siege.cli --model anthropic/claude-3-5 --prompt "Say hello in one sentence."
```

## Programmatic Example

```python
from siege.attacks import PromptInjectionAttack
from siege.models import create_model_client
from siege.reporting import Report, ReportWriter
from siege.scoring import Scorer

model = create_model_client("ollama/mistral")
attack = PromptInjectionAttack()
results = attack.run_all(model)
summary = Scorer().score(results)
report = Report.from_scoring_summary(
    model="ollama/mistral",
    summary=summary,
    metadata={"attack": attack.name},
)
ReportWriter().write(report, "examples/local_prompt_injection_report.json")
```

## Attacks Covered

- Prompt injection
- Jailbreaking
- Adversarial suffixes (GCG)
- System prompt extraction
- Multi-turn manipulation
- Data exfiltration

See [`attacks.md`](attacks.md) for details.

## Examples

Example JSON reports are committed in `examples/`, including direct
prompt-injection runs for Groq-style and OpenAI-style model labels.

## Tests

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests
```

## Citation

If you use SEIGE in your research, please cite:

```text
Mestery, T. (2026). SEIGE: Security Evaluation and Integrity of Generative Engines. GitHub.
https://github.com/tmestery/seige
```

## Contributing

Contributions are welcome. Please start with [`CONTRIBUTING.md`](CONTRIBUTING.md)
and keep new attack modules deterministic, documented, and covered by tests.

## License

See [`LICENSE`](LICENSE). Free for research use with attribution.
Commercial use or redistribution requires written permission.