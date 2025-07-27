import serial
import threading
import time

SERIAL_PORTS = ['COM7', 'COM9']
BAUDRATE = 115200
OUTPUT_FILE = 'Data/serial_frames.txt'

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
    file_lock = threading.Lock()
    threads = []
    for port in SERIAL_PORTS:
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