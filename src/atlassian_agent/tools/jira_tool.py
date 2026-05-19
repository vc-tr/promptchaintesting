"""Jira tools: search, get, create, and transition issues."""

from __future__ import annotations

import json
import os
from typing import Any

from atlassian_agent.tools.base import Tool, ToolResult


def _get_jira_client() -> Any:
    from atlassian import Jira

    return Jira(
        url=os.environ["ATLASSIAN_URL"],
        username=os.environ["ATLASSIAN_EMAIL"],
        password=os.environ["ATLASSIAN_TOKEN"],
    )


class SearchIssuesTool(Tool):
    @property
    def name(self) -> str:
        return "jira_search_issues"

    @property
    def description(self) -> str:
        return "Search Jira issues using JQL."

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "jql": {"type": "string", "description": "JQL query string"},
                "max_results": {
                    "type": "integer",
                    "description": "Maximum results to return",
                    "default": 20,
                },
            },
            "required": ["jql"],
        }

    def run(self, **kwargs: Any) -> ToolResult:
        jql: str = kwargs["jql"]
        max_results: int = kwargs.get("max_results", 20)
        try:
            client = _get_jira_client()
            results = client.jql(jql, limit=max_results)
            issues = [
                {
                    "key": i["key"],
                    "summary": i["fields"]["summary"],
                    "status": i["fields"]["status"]["name"],
                    "priority": i["fields"].get("priority", {}).get("name", "None"),
                    "assignee": (i["fields"].get("assignee") or {}).get("displayName"),
                }
                for i in results.get("issues", [])
            ]
            return ToolResult(output=json.dumps(issues))
        except Exception as e:
            return ToolResult(output=str(e), error=True)


class GetIssueTool(Tool):
    @property
    def name(self) -> str:
        return "jira_get_issue"

    @property
    def description(self) -> str:
        return "Get a single Jira issue by key."

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "key": {"type": "string", "description": "Issue key, e.g. FOO-123"},
            },
            "required": ["key"],
        }

    def run(self, **kwargs: Any) -> ToolResult:
        key: str = kwargs["key"]
        try:
            client = _get_jira_client()
            issue = client.issue(key)
            return ToolResult(output=json.dumps(issue, default=str))
        except Exception as e:
            return ToolResult(output=str(e), error=True)


class CreateIssueTool(Tool):
    @property
    def name(self) -> str:
        return "jira_create_issue"

    @property
    def description(self) -> str:
        return "Create a new Jira issue."

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "project": {"type": "string", "description": "Project key"},
                "summary": {"type": "string", "description": "Issue summary"},
                "description": {"type": "string", "description": "Issue description"},
                "issue_type": {
                    "type": "string",
                    "description": "Issue type, e.g. Bug, Task, Story",
                    "default": "Task",
                },
            },
            "required": ["project", "summary", "description"],
        }

    def run(self, **kwargs: Any) -> ToolResult:
        try:
            client = _get_jira_client()
            result = client.issue_create(
                fields={
                    "project": {"key": kwargs["project"]},
                    "summary": kwargs["summary"],
                    "description": kwargs["description"],
                    "issuetype": {"name": kwargs.get("issue_type", "Task")},
                }
            )
            return ToolResult(output=json.dumps(result, default=str))
        except Exception as e:
            return ToolResult(output=str(e), error=True)


class TransitionIssueTool(Tool):
    @property
    def name(self) -> str:
        return "jira_transition_issue"

    @property
    def description(self) -> str:
        return "Transition a Jira issue to a new status."

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "key": {"type": "string", "description": "Issue key, e.g. FOO-123"},
                "transition_name": {
                    "type": "string",
                    "description": "Name of the transition, e.g. 'In Progress', 'Done'",
                },
            },
            "required": ["key", "transition_name"],
        }

    def run(self, **kwargs: Any) -> ToolResult:
        key: str = kwargs["key"]
        transition_name: str = kwargs["transition_name"]
        try:
            client = _get_jira_client()
            transitions = client.get_issue_transitions(key)
            target = next(
                (t for t in transitions if t["name"].lower() == transition_name.lower()),
                None,
            )
            if not target:
                available = [t["name"] for t in transitions]
                return ToolResult(
                    output=f"Transition '{transition_name}' not found. Available: {available}",
                    error=True,
                )
            client.issue_transition(key, target["id"])
            return ToolResult(output=f"Transitioned {key} to '{transition_name}'")
        except Exception as e:
            return ToolResult(output=str(e), error=True)


ALL_JIRA_TOOLS: list[Tool] = [
    SearchIssuesTool(),
    GetIssueTool(),
    CreateIssueTool(),
    TransitionIssueTool(),
]
