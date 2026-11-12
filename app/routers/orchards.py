import os
import json
import uuid
from datetime import datetime, date
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlmodel import Session, select
from app.models import Orchard, Farmer, Assessment, Lot
from app.engine.gate import check_photo_quality
from app.engine.vision import analyze_visual
from app.engine.timeline import evaluate_timeline
from app.engine.combine import combine_assessments
from pydantic import BaseModel

router = APIRouter(tags=["Orchards & Assessments"])

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "media", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

def get_session():
    from app.seed import engine
    with Session(engine) as session:
        yield session

class SignoffRequest(BaseModel):
    decision: str  # "harvest" or "hold"
    override_note: Optional[str] = None

@router.get("/orchards")
def list_orchards(ward: Optional[str] = None, session: Session = Depends(get_session)):
    query = select(Orchard, Farmer).where(Orchard.farmer_id == Farmer.id)
    if ward:
        query = query.where(Orchard.ward == ward)
    results = session.exec(query).all()
    
    orchards_list = []
    for orchard, farmer in results:
        orchards_list.append({
            "id": orchard.id,
            "farmer_id": farmer.id,
            "farmer_name": farmer.name,
            "farmer_phone": farmer.phone,
            "farmer_group": farmer.group_name,
            "ward": orchard.ward,
            "trees": orchard.trees,
            "est_tonnes": orchard.est_tonnes,
            "flowering_date": orchard.flowering_date.isoformat(),
            "status": orchard.status,
            "variety": orchard.variety
        })
    return orchards_list

@router.get("/orchards/{id}")
def get_orchard(id: int, session: Session = Depends(get_session)):
    orchard = session.get(Orchard, id)
    if not orchard:
        raise HTTPException(status_code=404, detail="Orchard not found")
    farmer = session.get(Farmer, orchard.farmer_id)
    
    # Get any recent assessments
    assessments = session.exec(
        select(Assessment).where(Assessment.orchard_id == id).order_by(Assessment.created_at.desc())
    ).all()

    return {
        "id": orchard.id,
        "farmer_id": farmer.id if farmer else None,
        "farmer_name": farmer.name if farmer else "Unknown",
        "farmer_phone": farmer.phone if farmer else "",
        "ward": orchard.ward,
        "trees": orchard.trees,
        "est_tonnes": orchard.est_tonnes,
        "flowering_date": orchard.flowering_date.isoformat(),
        "status": orchard.status,
        "variety": orchard.variety,
        "recent_assessments": [
            {
                "id": a.id,
                "ai_band": a.ai_band,
                "confidence": a.confidence,
                "reasons": a.reasons,
                "grader_decision": a.grader_decision,
                "override_note": a.override_note,
                "created_at": a.created_at.isoformat()
            } for a in assessments[:3]
        ]
    }

@router.post("/orchards/{id}/assessments")
async def create_assessment(
    id: int,
    photos: List[UploadFile] = File(...),
    flowering_date_str: Optional[str] = Form(None),
    live_ai: bool = Form(True),
    session: Session = Depends(get_session)
):
    orchard = session.get(Orchard, id)
    if not orchard:
        raise HTTPException(status_code=404, detail="Orchard not found")

    if not photos:
        raise HTTPException(status_code=400, detail="At least one photo of the cut fruit is required.")

    # 1. Read files and run Quality Gate
    photo_bytes_list = []
    photo_urls = []
    filenames = []

    for photo in photos[:2]:
        content = await photo.read()
        photo_bytes_list.append(content)
        filenames.append(photo.filename)

        # Gate check on the first photo
        if len(photo_bytes_list) == 1:
            gate_res = check_photo_quality(content)
            if not gate_res["passed"]:
                raise HTTPException(
                    status_code=422,
                    detail=f"Photo Quality Gate failed: {gate_res['message']}"
                )

        # Save to media/uploads
        ext = os.path.splitext(photo.filename)[1] or ".jpg"
        saved_filename = f"orchard_{id}_{uuid.uuid4().hex[:6]}{ext}"
        saved_path = os.path.join(UPLOAD_DIR, saved_filename)
        with open(saved_path, "wb") as f:
            f.write(content)
        photo_urls.append(f"/media/uploads/{saved_filename}")

    # 2. Timeline prior evaluation
    try:
        f_date = date.fromisoformat(flowering_date_str) if flowering_date_str else orchard.flowering_date
    except Exception:
        f_date = orchard.flowering_date

    timeline_data = evaluate_timeline(f_date)

    # 3. Visual reading with Anthropic API or pre-cached fallback
    visual_data = await analyze_visual(photo_bytes_list, filenames, live_ai=live_ai)

    # 4. Combine weighted logic
    combined = combine_assessments(visual_data, timeline_data)

    # 5. Store Assessment record
    assessment = Assessment(
        orchard_id=orchard.id,
        photos_json=json.dumps(photo_urls),
        ai_band=combined["band"],
        confidence=combined["confidence"],
        reasons_json=json.dumps(combined["reasons"]),
        visual_flesh_score=combined.get("visual_score"),
        seed_coat_color=combined.get("seed_coat_color"),
        days_since_flowering=combined.get("days_since_flowering"),
        source=visual_data.get("source", "cached")
    )
    session.add(assessment)
    session.commit()
    session.refresh(assessment)

    return {
        "assessment_id": assessment.id,
        "orchard_id": orchard.id,
        "ai_band": assessment.ai_band,
        "confidence": assessment.confidence,
        "reasons": assessment.reasons,
        "source": assessment.source,
        "photos": assessment.photos,
        "visual_score": assessment.visual_flesh_score,
        "seed_coat_color": assessment.seed_coat_color,
        "days_since_flowering": assessment.days_since_flowering,
        "created_at": assessment.created_at.isoformat()
    }

@router.post("/assessments/{id}/signoff")
def signoff_assessment(id: int, req: SignoffRequest, session: Session = Depends(get_session)):
    assessment = session.get(Assessment, id)
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")

    orchard = session.get(Orchard, assessment.orchard_id)
    if not orchard:
        raise HTTPException(status_code=404, detail="Orchard not found")

    decision = req.decision.lower()
    if decision not in ["harvest", "hold"]:
        raise HTTPException(status_code=400, detail="Decision must be 'harvest' or 'hold'")

    assessment.grader_decision = decision
    assessment.override_note = req.override_note
    session.add(assessment)

    created_lot = None
    if decision == "harvest":
        orchard.status = "cleared"
        # Create a new Lot for the weighbridge queue
        lot_code = f"LOT-KIS-{datetime.utcnow().strftime('%m%d')}-{uuid.uuid4().hex[:4].upper()}"
        lot = Lot(
            lot_code=lot_code,
            orchard_id=orchard.id,
            assessment_id=assessment.id,
            status="incoming"
        )
        session.add(lot)
        session.commit()
        session.refresh(lot)
        created_lot = {
            "lot_id": lot.id,
            "lot_code": lot.lot_code,
            "status": lot.status
        }
    else:
        orchard.status = "hold"
        session.commit()

    session.add(orchard)
    session.commit()

    return {
        "message": f"Orchard {orchard.id} signed off as {decision.upper()}",
        "assessment_id": assessment.id,
        "orchard_status": orchard.status,
        "grader_decision": decision,
        "override_note": assessment.override_note,
        "lot": created_lot
    }

