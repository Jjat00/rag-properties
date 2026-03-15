"""Load multimodal properties from a JSON file (MongoDB export)."""

import json
import logging
from pathlib import Path

from models.multimodal_property import MultimodalProperty

logger = logging.getLogger(__name__)


def load_multimodal_properties(path: str) -> list[MultimodalProperty]:
    """Read JSON array and return parsed MultimodalProperty objects.

    Only includes properties with ad_status == "Publicado".
    """
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"JSON file not found: {path}")

    with open(file_path, encoding="utf-8") as f:
        raw_data: list[dict] = json.load(f)

    logger.info("Loaded %d raw documents from %s", len(raw_data), path)

    properties: list[MultimodalProperty] = []
    skipped = 0
    for raw in raw_data:
        if raw.get("ad_status") != "Publicado":
            skipped += 1
            continue
        try:
            prop = MultimodalProperty.from_json(raw)
            properties.append(prop)
        except Exception:
            logger.warning("Failed to parse document: %s", raw.get("_id"), exc_info=True)
            skipped += 1

    logger.info(
        "Parsed %d multimodal properties (%d skipped)",
        len(properties),
        skipped,
    )
    return properties
