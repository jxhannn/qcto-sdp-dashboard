
"""
QCTO SDP Data Cleaning Script — Version 3
=========================================
Purpose:
- Clean the full 49,000+ row QCTO/SDP dataset more robustly than v2
- Works on either the raw export or a partially cleaned file
- Repairs contact fields across Email 1 / Email 2 / Phone Number
- Forces Province to the 9 valid South African provinces (or blank if unresolved)
- Cleans Town-City using learned town→province mappings from valid rows
- Separates true SETAs from non-SETA partners such as NATED, OLD TRADES, SAPC, QCTO
- Drops exact duplicate rows
- Exports:
    1) cleaned CSV
    2) rows that still need manual review
    3) audit summary text file

Usage:
    python clean_sdp_data_v3.py
    python clean_sdp_data_v3.py --input sdp_data.csv --output sdp_clean_v3.csv
"""

from __future__ import annotations

import argparse
import os
import re
import unicodedata
from collections import Counter
from datetime import date
from typing import Iterable, Optional, List, Dict

import numpy as np
import pandas as pd

TODAY = pd.Timestamp(date.today())

VALID_PROVINCES = [
    "Eastern Cape",
    "Free State",
    "Gauteng",
    "KwaZulu-Natal",
    "Limpopo",
    "Mpumalanga",
    "North West",
    "Northern Cape",
    "Western Cape",
]
VALID_PROVINCES_SET = set(VALID_PROVINCES)

PROVINCE_NORMALIZATION = {
    "eastern cape": "Eastern Cape",
    "free state": "Free State",
    "gauteng": "Gauteng",
    "kwazulu natal": "KwaZulu-Natal",
    "kwazulunatal": "KwaZulu-Natal",
    "kzn": "KwaZulu-Natal",
    "limpopo": "Limpopo",
    "mpumalanga": "Mpumalanga",
    "north west": "North West",
    "north-west": "North West",
    "northern cape": "Northern Cape",
    "western cape": "Western Cape",
}

TRUE_SETAS = {
    "AGRISETA",
    "BANKSETA",
    "CATHSSETA",
    "CETA",
    "CHIETA",
    "ETDP SETA",
    "EWSETA",
    "FASSET",
    "FOODBEV SETA",
    "FP&M SETA",
    "HWSETA",
    "INSETA",
    "LGSETA",
    "MERSETA",
    "MICT SETA",
    "MQA",
    "PSETA",
    "SASSETA",
    "SERVICES SETA",
    "TETA",
    "W&R SETA",
}

PARTNER_MAP = {
    "AGRISETA": "AGRISETA",
    "BANKSETA": "BANKSETA",
    "CATHSSETA": "CATHSSETA",
    "CETA": "CETA",
    "CHIETA": "CHIETA",
    "ETDPSETA": "ETDP SETA",
    "ETDP": "ETDP SETA",
    "ETDP SETA": "ETDP SETA",
    "EWSETA": "EWSETA",
    "FASSET": "FASSET",
    "FOODBEV": "FOODBEV SETA",
    "FOODBEV SETA": "FOODBEV SETA",
    "FP&MSETA": "FP&M SETA",
    "FPMSETA": "FP&M SETA",
    "FP&M SETA": "FP&M SETA",
    "HWSETA": "HWSETA",
    "INSETA": "INSETA",
    "LGSETA": "LGSETA",
    "MERSETA": "MERSETA",
    "MICSETA": "MICT SETA",
    "MICTSETA": "MICT SETA",
    "MICT": "MICT SETA",
    "MICT SETA": "MICT SETA",
    "MQA": "MQA",
    "PSETA": "PSETA",
    "QCTO": "QCTO",
    "SAPC": "SAPC",
    "SASSETA": "SASSETA",
    "SERVICES SE": "SERVICES SETA",
    "SERVICES SETA": "SERVICES SETA",
    "TETA": "TETA",
    "W&RSETA": "W&R SETA",
    "W&R SETA": "W&R SETA",
    "OLD TRADES": "OLD TRADES",
    "Old Trades": "OLD TRADES",
    "NATED": "NATED",
    "Nated": "NATED",
}

