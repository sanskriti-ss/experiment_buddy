"""
Command-line interface for the plan validator.

Usage:
    python -m planlint.validate <plan_file.json>
    python -m planlint.validate <plan_file.json> --schema <schema_file.json>
"""

import sys
import argparse
from pathlib import Path

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

from planlint.validator import validate_plan


def print_result_rich(result):
    """Print validation result using rich formatting."""
    console = Console()
    
    if result.is_valid:
        # Success message
        console.print()
        console.print(Panel(
            f"[bold green]✓ Valid![/bold green]\n\n"
            f"Plan conforms to [cyan]{result.schema_version}[/cyan] schema",
            title=f"[bold]{Path(result.plan_path).name}[/bold]",
            border_style="green"
        ))
        console.print()
    else:
        # Error message
        console.print()
        console.print(Panel(
            f"[bold red]✗ Validation Failed[/bold red]\n\n"
            f"Found {len(result.errors)} error(s):",
            title=f"[bold]{Path(result.plan_path).name}[/bold]",
            border_style="red"
        ))
        console.print()
        
        for i, error in enumerate(result.errors, 1):
            # Split error into path and message
            if ": " in error:
                path, message = error.split(": ", 1)
                console.print(f"  [bold red]{i}.[/bold red] [yellow]{path}[/yellow]")
                console.print(f"     {message}")
            else:
                console.print(f"  [bold red]{i}.[/bold red] {error}")
            console.print()


def print_result_plain(result):
    """Print validation result using plain text formatting."""
    if result.is_valid:
        print()
        print(f"✓ Valid! {Path(result.plan_path).name}")
        print(f"  Plan conforms to {result.schema_version} schema")
        print()
    else:
        print()
        print(f"✗ Validation Failed: {Path(result.plan_path).name}")
        print(f"  Found {len(result.errors)} error(s):")
        print()
        
        for i, error in enumerate(result.errors, 1):
            print(f"  {i}. {error}")
        print()


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Validate an experiment plan against the canonical schema",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Validate a plan using the default microscopy schema
  python -m planlint.validate examples/heart_organoid_fluorescence_plan.json
  
  # Validate using a custom schema
  python -m planlint.validate my_plan.json --schema custom_schema.json
  
  # Disable colored output
  python -m planlint.validate my_plan.json --no-color
        """
    )
    
    parser.add_argument(
        "plan_file",
        type=str,
        help="Path to the experiment plan JSON file to validate"
    )
    
    parser.add_argument(
        "--schema",
        type=str,
        default=None,
        help="Path to custom schema file (optional, uses default if not provided)"
    )
    
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable colored output"
    )
    
    args = parser.parse_args()
    
    # Convert to Path objects
    plan_path = Path(args.plan_file)
    schema_path = Path(args.schema) if args.schema else None
    
    # Validate the plan
    result = validate_plan(plan_path, schema_path)
    
    # Print results
    use_rich = RICH_AVAILABLE and not args.no_color and sys.stdout.isatty()
    
    if use_rich:
        print_result_rich(result)
    else:
        print_result_plain(result)
    
    # Exit with appropriate code
    sys.exit(0 if result.is_valid else 1)


if __name__ == "__main__":
    main()
