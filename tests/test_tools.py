"""Tests for Jira and Confluence tools — mocked HTTP."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from atlassian_agent.tools.confluence_tool import (
    CreatePageTool,
    GetPageTool,
    SearchPagesTool,
    UpdatePageTool,
)
from atlassian_agent.tools.jira_tool import (
    CreateIssueTool,
    GetIssueTool,
    SearchIssuesTool,
    TransitionIssueTool,
)


@pytest.fixture()
def mock_jira() -> MagicMock:
    with patch("atlassian_agent.tools.jira_tool._get_jira_client") as mock:
        client = MagicMock()
        mock.return_value = client
        yield client


@pytest.fixture()
def mock_confluence() -> MagicMock:
    with patch("atlassian_agent.tools.confluence_tool._get_confluence_client") as mock:
        client = MagicMock()
        mock.return_value = client
        yield client


class TestJiraSearchIssues:
    def test_schema_has_required_jql(self) -> None:
        tool = SearchIssuesTool()
        assert tool.name == "jira_search_issues"
        assert "jql" in tool.parameters_schema["properties"]
        assert "jql" in tool.parameters_schema["required"]

    def test_search_returns_formatted_issues(self, mock_jira: MagicMock) -> None:
        mock_jira.jql.return_value = {
            "issues": [
                {
                    "key": "FOO-1",
                    "fields": {
                        "summary": "Bug in login",
                        "status": {"name": "Open"},
                        "priority": {"name": "P1"},
                        "assignee": {"displayName": "Alice"},
                    },
                }
            ]
        }
        result = SearchIssuesTool().run(jql="project = FOO AND priority = P1")
        data = json.loads(result.output)
        assert len(data) == 1
        assert data[0]["key"] == "FOO-1"
        assert data[0]["priority"] == "P1"
        assert not result.error

    def test_search_error_returns_error_result(self, mock_jira: MagicMock) -> None:
        mock_jira.jql.side_effect = Exception("Connection refused")
        result = SearchIssuesTool().run(jql="invalid")
        assert result.error
        assert "Connection refused" in result.output


class TestJiraGetIssue:
    def test_get_issue(self, mock_jira: MagicMock) -> None:
        mock_jira.issue.return_value = {"key": "FOO-1", "fields": {"summary": "test"}}
        result = GetIssueTool().run(key="FOO-1")
        assert not result.error
        data = json.loads(result.output)
        assert data["key"] == "FOO-1"


class TestJiraCreateIssue:
    def test_create_issue(self, mock_jira: MagicMock) -> None:
        mock_jira.issue_create.return_value = {"id": "10001", "key": "FOO-2"}
        result = CreateIssueTool().run(
            project="FOO", summary="New bug", description="Details here"
        )
        assert not result.error
        mock_jira.issue_create.assert_called_once()
        call_fields = mock_jira.issue_create.call_args[1]["fields"]
        assert call_fields["project"]["key"] == "FOO"
        assert call_fields["summary"] == "New bug"


class TestJiraTransitionIssue:
    def test_transition_success(self, mock_jira: MagicMock) -> None:
        mock_jira.get_issue_transitions.return_value = [
            {"id": "3", "name": "Done"},
            {"id": "2", "name": "In Progress"},
        ]
        result = TransitionIssueTool().run(key="FOO-1", transition_name="Done")
        assert not result.error
        mock_jira.issue_transition.assert_called_once_with("FOO-1", "3")

    def test_transition_not_found(self, mock_jira: MagicMock) -> None:
        mock_jira.get_issue_transitions.return_value = [{"id": "3", "name": "Done"}]
        result = TransitionIssueTool().run(key="FOO-1", transition_name="Rejected")
        assert result.error
        assert "not found" in result.output.lower()


class TestConfluenceSearchPages:
    def test_schema(self) -> None:
        tool = SearchPagesTool()
        assert tool.name == "confluence_search_pages"
        assert "cql" in tool.parameters_schema["required"]

    def test_search(self, mock_confluence: MagicMock) -> None:
        mock_confluence.cql.return_value = {
            "results": [
                {
                    "content": {
                        "id": "123",
                        "title": "Sprint Review",
                        "space": {"key": "ENG"},
                        "_links": {"webui": "/wiki/spaces/ENG/pages/123"},
                    }
                }
            ]
        }
        result = SearchPagesTool().run(cql="type=page AND space=ENG")
        data = json.loads(result.output)
        assert data[0]["title"] == "Sprint Review"


class TestConfluenceGetPage:
    def test_get_page(self, mock_confluence: MagicMock) -> None:
        mock_confluence.get_page_by_id.return_value = {
            "id": "123",
            "title": "My Page",
            "version": {"number": 2},
            "body": {"storage": {"value": "<p>Hello</p>"}},
        }
        result = GetPageTool().run(page_id="123")
        data = json.loads(result.output)
        assert data["title"] == "My Page"
        assert data["body"] == "<p>Hello</p>"


class TestConfluenceCreatePage:
    def test_create(self, mock_confluence: MagicMock) -> None:
        mock_confluence.create_page.return_value = {"id": "456", "title": "New Page"}
        result = CreatePageTool().run(space="ENG", title="New Page", body="<p>Content</p>")
        assert not result.error
        data = json.loads(result.output)
        assert data["id"] == "456"


class TestConfluenceUpdatePage:
    def test_update(self, mock_confluence: MagicMock) -> None:
        mock_confluence.get_page_by_id.return_value = {
            "title": "Existing",
            "version": {"number": 3},
        }
        result = UpdatePageTool().run(page_id="123", body="<p>Updated</p>")
        assert not result.error
        mock_confluence.update_page.assert_called_once()


class TestToolSchemas:
    """Verify all tools produce valid LLM schemas."""

    @pytest.mark.parametrize(
        "tool_cls",
        [
            SearchIssuesTool,
            GetIssueTool,
            CreateIssueTool,
            TransitionIssueTool,
            SearchPagesTool,
            GetPageTool,
            CreatePageTool,
            UpdatePageTool,
        ],
    )
    def test_llm_schema_structure(self, tool_cls: type) -> None:
        tool = tool_cls()
        schema = tool.to_llm_schema()
        assert "name" in schema
        assert "description" in schema
        assert "parameters" in schema
        assert schema["parameters"]["type"] == "object"
