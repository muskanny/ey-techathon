from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


@dataclass
class Message:
    role: str
    content: str


class Phase(str, Enum):
    INTAKE = "intake"
    SALES = "sales"
    KYC = "kyc"
    UNDERWRITING = "underwriting"
    SANCTION = "sanction"
    COMPLETED = "completed"


@dataclass
class LoanSession:
    """Holds in-memory state for the demo loan journey."""

    messages: List[Message] = field(default_factory=list)
    phase: Phase = Phase.INTAKE
    loan_request: Optional[dict] = None
    customer_profile: Optional[dict] = None
    underwriting_result: Optional[dict] = None
    sanction_letter: Optional[dict] = None

    def add_message(self, role: str, content: str) -> None:
        self.messages.append(Message(role=role, content=content))

    def advance_phase(self, next_phase: Phase) -> None:
        self.phase = next_phase

    def status_summary(self) -> str:
        mapping = {
            Phase.INTAKE: "Collecting loan requirements",
            Phase.SALES: "Recommending loan products",
            Phase.KYC: "Running KYC verification",
            Phase.UNDERWRITING: "Evaluating eligibility",
            Phase.SANCTION: "Preparing sanction letter",
            Phase.COMPLETED: "Loan journey completed",
        }
        return mapping[self.phase]

    def serialize(self) -> dict:
        return {
            "phase": self.phase.value,
            "loan_request": self.loan_request,
            "customer_profile": self.customer_profile,
            "underwriting_result": self.underwriting_result,
            "sanction_letter": self.sanction_letter,
        }

    def reset(self) -> None:
        self.messages.clear()
        self.phase = Phase.INTAKE
        self.loan_request = None
        self.customer_profile = None
        self.underwriting_result = None
        self.sanction_letter = None
