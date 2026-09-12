"""
Ledger Lens — Demo Data Generator

IMPORTANT: This module generates SYNTHETIC project records for demonstration purposes.
These are NOT government records. They are clearly labeled throughout the system.

The synthetic projects are built on top of REAL MP allocation data so that:
- MP names, constituencies, states are real
- Financial amounts are realistic (derived from real allocation limits)
- Risk patterns are diverse and demonstrative

Every synthetic record has:
- is_demo_record=True
- data_source="SYNTHETIC_DEMO"

This is displayed prominently in the UI with a "DEMO DATA" banner.
"""

import random
from datetime import date, timedelta
from typing import List, Dict
import numpy as np
import pandas as pd


WORK_CATEGORIES = [
    "Road Construction", "Road Repair", "Bridge Construction",
    "Drinking Water Supply", "Drainage & Sewerage", "School Building",
    "Anganwadi Centre", "Community Hall", "Health Centre",
    "Solar Street Lights", "Park Development", "Sports Facility",
    "Pond Renovation", "Canal Repair", "Check Dam",
    "Cremation Ground", "Public Toilet", "Library",
]

SECTORS = [
    "Infrastructure", "Water Supply", "Education", "Health",
    "Rural Development", "Urban Development", "Environment", "Energy",
]

WORK_DESCRIPTIONS = {
    "Road Construction": [
        "Construction of cement concrete road from {loc1} to {loc2}",
        "Construction of black-top road connecting {loc1} and {loc2} village",
        "Construction of approach road to {loc1} village",
        "Laying of CC road in {loc1} ward no. {ward}",
    ],
    "Road Repair": [
        "Repair and maintenance of road from {loc1} to {loc2}",
        "Resurfacing of damaged road near {loc1} market",
        "Repairing of potholed road in {loc1} area",
    ],
    "Drinking Water Supply": [
        "Supply and installation of hand pump at {loc1} village",
        "Construction of overhead water tank at {loc1}",
        "Laying of water supply pipeline in {loc1} colony",
        "Renovation of drinking water well at {loc1}",
    ],
    "School Building": [
        "Construction of additional classroom at Government School {loc1}",
        "Construction of boundary wall at Government Primary School {loc1}",
        "Construction of toilet block at Government School {loc1}",
    ],
    "Solar Street Lights": [
        "Installation of solar street lights at {loc1} village",
        "Supply and installation of LED solar street lights in {loc1} ward",
        "Installation of {count} solar street lights from {loc1} to {loc2}",
    ],
    "Community Hall": [
        "Construction of multipurpose community hall at {loc1}",
        "Renovation and repair of community hall at {loc1} village",
    ],
    "Health Centre": [
        "Construction of additional room at Primary Health Centre {loc1}",
        "Renovation of Sub Health Centre at {loc1}",
    ],
    "Anganwadi Centre": [
        "Construction of Anganwadi centre building at {loc1}",
        "Renovation of Anganwadi Kendra at {loc1} village",
    ],
    "Bridge Construction": [
        "Construction of small bridge over {loc1} nallah",
        "Construction of culvert at {loc1} village road",
    ],
    "Drainage & Sewerage": [
        "Construction of drainage channel in {loc1} colony",
        "Renovation of drain from {loc1} to {loc2}",
    ],
    "Park Development": [
        "Development of public park at {loc1}",
        "Beautification of garden at {loc1} ward",
    ],
    "Sports Facility": [
        "Construction of volleyball court at {loc1}",
        "Renovation of playground at {loc1} village",
    ],
    "Pond Renovation": [
        "Renovation and desilting of village pond at {loc1}",
        "Development of pond at {loc1} for water conservation",
    ],
    "Canal Repair": [
        "Repair of irrigation canal in {loc1} area",
        "Desilting of {loc1} minor irrigation canal",
    ],
    "Check Dam": [
        "Construction of check dam across {loc1} nallah",
        "Renovation of existing check dam at {loc1}",
    ],
    "Cremation Ground": [
        "Development of cremation ground at {loc1} village",
        "Construction of shed at cremation ground {loc1}",
    ],
    "Public Toilet": [
        "Construction of public toilet complex at {loc1} bus stand",
        "Construction of toilet block at {loc1} market area",
    ],
    "Library": [
        "Construction of library building at {loc1}",
        "Renovation of public library at {loc1}",
    ],
}

