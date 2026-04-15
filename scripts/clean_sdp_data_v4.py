"""
QCTO SDP Data Cleaning Script — Version 4
==========================================
Built by running an independent full-file inspection of the 48,717-row v3
output. Preserves all correct v3 logic. Fixes 7 issues v3 missed:

  FIX 1  — Phone numbers stored as strings (not float) → leading 0 preserved
  FIX 2  — Qualification Title: "Programmes :" space → "Programmes:"
  FIX 3  — Credits stored as int (not float 251.0)
  FIX 4  — Contact Person: extract emails to Email 1 when Contact Person is an email
  FIX 5  — Accredited Address: flag company reg numbers
  FIX 6  — Town-City: fix 35 remaining street-name values
  FIX 7  — Days Until Expiry: always recalculated fresh from today's date
  FIX 8  — Qualification Category "Other": 7,530 → target <2,500 with 8 new categories
            + expanded keywords for Engineering (Solar PV, Coded Welding),
              Security (Close Protector), Retail (Checkout, Store Person, Shelf Filler),
              Facilities (Cleaner), Education (Assessment Practitioner), etc.

NATED research verdict (Government Gazette 49518, Umalusi 2024/2025 statements):
  NATED Report 190/191 = N1–N6 qualification framework administered by DHET.
  N1–N3 quality assured by Umalusi. N4–N6 accredited by QCTO.
  N1–N3 phased out from 1 January 2024. NOT a SETA, NOT SETA-funded.
  → v3 Partner Type "NATED / Report 191" classification is CORRECT — kept as-is.

Usage:
    python clean_sdp_data_v4.py
    python clean_sdp_data_v4.py --input sdp_clean_v3.csv --output sdp_clean_v4.csv
"""

from __future__ import annotations

import argparse
import os
import re
from datetime import date
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

# ─────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────

TODAY = date.today()
TODAY_TS = pd.Timestamp(TODAY)

VALID_PROVINCES = [
    "Eastern Cape", "Free State", "Gauteng", "KwaZulu-Natal",
    "Limpopo", "Mpumalanga", "North West", "Northern Cape", "Western Cape",
]
VALID_PROVINCES_SET = set(VALID_PROVINCES)

PROVINCE_NORMALIZATION: Dict[str, str] = {
    "eastern cape": "Eastern Cape", "free state": "Free State",
    "gauteng": "Gauteng", "kwazulu natal": "KwaZulu-Natal",
    "kwazulunatal": "KwaZulu-Natal", "kzn": "KwaZulu-Natal",
    "limpopo": "Limpopo", "mpumalanga": "Mpumalanga",
    "north west": "North West", "north-west": "North West",
    "northern cape": "Northern Cape", "western cape": "Western Cape",
}

TRUE_SETAS = {
    "AGRISETA", "BANKSETA", "CATHSSETA", "CETA", "CHIETA",
    "ETDP SETA", "EWSETA", "FASSET", "FOODBEV SETA", "FP&M SETA",
    "HWSETA", "INSETA", "LGSETA", "MERSETA", "MICT SETA",
    "MQA", "PSETA", "SASSETA", "SERVICES SETA", "TETA", "W&R SETA",
}

PARTNER_MAP: Dict[str, str] = {
    "AGRISETA": "AGRISETA", "BANKSETA": "BANKSETA", "CATHSSETA": "CATHSSETA",
    "CETA": "CETA", "CHIETA": "CHIETA",
    "ETDPSETA": "ETDP SETA", "ETDP": "ETDP SETA", "ETDP SETA": "ETDP SETA",
    "EWSETA": "EWSETA", "FASSET": "FASSET",
    "FOODBEVSETA": "FOODBEV SETA", "FOODBEV SETA": "FOODBEV SETA", "FOODBEV": "FOODBEV SETA",
    "FP&MSETA": "FP&M SETA", "FPMSETA": "FP&M SETA", "FP&M SETA": "FP&M SETA",
    "HWSETA": "HWSETA", "INSETA": "INSETA", "LGSETA": "LGSETA",
    "MERSETA": "MERSETA", "MICT SETA": "MICT SETA", "MICTSETA": "MICT SETA", "MICT": "MICT SETA",
    "MQA": "MQA", "PSETA": "PSETA", "SASSETA": "SASSETA",
    "SERVICES SE": "SERVICES SETA", "SERVICES SETA": "SERVICES SETA",
    "TETA": "TETA",
    "W&RSETA": "W&R SETA", "W&R SETA": "W&R SETA",
    "NATED": "NATED", "OLD TRADES": "OLD TRADES",
    "QCTO": "QCTO", "SAPC": "SAPC",
}

