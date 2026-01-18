import tkinter as tk

# Initialize global target variables
target_voltage = 52.20
target_current = 7.65

sequence_number = 1

INITIAL_BYTES1 = bytes([0x55, 0x0E, 0x04, 0x66, 0xAB, 0x00, 0x01, 0x00, 0x40, 0x00, 0x01, 0x01])

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

# Status Label (to show success or error)
status_label = tk.Label(root, text="Enter values and click Set")
status_label.grid(row=3, column=0, columnspan=2)

root.mainloop()
