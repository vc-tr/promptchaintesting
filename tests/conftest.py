"""Shared test fixtures."""

from __future__ import annotations

from typing import Any

import pytest

from atlassian_agent.tools.base import Tool, ToolResult


class FakeTool(Tool):
    def __init__(self, tool_name: str, response: str = "ok") -> None:
        self._name = tool_name
        self._response = response
        self.calls: list[dict[str, Any]] = []

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return f"Fake {self._name} tool"

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        }

    def run(self, **kwargs: Any) -> ToolResult:
        self.calls.append(kwargs)
        return ToolResult(output=self._response)


@pytest.fixture()
def fake_tool() -> FakeTool:
    return FakeTool("test_tool", response='{"result": "test data"}')
