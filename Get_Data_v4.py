import pyvisa
import matplotlib.pyplot as plt
import numpy as np
import time
import math
import csv
import os
from datetime import datetime

# File paths
input_file = r'C:\Users\bpkro\OneDrive\Escritorio\Chi-2\log.csv'
output_file = r'C:\Users\bpkro\OneDrive\Escritorio\Chi-2\Full_Data.csv'
# GPIB address of the lock-in amplifier
lock_in_address = 'GPIB0::13::INSTR'

# Read the most recent temperature from the log.csv file
def get_latest_temperature(file_path):
    with open(file_path, mode='r', newline='') as file:
        reader = csv.reader(file)
        for row in reader:
            pass
        last_line = row

    timestamp = int(float(last_line[0]))
    temperature = float(last_line[1])
    latest_timestamp = datetime.fromtimestamp(timestamp)
    latest_temperature = temperature    

    return latest_timestamp, latest_temperature

# Create the data_log csv file
def create_log_file():
    with open(output_file, 'w', newline='') as file:
        writer = csv.writer(file)

        #Header
        current_time = datetime.now().strftime("%B %d %Y %I:%M%p")
        writer.writerow(["-----------------------------------------------------------"])
        writer.writerow([current_time])
        writer.writerow(["Entire Data from session is collected in file. No distinction between runs is made."])
        writer.writerow(["-----------------------------------------------------------"])
        #Begin Data
        writer.writerow(['Timestamp', 'Temperature (K)', 'Vx', 'Vy'])

# Append new temperature and voltage data to the data_log csv file
def append_to_data_log(timestamp, temperature, voltage_data):
    with open(output_file, 'a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([timestamp, temperature, voltage_data[0], voltage_data[1]])

# Returns reading from Lock-in Data - A list with 2 values
def read_lockin_data(address):
    rm = pyvisa.ResourceManager()
    lockin = rm.open_resource(address)
    try:
        x2 = float(lockin.query('OUTP? 0'))  # Query X2 (in-phase 2nd Harm)
        y2 = float(lockin.query('OUTP? 1'))  # Query Y2 (out-of-phase 2nd Harm)
        voltage_data = [x2, y2]
        return voltage_data
    except pyvisa.VisaIOError as e:
        print(f"An error occurred: {e}")
        return [None, None]
    finally:
        lockin.close()

# Returns magnitude of voltage reading
def magnitude(x, y):
    return [math.sqrt(x[i]**2 + y[i]**2) for i in range(len(x))]

# Records live data to file and plots newly added data
def live_readout():
    timestamps = []
    temperatures = []
    x2_vals = []
    y2_vals = []

    fig, (ax1, ax2, ax3) = plt.subplots(3, 1)
    fig.suptitle('Live Data Readout')
    line1, = ax1.plot([], [], 'r')
    line2, = ax2.plot([], [], 'g')
    line3, = ax3.plot([], [], 'b')
    ax1.set_ylabel('Temperature (K)')
    ax2.set_ylabel('Second Harmonic In-phase (V)')
    ax3.set_xlabel('Time (s)')
    ax3.set_ylabel('Second Harmonic Out-of-phase (V)')
    fig.show()

    while True:
        latest_timestamp, latest_temperature= get_latest_temperature(input_file)
        if latest_timestamp and latest_temperature:
            # Record data
            v_readings = read_lockin_data(lock_in_address)
            append_to_data_log(latest_timestamp, latest_temperature, v_readings)

            timestamps.append(latest_timestamp)
            temperatures.append(latest_temperature)
            x2_vals.append(v_readings[0])
            y2_vals.append(v_readings[1])

            # Convert timestamps to elapsed seconds
            time_elapsed = [(t - timestamps[0]).total_seconds() for t in timestamps]

            # Update plot data
            line1.set_data(time_elapsed, temperatures)
            line2.set_data(time_elapsed, x2_vals)
            line3.set_data(time_elapsed, y2_vals)
           
            # Adjust plot limits
            ax1.set_xlim(0, max(time_elapsed) + 1)
            ax1.set_ylim(min(temperatures) - 1, max(temperatures) + 1)
            ax1.set_title(f'Current Temperature: {latest_temperature:.2f} K')
            ax1.set_xticks([])

            ax2.set_xlim(0, max(time_elapsed) + 1)
            ax2.set_ylim(min(x2_vals), max(x2_vals))
            ax2.set_title(f'Current Reading: {v_readings[0]:.2f} V')
            ax2.set_xticks([])

            ax3.set_xlim(0, max(time_elapsed) + 1)
            ax3.set_ylim(min(y2_vals), max(y2_vals))
            ax3.set_title(f'Current Reading: {v_readings[1]:.2f} V')

            fig.canvas.draw()
            fig.canvas.flush_events()
        time.sleep(1)        

if __name__ == "__main__":
    # Create log file
    create_log_file()
    # Run Data recording and Live Plotting
    live_readout()
