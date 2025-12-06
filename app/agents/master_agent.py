from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from langgraph.graph import END, StateGraph

from app.agents.base_tools import (
    kyc_agent,
    sales_agent,
    sanction_agent,
    underwriting_agent,
)
from app.config import get_llm
from app.state import LoanSession, Phase


@dataclass
class MasterAgent:
    """LangGraph-based orchestrator coordinating the loan journey."""

    session: LoanSession

    def __post_init__(self) -> None:
        self.llm = get_llm()
        self.workflow = self._build_graph()

    def _build_graph(self):
        graph = StateGraph(dict)
        graph.add_node("controller", self._controller)
        graph.add_node("sales", self._run_sales)
        graph.add_node("kyc", self._run_kyc)
        graph.add_node("underwriting", self._run_underwriting)
        graph.add_node("sanction", self._run_sanction)
        graph.set_entry_point("controller")
        graph.add_conditional_edges(
            "controller",
            self._route_from_controller,
            {
                "sales": "sales",
                "kyc": "kyc",
                "underwriting": "underwriting",
                "sanction": "sanction",
                "end": END,
            },
        )
        return graph.compile()

    def _controller(self, state: Dict[str, Any]) -> Dict[str, Any]:
        # Controller just passes through the state; routing decision handled in _route_from_controller.
        return state

    def _route_from_controller(self, state: Dict[str, Any]) -> str:
        phase = self.session.phase
        if phase in (Phase.INTAKE, Phase.SALES):
            return "sales"
        if phase is Phase.KYC:
            return "kyc"
        if phase is Phase.UNDERWRITING:
            return "underwriting"
        if phase in (Phase.SANCTION, Phase.COMPLETED):
            return "sanction" if phase is Phase.SANCTION else "end"
        return "end"

    def _run_sales(self, state: Dict[str, Any]) -> Dict[str, Any]:
        tool_result = sales_agent.run(state["user_input"], session=self.session)
        return {**state, **tool_result}

    def _run_kyc(self, state: Dict[str, Any]) -> Dict[str, Any]:
        tool_result = kyc_agent.run(state["user_input"], session=self.session)
        return {**state, **tool_result}

    def _run_underwriting(self, state: Dict[str, Any]) -> Dict[str, Any]:
        tool_result = underwriting_agent.run(state["user_input"], session=self.session)
        return {**state, **tool_result}

    def _run_sanction(self, state: Dict[str, Any]) -> Dict[str, Any]:
        tool_result = sanction_agent.run(state["user_input"], session=self.session)
        return {**state, **tool_result}

    def handle_user_message(self, message: str) -> str:
        sanitized = message.strip() or "..."
        self.session.add_message("user", sanitized)
        payload = {"user_input": sanitized}
        result = self.workflow.invoke(payload)
        response = result.get(
            "assistant_message",
            "Processing your request with the loan agents...",
        )
        self.session.add_message("assistant", response)
        return response
