"""Tests for the ReAct agent loop."""

from __future__ import annotations

from atlassian_agent.agent import Agent
from atlassian_agent.llm.base import LLMResponse, ToolCall
from atlassian_agent.llm.fake_client import FakeLLMClient
from tests.conftest import FakeTool


class TestAgentLoop:
    def test_no_tool_needed(self) -> None:
        llm = FakeLLMClient([LLMResponse(text="The answer is 42.")])
        agent = Agent(llm=llm, tools=[])
        result = agent.run("What is the meaning of life?")
        assert result.answer == "The answer is 42."
        assert result.steps >= 1
        assert result.tool_calls_made == []

    def test_single_tool_call(self) -> None:
        tool = FakeTool("jira_search", response='[{"key": "FOO-1"}]')
        llm = FakeLLMClient([
            LLMResponse(
                text="I'll search Jira.",
                tool_calls=[ToolCall(id="tc1", name="jira_search", arguments={"query": "P1"})],
            ),
            LLMResponse(text="Found FOO-1."),
        ])
        agent = Agent(llm=llm, tools=[tool])
        result = agent.run("Find P1 bugs")
        assert result.answer == "Found FOO-1."
        assert "jira_search" in result.tool_calls_made
        assert len(tool.calls) == 1

    def test_multi_tool_sequence(self) -> None:
        search = FakeTool("search", response='[{"key": "X-1"}]')
        create = FakeTool("create", response='{"id": "page-1"}')
        llm = FakeLLMClient([
            LLMResponse(
                text="Searching...",
                tool_calls=[ToolCall(id="tc1", name="search", arguments={"query": "bugs"})],
            ),
            LLMResponse(
                text="Creating page...",
                tool_calls=[ToolCall(id="tc2", name="create", arguments={"query": "draft"})],
            ),
            LLMResponse(text="Done. Created page-1 with bug summary."),
        ])
        agent = Agent(llm=llm, tools=[search, create])
        result = agent.run("Summarize bugs and write a page")
        assert result.answer == "Done. Created page-1 with bug summary."
        assert result.tool_calls_made == ["search", "create"]

    def test_step_budget_enforced(self) -> None:
        tool = FakeTool("loop_tool", response="still going")
        responses = [
            LLMResponse(
                text=f"Step {i}",
                tool_calls=[ToolCall(id=f"tc{i}", name="loop_tool", arguments={"query": "x"})],
            )
            for i in range(20)
        ]
        llm = FakeLLMClient(responses)
        agent = Agent(llm=llm, tools=[tool], max_steps=3)
        result = agent.run("Do something")
        assert "budget exhausted" in result.answer.lower()

    def test_unknown_tool_handled(self) -> None:
        llm = FakeLLMClient([
            LLMResponse(
                tool_calls=[ToolCall(id="tc1", name="nonexistent", arguments={"query": "x"})],
            ),
            LLMResponse(text="I couldn't find that tool."),
        ])
        agent = Agent(llm=llm, tools=[])
        result = agent.run("Use a tool")
        assert result.answer == "I couldn't find that tool."

    def test_token_counts_accumulated(self) -> None:
        llm = FakeLLMClient([
            LLMResponse(
                text="Searching.",
                tool_calls=[ToolCall(id="tc1", name="t", arguments={"query": "x"})],
                input_tokens=100,
                output_tokens=50,
            ),
            LLMResponse(text="Done.", input_tokens=200, output_tokens=75),
        ])
        tool = FakeTool("t")
        agent = Agent(llm=llm, tools=[tool])
        result = agent.run("task")
        assert result.total_input_tokens == 300
        assert result.total_output_tokens == 125

    def test_tracing_records_steps(self) -> None:
        import os
        import tempfile

        from atlassian_agent.tracing import TraceLogger

        db_path = os.path.join(tempfile.mkdtemp(), "test.db")
        tracer = TraceLogger(db_path)
        tool = FakeTool("t", response="data")
        llm = FakeLLMClient([
            LLMResponse(
                text="calling",
                tool_calls=[ToolCall(id="tc1", name="t", arguments={"query": "x"})],
            ),
            LLMResponse(text="Done."),
        ])
        agent = Agent(llm=llm, tools=[tool], trace_logger=tracer)
        result = agent.run("task")
        steps = tracer.get_run(result.run_id)
        assert len(steps) >= 3
        kinds = [s.kind for s in steps]
        assert "llm_call" in kinds
        assert "tool_call" in kinds
        assert "final" in kinds
        tracer.close()
