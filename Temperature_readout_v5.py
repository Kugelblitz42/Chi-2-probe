import os
import time
import csv
import matplotlib.pyplot as plt
from datetime import datetime

# File paths
input_file = r'C:\Users\bpkro\OneDrive\Escritorio\Chi-2\log.csv'
output_file = r'C:\Users\bpkro\OneDrive\Escritorio\Chi-2\Temperature_log.csv'

# Create the temperature_log csv file
def create_temperature_log_file():
    with open(output_file, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['Timestamp', 'Temperature (K)'])

# Read the most recent temperature from the log.csv file
def get_latest_temperature(file_path):
    with open(file_path, 'r') as file:
        lines = file.readlines()
    
    data_start = False
    latest_temperature = None
    latest_timestamp = None
    
    for line in lines:
        if data_start:
            parts = line.strip().split(',')
            if len(parts) > 1:
                try:
                    timestamp = float(parts[0])
                    temperature = float(parts[1])
                    latest_timestamp = datetime.fromtimestamp(timestamp)
                    latest_temperature = temperature
                except ValueError:
                    continue
        elif '[Data]' in line:
            data_start = True
    
    return latest_timestamp, latest_temperature

# Append new temperature data to the temperature_log csv file
def append_to_temperature_log(timestamp, temperature):
    with open(output_file, 'a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([timestamp, temperature])

# Function to monitor the file for changes
def wait_for_file_update(file_path, last_mod_time):
    while True:
        mod_time = os.path.getmtime(file_path)
        if mod_time != last_mod_time:
            return mod_time
        time.sleep(0.4)

# Function to plot the temperature data
def live_plot():
    timestamps = []
    temperatures = []

    plt.ion()
    fig, ax = plt.subplots()
    line, = ax.plot(timestamps, temperatures, label='Temperature (K)')
    ax.set_xlabel('Time')
    ax.set_ylabel('Temperature (K)')
    plt.legend()

    while True:
        latest_timestamp, latest_temperature = get_latest_temperature(input_file)
        if latest_timestamp and latest_temperature:
            append_to_temperature_log(latest_timestamp, latest_temperature)
            
            timestamps.append(latest_timestamp)
            temperatures.append(latest_temperature)
            
            line.set_xdata(timestamps)
            line.set_ydata(temperatures)
            ax.relim()
            ax.autoscale_view()
            plt.draw()
            plt.pause(0.3)
            
        time.sleep(0.1)
        wait_for_file_update(input_file, os.path.getmtime(input_file))

if __name__ == "__main__":
    create_temperature_log_file()
    live_plot()
