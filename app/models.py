from datetime import datetime, date, timezone
from typing import Optional, List
from sqlmodel import SQLModel, Field
import json

def get_utc_now():
    return datetime.now(timezone.utc)

class Farmer(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    phone: str
    ward: str
    group_name: str
    created_at: datetime = Field(default_factory=get_utc_now)

class Orchard(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    farmer_id: int = Field(foreign_key="farmer.id")
    ward: str
    trees: int
    flowering_date: date
    est_tonnes: float
    status: str = Field(default="unassessed")  # unassessed, hold, cleared
    variety: str = Field(default="Hass")

class Assessment(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    orchard_id: int = Field(foreign_key="orchard.id")
    photos_json: str = Field(default="[]")  # List of URLs or file paths
    ai_band: str  # "below target", "borderline", "likely at or above 23%"
    confidence: float
    reasons_json: str = Field(default="[]")  # 3 plain-language reasons
    visual_flesh_score: Optional[float] = None
    seed_coat_color: Optional[str] = None  # white, tan, brown
    days_since_flowering: Optional[int] = None
    grader_decision: Optional[str] = None  # "harvest", "hold"
    override_note: Optional[str] = None
    source: str = Field(default="cached")  # "live" or "cached"
    created_at: datetime = Field(default_factory=get_utc_now)

    @property
    def photos(self) -> List[str]:
        try:
            return json.loads(self.photos_json)
        except Exception:
            return []

    @property
    def reasons(self) -> List[str]:
        try:
            return json.loads(self.reasons_json)
        except Exception:
            return []

class Booking(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    exporter_name: str
    week: str  # e.g., "2026-W46"
    tonnes: float
    status: str = Field(default="confirmed")  # confirmed, pending, fulfilled
    created_at: datetime = Field(default_factory=get_utc_now)

class Lot(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    lot_code: str = Field(unique=True, index=True)
    orchard_id: int = Field(foreign_key="orchard.id")
    assessment_id: int = Field(foreign_key="assessment.id")
    booking_id: Optional[int] = Field(default=None, foreign_key="booking.id")
    status: str = Field(default="incoming")  # incoming, weighed, settled
    created_at: datetime = Field(default_factory=get_utc_now)

class Weighin(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    lot_id: int = Field(foreign_key="lot.id", unique=True)
    export_kg: float
    oil_kg: float
    reject_kg: float
    gross_kg: float
    recorded_by: str = Field(default="Hub Officer - Kisii Central")
    created_at: datetime = Field(default_factory=get_utc_now)

class Payout(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    lot_id: int = Field(foreign_key="lot.id", unique=True)
    farmer_id: int = Field(foreign_key="farmer.id")
    export_amount: float
    oil_amount: float
    transport_deduction: float
    grading_fee_deduction: float
    net_payout: float
    line_items_json: str = Field(default="[]")
    mpesa_receipt: str
    mpesa_phone: str
    status: str = Field(default="paid")
    created_at: datetime = Field(default_factory=get_utc_now)

    @property
    def line_items(self) -> List[dict]:
        try:
            return json.loads(self.line_items_json)
        except Exception:
            return []

class LedgerEntry(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    farmer_id: int = Field(foreign_key="farmer.id", index=True)
    lot_id: Optional[int] = Field(default=None, foreign_key="lot.id")
    kg_settled: float
    net_paid: float
    running_balance: float
    reference: str
    date: date
    note: str

# Sample rate configurations as defined in the plan
SAMPLE_RATES = {
    "export_price_per_kg": 95.0,     # KES per kg for verified export grade
    "oil_price_per_kg": 38.0,        # KES per kg for off-grade extraction
    "transport_deduction_per_kg": 4.5, # KES per kg
    "grading_fee_per_kg": 3.0        # KES per kg verification charge
}

