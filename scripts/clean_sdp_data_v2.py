"""
QCTO SDP Data Cleaning Script — Version 2
==========================================
Fixes all 9 data quality issues found in the 500-row audit.

HOW TO USE:
1. Place your CSV in the same folder as this script
2. Set INPUT_FILE below to your CSV filename
3. Run: python clean_sdp_data_v2.py
4. Output saved to: sdp_clean_v2.csv
"""

import pandas as pd
import numpy as np
import re
from datetime import datetime, date
import os
import warnings
warnings.filterwarnings('ignore')

INPUT_FILE  = "sdp_data.csv"
OUTPUT_FILE = "sdp_clean_v2.csv"
TODAY = date.today()

EMAIL_RE = re.compile(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$')

def is_email(val):
    return bool(EMAIL_RE.match(str(val).strip())) if pd.notna(val) else False

def is_phone(val):
    """True if the value looks like a phone number (digits, spaces, +, -, /)"""
    if pd.isna(val):
        return False
    stripped = re.sub(r'[\s\-/+()]', '', str(val).strip())
    return stripped.isdigit() and len(stripped) >= 7

# ─────────────────────────────────────────────
print("\n" + "="*60)
print("LOADING DATA")
print("="*60)

if not os.path.exists(INPUT_FILE):
    print(f"ERROR: '{INPUT_FILE}' not found. Please rename your file.")
    exit()

df = pd.read_csv(INPUT_FILE, low_memory=False)
original_rows = len(df)
print(f"  Rows: {original_rows:,}  |  Columns: {len(df.columns)}")

# ─────────────────────────────────────────────
# CARRY OVER: steps from v1 that still apply
# ─────────────────────────────────────────────

# Drop the same unnecessary columns as v1
columns_to_drop_v1 = [
    "Provider Legal Name", "Accreditation Number", "Accreditation-Unique-ID",
    "Organisation-Unique-ID", "Accredited Period (Years)", "Postal Code",
    "Contact Person Title",
]
df.drop(columns=[c for c in columns_to_drop_v1 if c in df.columns], inplace=True)

# Strip whitespace from all strings
str_cols = df.select_dtypes(include='object').columns
for col in str_cols:
    df[col] = df[col].apply(lambda x: x.strip() if isinstance(x, str) else x)

# Standardise dates
def parse_mixed_date(val):
    if pd.isna(val) or str(val).strip() == '':
        return None
    val = str(val).strip()
    for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%d/%m/%y', '%m/%d/%y', '%d-%m-%Y'):
        try:
            return datetime.strptime(val, fmt).date()
        except ValueError:
            continue
    return None

for col in ["Accreditation Start Date", "Accreditation End Date",
            "Start Date", "End Date"]:
    if col in df.columns:
        df[col] = df[col].apply(parse_mixed_date)

# Standardise NQF
if 'Qual-Prog NQF' in df.columns:
    def clean_nqf(val):
        if pd.isna(val): return val
        val = str(val).strip()
        if val == 'Listed Trade': return 'Listed Trade'
        m = re.search(r'(\d+)', val)
        return f'NQF Level {int(m.group(1)):02d}' if m else val
    df['Qual-Prog NQF'] = df['Qual-Prog NQF'].apply(clean_nqf)

# Credits N/A → blank
for col in ['Qual-Prog Credits', 'Credits']:
    if col in df.columns:
        df[col] = df[col].apply(
            lambda x: None if str(x).strip().upper() in ['N/A','NA',''] else x)

# Accreditation Status → Title Case
for col in ['Accreditation Status', 'Status']:
    if col in df.columns:
        df[col] = df[col].str.strip().str.title()

# ─────────────────────────────────────────────
# FIX 1: DROP FULLY EMPTY COLUMNS (Column 1, Column 2)
# ─────────────────────────────────────────────
print("\n" + "="*60)
print("FIX 1 — Drop fully empty columns")
print("="*60)

empty_cols = [col for col in df.columns if df[col].isna().all()]
if empty_cols:
    df.drop(columns=empty_cols, inplace=True)
    print(f"  Dropped: {empty_cols}")
else:
    print("  No fully empty columns found.")

# ─────────────────────────────────────────────
# FIX 2: SETA NAME STANDARDISATION (expanded)
# ─────────────────────────────────────────────
print("\n" + "="*60)
print("FIX 2 — Standardise SETA names")
print("="*60)

seta_col = 'Quality Partner' if 'Quality Partner' in df.columns else 'SETA'
if seta_col in df.columns:
    seta_map = {
        # Spacing fixes
        'MICTSETA':     'MICT SETA',
        'MICT':         'MICT SETA',
        'MICT SETA':    'MICT SETA',
        'ETDPSETA':     'ETDP SETA',
        'ETDP SETA':    'ETDP SETA',
        'ETDP':         'ETDP SETA',
        'FP&MSETA':     'FP&M SETA',
        'FP&M SETA':    'FP&M SETA',
        'FPMSETA':      'FP&M SETA',
        'W&RSETA':      'W&R SETA',
        'W&R SETA':     'W&R SETA',
        'SERVICES SE':  'SERVICES SETA',
        'SERVICES SETA':'SERVICES SETA',
        # These SETAs don't need a space suffix but need to be consistent
        'HWSETA':       'HWSETA',
        'MERSETA':      'MERSETA',
        'CATHSSETA':    'CATHSSETA',
        'AGRISETA':     'AGRISETA',
        'BANKSETA':     'BANKSETA',
        'LGSETA':       'LGSETA',
        'SASSETA':      'SASSETA',
        'INSETA':       'INSETA',
        'CHIETA':       'CHIETA',
        'EWSETA':       'EWSETA',
        'FASSET':       'FASSET',
        'TETA':         'TETA',
        'CETA':         'CETA',
        'PSETA':        'PSETA',
        'MQA':          'MQA',
        'QCTO':         'QCTO',
        # Old Trades
        'Old Trades':   'OLD TRADES',
        'OLD TRADES':   'OLD TRADES',
        # NATED — this is a qualification TYPE, not a SETA
        # Flag it rather than remap, so you can manually review
        'NATED':        'NATED (review needed)',
    }
    before = df[seta_col].nunique()
    df[seta_col] = df[seta_col].map(
        lambda x: seta_map.get(str(x).strip(), str(x).strip()) if pd.notna(x) else x
    )
    after = df[seta_col].nunique()
    print(f"  Unique SETAs before: {before}  →  after: {after}")
    print(f"  All values: {sorted(df[seta_col].dropna().unique())}")

# Rename column if still old name
if 'Quality Partner' in df.columns:
    df.rename(columns={'Quality Partner': 'SETA'}, inplace=True)

# ─────────────────────────────────────────────
# FIX 3: PROVINCE — replace city names with correct provinces
# ─────────────────────────────────────────────
print("\n" + "="*60)
print("FIX 3 — Fix Province column (city names → correct province)")
print("="*60)

VALID_PROVINCES = {
    'Gauteng', 'Western Cape', 'Eastern Cape', 'KwaZulu-Natal',
    'Limpopo', 'Mpumalanga', 'North West', 'Northern Cape', 'Free State'
}

# Map of city/suburb names that appeared in the Province column → correct province
# Also covers the Town-City → Province repair for rows where province was a city
city_to_province = {
    # Gauteng suburbs/cities
    'Sandton':          'Gauteng',
    'Johannesburg':     'Gauteng',
    'Midrand':          'Gauteng',
    'Vereeniging':      'Gauteng',
    'Brakpan':          'Gauteng',
    'Parktown':         'Gauteng',
    'Pretoria':         'Gauteng',
    'Centurion':        'Gauteng',
    'Randburg':         'Gauteng',
    'Roodepoort':       'Gauteng',
    'Soweto':           'Gauteng',
    'Germiston':        'Gauteng',
    'Kempton Park':     'Gauteng',
    'Boksburg':         'Gauteng',
    'Benoni':           'Gauteng',
    'Alberton':         'Gauteng',
    'Krugersdorp':      'Gauteng',
    # Western Cape
    'Cape Town':        'Western Cape',
    'Stellenbosch':     'Western Cape',
    'George':           'Western Cape',
    'Paarl':            'Western Cape',
    'Worcester':        'Western Cape',
    'Bellville':        'Western Cape',
    # Eastern Cape
    'East London':      'Eastern Cape',
    'Gqeberha':         'Eastern Cape',
    'Port Elizabeth':   'Eastern Cape',
    'Port Alfred':      'Eastern Cape',
    'Queenstown':       'Eastern Cape',
    'Komani':           'Eastern Cape',
    # KwaZulu-Natal
    'Durban':           'KwaZulu-Natal',
    'Pinetown':         'KwaZulu-Natal',
    'Tongaat':          'KwaZulu-Natal',
    'Chatsworth':       'KwaZulu-Natal',
    'Pietermaritzburg': 'KwaZulu-Natal',
    'Congella':         'KwaZulu-Natal',
    'Bothas Hill':      'KwaZulu-Natal',
    # Limpopo
    'Thohoyandou':      'Limpopo',
    'Polokwane':        'Limpopo',
    'Louis Trichardt':  'Limpopo',
    'Groblersdal':      'Limpopo',
    'Sekhukhune':       'Limpopo',
    'Lwamondo':         'Limpopo',
    'Burgersfort':      'Limpopo',
    # Mpumalanga
    'Emalahleni':       'Mpumalanga',
    'Secunda':          'Mpumalanga',
    # North West
    'Mogwase':          'North West',
    'Siyabuswa':        'North West',
    # Northern Cape
    'Kathu':            'Northern Cape',
    'Kimberley':        'Northern Cape',
    # Free State
    'Bloemfontein':     'Free State',
    'Welkom':           'Free State',
    'Daspoort':         'Free State',
}

if 'Province' in df.columns:
    fixed_province = 0
    for idx, row in df.iterrows():
        prov = str(row['Province']).strip() if pd.notna(row['Province']) else ''
        if prov not in VALID_PROVINCES:
            # The "province" value is actually a city — look up the real province
            correct = city_to_province.get(prov)
            if correct:
                # Move city to Town-City only if Town-City is a street address
                # (i.e., Town-City looks like an address, not a clean city name)
                town = str(row.get('Town-City', '')).strip()
                if re.match(r'^\d|.*[;]', town):
                    # Town-City is a messy address — replace with the correct city
                    df.at[idx, 'Town-City'] = prov
                df.at[idx, 'Province'] = correct
                fixed_province += 1
            else:
                df.at[idx, 'Province'] = 'Unknown'
    print(f"  Fixed {fixed_province} rows where Province was a city name")

    # Standardise capitalisation for valid province names
    prov_fix = {p.lower(): p for p in VALID_PROVINCES}
    prov_fix.update({
        'kwazulu natal': 'KwaZulu-Natal',
        'kwazulunatal': 'KwaZulu-Natal',
        'north-west': 'North West',
    })
    df['Province'] = df['Province'].apply(
        lambda x: prov_fix.get(str(x).strip().lower(), str(x).strip()) if pd.notna(x) else x
    )
    print(f"  Province values after fix: {sorted(df['Province'].dropna().unique())}")

# ─────────────────────────────────────────────
# FIX 4: TOWN-CITY — typos and street addresses
# ─────────────────────────────────────────────
print("\n" + "="*60)
print("FIX 4 — Clean Town-City column")
print("="*60)

if 'Town-City' in df.columns:
    # 4a. Known typos — correct them
    town_typos = {
        'Emalehleni':   'Emalahleni',
        'Emalehleni ':  'Emalahleni',
        'Groblersdssl': 'Groblersdal',
        'Khathu':       'Kathu',
        'khathu':       'Kathu',
        'Port Elizabeth': 'Gqeberha',     # Official name change
    }
    typo_fixed = 0
    for wrong, correct in town_typos.items():
        mask = df['Town-City'].astype(str).str.strip() == wrong
        if mask.sum():
            df.loc[mask, 'Town-City'] = correct
            typo_fixed += mask.sum()
    print(f"  Typos fixed: {typo_fixed} rows")

    # 4b. Extract clean city from street addresses
    # Pattern: if Town-City starts with a digit or contains commas/semicolons,
    # try to pull the last meaningful word/phrase as the city name
    def clean_address_to_city(val, province=None):
        if pd.isna(val):
            return val
        val = str(val).strip()

        # Already a clean city name (no digits at start, no semicolons)
        if not re.match(r'^\d|.*[;]', val) and len(val) < 40:
            return val

        # Try to extract city: last comma-separated part that looks like a city
        parts = re.split(r'[,;]', val)
        parts = [p.strip() for p in parts if p.strip()]

        # Work backwards — find first part that looks like a place name (no digits)
        for part in reversed(parts):
            part = part.strip()
            if part and not re.search(r'\d', part) and len(part) > 2 and len(part) < 35:
                return part

        # Fallback: use province's main city
        province_main_city = {
            'Gauteng': 'Johannesburg',
            'Western Cape': 'Cape Town',
            'Eastern Cape': 'Gqeberha',
            'KwaZulu-Natal': 'Durban',
            'Limpopo': 'Polokwane',
            'Mpumalanga': 'Mbombela',
            'North West': 'Mahikeng',
            'Northern Cape': 'Kimberley',
            'Free State': 'Bloemfontein',
        }
        if province and province in province_main_city:
            return province_main_city[province]

        return val  # give up — keep original

    addr_mask = df['Town-City'].astype(str).str.match(r'^\d|.*[;]', na=False)
    addr_count = addr_mask.sum()
    if addr_count:
        df.loc[addr_mask, 'Town-City'] = df[addr_mask].apply(
            lambda row: clean_address_to_city(row['Town-City'], row.get('Province')),
            axis=1
        )
    print(f"  Street addresses cleaned: {addr_count} rows")

    # 4c. Remove extra spaces inside town names
    df['Town-City'] = df['Town-City'].str.strip()

    # 4d. Handle "No 22 Sloane Street, Bryanston" → "Bryanston" type case
    # (These remain after above — catch anything still starting with No./No )
    no_mask = df['Town-City'].astype(str).str.match(r'^No\.?\s*\d', na=False)
    if no_mask.sum():
        df.loc[no_mask, 'Town-City'] = df.loc[no_mask, 'Town-City'].apply(
            lambda v: clean_address_to_city(v)
        )
        print(f"  'No. X Street' addresses cleaned: {no_mask.sum()} rows")

# ─────────────────────────────────────────────
# FIX 5: EMAIL 1 — shift Email 2 when Email 1 is a person's name
# ─────────────────────────────────────────────
print("\n" + "="*60)
print("FIX 5 — Fix Email 1 (has names instead of emails)")
print("="*60)

email1_col = 'E-Mail Contact 1' if 'E-Mail Contact 1' in df.columns else 'Email 1'
email2_col = 'E-Mail Contact 2' if 'E-Mail Contact 2' in df.columns else 'Email 2'

if email1_col in df.columns and email2_col in df.columns:
    fixed_email = 0
    for idx, row in df.iterrows():
        e1 = row[email1_col]
        e2 = row[email2_col]
        if pd.notna(e1) and not is_email(e1):
            # Email 1 is not a valid email — check if Email 2 has the real one
            if pd.notna(e2) and is_email(e2):
                df.at[idx, email1_col] = e2
                df.at[idx, email2_col] = np.nan
                fixed_email += 1
            else:
                # Both are bad — clear Email 1 (it was a name)
                df.at[idx, email1_col] = np.nan
    print(f"  Shifted Email 2 → Email 1 for {fixed_email} rows")

# Lowercase all emails
for col in [email1_col, email2_col]:
    if col in df.columns:
        df[col] = df[col].apply(
            lambda x: x.strip().lower() if isinstance(x, str) else x
        )

# ─────────────────────────────────────────────
# FIX 6: PHONE NUMBER — remove emails and fix missing leading 0
# ─────────────────────────────────────────────
print("\n" + "="*60)
print("FIX 6 — Fix Phone Number column")
print("="*60)

phone_col = 'Contact Number2' if 'Contact Number2' in df.columns else 'Phone Number'
if phone_col in df.columns:
    email_in_phone = 0
    leading_zero_fixed = 0

    for idx, row in df.iterrows():
        phone = row[phone_col]
        if pd.isna(phone):
            continue
        phone_str = str(phone).strip()

        # If it's an email, remove it
        if '@' in phone_str:
            df.at[idx, phone_col] = np.nan
            email_in_phone += 1
            continue

        # Fix missing leading zero on SA numbers (9-digit numbers)
        digits_only = re.sub(r'[\s\-/+()\n]', '', phone_str)
        if digits_only.isdigit() and len(digits_only) == 9 and not digits_only.startswith('0'):
            # Prepend missing 0
            df.at[idx, phone_col] = '0' + digits_only
            leading_zero_fixed += 1

    print(f"  Emails removed from Phone Number: {email_in_phone}")
    print(f"  Missing leading 0 fixed: {leading_zero_fixed}")

# ─────────────────────────────────────────────
# FIX 7: PROVIDER TYPE — fill known blanks
# ─────────────────────────────────────────────
print("\n" + "="*60)
print("FIX 7 — Provider Type (85% null)")
print("="*60)

ptype_col = 'Provider Type'
if ptype_col in df.columns:
    nulls_before = df[ptype_col].isna().sum()
    df[ptype_col].fillna('Not Specified', inplace=True)
    print(f"  Filled {nulls_before} blanks with 'Not Specified'")
    print(f"  Note: Source data is incomplete here — treat 'Not Specified' as unknown.")

# ─────────────────────────────────────────────
# FIX 8: QUALIFICATION CATEGORY — more keywords, new categories
# ─────────────────────────────────────────────
print("\n" + "="*60)
print("FIX 8 — Expand Qualification Category mapping")
print("="*60)

title_col = 'Qual-Prog Title' if 'Qual-Prog Title' in df.columns else 'Qualification Title'

def categorise_qualification(title):
    if pd.isna(title):
        return 'Uncategorised'
    t = str(title).lower()

    # ICT & Data (MICT SETA focus — your primary interest)
    if any(kw in t for kw in [
        'data', 'analytics', 'analysis', 'software', 'developer', 'development',
        'systems', 'network', 'cyber', 'information technology', 'ict', 'digital',
        'computer', 'programming', 'database', 'web developer', 'technical support',
        'cloud', 'support technician', 'end user', 'it support',
    ]):
        return 'ICT & Data'

    # Business & Management
    if any(kw in t for kw in [
        'business', 'management', 'administrator', 'administration', 'manager',
        'operations', 'office', 'executive', 'supervision', 'supervisor',
        'entrepreneurship', 'enterprise',
    ]):
        return 'Business & Management'

    # Project Management (separate — useful for filtering)
    if 'project' in t and any(kw in t for kw in ['manage', 'coordinator', 'leader']):
        return 'Business & Management'

    # Finance & Accounting
    if any(kw in t for kw in [
        'finance', 'financial', 'accounting', 'accounts', 'bookkeep', 'bookkeeper',
        'auditor', 'audit', 'tax', 'payroll', 'treasury', 'credit', 'cost account',
    ]):
        return 'Finance & Accounting'

    # Investment & Wealth
    if any(kw in t for kw in [
        'investment', 'wealth', 'retirement', 'pension', 'fund', 'asset manag',
        'portfolio', 'adviser', 'advisor',
    ]):
        return 'Finance & Accounting'

    # Insurance & Banking
    if any(kw in t for kw in [
        'insurance', 'underwriter', 'broker', 'banking', 'bank', 'financial service',
        'short-term', 'long-term',
    ]):
        return 'Insurance & Banking'

    # Legal & Compliance
    if any(kw in t for kw in [
        'paralegal', 'legal', 'compliance', 'law', 'regulatory', 'governance',
    ]):
        return 'Legal & Compliance'

    # Health & Social Services
    if any(kw in t for kw in [
        'health', 'nursing', 'care', 'social', 'welfare', 'community', 'child',
        'counsel', 'therapist', 'medical', 'pharmacy', 'disability', 'first aid',
        'emergency', 'paramedic', 'ambulance', 'hiv', 'aids', 'auxiliary',
    ]):
        return 'Health & Social Services'

    # Engineering & Trades
    if any(kw in t for kw in [
        'electrician', 'electrical', 'engineer', 'mechanic', 'mechanical',
        'fitter', 'millwright', 'welder', 'boiler', 'diesel', 'motor',
        'artisan', 'rigger', 'automotive', 'instrumentation', 'refrigeration',
        'plumber', 'plumbing',
    ]):
        return 'Engineering & Trades'

    # Construction & Building
    if any(kw in t for kw in [
        'construction', 'bricklayer', 'carpenter', 'plasterer', 'builder',
        'civil', 'quantity', 'surveyor', 'painter', 'tiler', 'roofer',
        'glazier',
    ]):
        return 'Construction & Building'

    # Logistics & Supply Chain
    if any(kw in t for kw in [
        'logistics', 'supply chain', 'transport', 'freight', 'warehouse',
        'distribution', 'procurement', 'purchasing', 'forklift', 'driver',
        'shipping', 'customs',
    ]):
        return 'Logistics & Supply Chain'

    # HR & Training
    if any(kw in t for kw in [
        'human resource', 'hr ', 'hrm', 'facilitator', 'educator', 'assessor',
        'moderator', 'skills development', 'etdp', 'adult education', 'trainer',
        'training officer',
    ]):
        return 'HR & Training'

    # Agriculture & Environment
    if any(kw in t for kw in [
        'agri', 'farm', 'crop', 'livestock', 'horticulture', 'nature', 'game',
        'environmental', 'conservation', 'tractor operator', 'grader operator',
        'animal', 'aquaculture',
    ]):
        return 'Agriculture & Environment'

    # Hospitality & Tourism
    if any(kw in t for kw in [
        'hospitality', 'hotel', 'chef', 'cook', 'tourism', 'travel', 'guiding',
        'accommodation', 'food service', 'kitchen', 'catering', 'restaurant',
        'beverage',
    ]):
        return 'Hospitality & Tourism'

    # NEW: Marketing, Sales & Retail
    if any(kw in t for kw in [
        'marketing', 'sales', 'retail', 'customer service', 'customer care',
        'call centre', 'contact centre', 'merchandis', 'promotions',
    ]):
        return 'Marketing, Sales & Retail'

    # NEW: Beauty & Personal Care
    if any(kw in t for kw in [
        'beauty', 'hairdress', 'nail', 'make-up', 'makeup', 'cosmetology',
        'esthetician', 'personal care', 'spa', 'hair',
    ]):
        return 'Beauty & Personal Care'

    # NEW: Media, Communication & PR
    if any(kw in t for kw in [
        'journalist', 'journalism', 'media', 'public relations', 'pr ',
        'communication', 'copywriting', 'graphic design', 'photography',
        'broadcast', 'videograph',
    ]):
        return 'Media & Communications'

    # NEW: Real Estate & Property
    if any(kw in t for kw in [
        'real estate', 'property', 'estate agent',
    ]):
        return 'Real Estate & Property'

    # NEW: Sport & Fitness
    if any(kw in t for kw in [
        'fitness', 'sport', 'gym', 'exercise', 'coaching', 'referee',
        'physical education',
    ]):
        return 'Sport & Fitness'

    # NEW: Plant & Equipment Operations
    if any(kw in t for kw in [
        'crane operator', 'crane pendant', 'forklift', 'grader operator',
        'bulldozer', 'excavator', 'scraper operator', 'dozer', 'roller operator',
        'boom handler', 'track handler', 'plant operator',
    ]):
        return 'Plant & Equipment Operations'

    # Mining
    if any(kw in t for kw in [
        'mining', 'mine', 'blasting', 'rock', 'mineral', 'metallurg',
    ]):
        return 'Mining'

    # Public Sector
    if any(kw in t for kw in [
        'public sector', 'government', 'municipality', 'ward', 'councillor',
        'public administration', 'public management',
    ]):
        return 'Public Sector'

    # Security
    if any(kw in t for kw in [
        'security', 'guard', 'protection', 'close protection',
    ]):
        return 'Security'

    return 'Other'

if title_col in df.columns:
    before_other = (df.get('Qualification Category', pd.Series()) == 'Other').sum()
    df['Qualification Category'] = df[title_col].apply(categorise_qualification)
    after_other = (df['Qualification Category'] == 'Other').sum()
    print(f"  'Other' reduced from ~{before_other} → {after_other} rows")
    print("  Category distribution:")
    for cat, cnt in df['Qualification Category'].value_counts().items():
        print(f"    {cat:40s}: {cnt:,}")

# ─────────────────────────────────────────────
# ADD HELPER COLUMNS (Days Until Expiry, Has Contact Email, Is Old Trade)
# ─────────────────────────────────────────────
print("\n" + "="*60)
print("ADDING HELPER COLUMNS")
print("="*60)

end_col = 'Accreditation End Date' if 'Accreditation End Date' in df.columns else 'End Date'
if end_col in df.columns:
    df['Days Until Expiry'] = df[end_col].apply(
        lambda d: (d - TODAY).days if d and pd.notna(d) else None
    )
    print(f"  Added: Days Until Expiry")

if email1_col in df.columns:
    df['Has Contact Email'] = df[email1_col].apply(
        lambda x: 'Yes' if pd.notna(x) and str(x).strip() != '' else 'No'
    )
    contactable = (df['Has Contact Email'] == 'Yes').sum()
    print(f"  Added: Has Contact Email — {contactable:,} ({contactable/len(df)*100:.1f}%) have an email")

seta_col_final = 'SETA' if 'SETA' in df.columns else 'Quality Partner'
if seta_col_final in df.columns:
    df['Is Old Trade'] = df[seta_col_final].apply(
        lambda x: 'Yes' if str(x).upper() == 'OLD TRADES' else 'No'
    )

# ─────────────────────────────────────────────
# FINAL: RENAME, VALIDATE, EXPORT
# ─────────────────────────────────────────────
print("\n" + "="*60)
print("FINAL — Rename columns and export")
print("="*60)

rename_map = {
    'Qual-Prog Title':          'Qualification Title',
    'Qual-Prog ID':             'Qualification ID',
    'Qual-Prog NQF':            'NQF Level',
    'Qual-Prog Credits':        'Credits',
    'Quality Partner':          'SETA',
    'E-Mail Contact 1':         'Email 1',
    'E-Mail Contact 2':         'Email 2',
    'Contact Number2':          'Phone Number',
    'Contact Person Names':     'Contact Person',
    'Accreditation Status':     'Status',
    'Accreditation Start Date': 'Start Date',
    'Accreditation End Date':   'End Date',
    'Type of Accreditation':    'Accreditation Type',
}
df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns}, inplace=True)

