"""ReAct agent loop: plan -> tool -> observe -> repeat."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from atlassian_agent.llm.base import LLMClient, Message
from atlassian_agent.tools.base import Tool, ToolResult
from atlassian_agent.tracing import TraceLogger, TraceStep, new_run_id, timed

SYSTEM_PROMPT = """\
You are an Atlassian Agent. You help users manage Jira issues and Confluence pages.

You have access to tools. When you need information or want to take an action,
call the appropriate tool. After receiving a tool result, reason about what to
do next. Continue until the user's task is fully complete.

Think step-by-step. Be concise in your reasoning."""


@dataclass
class AgentResult:
    answer: str
    run_id: str
    steps: int
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    tool_calls_made: list[str] = field(default_factory=list)


class Agent:
    def __init__(
        self,
        llm: LLMClient,
        tools: list[Tool],
        max_steps: int = 10,
        system_prompt: str = SYSTEM_PROMPT,
        trace_logger: TraceLogger | None = None,
    ) -> None:
        self._llm = llm
        self._tools = {t.name: t for t in tools}
        self._max_steps = max_steps
        self._system_prompt = system_prompt
        self._tracer = trace_logger

    def run(self, task: str) -> AgentResult:
        run_id = new_run_id()
        messages: list[Message] = [Message(role="user", content=task)]
        tool_schemas = [t.to_llm_schema() for t in self._tools.values()]
        step_idx = 0
        total_in = 0
        total_out = 0
        tool_calls_made: list[str] = []

        for _ in range(self._max_steps):
            with timed() as timing:
                response = self._llm.chat(
                    messages=messages, tools=tool_schemas, system=self._system_prompt
                )
            total_in += response.input_tokens
            total_out += response.output_tokens

            self._trace(
                run_id,
                step_idx,
                "llm_call",
                {
                    "text": response.text,
                    "tool_calls": [
                        {"name": tc.name, "arguments": tc.arguments}
                        for tc in response.tool_calls
                    ],
                },
                timing["elapsed_ms"],
                response.input_tokens,
                response.output_tokens,
            )
            step_idx += 1

            if not response.has_tool_calls:
                self._trace(
                    run_id,
                    step_idx,
                    "final",
                    {"answer": response.text or ""},
                    0,
                    0,
                    0,
                )
                return AgentResult(
                    answer=response.text or "",
                    run_id=run_id,
                    steps=step_idx,
                    total_input_tokens=total_in,
                    total_output_tokens=total_out,
                    tool_calls_made=tool_calls_made,
                )

            messages.append(
                Message(
                    role="assistant",
                    content=response.text or "",
                    tool_calls=response.tool_calls,
                )
            )

            for tc in response.tool_calls:
                tool_calls_made.append(tc.name)
                tool = self._tools.get(tc.name)
                if tool is None:
                    result = ToolResult(
                        output=f"Unknown tool: {tc.name}", error=True
                    )
                else:
                    with timed() as tool_timing:
                        result = tool.run(**tc.arguments)

                    self._trace(
                        run_id,
                        step_idx,
                        "tool_call",
                        {"tool": tc.name, "args": tc.arguments, "output": result.output},
                        tool_timing["elapsed_ms"],
                        0,
                        0,
                    )
                    step_idx += 1

                messages.append(
                    Message(role="tool", content=result.output, tool_call_id=tc.id)
                )

        final_answer = "Step budget exhausted. Partial progress made."
        self._trace(run_id, step_idx, "final", {"answer": final_answer}, 0, 0, 0)
        return AgentResult(
            answer=final_answer,
            run_id=run_id,
            steps=step_idx,
            total_input_tokens=total_in,
            total_output_tokens=total_out,
            tool_calls_made=tool_calls_made,
        )

    def _trace(
        self,
        run_id: str,
        step_idx: int,
        kind: str,
        payload: dict[str, Any],
        latency_ms: float,
        input_tokens: int,
        output_tokens: int,
    ) -> None:
        if self._tracer is None:
            return
        self._tracer.log(
            TraceStep(
                run_id=run_id,
                step_idx=step_idx,
                kind=kind,
                payload=payload,
                latency_ms=latency_ms,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            )
        )
