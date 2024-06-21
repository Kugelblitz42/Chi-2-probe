import pyvisa
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.animation import FuncAnimation
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

# Function to monitor changes in the temperature log file
def wait_for_file_update(file_path, last_mod_time):
    while True:
        mod_time = os.path.getmtime(file_path)
        if mod_time != last_mod_time:
            return mod_time
        time.sleep(1)

# Create the data_log csv file
def create_log_file():
    with open(output_file, 'w', newline='') as file:
        writer = csv.writer(file)

        #Header
        current_time = datetime.now().strftime("%B %dth %Y %I:%M%p")
        writer.writerow(["-----------------------------------------------------------"])
        writer.writerow([current_time])
        writer.writerow(["Entire Data from session is collected in file. No distinction between runs is made."])
        writer.writerow(["-----------------------------------------------------------"])

        #Begin Data
        writer.writerow(['Timestamp', 'Temperature (K)', 'Vx', 'Vy'])

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

# Append new temperature and voltage data to the data_log csv file
def append_to_data_log(timestamp, temperature, voltage_data):
    with open(output_file, 'a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([timestamp, temperature, voltage_data[0], voltage_data[1]])

#Returns reading from Lock-in Data -  A list with 4 values
def read_lockin_data(address):
    """
    Read the X and Y data from the SRS865A lock-in amplifier.
    Parameters:
    address (str): GPIB address of the lock-in amplifier.
    Returns:
    List: (x2, y2, x3, y3) where x is the in-phase component and y is the out-of-phase component of the corresponding harmonics.
    """
    rm = pyvisa.ResourceManager()
    lockin = rm.open_resource(address)
    
    try:
        x2 = float(lockin.query('OUTP? 0'))  # Query X2 (in-phase 2nd Harm)
        y2 = float(lockin.query('OUTP? 1'))  # Query Y2 (out-of-phase 2nd Harm)
        voltage_data = [x2, y2]
        return  voltage_data
    except pyvisa.VisaIOError as e:
        print(f"An error occurred: {e}")
        return [None, None]
    finally:
        lockin.close()

#Returns magnitude of voltage reading
def magnitude(x, y):
    vals = []
    for i in range(len(x)):
        vals.append(math.sqrt(x[i]**2 + y[i]**2))
    return vals

#Records live data to file and plots newly added data
def live_readout():
    timestamps = []
    temperatures = []
    x2_vals = []
    y2_vals = []

    #Plot begins
    plt.ion()
    fig, axs=plt.subplots(1, 2)
    line1, = axs[0].plot([], [], 'r', label='Temperature (K)', marker='o')
    line2, = axs[1].plot([], [], 'g', label='Second Harmonic (V)', marker='o')
    plt.legend()
    
    while True:
        latest_timestamp, latest_temperature = get_latest_temperature(input_file)
        if latest_timestamp and latest_temperature:
            #Record data
            v_readings= read_lockin_data(lock_in_address)
            append_to_data_log(latest_timestamp, latest_temperature, v_readings)
            
            timestamps.append(latest_timestamp)
            temperatures.append(latest_temperature)
            x2_vals.append(v_readings[0])
            y2_vals.append(v_readings[1])

            #Live_Plot
            line1.set_xdata(np.subtract(timestamps,timestamps[0])) #Time reset to zero for plotting
            line1.set_ydata(temperatures)
            line2.set_xdata(np.subtract(timestamps,timestamps[0]))
            line2.set_ydata(magnitude(x2_vals, y2_vals))

            axs[0].relim()
            axs[0].autoscale_view()
            axs[1].relim()
            axs[1].autoscale_view()
            axs[0].set_title('Current Temperature: '+ str(latest_temperature)+ ' K')
            plt.draw()
            plt.pause(0.1)

        wait_for_file_update(input_file, os.path.getmtime(input_file))

if __name__ == "__main__":
    #Create log file
    create_log_file()
    #Run Data recording and Live Plotting
    live_readout()
