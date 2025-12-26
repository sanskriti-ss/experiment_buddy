"""
CLI tool for extracting and analyzing experimental procedures from papers.

Usage:
    python -m planlint.cli extract-paper <url> [--output FILE] [--model MODEL]
    python -m planlint.cli analyze-procedure <json-file>
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Optional, Dict, Any
import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from planlint.paper_fetcher import PaperFetcher, PaperContent
from planlint.llm_extractor import LLMExtractor
from planlint.procedure_validator import ProcedureValidator
from planlint.action_requirements import ActionRequirements


console = Console()


@click.group()
def cli():
    """Plan-linter: Extract and analyze experimental procedures."""
    pass


@cli.command("extract-paper")
@click.argument("url")
@click.option("--output", "-o", type=click.Path(), help="Output JSON file path")
@click.option("--model", "-m", default="openai/gpt-4o-mini", help="LLM model to use")
@click.option("--report", "-r", type=click.Path(), help="Generate analysis report")
def extract_paper(url: str, output: Optional[str], model: str, report: Optional[str]):
    """
    Extract and analyze procedure from a scientific paper.
    
    URL can be a DOI, PubMed ID, arXiv ID, or direct paper URL.
    
    Examples:
        planlint extract-paper 10.1038/s41586-020-2649-2
        planlint extract-paper https://pubmed.ncbi.nlm.nih.gov/33293615/
        planlint extract-paper arxiv:2012.12345 --output procedure.json
    """
    asyncio.run(_extract_paper_async(url, output, model, report))


async def _extract_paper_async(
    url: str,
    output: Optional[str],
    model: str,
    report: Optional[str]
):
    """Async implementation of extract-paper command."""
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        
        # Step 1: Fetch paper
        task1 = progress.add_task("Fetching paper and extracting Methods section...", total=None)
        
        try:
            fetcher = PaperFetcher(model=model)
            paper = await fetcher.fetch_paper_async(url)
        except Exception as e:
            console.print(f"[bold red]Error fetching paper:[/bold red] {e}")
            sys.exit(1)
        
        progress.update(task1, completed=True)
        
        console.print(f"\n[green]✓[/green] Found Methods section: {paper.section_name}")
        console.print(f"  Length: {len(paper.methods_text)} characters")
        if paper.citation:
            console.print(f"  Citation: {paper.citation}")
        
        # Step 2: Extract procedure IR
        task2 = progress.add_task("Extracting structured procedure...", total=None)
        
        try:
            extractor = LLMExtractor(model=model)
            procedure_ir = await extractor.extract_procedure_async(
                methods_text=paper.methods_text,
                source_type="methods_section",
                citation=paper.citation,
                url=paper.url,
                section_name=paper.section_name
            )
        except Exception as e:
            console.print(f"\n[bold red]Error extracting procedure:[/bold red] {e}")
            sys.exit(1)
        
        progress.update(task2, completed=True)
        
        console.print(f"[green]✓[/green] Extracted {len(procedure_ir['steps'])} steps")
        
        # Step 3: Validate
        task3 = progress.add_task("Validating against schema...", total=None)
        
        validator = ProcedureValidator()
        errors = validator.validate(procedure_ir)
        
        progress.update(task3, completed=True)
        
        if errors:
            console.print(f"\n[yellow]⚠[/yellow] Validation warnings:")
            for error in errors:
                console.print(f"  • {error}")
        else:
            console.print("[green]✓[/green] Valid procedure IR")
        
        # Step 4: Analyze missing parameters
        task4 = progress.add_task("Analyzing completeness...", total=None)
        analysis = _analyze_procedure(procedure_ir)
        progress.update(task4, completed=True)
    
    # Display results
    _display_analysis(analysis)
    
    # Save outputs
    if output:
        output_path = Path(output)
        with open(output_path, 'w') as f:
            json.dump(procedure_ir, f, indent=2)
        console.print(f"\n[green]✓[/green] Saved procedure IR to: {output_path}")
    
    if report:
        report_path = Path(report)
        with open(report_path, 'w') as f:
            json.dump(analysis, f, indent=2)
        console.print(f"[green]✓[/green] Saved analysis report to: {report_path}")


@cli.command("extract-text")
@click.argument("text_file", type=click.Path(exists=True))
@click.option("--output", "-o", type=click.Path(), help="Output JSON file path")
@click.option("--model", "-m", default="openai/gpt-4o-mini", help="LLM model to use")
@click.option("--report", "-r", type=click.Path(), help="Generate analysis report")
@click.option("--citation", "-c", help="Optional citation or DOI")
def extract_text(text_file: str, output: Optional[str], model: str, report: Optional[str], citation: Optional[str]):
    """
    Extract and analyze procedure from a text file containing Methods section.
    
    This is useful when you've manually copied the Methods section from a paper.
    
    Examples:
        planlint extract-text methods.txt --output procedure.json
        planlint extract-text methods.txt --citation "Smith et al. 2023"
    """
    asyncio.run(_extract_text_async(text_file, output, model, report, citation))


async def _extract_text_async(
    text_file: str,
    output: Optional[str],
    model: str,
    report: Optional[str],
    citation: Optional[str]
):
    """Async implementation of extract-text command."""
    
    # Read the text file
    with open(text_file, 'r') as f:
        methods_text = f.read()
    
    if len(methods_text) < 50:
        console.print(f"[bold red]Error:[/bold red] Text file seems too short ({len(methods_text)} chars)")
        sys.exit(1)
    
    console.print(f"[green]✓[/green] Loaded Methods text: {len(methods_text)} characters")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        
        # Extract procedure IR
        task = progress.add_task("Extracting structured procedure...", total=None)
        
        try:
            extractor = LLMExtractor(model=model)
            procedure_ir = await extractor.extract_procedure_async(
                methods_text=methods_text,
                source_type="paper_procedure_paste",
                citation=citation
            )
        except Exception as e:
            console.print(f"\n[bold red]Error extracting procedure:[/bold red] {e}")
            sys.exit(1)
        
        progress.update(task, completed=True)
        
        console.print(f"[green]✓[/green] Extracted {len(procedure_ir['steps'])} steps")
        
        # Validate
        task2 = progress.add_task("Validating against schema...", total=None)
        
        validator = ProcedureValidator()
        errors = validator.validate(procedure_ir)
        
        progress.update(task2, completed=True)
        
        if errors:
            console.print(f"\n[yellow]⚠[/yellow] Validation warnings:")
            for error in errors:
                console.print(f"  • {error}")
        else:
            console.print("[green]✓[/green] Valid procedure IR")
        
        # Analyze
        task3 = progress.add_task("Analyzing completeness...", total=None)
        analysis = _analyze_procedure(procedure_ir)
        progress.update(task3, completed=True)
    
    # Display results
    _display_analysis(analysis)
    
    # Save outputs
    if output:
        output_path = Path(output)
        with open(output_path, 'w') as f:
            json.dump(procedure_ir, f, indent=2)
        console.print(f"\n[green]✓[/green] Saved procedure IR to: {output_path}")
    
    if report:
        report_path = Path(report)
        with open(report_path, 'w') as f:
            json.dump(analysis, f, indent=2)
        console.print(f"[green]✓[/green] Saved analysis report to: {report_path}")


@cli.command("analyze-procedure")
@click.argument("json_file", type=click.Path(exists=True))
@click.option("--report", "-r", type=click.Path(), help="Save analysis report")
def analyze_procedure(json_file: str, report: Optional[str]):
    """
    Analyze a procedure IR JSON file for missing parameters.
    
    Examples:
        planlint analyze-procedure examples/procedure_ir_from_paper.json
        planlint analyze-procedure procedure.json --report analysis.json
    """
    
    # Load procedure
    with open(json_file) as f:
        procedure_ir = json.load(f)
    
    # Validate
    console.print("[bold]Validating procedure...[/bold]")
    validator = ProcedureValidator()
    errors = validator.validate(procedure_ir)
    
    if errors:
        console.print("[yellow]⚠ Validation errors:[/yellow]")
        for error in errors:
            console.print(f"  • {error}")
        console.print()
    
    # Analyze
    console.print("[bold]Analyzing completeness...[/bold]\n")
    analysis = _analyze_procedure(procedure_ir)
    
    # Display
    _display_analysis(analysis)
    
    # Save report
    if report:
        with open(report, 'w') as f:
            json.dump(analysis, f, indent=2)
        console.print(f"\n[green]✓[/green] Saved analysis report to: {report}")


def _analyze_procedure(procedure_ir: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze a procedure for completeness and missing parameters."""
    
    steps = procedure_ir.get("steps", [])
    
    step_analyses = []
    total_missing = 0
    total_complete = 0
    
    for step in steps:
        step_id = step.get("id", "unknown")
        action = step.get("action", "other")
        raw_text = step.get("raw_text", "")
        parameters = step.get("parameters", [])
        
        # Extract parameter names
        param_names = [p["name"] for p in parameters if "name" in p]
        
        # Check for missing required parameters
        missing = ActionRequirements.check_missing_params(action, param_names)
        completeness = ActionRequirements.get_completeness_score(action, param_names)
        
        step_analysis = {
            "step_id": step_id,
            "action": action,
            "raw_text": raw_text[:100] + "..." if len(raw_text) > 100 else raw_text,
            "parameters_found": param_names,
            "missing_required": missing,
            "completeness_score": round(completeness, 2),
            "is_complete": len(missing) == 0
        }
        
        step_analyses.append(step_analysis)
        total_missing += len(missing)
        if len(missing) == 0:
            total_complete += 1
    
    overall_completeness = total_complete / len(steps) if steps else 0
    
    return {
        "summary": {
            "total_steps": len(steps),
            "complete_steps": total_complete,
            "incomplete_steps": len(steps) - total_complete,
            "total_missing_params": total_missing,
            "overall_completeness": round(overall_completeness, 2)
        },
        "steps": step_analyses,
        "source": procedure_ir.get("source", {})
    }


