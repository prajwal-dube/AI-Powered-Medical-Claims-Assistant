from datetime import date
from decimal import Decimal

from .models import ExtractedClaim, Flag

REQUIRED = ("patient_id", "diagnosis", "procedure", "amount", "service_date")


def review_claim(claim: ExtractedClaim, duplicate: bool = False) -> list[Flag]:
    flags = [Flag(code=f"missing_{field}", detail=f"{field.replace('_', ' ').title()} is missing")
             for field in REQUIRED if getattr(claim, field) is None]
    if claim.amount is not None and claim.amount <= Decimal("0"):
        flags.append(Flag(code="invalid_amount", detail="Amount must be greater than zero"))
    if claim.amount is not None and claim.amount > Decimal("100000"):
        flags.append(Flag(code="high_amount", detail="Amount exceeds demo review threshold (100000)"))
    if claim.service_date:
        try:
            parsed = date.fromisoformat(claim.service_date)
            if parsed > date.today():
                flags.append(Flag(code="future_date", detail="Service date is in the future"))
        except ValueError:
            flags.append(Flag(code="invalid_date", detail="Service date must be YYYY-MM-DD"))
    if duplicate:
        flags.append(Flag(code="possible_duplicate", detail="Same normalized claim fields appeared earlier"))
    return flags
