"""Canonical team registry.

Design:
- Canonical team ID = kebab-case slug of the *current* identity
  (e.g. "south-korea"). Matches played under former names (Zaïre, Soviet
  Union, ...) are attributed to the current identity per the upstream
  former_names mapping, while the era-accurate display name is preserved on
  each match row as `home_team_name` / `away_team_name`.
- Deliberately-distinct historical teams (Czechoslovakia, East Germany,
  Yugoslavia, ...) are NOT merged into successors: the upstream dataset and
  football historiography treat them as separate national teams.
- `flag_code` targets the MIT-licensed `flag-icons` package (ISO 3166-1
  alpha-2, plus gb-eng / gb-sct / gb-wls / gb-nir and xk for Kosovo).
  Teams without a licensed flag (CONIFA sides, dissolved states) get
  flag_code=None and the UI renders a neutral fallback glyph + text label.
"""

from __future__ import annotations

import csv
import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from kickoff_ml.config import RAW_DIR


def slugify(name: str) -> str:
    """Stable ASCII kebab-case slug for a team display name."""
    norm = unicodedata.normalize("NFKD", name)
    ascii_ = norm.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "-", ascii_.lower()).strip("-")


# Canonical display name -> flag-icons code (ISO alpha-2 lowercase).
FLAG_CODES: dict[str, str] = {
    # UEFA
    "Albania": "al", "Andorra": "ad", "Armenia": "am", "Austria": "at",
    "Azerbaijan": "az", "Belarus": "by", "Belgium": "be",
    "Bosnia and Herzegovina": "ba", "Bulgaria": "bg", "Croatia": "hr",
    "Cyprus": "cy", "Czech Republic": "cz", "Denmark": "dk", "England": "gb-eng",
    "Estonia": "ee", "Faroe Islands": "fo", "Finland": "fi", "France": "fr",
    "Georgia": "ge", "Germany": "de", "Gibraltar": "gi", "Greece": "gr",
    "Hungary": "hu", "Iceland": "is", "Israel": "il", "Italy": "it",
    "Kazakhstan": "kz", "Kosovo": "xk", "Latvia": "lv", "Liechtenstein": "li",
    "Lithuania": "lt", "Luxembourg": "lu", "Malta": "mt", "Moldova": "md",
    "Monaco": "mc", "Montenegro": "me", "Netherlands": "nl",
    "North Macedonia": "mk", "Northern Ireland": "gb-nir", "Norway": "no",
    "Poland": "pl", "Portugal": "pt", "Republic of Ireland": "ie",
    "Romania": "ro", "Russia": "ru", "San Marino": "sm", "Scotland": "gb-sct",
    "Serbia": "rs", "Slovakia": "sk", "Slovenia": "si", "Spain": "es",
    "Sweden": "se", "Switzerland": "ch", "Turkey": "tr", "Ukraine": "ua",
    "Wales": "gb-wls",
    # CONMEBOL
    "Argentina": "ar", "Bolivia": "bo", "Brazil": "br", "Chile": "cl",
    "Colombia": "co", "Ecuador": "ec", "Paraguay": "py", "Peru": "pe",
    "Uruguay": "uy", "Venezuela": "ve",
    # CONCACAF
    "Anguilla": "ai", "Antigua and Barbuda": "ag", "Aruba": "aw",
    "Bahamas": "bs", "Barbados": "bb", "Belize": "bz", "Bermuda": "bm",
    "Bonaire": "bq", "British Virgin Islands": "vg", "Canada": "ca",
    "Cayman Islands": "ky", "Costa Rica": "cr", "Cuba": "cu", "Curaçao": "cw",
    "Dominica": "dm", "Dominican Republic": "do", "El Salvador": "sv",
    "Grenada": "gd", "Guadeloupe": "gp", "Guatemala": "gt", "Guyana": "gy",
    "Haiti": "ht", "Honduras": "hn", "Jamaica": "jm", "Martinique": "mq",
    "Mexico": "mx", "Montserrat": "ms", "Nicaragua": "ni", "Panama": "pa",
    "Puerto Rico": "pr", "Saint Kitts and Nevis": "kn", "Saint Lucia": "lc",
    "Saint Martin": "mf", "Saint Vincent and the Grenadines": "vc",
    "Sint Maarten": "sx", "Suriname": "sr", "Trinidad and Tobago": "tt",
    "Turks and Caicos Islands": "tc", "United States": "us",
    "United States Virgin Islands": "vi", "French Guiana": "gf",
    # CAF
    "Algeria": "dz", "Angola": "ao", "Benin": "bj", "Botswana": "bw",
    "Burkina Faso": "bf", "Burundi": "bi", "Cameroon": "cm",
    "Cape Verde": "cv", "Central African Republic": "cf", "Chad": "td",
    "Comoros": "km", "Congo": "cg", "DR Congo": "cd", "Djibouti": "dj",
    "Egypt": "eg", "Equatorial Guinea": "gq", "Eritrea": "er",
    "Eswatini": "sz", "Ethiopia": "et", "Gabon": "ga", "Gambia": "gm",
    "Ghana": "gh", "Guinea": "gn", "Guinea-Bissau": "gw", "Ivory Coast": "ci",
    "Kenya": "ke", "Lesotho": "ls", "Liberia": "lr", "Libya": "ly",
    "Madagascar": "mg", "Malawi": "mw", "Mali": "ml", "Mauritania": "mr",
    "Mauritius": "mu", "Morocco": "ma", "Mozambique": "mz", "Namibia": "na",
    "Niger": "ne", "Nigeria": "ng", "Rwanda": "rw",
    "São Tomé and Príncipe": "st", "Senegal": "sn", "Seychelles": "sc",
    "Sierra Leone": "sl", "Somalia": "so", "South Africa": "za",
    "South Sudan": "ss", "Sudan": "sd", "Tanzania": "tz", "Togo": "tg",
    "Tunisia": "tn", "Uganda": "ug", "Zambia": "zm", "Zimbabwe": "zw",
    "Réunion": "re", "Mayotte": "yt",
    # AFC
    "Afghanistan": "af", "Australia": "au", "Bahrain": "bh",
    "Bangladesh": "bd", "Bhutan": "bt", "Brunei": "bn", "Cambodia": "kh",
    "China": "cn", "Guam": "gu", "Hong Kong": "hk", "India": "in",
    "Indonesia": "id", "Iran": "ir", "Iraq": "iq", "Japan": "jp",
    "Jordan": "jo", "Kuwait": "kw", "Kyrgyzstan": "kg", "Laos": "la",
    "Lebanon": "lb", "Macau": "mo", "Malaysia": "my", "Maldives": "mv",
    "Mongolia": "mn", "Myanmar": "mm", "Nepal": "np", "North Korea": "kp",
    "Northern Mariana Islands": "mp", "Oman": "om", "Pakistan": "pk",
    "Palestine": "ps", "Philippines": "ph", "Qatar": "qa",
    "Saudi Arabia": "sa", "Singapore": "sg", "South Korea": "kr",
    "Sri Lanka": "lk", "Syria": "sy", "Taiwan": "tw", "Tajikistan": "tj",
    "Thailand": "th", "Timor-Leste": "tl", "Turkmenistan": "tm",
    "United Arab Emirates": "ae", "Uzbekistan": "uz", "Vietnam": "vn",
    "Yemen": "ye",
    # OFC
    "American Samoa": "as", "Cook Islands": "ck", "Fiji": "fj",
    "Kiribati": "ki", "Marshall Islands": "mh", "New Caledonia": "nc",
    "New Zealand": "nz", "Papua New Guinea": "pg", "Samoa": "ws",
    "Solomon Islands": "sb", "Tahiti": "pf", "Tonga": "to", "Tuvalu": "tv",
    "Vanuatu": "vu", "Niue": "nu",
    # Non-FIFA with ISO codes
    "Greenland": "gl", "Vatican City": "va", "Falkland Islands": "fk",
    "Saint Helena": "sh", "Saint Barthélemy": "bl", "Åland Islands": "ax",
    "Isle of Man": "im", "Jersey": "je", "Guernsey": "gg", "Norfolk Island": "nf",
}