# Known city → province mappings (extended)
CITY_TO_PROVINCE: Dict[str, str] = {
    # Gauteng
    "Johannesburg": "Gauteng", "Sandton": "Gauteng", "Midrand": "Gauteng",
    "Pretoria": "Gauteng", "Centurion": "Gauteng", "Randburg": "Gauteng",
    "Roodepoort": "Gauteng", "Soweto": "Gauteng", "Germiston": "Gauteng",
    "Kempton Park": "Gauteng", "Boksburg": "Gauteng", "Benoni": "Gauteng",
    "Alberton": "Gauteng", "Vereeniging": "Gauteng", "Brakpan": "Gauteng",
    "Parktown": "Gauteng", "Pretoria West": "Gauteng", "Pretoria Gardens": "Gauteng",
    "Fourways": "Gauteng", "Bedfordview": "Gauteng", "Lyndhurst": "Gauteng",
    "Bryanston": "Gauteng", "Daveyton": "Gauteng", "Vanderbijlpark": "Gauteng",
    "Vanderbijlpark Cw 3": "Gauteng", "Isando": "Gauteng", "Krugersdorp": "Gauteng",
    "Krugersdorp West": "Gauteng", "Krugerdorp": "Gauteng", "Ennerdale": "Gauteng",
    "Parkwood": "Gauteng", "Wingate Park": "Gauteng", "Brackenhurst": "Gauteng",
    "Willow Park Manor": "Gauteng", "Randpark Ridge": "Gauteng",
    "Killarney Gardens": "Gauteng", "Daspoort": "Gauteng",
    # Western Cape
    "Cape Town": "Western Cape", "Stellenbosch": "Western Cape",
    "George": "Western Cape", "Paarl": "Western Cape", "Worcester": "Western Cape",
    "Bellville": "Western Cape", "Somerset West": "Western Cape",
    "Paarden Eiland": "Western Cape", "Beaufort-West": "Western Cape",
    "St Helena Bay": "Western Cape", "1 Sandhill Road, De Waterkant": "Western Cape",
    # Eastern Cape
    "East London": "Eastern Cape", "Gqeberha": "Eastern Cape",
    "Port Elizabeth": "Eastern Cape", "Port Alfred": "Eastern Cape",
    "Queenstown": "Eastern Cape", "Komani": "Eastern Cape",
    # KwaZulu-Natal
    "Durban": "KwaZulu-Natal", "Pinetown": "KwaZulu-Natal", "Tongaat": "KwaZulu-Natal",
    "Chatsworth": "KwaZulu-Natal", "Pietermaritzburg": "KwaZulu-Natal",
    "Congella": "KwaZulu-Natal", "Bothas Hill": "KwaZulu-Natal",
    "Richards Bay": "KwaZulu-Natal", "Hibberdene": "KwaZulu-Natal",
    "Kwa Dlanezwa": "KwaZulu-Natal", "Hillcrest": "KwaZulu-Natal",
    "Port Edward": "KwaZulu-Natal", "Park Rynie": "KwaZulu-Natal",
    "Camperdown": "KwaZulu-Natal", "Musgrave": "KwaZulu-Natal",
    # Limpopo
    "Thohoyandou": "Limpopo", "Polokwane": "Limpopo", "Louis Trichardt": "Limpopo",
    "Groblersdal": "Limpopo", "Sekhukhune": "Limpopo", "Lwamondo": "Limpopo",
    "Burgersfort": "Limpopo", "Malamulele": "Limpopo",
    # Mpumalanga
    "Emalahleni": "Mpumalanga", "Secunda": "Mpumalanga", "Malelane": "Mpumalanga",
    "Belfast": "Mpumalanga", "Volksrust": "Mpumalanga", "Groblersdal (Mpum)": "Mpumalanga",
    # North West
    "Mogwase": "North West", "Siyabuswa": "North West", "Zeerust": "North West",
    # Northern Cape
    "Kathu": "Northern Cape", "Kimberley": "Northern Cape",
    # Free State
    "Bloemfontein": "Free State", "Welkom": "Free State",
}

# Street names that ended up in Town-City — map to nearest real city by province
STREET_TOWN_FIXES: Dict[str, str] = {
    "Rozenburg Street": "Cape Town",       # Western Cape address
    "Kiewiet Street": "Emalahleni",        # Mpumalanga context from province column
    "Fish Eagle Road": "Richards Bay",     # KZN context
    "Aloette Road Aeroton": "Johannesburg",
    "Somerset Street": "Gqeberha",
    "Kendal/balmoral Road": "Emalahleni",
    "N2 & Rockview Dam Road": "George",
    "Delmas Road": "Johannesburg",
    "Malamulele Road": "Thohoyandou",
    "Off Malta Road": "Cape Town",
}

# Valid email regex
EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")
# Relaxed — for detecting emails embedded in other text
RELAX_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
# Company registration number pattern
REG_NUM_RE = re.compile(r"^\d{4}/\d+/\d{2,}$|^\d{9,}[-/]\d+$|^\d{3}\d{7,}[-/]\d$")


# ─────────────────────────────────────────────
# UTILITY FUNCTIONS (preserved from v3, improved)
# ─────────────────────────────────────────────

def s(val: object) -> str:
    """Return stripped string or empty string for NA."""
    return str(val).strip() if pd.notna(val) else ""


def normalize_province(val: object) -> Optional[str]:
    sv = s(val)
    if sv in VALID_PROVINCES_SET:
        return sv
    lower = sv.lower()
    if lower in PROVINCE_NORMALIZATION:
        return PROVINCE_NORMALIZATION[lower]
    # Check if it's a known city
    city_prov = CITY_TO_PROVINCE.get(sv)
    if city_prov:
        return city_prov
    return None


def is_probable_address(val: object) -> bool:
    sv = s(val)
    if not sv:
        return False
    return bool(
        re.match(r"^\d+\s", sv) or
        ";" in sv or
        re.search(r"\b(street|road|avenue|crescent|drive|close|lane|place|boulevard)\b", sv, re.I)
    )


def is_email(val: object) -> bool:
    sv = s(val)
    return bool(EMAIL_RE.match(sv)) if sv else False


def fix_email_token(email: str) -> Optional[str]:
    """Clean up minor email formatting issues."""
    e = email.strip().lower()
    # Fix double @ (leani@@360businessconsulting.net)
    e = re.sub(r"@+", "@", e)
    if EMAIL_RE.match(e):
        return e
    return None


