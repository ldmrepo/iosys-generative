"""Image utilities for validation and copying."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Dict, List, Optional

from PIL import Image


def validate_image(image_path: Path) -> bool:
    """
    Validate that a file is a valid image.

    Args:
        image_path: Path to the image file

    Returns:
        True if valid image, False otherwise
    """
    if not image_path.exists():
        return False

    try:
        with Image.open(image_path) as img:
            img.verify()
        return True
    except Exception:
        return False


def get_image_info(image_path: Path) -> dict | None:
    """
    Get information about an image file.

    Args:
        image_path: Path to the image file

    Returns:
        Dictionary with image info or None if invalid
    """
    if not image_path.exists():
        return None

    try:
        with Image.open(image_path) as img:
            return {
                "path": str(image_path),
                "format": img.format,
                "mode": img.mode,
                "width": img.width,
                "height": img.height,
                "size_bytes": image_path.stat().st_size,
            }
    except Exception:
        return None


def copy_images(
    source_dir: Path,
    dest_dir: Path,
    image_paths: list[str],
    validate: bool = True,
) -> list[str]:
    """
    Copy images from source to destination directory.

    Args:
        source_dir: Base directory containing IML files
        dest_dir: Destination directory for images
        image_paths: List of relative image paths from IML
        validate: Whether to validate images before copying

    Returns:
        List of successfully copied image paths (relative to dest_dir)
    """
    copied: list[str] = []
    dest_dir.mkdir(parents=True, exist_ok=True)

    for rel_path in image_paths:
        # Normalize path separators
        rel_path_normalized = rel_path.replace("\\", "/")

        # Try to find the source image
        # IML paths may be relative to the IML file or include subdirectories
        possible_sources = [
            source_dir / rel_path_normalized,
            source_dir / Path(rel_path_normalized).name,
        ]

        source_found = None
        for source_path in possible_sources:
            if source_path.exists():
                source_found = source_path
                break

        if source_found is None:
            continue

        # Validate if requested
        if validate and not validate_image(source_found):
            continue

        # Copy to destination
        dest_filename = source_found.name
        dest_path = dest_dir / dest_filename

        # Handle duplicate filenames
        counter = 1
        while dest_path.exists():
            stem = source_found.stem
            suffix = source_found.suffix
            dest_filename = f"{stem}_{counter}{suffix}"
            dest_path = dest_dir / dest_filename
            counter += 1

        try:
            shutil.copy2(source_found, dest_path)
            copied.append(dest_filename)
        except Exception:
            continue

    return copied


def find_item_images(item_dir: Path) -> list[Path]:
    """
    Find all image files in an item's directory.

    Looks for images in:
    - {item_dir}/DrawObjPic/
    - {item_dir}/

    Args:
        item_dir: Directory containing the item

    Returns:
        List of image file paths
    """
    image_extensions = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".webp"}
    images: list[Path] = []

    # Check DrawObjPic subdirectory
    drawobj_dir = item_dir / "DrawObjPic"
    if drawobj_dir.exists():
        for file_path in drawobj_dir.iterdir():
            if file_path.suffix.lower() in image_extensions:
                images.append(file_path)

    # Also check item directory itself
    for file_path in item_dir.iterdir():
        if file_path.is_file() and file_path.suffix.lower() in image_extensions:
            images.append(file_path)

    return images