CONFEDERATIONS: dict[str, str] = {}
for _conf, _names in {
    "UEFA": [
        "Albania", "Andorra", "Armenia", "Austria", "Azerbaijan", "Belarus",
        "Belgium", "Bosnia and Herzegovina", "Bulgaria", "Croatia", "Cyprus",
        "Czech Republic", "Denmark", "England", "Estonia", "Faroe Islands",
        "Finland", "France", "Georgia", "Germany", "Gibraltar", "Greece",
        "Hungary", "Iceland", "Israel", "Italy", "Kazakhstan", "Kosovo",
        "Latvia", "Liechtenstein", "Lithuania", "Luxembourg", "Malta",
        "Moldova", "Montenegro", "Netherlands", "North Macedonia",
        "Northern Ireland", "Norway", "Poland", "Portugal",
        "Republic of Ireland", "Romania", "Russia", "San Marino", "Scotland",
        "Serbia", "Slovakia", "Slovenia", "Spain", "Sweden", "Switzerland",
        "Turkey", "Ukraine", "Wales",
        # Historical UEFA-region teams kept distinct
        "Czechoslovakia", "East Germany", "Yugoslavia", "Saarland",
    ],
    "CONMEBOL": [
        "Argentina", "Bolivia", "Brazil", "Chile", "Colombia", "Ecuador",
        "Paraguay", "Peru", "Uruguay", "Venezuela",
    ],
    "CONCACAF": [
        "Anguilla", "Antigua and Barbuda", "Aruba", "Bahamas", "Barbados",
        "Belize", "Bermuda", "Bonaire", "British Virgin Islands", "Canada",
        "Cayman Islands", "Costa Rica", "Cuba", "Curaçao", "Dominica",
        "Dominican Republic", "El Salvador", "French Guiana", "Grenada",
        "Guadeloupe", "Guatemala", "Guyana", "Haiti", "Honduras", "Jamaica",
        "Martinique", "Mexico", "Montserrat", "Nicaragua", "Panama",
        "Puerto Rico", "Saint Kitts and Nevis", "Saint Lucia", "Saint Martin",
        "Saint Vincent and the Grenadines", "Sint Maarten", "Suriname",
        "Trinidad and Tobago", "Turks and Caicos Islands", "United States",
        "United States Virgin Islands",
    ],
    "CAF": [
        "Algeria", "Angola", "Benin", "Botswana", "Burkina Faso", "Burundi",
        "Cameroon", "Cape Verde", "Central African Republic", "Chad",
        "Comoros", "Congo", "DR Congo", "Djibouti", "Egypt",
        "Equatorial Guinea", "Eritrea", "Eswatini", "Ethiopia", "Gabon",
        "Gambia", "Ghana", "Guinea", "Guinea-Bissau", "Ivory Coast", "Kenya",
        "Lesotho", "Liberia", "Libya", "Madagascar", "Malawi", "Mali",
        "Mauritania", "Mauritius", "Morocco", "Mozambique", "Namibia",
        "Niger", "Nigeria", "Rwanda", "São Tomé and Príncipe", "Senegal",
        "Seychelles", "Sierra Leone", "Somalia", "South Africa",
        "South Sudan", "Sudan", "Tanzania", "Togo", "Tunisia", "Uganda",
        "Zambia", "Zimbabwe", "Réunion", "Mayotte",
    ],
    "AFC": [
        "Afghanistan", "Australia", "Bahrain", "Bangladesh", "Bhutan",
        "Brunei", "Cambodia", "China", "Guam", "Hong Kong", "India",
        "Indonesia", "Iran", "Iraq", "Japan", "Jordan", "Kuwait",
        "Kyrgyzstan", "Laos", "Lebanon", "Macau", "Malaysia", "Maldives",
        "Mongolia", "Myanmar", "Nepal", "North Korea",
        "Northern Mariana Islands", "Oman", "Pakistan", "Palestine",
        "Philippines", "Qatar", "Saudi Arabia", "Singapore", "South Korea",
        "Sri Lanka", "Syria", "Taiwan", "Tajikistan", "Thailand",
        "Timor-Leste", "Turkmenistan", "United Arab Emirates", "Uzbekistan",
        "Vietnam", "Yemen",
    ],
    "OFC": [
        "American Samoa", "Cook Islands", "Fiji", "Kiribati",
        "Marshall Islands", "New Caledonia", "New Zealand",
        "Papua New Guinea", "Samoa", "Solomon Islands", "Tahiti", "Tonga",
        "Tuvalu", "Vanuatu", "Niue",
    ],
}.items():
    for _n in _names:
        CONFEDERATIONS[_n] = _conf


