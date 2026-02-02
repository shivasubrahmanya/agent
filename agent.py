"""
B2B Lead Discovery Agent - Terminal CLI
A full terminal-based agent with Apollo.io integration
"""

import os
import sys
import json
from datetime import datetime

# Rich terminal UI
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.table import Table
    from rich.markdown import Markdown
    from rich import print as rprint
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    print("Note: Install 'rich' for better UI: pip install rich")

from workflow import run_pipeline, enrich_person_direct, WorkflowProgress, parse_input
import database as db


# Console for rich output
console = Console() if RICH_AVAILABLE else None


def print_banner():
    """Print the agent banner."""
    banner = """
╔══════════════════════════════════════════════════════════════╗
║           🎯 B2B Lead Discovery Agent                        ║
║           Powered by Groq + Apollo.io                        ║
╚══════════════════════════════════════════════════════════════╝
"""
    if RICH_AVAILABLE:
        console.print(Panel.fit(
            "[bold cyan]🎯 B2B Lead Discovery Agent[/bold cyan]\n"
            "[dim]Powered by Groq + Apollo.io[/dim]",
            border_style="cyan"
        ))
    else:
        print(banner)


def print_help():
    """Print available commands."""
    help_text = """
[bold]Available Commands:[/bold]

  [cyan]analyze[/cyan] <company>, Roles: <role1>, <role2>
      Run full lead discovery pipeline
      Example: analyze Microsoft, Roles: CEO, VP Sales

  [cyan]enrich[/cyan] <name> at <company>
      Direct person enrichment via Apollo.io
      Example: enrich Satya Nadella at Microsoft

  [cyan]history[/cyan]
      View all analyzed leads

  [cyan]export[/cyan]
      Export leads to CSV file

  [cyan]clear[/cyan]
      Clear the screen

  [cyan]help[/cyan]
      Show this help message

  [cyan]quit[/cyan] or [cyan]exit[/cyan]
      Exit the agent
"""
    if RICH_AVAILABLE:
        console.print(Markdown(help_text.replace("[bold]", "**").replace("[/bold]", "**")
                               .replace("[cyan]", "`").replace("[/cyan]", "`")))
    else:
        print(help_text.replace("[bold]", "").replace("[/bold]", "")
              .replace("[cyan]", "").replace("[/cyan]", ""))


def progress_callback(stage: str, status: str, data: dict = None):
    """Progress callback for workflow."""
    stages_emoji = {
        "discovery": "🔍",
        "structure": "🏢",
        "roles": "👤",
        "enrichment": "📧",
        "verification": "✅"
    }
    emoji = stages_emoji.get(stage, "•")
    
    if RICH_AVAILABLE:
        if status == "running":
            console.print(f"  {emoji} [yellow]Running {stage}...[/yellow]")
        else:
            console.print(f"  {emoji} [green]{stage.title()} completed[/green]")
    else:
        if status == "running":
            print(f"  {emoji} Running {stage}...")
        else:
            print(f"  {emoji} {stage.title()} completed")


