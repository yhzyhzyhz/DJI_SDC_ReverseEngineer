import serial, serial.tools.list_ports
import threading
import time
from datetime import datetime, timezone
import tkinter as tk
from tkinter import scrolledtext

BAUDRATE = 115200
OUTPUT_FILE_PFX = 'Data/serial_frames_'
# Supported DEVICEMODE are MPPT3 or BATTPAK for now
DEVICEMODE = "MPPT3"

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
            parse_frame(buffer)
            timestamp = int(time.time() * 1000)
            with file_lock:
                with open(OUTPUT_FILE, 'a') as f:
                    line = f"{timestamp}\t" + '\t'.join(f"0x{b:02X}" for b in buffer) + '\n'
                    f.write(line)
            buffer.clear()
        else:
            buffer.clear()  # Reset if out of sync

def parse_frame(frame):
    if frame[0] != 0x55:
        return None
    if len(frame) != frame[1]:
        return None
    
    if DEVICEMODE == "MPPT3":
        if frame[3] == 0x38:
            payload_text = ' '.join(f'{byte:02X}' for byte in frame)
            text_area_38.insert(tk.END, f'Payload: {payload_text}\n')
            text_area_38.see(tk.END)

            request_voltage_var.set(f"Voltage: {(int.from_bytes(frame[12:14], byteorder='little') * 0.01):.2f} V")
            request_current_var.set(f"Current: {(int.from_bytes(frame[14:16], byteorder='little') * 0.01):.2f} A")
        elif frame[3] == 0x9C:
            payload_text = ' '.join(f'{byte:02X}' for byte in frame)
            text_area_9C.insert(tk.END, f'Payload: {payload_text}\n')
            text_area_9C.see(tk.END)

            output_voltage  = int.from_bytes(frame[16:18], byteorder='little') * 0.01
            output_current  = int.from_bytes(frame[18:20], byteorder='little') * 0.01
            temperature     = int.from_bytes(frame[28:30], byteorder='little') * 0.1
            input_voltage_1 = int.from_bytes(frame[30:32], byteorder='little') * 0.01
            input_voltage_2 = int.from_bytes(frame[32:34], byteorder='little') * 0.01
            input_voltage_3 = int.from_bytes(frame[34:36], byteorder='little') * 0.01

            byte2021_var.set(f"Byte20 21: {int.from_bytes(frame[20:22], byteorder='little')}")
            byte2223_var.set(f"Byte22 23: {int.from_bytes(frame[22:24], byteorder='little')}")
            byte2627_var.set(f"Input Power: {int.from_bytes(frame[26:28], byteorder='little')}")

            output_power_var.set(f"Output Power(Calculated): {(output_voltage*output_current):.2f} W")
            output_voltage_var.set(f"Output Voltage: {output_voltage:.2f} V")
            output_current_var.set(f"Output Current: {output_current:.2f} A")
            temperature_var.set(f"Temperature: {temperature:.1f} C")
            input_voltage_1_var.set(f"Input Voltage 1: {input_voltage_1:.2f} V")
            input_voltage_2_var.set(f"Input Voltage 2: {input_voltage_2:.2f} V")
            input_voltage_3_var.set(f"Input Voltage 3: {input_voltage_3:.2f} V")
    if DEVICEMODE == "BATTPAK":
        if frame[3] == 0xFC:
            payload_text = ' '.join(f'{byte:02X}' for byte in frame)
            text_area_FC.insert(tk.END, f'Payload: {payload_text}\n')
            text_area_FC.see(tk.END)
        if frame[3] == 0x2D:
            payload_text = ' '.join(f'{byte:02X}' for byte in frame)
            text_area_2D.insert(tk.END, f'Payload: {payload_text}\n')
            text_area_2D.see(tk.END)

