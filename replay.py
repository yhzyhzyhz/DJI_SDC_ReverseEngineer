import serial, serial.tools.list_ports
import time
import sys

def select_serial_port():
    ports = list(serial.tools.list_ports.comports())
    if not ports:
        print("No serial ports available. ")
        return None
    
    for i, port in enumerate(ports):
        print(f"{i}: {port.device} - {port.description}")

    while True:
        choice = input(f"Select port [0-{len(ports)-1}]: ")
        if choice.isdigit():
            idx = int(choice)
            if 0<= idx < len(ports):
                return ports[idx].device
        print("Invalid selection. Please try again. ")

def parse_file(filename):
    messages = []
    with open(filename, 'r') as f:
        for line in f:
            parts = line.strip().split('\t')
            if len(parts) < 2:
                continue
            timestamp = int(parts[0])
            data = bytearray(int(b, 16) for b in parts[1:])
            messages.append((timestamp, data))
    return messages

def read_frame(ser, timeout=0.6):
    """Read a frame starting with 0x55, where the second byte is the length."""
    start_time = time.time()
    while True:
        if time.time() - start_time > timeout:
            return None
        byte = ser.read(1)
        if not byte:
            continue
        if byte[0] == 0x55:
            length_byte = ser.read(1)
            if not length_byte:
                return None
            frame_length = length_byte[0]
            rest = ser.read(frame_length - 2)
            if len(rest) != frame_length - 2:
                return None
            frame = bytearray([0x55, frame_length]) + rest
            return frame

def replay_messages(messages, com_port, baudrate=115200):
    ser = serial.Serial(com_port, baudrate, timeout=0.1)
    try:
        base_time = messages[0][0]
        replay_start = time.time()
        for i, (timestamp, data) in enumerate(messages):
            target_time = replay_start + (timestamp - base_time) / 1000.0
            now = time.time()
            sleep_time = target_time - now
            if sleep_time > 0:
                time.sleep(sleep_time)
            # Send command
            if data[4] == 0xAB:
                ser.write(data)
                print(f"Sent at {timestamp}: {data.hex(' ')}")

            # Listen for response frame
            frame = read_frame(ser)
            if frame:
                print(f"Received response: {frame.hex(' ')}")
    finally:
        ser.close()
        print("COM port closed.")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        filename = sys.argv[1]
    else:
        print("Usage: python replay.py xxx.txt.")
        exit()

    com_port = select_serial_port()
    
    messages = parse_file(filename)
    if messages:
        print(f"Loaded {len(messages)} messages. Starting replay...")

        replay_messages(messages, com_port, 115200)
    else:
        print("No valid messages found in the file.")