@dataclass(frozen=True)
class Team:
    team_id: str          # canonical slug
    name: str             # current display name
    flag_code: str | None  # flag-icons code or None -> UI fallback
    confederation: str    # UEFA/CONMEBOL/CONCACAF/CAF/AFC/OFC/OTHER
    is_historical: bool   # dissolved identity kept distinct


@lru_cache(maxsize=1)
def former_name_map(raw_dir: str | None = None) -> dict[str, str]:
    """Era name -> current display name, from the upstream former_names file."""
    path = Path(raw_dir) if raw_dir else RAW_DIR
    f = path / "former_names.csv"
    mapping: dict[str, str] = {}
    if f.exists():
        with f.open(newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                mapping[row["former"]] = row["current"]
    return mapping


HISTORICAL_DISTINCT = {"Czechoslovakia", "East Germany", "Yugoslavia", "Saarland"}


def canonicalize(name: str) -> tuple[str, str]:
    """Return (team_id, current_display_name) for an era-accurate name."""
    current = former_name_map().get(name, name)
    return slugify(current), current


def build_team(name: str) -> Team:
    team_id, current = canonicalize(name)
    return Team(
        team_id=team_id,
        name=current,
        flag_code=FLAG_CODES.get(current),
        confederation=CONFEDERATIONS.get(current, "OTHER"),
        is_historical=current in HISTORICAL_DISTINCT,
    )
