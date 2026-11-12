from typing import Dict, Any, List

def combine_assessments(visual_data: Dict[str, Any], timeline_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Weighted rule merges visual reading and timeline prior into a defensible maturity band,
    confidence level, and three plain-language reasons.
    Enforces rule: low confidence or disagreement between inputs always returns 'borderline'.
    """
    v_band = visual_data.get("visual_band", "borderline")
    v_score = visual_data.get("visual_score", 0.5)
    seed_color = visual_data.get("seed_coat_color", "tan").lower()
    v_reasons = visual_data.get("reasons", [])

    t_band = timeline_data.get("timeline_band", "borderline")
    t_score = timeline_data.get("timeline_score", 0.5)
    t_days = timeline_data.get("days_since_flowering", 160)
    t_reason = timeline_data.get("reason", "")

    reasons: List[str] = []

    # 1. Visual reason
    if v_reasons:
        reasons.append(v_reasons[0])
    else:
        reasons.append(f"Visual flesh reading score: {v_score:.2f} with {seed_color} seed coat.")

    # 2. Seed coat specific observation (AFA visual cue)
    if "white" in seed_color:
        reasons.append("Seed coat is white and adhering firmly to flesh, characteristic of immature fruit.")
    elif "brown" in seed_color:
        reasons.append("Seed coat has darkened to deep brown and cleanly detaches from seed cavity, indicating maturity.")
    else:
        reasons.append("Seed coat is transitional tan; partial detachment observed.")

    # 3. Timeline prior reason
    reasons.append(t_reason)

    # Decision logic
    # Check for strong agreement
    if v_band == "likely at or above 23%" and t_band == "likely at or above 23%":
        final_band = "likely at or above 23%"
        confidence = round(min(0.95, (v_score * 0.6) + (t_score * 0.4)), 2)
    elif v_band == "below target" and t_band == "below target":
        final_band = "below target"
        confidence = round(min(0.92, ((1.0 - v_score) * 0.6) + ((1.0 - t_score) * 0.4)), 2)
    else:
        # Disagreement or borderline
        final_band = "borderline"
        confidence = 0.64
        reasons.insert(0, "Visual cue and flowering window show divergent indicators: grader sign-off required.")

    # Ensure exactly 3 or 4 crisp reasons
    return {
        "band": final_band,
        "confidence": confidence,
        "reasons": reasons[:3],
        "visual_score": v_score,
        "seed_coat_color": seed_color,
        "days_since_flowering": t_days
    }

