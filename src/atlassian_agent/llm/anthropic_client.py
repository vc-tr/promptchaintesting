"""Anthropic Claude adapter."""

from __future__ import annotations

import json
import os
from typing import Any

import anthropic

from atlassian_agent.llm.base import LLMClient, LLMResponse, Message, ToolCall


class AnthropicClient(LLMClient):
    def __init__(
        self,
        model: str = "claude-sonnet-4-20250514",
        api_key: str | None = None,
        max_tokens: int = 4096,
    ) -> None:
        self._model = model
        self._max_tokens = max_tokens
        self._client = anthropic.Anthropic(api_key=api_key or os.environ["ANTHROPIC_API_KEY"])

    def chat(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]] | None = None,
        system: str | None = None,
    ) -> LLMResponse:
        api_messages = self._convert_messages(messages)
        kwargs: dict[str, Any] = {
            "model": self._model,
            "max_tokens": self._max_tokens,
            "messages": api_messages,
        }
        if system:
            kwargs["system"] = system
        if tools:
            kwargs["tools"] = self._convert_tools(tools)
        response = self._client.messages.create(**kwargs)
        return self._parse_response(response)

    @staticmethod
    def _convert_messages(messages: list[Message]) -> list[dict[str, Any]]:
        api_msgs: list[dict[str, Any]] = []
        for msg in messages:
            if msg.role == "tool":
                api_msgs.append(
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": msg.tool_call_id,
                                "content": msg.content,
                            }
                        ],
                    }
                )
            elif msg.tool_calls:
                blocks: list[dict[str, Any]] = []
                if msg.content:
                    blocks.append({"type": "text", "text": msg.content})
                for tc in msg.tool_calls:
                    blocks.append(
                        {
                            "type": "tool_use",
                            "id": tc.id,
                            "name": tc.name,
                            "input": tc.arguments,
                        }
                    )
                api_msgs.append({"role": "assistant", "content": blocks})
            else:
                api_msgs.append({"role": msg.role, "content": msg.content})
        return api_msgs

    @staticmethod
    def _convert_tools(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
        converted: list[dict[str, Any]] = []
        for tool in tools:
            converted.append(
                {
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "input_schema": tool["parameters"],
                }
            )
        return converted

    @staticmethod
    def _parse_response(response: anthropic.types.Message) -> LLMResponse:
        text_parts: list[str] = []
        tool_calls: list[ToolCall] = []
        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                input_data: dict[str, Any] = (
                    block.input if isinstance(block.input, dict) else json.loads(str(block.input))
                )
                tool_calls.append(
                    ToolCall(id=block.id, name=block.name, arguments=input_data)
                )
        return LLMResponse(
            text="\n".join(text_parts) if text_parts else None,
            tool_calls=tool_calls,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )
