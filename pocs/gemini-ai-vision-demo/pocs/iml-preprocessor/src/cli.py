"""CLI interface for IML Preprocessor."""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from .core.config import get_settings
from .parsers.iml_parser import IMLParser
from .samplers.stratified_sampler import StratifiedSampler

app = typer.Typer(
    name="iml-preprocess",
    help="IML 문항 데이터 전처리 및 샘플링 도구",
    add_completion=False,
)
console = Console()


@app.command()
def sample(
    raw_dir: Path = typer.Option(
        None,
        "--raw-dir",
        "-r",
        help="Raw IML data directory",
    ),
    output_dir: Path = typer.Option(
        None,
        "--output-dir",
        "-o",
        help="Output directory for samples",
    ),
    samples: int = typer.Option(
        30,
        "--samples",
        "-n",
        help="Number of samples per subject/grade group",
    ),
    no_images: bool = typer.Option(
        False,
        "--no-images",
        help="Include items without images",
    ),
    seed: Optional[int] = typer.Option(
        42,
        "--seed",
        "-s",
        help="Random seed for reproducibility",
    ),
) -> None:
    """
    Sample IML items by subject and grade.

    Creates a stratified sample of IML items, organized by subject and grade,
    with images copied to the output directory.
    """
    settings = get_settings()

    # Use defaults from settings if not provided
    if raw_dir is None:
        raw_dir = settings.raw_data_dir
    if output_dir is None:
        output_dir = settings.sample_output_dir

    # Resolve relative paths
    raw_dir = raw_dir.resolve()
    output_dir = output_dir.resolve()

    if not raw_dir.exists():
        console.print(f"[red]Error: Raw directory does not exist: {raw_dir}[/red]")
        raise typer.Exit(1)

    console.print("[bold]IML Preprocessor - Stratified Sampling[/bold]")
    console.print(f"  Raw directory: {raw_dir}")
    console.print(f"  Output directory: {output_dir}")
    console.print(f"  Samples per group: {samples}")
    console.print(f"  Require images: {not no_images}")
    console.print(f"  Random seed: {seed}")
    console.print()

    sampler = StratifiedSampler(settings)
    report = sampler.sample_items(
        raw_dir=raw_dir,
        output_dir=output_dir,
        samples_per_group=samples,
        require_images=not no_images,
        seed=seed,
    )

    # Print summary table
    console.print("\n[bold]Sampling Summary[/bold]")

    table = Table(title="By Subject")
    table.add_column("Subject", style="cyan")
    table.add_column("Count", justify="right")

    for subject, count in sorted(report.by_subject.items()):
        table.add_row(subject, str(count))

    console.print(table)

    table = Table(title="By Grade")
    table.add_column("Grade", style="cyan")
    table.add_column("Count", justify="right")

    for grade in settings.TARGET_GRADES:
        count = report.by_grade.get(grade, 0)
        table.add_row(grade, str(count))

    console.print(table)


@app.command()
def parse(
    iml_file: Path = typer.Argument(
        ...,
        help="Path to IML file to parse",
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Output JSON file (prints to console if not specified)",
    ),
) -> None:
    """
    Parse a single IML file and show its contents.

    Useful for debugging and testing the parser.
    """
    if not iml_file.exists():
        console.print(f"[red]Error: File does not exist: {iml_file}[/red]")
        raise typer.Exit(1)

    parser = IMLParser()
    item = parser.parse_file(iml_file)

    if item is None:
        console.print("[red]Error: Failed to parse file[/red]")
        raise typer.Exit(1)

    import json

    json_output = json.dumps(item.model_dump(), ensure_ascii=False, indent=2, default=str)

    if output:
        with open(output, "w", encoding="utf-8") as f:
            f.write(json_output)
        console.print(f"[green]Saved to: {output}[/green]")
    else:
        console.print(json_output)


@app.command()
def stats(
    raw_dir: Path = typer.Option(
        None,
        "--raw-dir",
        "-r",
        help="Raw IML data directory",
    ),
) -> None:
    """
    Show statistics about the raw data directory.

    Scans all IML files and displays distribution by subject and grade.
    """
    settings = get_settings()

    if raw_dir is None:
        raw_dir = settings.raw_data_dir

    raw_dir = raw_dir.resolve()

    if not raw_dir.exists():
        console.print(f"[red]Error: Directory does not exist: {raw_dir}[/red]")
        raise typer.Exit(1)

    console.print(f"[bold]Scanning: {raw_dir}[/bold]")

    sampler = StratifiedSampler(settings)

    # Scan with images
    console.print("\n[bold blue]Items with images:[/bold blue]")
    grouped_with_images = sampler.scan_raw_directory(raw_dir, require_images=True)

    # Create summary tables
    subject_counts: dict[str, int] = {}
    grade_counts: dict[str, int] = {}

    for (subject, grade), items in grouped_with_images.items():
        subject_counts[subject] = subject_counts.get(subject, 0) + len(items)
        grade_counts[grade] = grade_counts.get(grade, 0) + len(items)

    table = Table(title="By Subject (with images)")
    table.add_column("Subject", style="cyan")
    table.add_column("Count", justify="right")

    for subject in settings.TARGET_SUBJECTS:
        count = subject_counts.get(subject, 0)
        table.add_row(subject, str(count))

    console.print(table)

    table = Table(title="By Grade (with images)")
    table.add_column("Grade", style="cyan")
    table.add_column("Count", justify="right")

    for grade in settings.TARGET_GRADES:
        count = grade_counts.get(grade, 0)
        table.add_row(grade, str(count))

    console.print(table)

    # Detailed matrix
    console.print("\n[bold]Distribution Matrix (Subject x Grade)[/bold]")

    matrix_table = Table()
    matrix_table.add_column("Subject")
    for grade in settings.TARGET_GRADES:
        matrix_table.add_column(grade, justify="right")

    for subject in settings.TARGET_SUBJECTS:
        row = [subject]
        for grade in settings.TARGET_GRADES:
            count = len(grouped_with_images.get((subject, grade), []))
            row.append(str(count) if count > 0 else "-")
        matrix_table.add_row(*row)

    console.print(matrix_table)

    total = sum(len(items) for items in grouped_with_images.values())
    console.print(f"\n[bold]Total items with images: {total}[/bold]")


@app.command()
def convert(
    input_file: Path = typer.Argument(
        ...,
        help="Input IML file (EUC-KR encoded)",
    ),
    output_file: Path = typer.Argument(
        ...,
        help="Output IML file (UTF-8 encoded)",
    ),
) -> None:
    """
    Convert an IML file from EUC-KR to UTF-8 encoding.
    """
    if not input_file.exists():
        console.print(f"[red]Error: File does not exist: {input_file}[/red]")
        raise typer.Exit(1)

    from .utils.encoding import convert_file_to_utf8

    convert_file_to_utf8(input_file, output_file)
    console.print(f"[green]Converted: {input_file} -> {output_file}[/green]")


def main() -> None:
    """Entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
