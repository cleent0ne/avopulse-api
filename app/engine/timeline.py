from datetime import date
from typing import Dict, Any

# Standard KALRO / AFA maturity guidelines for Hass avocado in Kisii highlands (elevated 1,700m - 1,900m)
HASS_CONFIG = {
    "min_days_early": 140,      # Prior to 140 days: clearly below maturity
    "borderline_min": 150,     # 150 - 165 days: borderline transition
    "optimal_min": 166,        # 166 - 195 days: optimal commercial maturity (~23%+ dry matter)
    "late_max": 210            # Over 210: risk of over-maturity / drop
}

def evaluate_timeline(flowering_date: date, assessment_date: date = None) -> Dict[str, Any]:
    if assessment_date is None:
        assessment_date = date.today()
    
    days = (assessment_date - flowering_date).days
    
    if days < HASS_CONFIG["borderline_min"]:
        score = max(0.1, min(0.45, days / HASS_CONFIG["borderline_min"] * 0.45))
        band = "below target"
        reason = f"Flowering was {days} days ago. Hass in Kisii highlands needs at least {HASS_CONFIG['borderline_min']} days to accumulate oil."
    elif days < HASS_CONFIG["optimal_min"]:
        score = 0.5 + ((days - HASS_CONFIG["borderline_min"]) / (HASS_CONFIG["optimal_min"] - HASS_CONFIG["borderline_min"])) * 0.2
        band = "borderline"
        reason = f"Flowering was {days} days ago. In borderline maturity window ({HASS_CONFIG['borderline_min']}-{HASS_CONFIG['optimal_min']} days)."
    else:
        score = min(0.95, 0.75 + ((days - HASS_CONFIG["optimal_min"]) / 30.0) * 0.2)
        band = "likely at or above 23%"
        reason = f"Flowering was {days} days ago ({days // 30} months). Exceeds the {HASS_CONFIG['optimal_min']}-day commercial harvest threshold."
        
    return {
        "days_since_flowering": days,
        "timeline_score": score,
        "timeline_band": band,
        "reason": reason
    }

