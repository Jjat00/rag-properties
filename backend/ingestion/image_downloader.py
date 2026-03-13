"""Download property images to local disk for multimodal embedding."""

import asyncio
import logging
from pathlib import Path

import httpx

from models.multimodal_property import MultimodalProperty

logger = logging.getLogger(__name__)

_MAX_CONCURRENCY = 10
_TIMEOUT = 30.0
_MAX_IMAGES_PER_PROPERTY = 6


async def download_property_images(
    properties: list[MultimodalProperty],
    output_dir: Path,
) -> dict[str, list[Path]]:
    """Download images for each property to disk.

    Images are saved as: output_dir/{firebase_id or id}/img_0.jpeg, img_1.jpeg, etc.
    Skips if already downloaded (idempotent).

    Returns a map of {property_id: [local_paths]}.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    semaphore = asyncio.Semaphore(_MAX_CONCURRENCY)
    image_map: dict[str, list[Path]] = {}

    async with httpx.AsyncClient(timeout=_TIMEOUT, follow_redirects=True) as client:
        tasks = [
            _download_for_property(prop, output_dir, client, semaphore)
            for prop in properties
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    for prop, result in zip(properties, results):
        if isinstance(result, Exception):
            logger.warning("Failed to download images for %s: %s", prop.id, result)
            image_map[prop.id] = []
        else:
            image_map[prop.id] = result

    total_images = sum(len(paths) for paths in image_map.values())
    props_with_images = sum(1 for paths in image_map.values() if paths)
    logger.info(
        "Downloaded %d images for %d/%d properties",
        total_images,
        props_with_images,
        len(properties),
    )
    return image_map


async def _download_for_property(
    prop: MultimodalProperty,
    output_dir: Path,
    client: httpx.AsyncClient,
    semaphore: asyncio.Semaphore,
) -> list[Path]:
    """Download images for a single property."""
    prop_dir_name = prop.firebase_id or prop.id
    prop_dir = output_dir / prop_dir_name
    prop_dir.mkdir(parents=True, exist_ok=True)

    pictures = prop.pictures[:_MAX_IMAGES_PER_PROPERTY]
    paths: list[Path] = []

    for i, url in enumerate(pictures):
        file_path = prop_dir / f"img_{i}.jpeg"

        # Skip if already downloaded
        if file_path.exists() and file_path.stat().st_size > 0:
            paths.append(file_path)
            continue

        async with semaphore:
            try:
                response = await client.get(url)
                response.raise_for_status()
                file_path.write_bytes(response.content)
                paths.append(file_path)
            except Exception:
                logger.debug("Failed to download image %d for %s: %s", i, prop.id, url)

    return paths
