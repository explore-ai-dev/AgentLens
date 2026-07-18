from __future__ import annotations

from firstcoder.agent.session import AgentSession
from firstcoder.agent.tool_settlement import ToolCallSettlement
from firstcoder.context.store import JsonlSessionStore
from firstcoder.providers.types import ChatResponse, ToolCall


def test_append_skipped_closes_remaining_tool_calls(tmp_path) -> None:
    session = AgentSession.create(store=JsonlSessionStore(tmp_path), session_id="sess_test")
    tool_calls = [
        ToolCall(id="call_1", name="grep", arguments={"pattern": "TODO"}),
        ToolCall(id="call_2", name="read_file", arguments={"path": "a.py"}),
    ]
    session.append_assistant_response(
        ChatResponse(
            provider="fake",
            model="fake-model",
            content="",
            tool_calls=tool_calls,
            finish_reason="tool_calls",
        )
    )

    settlements = ToolCallSettlement(session).append_skipped(tool_calls)

    assert [item.tool_call.id for item in settlements] == ["call_1", "call_2"]
    assert all(item.result.data["skipped"] is True for item in settlements)
    assert session._pending_tool_calls_from_tail() == []


def test_repair_before_provider_request_closes_interrupted_tail(tmp_path) -> None:
    session = AgentSession.create(store=JsonlSessionStore(tmp_path), session_id="sess_test")
    tool_call = ToolCall(id="call_1", name="shell", arguments={"command": "long-task"})
    session.append_assistant_response(
        ChatResponse(
            provider="fake",
            model="fake-model",
            content="",
            tool_calls=[tool_call],
            finish_reason="tool_calls",
        )
    )

    settlements = ToolCallSettlement(session).repair_before_provider_request()

    assert [item.tool_call.id for item in settlements] == ["call_1"]
    assert settlements[0].result.data["interrupted"] is True
    assert settlements[0].result.data["execution_outcome"] == "unknown"
    assert session._pending_tool_calls_from_tail() == []
