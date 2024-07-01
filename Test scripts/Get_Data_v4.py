import pyvisa
import matplotlib.pyplot as plt
import numpy as np
import time
import math
import csv
import os
from datetime import datetime, timedelta

# File paths
input_file = r'C:\Users\bpkro\OneDrive\Escritorio\Chi-2\log.csv'
output_file = r'C:\Users\bpkro\OneDrive\Escritorio\Chi-2\Full_Data.csv'
# GPIB address of the lock-in amplifier
lock_in_address = 'GPIB0::13::INSTR'
start_time = datetime.now()  # Record the start time of the script

# Create the data_log csv file
def create_log_file():
    with open(output_file, 'w', newline='') as file:
        writer = csv.writer(file)

        # Header
        current_time = start_time.strftime("%B %d %Y %I:%M%p")
        writer.writerow(["-----------------------------------------------------------"])
        writer.writerow([current_time])
        writer.writerow(["Entire Data from session is collected in file. No distinction between runs is made."])
        writer.writerow(["-----------------------------------------------------------"])
        # Begin Data
        writer.writerow(['Timestamp', 'Temperature (K)', 'Vx', 'Vy'])

# Read new temperature lines from the log.csv file
def get_new_temperature_lines(file_path, last_position, start_time):
    with open(file_path, 'r') as file:
        file.seek(last_position)
        lines = file.readlines()
        last_position = file.tell()

    data = []
    for line in lines:
        parts = line.strip().split(',')
        if len(parts) > 1:
            try:
                timestamp = int(float(parts[0]))
                temperature = float(parts[1])
                latest_timestamp = datetime.fromtimestamp(timestamp)
                if latest_timestamp >= start_time:
                    data.append((latest_timestamp, temperature))
            except ValueError:
                continue
    
    return data, last_position

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

# Records live data to file and plots newly added data
def live_readout():
    timestamps = []
    temperatures = []
    x2_vals = []
    y2_vals = []
    voltage_readings = []

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

    last_position = 0
    plot_counter = 0

    def match_readings(temperature_data, voltage_readings):
        for temp_time, temp in temperature_data:
            closest_time = min(voltage_readings, key=lambda x: abs(x[0] - temp_time))
            append_to_data_log(temp_time, temp, closest_time[1])
            timestamps.append(temp_time)
            temperatures.append(temp)
            x2_vals.append(closest_time[1][0])
            y2_vals.append(closest_time[1][1])

            # Keep only the last 2000 data points for plotting
            if len(timestamps) > 2000:
                timestamps.pop(0)
                temperatures.pop(0)
                x2_vals.pop(0)
                y2_vals.pop(0)

    while True:
        # Collect lock-in data at regular intervals
        voltage_reading = read_lockin_data(lock_in_address)
        voltage_readings.append((datetime.now(), voltage_reading))

        # Read new temperature data from the log file
        new_data, last_position = get_new_temperature_lines(input_file, last_position, start_time)
        if new_data:
            match_readings(new_data, voltage_readings)

            # Convert timestamps to elapsed seconds
            time_elapsed = [(t - timestamps[0]).total_seconds() for t in timestamps]

            if plot_counter == 2:
                # Update plot data
                line1.set_data(time_elapsed, temperatures)
                line2.set_data(time_elapsed, x2_vals)
                line3.set_data(time_elapsed, y2_vals)

                # Adjust plot limits
                ax1.set_xlim(0, max(time_elapsed) + 1)
                ax1.set_ylim(min(temperatures) - 1, max(temperatures) + 1)
                ax1.set_title(f'Current Temperature: {temperatures[-1]:.2f} K')
                ax1.set_xticks([])

                ax2.set_xlim(0, max(time_elapsed) + 1)
                ax2.set_ylim(min(x2_vals), max(x2_vals))
                ax2.set_title(f'Current Reading: {x2_vals[-1]:.2f} V')
                ax2.set_xticks([])

                ax3.set_xlim(0, max(time_elapsed) + 1)
                ax3.set_ylim(min(y2_vals), max(y2_vals))
                ax3.set_title(f'Current Reading: {y2_vals[-1]:.2f} V')

                fig.canvas.draw()
                fig.canvas.flush_events()
                plot_counter = 0
            else:
                plot_counter += 1

        # Sleep for a second to maintain a 1-second interval for lock-in data collection
        time.sleep(1)

if __name__ == "__main__":
    # Create log file
    create_log_file()
    # Run Data recording and Live Plotting
    live_readout()
