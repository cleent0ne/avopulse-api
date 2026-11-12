from fastapi import APIRouter
from pydantic import BaseModel
import uuid

router = APIRouter(prefix="/auth", tags=["Auth"])

class DemoLoginRequest(BaseModel):
    role: str  # grader, hub, exporter, farmer

@router.post("/demo-login")
def demo_login(req: DemoLoginRequest):
    """
    Demo login returning a signed demo token and role persona.
    Eliminates password friction during stage pitch.
    """
    role = req.role.lower()
    personas = {
        "grader": {
            "name": "Dennis Omwamba",
            "title": "AFA-Certified Field Grader",
            "ward": "Nyaribari Chache",
            "hub": "Keumbu Aggregation Hub"
        },
        "hub": {
            "name": "Sarah Kwamboka",
            "title": "Weighbridge Operations Officer",
            "hub": "Kisii Central Hub #2"
        },
        "exporter": {
            "name": "Martin Kamau",
            "title": "Procurement Director",
            "company": "East African Fresh Ltd"
        },
        "farmer": {
            "name": "Jared Mogaka",
            "title": "Commercial Avocado Producer",
            "farmer_id": 1,
            "group": "Keumbu Avocado Producers Co-op"
        }
    }

    persona = personas.get(role, personas["grader"])
    token = f"AvoPulse_demo_{role}_{uuid.uuid4().hex[:8]}"

    return {
        "access_token": token,
        "token_type": "bearer",
        "role": role,
        "persona": persona
    }

