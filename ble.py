import asyncio
import sqlite3
from bleak import BleakScanner
from colorama import Fore, Style, init
from storage import load_mac_addresses

# Initialize colors for radar
init(autoreset=True)

DB_PATH = "./devices.db"



async def main():
    def callback(device, advertisement_data):
        # Even if the phone rotates its MAC, the Linux kernel
        # resolves it back to the Identity MAC for us.

        target_macs = load_mac_addresses()
        if not target_macs:
            return

        if device.address.upper() in target_macs:
            rssi = advertisement_data.rssi
            print(f"{device.address}: {rssi}")

    async with BleakScanner(callback) as scanner:
        while True:
            await asyncio.sleep(0.1)

try:
    asyncio.run(main())
except KeyboardInterrupt:
    print("\nRadar stopped.")
