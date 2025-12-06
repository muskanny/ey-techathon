from __future__ import annotations

from typing import Dict, Optional

from app.services import db


def recommend_product(amount: float, purpose: str) -> Optional[Dict[str, float]]:
    rows = db.fetchall(
        """
        SELECT * FROM loan_products
        WHERE purpose = ? AND ? BETWEEN min_amount AND max_amount
        ORDER BY interest_rate ASC
        LIMIT 1
        """,
        (purpose, amount),
    )
    if rows:
        row = rows[0]
        return {
            "id": row["id"],
            "name": row["name"],
            "interest_rate": row["interest_rate"],
            "tenure_months": row["tenure_months"],
            "description": row["description"],
        }

    fallback = db.fetchone(
        """
        SELECT * FROM loan_products WHERE purpose = ? ORDER BY max_amount DESC LIMIT 1
        """,
        (purpose,),
    )
    if fallback:
        return {
            "id": fallback["id"],
            "name": fallback["name"],
            "interest_rate": fallback["interest_rate"],
            "tenure_months": fallback["tenure_months"],
            "description": fallback["description"],
        }
    return None
