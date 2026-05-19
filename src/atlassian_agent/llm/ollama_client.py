"""Ollama adapter."""

from __future__ import annotations

import json
from typing import Any

from atlassian_agent.llm.base import LLMClient, LLMResponse, Message, ToolCall


class OllamaClient(LLMClient):
    def __init__(
        self,
        model: str = "llama3.1",
        host: str | None = None,
    ) -> None:
        try:
            import ollama as _ollama
        except ImportError as e:
            msg = "Install the ollama extra: pip install atlassian-agent[ollama]"
            raise ImportError(msg) from e
        self._model = model
        kwargs: dict[str, Any] = {}
        if host:
            kwargs["host"] = host
        self._client = _ollama.Client(**kwargs)

    def chat(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]] | None = None,
        system: str | None = None,
    ) -> LLMResponse:
        api_messages: list[dict[str, Any]] = []
        if system:
            api_messages.append({"role": "system", "content": system})

        for msg in messages:
            if msg.role == "tool":
                api_messages.append({"role": "tool", "content": msg.content})
            else:
                api_messages.append({"role": msg.role, "content": msg.content})

        kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": api_messages,
        }
        if tools:
            kwargs["tools"] = self._convert_tools(tools)

        response = self._client.chat(**kwargs)
        return self._parse_response(response)

    @staticmethod
    def _convert_tools(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "parameters": tool["parameters"],
                },
            }
            for tool in tools
        ]

    @staticmethod
    def _parse_response(response: Any) -> LLMResponse:
        message = response.message
        tool_calls: list[ToolCall] = []
        if hasattr(message, "tool_calls") and message.tool_calls:
            for i, tc in enumerate(message.tool_calls):
                args = tc.function.arguments
                if isinstance(args, str):
                    args = json.loads(args)
                tool_calls.append(
                    ToolCall(id=f"ollama_{i}", name=tc.function.name, arguments=args)
                )
        return LLMResponse(
            text=message.content if message.content else None,
            tool_calls=tool_calls,
            input_tokens=getattr(response, "prompt_eval_count", 0) or 0,
            output_tokens=getattr(response, "eval_count", 0) or 0,
        )