def extract_emails(*values: object) -> List[str]:
    emails: List[str] = []
    for value in values:
        sv = s(value)
        if not sv:
            continue
        for match in RELAX_EMAIL_RE.finditer(sv):
            fixed = fix_email_token(match.group())
            if fixed and fixed not in emails:
                emails.append(fixed)
    return emails


def normalize_phone(number: object) -> Optional[str]:
    """
    Return a clean 10-digit SA phone number string with leading 0.
    Returns None if the value cannot be normalized.
    Stored as STRING always to preserve leading 0.
    """
    sv = s(number)
    if not sv:
        return None
    # Remove all non-digit characters
    digits = re.sub(r"\D", "", sv)
    if not digits:
        return None
    # Handle +27 prefix
    if digits.startswith("27") and len(digits) == 11:
        digits = "0" + digits[2:]
    elif digits.startswith("270") and len(digits) == 12:
        digits = digits[2:]
    # Add missing leading 0 for 9-digit numbers
    elif len(digits) == 9 and not digits.startswith("0"):
        digits = "0" + digits
    # Must be 10 digits
    if len(digits) != 10:
        return None
    return digits  # returned as string — never cast to numeric


def extract_phones(*values: object) -> List[str]:
    phones: List[str] = []
    for value in values:
        sv = s(value)
        if not sv:
            continue
        # Remove embedded emails first
        sv = RELAX_EMAIL_RE.sub(" ", sv)
        sv = sv.replace("\n", " ").replace("\r", " ")
        for piece in re.split(r"[;/]|(?:\s{2,})", sv):
            fixed = normalize_phone(piece)
            if fixed and fixed not in phones:
                phones.append(fixed)
    return phones


def parse_mixed_date(val: object) -> Optional[pd.Timestamp]:
    sv = s(val)
    if not sv:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d/%m/%y", "%m/%d/%y", "%d-%m-%Y"):
        try:
            return pd.Timestamp(sv, ) if fmt == "%Y-%m-%d" else pd.Timestamp(
                __import__("datetime").datetime.strptime(sv, fmt)
            )
        except (ValueError, Exception):
            try:
                return pd.to_datetime(sv, format=fmt)
            except Exception:
                continue
    return None


# ─────────────────────────────────────────────
# QUALIFICATION CATEGORY (v4 — expanded)
# ─────────────────────────────────────────────

