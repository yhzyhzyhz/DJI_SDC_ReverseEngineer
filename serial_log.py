import serial, serial.tools.list_ports
import threading
import time
from datetime import datetime, timezone

BAUDRATE = 115200
OUTPUT_FILE_PFX = 'Data/serial_frames_'

OUTPUT_FILE = OUTPUT_FILE_PFX + datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S") + "z.txt"

def select_serial_ports():
    ports = list(serial.tools.list_ports.comports())
    if not ports:
        print("No serial ports available. ")
        return None
    
    for i, port in enumerate(ports):
        print(f"{i}: {port.device} - {port.description}")

    selected_indices = set()
    selected_ports = []

    while True:
        choice = input(f"Select port [0-{len(ports)-1}] or 's' to stop: ").strip()
        if choice.lower() == 's':
            break
        if choice.isdigit():
            idx = int(choice)
            if 0<= idx < len(ports):
                if idx in selected_indices:
                    print("Port already selected. ")
                    continue
                selected_indices.add(idx)
                selected_ports.append(ports[idx].device)
                continue
        print("Invalid selection. Please try again. ")
    
    return selected_ports


def read_serial(port_name, file_lock):
    ser = serial.Serial(port_name, BAUDRATE, timeout=0.6)
    buffer = bytearray()
    while True:
        data = ser.read(1)
        if not data:
            continue
        byte = data[0]
        if len(buffer) == 0:
            if byte == 0x55:
                buffer.append(byte)
        elif len(buffer) == 1:
            frame_len = data[0]
            buffer.append(frame_len)
            while len(buffer) < frame_len:
                next_bytes = ser.read(frame_len - len(buffer))
                if next_bytes:
                    buffer.extend(next_bytes)
            # Frame complete
            timestamp = int(time.time() * 1000)
            with file_lock:
                with open(OUTPUT_FILE, 'a') as f:
                    line = f"{timestamp}\t" + '\t'.join(f"{b:02X}" for b in buffer) + '\n'
                    f.write(line)
            buffer.clear()
        else:
            buffer.clear()  # Reset if out of sync

def main():
    serial_ports = select_serial_ports()
    file_lock = threading.Lock()
    threads = []
    for port in serial_ports:
        t = threading.Thread(target=read_serial, args=(port, file_lock), daemon=True)
        t.start()
        threads.append(t)
    print("Receiving data. Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Exiting.")

if __name__ == '__main__':
    main()