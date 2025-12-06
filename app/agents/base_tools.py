from __future__ import annotations

import re
from typing import Dict, Optional

from langchain.tools import Tool
from langchain_core.pydantic_v1 import BaseModel, Field

from app.services.products import recommend_product
from app.services.kyc import verify_customer
from app.state import LoanSession, Phase


class LoanNeed(BaseModel):
    loan_amount: float = Field(..., description="Requested loan amount in INR.")
    purpose: str = Field(..., description="Purpose of the loan (travel, education, etc.).")
    income: Optional[float] = Field(None, description="Customer's disclosed annual income in INR.")


class KycPayload(BaseModel):
    pan: str = Field(..., description="Customer PAN in uppercase")
    dob: str = Field(..., description="Date of birth in YYYY-MM-DD format")
    phone: str = Field(..., description="Registered phone number")


def _sales_tool(user_input: str, session: LoanSession, llm) -> Dict[str, str]:
    parser_llm = llm.with_structured_output(LoanNeed)
    try:
        need = parser_llm.invoke(
            "Extract the customer's loan request details from this conversation: " + user_input
        )
    except Exception:
        need = LoanNeed(loan_amount=500000.0, purpose="general", income=None)

    product = recommend_product(amount=need.loan_amount, purpose=need.purpose)
    session.loan_request = {
        "raw_input": user_input,
        "loan_amount": need.loan_amount,
        "purpose": need.purpose,
        "income": need.income,
        "recommended_product": product,
    }
    session.advance_phase(Phase.KYC)

    if product:
        summary = (
            f"Captured your requirement for INR {need.loan_amount:,.0f} towards {need.purpose}.\n"
            f"Recommended product: **{product['name']}** at {product['interest_rate']}% for {product['tenure_months']} months.\n"
            "Let's verify your identity next (PAN, DOB, and phone)."
        )
    else:
        summary = (
            f"Logged your requirement for INR {need.loan_amount:,.0f} towards {need.purpose}.\n"
            "I couldn't find a direct product match, but we'll proceed with verification and tailor an offer."
        )
    return {"assistant_message": summary}


def _kyc_tool(user_input: str, session: LoanSession, llm) -> Dict[str, str]:
    parser_llm = llm.with_structured_output(KycPayload)
    try:
        payload = parser_llm.invoke(
            "Extract PAN, DOB (YYYY-MM-DD) and phone number from this response: " + user_input
        )
    except Exception:
        payload = _regex_parse_kyc(user_input)
        if not payload:
            return {
                "assistant_message": (
                    "I couldn't read your PAN/DOB/phone clearly. Please provide them in the format "
                    "PAN ABCDE1234F, DOB 1990-01-01, phone +91-90000..."
                )
            }

    result = verify_customer(payload.pan, payload.dob, payload.phone)
    if result.get("verified"):
        session.customer_profile = {
            "pan": payload.pan,
            "dob": payload.dob,
            "phone": payload.phone,
            "customer": result.get("customer"),
            "verified": True,
        }
        session.advance_phase(Phase.UNDERWRITING)
        message = (
            f"KYC verification successful for PAN {payload.pan}. "
            "Let's evaluate your eligibility next."
        )
    else:
        session.customer_profile = {
            "pan": payload.pan,
            "dob": payload.dob,
            "phone": payload.phone,
            "verified": False,
            "reason": result.get("reason"),
        }
        message = (
            "KYC verification failed: " + result.get("reason", "Unknown reason") +
            ". Please re-enter your PAN, DOB (YYYY-MM-DD) and phone number."
        )
    return {"assistant_message": message}


def _regex_parse_kyc(user_input: str) -> Optional[KycPayload]:
    pan_match = re.search(r"\b([A-Z]{5}[0-9]{4}[A-Z])\b", user_input.upper())
    dob_match = re.search(r"(\d{4}-\d{2}-\d{2})", user_input)
    phone_match = re.search(r"(\+?\d[\d\- ]{8,})", user_input)
    if not (pan_match and dob_match and phone_match):
        return None
    return KycPayload(
        pan=pan_match.group(1),
        dob=dob_match.group(1),
        phone=re.sub(r"[^\d+]", "", phone_match.group(1)),
    )


def _underwriting_tool(user_input: str, session: LoanSession) -> Dict[str, str]:
    session.underwriting_result = {"status": "pending", "notes": user_input}
    session.advance_phase(Phase.SANCTION)
    return {"assistant_message": "Underwriting stub finished. Preparing sanction letter."}


def _sanction_tool(user_input: str, session: LoanSession) -> Dict[str, str]:
    session.sanction_letter = {"path": "artifacts/demo.pdf"}
    session.advance_phase(Phase.COMPLETED)
    return {"assistant_message": "Sanction letter will be ready shortly."}


def create_sales_agent(llm, session: LoanSession) -> Tool:
    return Tool(
        name="SalesAgent",
        description="Captures loan request details and maps to the right product.",
        func=lambda user_input: _sales_tool(user_input, session, llm),
    )


def create_kyc_agent(llm, session: LoanSession) -> Tool:
    return Tool(
        name="KycAgent",
        description="Validates customer identity details.",
        func=lambda user_input: _kyc_tool(user_input, session, llm),
    )


def create_underwriting_agent(session: LoanSession) -> Tool:
    return Tool(
        name="UnderwritingAgent",
        description="Performs eligibility checks and approvals.",
        func=lambda user_input: _underwriting_tool(user_input, session),
    )


def create_sanction_agent(session: LoanSession) -> Tool:
    return Tool(
        name="SanctionAgent",
        description="Generates sanction letters.",
        func=lambda user_input: _sanction_tool(user_input, session),
    )
