"""Confluence tools: search, get, create, and update pages."""

from __future__ import annotations

import json
import os
from typing import Any

from atlassian_agent.tools.base import Tool, ToolResult


def _get_confluence_client() -> Any:
    from atlassian import Confluence

    return Confluence(  # type: ignore[no-untyped-call]
        url=os.environ["ATLASSIAN_URL"],
        username=os.environ["ATLASSIAN_EMAIL"],
        password=os.environ["ATLASSIAN_TOKEN"],
    )


class SearchPagesTool(Tool):
    @property
    def name(self) -> str:
        return "confluence_search_pages"

    @property
    def description(self) -> str:
        return "Search Confluence pages using CQL."

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "cql": {"type": "string", "description": "CQL query string"},
                "max_results": {
                    "type": "integer",
                    "description": "Maximum results to return",
                    "default": 10,
                },
            },
            "required": ["cql"],
        }

    def run(self, **kwargs: Any) -> ToolResult:
        cql: str = kwargs["cql"]
        max_results: int = kwargs.get("max_results", 10)
        try:
            client = _get_confluence_client()
            results = client.cql(cql, limit=max_results)
            pages = [
                {
                    "id": r["content"]["id"],
                    "title": r["content"]["title"],
                    "space": r["content"].get("space", {}).get("key", ""),
                    "url": r["content"]["_links"].get("webui", ""),
                }
                for r in results.get("results", [])
            ]
            return ToolResult(output=json.dumps(pages))
        except Exception as e:
            return ToolResult(output=str(e), error=True)


class GetPageTool(Tool):
    @property
    def name(self) -> str:
        return "confluence_get_page"

    @property
    def description(self) -> str:
        return "Get a Confluence page by ID, including its body content."

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "page_id": {"type": "string", "description": "Page ID"},
            },
            "required": ["page_id"],
        }

    def run(self, **kwargs: Any) -> ToolResult:
        page_id: str = kwargs["page_id"]
        try:
            client = _get_confluence_client()
            page = client.get_page_by_id(page_id, expand="body.storage,version")
            result = {
                "id": page["id"],
                "title": page["title"],
                "version": page["version"]["number"],
                "body": page["body"]["storage"]["value"],
            }
            return ToolResult(output=json.dumps(result))
        except Exception as e:
            return ToolResult(output=str(e), error=True)


class CreatePageTool(Tool):
    @property
    def name(self) -> str:
        return "confluence_create_page"

    @property
    def description(self) -> str:
        return "Create a new Confluence page in a given space."

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "space": {"type": "string", "description": "Space key"},
                "title": {"type": "string", "description": "Page title"},
                "body": {"type": "string", "description": "Page body in HTML storage format"},
            },
            "required": ["space", "title", "body"],
        }

    def run(self, **kwargs: Any) -> ToolResult:
        try:
            client = _get_confluence_client()
            result = client.create_page(
                space=kwargs["space"],
                title=kwargs["title"],
                body=kwargs["body"],
            )
            return ToolResult(
                output=json.dumps({"id": result["id"], "title": result["title"]})
            )
        except Exception as e:
            return ToolResult(output=str(e), error=True)


class UpdatePageTool(Tool):
    @property
    def name(self) -> str:
        return "confluence_update_page"

    @property
    def description(self) -> str:
        return "Update an existing Confluence page body."

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "page_id": {"type": "string", "description": "Page ID to update"},
                "body": {"type": "string", "description": "New page body in HTML storage format"},
            },
            "required": ["page_id", "body"],
        }

    def run(self, **kwargs: Any) -> ToolResult:
        page_id: str = kwargs["page_id"]
        try:
            client = _get_confluence_client()
            page = client.get_page_by_id(page_id, expand="version")
            client.update_page(
                page_id=page_id,
                title=page["title"],
                body=kwargs["body"],
            )
            return ToolResult(output=f"Updated page {page_id}")
        except Exception as e:
            return ToolResult(output=str(e), error=True)


ALL_CONFLUENCE_TOOLS: list[Tool] = [
    SearchPagesTool(),
    GetPageTool(),
    CreatePageTool(),
    UpdatePageTool(),
]
