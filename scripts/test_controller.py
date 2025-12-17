#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "pygame",
#     "rich",
# ]
# ///
"""
DualSense Controller Diagnostic Tool
Displays real-time controller input data
"""
import pygame
from rich.console import Console
import time
import sys

console = Console()

def main():
    # Initialize pygame and joystick
    pygame.init()
    pygame.joystick.init()

    # Check for controllers
    joystick_count = pygame.joystick.get_count()
    if joystick_count == 0:
        console.print("[red]No controllers detected![/red]")
        console.print("Make sure your DualSense controller is connected via USB or Bluetooth.")
        sys.exit(1)

    # Get first controller
    joystick = pygame.joystick.Joystick(0)
    joystick.init()

    # Display controller info
    console.print(f"[green]Controller detected:[/green] {joystick.get_name()}")
    console.print(f"Axes: {joystick.get_numaxes()}")
    console.print(f"Buttons: {joystick.get_numbuttons()}")
    console.print(f"Hats (D-pad): {joystick.get_numhats()}\n")
    console.print("[yellow]Move the left stick and press buttons to see values[/yellow]")
    console.print("[yellow]Press Ctrl+C to exit[/yellow]\n")

    # Main loop: display live data
    from rich.live import Live
    from rich.table import Table

    try:
        with Live(console=console, refresh_per_second=20) as live:
            while True:
                pygame.event.pump()  # Process events

                # Read all axes (analog sticks, triggers)
                axes = [joystick.get_axis(i) for i in range(joystick.get_numaxes())]

                # Read all buttons
                buttons = [joystick.get_button(i) for i in range(joystick.get_numbuttons())]

                # Read D-pad (hat)
                hats = [joystick.get_hat(i) for i in range(joystick.get_numhats())]

                # Create table for display
                table = Table(show_header=False, box=None)
                table.add_column("Label", style="cyan")
                table.add_column("Value")

                # L3 stick (main control)
                table.add_row("L3 X (left/right)", f"[yellow]{axes[0]:+.2f}[/yellow]" if len(axes) > 0 else "N/A")
                table.add_row("L3 Y (up/down)", f"[yellow]{axes[1]:+.2f}[/yellow]" if len(axes) > 1 else "N/A")

                # R1/R2 for speed control
                r1_button = joystick.get_button(10) if joystick.get_numbuttons() > 10 else 0
                r2_trigger = axes[5] if len(axes) > 5 else 0.0
                table.add_row("R1 (button)", f"[cyan]{'PRESSED' if r1_button else 'released'}[/cyan]")
                table.add_row("R2 (trigger)", f"[magenta]{r2_trigger:+.2f}[/magenta]")

                # Other axes
                if len(axes) > 6:
                    table.add_row("Other axes", str([f"{a:+.2f}" for a in axes[6:]]))

                # Buttons pressed
                buttons_pressed = [i for i, b in enumerate(buttons) if b == 1]
                if buttons_pressed:
                    table.add_row("Buttons pressed", f"[magenta]{buttons_pressed}[/magenta]")
                else:
                    table.add_row("Buttons pressed", "[dim]none[/dim]")

                # D-pad
                if hats:
                    table.add_row("D-pad (hat)", f"[green]{hats[0]}[/green]")

                live.update(table)
                time.sleep(0.05)  # 20Hz

    except KeyboardInterrupt:
        console.print("\n[green]Exiting...[/green]")
    finally:
        pygame.quit()

if __name__ == "__main__":
    main()
