"""Command-line interface for Bookkeeper."""

from datetime import date, datetime
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table

from .backup import create_backup
from .classifier import TransactionClassifier
from .reader import QuickenReader
from .writer import QuickenWriter

app = typer.Typer(help="AI-powered financial data cleanup for better reporting")
console = Console()


@app.command()
def main(
    quicken_file: Path = typer.Argument(..., help="Path to .quicken file"),
    start_date: Optional[str] = typer.Option(None, help="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = typer.Option(None, help="End date (YYYY-MM-DD)"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview changes without applying"),
    api_key: Optional[str] = typer.Option(None, "--api-key", envvar="ANTHROPIC_API_KEY", help="Anthropic API key"),
):
    """
    Clean and categorize transactions in a Quicken file.

    Examples:
        # Dry run for transactions since Jan 1, 2024
        bookkeeper myfile.quicken --start-date 2024-01-01 --dry-run

        # Apply changes for a specific date range
        bookkeeper myfile.quicken --start-date 2024-01-01 --end-date 2024-12-31
    """
    console.print(f"[bold blue]Bookkeeper v{__import__('bookkeeper').__version__}[/bold blue]")
    console.print()

    # Validate inputs
    if not quicken_file.exists():
        console.print(f"[red]Error: File not found: {quicken_file}[/red]")
        raise typer.Exit(1)

    if not quicken_file.suffix == ".quicken":
        console.print(f"[yellow]Warning: Expected .quicken file, got {quicken_file.suffix}[/yellow]")

    # Display configuration
    console.print(f"[green]File:[/green] {quicken_file}")
    console.print(f"[green]Date range:[/green] {start_date or 'all'} to {end_date or 'now'}")
    console.print(f"[green]Mode:[/green] {'DRY RUN' if dry_run else 'UPDATE'}")
    console.print()

    # Parse dates
    parsed_start = datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else None
    parsed_end = datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else None

    # Create backup before making any changes (even in dry-run for safety)
    if not dry_run:
        console.print("[cyan]Creating backup...[/cyan]")
        backup_path = create_backup(quicken_file)
        console.print(f"[green]Backup created:[/green] {backup_path}")
        console.print()

    # Read transactions
    console.print("[cyan]Reading transactions...[/cyan]")
    reader = QuickenReader(quicken_file)
    transactions = reader.read_transactions(start_date=parsed_start, end_date=parsed_end)
    categories = reader.get_all_categories()

    console.print(f"[green]Found {len(transactions)} transactions[/green]")
    console.print(f"[green]Available categories: {len(categories)}[/green]")
    console.print()

    # Find uncategorized transactions (None, empty string, or "Uncategorized" category)
    uncategorized = [
        t for t in transactions
        if not t.category or t.category == "Uncategorized"
    ]

    if not uncategorized:
        console.print("[green]All transactions are already categorized![/green]")
        return

    console.print(f"[yellow]Found {len(uncategorized)} uncategorized transactions[/yellow]")
    console.print()

    # Initialize classifier
    classifier = TransactionClassifier(api_key=api_key)

    # Classify and build suggestions with progress bar
    suggestions = {}
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console
    ) as progress:
        task = progress.add_task(
            "[cyan]Classifying transactions...",
            total=len(uncategorized)
        )

        for txn in uncategorized:
            suggested_category, confidence = classifier.classify(txn, categories)
            if confidence > 0.5:  # Only suggest if confidence is reasonable
                suggestions[txn.id] = (txn, suggested_category, confidence)
            progress.advance(task)

    console.print()

    if not suggestions:
        console.print("[yellow]No high-confidence suggestions available[/yellow]")
        console.print("[dim]Tip: Provide an API key to enable LLM classification[/dim]")
        return

    # Display suggestions in a table
    table = Table(title=f"Suggested Categorizations ({len(suggestions)} transactions)")
    table.add_column("Date", style="cyan")
    table.add_column("Payee", style="yellow")
    table.add_column("Amount", style="magenta", justify="right")
    table.add_column("Suggested Category", style="green")
    table.add_column("Confidence", justify="right")

    for txn, category, confidence in suggestions.values():
        table.add_row(
            str(txn.date),
            txn.payee[:40],  # Truncate long payees
            f"${txn.amount:.2f}",
            category,
            f"{confidence:.0%}"
        )

    console.print(table)
    console.print()

    # Apply changes if not dry-run
    if dry_run:
        console.print("[bold yellow]DRY RUN - No changes applied[/bold yellow]")
    else:
        console.print("[cyan]Applying categorizations...[/cyan]")

        # Prepare updates dict
        updates = {txn.id: category for txn, category, _ in suggestions.values()}

        # Get database path and create writer
        db_path = quicken_file / "data"
        writer = QuickenWriter(db_path)

        # Apply updates
        results = writer.update_categories(updates)

        # Report results
        successes = sum(1 for success in results.values() if success)
        failures = len(results) - successes

        console.print(f"[green]Successfully updated {successes} transactions[/green]")
        if failures > 0:
            console.print(f"[red]Failed to update {failures} transactions[/red]")

        console.print()
        console.print("[bold green]Done![/bold green]")


if __name__ == "__main__":
    app()
