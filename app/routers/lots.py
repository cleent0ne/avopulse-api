import json
from datetime import datetime, date
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select
from pydantic import BaseModel
from app.models import Lot, Orchard, Farmer, Weighin, Payout, LedgerEntry, SAMPLE_RATES
from app.payments import payment_service

router = APIRouter(tags=["Hub Weigh-in & Settlement"])

def get_session():
    from app.seed import engine
    with Session(engine) as session:
        yield session

class WeighinRequest(BaseModel):
    export_kg: float
    oil_kg: float
    reject_kg: float
    gross_kg: float
    recorded_by: Optional[str] = "Hub Officer - Kisii Central"

@router.get("/lots")
def list_lots(status: Optional[str] = Query(None), session: Session = Depends(get_session)):
    """Incoming queue and status view for the weighbridge."""
    query = select(Lot, Orchard, Farmer).where(
        Lot.orchard_id == Orchard.id,
        Orchard.farmer_id == Farmer.id
    )
    if status:
        query = query.where(Lot.status == status)
    query = query.order_by(Lot.created_at.desc())

    results = session.exec(query).all()
    lots_list = []
    for lot, orchard, farmer in results:
        # Check if weighed
        weighin = session.exec(select(Weighin).where(Weighin.lot_id == lot.id)).first()
        payout = session.exec(select(Payout).where(Payout.lot_id == lot.id)).first()

        lots_list.append({
            "id": lot.id,
            "lot_code": lot.lot_code,
            "status": lot.status,
            "created_at": lot.created_at.isoformat(),
            "orchard_id": orchard.id,
            "ward": orchard.ward,
            "est_tonnes": orchard.est_tonnes,
            "farmer_id": farmer.id,
            "farmer_name": farmer.name,
            "farmer_phone": farmer.phone,
            "farmer_group": farmer.group_name,
            "weighin": {
                "export_kg": weighin.export_kg,
                "oil_kg": weighin.oil_kg,
                "reject_kg": weighin.reject_kg,
                "gross_kg": weighin.gross_kg
            } if weighin else None,
            "payout": {
                "net_payout": payout.net_payout,
                "mpesa_receipt": payout.mpesa_receipt,
                "created_at": payout.created_at.isoformat()
            } if payout else None
        })

    return lots_list

@router.post("/lots/{id}/weighin")
def weighin_lot(id: int, req: WeighinRequest, session: Session = Depends(get_session)):
    lot = session.get(Lot, id)
    if not lot:
        raise HTTPException(status_code=404, detail="Lot not found")

    # Pure business logic: validate the 3-way split adds up to gross
    calculated_sum = round(req.export_kg + req.oil_kg + req.reject_kg, 1)
    if abs(calculated_sum - round(req.gross_kg, 1)) > 0.2:
        raise HTTPException(
            status_code=400,
            detail=f"Validation failed: export ({req.export_kg} kg) + oil ({req.oil_kg} kg) + reject ({req.reject_kg} kg) = {calculated_sum} kg, does not equal gross ({req.gross_kg} kg)."
        )

    # Check for existing weighin or create new
    existing_weighin = session.exec(select(Weighin).where(Weighin.lot_id == id)).first()
    if existing_weighin:
        existing_weighin.export_kg = req.export_kg
        existing_weighin.oil_kg = req.oil_kg
        existing_weighin.reject_kg = req.reject_kg
        existing_weighin.gross_kg = req.gross_kg
        existing_weighin.recorded_by = req.recorded_by
        session.add(existing_weighin)
        weighin = existing_weighin
    else:
        weighin = Weighin(
            lot_id=lot.id,
            export_kg=req.export_kg,
            oil_kg=req.oil_kg,
            reject_kg=req.reject_kg,
            gross_kg=req.gross_kg,
            recorded_by=req.recorded_by
        )
        session.add(weighin)

    lot.status = "weighed"
    session.add(lot)
    session.commit()
    session.refresh(weighin)

    return {
        "message": f"Lot {lot.lot_code} successfully weighed and verified.",
        "lot_id": lot.id,
        "lot_code": lot.lot_code,
        "status": lot.status,
        "weighin": {
            "export_kg": weighin.export_kg,
            "oil_kg": weighin.oil_kg,
            "reject_kg": weighin.reject_kg,
            "gross_kg": weighin.gross_kg
        }
    }

