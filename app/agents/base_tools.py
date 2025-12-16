from __future__ import annotations
import re

from typing import Dict, Optional
from datetime import datetime

from langchain_core.tools import Tool

from pydantic import BaseModel, Field # <--- CORRECT

from app.services.products import recommend_product
from app.services.kyc import verify_customer
from app.services.underwriting import perform_eligibility_check
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
        
        # --- START OF MODIFICATION ---
        customer_data = result.get("customer", {})
        
        # CRITICAL FIX: Explicitly remove the 'income' key from the fetched customer data.
        # This prevents the verified income from being stored in the session.customer_profile.
        if "income" in customer_data:
            del customer_data["income"] 
            
        session.customer_profile = {
            "pan": payload.pan,
            "dob": payload.dob,
            "phone": payload.phone,
            "customer": customer_data, # Use the cleaned customer_data without income
            "verified": True,
        }
        # --- END OF MODIFICATION ---
        
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
    
    # -----------------------------------------------------------
    # STEP 1: CONDITIONAL INCOME COLLECTION
    # Check if income is missing from the loan request (it should be, since the user didn't provide it initially)
    # -----------------------------------------------------------
    if session.loan_request.get("income") is None:
        
        # Try to parse income from the user's current message
        # This is a simplified regex; a real system would use the LLM to parse this reliably.
        income_match = re.search(r"(\d+([.,]\d+)?)\s*(lakh|lac|k|inr)", user_input, re.IGNORECASE)
        
        if income_match:
            # Income provided now. Parse and store it in the loan_request.
            amount_str = income_match.group(1).replace(",", "")
            unit = income_match.group(3).lower()
            
            income_value = float(amount_str)
            if unit in ["lakh", "lac"]:
                income_value *= 100000
            elif unit == "k":
                income_value *= 1000
                
            # Update the loan request with the self-disclosed income
            session.loan_request["income"] = income_value
            # Now, the code falls through to STEP 2 (the eligibility check)
            
        else:
            # Income is still missing and the user didn't provide it in this turn.
            # Ask the user and stop the tool execution.
            return {
                "assistant_message": (
                    "Thank you for the verification. To proceed with the eligibility check, "
                    "please provide your **annual income** in INR (e.g., '15 lakhs' or '800000')."
                )
            }
            # Phase remains UNDERWRITING, which ensures this tool is run again next time.
    
    # -----------------------------------------------------------
    # STEP 2: RUN ELIGIBILITY CHECK (Only reached if income is now present)
    # -----------------------------------------------------------
    result = perform_eligibility_check(session) # This now uses session.loan_request["income"]
    
    session.underwriting_result = {
        "status": result["status"], 
        "notes": result["reason"],
        "approved_amount": result["approved_amount"],
    }

    if result["status"] == "APPROVED":
        session.advance_phase(Phase.SANCTION)
        message = (
            f"**Eligibility Check Complete:** Your loan is Approved for INR {result['approved_amount']:,.0f}. "
            "Proceeding to prepare your sanction letter."
        )
    else:
        # Stop the process if rejected
        session.advance_phase(Phase.COMPLETED) 
        message = (
            f"**Application Rejected:** {result['reason']} "
            "We cannot proceed with the loan at this time."
        )
    
    return {"assistant_message": message}

def _sanction_tool(user_input: str, session: LoanSession) -> Dict[str, str]:
    # --- Data Retrieval ---
    loan_data = session.loan_request
    product = loan_data["recommended_product"]
    approved_amount = session.underwriting_result.get("approved_amount", loan_data["loan_amount"])
    customer_name = session.customer_profile["customer"].get("name", "Valued Customer")
    pan_id = session.customer_profile["pan"]
    
    sanction_path = f"artifacts/{customer_name.replace(' ', '_')}_Sanction_Letter.pdf" 
    
    # --- Generate Letter Content ---
    letter_content = f"""
### Sanction Letter - Loan Approval
**Reference No:** LSA-{pan_id[:5]}-2025

**Date:** {datetime.now().strftime("%B %d, %Y")}

**Applicant:** {customer_name}
**PAN:** {pan_id}

---

Dear {customer_name},

We are pleased to inform you that your loan application has been **APPROVED**. This sanction letter outlines the key terms of your agreement:

| Parameter | Details |
| :--- | :--- |
| **Product** | {product['name']} |
| **Sanctioned Amount** | **INR {approved_amount:,.0f}** |
| **Purpose** | {loan_data['purpose'].title()} |
| **Interest Rate** | {product['interest_rate']}% p.a. (Fixed) |
| **Tenure** | {product['tenure_months']} Months |

**Terms and Conditions:**
1. The sanctioned amount is subject to final document verification.
2. Disbursal will be made within 3 business days of signing the agreement.

Thank you for choosing us.

Sincerely,
The Loans Team
"""
    
    session.sanction_letter = {
        "path": sanction_path,
        "content": letter_content, # <-- NEW: Store the generated Markdown text
    }
    session.advance_phase(Phase.COMPLETED)
    
    message = (
        "**Congratulations!** Your sanction letter has been successfully generated. "
        "Please review the document below and use the link to download the final PDF."
    )
    return {"assistant_message": message}

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