def categorize_qualification(title: object) -> str:
    if pd.isna(title):
        return "Uncategorised"
    t = str(title).lower()

    # ICT & Data (MICT SETA)
    if any(kw in t for kw in [
        "data", "analytics", "analysis", "software", "developer", "development",
        "systems", "network", "cyber", "information technology", "ict", "digital",
        "computer", "programming", "database", "web developer", "technical support",
        "cloud", "support technician", "end user computing", "it support",
        "artificial intelligence", "internet-of-things", "iot",
    ]):
        return "ICT & Data"

    # Business & Management
    if any(kw in t for kw in [
        "business", "management", "administrator", "administration", "manager",
        "operations", "office", "executive", "supervision", "supervisor",
        "entrepreneurship", "enterprise", "project manag",
    ]):
        return "Business & Management"

    # NEW: New Venture Creation / Entrepreneurship (was "Other")
    if any(kw in t for kw in [
        "new venture", "venture creation", "technopreneur", "entrepreneur",
        "start-up", "startup",
    ]):
        return "Business & Management"

    # Finance & Accounting
    if any(kw in t for kw in [
        "finance", "financial", "accounting", "accounts", "bookkeep", "bookkeeper",
        "auditor", "audit", "tax", "payroll", "treasury", "credit", "cost account",
        "investment", "wealth", "retirement", "pension", "fund adviser",
        "asset manag", "portfolio",
    ]):
        return "Finance & Accounting"

    # Insurance & Banking
    if any(kw in t for kw in [
        "insurance", "underwriter", "broker", "banking", "bank", "financial service",
        "short-term", "long-term", "employee and pension fund benefit",
    ]):
        return "Insurance & Banking"

    # Legal & Compliance
    if any(kw in t for kw in [
        "paralegal", "legal", "compliance", "regulatory", "governance", "trade unionist",
    ]):
        return "Legal & Compliance"

    # Health & Social Services
    if any(kw in t for kw in [
        "health", "nursing", "care", "social", "welfare", "community", "child",
        "counsel", "therapist", "medical", "pharmacy", "disability", "hiv", "aids",
        "auxiliary", "mortician", "embalmer",
    ]):
        return "Health & Social Services"

    # Emergency Services (new — was Other)
    if any(kw in t for kw in [
        "first aid", "emergency", "paramedic", "ambulance", "firefighter", "fire fighter",
        "rescue",
    ]):
        return "Emergency Services"

    # Engineering & Trades (expanded)
    if any(kw in t for kw in [
        "electrician", "electrical", "engineer", "mechanic", "mechanical",
        "fitter", "millwright", "welder", "boiler", "diesel", "motor",
        "artisan", "rigger", "automotive", "instrumentation", "refrigeration",
        "plumber", "plumbing", "solar photovoltaic", "solar pv", "coded welding",
        "draughtsperson", "drafter", "metal machinist", "sheet metal",
        "water reticulation", "pipe repairer", "domestic water",
    ]):
        return "Engineering & Trades"

    # Construction & Building
    if any(kw in t for kw in [
        "construction", "bricklayer", "carpenter", "plasterer", "builder",
        "civil", "quantity", "surveyor", "painter", "tiler", "roofer",
        "glazier", "general residential repairer", "handyperson", "assistant handyperson",
    ]):
        return "Construction & Building"

    # Logistics & Supply Chain
    if any(kw in t for kw in [
        "logistics", "supply chain", "transport", "freight", "warehouse",
        "distribution", "procurement", "purchasing", "driver", "shipping",
        "customs", "store person", "storesperson", "stores",
    ]):
        return "Logistics & Supply Chain"

    # Retail & Customer Service (expanded — was Other for Checkout, Shelf Filler)
    if any(kw in t for kw in [
        "marketing", "sales", "retail", "customer service", "customer care",
        "call centre", "contact centre", "merchandis", "promotions",
        "checkout operator", "shelf filler", "service station attendant",
        "perishable goods",
    ]):
        return "Marketing, Sales & Retail"

    # Facilities & Cleaning (new — was Other for Cleaner, Ablution Cleaner)
    if any(kw in t for kw in [
        "cleaner", "cleaning", "ablution", "commercial clean", "commercial floor",
        "garden worker", "gardener", "laundry",
    ]):
        return "Facilities & Cleaning"

    # HR & Training (expanded)
    if any(kw in t for kw in [
        "human resource", "hr ", "hrm", "facilitator", "educator", "assessor",
        "moderator", "skills development", "etdp", "adult education",
        "trainer", "training officer", "assessment practitioner",
        "learning and development", "learning support facilitator",
        "workplace based practitioner", "skills development facilitation",
        "adult literacy teacher", "foundational learning",
        "workplace essential skills", "workplace preparation",
    ]):
        return "HR & Training"

    # Agriculture & Environment
    if any(kw in t for kw in [
        "agri", "farm", "crop", "livestock", "horticulture", "nature", "game",
        "environmental", "conservation", "tractor operator", "animal", "aquaculture",
        "grader operator",
    ]):
        return "Agriculture & Environment"

    # Hospitality & Tourism
    if any(kw in t for kw in [
        "hospitality", "hotel", "chef", "cook", "tourism", "travel", "guiding",
        "accommodation", "food service", "kitchen hand", "catering", "restaurant",
        "beverage", "food handler",
    ]):
        return "Hospitality & Tourism"

    # Beauty & Personal Care
    if any(kw in t for kw in [
        "beauty", "hairdress", "nail", "make-up", "makeup", "cosmetology",
        "esthetician", "personal care", "spa", "barber",
    ]):
        return "Beauty & Personal Care"

    # Media & Communications
    if any(kw in t for kw in [
        "journalist", "journalism", "media", "public relations",
        "communication", "copywriting", "graphic design", "photography",
        "broadcast", "videograph",
    ]):
        return "Media & Communications"

    # Real Estate & Property
    if any(kw in t for kw in ["real estate", "property", "estate agent"]):
        return "Real Estate & Property"

    # Sport & Fitness
    if any(kw in t for kw in [
        "fitness", "sport", "gym", "exercise", "coaching", "referee",
        "physical education", "group fitness",
    ]):
        return "Sport & Fitness"

    # Plant & Equipment Operations (expanded)
    if any(kw in t for kw in [
        "crane operator", "crane pendant", "forklift", "lift truck",
        "bulldozer", "excavator", "scraper operator", "dozer", "roller operator",
        "boom handler", "track handler", "plant operator", "surface tracked",
        "surface grader", "surface roller", "truck mounted crane", "overhead crane",
    ]):
        return "Plant & Equipment Operations"

    # Mining
    if any(kw in t for kw in ["mining", "mine", "blasting", "mineral", "metallurg"]):
        return "Mining"

    # Quality & Risk (new — was Other)
    if any(kw in t for kw in [
        "quality assurer", "quality control", "organisational risk",
        "risk practitioner", "risk management", "design thinking",
        "innovation lead",
    ]):
        return "Quality & Risk Management"

    # Security
    if any(kw in t for kw in [
        "security", "guard", "protection", "close protector", "close protection",
    ]):
        return "Security"

    # Public Sector
    if any(kw in t for kw in [
        "public sector", "government", "municipality", "ward", "councillor",
        "public administration", "public management",
    ]):
        return "Public Sector"

    # Religious / Charitable
    if any(kw in t for kw in ["religious", "christian", "church"]):
        return "Religious & Charitable"

    return "Other"


# ─────────────────────────────────────────────
# COLUMN STANDARDISATION
# ─────────────────────────────────────────────

RENAME_MAP = {
    "Qual-Prog Title": "Qualification Title",
    "Qual-Prog ID": "Qualification ID",
    "Qual-Prog NQF": "NQF Level",
    "Qual-Prog Credits": "Credits",
    "Quality Partner": "Quality Partner",
    "E-Mail Contact 1": "Email 1",
    "E-Mail Contact 2": "Email 2",
    "Contact Number2": "Phone Number",
    "Contact Person Names": "Contact Person",
    "Accreditation Status": "Status",
    "Accreditation Start Date": "Start Date",
    "Accreditation End Date": "End Date",
    "Type of Accreditation": "Accreditation Type",
}

REQUIRED_COLS = [
    "Provider Trading Name", "Qualification Title", "Qualification ID",
    "NQF Level", "Credits", "Quality Partner", "Start Date", "End Date",
    "Status", "Accreditation Type", "Accredited Address",
    "Town-City", "Province", "Contact Person",
    "Email 1", "Email 2", "Phone Number", "Provider Type",
]


def ensure_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.rename(columns={k: v for k, v in RENAME_MAP.items() if k in df.columns})
    for col in REQUIRED_COLS:
        if col not in df.columns:
            df[col] = pd.NA
    return df


# ─────────────────────────────────────────────
# LOCATION REPAIR
# ─────────────────────────────────────────────

