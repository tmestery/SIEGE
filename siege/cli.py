"""Command-line entry points for SEIGE."""

from __future__ import annotations

import argparse

from siege.models import create_model_client, parse_model_spec


def build_parser() -> argparse.ArgumentParser:
    """Build the SEIGE command-line parser."""
    parser = argparse.ArgumentParser(prog="seige")
    parser.add_argument(
        "--model",
        required=True,
        type=_model_spec,
        help=(
            "Model identifier in provider/model format, for example "
            "groq/llama3, openai/gpt-4o, anthropic/claude-3-5, or ollama/mistral."
        ),
    )
    parser.add_argument(
        "--prompt",
        help="Optional prompt to send through the selected model client.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the CLI."""
    args = build_parser().parse_args(argv)
    client = create_model_client(args.model)
    if args.prompt:
        print(client.complete(args.prompt))
    return 0


def _model_spec(value: str) -> str:
    """Validate a CLI model spec and return it unchanged."""
    try:
        parse_model_spec(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc
    return value


if __name__ == "__main__":
    raise SystemExit(main())