# This map is only used for rows where Province is wrong and is actually a town/suburb/village.
MANUAL_PROVINCE_FROM_PLACE = {
    "aliwal": "Eastern Cape",
    "aliwal north": "Eastern Cape",
    "athlone": "Western Cape",
    "burgerfort": "Limpopo",
    "burgersfort": "Limpopo",
    "elsenburg": "Western Cape",
    "false bay": "Western Cape",
    "ga molepo": "Limpopo",
    "ga sekororo": "Limpopo",
    "ga-sekororo": "Limpopo",
    "groblesdal": "Limpopo",
    "hartbeespoort.": "North West",
    "lady frere": "Eastern Cape",
    "lawley": "Gauteng",
    "leandre": "Mpumalanga",
    "lephalale": "Limpopo",
    "mathulini": "KwaZulu-Natal",
    "mbobela": "Mpumalanga",
    "mkhuze": "KwaZulu-Natal",
    "modderfointein": "Gauteng",
    "modderkruil": "Mpumalanga",
    "modimolle mookgophon": "Limpopo",
    "modimolle-mookgophon": "Limpopo",
    "modjadjieskloof": "Limpopo",
    "moletji polokwane": "Limpopo",
    "mokodumela": "Limpopo",
    "mashamba village": "Limpopo",
    "mzinti": "Mpumalanga",
    "nelspruit": "Mpumalanga",
    "nelspurit": "Mpumalanga",
    "paul roux": "Free State",
    "phetwane village": "Limpopo",
    "piet reitief": "Mpumalanga",
    "pinetown durban": "KwaZulu-Natal",
    "polokwnane": "Limpopo",
    "port shepstone": "KwaZulu-Natal",
    "port sherpstone": "KwaZulu-Natal",
    "qwa qwa": "Free State",
    "qwa-qwa": "Free State",
    "rensburg": "Free State",
    "ridge park complex": "KwaZulu-Natal",
    "ridge park complex merrivale": "KwaZulu-Natal",
    "rietkuil": "Mpumalanga",
    "rustenburg cbd": "North West",
    "silvertondale": "Gauteng",
    "tshandama village": "Limpopo",
    "tshilivho": "Limpopo",
    "underberg": "KwaZulu-Natal",
    "underbolt boksburg": "Gauteng",
    "vanderbijl park": "Gauteng",
    "vhembe": "Limpopo",
    "villiera": "Gauteng",
    "winterton": "KwaZulu-Natal",
    "zastron": "Free State",
}

TOWN_ALIAS = {
    "burgerfort": "Burgersfort",
    "emalahleni": "Emalahleni",
    "emalehleni": "Emalahleni",
    "groblesdal": "Groblersdal",
    "groblersdal": "Groblersdal",
    "groblersdssl": "Groblersdal",
    "khathu": "Kathu",
    "kimberly": "Kimberley",
    "krurgersdorp": "Krugersdorp",
    "kwa mashu": "KwaMashu",
    "louis trichaardt": "Louis Trichardt",
    "mbobela": "Mbombela",
    "modderfointein": "Modderfontein",
    "nelspurit": "Mbombela",
    "nelspruit": "Mbombela",
    "piet reitief": "Piet Retief",
    "polokwnane": "Polokwane",
    "port elizabeth": "Gqeberha",
    "port sherpstone": "Port Shepstone",
    "queenstown": "Komani",
    "qwa qwa": "QwaQwa",
    "qwa-qwa": "QwaQwa",
    "underbolt boksburg": "Boksburg",
    "e malahleni": "Emalahleni",
}

ADDRESS_WORDS = {
    "street",
    "st",
    "road",
    "rd",
    "avenue",
    "ave",
    "drive",
    "dr",
    "boulevard",
    "blvd",
    "lane",
    "ln",
    "way",
    "close",
    "crescent",
    "park",
    "industrial",
    "building",
    "bldg",
    "complex",
    "office",
    "block",
    "unit",
    "floor",
    "corner",
    "cnr",
    "ext",
    "extension",
    "stand",
    "shop",
    "suite",
    "campus",
    "highway",
    "site",
    "section",
    "zone",
    "plot",
    "centre",
    "center",
}

RELAX_EMAIL_RE = re.compile(r"([A-Z0-9._%+\-\'`]+@+[A-Z0-9.\-]+\.[A-Z]{2,})", re.I)
STRICT_EMAIL_RE = re.compile(r"^[A-Z0-9._%+\-\'`]+@[A-Z0-9.\-]+\.[A-Z]{2,}$", re.I)