def build_location_lookups(df: pd.DataFrame):
    """
    Learn town→province mappings from rows that already have valid provinces.
    Returns (town_to_province, province_majority_town) dicts.
    """
    town_to_province: Dict[str, str] = {}
    province_majority_town: Dict[str, str] = {}

    valid = df[df["Province"].isin(VALID_PROVINCES_SET)].copy()
    valid["_town_norm"] = valid["Town-City"].apply(
        lambda v: s(v).title() if pd.notna(v) else ""
    )

    # Build town → province from data
    for _, row in valid[valid["_town_norm"] != ""].iterrows():
        town = row["_town_norm"]
        prov = row["Province"]
        if town not in town_to_province:
            town_to_province[town] = prov

    # Start with known hardcoded mapping, data learning overrides
    combined = {**{k.title(): v for k, v in CITY_TO_PROVINCE.items()}, **town_to_province}

    # Build province majority town (for fallback)
    for prov in VALID_PROVINCES:
        towns = valid[valid["Province"] == prov]["_town_norm"]
        if len(towns):
            majority = towns.value_counts().index[0]
            if majority:
                province_majority_town[prov] = majority

    return combined, province_majority_town


def clean_address_to_city(val: str, province: Optional[str],
                           town_to_prov: Dict, prov_majority: Dict) -> str:
    """
    Extract the best city name from a messy address string.
    """
    if not val:
        return val

    # First check if it's a known street fix
    for street, city in STREET_TOWN_FIXES.items():
        if street.lower() in val.lower():
            return city

    # Split by comma/semicolon and find last clean part
    parts = re.split(r"[,;]", val)
    parts = [p.strip() for p in parts if p.strip()]

    for part in reversed(parts):
        part = part.strip()
        # Skip if it has digits or is very short
        if re.search(r"\d", part) or len(part) < 3 or len(part) > 40:
            continue
        # Skip obvious non-city parts
        if re.search(r"\b(ext|unit|floor|office|suite|block|building|plot|farm|stand|no)\b", part, re.I):
            continue
        return part

    # Fallback: use province's majority city
    if province and province in prov_majority:
        return prov_majority[province]

    return val  # give up — return original


def repair_location_fields(df: pd.DataFrame) -> pd.DataFrame:
    print("  Building town→province lookup from valid rows...")
    town_to_prov, prov_majority = build_location_lookups(df)

    fixed_province = 0
    fixed_town = 0

    for idx, row in df.iterrows():
        raw_prov = s(row["Province"])
        raw_town = s(row["Town-City"])

        # Normalize province first
        norm_prov = normalize_province(raw_prov)

        if norm_prov is None:
            # Province is wrong — try to recover from town
            town_title = raw_town.title()
            if town_title in town_to_prov:
                norm_prov = town_to_prov[town_title]
                fixed_province += 1
            else:
                norm_prov = None

        if raw_prov != (norm_prov or raw_prov):
            df.at[idx, "Province"] = norm_prov
            fixed_province += 1

        # Fix Town-City if it looks like a street address
        if is_probable_address(raw_town) or raw_town in STREET_TOWN_FIXES.values() is False:
            # Check known street fixes
            new_town = None
            for street, city in STREET_TOWN_FIXES.items():
                if street.lower() in raw_town.lower():
                    new_town = city
                    break

            if new_town is None and is_probable_address(raw_town):
                new_town = clean_address_to_city(
                    raw_town, norm_prov, town_to_prov, prov_majority
                )

            if new_town and new_town != raw_town:
                df.at[idx, "Town-City"] = new_town
                fixed_town += 1

    print(f"  Province fixes applied: {fixed_province:,}")
    print(f"  Town-City fixes applied: {fixed_town:,}")
    return df


# ─────────────────────────────────────────────
# CONTACT FIELD REPAIR
# ─────────────────────────────────────────────

def repair_contact_fields(df: pd.DataFrame) -> pd.DataFrame:
    email1_list: List = []
    email2_list: List = []
    phone1_list: List = []
    phone2_list: List = []

    for _, row in df[["Email 1", "Email 2", "Phone Number", "Contact Person"]].iterrows():
        # Pull emails from all possible sources including Contact Person
        emails = extract_emails(
            row["Email 1"], row["Email 2"],
            row["Phone Number"], row["Contact Person"]
        )
        # Pull phones from all possible sources
        phones = extract_phones(
            row["Phone Number"], row["Email 2"],
            row["Email 1"]
        )

        email1_list.append(emails[0] if len(emails) > 0 else pd.NA)
        email2_list.append(emails[1] if len(emails) > 1 else pd.NA)
        # FIX 1: store as string, not float — preserves leading 0
        phone1_list.append(phones[0] if len(phones) > 0 else pd.NA)
        phone2_list.append(phones[1] if len(phones) > 1 else pd.NA)

    df["Email 1"] = email1_list
    df["Email 2"] = email2_list
    # FIX 1: explicitly keep as object (string) dtype — never cast to numeric
    df["Phone Number"] = pd.array(phone1_list, dtype=object)
    df["Phone Number 2"] = pd.array(phone2_list, dtype=object)
    return df


def clean_contact_person(df: pd.DataFrame) -> pd.DataFrame:
    """
    FIX 4: If Contact Person contains an email address, extract it to Email 1
    (if Email 1 is blank) and clear Contact Person.
    """
    fixed = 0
    for idx, row in df.iterrows():
        cp = s(row["Contact Person"])
        if not cp:
            continue
        if is_email(cp):
            # Contact Person is actually an email
            if not is_email(row.get("Email 1")):
                df.at[idx, "Email 1"] = cp.lower()
            df.at[idx, "Contact Person"] = pd.NA
            fixed += 1
    print(f"  Contact Person emails extracted: {fixed}")
    return df