@router.post("/lots/{id}/settle")
async def settle_lot(id: int, session: Session = Depends(get_session)):
    lot = session.get(Lot, id)
    if not lot:
        raise HTTPException(status_code=404, detail="Lot not found")

    weighin = session.exec(select(Weighin).where(Weighin.lot_id == id)).first()
    if not weighin:
        raise HTTPException(status_code=400, detail="Cannot settle an unweighed lot. Complete weighbridge intake first.")

    orchard = session.get(Orchard, lot.orchard_id)
    farmer = session.get(Farmer, orchard.farmer_id)

    # Settlement maths
    exp_amt = round(weighin.export_kg * SAMPLE_RATES["export_price_per_kg"], 2)
    oil_amt = round(weighin.oil_kg * SAMPLE_RATES["oil_price_per_kg"], 2)
    trans_fee = round(weighin.gross_kg * SAMPLE_RATES["transport_deduction_per_kg"], 2)
    grad_fee = round(weighin.gross_kg * SAMPLE_RATES["grading_fee_per_kg"], 2)
    net_payout = round(exp_amt + oil_amt - trans_fee - grad_fee, 2)

    line_items = [
        {
            "description": f"Verified Export Grade A ({weighin.export_kg:,.1f} kg @ KES {SAMPLE_RATES['export_price_per_kg']:.2f})",
            "amount": exp_amt,
            "type": "credit"
        },
        {
            "description": f"Oil-Grade Offtake Stream ({weighin.oil_kg:,.1f} kg @ KES {SAMPLE_RATES['oil_price_per_kg']:.2f})",
            "amount": oil_amt,
            "type": "credit"
        },
        {
            "description": f"Transport Deduction ({weighin.gross_kg:,.1f} kg @ KES {SAMPLE_RATES['transport_deduction_per_kg']:.2f})",
            "amount": -trans_fee,
            "type": "deduction"
        },
        {
            "description": f"AvoPulse Digital Hub Grading Fee ({weighin.gross_kg:,.1f} kg @ KES {SAMPLE_RATES['grading_fee_per_kg']:.2f})",
            "amount": -grad_fee,
            "type": "deduction"
        }
    ]

    # Trigger PaymentProvider (1.5-second realistic delay)
    payment_result = await payment_service.disburse(
        phone=farmer.phone,
        amount=net_payout,
        reference=lot.lot_code
    )

    # Store Payout
    existing_payout = session.exec(select(Payout).where(Payout.lot_id == id)).first()
    if existing_payout:
        existing_payout.net_payout = net_payout
        existing_payout.line_items_json = json.dumps(line_items)
        existing_payout.mpesa_receipt = payment_result["receipt"]
        payout = existing_payout
    else:
        payout = Payout(
            lot_id=lot.id,
            farmer_id=farmer.id,
            export_amount=exp_amt,
            oil_amount=oil_amt,
            transport_deduction=trans_fee,
            grading_fee_deduction=grad_fee,
            net_payout=net_payout,
            line_items_json=json.dumps(line_items),
            mpesa_receipt=payment_result["receipt"],
            mpesa_phone=farmer.phone,
            status="paid"
        )
        session.add(payout)

    lot.status = "settled"
    session.add(lot)
    session.commit()

    # Append to Farmer Ledger
    last_ledger = session.exec(
        select(LedgerEntry).where(LedgerEntry.farmer_id == farmer.id).order_by(LedgerEntry.id.desc())
    ).first()
    prev_balance = last_ledger.running_balance if last_ledger else 0.0

    ledger_entry = LedgerEntry(
        farmer_id=farmer.id,
        lot_id=lot.id,
        kg_settled=weighin.gross_kg,
        net_paid=net_payout,
        running_balance=prev_balance + net_payout,
        reference=f"M-PESA {payment_result['receipt']}",
        date=date.today(),
        note=f"Settlement for {lot.lot_code} ({weighin.export_kg:.0f}kg export, {weighin.oil_kg:.0f}kg oil)"
    )
    session.add(ledger_entry)
    session.commit()

    return {
        "status": "SETTLED",
        "lot_code": lot.lot_code,
        "farmer_name": farmer.name,
        "farmer_phone": farmer.phone,
        "net_payout": net_payout,
        "mpesa_receipt": payment_result["receipt"],
        "timestamp": payment_result["timestamp"],
        "line_items": line_items,
        "gross_kg": weighin.gross_kg,
        "export_kg": weighin.export_kg,
        "oil_kg": weighin.oil_kg,
        "reject_kg": weighin.reject_kg
    }

