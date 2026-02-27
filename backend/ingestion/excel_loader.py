"""Load properties from the Excel source file."""

import logging
import math

import pandas as pd

from ingestion.location_normalizer import canonicalize_city, canonicalize_state
from models.property import EXCEL_COLUMN_MAP, Property

logger = logging.getLogger(__name__)


def _clean_value(v: object) -> object:
    """Convert pandas NaN/NaT to None. Handles float NaN that .where() misses."""
    if v is None:
        return None
    if isinstance(v, float) and math.isnan(v):
        return None
    if pd.isna(v):
        return None
    return v


def load_properties(path: str) -> list[Property]:
    """Read the Excel file and return a list of validated Property objects.

    - Renames columns via EXCEL_COLUMN_MAP
    - Converts pandas NaN → None
    - Canonicalizes state and city names
    - Deduplicates by ID (keeps first occurrence)
    """
    df = pd.read_excel(path)
    logger.info("Read %d rows from %s", len(df), path)

    # Rename Excel columns to Property field names
    df = df.rename(columns=EXCEL_COLUMN_MAP)

    # Keep only columns we know about
    known_cols = [c for c in EXCEL_COLUMN_MAP.values() if c in df.columns]
    df = df[known_cols]

    # Deduplicate by ID, keep first
    before = len(df)
    df = df.drop_duplicates(subset="id", keep="first")
    dupes = before - len(df)
    if dupes:
        logger.info("Dropped %d duplicate IDs", dupes)

    properties: list[Property] = []
    errors = 0
    for _, row in df.iterrows():
        # Clean every value to convert NaN → None
        row_dict = {k: _clean_value(v) for k, v in row.to_dict().items()}

        # Canonicalize locations before creating Property
        row_dict["state"] = canonicalize_state(row_dict.get("state"))
        row_dict["city"] = canonicalize_city(row_dict.get("city"))

        try:
            prop = Property(**row_dict)
            properties.append(prop)
        except Exception:
            errors += 1
            if errors <= 5:
                logger.warning("Failed to parse row: %s", row_dict.get("id"), exc_info=True)

    if errors:
        logger.warning("Total parse errors: %d / %d rows", errors, before)

    logger.info("Loaded %d properties", len(properties))
    return properties
