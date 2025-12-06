from __future__ import annotations

from typing import Dict

from langchain.tools import Tool

from app.state import LoanSession, Phase


def _sales_tool(user_input: str, session: LoanSession) -> Dict[str, str]:
    session.loan_request = {"description": user_input}
    session.advance_phase(Phase.KYC)
    return {"assistant_message": "Thanks! I'll verify your identity next."}


def _kyc_tool(user_input: str, session: LoanSession) -> Dict[str, str]:
    session.customer_profile = {"provided_details": user_input, "verified": False}
    session.advance_phase(Phase.UNDERWRITING)
    return {"assistant_message": "KYC placeholder complete. Moving to eligibility."}


def _underwriting_tool(user_input: str, session: LoanSession) -> Dict[str, str]:
    session.underwriting_result = {"status": "pending", "notes": user_input}
    session.advance_phase(Phase.SANCTION)
    return {"assistant_message": "Underwriting stub finished. Preparing sanction letter."}


def _sanction_tool(user_input: str, session: LoanSession) -> Dict[str, str]:
    session.sanction_letter = {"path": "artifacts/demo.pdf"}
    session.advance_phase(Phase.COMPLETED)
    return {"assistant_message": "Sanction letter will be ready shortly."}


sales_agent = Tool(
    name="SalesAgent",
    description="Captures loan request and recommends products.",
    func=lambda user_input, session=None: _sales_tool(user_input, session),
)

kyc_agent = Tool(
    name="KycAgent",
    description="Validates customer identity details.",
    func=lambda user_input, session=None: _kyc_tool(user_input, session),
)

underwriting_agent = Tool(
    name="UnderwritingAgent",
    description="Performs eligibility checks and approvals.",
    func=lambda user_input, session=None: _underwriting_tool(user_input, session),
)

sanction_agent = Tool(
    name="SanctionAgent",
    description="Generates sanction letters.",
    func=lambda user_input, session=None: _sanction_tool(user_input, session),
)
