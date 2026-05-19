# Atlassian Agent

A tool-using LLM agent for Jira and Confluence, with an eval harness.

The agent uses a **ReAct loop** (plan → tool → observe → repeat) to complete
tasks like triaging bugs, summarizing sprints, and drafting Confluence pages.
It supports **Claude** (default), **OpenAI**, and **Ollama** as LLM providers
behind a single `LLMClient` interface.

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌────────────────┐
│   CLI / UI   │────▶│  Agent Loop   │────▶│   LLM Client   │
│  (cli.py)    │     │  (agent.py)   │     │ Claude/OpenAI/  │
└─────────────┘     │               │     │   Ollama        │
                    │  plan → tool  │     └────────────────┘
                    │  → observe    │
                    │  → repeat     │
                    └──────┬───────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
        ┌──────────┐ ┌──────────┐ ┌──────────┐
        │   Jira   │ │Confluence│ │MCP Bridge│
        │  Tools   │ │  Tools   │ │  (any    │
        │          │ │          │ │  server) │
        └──────────┘ └──────────┘ └──────────┘
```

## Quickstart

```bash
# Install with uv
uv sync --extra dev

# Set credentials
export ANTHROPIC_API_KEY=sk-...
export ATLASSIAN_URL=https://your-site.atlassian.net
export ATLASSIAN_EMAIL=you@example.com
export ATLASSIAN_TOKEN=your-api-token

# Run the agent
python -m atlassian_agent.cli "summarize open P1 bugs in project FOO and draft a Confluence page"

# Run tests
uv run pytest -x -v

# Run eval suite (fake LLM, no credentials needed)
uv run python -m evals.runner --suite smoke --provider fake
```

## What It Does

- **Triage**: Search, label, and transition Jira issues
- **Summarize**: Sprint status, bug backlogs, team workload
- **Author**: Release notes, postmortems, design docs on Confluence
- **Cross-tool**: Read from Jira → write to Confluence in one flow

## Add a Tool

1. Create a class extending `Tool` in `src/atlassian_agent/tools/`
2. Implement `name`, `description`, `parameters_schema`, and `run()`
3. Register it in `cli.py` or pass it to `Agent(tools=[...])`

Alternatively, use `MCPRemoteBridge` or `MCPStdioBridge` to wrap any MCP
server's tools automatically.

## Add an Eval Task

Create a YAML file in `evals/tasks/`:

```yaml
id: my_task
prompt: "Do something with Jira and Confluence"
suites: [all, smoke]
max_steps: 8
expected_tools: [jira_search_issues, confluence_create_page]
success_criteria: "tools_called:jira_search_issues,confluence_create_page"
scripted_responses:
  - text: "Searching..."
    tool_calls:
      - id: tc1
        name: jira_search_issues
        arguments: {jql: "project = FOO"}
  - text: "Done — found and documented the results."
```

## Eval Results

Run the full suite:

```bash
uv run python -m evals.runner --suite all --provider fake --repeats 3
```

Reports are generated in `evals/reports/<timestamp>/report.md`.

## Project Structure

```
src/atlassian_agent/       # Main package
  agent.py                 # ReAct loop
  cli.py                   # CLI entrypoint
  tracing.py               # SQLite trace logger
  llm/                     # Provider-agnostic LLM layer
  tools/                   # Jira, Confluence, MCP bridge
evals/                     # Eval harness
  tasks/                   # 15 YAML task definitions
  scorers.py               # Scoring functions
  runner.py                # Eval runner + report generator
tests/                     # pytest suite
legacy/                    # Original n8n demo (preserved)
```

## Legacy

The original n8n + OpenAI prompt-chain demo lives in [`legacy/`](legacy/).
See [`legacy/README.md`](legacy/README.md) for setup instructions.

## License

MIT
