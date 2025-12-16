#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "bleak",
#     "readchar",
#     "rich",
# ]
# ///
"""
MicroRacer Keyboard Controller with readchar
Run with: ./controller_new.py
"""
import asyncio
import os
import json
from bleak import BleakClient, BleakScanner
import readchar
from rich.console import Console

console = Console()

CONFIG_FILE = "ble_device_config.json"
CHARACTERISTIC_UUID = "23408888-1f40-4cd8-9b89-ca8d45f8a5b0"

async def send_command(client, speedA, directionA, speedB, directionB, duration):
    command = bytearray([speedA, directionA, speedB, directionB, duration])
    await client.write_gatt_char(CHARACTERISTIC_UUID, command)

async def select_device():
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
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {}

def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f)

async def get_ble_address():
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

async def read_key_async():
    """Run readchar in executor to avoid blocking the event loop"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, readchar.readkey)

async def main():
    ble_address = await get_ble_address()
    if not ble_address:
        console.print("[red]No device selected. Exiting.[/red]")
        return

    console.print(f"[cyan]Connecting to device: {ble_address}[/cyan]")
    async with BleakClient(ble_address) as client:
        console.print(f"[green]Connected: {client.is_connected}[/green]")
        console.print("[bold]Controls: W=Forward, S=Backward, A=Left, D=Right, Q=Quit[/bold]\n")

        while True:
            # Read key in executor to not block async loop
            key = await read_key_async()

            if key == 'q':
                console.print("\n[red]Quitting...[/red]")
                break
            elif key == 'w':
                await send_command(client, 60, 1, 60, 1, 5)
                console.print("⬆️  [cyan]Forward[/cyan]")
            elif key == 's':
                await send_command(client, 50, 0, 50, 0, 5)
                console.print("⬇️  [yellow]Backward[/yellow]")
            elif key == 'a':
                await send_command(client, 40, 0, 40, 1, 3)
                console.print("⬅️  [magenta]Left[/magenta]")
            elif key == 'd':
                await send_command(client, 40, 1, 40, 0, 3)
                console.print("➡️  [blue]Right[/blue]")

if __name__ == "__main__":
    asyncio.run(main())
