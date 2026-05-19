"""Eval runner: load YAML tasks, run agent, score, and generate reports."""

from __future__ import annotations

import datetime
import json
from pathlib import Path
from typing import Any

import click
import yaml

from atlassian_agent.agent import Agent, AgentResult
from atlassian_agent.llm.base import LLMClient, LLMResponse, ToolCall
from atlassian_agent.llm.fake_client import FakeLLMClient
from atlassian_agent.tools.base import Tool, ToolResult
from atlassian_agent.tracing import TraceLogger
from evals.scorers import AggregateScores, EvalScore, aggregate, score_run

TASKS_DIR = Path(__file__).parent / "tasks"
REPORTS_DIR = Path(__file__).parent / "reports"


def load_task(path: Path) -> dict[str, Any]:
    with open(path) as f:
        return yaml.safe_load(f)  # type: ignore[no-any-return]


def load_suite(suite: str) -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    for p in sorted(TASKS_DIR.glob("*.yaml")):
        task = load_task(p)
        if suite == "all" or suite in task.get("suites", ["all"]):
            tasks.append(task)
    return tasks


class FakeFixtureTool(Tool):
    """Tool backed by fixture data for eval runs."""

    def __init__(self, tool_name: str, fixture_responses: dict[str, str]) -> None:
        self._name = tool_name
        self._fixtures = fixture_responses

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return f"Fixture-backed {self._name}"

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {"type": "object", "properties": {}, "additionalProperties": True}

    def run(self, **kwargs: Any) -> ToolResult:
        key = json.dumps(kwargs, sort_keys=True)
        if key in self._fixtures:
            return ToolResult(output=self._fixtures[key])
        return ToolResult(output=json.dumps({"fixture": True, "args": kwargs}))


def build_fake_llm(task: dict[str, Any]) -> FakeLLMClient:
    """Build a fake LLM from task's scripted_responses."""
    scripted = task.get("scripted_responses", [])
    responses: list[LLMResponse] = []
    for entry in scripted:
        tool_calls = []
        for tc in entry.get("tool_calls", []):
            tool_calls.append(
                ToolCall(id=tc.get("id", "tc"), name=tc["name"], arguments=tc.get("arguments", {}))
            )
        responses.append(
            LLMResponse(text=entry.get("text"), tool_calls=tool_calls)
        )
    if not responses:
        responses = [LLMResponse(text=task.get("expected_answer", "No scripted response."))]
    return FakeLLMClient(responses)


def build_fake_tools(task: dict[str, Any]) -> list[Tool]:
    fixtures = task.get("setup_fixtures", {})
    tool_names = task.get("expected_tools", [])
    tools: list[Tool] = []
    for name in tool_names:
        tool_fixtures = fixtures.get(name, {})
        tools.append(FakeFixtureTool(name, tool_fixtures))
    return tools


def evaluate_success(task: dict[str, Any], result: AgentResult) -> bool:
    criteria = task.get("success_criteria")
    if not criteria:
        return len(result.answer) > 0
    if criteria == "answer_not_empty":
        return len(result.answer.strip()) > 0
    if criteria.startswith("answer_contains:"):
        substring = criteria.split(":", 1)[1].strip()
        return substring.lower() in result.answer.lower()
    if criteria.startswith("tools_called:"):
        required = [t.strip() for t in criteria.split(":", 1)[1].split(",")]
        return all(t in result.tool_calls_made for t in required)
    return len(result.answer) > 0


def run_task(
    task: dict[str, Any],
    llm: LLMClient | None = None,
    tools: list[Tool] | None = None,
    repeats: int = 3,
    tracer: TraceLogger | None = None,
) -> list[EvalScore]:
    if llm is None:
        llm = build_fake_llm(task)
    if tools is None:
        tools = build_fake_tools(task)

    scores: list[EvalScore] = []
    for i in range(repeats):
        if isinstance(llm, FakeLLMClient):
            llm = build_fake_llm(task)
        agent = Agent(
            llm=llm,
            tools=tools,
            max_steps=task.get("max_steps", 10),
            trace_logger=tracer,
        )
        result = agent.run(task["prompt"])
        success = evaluate_success(task, result)
        score = score_run(
            task_id=task["id"],
            run_number=i + 1,
            result=result,
            expected_tools=task.get("expected_tools", []),
            success_check=success,
            tracer=tracer,
        )
        scores.append(score)
    return scores


def generate_report(all_scores: dict[str, list[EvalScore]], output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    aggregates: list[AggregateScores] = []
    for _task_id, scores in all_scores.items():
        if scores:
            aggregates.append(aggregate(scores))

    lines = ["# Eval Report", ""]
    lines.append(f"Generated: {datetime.datetime.now(datetime.timezone.utc).isoformat()}")
    lines.append("")
    header = "| Task | Success | Steps | Tokens | P50 Lat | P95 Lat | Tool Acc |"
    lines.append(header)
    lines.append("|------|---------|-------|--------|---------|---------|----------|")
    for a in aggregates:
        lines.append(
            f"| {a.task_id} | {a.success_rate:.0%} | {a.avg_steps:.1f} | "
            f"{a.avg_tokens:.0f} | {a.p50_latency_ms:.0f}ms | {a.p95_latency_ms:.0f}ms | "
            f"{a.avg_tool_accuracy:.0%} |"
        )

    lines.append("")
    total_success = sum(a.success_rate for a in aggregates) / len(aggregates) if aggregates else 0
    lines.append(f"**Overall success rate: {total_success:.0%}**")

    report_path = output_dir / "report.md"
    report_path.write_text("\n".join(lines))
    return report_path


@click.command()
@click.option("--suite", default="all", help="Task suite to run: all, smoke, triage, etc.")
@click.option("--provider", default="fake", help="LLM provider: fake, anthropic, openai, ollama")
@click.option("--repeats", default=3, help="Number of times to run each task")
def main(suite: str, provider: str, repeats: int) -> None:
    """Run the eval suite."""
    tasks = load_suite(suite)
    if not tasks:
        click.echo(f"No tasks found for suite '{suite}'")
        return

    click.echo(f"Running {len(tasks)} tasks × {repeats} repeats (provider={provider})")

    tracer = TraceLogger()
    all_scores: dict[str, list[EvalScore]] = {}

    for task in tasks:
        click.echo(f"  {task['id']}...", nl=False)
        llm: LLMClient | None = None
        tools: list[Tool] | None = None
        if provider == "fake":
            llm = build_fake_llm(task)
            tools = build_fake_tools(task)
        scores = run_task(task, llm=llm, tools=tools, repeats=repeats, tracer=tracer)
        all_scores[task["id"]] = scores
        success_count = sum(1 for s in scores if s.success)
        click.echo(f" {success_count}/{len(scores)} passed")

    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d_%H%M%S")
    report_dir = REPORTS_DIR / timestamp
    report_path = generate_report(all_scores, report_dir)
    click.echo(f"\nReport: {report_path}")
    tracer.close()


if __name__ == "__main__":
    main()