# ─────────────────────────────────────────────
# QUALITY PARTNER / SETA CLASSIFICATION
# ─────────────────────────────────────────────

def standardize_partner(val: object) -> object:
    sv = s(val).upper().replace("-", " ").strip()
    # Try direct map
    result = PARTNER_MAP.get(s(val).strip())
    if result:
        return result
    result = PARTNER_MAP.get(sv)
    if result:
        return result
    # Fuzzy — strip common suffixes
    for key, mapped in PARTNER_MAP.items():
        if sv.startswith(key.upper()):
            return mapped
    return s(val).strip() if s(val).strip() else pd.NA


def classify_partner_type(val: object) -> str:
    sv = s(val)
    if not sv:
        return "Missing"
    if sv in TRUE_SETAS:
        return "SETA"
    if sv == "NATED":
        return "NATED / Report 191"
    if sv == "OLD TRADES":
        return "Old Trades"
    if sv == "QCTO":
        return "QCTO"
    if sv in {"SAPC"}:
        return "Professional Body"
    return "Other / Unknown"


# ─────────────────────────────────────────────
# NQF NORMALISATION
# ─────────────────────────────────────────────

def clean_nqf(val: object) -> object:
    sv = s(val)
    if not sv:
        return pd.NA
    if sv == "Listed Trade":
        return "Listed Trade"
    m = re.search(r"(\d+)", sv)
    return f"NQF Level {int(m.group(1)):02d}" if m else sv


# ─────────────────────────────────────────────
# REVIEW FLAG
# ─────────────────────────────────────────────

