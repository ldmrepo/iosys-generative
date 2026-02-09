#!/usr/bin/env python3
"""Script to run IML sampling."""

import sys
from pathlib import Path

# Add src to path for direct execution
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.samplers.stratified_sampler import run_sampling


def main() -> None:
    """Run the sampling process with default settings."""
    # Default paths relative to this script
    script_dir = Path(__file__).parent
    project_dir = script_dir.parent

    # Default directories (can be overridden via environment or CLI)
    raw_dir = project_dir / ".." / ".." / ".." / ".." / "data" / "raw"
    output_dir = project_dir / ".." / ".." / ".." / ".." / "data" / "sample"

    # Resolve to absolute paths
    raw_dir = raw_dir.resolve()
    output_dir = output_dir.resolve()

    print(f"Raw directory: {raw_dir}")
    print(f"Output directory: {output_dir}")

    if not raw_dir.exists():
        print(f"Error: Raw directory does not exist: {raw_dir}")
        sys.exit(1)

    # Run sampling
    report = run_sampling(
        raw_dir=raw_dir,
        output_dir=output_dir,
        samples_per_group=30,
        require_images=True,
        seed=42,
    )

    print(f"\nSampling complete!")
    print(f"Total items sampled: {report.total_items_sampled}")


if __name__ == "__main__":
    main()
