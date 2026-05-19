"""OpenAI adapter."""

from __future__ import annotations

import json
import os
from typing import Any

import openai

from atlassian_agent.llm.base import LLMClient, LLMResponse, Message, ToolCall


class OpenAIClient(LLMClient):
    def __init__(
        self,
        model: str = "gpt-4o",
        api_key: str | None = None,
        max_tokens: int = 4096,
    ) -> None:
        self._model = model
        self._max_tokens = max_tokens
        self._client = openai.OpenAI(api_key=api_key or os.environ["OPENAI_API_KEY"])

    def chat(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]] | None = None,
        system: str | None = None,
    ) -> LLMResponse:
        api_messages: list[dict[str, Any]] = []
        if system:
            api_messages.append({"role": "system", "content": system})
        api_messages.extend(self._convert_messages(messages))

        kwargs: dict[str, Any] = {
            "model": self._model,
            "max_tokens": self._max_tokens,
            "messages": api_messages,
        }
        if tools:
            kwargs["tools"] = self._convert_tools(tools)

        response = self._client.chat.completions.create(**kwargs)
        return self._parse_response(response)

    @staticmethod
    def _convert_messages(messages: list[Message]) -> list[dict[str, Any]]:
        api_msgs: list[dict[str, Any]] = []
        for msg in messages:
            if msg.role == "tool":
                api_msgs.append(
                    {
                        "role": "tool",
                        "tool_call_id": msg.tool_call_id,
                        "content": msg.content,
                    }
                )
            elif msg.tool_calls:
                oai_tool_calls = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": json.dumps(tc.arguments),
                        },
                    }
                    for tc in msg.tool_calls
                ]
                api_msgs.append(
                    {
                        "role": "assistant",
                        "content": msg.content or "",
                        "tool_calls": oai_tool_calls,
                    }
                )
            else:
                api_msgs.append({"role": msg.role, "content": msg.content})
        return api_msgs

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
    def _parse_response(response: openai.types.chat.ChatCompletion) -> LLMResponse:
        choice = response.choices[0]
        message = choice.message
        tool_calls: list[ToolCall] = []
        if message.tool_calls:
            for tc in message.tool_calls:
                if hasattr(tc, "function"):
                    tool_calls.append(
                        ToolCall(
                            id=tc.id,
                            name=tc.function.name,
                            arguments=json.loads(tc.function.arguments),
                        )
                    )
        return LLMResponse(
            text=message.content,
            tool_calls=tool_calls,
            input_tokens=response.usage.prompt_tokens if response.usage else 0,
            output_tokens=response.usage.completion_tokens if response.usage else 0,
        )