LOCATIONS = {
    "Uttar Pradesh": ["Lucknow", "Kanpur", "Agra", "Varanasi", "Allahabad", "Meerut", "Bareilly",
                      "Mathura", "Moradabad", "Aligarh", "Gorakhpur", "Ghaziabad"],
    "Maharashtra": ["Pune", "Nagpur", "Nashik", "Aurangabad", "Solapur", "Kolhapur", "Thane",
                    "Amravati", "Nanded", "Latur"],
    "West Bengal": ["Kolkata", "Howrah", "Darjeeling", "Siliguri", "Asansol", "Durgapur", "Bardhaman"],
    "Bihar": ["Patna", "Gaya", "Bhagalpur", "Muzaffarpur", "Darbhanga", "Purnia", "Arrah"],
    "Tamil Nadu": ["Chennai", "Coimbatore", "Madurai", "Trichy", "Salem", "Tirunelveli", "Erode"],
    "Madhya Pradesh": ["Bhopal", "Indore", "Jabalpur", "Gwalior", "Ujjain", "Sagar", "Rewa"],
    "Karnataka": ["Bengaluru", "Mysuru", "Hubli", "Mangaluru", "Belgaum", "Davangere", "Shimoga"],
    "Gujarat": ["Ahmedabad", "Surat", "Vadodara", "Rajkot", "Bhavnagar", "Jamnagar", "Gandhinagar"],
    "Andhra Pradesh": ["Vijayawada", "Visakhapatnam", "Tirupati", "Guntur", "Rajahmundry", "Kakinada"],
    "Rajasthan": ["Jaipur", "Jodhpur", "Udaipur", "Ajmer", "Kota", "Bikaner", "Alwar"],
}

DEFAULT_LOCATIONS = ["Sector 12", "Block A", "Ward 5", "Village Chandpur", "Nagar Panchayat Area"]


def _get_locations_for_state(state: str):
    return LOCATIONS.get(state, DEFAULT_LOCATIONS)


def _make_description(category: str, state: str, ward: int = 1) -> str:
    templates = WORK_DESCRIPTIONS.get(category, ["Construction work at {loc1}"])
    template = random.choice(templates)
    locs = _get_locations_for_state(state)
    loc1 = random.choice(locs)
    loc2 = random.choice([l for l in locs if l != loc1] or locs)
    count = random.choice([10, 15, 20, 25, 30])
    return template.format(loc1=loc1, loc2=loc2, count=count, ward=ward)


