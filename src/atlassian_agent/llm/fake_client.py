"""Fake LLM client for testing — returns scripted responses."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from atlassian_agent.llm.base import LLMClient, LLMResponse, Message

if TYPE_CHECKING:
    from collections.abc import Sequence


class FakeLLMClient(LLMClient):
    def __init__(self, responses: Sequence[LLMResponse]) -> None:
        self._responses = list(responses)
        self._call_index = 0
        self.calls: list[dict[str, Any]] = []

    def chat(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]] | None = None,
        system: str | None = None,
    ) -> LLMResponse:
        self.calls.append({"messages": messages, "tools": tools, "system": system})
        if self._call_index >= len(self._responses):
            raise RuntimeError(
                f"FakeLLMClient exhausted: {self._call_index} calls made "
                f"but only {len(self._responses)} responses scripted"
            )
        resp = self._responses[self._call_index]
        self._call_index += 1
        return resp
