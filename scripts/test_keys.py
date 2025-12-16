#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "readchar",
#     "rich",
# ]
# ///
"""
Simple keyboard test script
"""
import readchar
from rich.console import Console
from rich.live import Live
from rich.panel import Panel

console = Console()

def main():
    console.print("[bold green]Press keys to test. Press 'q' to quit.[/bold green]\n")

    while True:
        key = readchar.readkey()

        if key == 'q':
            console.print("\n[bold red]Quitting...[/bold red]")
            break
        elif key == 'w':
            console.print("⬆️  [cyan]Forward[/cyan]")
        elif key == 's':
            console.print("⬇️  [yellow]Backward[/yellow]")
        elif key == 'a':
            console.print("⬅️  [magenta]Left[/magenta]")
        elif key == 'd':
            console.print("➡️  [blue]Right[/blue]")
        else:
            console.print(f"Key pressed: {repr(key)}")

if __name__ == "__main__":
    main()
