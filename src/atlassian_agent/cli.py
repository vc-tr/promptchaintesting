"""CLI entrypoint for the Atlassian Agent."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING, Any

import click
from rich.console import Console
from rich.table import Table

from atlassian_agent.agent import Agent
from atlassian_agent.tools.confluence_tool import ALL_CONFLUENCE_TOOLS
from atlassian_agent.tools.jira_tool import ALL_JIRA_TOOLS
from atlassian_agent.tracing import TraceLogger

if TYPE_CHECKING:
    from atlassian_agent.llm.base import LLMClient
    from atlassian_agent.tools.base import Tool

console = Console()


def _get_llm(provider: str, model: str | None) -> LLMClient:
    if provider == "anthropic":
        from atlassian_agent.llm.anthropic_client import AnthropicClient

        kwargs: dict[str, Any] = {}
        if model:
            kwargs["model"] = model
        return AnthropicClient(**kwargs)
    elif provider == "openai":
        from atlassian_agent.llm.openai_client import OpenAIClient

        kwargs = {}
        if model:
            kwargs["model"] = model
        return OpenAIClient(**kwargs)
    elif provider == "ollama":
        from atlassian_agent.llm.ollama_client import OllamaClient

        kwargs = {}
        if model:
            kwargs["model"] = model
        return OllamaClient(**kwargs)
    else:
        console.print(f"[red]Unknown provider: {provider}[/red]")
        sys.exit(1)


def _get_tools() -> list[Tool]:
    return [*ALL_JIRA_TOOLS, *ALL_CONFLUENCE_TOOLS]


@click.command()
@click.argument("task")
@click.option("--provider", default="anthropic", help="LLM provider: anthropic, openai, ollama")
@click.option("--model", default=None, help="Model override")
@click.option("--max-steps", default=10, help="Maximum agent steps")
@click.option("--trace/--no-trace", default=True, help="Enable/disable tracing")
def main(task: str, provider: str, model: str | None, max_steps: int, trace: bool) -> None:
    """Run the Atlassian Agent on a task."""
    llm = _get_llm(provider, model)
    tools = _get_tools()
    tracer = TraceLogger() if trace else None

    agent = Agent(llm=llm, tools=tools, max_steps=max_steps, trace_logger=tracer)

    console.print(f"\n[bold]Task:[/bold] {task}\n")

    result = agent.run(task)

    table = Table(title="Agent Run Summary")
    table.add_column("Metric", style="bold")
    table.add_column("Value")
    table.add_row("Run ID", result.run_id)
    table.add_row("Steps", str(result.steps))
    table.add_row("Input tokens", str(result.total_input_tokens))
    table.add_row("Output tokens", str(result.total_output_tokens))
    table.add_row("Tools called", ", ".join(result.tool_calls_made) or "none")
    console.print(table)

    console.print(f"\n[bold green]Answer:[/bold green]\n{result.answer}")

    if tracer:
        tracer.close()


if __name__ == "__main__":
    main()