def _display_analysis(analysis: Dict[str, Any]):
    """Display analysis results with rich formatting."""
    
    summary = analysis["summary"]
    steps = analysis["steps"]
    
    # Summary panel
    summary_text = f"""
    [bold]Total Steps:[/bold] {summary['total_steps']}
    [bold green]Complete:[/bold green] {summary['complete_steps']}
    [bold yellow]Incomplete:[/bold yellow] {summary['incomplete_steps']}
    [bold red]Missing Parameters:[/bold red] {summary['total_missing_params']}
    [bold]Completeness:[/bold] {summary['overall_completeness'] * 100:.0f}%
    """
    
    console.print(Panel(summary_text, title="[bold]Procedure Analysis Summary[/bold]", border_style="blue"))
    
    # Detailed table
    console.print("\n[bold]Step-by-Step Analysis:[/bold]\n")
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Step", style="cyan", width=12)
    table.add_column("Action", style="blue", width=15)
    table.add_column("Score", justify="center", width=8)
    table.add_column("Missing Parameters", style="yellow")
    
    for step in steps:
        step_id = step["step_id"]
        action = step["action"]
        score = f"{step['completeness_score'] * 100:.0f}%"
        missing = ", ".join(step["missing_required"]) if step["missing_required"] else "[green]✓ Complete[/green]"
        
        # Color code the score
        score_colored = score
        if step["completeness_score"] >= 1.0:
            score_colored = f"[green]{score}[/green]"
        elif step["completeness_score"] >= 0.5:
            score_colored = f"[yellow]{score}[/yellow]"
        else:
            score_colored = f"[red]{score}[/red]"
        
        table.add_row(step_id, action, score_colored, missing)
    
    console.print(table)
    
    # Highlight most problematic steps
    incomplete_steps = [s for s in steps if not s["is_complete"]]
    if incomplete_steps:
        console.print("\n[bold yellow]⚠ Steps Needing Attention:[/bold yellow]\n")
        
        # Sort by number of missing params (most first)
        incomplete_steps.sort(key=lambda s: len(s["missing_required"]), reverse=True)
        
        for step in incomplete_steps[:5]:  # Show top 5
            missing_list = "\n    • ".join(step["missing_required"])
            console.print(f"[cyan]{step['step_id']}[/cyan] ({step['action']})")
            console.print(f"  Text: {step['raw_text']}")
            console.print(f"  Missing:\n    • {missing_list}\n")


if __name__ == "__main__":
    cli()
