"""Contract tests for LLM client adapters."""

from __future__ import annotations

from atlassian_agent.llm.base import LLMResponse, Message, ToolCall
from atlassian_agent.llm.fake_client import FakeLLMClient


class TestFakeLLMClient:
    def test_returns_scripted_text_response(self) -> None:
        client = FakeLLMClient([LLMResponse(text="Hello world")])
        result = client.chat(messages=[Message(role="user", content="Hi")])
        assert result.text == "Hello world"
        assert not result.has_tool_calls

    def test_returns_scripted_tool_call(self) -> None:
        tc = ToolCall(id="tc_1", name="search", arguments={"q": "test"})
        client = FakeLLMClient([LLMResponse(tool_calls=[tc])])
        result = client.chat(messages=[Message(role="user", content="Search")])
        assert result.has_tool_calls
        assert result.tool_calls[0].name == "search"
        assert result.tool_calls[0].arguments == {"q": "test"}

    def test_records_calls(self) -> None:
        client = FakeLLMClient([LLMResponse(text="ok")])
        msgs = [Message(role="user", content="Hi")]
        tools = [{"name": "t", "description": "d", "parameters": {}}]
        client.chat(messages=msgs, tools=tools, system="sys")
        assert len(client.calls) == 1
        assert client.calls[0]["system"] == "sys"
        assert client.calls[0]["tools"] == tools

    def test_multiple_responses_in_order(self) -> None:
        client = FakeLLMClient([
            LLMResponse(text="first"),
            LLMResponse(text="second"),
            LLMResponse(text="third"),
        ])
        r1 = client.chat(messages=[Message(role="user", content="1")])
        r2 = client.chat(messages=[Message(role="user", content="2")])
        r3 = client.chat(messages=[Message(role="user", content="3")])
        assert r1.text == "first"
        assert r2.text == "second"
        assert r3.text == "third"

    def test_exhausted_raises(self) -> None:
        client = FakeLLMClient([LLMResponse(text="only")])
        client.chat(messages=[Message(role="user", content="1")])
        try:
            client.chat(messages=[Message(role="user", content="2")])
            raise AssertionError("Should have raised")
        except RuntimeError as e:
            assert "exhausted" in str(e)

    def test_token_counts_preserved(self) -> None:
        client = FakeLLMClient([LLMResponse(text="ok", input_tokens=100, output_tokens=50)])
        result = client.chat(messages=[Message(role="user", content="Hi")])
        assert result.input_tokens == 100
        assert result.output_tokens == 50
