"""MCP bridge: wraps any MCP server's tools as agent Tool instances."""

from __future__ import annotations

import json
import subprocess
from typing import Any

import httpx

from atlassian_agent.tools.base import Tool, ToolResult


class MCPTool(Tool):
    """Wraps a single MCP tool discovered from an MCP server."""

    def __init__(
        self,
        tool_name: str,
        tool_description: str,
        schema: dict[str, Any],
        call_fn: Any,
    ) -> None:
        self._name = tool_name
        self._description = tool_description
        self._schema = schema
        self._call_fn = call_fn

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return self._schema

    def run(self, **kwargs: Any) -> ToolResult:
        try:
            result = self._call_fn(self._name, kwargs)
            return ToolResult(output=json.dumps(result, default=str))
        except Exception as e:
            return ToolResult(output=str(e), error=True)


class MCPRemoteBridge:
    """Connect to a remote MCP server over HTTP/SSE."""

    def __init__(self, base_url: str, auth_token: str | None = None) -> None:
        self._base_url = base_url.rstrip("/")
        self._headers: dict[str, str] = {}
        if auth_token:
            self._headers["Authorization"] = f"Bearer {auth_token}"

    def list_tools(self) -> list[Tool]:
        resp = httpx.post(
            f"{self._base_url}/",
            json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
            headers=self._headers,
        )
        resp.raise_for_status()
        data = resp.json()
        tools: list[Tool] = []
        for t in data.get("result", {}).get("tools", []):
            tools.append(
                MCPTool(
                    tool_name=t["name"],
                    tool_description=t.get("description", ""),
                    schema=t.get("inputSchema", {"type": "object", "properties": {}}),
                    call_fn=self._call_tool,
                )
            )
        return tools

    def _call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        resp = httpx.post(
            f"{self._base_url}/",
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {"name": name, "arguments": arguments},
            },
            headers=self._headers,
            timeout=30.0,
        )
        resp.raise_for_status()
        result = resp.json().get("result", {})
        content = result.get("content", [])
        texts = [c.get("text", "") for c in content if c.get("type") == "text"]
        return "\n".join(texts) if texts else result


class MCPStdioBridge:
    """Connect to a local MCP server over stdio (JSON-RPC)."""

    def __init__(self, command: list[str]) -> None:
        self._command = command

    def list_tools(self) -> list[Tool]:
        result = self._send({"method": "tools/list"})
        tools: list[Tool] = []
        for t in result.get("tools", []):
            tools.append(
                MCPTool(
                    tool_name=t["name"],
                    tool_description=t.get("description", ""),
                    schema=t.get("inputSchema", {"type": "object", "properties": {}}),
                    call_fn=self._call_tool,
                )
            )
        return tools

    def _call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        result = self._send(
            {"method": "tools/call", "params": {"name": name, "arguments": arguments}}
        )
        content = result.get("content", [])
        texts = [c.get("text", "") for c in content if c.get("type") == "text"]
        return "\n".join(texts) if texts else result

    def _send(self, request: dict[str, Any]) -> Any:
        payload = json.dumps(
            {"jsonrpc": "2.0", "id": 1, **request}
        )
        proc = subprocess.run(
            self._command,
            input=payload,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if proc.returncode != 0:
            raise RuntimeError(f"MCP server error: {proc.stderr}")
        return json.loads(proc.stdout).get("result", {})
