"""Smoke test: run one cheap eval task end-to-end with fake LLM."""

from __future__ import annotations

import os
import tempfile

from evals.runner import evaluate_success, load_suite, run_task

from atlassian_agent.tracing import TraceLogger


class TestEvalsSmoke:
    def test_smoke_suite_loads(self) -> None:
        tasks = load_suite("smoke")
        assert len(tasks) >= 1

    def test_smoke_task_runs_and_scores(self) -> None:
        tasks = load_suite("smoke")
        task = tasks[0]
        db_path = os.path.join(tempfile.mkdtemp(), "test_eval.db")
        tracer = TraceLogger(db_path)
        scores = run_task(task, repeats=1, tracer=tracer)
        assert len(scores) == 1
        score = scores[0]
        assert score.task_id == task["id"]
        assert score.step_count > 0
        tracer.close()

    def test_all_smoke_tasks_pass(self) -> None:
        tasks = load_suite("smoke")
        for task in tasks:
            scores = run_task(task, repeats=1)
            for score in scores:
                assert score.success, f"Task {score.task_id} failed"

    def test_success_criteria_answer_contains(self) -> None:
        from atlassian_agent.agent import AgentResult
        task = {"success_criteria": "answer_contains:hello"}
        result = AgentResult(answer="Hello world", run_id="x", steps=1)
        assert evaluate_success(task, result)
        result2 = AgentResult(answer="Goodbye", run_id="x", steps=1)
        assert not evaluate_success(task, result2)

    def test_success_criteria_tools_called(self) -> None:
        from atlassian_agent.agent import AgentResult
        task = {"success_criteria": "tools_called:jira_search_issues"}
        result = AgentResult(
            answer="done", run_id="x", steps=1,
            tool_calls_made=["jira_search_issues", "confluence_create_page"],
        )
        assert evaluate_success(task, result)
