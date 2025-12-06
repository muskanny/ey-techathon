from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from langgraph.graph import END, StateGraph

from app.agents.base_tools import (
    create_kyc_agent,
    create_sales_agent,
    create_sanction_agent,
    create_underwriting_agent,
)
from app.config import get_llm
from app.state import LoanSession, Phase


@dataclass
class MasterAgent:
    """LangGraph-based orchestrator coordinating the loan journey."""

    session: LoanSession

    def __post_init__(self) -> None:
        self.llm = get_llm()
        self.sales_agent = create_sales_agent(self.llm, self.session)
        self.kyc_agent = create_kyc_agent(self.llm, self.session)
        self.underwriting_agent = create_underwriting_agent(self.session)
        self.sanction_agent = create_sanction_agent(self.session)
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
        # Each node handles a single user turn, then stop. Next user input restarts via controller.
        for node in ["sales", "kyc", "underwriting", "sanction"]:
            graph.add_edge(node, END)

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
        tool_result = self.sales_agent.run(state["user_input"])
        return {**state, **tool_result}

    def _run_kyc(self, state: Dict[str, Any]) -> Dict[str, Any]:
        tool_result = self.kyc_agent.run(state["user_input"])
        return {**state, **tool_result}

    def _run_underwriting(self, state: Dict[str, Any]) -> Dict[str, Any]:
        tool_result = self.underwriting_agent.run(state["user_input"])
        return {**state, **tool_result}

    def _run_sanction(self, state: Dict[str, Any]) -> Dict[str, Any]:
        tool_result = self.sanction_agent.run(state["user_input"])
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