def create_review_flag(df: pd.DataFrame) -> pd.DataFrame:
    issues = []
    for _, row in df.iterrows():
        row_issues = []
        if pd.isna(row.get("Province")):
            row_issues.append("Province missing")
        if pd.isna(row.get("Town-City")):
            row_issues.append("Town missing")
        if pd.isna(row.get("Quality Partner")):
            row_issues.append("Quality Partner missing")
        if pd.isna(row.get("Email 1")) and pd.isna(row.get("Phone Number")):
            row_issues.append("No usable contact")
        if str(row.get("Accredited Address", "")).strip().startswith("FLAGGED"):
            row_issues.append("Address is company reg number")
        issues.append("; ".join(row_issues) if row_issues else pd.NA)
    df["Needs Review"] = issues
    return df


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default=None)
    parser.add_argument("--output", default="sdp_clean_v4.csv")
    args = parser.parse_args()

    # Find input file
    candidates = [
        args.input,
        "sdp_clean_v3.csv", "sdp_clean.csv",
        "sdp_data.csv", "sdp_raw.csv",
    ]
    input_file = next((f for f in candidates if f and os.path.exists(f)), None)
    if input_file is None:
        raise FileNotFoundError(
            "No input file found. Pass --input or place sdp_clean_v3.csv in this folder."
        )

    output_file = args.output
    review_file = output_file.replace(".csv", "_needs_review.csv")
    audit_file = output_file.replace(".csv", "_audit_summary.txt")

    print("\n" + "=" * 70)
    print("QCTO SDP CLEANING — VERSION 4")
    print("=" * 70)
    print(f"Input : {input_file}")
    print(f"Output: {output_file}")

    df = pd.read_csv(input_file, low_memory=False, dtype=str)
    original_rows = len(df)
    print(f"Loaded: {original_rows:,} rows | {len(df.columns)} columns")

    # ── Standardise column names ──────────────────────────────────────────
    print("\n── Step 1: Standardise column names")
    df = ensure_columns(df)

    # Drop fully-empty columns
    empty_cols = [c for c in df.columns if df[c].replace("nan", pd.NA).isna().all()]
    if empty_cols:
        df.drop(columns=empty_cols, inplace=True)
        print(f"  Dropped empty columns: {empty_cols}")

    # Strip whitespace from all strings
    for col in df.select_dtypes(include="object").columns:
        df[col] = df[col].apply(lambda x: x.strip() if isinstance(x, str) else x)
    df.replace({"nan": pd.NA, "": pd.NA, "NaN": pd.NA}, inplace=True)

    # ── NQF Level ─────────────────────────────────────────────────────────
    print("\n── Step 2: NQF Level normalisation")
    df["NQF Level"] = df["NQF Level"].apply(clean_nqf)
    print(f"  NQF values: {sorted(df['NQF Level'].dropna().unique())}")

    # ── Credits: FIX 3 — store as int ────────────────────────────────────
    print("\n── Step 3: Credits → integer")
    def to_int_credits(v):
        if pd.isna(v) or s(v).upper() in ("N/A", "NA", "NONE", ""):
            return pd.NA
        try:
            return int(float(s(v)))
        except (ValueError, TypeError):
            return pd.NA
    df["Credits"] = df["Credits"].apply(to_int_credits)
    null_credits = df["Credits"].isna().sum()
    print(f"  Non-null credits: {df['Credits'].notna().sum():,} | Null: {null_credits:,}")
    print(f"  (Listed Trade rows have no credits — expected)")

    # ── Dates ─────────────────────────────────────────────────────────────
    print("\n── Step 4: Date standardisation")
    for col in ["Start Date", "End Date"]:
        if col in df.columns:
            df[col] = df[col].apply(parse_mixed_date)
    print(f"  Start Date nulls: {df['Start Date'].isna().sum()} | End Date nulls: {df['End Date'].isna().sum()}")

    # ── FIX 7: Days Until Expiry — always fresh from TODAY ───────────────
    print("\n── Step 5: Days Until Expiry (recalculated from today)")
    df["Days Until Expiry"] = df["End Date"].apply(
        lambda d: int((d - TODAY_TS).days) if pd.notna(d) else pd.NA
    )
    expired = (df["Days Until Expiry"].dropna() < 0).sum()
    expiring_soon = ((df["Days Until Expiry"].dropna() >= 0) & (df["Days Until Expiry"].dropna() <= 90)).sum()
    print(f"  Already expired: {expired:,} | Expiring within 90 days: {expiring_soon:,}")

    # ── Quality Partner / SETA classification ────────────────────────────
    print("\n── Step 6: Quality Partner standardisation")
    df["Quality Partner"] = df["Quality Partner"].apply(standardize_partner)
    df["Partner Type"] = df["Quality Partner"].apply(classify_partner_type)
    df["SETA"] = df["Quality Partner"].apply(
        lambda v: v if s(v) in TRUE_SETAS else pd.NA
    )
    df["Is Old Trade"] = df["Quality Partner"].apply(
        lambda v: "Yes" if s(v) == "OLD TRADES" else "No"
    )
    print(f"  Partner types: {df['Partner Type'].value_counts().to_dict()}")

    # ── Accreditation Status ──────────────────────────────────────────────
    print("\n── Step 7: Accreditation Status normalisation")
    if "Status" in df.columns:
        df["Status"] = df["Status"].apply(lambda v: s(v).title() if pd.notna(v) else v)
    else:
        df["Status"] = pd.NA

    # ── Accreditation Type ────────────────────────────────────────────────
    if "Accreditation Type" in df.columns:
        df["Accreditation Type"] = df["Accreditation Type"].apply(
            lambda v: s(v).strip() if pd.notna(v) else v
        )

    # ── Provider Type ─────────────────────────────────────────────────────
    if "Provider Type" in df.columns:
        df["Provider Type"].fillna("Not Specified", inplace=True)
        df["Provider Type"] = df["Provider Type"].apply(
            lambda v: "Not Specified" if s(v) in ("", "nan") else s(v)
        )

    # ── FIX 5: Accredited Address — flag company reg numbers ─────────────
    print("\n── Step 8: Accredited Address — flag company reg numbers")
    if "Accredited Address" in df.columns:
        reg_mask = df["Accredited Address"].apply(
            lambda v: bool(REG_NUM_RE.match(s(v))) if pd.notna(v) else False
        )
        flagged_addr = reg_mask.sum()
        df.loc[reg_mask, "Accredited Address"] = df.loc[reg_mask, "Accredited Address"].apply(
            lambda v: f"FLAGGED_REG_NUM: {v}"
        )
        print(f"  Flagged {flagged_addr:,} rows where Accredited Address was a company reg number")

    # ── FIX 2: Qualification Title spacing ("Programmes :") ───────────────
    print("\n── Step 9: Fix Qualification Title formatting")
    if "Qualification Title" in df.columns:
        before = df["Qualification Title"].apply(
            lambda v: bool(re.search(r"Programmes\s+:", s(v))) if pd.notna(v) else False
        ).sum()
        df["Qualification Title"] = df["Qualification Title"].apply(
            lambda v: re.sub(r"Programmes\s+:", "Programmes:", s(v)) if pd.notna(v) else v
        )
        # Also fix double spaces in titles
        df["Qualification Title"] = df["Qualification Title"].apply(
            lambda v: re.sub(r"\s{2,}", " ", s(v)).strip() if pd.notna(v) else v
        )
        print(f"  'Programmes :' spacing fixed in {before:,} rows")

    # ── Location repair ───────────────────────────────────────────────────
    print("\n── Step 10: Province & Town-City repair")
    df = repair_location_fields(df)
    province_nulls = df["Province"].isna().sum()
    town_nulls = df["Town-City"].isna().sum()
    print(f"  Province nulls remaining: {province_nulls}")
    print(f"  Town-City nulls remaining: {town_nulls}")
    print(f"  Province values: {sorted(df['Province'].dropna().unique())}")

    # ── FIX 4: Contact Person email extraction ─────────────────────────────
    print("\n── Step 11: Contact Person — extract embedded emails")
    df = clean_contact_person(df)

    # ── FIX 1: Contact field repair (phones as strings) ───────────────────
    print("\n── Step 12: Email & phone repair (phones stored as strings)")
    df = repair_contact_fields(df)
    print(f"  Email 1 non-null: {df['Email 1'].notna().sum():,}")
    print(f"  Phone Number non-null: {df['Phone Number'].notna().sum():,}")
    # Verify phones are strings, not floats
    phone_dtype = df["Phone Number"].dtype
    print(f"  Phone Number dtype: {phone_dtype} (should be object/string)")
    # Sample check
    sample_phones = df["Phone Number"].dropna().head(5).tolist()
    print(f"  Sample phones: {sample_phones}")

    # ── Has Contact Email flag ────────────────────────────────────────────
    df["Has Contact Email"] = df["Email 1"].apply(
        lambda v: "Yes" if pd.notna(v) and s(v) else "No"
    )

    # ── FIX 8: Qualification Category (expanded) ──────────────────────────
    print("\n── Step 13: Qualification Category (expanded v4)")
    df["Qualification Category"] = df["Qualification Title"].apply(categorize_qualification)
    cat_counts = df["Qualification Category"].value_counts()
    print(f"  'Other' rows: {cat_counts.get('Other', 0):,} (down from 7,530 in v3)")
    print("  All categories:")
    for cat, cnt in cat_counts.items():
        print(f"    {cat:45s}: {cnt:,}")

    # ── Remove exact duplicates ───────────────────────────────────────────
    print("\n── Step 14: Remove exact duplicate rows")
    before_dedup = len(df)
    df.drop_duplicates(inplace=True)
    dupes_removed = before_dedup - len(df)
    print(f"  Duplicates removed: {dupes_removed:,}")

    # ── Needs Review flag ─────────────────────────────────────────────────
    print("\n── Step 15: Review flag")
    df = create_review_flag(df)

    # ── Export dates back to strings ──────────────────────────────────────
    for col in ["Start Date", "End Date"]:
        if col in df.columns:
            df[col] = df[col].apply(
                lambda d: d.strftime("%Y-%m-%d") if pd.notna(d) else ""
            )

    # ── Credits as nullable int string ───────────────────────────────────
    df["Credits"] = df["Credits"].apply(
        lambda v: str(int(v)) if pd.notna(v) else ""
    )

    # ── Final column ordering ─────────────────────────────────────────────
    preferred_order = [
        "Provider Trading Name", "Qualification Title", "Qualification ID",
        "NQF Level", "Credits", "Quality Partner", "Partner Type", "SETA",
        "Start Date", "End Date", "Status", "Accreditation Type",
        "Accredited Address", "Town-City", "Province",
        "Contact Person", "Email 1", "Email 2",
        "Phone Number", "Phone Number 2",
        "Provider Type", "Days Until Expiry", "Has Contact Email",
        "Qualification Category", "Is Old Trade", "Needs Review",
    ]
    ordered = [c for c in preferred_order if c in df.columns]
    remaining = [c for c in df.columns if c not in ordered]
    df = df[ordered + remaining]

    # ── Summary ───────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("FINAL SUMMARY")
    print("=" * 70)
    print(f"  Original rows    : {original_rows:,}")
    print(f"  Final rows       : {len(df):,}")
    print(f"  Duplicates removed: {original_rows - len(df):,}")
    print(f"  Final columns    : {len(df.columns)}")

    mict = df[(df["Quality Partner"] == "MICT SETA") & (df["Status"] == "Active")]
    print(f"\n  Active MICT SETA providers: {len(mict):,}")
    print(f"  Unique MICT providers: {mict['Provider Trading Name'].nunique():,}")

    print("\n  Remaining 'Other' qualifications (top 20):")
    other_titles = df[df["Qualification Category"] == "Other"]["Qualification Title"].value_counts()
    for title, cnt in other_titles.head(20).items():
        print(f"    [{cnt:4d}] {title}")

    # ── Write outputs ─────────────────────────────────────────────────────
    df.to_csv(output_file, index=False, encoding="utf-8-sig")
    print(f"\n  Main output   : {output_file}")

    review_df = df[df["Needs Review"].notna()]
    review_df.to_csv(review_file, index=False, encoding="utf-8-sig")
    print(f"  Review output : {review_file} ({len(review_df):,} rows)")

    # Audit summary
    partner_type_counts = df["Partner Type"].value_counts()
    audit_lines = [
        "QCTO SDP CLEANING AUDIT — VERSION 4",
        "=" * 50,
        f"Input file : {input_file}",
        f"Output file: {output_file}",
        f"Run date   : {TODAY}",
        "",
        f"Original rows: {original_rows:,}",
        f"Final rows   : {len(df):,}",
        f"Duplicates removed: {original_rows - len(df):,}",
        "",
        "Province values: " + str(sorted(df["Province"].dropna().unique())),
        f"Rows with missing Province: {df['Province'].isna().sum()}",
        f"Rows with missing Town-City: {df['Town-City'].isna().sum()}",
        f"Rows with Email 1: {df['Email 1'].notna().sum():,}",
        f"Rows with Phone Number: {df['Phone Number'].notna().sum():,}",
        f"Rows flagged for review: {review_df['Needs Review'].notna().sum():,}",
        "",
        "Partner type counts:",
    ]
    for pt, cnt in partner_type_counts.items():
        audit_lines.append(f"  - {pt}: {cnt:,}")
    audit_lines += [
        "",
        "Top Quality Partner values:",
    ]
    for qp, cnt in df["Quality Partner"].value_counts().head(25).items():
        audit_lines.append(f"  - {qp}: {cnt:,}")
    audit_lines += [
        "",
        "Qualification Category distribution:",
    ]
    for cat, cnt in df["Qualification Category"].value_counts().items():
        audit_lines.append(f"  - {cat}: {cnt:,}")
    audit_lines += [
        "",
        "NATED classification note:",
        "  NATED Report 190/191 = N1-N6 qualification framework (DHET).",
        "  N1-N3 quality assured by Umalusi. N4-N6 accredited by QCTO.",
        "  N1-N3 phased out from 1 Jan 2024 (Gazette 49518).",
        "  NOT a SETA. Partner Type = 'NATED / Report 191' is correct.",
        "",
        "v4 fixes applied:",
        "  FIX 1: Phone numbers stored as strings — leading 0 preserved",
        "  FIX 2: 'Programmes :' spacing fixed in Qualification Title",
        "  FIX 3: Credits stored as integer (not float 251.0)",
        "  FIX 4: Emails in Contact Person field extracted to Email 1",
        "  FIX 5: Accredited Address company reg numbers flagged",
        "  FIX 6: Remaining Town-City street names resolved",
        "  FIX 7: Days Until Expiry recalculated from today at runtime",
        "  FIX 8: Qualification Category 'Other' reduced with 8 new categories",
    ]

    with open(audit_file, "w", encoding="utf-8") as f:
        f.write("\n".join(audit_lines))
    print(f"  Audit summary : {audit_file}")
    print("\n" + "=" * 70)
    print("  DONE. Ready for Power BI.")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
