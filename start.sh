#!/bin/bash

sudo -v

# Start bt_service
sudo python bt_service.py &
BT_PID=$!

# Start ble
python ble.py &
BLE_PID=$!

# Cleanup on exit
cleanup() {
    echo "Stopping services..."
    sudo kill $BT_PID 2>/dev/null
    kill $BLE_PID 2>/dev/null
    exit 0
}

trap cleanup SIGINT SIGTERM

wait
