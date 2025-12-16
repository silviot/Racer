#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "bleak",
#     "pygame",
#     "rich",
# ]
# ///
"""
MicroRacer DualSense Controller Bridge
Control the MicroRacer car with a PlayStation DualSense controller
"""
import asyncio
import os
import json
import sys
from bleak import BleakClient, BleakScanner
import pygame
from rich.console import Console
from rich.live import Live
from rich.table import Table

console = Console()

CONFIG_FILE = "ble_device_config.json"
CHARACTERISTIC_UUID = "23408888-1f40-4cd8-9b89-ca8d45f8a5b0"

# Configuration
DEADZONE = 0.15  # Ignore stick movements below 15%
MAX_SPEED_LEVELS = [50, 75, 100]  # Speed limit modes

async def send_command(client, speedA, directionA, speedB, directionB, duration):
    """Send motor command to car via BLE."""
    command = bytearray([speedA, directionA, speedB, directionB, duration])
    await client.write_gatt_char(CHARACTERISTIC_UUID, command)

async def select_device():
    """Scan for and select a BLE device."""
    devices = await BleakScanner.discover()
    if not devices:
        console.print("[red]No BLE devices found.[/red]")
        return None

    console.print("[bold]Available BLE devices:[/bold]")
    for i, device in enumerate(devices):
        console.print(f"{i}: {device.name} - {device.address}")

    while True:
        try:
            selection = int(input("Select device by number: "))
            if 0 <= selection < len(devices):
                return devices[selection].address
            else:
                console.print("[yellow]Invalid selection. Please try again.[/yellow]")
        except ValueError:
            console.print("[yellow]Please enter a valid number.[/yellow]")

def load_config():
    """Load saved BLE device address."""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {}

def save_config(config):
    """Save BLE device address."""
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f)

async def get_ble_address():
    """Get BLE address from config or user selection."""
    config = load_config()
    saved_address = config.get("ble_address")

    if saved_address:
        console.print(f"[cyan]Previously connected to device: {saved_address}[/cyan]")
        choice = input("Connect to the same device? (y/n): ").lower()
        if choice == 'y':
            return saved_address

    new_address = await select_device()
    if new_address:
        config["ble_address"] = new_address
        save_config(config)
    return new_address

def calculate_motor_command(left_stick_x, left_stick_y, max_speed):
    """
    Convert joystick input to motor command.

    Args:
        left_stick_x: -1.0 (left) to +1.0 (right)
        left_stick_y: -1.0 (up/forward) to +1.0 (down/backward)
        max_speed: Maximum speed limit (50, 75, or 100)

    Returns:
        (speedA, dirA, speedB, dirB, duration)
    """
    # Apply deadzone
    if abs(left_stick_x) < DEADZONE:
        left_stick_x = 0.0
    if abs(left_stick_y) < DEADZONE:
        left_stick_y = 0.0

    # If both centered, stop
    if left_stick_x == 0 and left_stick_y == 0:
        return (0, 1, 0, 1, 1)

    # Calculate forward/backward speed (0-max_speed)
    base_speed = int(abs(left_stick_y) * max_speed)
    base_speed = max(15, min(max_speed, base_speed))  # Clamp to 15-max_speed

    # Determine direction (negative Y = forward, positive Y = backward)
    direction = 1 if left_stick_y < 0 else 0

    # Apply steering (differential drive)
    if abs(left_stick_x) > 0:
        # Reduce speed on inside wheel
        turn_factor = abs(left_stick_x)
        speed_reduction = int(base_speed * turn_factor * 0.5)

        if left_stick_x < 0:  # Turn left
            speedA = max(15, base_speed - speed_reduction)
            speedB = base_speed
        else:  # Turn right
            speedA = base_speed
            speedB = max(15, base_speed - speed_reduction)
    else:
        # Straight
        speedA = speedB = base_speed

    return (speedA, direction, speedB, direction, 2)

