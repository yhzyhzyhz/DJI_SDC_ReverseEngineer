import tkinter as tk
import serial
import threading
import time
from datetime import datetime

# Initialize global target variables
target_voltage = 52.20
target_current = 7.65

sequence_number = 1

INITIAL_BYTES1 = bytes([0x55, 0x0E, 0x04, 0x66, 0xAB, 0x00, 0x01, 0x00, 0x40, 0x00, 0x01, 0x01])
INITIAL_BYTES2 = bytes([0x55, 0x0E, 0x04, 0x66, 0xAB, 0xEB, 0x01, 0x00, 0x40, 0x5A, 0x01, 0x01])

FRAME_66 = bytes([0x55, 0x0E, 0x04, 0x66, 0xAB, 0xEB, 0x01, 0x00, 0x40, 0x5A, 0x02, 0x01])

# Serial port configuration
SERIAL_PORT = "/dev/ttyUSB0"
BAUD_RATE = 115200
serial_connection = None
serial_thread = None
serial_stop_event = threading.Event()
log_file_path = f"Data/host_mppt_serial_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

def construct_frame_38():
    """Construct the byte frame for command 0x38."""
    frame = bytearray()
    frame.append(0x55)  # 0: Start byte
    frame.append(0x17)  # 1: Length byte 
    frame.append(0x04)  # 2: Class_A byte
    frame.append(0x38)  # 3: Class_B byte
    frame.append(0xAB)  # 4: Talker
    frame.append(0xEB)  # 5: Listener

    global sequence_number
    # Convert sequence number to 2 bytes in little-endian format Bytes 6-7
    seq_bytes = sequence_number.to_bytes(2, byteorder='little')
    frame.extend(seq_bytes)
    sequence_number += 1

    frame.append(0x40) # 8: direction
    frame.append(0x5A) # 9: fixed byte
    frame.append(0x03) # 10: fixed byte
    frame.append(0x01) # 11: Charging enable?

    # Voltage in x0.1V (2 bytes)    
    voltage_send = int(target_voltage * 100)
    frame.extend(voltage_send.to_bytes(2, byteorder='little'))
    # Current in x0.1A (2 bytes)
    current_send = int(target_current * 100)
    frame.extend(current_send.to_bytes(2, byteorder='little'))

    frame.append(0x01) # 16: charging enable?
    frame.append(0x01) # 17: is charging?
    frame.append(0x00) # 18: fixed byte
    frame.append(0x8F) # 19: bitwise flags?
    frame.append(0x01) # 20: is charging?

    return bytes(frame)

def update_sequence_number(data: bytes) -> bytes:
    """Update the sequence number in the data frame."""
    if len(data) < 7:
        raise ValueError("Data frame is too short to update sequence number.")
    
    global sequence_number
    # Convert sequence number to 2 bytes in little-endian format
    seq_bytes = sequence_number.to_bytes(2, byteorder='little')
    
    # Create a mutable bytearray from the original data
    mutable_data = bytearray(data)
    
    # Update the sequence number bytes
    mutable_data[6] = seq_bytes[0]
    mutable_data[7] = seq_bytes[1]

    sequence_number += 1

    return bytes(mutable_data)

def add_crc16_checksum(data: bytes) -> bytes:
    """
    Calculates a CRC16 checksum and appends it to the data.
    Length of data is determined by the value of the second byte. Including the CRC bytes.
    Settings: Poly=0x1021, Init=0x496c, RefIn=True, RefOut=True, XorOut=0x0000
    """
    # Truncate or slice data based on the length specified in the second byte
    if len(data) < 2:
        raise ValueError("Input bytes must be at least 2 bytes long.")
    
    crc = 0x496C  # Initial value
    poly = 0x1021

    for byte in data:
        # Input reverse: Reflect each byte
        temp_byte = bin(byte)[2:].zfill(8)[::-1]
        crc ^= (int(temp_byte, 2) << 8)
        
        for _ in range(8):
            if crc & 0x8000:
                crc = (crc << 1) ^ poly
            else:
                crc <<= 1
            crc &= 0xFFFF

    # Output reverse: Reflect the final 16-bit result
    reflected_crc = int(bin(crc)[2:].zfill(16)[::-1], 2)
    
    # Append CRC in Little Endian (standard for reflected CRC) or Big Endian as needed
    # Using pack to append the 2 bytes of the checksum
    return data + reflected_crc.to_bytes(2, byteorder='little')


def set_values():
    """Update global variables based on current entry box content."""
    global target_voltage, target_current
    
    try:
        # Retrieve content from entry boxes and convert to float
        target_voltage = float(voltage_entry.get())
        target_current = float(current_entry.get())
        
        # Confirmation in console and UI
        print(f"Updated: Voltage = {target_voltage}V, Current = {target_current}A")
        status_label.config(text=f"Target Set: {target_voltage}V, {target_current}A", fg="green")
    except ValueError:
        # Handle cases where input is not a valid number
        status_label.config(text="Error: Please enter numeric values", fg="red")