if __name__ == '__main__':

    serial_ports = select_serial_ports()

    # Initialize GUI
    root = tk.Tk()
    root.title("Serial Frame Payload Viewer")

    if DEVICEMODE == "MPPT3":
        text_area_38 = scrolledtext.ScrolledText(root, wrap="none", width=180, height=10)
        text_area_38.pack(padx=10, pady=10)
        text_area_38.insert(tk.END, "Payloads with class_b = 0x38:\n")

        text_area_9C = scrolledtext.ScrolledText(root, wrap="none", width=180, height=10)
        text_area_9C.pack(padx=10, pady=10)
        text_area_9C.insert(tk.END, "Payloads with class_b = 0x9C:\n")

        request_voltage_var = tk.StringVar()
        request_voltage_label = tk.Label(root, textvariable=request_voltage_var, anchor=tk.W)
        request_voltage_label.pack(padx=10, pady=5, fill=tk.X)

        request_current_var = tk.StringVar()
        request_current_label = tk.Label(root, textvariable=request_current_var, anchor=tk.W)
        request_current_label.pack(padx=10, pady=5, fill=tk.X)

        output_power_var = tk.StringVar()
        output_power_label = tk.Label(root, textvariable=output_power_var, anchor=tk.W)
        output_power_label.pack(padx=10, pady=5, fill=tk.X)

        output_voltage_var = tk.StringVar()
        output_voltage_label = tk.Label(root, textvariable=output_voltage_var, anchor=tk.W)
        output_voltage_label.pack(padx=10, pady=5, fill=tk.X)

        output_current_var = tk.StringVar()
        output_current_label = tk.Label(root, textvariable=output_current_var, anchor=tk.W)
        output_current_label.pack(padx=10, pady=5, fill=tk.X)

        temperature_var = tk.StringVar()
        temperature_label = tk.Label(root, textvariable=temperature_var, anchor=tk.W)
        temperature_label.pack(padx=10, pady=5, fill=tk.X)

        input_voltage_1_var = tk.StringVar()
        input_voltage_1_label = tk.Label(root, textvariable=input_voltage_1_var, anchor=tk.W)
        input_voltage_1_label.pack(padx=10, pady=5, fill=tk.X)

        input_voltage_2_var = tk.StringVar()
        input_voltage_2_label = tk.Label(root, textvariable=input_voltage_2_var, anchor=tk.W)
        input_voltage_2_label.pack(padx=10, pady=5, fill=tk.X)

        input_voltage_3_var = tk.StringVar()
        input_voltage_3_label = tk.Label(root, textvariable=input_voltage_3_var, anchor=tk.W)
        input_voltage_3_label.pack(padx=10, pady=5, fill=tk.X)

        byte2021_var = tk.StringVar()
        byte2021_label = tk.Label(root, textvariable=byte2021_var, anchor=tk.W)
        byte2021_label.pack(padx=10, pady=5, fill=tk.X)

        byte2223_var = tk.StringVar()
        byte2223_label = tk.Label(root, textvariable=byte2223_var, anchor=tk.W)
        byte2223_label.pack(padx=10, pady=5, fill=tk.X)

        byte2627_var = tk.StringVar()
        byte2627_label = tk.Label(root, textvariable=byte2627_var, anchor=tk.W)
        byte2627_label.pack(padx=10, pady=5, fill=tk.X)
    if DEVICEMODE == "BATTPAK":
        text_area_FC = scrolledtext.ScrolledText(root, wrap="none", width=180, height=10)
        text_area_FC.pack(padx=10, pady=10)
        text_area_FC.insert(tk.END, "Payloads with class_b = 0xFC:\n")

        text_area_2D = scrolledtext.ScrolledText(root, wrap="none", width=180, height=10)
        text_area_2D.pack(padx=10, pady=10)
        text_area_2D.insert(tk.END, "Payloads with class_b = 0x2D:\n")

    OUTPUT_FILE = OUTPUT_FILE_PFX + datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S") + "z.txt"
    file_lock = threading.Lock()
    threads = []
    for port in serial_ports:
        t = threading.Thread(target=read_serial, args=(port, file_lock), daemon=True)
        t.start()
        threads.append(t)

    root.mainloop()
