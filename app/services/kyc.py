from __future__ import annotations

from typing import Dict, Optional

from app.services import db


def fetch_customer_by_pan(pan: str) -> Optional[Dict[str, str]]:
    row = db.fetchone(
        "SELECT * FROM customers WHERE pan = ?",
        (pan.upper(),),
    )
    if not row:
        return None
    return {
        "name": row["name"],
        "pan": row["pan"],
        "dob": row["dob"],
        "phone": row["phone"],
        "income": row["income"],
    }


def record_kyc_event(pan: str, outcome: str, reason: str | None = None) -> None:
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO kyc_events (pan, outcome, reason) VALUES (?, ?, ?)",
        (pan.upper(), outcome, reason),
    )
    conn.commit()
    conn.close()


def verify_customer(pan: str, dob: str, phone: str) -> Dict[str, str | bool]:
    customer = fetch_customer_by_pan(pan)
    if not customer:
        record_kyc_event(pan, "failed", "PAN not found")
        return {"verified": False, "reason": "PAN not found in records."}

    if customer["dob"] != dob:
        record_kyc_event(pan, "failed", "DOB mismatch")
        return {"verified": False, "reason": "Date of birth does not match."}

    if customer["phone"] != phone:
        record_kyc_event(pan, "failed", "Phone mismatch")
        return {"verified": False, "reason": "Phone number does not match."}

    record_kyc_event(pan, "success", None)
    return {"verified": True, "customer": customer}