def serial_worker():
    """Worker thread to handle serial communication."""
    global serial_connection
    
    try:
        # Open serial port
        serial_connection = serial.Serial(
            port=SERIAL_PORT,
            baudrate=BAUD_RATE,
            timeout=1.0
        )
        print(f"Serial port {SERIAL_PORT} opened successfully.")
        status_label.config(text="Serial connected", fg="green")
        
        last_send_time = time.time()
        
        # Open log file for writing
        with open(log_file_path, 'w') as log_file:
            log_file.write(f"Serial Log Start - {datetime.now()}\n")
            log_file.write(f"Port: {SERIAL_PORT}, Baud: {BAUD_RATE}\n\n")
            
            frame_to_send = add_crc16_checksum(update_sequence_number(INITIAL_BYTES1))
            serial_connection.write(frame_to_send)
            log_entry = f"[{datetime.now()}] SENT: {' '.join(f'{byte:02X}' for byte in frame_to_send)}\n"
            print(log_entry.strip())
            log_file.write(log_entry)
            log_file.flush()

            # Receive data from serial port
            if serial_connection.in_waiting > 0:
                data = serial_connection.read(serial_connection.in_waiting)
                log_entry = f"[{datetime.now()}] RECV: {' '.join(f'{byte:02X}' for byte in data)}\n"
                print(log_entry.strip())
                log_file.write(log_entry)
                log_file.flush()

            frame_to_send = add_crc16_checksum(update_sequence_number(INITIAL_BYTES2))
            serial_connection.write(frame_to_send)
            log_entry = f"[{datetime.now()}] SENT: {' '.join(f'{byte:02X}' for byte in frame_to_send)}\n"
            print(log_entry.strip())
            log_file.write(log_entry)
            log_file.flush()



            while not serial_stop_event.is_set():
                try:
                    # Send bytes every 500ms
                    current_time = time.time()
                    if current_time - last_send_time >= 0.5:

                        # frame_to_send = add_crc16_checksum(update_sequence_number(INITIAL_BYTES1))
                        frame_to_send = add_crc16_checksum(update_sequence_number(FRAME_66))
                        serial_connection.write(frame_to_send)
                        log_entry = f"[{datetime.now()}] SENT: {' '.join(f'{byte:02X}' for byte in frame_to_send)}\n"
                        print(log_entry.strip())
                        log_file.write(log_entry)
                        log_file.flush()

                        frame_to_send = add_crc16_checksum(construct_frame_38())
                        serial_connection.write(frame_to_send)
                        log_entry = f"[{datetime.now()}] SENT: {' '.join(f'{byte:02X}' for byte in frame_to_send)}\n"
                        print(log_entry.strip())
                        log_file.write(log_entry)
                        log_file.flush()

                        last_send_time = current_time
                    
                    # Receive data from serial port
                    if serial_connection.in_waiting > 0:
                        data = serial_connection.read(serial_connection.in_waiting)
                        log_entry = f"[{datetime.now()}] RECV: {' '.join(f'{byte:02X}' for byte in data)}\n"
                        print(log_entry.strip())
                        log_file.write(log_entry)
                        log_file.flush()
                    
                    time.sleep(0.01)  # Small sleep to prevent busy waiting
                    
                except Exception as e:
                    error_msg = f"[{datetime.now()}] Error in serial communication: {e}\n"
                    print(error_msg.strip())
                    log_file.write(error_msg)
                    log_file.flush()
                    break
        
        print(f"Serial log saved to {log_file_path}")
        
    except serial.SerialException as e:
        error_msg = f"Failed to open serial port {SERIAL_PORT}: {e}"
        print(error_msg)
        status_label.config(text=error_msg, fg="red")
    finally:
        if serial_connection and serial_connection.is_open:
            serial_connection.close()
            print(f"Serial port {SERIAL_PORT} closed.")
            status_label.config(text="Serial disconnected", fg="red")


def start_serial_thread():
    """Start the serial communication thread."""
    global serial_thread
    
    if serial_thread is None or not serial_thread.is_alive():
        serial_stop_event.clear()
        serial_thread = threading.Thread(target=serial_worker, daemon=True)
        serial_thread.start()
        print("Serial thread started.")
    else:
        print("Serial thread is already running.")


def stop_serial_thread():
    """Stop the serial communication thread."""
    global serial_thread
    
    if serial_thread and serial_thread.is_alive():
        serial_stop_event.set()
        serial_thread.join(timeout=2)
        print("Serial thread stopped.")
    else:
        print("Serial thread is not running.")

test = add_crc16_checksum(update_sequence_number(INITIAL_BYTES1))
print("Test Frame with CRC:", ' '.join(f'{byte:02X}' for byte in test))

# --- Setup Main Window ---
root = tk.Tk()
root.title("MPPT Controller")

# Voltage Input Row
tk.Label(root, text="Voltage (V):").grid(row=0, column=0, padx=10, pady=10)
voltage_entry = tk.Entry(root)
voltage_entry.grid(row=0, column=1)
voltage_entry.insert(0, "0.0") # Default value

# Current Input Row
tk.Label(root, text="Current (A):").grid(row=1, column=0, padx=10, pady=10)
current_entry = tk.Entry(root)
current_entry.grid(row=1, column=1)
current_entry.insert(0, "0.0") # Default value

# Set Button
set_button = tk.Button(root, text="Set", command=set_values, width=10)
set_button.grid(row=2, column=0, columnspan=2, pady=10)

# Serial Control Buttons
start_serial_button = tk.Button(root, text="Start Serial", command=start_serial_thread, width=10, bg="lightgreen")
start_serial_button.grid(row=3, column=0, padx=5, pady=10)

stop_serial_button = tk.Button(root, text="Stop Serial", command=stop_serial_thread, width=10, bg="lightcoral")
stop_serial_button.grid(row=3, column=1, padx=5, pady=10)

# Status Label (to show success or error)
status_label = tk.Label(root, text="Enter values and click Set")
status_label.grid(row=4, column=0, columnspan=2)

def on_closing():
    """Handle window closing event."""
    print("Closing application...")
    stop_serial_thread()
    root.destroy()

root.protocol("WM_DELETE_WINDOW", on_closing)
root.mainloop()
