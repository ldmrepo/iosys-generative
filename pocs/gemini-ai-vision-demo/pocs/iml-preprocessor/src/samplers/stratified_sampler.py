"""Stratified sampler for IML items by subject and grade."""

from __future__ import annotations

import json
import random
import shutil
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from rich.console import Console
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)
from tqdm import tqdm

from ..core.config import Settings, get_settings
from ..core.schemas import GroupSamplingResult, IMLItem, SamplingReport
from ..parsers.iml_parser import IMLParser
from ..utils.encoding import convert_file_to_utf8
from ..utils.image_utils import copy_images, find_item_images

console = Console()


class StratifiedSampler:
    """Stratified sampler for IML items."""

    def __init__(self, settings: Settings | None = None):
        """
        Initialize the sampler.

        Args:
            settings: Application settings
        """
        self.settings = settings or get_settings()
        self.parser = IMLParser(self.settings)

    def scan_raw_directory(
        self,
        raw_dir: Path,
        require_images: bool = True,
        show_progress: bool = True,
    ) -> dict[tuple[str, str], list[IMLItem]]:
        """
        Scan the raw data directory and group items by subject/grade.

        Args:
            raw_dir: Path to the raw data directory
            require_images: Only include items with images
            show_progress: Show progress bar

        Returns:
            Dictionary mapping (subject, grade) tuples to lists of items
        """
        grouped: dict[tuple[str, str], list[IMLItem]] = defaultdict(list)
        parse_errors: list[str] = []

        # Find all IML files
        iml_files = list(raw_dir.rglob("*.iml"))
        console.print(f"[blue]Found {len(iml_files)} IML files to scan[/blue]")

        # Parse each file
        iterator = tqdm(iml_files, desc="Scanning IML files") if show_progress else iml_files

        for iml_path in iterator:
            item = self.parser.parse_file(iml_path)

            if item is None:
                parse_errors.append(str(iml_path))
                continue

            # Filter by image requirement
            if require_images and not item.has_images:
                continue

            # Only include items with valid subject and grade
            if not item.subject or not item.grade:
                continue

            # Check if subject/grade is in our target list
            if item.subject not in self.settings.TARGET_SUBJECTS:
                continue
            if item.grade not in self.settings.TARGET_GRADES:
                continue

            # Add to group
            key = (item.subject, item.grade)
            grouped[key].append(item)

        console.print(f"[green]Scanned {len(iml_files)} files[/green]")
        console.print(f"[yellow]Parse errors: {len(parse_errors)}[/yellow]")

        return grouped

    def sample_items(
        self,
        raw_dir: Path,
        output_dir: Path,
        samples_per_group: int = 30,
        require_images: bool = True,
        seed: int | None = 42,
        show_progress: bool = True,
    ) -> SamplingReport:
        """
        Sample items from the raw directory and save to output.

        Args:
            raw_dir: Path to raw data directory
            output_dir: Path to output directory
            samples_per_group: Number of samples per subject/grade group
            require_images: Only sample items with images
            seed: Random seed for reproducibility
            show_progress: Show progress indicators

        Returns:
            Sampling report with statistics
        """
        if seed is not None:
            random.seed(seed)

        # Initialize report
        report = SamplingReport(
            raw_data_dir=str(raw_dir),
            output_dir=str(output_dir),
            samples_per_group=samples_per_group,
            require_images=require_images,
        )

        # Scan and group items
        console.print("[bold blue]Step 1: Scanning raw data directory...[/bold blue]")
        grouped = self.scan_raw_directory(raw_dir, require_images, show_progress)

        report.total_items_scanned = sum(len(items) for items in grouped.values())
        report.total_items_with_images = report.total_items_scanned  # Already filtered

        console.print(f"[green]Found {report.total_items_scanned} items with images[/green]")

        # Sample from each group
        console.print("\n[bold blue]Step 2: Sampling from each group...[/bold blue]")

        for subject in self.settings.TARGET_SUBJECTS:
            for grade in self.settings.TARGET_GRADES:
                key = (subject, grade)
                items = grouped.get(key, [])

                # Sample items
                if len(items) <= samples_per_group:
                    sampled = items
                else:
                    sampled = random.sample(items, samples_per_group)

                # Create group result
                group_result = GroupSamplingResult(
                    subject=subject,
                    grade=grade,
                    target_count=samples_per_group,
                    actual_count=len(sampled),
                    items=sampled,
                )
                report.groups.append(group_result)

                # Update statistics
                if subject not in report.by_subject:
                    report.by_subject[subject] = 0
                report.by_subject[subject] += len(sampled)

                if grade not in report.by_grade:
                    report.by_grade[grade] = 0
                report.by_grade[grade] += len(sampled)

                report.total_items_sampled += len(sampled)

                if len(sampled) > 0:
                    status = "✓" if len(sampled) >= samples_per_group else "△"
                    console.print(
                        f"  {status} {subject}/{grade}: {len(sampled)}/{samples_per_group}"
                    )
                else:
                    console.print(f"  ✗ {subject}/{grade}: 0/{samples_per_group} [red](no data)[/red]")

        # Save sampled items
        console.print("\n[bold blue]Step 3: Saving sampled items...[/bold blue]")
        self._save_samples(report, raw_dir, output_dir, show_progress)

        # Save report
        report_path = output_dir / "sampling_report.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report.model_dump(), f, ensure_ascii=False, indent=2, default=str)

        console.print(f"\n[bold green]Sampling complete![/bold green]")
        console.print(f"  Total items sampled: {report.total_items_sampled}")
        console.print(f"  Report saved to: {report_path}")

        return report

    def _save_samples(
        self,
        report: SamplingReport,
        raw_dir: Path,
        output_dir: Path,
        show_progress: bool = True,
    ) -> None:
        """
        Save sampled items to the output directory.

        Creates the following structure:
        output_dir/
        ├── {subject}/
        │   ├── {grade}/
        │   │   ├── {item_id}/
        │   │   │   ├── item.json
        │   │   │   ├── item.iml
        │   │   │   └── images/
        │   │   │       └── *.png
        """
        total_items = sum(len(g.items) for g in report.groups)
        progress_bar = tqdm(total=total_items, desc="Saving items") if show_progress else None

        for group in report.groups:
            if not group.items:
                continue

            # Create subject/grade directory
            group_dir = output_dir / group.subject / group.grade
            group_dir.mkdir(parents=True, exist_ok=True)

            for item in group.items:
                item_dir = group_dir / item.id
                item_dir.mkdir(parents=True, exist_ok=True)

                # Save item metadata as JSON
                item_json_path = item_dir / "item.json"
                with open(item_json_path, "w", encoding="utf-8") as f:
                    json.dump(item.model_dump(), f, ensure_ascii=False, indent=2, default=str)

                # Convert and save IML file
                iml_output_path = item_dir / "item.iml"
                convert_file_to_utf8(item.raw_path, iml_output_path)

                # Copy images
                if item.images:
                    images_dir = item_dir / "images"
                    images_dir.mkdir(parents=True, exist_ok=True)

                    # Get the source directory (parent of IML file)
                    source_base = item.raw_path.parent

                    for img_path in item.images:
                        # Normalize and find source
                        img_path_normalized = img_path.replace("\\", "/")
                        source_img = source_base / img_path_normalized

                        if source_img.exists():
                            dest_img = images_dir / source_img.name
                            try:
                                shutil.copy2(source_img, dest_img)
                            except Exception:
                                pass
                        else:
                            # Try without subdirectory prefix
                            img_name = Path(img_path_normalized).name
                            # Search in DrawObjPic
                            draw_dir = source_base / item.id / "DrawObjPic"
                            if draw_dir.exists():
                                for f in draw_dir.iterdir():
                                    if f.name == img_name:
                                        dest_img = images_dir / f.name
                                        try:
                                            shutil.copy2(f, dest_img)
                                        except Exception:
                                            pass
                                        break

                if progress_bar:
                    progress_bar.update(1)

        if progress_bar:
            progress_bar.close()


def run_sampling(
    raw_dir: Path,
    output_dir: Path,
    samples_per_group: int = 30,
    require_images: bool = True,
    seed: int | None = 42,
) -> SamplingReport:
    """
    Convenience function to run sampling.

    Args:
        raw_dir: Path to raw data directory
        output_dir: Path to output directory
        samples_per_group: Number of samples per group
        require_images: Only sample items with images
        seed: Random seed

    Returns:
        Sampling report
    """
    sampler = StratifiedSampler()
    return sampler.sample_items(
        raw_dir=raw_dir,
        output_dir=output_dir,
        samples_per_group=samples_per_group,
        require_images=require_images,
        seed=seed,
    )
