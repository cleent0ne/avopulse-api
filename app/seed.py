import os
import json
from datetime import datetime, date, timedelta, timezone
from sqlmodel import SQLModel, Session, create_engine, select
from app.models import Farmer, Orchard, Assessment, Booking, Lot, Weighin, Payout, LedgerEntry, SAMPLE_RATES

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./AvoPulse.db")
engine = create_engine(DATABASE_URL, echo=False)

def seed_database():
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        # 1. Seed 12 Farmers across 5 Kisii Wards
        farmers_data = [
            # Star farmer with extensive history
            {"id": 1, "name": "Jared Mogaka", "phone": "0722104589", "ward": "Nyaribari Chache", "group_name": "Keumbu Avocado Producers Co-op"},
            {"id": 2, "name": "Mary Kemunto", "phone": "0711452901", "ward": "Nyaribari Chache", "group_name": "Keumbu Avocado Producers Co-op"},
            {"id": 3, "name": "Peter Onyancha", "phone": "0723891045", "ward": "Nyaribari Chache", "group_name": "Birongo Growers Association"},
            {"id": 4, "name": "Agnes Nyaboke", "phone": "0728340123", "ward": "Kitutu Chache", "group_name": "Marani Valley Orchards"},
            {"id": 5, "name": "David Ombati", "phone": "0734567812", "ward": "Kitutu Chache", "group_name": "Marani Valley Orchards"},
            {"id": 6, "name": "Bosire Motari", "phone": "0712984510", "ward": "Bonchari", "group_name": "Suneka Organic Smallholders"},
            {"id": 7, "name": "Jane Kerubo", "phone": "0725671234", "ward": "Bonchari", "group_name": "Suneka Organic Smallholders"},
            {"id": 8, "name": "Evans Makori", "phone": "0718456123", "ward": "South Mugirango", "group_name": "Tabaka Hills Cooperative"},
            {"id": 9, "name": "Hellen Moraa", "phone": "0729876543", "ward": "South Mugirango", "group_name": "Tabaka Hills Cooperative"},
            {"id": 10, "name": "George Nyambane", "phone": "0710234567", "ward": "Bobasi", "group_name": "Nyamache Commercial Cluster"},
            {"id": 11, "name": "Beatrice Kwamboka", "phone": "0724112233", "ward": "Bobasi", "group_name": "Nyamache Commercial Cluster"},
            {"id": 12, "name": "Samuel Osoro", "phone": "0733998877", "ward": "Bobasi", "group_name": "Emanwa Farm Group"}
        ]
        
        for fd in farmers_data:
            f = Farmer(
                id=fd["id"],
                name=fd["name"],
                phone=fd["phone"],
                ward=fd["ward"],
                group_name=fd["group_name"],
                created_at=datetime.now(timezone.utc)
            )
            session.add(f)
        session.commit()

        # 2. Seed 18 Orchards (6 unassessed, 4 on hold, 8 cleared)
        today = date.today()
        orchards_data = [
            # Jared's Demo Target Orchard (Cleared / ready for harvest loop)
            {"id": 1, "farmer_id": 1, "ward": "Nyaribari Chache", "trees": 120, "flowering_date": today - timedelta(days=175), "est_tonnes": 4.8, "status": "unassessed"},
            # Jared's 2nd Orchard
            {"id": 2, "farmer_id": 1, "ward": "Nyaribari Chache", "trees": 85, "flowering_date": today - timedelta(days=140), "est_tonnes": 3.2, "status": "hold"},
            # Mary Kemunto
            {"id": 3, "farmer_id": 2, "ward": "Nyaribari Chache", "trees": 150, "flowering_date": today - timedelta(days=172), "est_tonnes": 6.0, "status": "cleared"},
            # Peter Onyancha
            {"id": 4, "farmer_id": 3, "ward": "Nyaribari Chache", "trees": 60, "flowering_date": today - timedelta(days=168), "est_tonnes": 2.4, "status": "cleared"},
            {"id": 5, "farmer_id": 3, "ward": "Nyaribari Chache", "trees": 45, "flowering_date": today - timedelta(days=130), "est_tonnes": 1.6, "status": "hold"},
            # Agnes Nyaboke
            {"id": 6, "farmer_id": 4, "ward": "Kitutu Chache", "trees": 110, "flowering_date": today - timedelta(days=176), "est_tonnes": 4.5, "status": "cleared"},
            {"id": 7, "farmer_id": 4, "ward": "Kitutu Chache", "trees": 70, "flowering_date": today - timedelta(days=142), "est_tonnes": 2.8, "status": "hold"},
            # David Ombati
            {"id": 8, "farmer_id": 5, "ward": "Kitutu Chache", "trees": 95, "flowering_date": today - timedelta(days=170), "est_tonnes": 3.8, "status": "cleared"},
            {"id": 9, "farmer_id": 5, "ward": "Kitutu Chache", "trees": 50, "flowering_date": today - timedelta(days=135), "est_tonnes": 1.9, "status": "unassessed"},
            # Bosire Motari
            {"id": 10, "farmer_id": 6, "ward": "Bonchari", "trees": 140, "flowering_date": today - timedelta(days=174), "est_tonnes": 5.6, "status": "cleared"},
            {"id": 11, "farmer_id": 6, "ward": "Bonchari", "trees": 65, "flowering_date": today - timedelta(days=132), "est_tonnes": 2.2, "status": "unassessed"},
            # Jane Kerubo
            {"id": 12, "farmer_id": 7, "ward": "Bonchari", "trees": 80, "flowering_date": today - timedelta(days=169), "est_tonnes": 3.1, "status": "cleared"},
            # Evans Makori
            {"id": 13, "farmer_id": 8, "ward": "South Mugirango", "trees": 130, "flowering_date": today - timedelta(days=171), "est_tonnes": 5.1, "status": "cleared"},
            {"id": 14, "farmer_id": 9, "ward": "South Mugirango", "trees": 75, "flowering_date": today - timedelta(days=145), "est_tonnes": 2.9, "status": "hold"},
            {"id": 15, "farmer_id": 9, "ward": "South Mugirango", "trees": 90, "flowering_date": today - timedelta(days=138), "est_tonnes": 3.4, "status": "unassessed"},
            # George Nyambane
            {"id": 16, "farmer_id": 10, "ward": "Bobasi", "trees": 160, "flowering_date": today - timedelta(days=177), "est_tonnes": 6.5, "status": "cleared"},
            {"id": 17, "farmer_id": 11, "ward": "Bobasi", "trees": 85, "flowering_date": today - timedelta(days=133), "est_tonnes": 3.0, "status": "unassessed"},
            # Samuel Osoro
            {"id": 18, "farmer_id": 12, "ward": "Bobasi", "trees": 55, "flowering_date": today - timedelta(days=136), "est_tonnes": 2.0, "status": "unassessed"}
        ]

        for od in orchards_data:
            session.add(Orchard(**od))
        session.commit()

        # 3. Seed Forward Bookings from 3 Exporters
        bookings_data = [
            {"id": 1, "exporter_name": "East African Fresh Ltd", "week": "2026-W46", "tonnes": 16.0, "status": "confirmed", "created_at": datetime.now(timezone.utc)},
            {"id": 2, "exporter_name": "Kisii Highlands Greens", "week": "2026-W46", "tonnes": 10.5, "status": "confirmed", "created_at": datetime.now(timezone.utc)},
            {"id": 3, "exporter_name": "Serengeti Organics", "week": "2026-W46", "tonnes": 8.0, "status": "confirmed", "created_at": datetime.now(timezone.utc)},
            {"id": 4, "exporter_name": "East African Fresh Ltd", "week": "2026-W47", "tonnes": 22.0, "status": "confirmed", "created_at": datetime.now(timezone.utc)},
            {"id": 5, "exporter_name": "Kisii Highlands Greens", "week": "2026-W47", "tonnes": 14.0, "status": "confirmed", "created_at": datetime.now(timezone.utc)},
            {"id": 6, "exporter_name": "Serengeti Organics", "week": "2026-W48", "tonnes": 25.0, "status": "pending", "created_at": datetime.now(timezone.utc)}
        ]
        for bd in bookings_data:
            session.add(Booking(**bd))
        session.commit()

        # 4. Seed Historical Assessments & Star Farmer Ledger (Jared Mogaka, Farmer 1)
        history_batches = [
            {"lot_code": "LOT-KIS-2026-0518", "orchard_id": 1, "days_ago": 180, "gross": 2100.0, "exp_pct": 0.82, "oil_pct": 0.14, "rej_pct": 0.04, "rcpt": "QL31A7M92X"},
            {"lot_code": "LOT-KIS-2026-0622", "orchard_id": 1, "days_ago": 145, "gross": 2450.0, "exp_pct": 0.85, "oil_pct": 0.12, "rej_pct": 0.03, "rcpt": "QM44K2P81Y"},
            {"lot_code": "LOT-KIS-2026-0810", "orchard_id": 1, "days_ago": 95, "gross": 1950.0, "exp_pct": 0.84, "oil_pct": 0.13, "rej_pct": 0.03, "rcpt": "QP89T3W40Z"},
            {"lot_code": "LOT-KIS-2026-0919", "orchard_id": 1, "days_ago": 55, "gross": 2800.0, "exp_pct": 0.86, "oil_pct": 0.11, "rej_pct": 0.03, "rcpt": "QR12F8L55M"},
            {"lot_code": "LOT-KIS-2026-1028", "orchard_id": 1, "days_ago": 14, "gross": 3100.0, "exp_pct": 0.87, "oil_pct": 0.10, "rej_pct": 0.03, "rcpt": "QS67V4B19K"}
        ]

        running_balance = 0.0
        for i, batch in enumerate(history_batches):
            past_date = today - timedelta(days=batch["days_ago"])
            past_dt = datetime.combine(past_date, datetime.min.time(), tzinfo=timezone.utc)
            
            # Assessment
            ass = Assessment(
                orchard_id=batch["orchard_id"],
                photos_json=json.dumps(["/media/samples/sample_mature_1.jpg", "/media/samples/sample_mature_2.jpg"]),
                ai_band="likely at or above 23%",
                confidence=0.93,
                reasons_json=json.dumps([
                    "Buttery golden flesh texture; dark brown seed coat cleanly separated.",
                    f"Flowering timeline ({170 + i} days) comfortably exceeds export threshold.",
                    "Pre-harvest grading verified by Keumbu Ward Inspector."
                ]),
                visual_flesh_score=0.88,
                seed_coat_color="brown",
                days_since_flowering=175,
                grader_decision="harvest",
                override_note="AFA Grader signed off for export batch picking",
                source="live",
                created_at=past_dt
            )
            session.add(ass)
            session.commit()

            # Lot
            lot = Lot(
                lot_code=batch["lot_code"],
                orchard_id=batch["orchard_id"],
                assessment_id=ass.id,
                booking_id=1,
                status="settled",
                created_at=past_dt
            )
            session.add(lot)
            session.commit()

            # Weighin
            gross = batch["gross"]
            exp_kg = round(gross * batch["exp_pct"], 1)
            oil_kg = round(gross * batch["oil_pct"], 1)
            rej_kg = round(gross - exp_kg - oil_kg, 1)

            weigh = Weighin(
                lot_id=lot.id,
                export_kg=exp_kg,
                oil_kg=oil_kg,
                reject_kg=rej_kg,
                gross_kg=gross,
                recorded_by="Hub Officer - Keumbu Aggregation Hub",
                created_at=past_dt + timedelta(hours=4)
            )
            session.add(weigh)
            session.commit()

            # Payout math
            exp_amt = round(exp_kg * SAMPLE_RATES["export_price_per_kg"], 2)
            oil_amt = round(oil_kg * SAMPLE_RATES["oil_price_per_kg"], 2)
            trans_fee = round(gross * SAMPLE_RATES["transport_deduction_per_kg"], 2)
            grad_fee = round(gross * SAMPLE_RATES["grading_fee_per_kg"], 2)
            net_amt = round(exp_amt + oil_amt - trans_fee - grad_fee, 2)

            line_items = [
                {"description": f"Export Grade A ({exp_kg:,.1f} kg @ KES {SAMPLE_RATES['export_price_per_kg']:.2f})", "amount": exp_amt, "type": "credit"},
                {"description": f"Oil Grade Extraction ({oil_kg:,.1f} kg @ KES {SAMPLE_RATES['oil_price_per_kg']:.2f})", "amount": oil_amt, "type": "credit"},
                {"description": f"Direct Field Transport ({gross:,.1f} kg @ KES {SAMPLE_RATES['transport_deduction_per_kg']:.2f})", "amount": -trans_fee, "type": "deduction"},
                {"description": f"AvoPulse Digital Hub Grading Fee ({gross:,.1f} kg @ KES {SAMPLE_RATES['grading_fee_per_kg']:.2f})", "amount": -grad_fee, "type": "deduction"}
            ]

            payout = Payout(
                lot_id=lot.id,
                farmer_id=1,
                export_amount=exp_amt,
                oil_amount=oil_amt,
                transport_deduction=trans_fee,
                grading_fee_deduction=grad_fee,
                net_payout=net_amt,
                line_items_json=json.dumps(line_items),
                mpesa_receipt=batch["rcpt"],
                mpesa_phone="0722104589",
                status="paid",
                created_at=past_dt + timedelta(hours=5)
            )
            session.add(payout)
            session.commit()

            # Ledger
            running_balance += net_amt
            ledger = LedgerEntry(
                farmer_id=1,
                lot_id=lot.id,
                kg_settled=gross,
                net_paid=net_amt,
                running_balance=running_balance,
                reference=f"M-PESA {batch['rcpt']}",
                date=past_date,
                note=f"Settlement for {batch['lot_code']} ({exp_kg:.0f}kg export, {oil_kg:.0f}kg oil)"
            )
            session.add(ledger)
            session.commit()

        # 5. Seed one INCOMING unweighed lot ready for the Hub Officer demo
        mary_ass = Assessment(
            orchard_id=3,
            photos_json=json.dumps(["/media/samples/sample_mature_1.jpg", "/media/samples/sample_mature_2.jpg"]),
            ai_band="likely at or above 23%",
            confidence=0.94,
            reasons_json=json.dumps([
                "Flesh reveals deep creamy yellow coloration spanning 82% of surface.",
                "Brown papery seed coat cleanly detached with no adhering cotyledon.",
                "172 days maturity prior fully aligns with dry-matter requirement."
            ]),
            visual_flesh_score=0.89,
            seed_coat_color="brown",
            days_since_flowering=172,
            grader_decision="harvest",
            override_note="Verified by Grader: Cleared for harvest",
            source="cached",
            created_at=datetime.now(timezone.utc) - timedelta(hours=2)
        )
        session.add(mary_ass)
        session.commit()

        demo_lot = Lot(
            lot_code="LOT-KIS-2026-1111",
            orchard_id=3,
            assessment_id=mary_ass.id,
            booking_id=1,
            status="incoming",
            created_at=datetime.now(timezone.utc) - timedelta(hours=1)
        )
        session.add(demo_lot)
        session.commit()

    print("Database seeded successfully with Kisii data model.")

if __name__ == "__main__":
    seed_database()
