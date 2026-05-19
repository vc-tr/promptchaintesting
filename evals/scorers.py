"""Eval scorers: success, step_count, token_usage, latency, tool_accuracy."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from atlassian_agent.agent import AgentResult
    from atlassian_agent.tracing import TraceLogger


@dataclass
class EvalScore:
    task_id: str
    run_number: int
    success: bool
    step_count: int
    total_tokens: int
    latency_ms: float
    tool_accuracy: float
    details: dict[str, Any] = field(default_factory=dict)


def score_run(
    task_id: str,
    run_number: int,
    result: AgentResult,
    expected_tools: list[str],
    success_check: bool,
    tracer: TraceLogger | None = None,
) -> EvalScore:
    latency_ms = 0.0
    if tracer:
        steps = tracer.get_run(result.run_id)
        latency_ms = sum(s.latency_ms for s in steps)

    if expected_tools:
        called = set(result.tool_calls_made)
        expected = set(expected_tools)
        tool_accuracy = len(called & expected) / len(expected) if expected else 1.0
    else:
        tool_accuracy = 1.0

    return EvalScore(
        task_id=task_id,
        run_number=run_number,
        success=success_check,
        step_count=result.steps,
        total_tokens=result.total_input_tokens + result.total_output_tokens,
        latency_ms=latency_ms,
        tool_accuracy=tool_accuracy,
        details={
            "answer_preview": result.answer[:200],
            "tools_called": result.tool_calls_made,
            "expected_tools": expected_tools,
        },
    )


@dataclass
class AggregateScores:
    task_id: str
    success_rate: float
    avg_steps: float
    avg_tokens: float
    p50_latency_ms: float
    p95_latency_ms: float
    avg_tool_accuracy: float


def aggregate(scores: list[EvalScore]) -> AggregateScores:
    n = len(scores)
    latencies = sorted(s.latency_ms for s in scores)
    return AggregateScores(
        task_id=scores[0].task_id,
        success_rate=sum(1 for s in scores if s.success) / n,
        avg_steps=sum(s.step_count for s in scores) / n,
        avg_tokens=sum(s.total_tokens for s in scores) / n,
        p50_latency_ms=latencies[n // 2] if latencies else 0,
        p95_latency_ms=latencies[int(n * 0.95)] if len(latencies) > 1 else latencies[0],
        avg_tool_accuracy=sum(s.tool_accuracy for s in scores) / n,
    )
