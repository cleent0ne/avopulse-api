from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select
from typing import List, Optional
from pydantic import BaseModel
from app.models import Orchard, Booking

router = APIRouter(tags=["Supply & Exporter Bookings"])

def get_session():
    from app.seed import engine
    with Session(engine) as session:
        yield session

class CreateBookingRequest(BaseModel):
    exporter_name: str
    week: str  # e.g., "2026-W46"
    tonnes: float

@router.get("/supply")
def get_supply(week: str = Query("2026-W46"), session: Session = Depends(get_session)):
    """
    Returns verified mature tonnes by Kisii ward and week, plus hold-back tonnes,
    and compares against exporter forward commitments.
    """
    orchards = session.exec(select(Orchard)).all()
    bookings = session.exec(select(Booking).where(Booking.week == week)).all()

    wards_data = {}
    total_verified = 0.0
    total_holdback = 0.0

    for o in orchards:
        if o.ward not in wards_data:
            wards_data[o.ward] = {
                "ward": o.ward,
                "verified_mature_tonnes": 0.0,
                "holdback_tonnes": 0.0,
                "orchard_count": 0,
                "cleared_count": 0,
                "hold_count": 0
            }
        
        wards_data[o.ward]["orchard_count"] += 1
        if o.status == "cleared":
            wards_data[o.ward]["verified_mature_tonnes"] += o.est_tonnes
            wards_data[o.ward]["cleared_count"] += 1
            total_verified += o.est_tonnes
        else:
            wards_data[o.ward]["holdback_tonnes"] += o.est_tonnes
            wards_data[o.ward]["hold_count"] += 1
            total_holdback += o.est_tonnes

    # Round ward tonnages
    by_ward = []
    for w, d in wards_data.items():
        d["verified_mature_tonnes"] = round(d["verified_mature_tonnes"], 1)
        d["holdback_tonnes"] = round(d["holdback_tonnes"], 1)
        by_ward.append(d)

    total_booked = sum(b.tonnes for b in bookings)
    coverage_ratio = round((total_verified / total_booked * 100), 1) if total_booked > 0 else 100.0

    return {
        "week": week,
        "total_verified_mature_tonnes": round(total_verified, 1),
        "total_holdback_tonnes": round(total_holdback, 1),
        "total_forward_booked_tonnes": round(total_booked, 1),
        "coverage_ratio_pct": coverage_ratio,
        "market_status": "adequately supplied" if total_verified >= total_booked else "under-supplied",
        "by_ward": by_ward,
        "bookings": [
            {
                "id": b.id,
                "exporter_name": b.exporter_name,
                "week": b.week,
                "tonnes": b.tonnes,
                "status": b.status
            } for b in bookings
        ]
    }

@router.get("/bookings")
def list_bookings(week: Optional[str] = None, session: Session = Depends(get_session)):
    query = select(Booking)
    if week:
        query = query.where(Booking.week == week)
    bookings = session.exec(query).all()
    return bookings

@router.post("/bookings")
def create_booking(req: CreateBookingRequest, session: Session = Depends(get_session)):
    if req.tonnes <= 0:
        raise HTTPException(status_code=400, detail="Booking tonnage must be greater than 0")

    booking = Booking(
        exporter_name=req.exporter_name,
        week=req.week,
        tonnes=round(req.tonnes, 1),
        status="confirmed"
    )
    session.add(booking)
    session.commit()
    session.refresh(booking)

    return {
        "message": f"Successfully forward-booked {booking.tonnes} tonnes for {booking.exporter_name}",
        "booking": booking
    }

