# Contributing to SEIGE

Thanks for your interest in improving SEIGE. The project is early, so small,
focused contributions are easiest to review.

## Setup

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

For hosted model providers, create a local `.env` file using `.env.example` as
the reference for supported environment variables.

## Development

Run the test suite before opening a pull request:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests
```

When adding a new attack module:

- Extend `siege.attacks.base.Attack`
- Return `AttackResult` for every prompt or case
- Document pass/fail semantics clearly
- Keep scoring deterministic and reproducible
- Add focused tests under `tests/`
- Include example report output when it helps reviewers understand behavior

## Reporting Issues

Please include:

- What you expected to happen
- What actually happened
- The model/provider used, if relevant
- Any prompt, report, or stack trace needed to reproduce the issue

Do not include API keys, private prompts, proprietary system messages, or other
sensitive data in issues or pull requests.