async def control_loop(client, joystick):
    """Main control loop - read controller and send commands to car."""
    max_speed_index = 2  # Start at 100%
    last_dpad_state = (0, 0)
    emergency_stop_active = False

    with Live(console=console, refresh_per_second=20) as live:
        while True:
            pygame.event.pump()

            # Read controller state
            left_x = joystick.get_axis(0)  # L3 X-axis
            left_y = joystick.get_axis(1)  # L3 Y-axis

            # Buttons
            button_x = joystick.get_button(0)      # X = emergency stop
            button_circle = joystick.get_button(1)  # Circle = quit

            # D-pad for speed adjustment
            dpad = joystick.get_hat(0) if joystick.get_numhats() > 0 else (0, 0)

            # Handle quit
            if button_circle:
                console.print("\n[yellow]Circle pressed - Quitting...[/yellow]")
                await send_command(client, 0, 1, 0, 1, 1)  # Stop car
                break

            # Handle emergency stop
            if button_x:
                if not emergency_stop_active:
                    emergency_stop_active = True
                    await send_command(client, 0, 1, 0, 1, 1)
                continue
            else:
                emergency_stop_active = False

            # Handle D-pad speed adjustment (detect rising edge)
            if dpad != last_dpad_state:
                if dpad[1] == 1:  # D-pad up
                    max_speed_index = min(len(MAX_SPEED_LEVELS) - 1, max_speed_index + 1)
                elif dpad[1] == -1:  # D-pad down
                    max_speed_index = max(0, max_speed_index - 1)
            last_dpad_state = dpad

            max_speed = MAX_SPEED_LEVELS[max_speed_index]

            # Calculate command
            command = calculate_motor_command(left_x, left_y, max_speed)

            # Send to car
            await send_command(client, *command)

            # Create status display
            table = Table(show_header=False, box=None)
            table.add_column("Label", style="cyan")
            table.add_column("Value")

            # Controller state
            table.add_row("L3 Position", f"[yellow]({left_x:+.2f}, {left_y:+.2f})[/yellow]")
            table.add_row("Max Speed", f"[green]{max_speed}%[/green] (D-pad ↑/↓ to adjust)")

            # Motor command
            speedA, dirA, speedB, dirB, duration = command
            dir_str_a = "FWD" if dirA == 1 else "BWD"
            dir_str_b = "FWD" if dirB == 1 else "BWD"
            table.add_row("Motor A", f"[magenta]{speedA}% {dir_str_a}[/magenta]")
            table.add_row("Motor B", f"[magenta]{speedB}% {dir_str_b}[/magenta]")

            # Status
            if emergency_stop_active:
                table.add_row("Status", "[red bold]EMERGENCY STOP[/red bold]")
            elif speedA == 0 and speedB == 0:
                table.add_row("Status", "[dim]Stopped[/dim]")
            else:
                table.add_row("Status", "[green]Running[/green]")

            table.add_row("", "[dim]X=Stop | Circle=Quit[/dim]")

            live.update(table)
            await asyncio.sleep(0.05)  # 20Hz

async def main():
    # Initialize pygame and joystick
    pygame.init()
    pygame.joystick.init()

    # Check for controllers
    joystick_count = pygame.joystick.get_count()
    if joystick_count == 0:
        console.print("[red]No controllers detected![/red]")
        console.print("Make sure your DualSense controller is connected.")
        sys.exit(1)

    # Get first controller
    joystick = pygame.joystick.Joystick(0)
    joystick.init()
    console.print(f"[green]Controller:[/green] {joystick.get_name()}\n")

    # Get BLE device
    ble_address = await get_ble_address()
    if not ble_address:
        console.print("[red]No device selected. Exiting.[/red]")
        pygame.quit()
        return

    console.print(f"[cyan]Connecting to car: {ble_address}[/cyan]")

    try:
        async with BleakClient(ble_address) as client:
            console.print(f"[green]Connected: {client.is_connected}[/green]\n")
            console.print("[bold]Controls:[/bold]")
            console.print("  L3 Up/Down: Forward/Backward")
            console.print("  L3 Left/Right: Steering")
            console.print("  D-pad Up/Down: Adjust max speed")
            console.print("  X: Emergency stop")
            console.print("  Circle: Quit\n")

            await control_loop(client, joystick)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
    finally:
        pygame.quit()
        console.print("[green]Disconnected. Goodbye![/green]")

if __name__ == "__main__":
    asyncio.run(main())