# Convert dates to string for clean CSV export
for col in ['Start Date', 'End Date']:
    if col in df.columns:
        df[col] = df[col].apply(lambda x: x.strftime('%Y-%m-%d') if pd.notna(x) and x else '')

print("\n  FINAL SUMMARY")
print(f"  Original rows    : {original_rows:,}")
print(f"  Final rows       : {len(df):,}")
print(f"  Final columns    : {len(df.columns)}")
print(f"  Columns          : {list(df.columns)}")

if 'SETA' in df.columns and 'Status' in df.columns:
    mict = df[(df['SETA'] == 'MICT SETA') & (df['Status'].str.lower() == 'active')]
    print(f"\n  Active MICT SETA providers in dataset: {len(mict):,}")

# Remaining "Other" qualifications — print so you can review and add keywords
other_titles = df[df['Qualification Category'] == 'Other']['Qualification Title'].value_counts()
if len(other_titles):
    print(f"\n  REMAINING 'Other' qualification titles (review these):")
    for title, count in other_titles.head(20).items():
        print(f"    [{count}] {title}")

df.to_csv(OUTPUT_FILE, index=False, encoding='utf-8-sig')
print(f"\n  Saved: {OUTPUT_FILE}")
print("\n" + "="*60)
print("  DONE.")
print("="*60 + "\n")