def find_input_file(cli_input: Optional[str]) -> str:
    if cli_input and os.path.exists(cli_input):
        return cli_input
    candidates = [
        "sdp_data.csv",
        "sdp_clean.csv",
        "sdp_clean_v2.csv",
        "QCTO_SDP.csv",
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    raise FileNotFoundError(
        "No input CSV found. Place your file in this folder and use --input filename.csv"
    )


def normalize_basic_text(value: object) -> object:
    if pd.isna(value):
        return pd.NA
    s = unicodedata.normalize("NFKC", str(value))
    s = s.replace("\xa0", " ").replace("\u200b", "")
    s = re.sub(r"\s+", " ", s).strip()
    return pd.NA if s == "" else s


def norm_place(value: object) -> Optional[str]:
    if pd.isna(value):
        return None
    s = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode("ascii")
    s = s.lower()
    s = s.replace("&", " and ")
    s = re.sub(r"[,;/]+", " ", s)
    s = re.sub(r"[\.\-]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def clean_place_label(value: object) -> object:
    if pd.isna(value):
        return pd.NA
    s = normalize_basic_text(value)
    if pd.isna(s):
        return pd.NA
    n = norm_place(s)
    if n in TOWN_ALIAS:
        return TOWN_ALIAS[n]

    if str(s).isupper() and len(str(s)) <= 5:
        return s

    parts = []
    for token in re.split(r"(\s+|-)", str(s)):
        if token == "-" or token.isspace():
            parts.append(token)
        else:
            parts.append(token.capitalize())
    s2 = "".join(parts)

    manual = {
        "Kwazulu-Natal": "KwaZulu-Natal",
        "Qwaqwa": "QwaQwa",
        "Kwamhlanga": "KwaMhlanga",
        "Emalahleni": "Emalahleni",
        "Mbobela": "Mbombela",
    }
    return manual.get(s2, s2)


def normalize_province(value: object) -> object:
    if pd.isna(value):
        return pd.NA
    n = norm_place(value)
    if n in PROVINCE_NORMALIZATION:
        return PROVINCE_NORMALIZATION[n]
    label = clean_place_label(value)
    return label if label in VALID_PROVINCES_SET else pd.NA


def is_probable_address(value: object) -> bool:
    if pd.isna(value):
        return False
    s = str(value).strip()
    sl = s.lower()
    if re.match(r"^(no\.?\s*)?\d", sl):
        return True
    if ";" in s or "\n" in s:
        return True
    if len(s) > 40:
        return True
    if len(re.findall(r"\d", s)) >= 3 and len(s.split()) >= 2:
        return True
    if any(word in sl for word in ADDRESS_WORDS) and ("," in sl or len(sl) > 25):
        return True
    return False


def pick_majority(series: pd.Series) -> object:
    counts = series.dropna().astype(str).value_counts()
    return counts.index[0] if len(counts) else pd.NA


def standardize_partner(value: object) -> object:
    if pd.isna(value):
        return pd.NA
    s = str(normalize_basic_text(value))
    return PARTNER_MAP.get(s, PARTNER_MAP.get(s.upper(), s.upper()))


def classify_partner_type(value: object) -> object:
    if pd.isna(value):
        return pd.NA
    s = str(value)
    if s in TRUE_SETAS:
        return "SETA"
    if s == "NATED":
        return "NATED / Report 191"
    if s == "OLD TRADES":
        return "Old Trades"
    if s == "QCTO":
        return "QCTO"
    if s == "SAPC":
        return "Professional Body"
    return "Other / Unknown"


def parse_mixed_date(value: object) -> object:
    if pd.isna(value):
        return pd.NA
    s = str(value).strip()
    if not s:
        return pd.NA

    # Already ISO-like
    if re.match(r"^\d{4}-\d{2}-\d{2}$", s):
        ts = pd.to_datetime(s, errors="coerce")
        return pd.NA if pd.isna(ts) else ts.normalize()

    # South African style should be day-first
    ts = pd.to_datetime(s, errors="coerce", dayfirst=True)
    if pd.isna(ts):
        return pd.NA
    return ts.normalize()


def fix_email_token(email: str) -> Optional[str]:
    if not email:
        return None
    e = unicodedata.normalize("NFKD", str(email)).encode("ascii", "ignore").decode("ascii")
    e = e.strip().lower()
    e = e.replace(" ", "")
    e = e.strip('";\'.,;/')
    e = e.replace("@@", "@")
    e = e.replace(".co,za", ".co.za")

    # Collapse repeated domains like gmail.com@gmail.com
    m = re.match(r"^([^@]+@[^@]+\.[a-z]{2,})(?:@[^@]+\.[a-z]{2,})+$", e)
    if m:
        e = m.group(1)

    return e if STRICT_EMAIL_RE.match(e) else None


def extract_emails(*values: object) -> List[str]:
    emails: List[str] = []
    for value in values:
        if pd.isna(value):
            continue
        s = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode("ascii")
        s = s.replace("\n", " ").replace("\r", " ")
        s = re.sub(r"\s*@\s*", "@", s)
        s = re.sub(r"\s*\.\s*", ".", s)
        s = s.replace("|", " ").replace("/", " ").replace(";", " ")
        for token in RELAX_EMAIL_RE.findall(s):
            fixed = fix_email_token(token)
            if fixed and fixed not in emails:
                emails.append(fixed)
    return emails


def normalize_phone(number: object) -> Optional[str]:
    digits = re.sub(r"\D", "", str(number))
    if not digits:
        return None

    if digits.startswith("27") and len(digits) == 11:
        digits = "0" + digits[2:]
    elif digits.startswith("27") and len(digits) == 12 and digits[2] == "0":
        digits = digits[2:]
    elif len(digits) == 9:
        digits = "0" + digits

    if len(digits) != 10:
        return None
    return digits


def extract_phones(*values: object) -> List[str]:
    phones: List[str] = []
    for value in values:
        if pd.isna(value):
            continue
        s = RELAX_EMAIL_RE.sub(" ", str(value))
        s = s.replace("\n", " ").replace("\r", " ")
        for piece in re.split(r"[;/]|(?:\s{2,})", s):
            fixed = normalize_phone(piece)
            if fixed and fixed not in phones:
                phones.append(fixed)
    return phones


def categorize_qualification(title: object) -> str:
    if pd.isna(title):
        return "Uncategorised"
    t = str(title).lower()

    if any(kw in t for kw in [
        "data", "analytics", "analysis", "software", "developer", "development",
        "systems", "network", "cyber", "information technology", "ict", "digital",
        "computer", "programming", "database", "web developer", "technical support",
        "cloud", "support technician", "end user", "it support",
    ]):
        return "ICT & Data"

    if any(kw in t for kw in [
        "business", "management", "administrator", "administration", "manager",
        "operations", "office", "executive", "supervision", "supervisor",
        "entrepreneurship", "enterprise", "public management",
    ]):
        return "Business & Management"

    if any(kw in t for kw in [
        "finance", "financial", "accounting", "accounts", "bookkeep", "bookkeeper",
        "auditor", "audit", "tax", "payroll", "treasury", "credit",
    ]):
        return "Finance & Accounting"

    if any(kw in t for kw in [
        "insurance", "underwriter", "broker", "banking", "bank", "financial service",
        "short-term", "long-term",
    ]):
        return "Insurance & Banking"

    if any(kw in t for kw in [
        "paralegal", "legal", "compliance", "law", "regulatory", "governance",
    ]):
        return "Legal & Compliance"

    if any(kw in t for kw in [
        "health", "nursing", "care", "social", "welfare", "community", "child",
        "counsel", "therapist", "medical", "pharmacy", "disability", "first aid",
        "emergency", "paramedic", "ambulance", "hiv", "aids", "auxiliary",
    ]):
        return "Health & Social Services"

    if any(kw in t for kw in [
        "electrician", "electrical", "engineer", "mechanic", "mechanical",
        "fitter", "millwright", "welder", "boiler", "diesel", "motor",
        "artisan", "rigger", "automotive", "instrumentation", "refrigeration",
        "plumber", "plumbing",
    ]):
        return "Engineering & Trades"

    if any(kw in t for kw in [
        "construction", "bricklayer", "carpenter", "plasterer", "builder",
        "civil", "quantity", "surveyor", "painter", "tiler", "roofer", "glazier",
    ]):
        return "Construction & Building"

    if any(kw in t for kw in [
        "logistics", "supply chain", "transport", "freight", "warehouse",
        "distribution", "procurement", "purchasing", "forklift", "driver",
        "shipping", "customs",
    ]):
        return "Logistics & Supply Chain"

    if any(kw in t for kw in [
        "human resource", "hr ", "hrm", "facilitator", "educator", "assessor",
        "moderator", "skills development", "etdp", "adult education", "trainer",
        "training officer",
    ]):
        return "HR & Training"

    if any(kw in t for kw in [
        "agri", "farm", "crop", "livestock", "horticulture", "nature", "game",
        "environmental", "conservation", "tractor operator", "grader operator",
        "animal", "aquaculture",
    ]):
        return "Agriculture & Environment"

    if any(kw in t for kw in [
        "hospitality", "hotel", "chef", "cook", "tourism", "travel", "guiding",
        "accommodation", "food service", "kitchen", "catering", "restaurant", "beverage",
    ]):
        return "Hospitality & Tourism"

    if any(kw in t for kw in [
        "marketing", "sales", "retail", "customer service", "customer care",
        "call centre", "contact centre", "merchandis", "promotions",
    ]):
        return "Marketing, Sales & Retail"

    if any(kw in t for kw in [
        "beauty", "hairdress", "nail", "make-up", "makeup", "cosmetology",
        "esthetician", "personal care", "spa", "hair",
    ]):
        return "Beauty & Personal Care"

    if any(kw in t for kw in [
        "journalist", "journalism", "media", "public relations", "pr ",
        "communication", "copywriting", "graphic design", "photography",
        "broadcast", "videograph",
    ]):
        return "Media & Communications"

    if any(kw in t for kw in ["real estate", "property", "estate agent"]):
        return "Real Estate & Property"

    if any(kw in t for kw in [
        "fitness", "sport", "gym", "exercise", "coaching", "referee", "physical education",
    ]):
        return "Sport & Fitness"

    if any(kw in t for kw in [
        "crane operator", "crane pendant", "grader operator", "bulldozer", "excavator",
        "scraper operator", "dozer", "roller operator", "boom handler", "track handler",
        "plant operator",
    ]):
        return "Plant & Equipment Operations"

    if any(kw in t for kw in ["mining", "mine", "blasting", "rock", "mineral", "metallurg"]):
        return "Mining"

    if any(kw in t for kw in [
        "public sector", "government", "municipality", "ward", "councillor", "public administration",
    ]):
        return "Public Sector"

    if any(kw in t for kw in ["security", "guard", "protection", "close protection"]):
        return "Security"

    return "Other"


def ensure_columns(df: pd.DataFrame) -> pd.DataFrame:
    alias_map = {
        "Provider Trading Name": "Provider Trading Name",
        "Provider Legal Name": "Provider Legal Name",
        "Qual-Prog Title": "Qualification Title",
        "Qualification Title": "Qualification Title",
        "Qual-Prog ID": "Qualification ID",
        "Qualification ID": "Qualification ID",
        "Qual-Prog NQF": "NQF Level",
        "NQF Level": "NQF Level",
        "Qual-Prog Credits": "Credits",
        "Credits": "Credits",
        "Quality Partner": "Quality Partner Raw",
        "SETA": "Quality Partner Raw",
        "Accreditation Start Date": "Start Date",
        "Start Date": "Start Date",
        "Accreditation End Date": "End Date",
        "End Date": "End Date",
        "Accreditation Status": "Status",
        "Status": "Status",
        "Type of Accreditation": "Accreditation Type",
        "Accreditation Type": "Accreditation Type",
        "Accredited Address": "Accredited Address",
        "Town-City": "Town-City",
        "Province": "Province",
        "Contact Person Names": "Contact Person",
        "Contact Person": "Contact Person",
        "E-Mail Contact 1": "Email 1",
        "Email 1": "Email 1",
        "E-Mail Contact 2": "Email 2",
        "Email 2": "Email 2",
        "Contact Number2": "Phone Number",
        "Phone Number": "Phone Number",
        "Provider Type": "Provider Type",
        "Days Until Expiry": "Days Until Expiry",
        "Has Contact Email": "Has Contact Email",
        "Qualification Category": "Qualification Category",
        "Is Old Trade": "Is Old Trade",
    }

    renamed = {}
    for col in df.columns:
        renamed[col] = alias_map.get(col, col)
    df = df.rename(columns=renamed)

    required = [
        "Provider Trading Name",
        "Qualification Title",
        "Qualification ID",
        "NQF Level",
        "Credits",
        "Quality Partner Raw",
        "Start Date",
        "End Date",
        "Status",
        "Accreditation Type",
        "Accredited Address",
        "Town-City",
        "Province",
        "Contact Person",
        "Email 1",
        "Email 2",
        "Phone Number",
        "Provider Type",
    ]
    for col in required:
        if col not in df.columns:
            df[col] = pd.NA
    return df


def build_location_lookups(df: pd.DataFrame) -> tuple[Dict[str, str], Dict[str, str]]:
    province0 = df["Province"].map(normalize_province)
    town0 = df["Town-City"].map(clean_place_label)

    clean_mask = (
        province0.isin(VALID_PROVINCES_SET)
        & df["Town-City"].notna()
        & ~df["Town-City"].map(is_probable_address)
    )

    temp = pd.DataFrame({
        "town_norm": df.loc[clean_mask, "Town-City"].map(norm_place),
        "town": town0[clean_mask],
        "province": province0[clean_mask],
    }).dropna()

    if temp.empty:
        return {}, {}

    canonical_town = temp.groupby("town_norm")["town"].agg(pick_majority).to_dict()
    town_to_province = temp.groupby("town_norm")["province"].agg(pick_majority).to_dict()
    return canonical_town, town_to_province


def extract_place_candidate(text: object, canonical_town: Dict[str, str]) -> List[str]:
    if pd.isna(text):
        return []
    s = normalize_basic_text(text)
    if pd.isna(s):
        return []

    sn = norm_place(s)
    found: List[str] = []

    # First try matching any known town inside the string (longest match wins).
    for town_norm, town in sorted(canonical_town.items(), key=lambda kv: len(kv[0]), reverse=True):
        if town_norm and re.search(rf"\b{re.escape(town_norm)}\b", sn):
            found.append(town)
            break

    # Then work backwards through split parts.
    parts = [p.strip() for p in re.split(r"[,;\n/]+", str(s)) if p.strip()]
    for part in reversed(parts):
        pn = norm_place(part)
        if pn in TOWN_ALIAS:
            found.append(TOWN_ALIAS[pn])
            break
        if pn in PROVINCE_NORMALIZATION:
            continue
        if re.search(r"\d", part):
            continue
        if any(w in pn.split() for w in ADDRESS_WORDS):
            continue
        found.append(clean_place_label(part))
        break

    out: List[str] = []
    for value in found:
        if value and value not in out:
            out.append(value)
    return out


def repair_location_fields(df: pd.DataFrame) -> pd.DataFrame:
    canonical_town, town_to_province = build_location_lookups(df)

    province_new: List[object] = []
    town_new: List[object] = []

    for _, row in df[["Province", "Town-City", "Accredited Address"]].iterrows():
        province_raw = row["Province"]
        town_raw = row["Town-City"]
        address_raw = row["Accredited Address"]

        province = normalize_province(province_raw)
        town = clean_place_label(town_raw)

        province_norm = norm_place(province_raw)
        town_norm = norm_place(town_raw)

        # Canonicalize town immediately if possible.
        if town_norm in TOWN_ALIAS:
            town = TOWN_ALIAS[town_norm]
            town_norm = norm_place(town)
        elif town_norm in canonical_town:
            town = canonical_town[town_norm]
            town_norm = norm_place(town)

        # Province field is actually a place name.
        if pd.isna(province) and province_norm:
            province = town_to_province.get(province_norm) or MANUAL_PROVINCE_FROM_PLACE.get(province_norm)

        # Province from town.
        if pd.isna(province) and town_norm:
            province = town_to_province.get(town_norm) or MANUAL_PROVINCE_FROM_PLACE.get(town_norm)

        # If Town-City is blank or is clearly an address, use Province-as-town if it is a place.
        if (pd.isna(town_raw) or is_probable_address(town_raw)) and province_norm:
            if town_to_province.get(province_norm) or MANUAL_PROVINCE_FROM_PLACE.get(province_norm):
                town = clean_place_label(province_raw)
                town_norm = norm_place(town)

        # Extract place from Town-City and Accredited Address if still needed.
        if pd.isna(town) or is_probable_address(town):
            candidates = extract_place_candidate(town_raw, canonical_town)
            if not candidates:
                candidates = extract_place_candidate(address_raw, canonical_town)
            if candidates:
                town = candidates[0]
                town_norm = norm_place(town)

        # Final province fallback from newly found town.
        if pd.isna(province) and town_norm:
            province = town_to_province.get(town_norm) or MANUAL_PROVINCE_FROM_PLACE.get(town_norm)

        # Final canonicalization.
        if town_norm in TOWN_ALIAS:
            town = TOWN_ALIAS[town_norm]
        elif town_norm in canonical_town:
            town = canonical_town[town_norm]
        elif pd.notna(town):
            town = clean_place_label(town)

        province = province if province in VALID_PROVINCES_SET else pd.NA

        # Do not keep obvious address strings in Town-City.
        if pd.notna(town) and is_probable_address(town) and norm_place(town) not in canonical_town:
            town = pd.NA

        province_new.append(province)
        town_new.append(town)

    df["Province"] = province_new
    df["Town-City"] = town_new
    return df


def repair_contact_fields(df: pd.DataFrame) -> pd.DataFrame:
    email1_list: List[object] = []
    email2_list: List[object] = []
    phone1_list: List[object] = []
    phone2_list: List[object] = []

    for _, row in df[["Email 1", "Email 2", "Phone Number"]].iterrows():
        emails = extract_emails(row["Email 1"], row["Email 2"], row["Phone Number"])
        phones = extract_phones(row["Phone Number"], row["Email 2"], row["Email 1"])

        email1_list.append(emails[0] if len(emails) > 0 else pd.NA)
        email2_list.append(emails[1] if len(emails) > 1 else pd.NA)
        phone1_list.append(phones[0] if len(phones) > 0 else pd.NA)
        phone2_list.append(phones[1] if len(phones) > 1 else pd.NA)

    df["Email 1"] = email1_list
    df["Email 2"] = email2_list
    df["Phone Number"] = phone1_list
    df["Phone Number 2"] = phone2_list
    return df


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
        elif row.get("Partner Type") == "Other / Unknown":
            row_issues.append("Partner type unknown")
        if pd.isna(row.get("Email 1")) and pd.isna(row.get("Phone Number")):
            row_issues.append("No usable contact")
        issues.append("; ".join(row_issues) if row_issues else pd.NA)

    df["Needs Review"] = issues
    return df


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", help="Input CSV path", default=None)
    parser.add_argument("--output", help="Output cleaned CSV path", default="sdp_clean_v3.csv")
    args = parser.parse_args()

    input_file = find_input_file(args.input)
    output_file = args.output

    print("\n" + "=" * 70)
    print("QCTO SDP CLEANING — VERSION 3")
    print("=" * 70)
    print(f"Input file:  {input_file}")
    print(f"Output file: {output_file}")

    df = pd.read_csv(input_file, dtype=str, keep_default_na=False, low_memory=False)
    original_rows = len(df)
    original_cols = len(df.columns)
    print(f"Loaded rows: {original_rows:,} | columns: {original_cols}")

    # Normalize blanks/whitespace everywhere.
    for col in df.columns:
        df[col] = df[col].map(normalize_basic_text)

    # Drop empty columns and known unnecessary columns if present.
    empty_cols = [col for col in df.columns if df[col].isna().all()]
    if empty_cols:
        df = df.drop(columns=empty_cols)

    columns_to_drop = [
        "Provider Legal Name",
        "Accreditation Number",
        "Accreditation-Unique-ID",
        "Organisation-Unique-ID",
        "Accredited Period (Years)",
        "Postal Code",
        "Contact Person Title",
    ]
    df = df.drop(columns=[c for c in columns_to_drop if c in df.columns], errors="ignore")

    # Standardize column names so raw and already-cleaned files both work.
    df = ensure_columns(df)

    # Dates
    for col in ["Start Date", "End Date"]:
        if col in df.columns:
            df[col] = df[col].map(parse_mixed_date)

    # NQF
    if "NQF Level" in df.columns:
        def clean_nqf(value: object) -> object:
            if pd.isna(value):
                return pd.NA
            s = str(value).strip()
            if s.lower() == "listed trade":
                return "Listed Trade"
            m = re.search(r"(\d+)", s)
            return f"NQF Level {int(m.group(1)):02d}" if m else s
        df["NQF Level"] = df["NQF Level"].map(clean_nqf)

    # Credits
    if "Credits" in df.columns:
        df["Credits"] = df["Credits"].map(
            lambda x: pd.NA if pd.notna(x) and str(x).strip().upper() in {"N/A", "NA"} else x
        )

    # Status
    if "Status" in df.columns:
        df["Status"] = df["Status"].map(lambda x: pd.NA if pd.isna(x) else str(x).strip().title())

    # Quality partner / SETA
    df["Quality Partner"] = df["Quality Partner Raw"].map(standardize_partner)
    df["Partner Type"] = df["Quality Partner"].map(classify_partner_type)
    df["SETA"] = df["Quality Partner"].where(df["Partner Type"].eq("SETA"))

    # Location
    df = repair_location_fields(df)

    # Contact fields
    df = repair_contact_fields(df)

    # Provider Type
    if "Provider Type" in df.columns:
        df["Provider Type"] = df["Provider Type"].fillna("Not Specified")

    # Helper columns
    if "End Date" in df.columns:
        df["Days Until Expiry"] = df["End Date"].map(
            lambda x: int((x - TODAY).days) if pd.notna(x) else pd.NA
        )

    df["Has Contact Email"] = df["Email 1"].notna().map({True: "Yes", False: "No"})
    df["Is Old Trade"] = df["Quality Partner"].eq("OLD TRADES").map({True: "Yes", False: "No"})
    df["Qualification Category"] = df["Qualification Title"].map(categorize_qualification)

    # Review flag
    df = create_review_flag(df)

    # Exact duplicates
    duplicates_before = int(df.duplicated().sum())
    if duplicates_before:
        df = df.drop_duplicates().reset_index(drop=True)

    # Convert dates back to YYYY-MM-DD for CSV export
    for col in ["Start Date", "End Date"]:
        if col in df.columns:
            df[col] = df[col].map(lambda x: x.strftime("%Y-%m-%d") if pd.notna(x) else "")

    final_columns = [
        "Provider Trading Name",
        "Qualification Title",
        "Qualification ID",
        "NQF Level",
        "Credits",
        "Quality Partner",
        "Partner Type",
        "SETA",
        "Start Date",
        "End Date",
        "Status",
        "Accreditation Type",
        "Accredited Address",
        "Town-City",
        "Province",
        "Contact Person",
        "Email 1",
        "Email 2",
        "Phone Number",
        "Phone Number 2",
        "Provider Type",
        "Days Until Expiry",
        "Has Contact Email",
        "Qualification Category",
        "Is Old Trade",
        "Needs Review",
    ]
    existing_final_columns = [c for c in final_columns if c in df.columns]
    df = df[existing_final_columns]

    # Save outputs
    review_file = os.path.splitext(output_file)[0] + "_needs_review.csv"
    summary_file = os.path.splitext(output_file)[0] + "_audit_summary.txt"

    df.to_csv(output_file, index=False, encoding="utf-8-sig")

    review_df = df[df["Needs Review"].notna()].copy()
    review_df.to_csv(review_file, index=False, encoding="utf-8-sig")

    province_values = sorted([p for p in df["Province"].dropna().unique() if p])
    quality_partner_counts = df["Quality Partner"].fillna("Missing").value_counts().to_dict()

    summary_lines = [
        "QCTO SDP CLEANING AUDIT — VERSION 3",
        "=" * 50,
        f"Input file: {input_file}",
        f"Output file: {output_file}",
        "",
        f"Original rows: {original_rows:,}",
        f"Final rows: {len(df):,}",
        f"Exact duplicates removed: {duplicates_before:,}",
        "",
        f"Province values after cleaning: {province_values}",
        f"Rows with missing Province: {int(df['Province'].isna().sum()):,}",
        f"Rows with missing Town-City: {int(df['Town-City'].isna().sum()):,}",
        f"Rows with Email 1: {int(df['Email 1'].notna().sum()):,}",
        f"Rows with Phone Number: {int(df['Phone Number'].notna().sum()):,}",
        f"Rows with review flag: {int(df['Needs Review'].notna().sum()):,}",
        "",
        "Partner type counts:",
    ]
    for k, v in df["Partner Type"].fillna("Missing").value_counts().items():
        summary_lines.append(f"  - {k}: {v:,}")

    summary_lines.append("")
    summary_lines.append("Top Quality Partner values:")
    for k, v in list(quality_partner_counts.items())[:20]:
        summary_lines.append(f"  - {k}: {v:,}")

    with open(summary_file, "w", encoding="utf-8") as f:
        f.write("\n".join(summary_lines))

    print("\nFINAL SUMMARY")
    print(f"Rows after cleaning        : {len(df):,}")
    print(f"Exact duplicates removed   : {duplicates_before:,}")
    print(f"Missing Province rows      : {int(df['Province'].isna().sum()):,}")
    print(f"Missing Town-City rows     : {int(df['Town-City'].isna().sum()):,}")
    print(f"Rows with Email 1          : {int(df['Email 1'].notna().sum()):,}")
    print(f"Rows with Phone Number     : {int(df['Phone Number'].notna().sum()):,}")
    print(f"Rows still needing review  : {int(df['Needs Review'].notna().sum()):,}")
    print(f"\nSaved cleaned file         : {output_file}")
    print(f"Saved review file          : {review_file}")
    print(f"Saved audit summary        : {summary_file}")
    print("\nDone.\n")


if __name__ == "__main__":
    main()