def display_lead_result(lead_data: dict):
    """Display lead analysis result."""
    if RICH_AVAILABLE:
        # Status header
        status = lead_data.get("status", "unknown")
        score = lead_data.get("confidence_score", 0)
        
        if status == "verified":
            status_color = "green"
            status_emoji = "✅"
        else:
            status_color = "red"
            status_emoji = "❌"
        
        console.print(f"\n{status_emoji} [bold {status_color}]Lead {status.upper()}[/bold {status_color}] "
                     f"(Confidence: {score:.0%})")
        
        # Company info
        company = lead_data.get("company", {})
        console.print(f"\n[bold]Company:[/bold] {company.get('name', 'Unknown')}")
        console.print(f"  Industry: {company.get('industry', 'N/A')}")
        console.print(f"  Size: {company.get('size', 'N/A')}")
        if company.get("location"):
            console.print(f"  Location: {company.get('location')}")
        if company.get("website"):
            console.print(f"  Website: {company.get('website')}")
        
        # Growth signals (from web search)
        growth = company.get("growth_signals", [])
        if growth:
            console.print(f"  [green]Growth Signals: {', '.join(growth)}[/green]")
        
        # Data sources used
        if company.get("_web_search_used"):
            sources = company.get("_sources", [])
            console.print(f"  [dim]Sources: {', '.join(sources) if sources else 'web search'}[/dim]")
        
        # People found (from LinkedIn search)
        people = lead_data.get("people", [])
        if people:
            accepted = [p for p in people if p.get("status") == "accepted"]
            rejected = [p for p in people if p.get("status") == "rejected"]
            
            console.print(f"\n[bold]Decision Makers Found ({len(accepted)} accepted):[/bold]")
            for person in people[:10]:  # Limit display
                status = "✓" if person.get("status") == "accepted" else "✗"
                power = person.get("decision_power", 0)
                name = person.get("name", "Unknown")
                title = person.get("title", "Unknown")
                source = person.get("source", "")
                
                # Color based on source
                if source == "linkedin":
                    source_tag = "[blue](LinkedIn)[/blue]"
                elif source == "suggested":
                    source_tag = "[dim](suggested role)[/dim]"
                else:
                    source_tag = ""
                
                console.print(f"  {status} [bold]{name}[/bold] - {title} (Power: {power}/10) {source_tag}")
                
                if person.get("linkedin_url") and source == "linkedin":
                    console.print(f"      🔗 {person.get('linkedin_url')}")
        
        # Fallback to roles (old format)
        elif lead_data.get("roles"):
            roles = lead_data.get("roles", [])
            console.print(f"\n[bold]Roles ({len(roles)}):[/bold]")
            for role in roles:
                status = "✓" if role.get("status") == "accepted" else "✗"
                power = role.get("decision_power", 0)
                console.print(f"  {status} {role.get('title', 'Unknown')} (Power: {power}/10)")
        
        # Contacts (from Apollo)
        contacts = lead_data.get("contacts", [])
        if contacts:
            console.print(f"\n[bold]Verified Contacts ({len(contacts)}):[/bold]")
            for contact in contacts:
                name = f"{contact.get('first_name', '')} {contact.get('last_name', '')}".strip()
                console.print(f"  👤 {name}")
                if contact.get("title"):
                    console.print(f"     💼 {contact.get('title')}")
                if contact.get("email"):
                    console.print(f"     📧 {contact.get('email')}")
                if contact.get("phone"):
                    console.print(f"     📱 {contact.get('phone')}")
                if contact.get("linkedin_url"):
                    console.print(f"     🔗 {contact.get('linkedin_url')}")
        
        # Summary
        if lead_data.get("summary"):
            console.print(f"\n[dim]{lead_data.get('summary')}[/dim]")
        
        if lead_data.get("recommended_action"):
            console.print(f"[bold]→ {lead_data.get('recommended_action')}[/bold]")
    else:
        # Plain text output
        print("\n" + "=" * 50)
        print(json.dumps(lead_data, indent=2))
        print("=" * 50)


def display_history():
    """Display lead history."""
    leads = db.list_leads()
    
    if not leads:
        print("\n📭 No leads in history yet.\n")
        return
    
    if RICH_AVAILABLE:
        table = Table(title="Lead History")
        table.add_column("ID", style="cyan")
        table.add_column("Company", style="white")
        table.add_column("Status", style="white")
        table.add_column("Score", style="white")
        table.add_column("Contacts", style="white")
        table.add_column("Date", style="dim")
        
        for lead in leads:
            company = lead.get("company", {}).get("name", "Unknown")
            status = lead.get("status", "unknown")
            score = f"{lead.get('confidence_score', 0):.0%}"
            contacts = str(len(lead.get("contacts", [])))
            date = lead.get("created_at", "")[:10]
            
            status_style = "green" if status == "verified" else "red"
            table.add_row(
                lead.get("id", "")[:8],
                company,
                f"[{status_style}]{status}[/{status_style}]",
                score,
                contacts,
                date
            )
        
        console.print(table)
    else:
        print("\n📋 Lead History:")
        for lead in leads:
            company = lead.get("company", {}).get("name", "Unknown")
            status = lead.get("status", "unknown")
            score = lead.get("confidence_score", 0)
            print(f"  • {lead.get('id', '')[:8]} | {company} | {status} | {score:.0%}")
        print()