def generate_demo_projects(mp_df: pd.DataFrame, n_projects: int = 200, seed: int = 42) -> List[Dict]:
    """
    Generate synthetic demonstration projects using real MP data as the base.

    Args:
        mp_df: Cleaned MP allocation DataFrame (real official data)
        n_projects: Number of synthetic projects to generate
        seed: Random seed for reproducibility

    Returns:
        List of project dicts ready for DB insertion.
        ALL records have is_demo_record=True and data_source="SYNTHETIC_DEMO".
    """
    rng = random.Random(seed)
    np_rng = np.random.default_rng(seed)

    # Use valid MP rows (with known amounts)
    valid_mps = mp_df[mp_df["allocated_amount_inr"] > 0].copy()

    projects = []
    today = date.today()

    for i in range(n_projects):
        # Sample a real MP as the project's "parent"
        mp_row = valid_mps.sample(1, random_state=rng.randint(0, 10000)).iloc[0]

        state = mp_row["state"]
        mp_name = mp_row["mp_name"]
        constituency = mp_row["constituency_clean"]
        allocated = mp_row["allocated_amount_inr"]

        # Project financials: each project is a fraction of the MP's total allocation
        fraction = rng.uniform(0.01, 0.12)
        sanctioned_amount = round(allocated * fraction, 2)
        # Clamp to realistic MPLADS work range: ₹2L to ₹1.5Cr
        sanctioned_amount = max(200000, min(sanctioned_amount, 15000000))

        # Determine risk tier for this project (realistic distribution)
        risk_tier_draw = rng.random()
        if risk_tier_draw < 0.45:
            risk_tier = "low"
        elif risk_tier_draw < 0.75:
            risk_tier = "moderate"
        elif risk_tier_draw < 0.92:
            risk_tier = "high"
        else:
            risk_tier = "critical"

        # Sanction date
        days_ago = rng.randint(30, 1800)
        sanction_date = today - timedelta(days=days_ago)
        project_age_days = days_ago

        # Expected duration (180–730 days)
        expected_duration = rng.randint(180, 730)
        expected_completion_date = sanction_date + timedelta(days=expected_duration)

        # Physical progress and financial progress based on risk tier
        if risk_tier == "low":
            physical_progress_pct = rng.uniform(70, 100)
            utilization_ratio = rng.uniform(0.65, 0.95)
            delay_days = max(0, days_ago - expected_duration - rng.randint(0, 30))
            status = "Completed" if physical_progress_pct >= 95 else "In Progress"
        elif risk_tier == "moderate":
            physical_progress_pct = rng.uniform(40, 75)
            utilization_ratio = rng.uniform(0.50, 0.80)
            delay_days = max(0, days_ago - expected_duration + rng.randint(-60, 90))
            status = "In Progress"
        elif risk_tier == "high":
            physical_progress_pct = rng.uniform(15, 55)
            utilization_ratio = rng.uniform(0.55, 0.90)
            delay_days = max(0, days_ago - expected_duration + rng.randint(30, 200))
            status = rng.choice(["In Progress", "Stalled"])
        else:  # critical
            physical_progress_pct = rng.uniform(0, 35)
            utilization_ratio = rng.uniform(0.65, 1.10)  # Overspent or very high
            delay_days = max(0, days_ago - expected_duration + rng.randint(100, 400))
            status = rng.choice(["Stalled", "Under Review"])

        expenditure_amount = round(sanctioned_amount * utilization_ratio, 2)
        financial_progress_pct = min(utilization_ratio * 100, 100.0)
        payment_progress_gap = financial_progress_pct - physical_progress_pct

        # Category & sector
        category = rng.choice(WORK_CATEGORIES)
        sector_map = {
            "Road Construction": "Infrastructure", "Road Repair": "Infrastructure",
            "Bridge Construction": "Infrastructure", "Drainage & Sewerage": "Infrastructure",
            "Drinking Water Supply": "Water Supply", "School Building": "Education",
            "Anganwadi Centre": "Education", "Health Centre": "Health",
            "Solar Street Lights": "Energy", "Park Development": "Environment",
            "Sports Facility": "Rural Development", "Pond Renovation": "Environment",
            "Canal Repair": "Water Supply", "Check Dam": "Water Supply",
            "Cremation Ground": "Rural Development", "Public Toilet": "Urban Development",
            "Library": "Education", "Community Hall": "Rural Development",
        }
        sector = sector_map.get(category, "Rural Development")

        description = _make_description(category, state, rng.randint(1, 20))
        locs = _get_locations_for_state(state)
        district = rng.choice(locs)
        agency_options = [
            "Gram Panchayat", "Municipal Corporation", "PWD", "Nagar Panchayat",
            "DRDA", "Block Development Office", "Zila Parishad"
        ]
        implementing_agency = rng.choice(agency_options)

        project_id = f"MPLADS-{state[:2].upper()}-{sanction_date.year}-{i+1:04d}"

        projects.append({
            "project_id": project_id,
            "work_description": description,
            "work_category": category,
            "sector": sector,
            "state": state,
            "district": district,
            "constituency": constituency,
            "location_detail": f"{district}, {state}",
            "mp_name": mp_name,
            "mp_allocation_id": int(mp_row["sr_no"]),
            "sanctioned_amount": sanctioned_amount,
            "expenditure_amount": expenditure_amount,
            "utilization_ratio": round(utilization_ratio, 4),
            "implementing_agency": implementing_agency,
            "sanction_date": sanction_date.isoformat(),
            "start_date": (sanction_date + timedelta(days=rng.randint(7, 90))).isoformat(),
            "expected_completion_date": expected_completion_date.isoformat(),
            "actual_completion_date": (
                (expected_completion_date + timedelta(days=rng.randint(-30, 60))).isoformat()
                if status == "Completed" else None
            ),
            "project_age_days": project_age_days,
            "delay_days": delay_days,
            "physical_progress_pct": round(physical_progress_pct, 1),
            "financial_progress_pct": round(financial_progress_pct, 1),
            "payment_progress_gap": round(payment_progress_gap, 1),
            "status": status,
            "risk_tier_hint": risk_tier,  # used by risk engine
            "is_demo_record": True,
            "data_source": "SYNTHETIC_DEMO",
        })

    return projects
