"""Streamlit UI for the Atlassian Agent."""

from __future__ import annotations

import streamlit as st

from atlassian_agent.agent import Agent
from atlassian_agent.llm.base import LLMResponse
from atlassian_agent.llm.fake_client import FakeLLMClient
from atlassian_agent.tools.confluence_tool import ALL_CONFLUENCE_TOOLS
from atlassian_agent.tools.jira_tool import ALL_JIRA_TOOLS
from atlassian_agent.tracing import TraceLogger

st.set_page_config(page_title="Atlassian Agent", layout="wide")
st.title("Atlassian Agent")

provider = st.sidebar.selectbox("LLM Provider", ["anthropic", "openai", "ollama", "fake"])
max_steps = st.sidebar.slider("Max Steps", 1, 20, 10)

task = st.text_area("Task", placeholder="e.g. Summarize open P1 bugs in project FOO")

if st.button("Run Agent") and task:
    with st.spinner("Running agent..."):
        if provider == "fake":
            llm = FakeLLMClient([LLMResponse(text=f"[Demo] Would process: {task}")])
        elif provider == "anthropic":
            from atlassian_agent.llm.anthropic_client import AnthropicClient
            llm = AnthropicClient()
        elif provider == "openai":
            from atlassian_agent.llm.openai_client import OpenAIClient
            llm = OpenAIClient()
        else:
            from atlassian_agent.llm.ollama_client import OllamaClient
            llm = OllamaClient()

        tools = [*ALL_JIRA_TOOLS, *ALL_CONFLUENCE_TOOLS]
        tracer = TraceLogger()
        agent = Agent(llm=llm, tools=tools, max_steps=max_steps, trace_logger=tracer)
        result = agent.run(task)

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Result")
            st.write(result.answer)
        with col2:
            st.subheader("Metrics")
            st.metric("Steps", result.steps)
            st.metric("Input Tokens", result.total_input_tokens)
            st.metric("Output Tokens", result.total_output_tokens)
            st.write("**Tools called:**", ", ".join(result.tool_calls_made) or "none")

        st.subheader("Trace")
        steps = tracer.get_run(result.run_id)
        for step in steps:
            with st.expander(f"Step {step.step_idx}: {step.kind} ({step.latency_ms:.0f}ms)"):
                st.json(step.payload)

        tracer.close()
