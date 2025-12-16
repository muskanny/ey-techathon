# app/services/underwriting.py

from app.state import LoanSession

def perform_eligibility_check(session: LoanSession) -> dict:
    """Performs a basic check to see if the customer is eligible for the requested loan."""
    
    # --- CRITICAL CHANGE: Use income from the loan_request dictionary ---
    # This income field now holds the self-disclosed income collected by the agent.
    customer_income = session.loan_request.get("income")
    
    # Defensive check: This should ideally be caught by the agent, but good practice to check here too
    if customer_income is None:
         return {
            "status": "REJECTED",
            "reason": "Income data is missing from the loan application.",
            "approved_amount": 0.0,
        }

    loan_amount = session.loan_request["loan_amount"]
    
    # Simple Business Rule: Income must be at least 3 times the loan amount
    REQUIRED_INCOME_RATIO = 3.0
    required_income = loan_amount * REQUIRED_INCOME_RATIO

    if customer_income >= required_income:
        return {
            "status": "APPROVED",
            "reason": "Self-disclosed income meets required loan-to-income ratio and creditworthiness criteria.",
            "approved_amount": loan_amount,
        }
    else:
        return {
            "status": "REJECTED",
            "reason": (
                f"Your self-disclosed annual income (INR {customer_income:,.0f}) is below the required minimum "
                f"for the requested loan amount of INR {loan_amount:,.0f} (Required minimum: INR {required_income:,.0f})."
            ),
            "approved_amount": 0.0,
        }