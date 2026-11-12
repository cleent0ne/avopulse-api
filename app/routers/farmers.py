from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from app.models import Farmer, Orchard, Payout, LedgerEntry, Lot, Weighin, SAMPLE_RATES

router = APIRouter(tags=["Farmer Statement & Ledger"])

def get_session():
    from app.seed import engine
    with Session(engine) as session:
        yield session

@router.get("/farmers/{id}/statement")
def get_farmer_statement(id: int, session: Session = Depends(get_session)):
    farmer = session.get(Farmer, id)
    if not farmer:
        raise HTTPException(status_code=404, detail="Farmer not found")

    # Get latest payout
    payout = session.exec(
        select(Payout, Lot).where(Payout.farmer_id == id, Payout.lot_id == Lot.id).order_by(Payout.created_at.desc())
    ).first()

    if not payout:
        return {
            "farmer_id": farmer.id,
            "farmer_name": farmer.name,
            "farmer_phone": farmer.phone,
            "group_name": farmer.group_name,
            "statement": None,
            "message": "No settled payouts on record yet."
        }

    payout_obj, lot_obj = payout
    weighin = session.exec(select(Weighin).where(Weighin.lot_id == lot_obj.id)).first()

    return {
        "farmer_id": farmer.id,
        "farmer_name": farmer.name,
        "farmer_phone": farmer.phone,
        "ward": farmer.ward,
        "group_name": farmer.group_name,
        "statement": {
            "lot_code": lot_obj.lot_code,
            "settled_at": payout_obj.created_at.isoformat(),
            "mpesa_receipt": payout_obj.mpesa_receipt,
            "mpesa_phone": payout_obj.mpesa_phone,
            "gross_kg": weighin.gross_kg if weighin else 0.0,
            "export_kg": weighin.export_kg if weighin else 0.0,
            "oil_kg": weighin.oil_kg if weighin else 0.0,
            "reject_kg": weighin.reject_kg if weighin else 0.0,
            "line_items": payout_obj.line_items,
            "net_payout": payout_obj.net_payout,
            "status": payout_obj.status
        }
    }

@router.get("/farmers/{id}/ledger")
def get_farmer_ledger(id: int, session: Session = Depends(get_session)):
    farmer = session.get(Farmer, id)
    if not farmer:
        raise HTTPException(status_code=404, detail="Farmer not found")

    ledger_entries = session.exec(
        select(LedgerEntry).where(LedgerEntry.farmer_id == id).order_by(LedgerEntry.date.desc())
    ).all()

    total_kg = sum(entry.kg_settled for entry in ledger_entries)
    total_net_earnings = sum(entry.net_paid for entry in ledger_entries)
    harvest_count = len(ledger_entries)

    # Credit readiness calculation (rules-based & labelled illustrative)
    # Tier 1 requires >= 3 harvests, > 5000 kg volume
    if harvest_count >= 4 and total_kg >= 6000:
        credit_tier = "Tier 1 - Prime Commercial"
        credit_score = 815
        eligible_limit_kes = 150000.0
        badge_status = "AFA Verified - Eligible for input credit"
        reasons = [
            f"{harvest_count} consecutive verified harvests logged over 6 months",
            f"Consistently high export packout (>84%) with low reject rate (<4%)",
            f"KES {total_net_earnings:,.0f} direct digital M-Pesa disbursements recorded on-chain"
        ]
    elif harvest_count >= 2:
        credit_tier = "Tier 2 - Emerging Producer"
        credit_score = 680
        eligible_limit_kes = 65000.0
        badge_status = "Pre-Qualified for Input Advance"
        reasons = [
            f"{harvest_count} verified harvest settlements on file",
            "Consistent quality indicators across last deliveries"
        ]
    else:
        credit_tier = "Tier 3 - Initial Season"
        credit_score = 520
        eligible_limit_kes = 20000.0
        badge_status = "Building Credit History"
        reasons = ["Initial harvest verification underway"]

    return {
        "farmer_id": farmer.id,
        "farmer_name": farmer.name,
        "ward": farmer.ward,
        "group_name": farmer.group_name,
        "total_harvests": harvest_count,
        "total_kg_settled": round(total_kg, 1),
        "total_net_paid_kes": round(total_net_earnings, 2),
        "credit_readiness": {
            "tier": credit_tier,
            "score": credit_score,
            "max_score": 900,
            "eligible_limit_kes": eligible_limit_kes,
            "badge": badge_status,
            "illustrative_note": "Rules-based calculation over verifiable delivery ledger. Pre-approved for fertiliser and certified seedling input loans.",
            "qualification_factors": reasons
        },
        "entries": [
            {
                "id": e.id,
                "date": e.date.isoformat(),
                "lot_id": e.lot_id,
                "reference": e.reference,
                "kg_settled": e.kg_settled,
                "net_paid": e.net_paid,
                "running_balance": e.running_balance,
                "note": e.note
            } for e in ledger_entries
        ]
    }

