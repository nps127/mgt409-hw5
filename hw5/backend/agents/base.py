"""Shared machinery for every agent: the agent loop, delegation, and auditing.

Each agent is a PydanticAI Agent with three things:
  - its prompt from backend/prompts/<name>.md,
  - the campus-customs MCP tools it's allowed to use (filtered toolset),
  - the `delegate` tool, which can reach any other agent (full connectivity).

`run_agent` drives one agent with `Agent.iter`, writing an audit row for every
node of the loop (prompt -> model response -> tool results -> ... -> final).
A delegation runs the other agent through the same `run_agent`, so nested
work is audited the same way, tagged with its chain and depth.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel
from pydantic_ai import Agent, RunContext, UsageLimits
from pydantic_ai.messages import (
    RetryPromptPart,
    TextPart,
    ThinkingPart,
    ToolCallPart,
    ToolReturnPart,
)
from pydantic_ai.models.openai import OpenAIResponsesModelSettings

import config
from audit import append_step, now_iso, preview
from models import AgentName, AgentReport, AuditStep, Delegation
from shop_mcp import toolset_for


@dataclass(frozen=True)
class AgentSpec:
    name: AgentName
    mcp_tools: frozenset[str]
    output_type: type[BaseModel]
    request_limit: int = config.SPECIALIST_REQUEST_LIMIT


@dataclass
class RunState:
    """Shared by every agent working on one ticket."""

    run_id: str
    ticket_id: int | None
    delegations: list[Delegation] = field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0
    requests: int = 0
    tool_calls: int = 0

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    def usage(self) -> dict[str, int]:
        return {
            "requests": self.requests,
            "tool_calls": self.tool_calls,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
        }


@dataclass
class AgentDeps:
    """Per agent run. `chain` runs from the boss (or whoever started) to this agent."""

    agent: AgentName
    chain: list[AgentName]
    state: RunState
    agent_run_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])

    @property
    def depth(self) -> int:
        return len(self.chain) - 1

    @property
    def parent(self) -> AgentName | None:
        return self.chain[-2] if len(self.chain) > 1 else None


# --- the delegate tool (every agent has it) ----------------------------------


async def delegate(ctx: RunContext[AgentDeps], to: AgentName, task: str) -> str:
    """Hand a task to another agent on the Campus Customs team and get their report back.

    Any agent can delegate to any other: boss, inventory, accounting,
    facilities, customer_service. Write `task` so it stands on its own:
    include the ticket id, what the ticket asks for, the facts you already
    have, and exactly what you need back. You can't delegate to yourself or
    to an agent already in your chain (whoever is waiting on you), and the
    team has a limit on hand-offs per ticket. If you are refused, finish with
    what you have.

    Args:
        to: The agent to ask.
        task: A complete, self-contained request for that agent.
    """
    deps = ctx.deps
    state = deps.state
    reason = None
    if to in deps.chain:
        reason = f"{to} is already in this chain ({' -> '.join(deps.chain)}); answer them instead of asking back"
    elif deps.depth + 1 > config.MAX_DELEGATION_DEPTH:
        reason = f"delegation depth limit ({config.MAX_DELEGATION_DEPTH}) reached"
    elif len([d for d in state.delegations if d.status != "refused"]) >= config.MAX_DELEGATIONS_PER_TICKET:
        reason = f"this ticket has used all {config.MAX_DELEGATIONS_PER_TICKET} hand-offs"
    elif state.total_tokens >= config.TICKET_TOKEN_BUDGET:
        reason = f"this ticket has used its {config.TICKET_TOKEN_BUDGET:,}-token budget"

    record = Delegation(from_agent=deps.agent, to_agent=to, task=task, depth=deps.depth + 1, status="refused")
    _audit(
        deps,
        step=ctx.run_step,
        kind="delegation",
        tool_calls=[{"tool": "delegate", "to": to, "task": task}],
        note=f"refused: {reason}" if reason else f"{deps.agent} -> {to}",
    )
    if reason:
        record.error = reason
        state.delegations.append(record)
        return f"DELEGATION REFUSED: {reason}. Finish with the facts you already have."

    child = AgentDeps(agent=to, chain=[*deps.chain, to], state=state)
    try:
        report = await run_agent(to, task, child, output_type=AgentReport)
        record.status, record.report = "done", report
        state.delegations.append(record)
        return report.model_dump_json(exclude_defaults=True)
    except Exception as exc:  # report the failure to the caller instead of crashing its run
        record.status, record.error = "error", f"{type(exc).__name__}: {exc}"[:500]
        state.delegations.append(record)
        return f"DELEGATION FAILED ({to}): {record.error}. Finish with the facts you already have."


# --- building agents ----------------------------------------------------------

_agents: dict[AgentName, Agent[AgentDeps, Any]] = {}


def get_spec(name: AgentName) -> AgentSpec:
    from . import SPECS  # late import: the agent modules import this one

    return SPECS[name]


def get_agent(name: AgentName) -> Agent[AgentDeps, Any]:
    if name not in _agents:
        spec = get_spec(name)
        _agents[name] = Agent(
            config.build_model(),
            name=spec.name,
            deps_type=AgentDeps,
            output_type=spec.output_type,
            instructions=config.load_prompt(spec.name),
            tools=[delegate],
            toolsets=[toolset_for(spec.mcp_tools)],
            model_settings=OpenAIResponsesModelSettings(max_tokens=config.MAX_OUTPUT_TOKENS),
            retries=2,
        )
    return _agents[name]


# --- the agent loop -----------------------------------------------------------


def _audit(deps: AgentDeps, *, step: int, kind: str, **fields: Any) -> None:
    append_step(
        AuditStep(
            time=now_iso(),
            run_id=deps.state.run_id,
            ticket_id=deps.state.ticket_id,
            agent=deps.agent,
            agent_run_id=deps.agent_run_id,
            parent_agent=deps.parent,
            chain=list(deps.chain),
            depth=deps.depth,
            step=step,
            kind=kind,
            model=config.MODEL_NAME,
            run_usage=deps.state.usage(),
            **fields,
        )
    )


async def run_agent(
    name: AgentName,
    prompt: str,
    deps: AgentDeps,
    output_type: type[BaseModel] | None = None,
) -> Any:
    """Run one agent's loop to its final output, auditing every step."""
    spec = get_spec(name)
    agent = get_agent(name)
    state = deps.state
    remaining = max(config.TICKET_TOKEN_BUDGET - state.total_tokens, 1)
    limits = UsageLimits(
        request_limit=spec.request_limit,
        tool_calls_limit=config.TOOL_CALLS_PER_AGENT,
        total_tokens_limit=remaining,
    )
    step = 0
    _audit(deps, step=step, kind="run_start", text=prompt, note=f"limits: {limits!r}")

    try:
        async with agent.iter(
            prompt, deps=deps, usage_limits=limits, output_type=output_type or spec.output_type
        ) as run:
            async for node in run:
                step += 1
                if Agent.is_user_prompt_node(node):
                    _audit(deps, step=step, kind="user_prompt", text=prompt)

                elif Agent.is_model_request_node(node):
                    results = []
                    for part in node.request.parts:
                        if isinstance(part, ToolReturnPart):
                            results.append(
                                {"tool": part.tool_name, "call_id": part.tool_call_id, "result": preview(part.content)}
                            )
                        elif isinstance(part, RetryPromptPart):
                            results.append(
                                {"tool": part.tool_name, "call_id": part.tool_call_id, "retry": preview(part.content)}
                            )
                    kind = "tool_results" if results else "model_request"
                    _audit(deps, step=step, kind=kind, tool_results=results)

                elif Agent.is_call_tools_node(node):
                    response = node.model_response
                    calls, texts, thoughts = [], [], []
                    for part in response.parts:
                        if isinstance(part, ToolCallPart):
                            calls.append(
                                {"tool": part.tool_name, "call_id": part.tool_call_id, "args": part.args_as_dict()}
                            )
                        elif isinstance(part, TextPart) and part.content:
                            texts.append(part.content)
                        elif isinstance(part, ThinkingPart) and part.content:
                            thoughts.append(part.content)
                    u = response.usage
                    state.requests += 1
                    state.input_tokens += u.input_tokens or 0
                    state.output_tokens += u.output_tokens or 0
                    state.tool_calls += sum(1 for c in calls if not c["tool"].startswith("final_result"))
                    _audit(
                        deps,
                        step=step,
                        kind="model_response",
                        text="\n".join(texts) or None,
                        thinking="\n".join(thoughts) or None,
                        tool_calls=calls,
                        usage={"input_tokens": u.input_tokens or 0, "output_tokens": u.output_tokens or 0},
                        note=f"finish_reason={response.finish_reason}",
                    )

                elif Agent.is_end_node(node):
                    output = node.data.output
                    _audit(
                        deps,
                        step=step,
                        kind="final",
                        output=output.model_dump(mode="json") if isinstance(output, BaseModel) else {"text": str(output)},
                    )

        result = run.result.output
        _audit(deps, step=step + 1, kind="run_end", note="ok")
        return result
    except Exception as exc:
        _audit(deps, step=step + 1, kind="error", note=f"{type(exc).__name__}: {exc}"[:1000])
        raise
