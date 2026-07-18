"""Close pending tool-call batches before the next provider request."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from firstcoder.providers.types import ToolCall
from firstcoder.tools.types import ToolResult, make_error_result

if TYPE_CHECKING:
    from firstcoder.agent.session import AgentSession


@dataclass(frozen=True, slots=True)
class ToolCallSettlementResult:
    tool_call: ToolCall
    result: ToolResult


class ToolCallSettlement:
    def __init__(self, session: AgentSession) -> None:
        self.session = session

    def append_skipped(self, tool_calls: list[ToolCall]) -> list[ToolCallSettlementResult]:
        settlements = [
            ToolCallSettlementResult(
                tool_call=tool_call,
                result=make_error_result(
                    tool_call.name,
                    "工具调用已跳过，因为本批次中的前一个工具需要用户输入。",
                    skipped=True,
                    execution_outcome="not_executed",
                ),
            )
            for tool_call in tool_calls
        ]
        self._append(settlements)
        return settlements

    def append_interrupted_tail(self) -> list[ToolCallSettlementResult]:
        return self._append_pending_as_interrupted()

    def repair_before_provider_request(self) -> list[ToolCallSettlementResult]:
        return self._append_pending_as_interrupted()

    def _append_pending_as_interrupted(self) -> list[ToolCallSettlementResult]:
        pending = self.session._pending_tool_calls_from_tail()
        if len(pending) != 1:
            return []
        first, remaining = pending[0]
        settlements = [
            ToolCallSettlementResult(
                tool_call=tool_call,
                result=make_error_result(
                    tool_call.name,
                    "工具执行被用户中断；结果未知，操作可能尚未执行、部分执行，或已在后台继续。",
                    interrupted=True,
                    execution_outcome="unknown",
                ),
            )
            for tool_call in [first, *remaining]
        ]
        self._append(settlements)
        return settlements

    def _append(self, settlements: list[ToolCallSettlementResult]) -> None:
        for settlement in settlements:
            self.session.append_tool_result(
                tool_call=settlement.tool_call,
                result=settlement.result,
            )