def handle_analyze(args: str):
    """Handle analyze command."""
    if not args:
        print("\n⚠️  Usage: analyze <company>, Roles: <role1>, <role2>")
        print("   Example: analyze Microsoft, Roles: CEO, VP Sales\n")
        return
    
    company, roles = parse_input(args)
    
    if not company:
        print("\n⚠️  Please provide a company name.\n")
        return
    
    print(f"\n🚀 Starting lead discovery for: {company}")
    if roles:
        print(f"   Roles to evaluate: {', '.join(roles)}")
    print()
    
    progress = WorkflowProgress(progress_callback)
    result = run_pipeline(args, progress)
    
    display_lead_result(result)
    print()


def handle_enrich(args: str):
    """Handle enrich command."""
    if " at " not in args.lower():
        print("\n⚠️  Usage: enrich <name> at <company>")
        print("   Example: enrich Satya Nadella at Microsoft\n")
        return
    
    # Parse "Name at Company"
    parts = args.lower().split(" at ")
    name = args[:args.lower().find(" at ")].strip()
    company = args[args.lower().find(" at ") + 4:].strip()
    
    print(f"\n🔍 Enriching: {name} at {company}\n")
    
    progress = WorkflowProgress(progress_callback)
    result = enrich_person_direct(name, company, progress)
    
    if result.get("error"):
        print(f"\n❌ {result.get('error')}")
        if result.get("note"):
            print(f"   {result.get('note')}")
    else:
        if RICH_AVAILABLE:
            console.print("\n[bold green]✅ Contact Found![/bold green]")
            console.print(f"  👤 {result.get('first_name', '')} {result.get('last_name', '')}")
            console.print(f"  💼 {result.get('title', 'N/A')}")
            console.print(f"  🏢 {result.get('company', 'N/A')}")
            if result.get("email"):
                console.print(f"  📧 {result.get('email')}")
            if result.get("phone"):
                console.print(f"  📱 {result.get('phone')}")
            if result.get("linkedin_url"):
                console.print(f"  🔗 {result.get('linkedin_url')}")
        else:
            print("\n✅ Contact Found!")
            print(json.dumps(result, indent=2))
    
    print()


def handle_export():
    """Handle export command."""
    filepath = db.export_leads_to_csv()
    if filepath == "No leads to export" or filepath == "No data to export":
        print(f"\n📭 {filepath}\n")
    else:
        print(f"\n✅ Exported to: {filepath}\n")


def main():
    """Main agent loop."""
    print_banner()
    print_help()
    
    # Check API configurations
    if not os.getenv("GROQ_API_KEY"):
        print("\n⚠️  Warning: GROQ_API_KEY not set. Add it to .env file.")
    if not os.getenv("APOLLO_API_KEY"):
        print("\n⚠️  Warning: APOLLO_API_KEY not set. Contact enrichment will be limited.")
        print("   Get free API key at: https://www.apollo.io\n")
    
    while True:
        try:
            # Get input
            if RICH_AVAILABLE:
                user_input = console.input("\n[bold cyan]>[/bold cyan] ").strip()
            else:
                user_input = input("\n> ").strip()
            
            if not user_input:
                continue
            
            # Parse command
            cmd_parts = user_input.split(maxsplit=1)
            command = cmd_parts[0].lower()
            args = cmd_parts[1] if len(cmd_parts) > 1 else ""
            
            # Handle commands
            if command in ["quit", "exit", "q"]:
                print("\n👋 Goodbye!\n")
                break
            
            elif command == "help":
                print_help()
            
            elif command == "clear":
                os.system("cls" if os.name == "nt" else "clear")
                print_banner()
            
            elif command == "history":
                display_history()
            
            elif command == "export":
                handle_export()
            
            elif command == "analyze":
                handle_analyze(args)
            
            elif command == "enrich":
                handle_enrich(args)
            
            else:
                # Treat entire input as analyze command
                handle_analyze(user_input)
                
        except KeyboardInterrupt:
            print("\n\n👋 Interrupted. Goodbye!\n")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}\n")


if __name__ == "__main__":
    main()
