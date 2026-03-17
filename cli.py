#!/usr/bin/env python3
"""
CLI for Generative AI Traffic Scenario Generator

Usage:
    python cli.py generate --count 10
    python cli.py generate --template highway_cruise --weather rainy
    python cli.py edge-cases
    python cli.py from-prompt "rainy night with pedestrian crossing"
"""

import typer
from pathlib import Path
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from scenario_generator import (
    WeatherType, TimeOfDay, TrafficDensity, EdgeCaseType
)
from ai_generator import AIScenarioGenerator, SCENARIO_TEMPLATES, generate_llm_scenario_description

app = typer.Typer(help="🚗 Generative AI Traffic Scenario Generator")
console = Console()


@app.command()
def generate(
    count: int = typer.Option(1, "--count", "-n", help="Number of scenarios to generate"),
    template: Optional[str] = typer.Option(None, "--template", "-t", help="Scenario template name"),
    weather: Optional[str] = typer.Option(None, "--weather", "-w", help="Weather condition"),
    time: Optional[str] = typer.Option(None, "--time", help="Time of day"),
    edge_case: Optional[str] = typer.Option(None, "--edge-case", "-e", help="Edge case type"),
    output_dir: str = typer.Option("scenarios", "--output", "-o", help="Output directory"),
    all_weather: bool = typer.Option(False, "--all-weather", help="Cover all weather types"),
    all_times: bool = typer.Option(False, "--all-times", help="Cover all times of day"),
    all_edges: bool = typer.Option(False, "--all-edges", help="Cover all edge cases"),
):
    """Generate OpenSCENARIO files for ADAS testing."""
    
    console.print(Panel.fit(
        "[bold blue]🚗 Generative AI Traffic Scenario Generator[/bold blue]\n"
        f"Generating {count} scenario(s)...",
        border_style="blue"
    ))
    
    generator = AIScenarioGenerator(output_dir=output_dir)
    
    # Parse optional overrides
    weather_enum = None
    if weather:
        try:
            weather_enum = WeatherType(weather.lower())
        except ValueError:
            console.print(f"[red]Invalid weather: {weather}[/red]")
            raise typer.Exit(1)
            
    time_enum = None
    if time:
        try:
            time_enum = TimeOfDay(time.lower())
        except ValueError:
            console.print(f"[red]Invalid time: {time}[/red]")
            raise typer.Exit(1)
            
    edge_enum = None
    if edge_case:
        try:
            edge_enum = EdgeCaseType(edge_case.lower())
        except ValueError:
            console.print(f"[red]Invalid edge case: {edge_case}[/red]")
            raise typer.Exit(1)
    
    # Generate scenarios
    if count == 1 and not (all_weather or all_times or all_edges):
        # Single scenario
        path = generator.generate_scenario(
            template_name=template,
            weather=weather_enum,
            time_of_day=time_enum,
            edge_case=edge_enum,
        )
        console.print(f"\n[green]✅ Generated:[/green] {path}")
    else:
        # Batch generation
        paths = generator.generate_batch(
            count=count,
            template_name=template,
            include_all_weather=all_weather,
            include_all_times=all_times,
            include_all_edge_cases=all_edges,
        )
        
        console.print(f"\n[green]✅ Generated {len(paths)} scenarios[/green]")
        for p in paths:
            console.print(f"  📄 {p}")


@app.command()
def edge_cases(
    output_dir: str = typer.Option("scenarios", "--output", "-o", help="Output directory"),
):
    """Generate comprehensive edge case test suite."""
    
    console.print(Panel.fit(
        "[bold yellow]⚠️  Edge Case Suite Generator[/bold yellow]\n"
        "Generating scenarios for all edge cases...",
        border_style="yellow"
    ))
    
    generator = AIScenarioGenerator(output_dir=output_dir)
    paths = generator.generate_edge_case_suite()
    
    console.print(f"\n[green]✅ Generated {len(paths)} edge case scenarios[/green]")


@app.command()
def from_prompt(
    prompt: str = typer.Argument(..., help="Natural language scenario description"),
    output_dir: str = typer.Option("scenarios", "--output", "-o", help="Output directory"),
):
    """Generate scenario from natural language description."""
    
    console.print(Panel.fit(
        "[bold magenta]🤖 AI-Powered Scenario Generation[/bold magenta]\n"
        f'Prompt: "{prompt}"',
        border_style="magenta"
    ))
    
    # Parse prompt to parameters
    params = generate_llm_scenario_description(prompt)
    
    console.print("\n[cyan]Extracted parameters:[/cyan]")
    for k, v in params.items():
        val = v.value if hasattr(v, 'value') else v
        console.print(f"  {k}: {val}")
    
    # Generate scenario
    generator = AIScenarioGenerator(output_dir=output_dir)
    path = generator.generate_scenario(
        weather=params.get("weather"),
        time_of_day=params.get("time_of_day"),
        edge_case=params.get("edge_case"),
        custom_name="prompt_generated",
    )
    
    console.print(f"\n[green]✅ Generated:[/green] {path}")


@app.command()
def templates():
    """List available scenario templates."""
    
    table = Table(title="📋 Available Scenario Templates")
    table.add_column("Template", style="cyan")
    table.add_column("Description", style="white")
    table.add_column("Road", style="green")
    table.add_column("Speed Range", style="yellow")
    
    for name, template in SCENARIO_TEMPLATES.items():
        speed_range = f"{template['ego_speed_range'][0]}-{template['ego_speed_range'][1]} km/h"
        table.add_row(
            name,
            template["description"],
            template["road_network"],
            speed_range
        )
    
    console.print(table)


@app.command()
def options():
    """List all available options for generation."""
    
    console.print("\n[bold]🌤️  Weather Types:[/bold]")
    for w in WeatherType:
        console.print(f"  • {w.value}")
        
    console.print("\n[bold]🕐 Times of Day:[/bold]")
    for t in TimeOfDay:
        console.print(f"  • {t.value}")
        
    console.print("\n[bold]🚗 Traffic Densities:[/bold]")
    for d in TrafficDensity:
        console.print(f"  • {d.value}")
        
    console.print("\n[bold]⚠️  Edge Cases:[/bold]")
    for e in EdgeCaseType:
        console.print(f"  • {e.value}")


@app.command()
def validate(
    file_path: str = typer.Argument(..., help="Path to .xosc file to validate"),
):
    """Validate an OpenSCENARIO file."""
    from lxml import etree
    
    path = Path(file_path)
    if not path.exists():
        console.print(f"[red]File not found: {file_path}[/red]")
        raise typer.Exit(1)
        
    try:
        tree = etree.parse(str(path))
        root = tree.getroot()
        
        # Basic validation
        checks = []
        
        # Check root element
        if "OpenSCENARIO" in root.tag:
            checks.append(("Root element", "✅"))
        else:
            checks.append(("Root element", "❌"))
            
        # Check FileHeader
        header = root.find(".//{*}FileHeader")
        checks.append(("FileHeader", "✅" if header is not None else "❌"))
        
        # Check Entities
        entities = root.find(".//{*}Entities")
        if entities is not None:
            entity_count = len(entities.findall(".//{*}ScenarioObject"))
            checks.append(("Entities", f"✅ ({entity_count} objects)"))
        else:
            checks.append(("Entities", "❌"))
            
        # Check Storyboard
        storyboard = root.find(".//{*}Storyboard")
        checks.append(("Storyboard", "✅" if storyboard is not None else "❌"))
        
        # Check RoadNetwork
        road_network = root.find(".//{*}RoadNetwork")
        checks.append(("RoadNetwork", "✅" if road_network is not None else "❌"))
        
        # Display results
        table = Table(title=f"📋 Validation: {path.name}")
        table.add_column("Check", style="cyan")
        table.add_column("Status", style="white")
        
        for check, status in checks:
            table.add_row(check, status)
            
        console.print(table)
        
        all_passed = all("✅" in str(s) for _, s in checks)
        if all_passed:
            console.print("\n[green]✅ File is valid OpenSCENARIO[/green]")
        else:
            console.print("\n[yellow]⚠️  Some checks failed[/yellow]")
            
    except etree.XMLSyntaxError as e:
        console.print(f"[red]❌ XML Syntax Error: {e}[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
