import pyvisa
import matplotlib.pyplot as plt
import numpy as np
import time
import csv
import os
from datetime import datetime

#read configuration file
def read_config(file_path):
    config = {}
    with open(file_path, 'r') as file:
        for line in file:
            # Ignore comments and empty lines
            if line.startswith('#') or line.strip() == '':
                continue
            # Split the line at '=' and strip whitespace
            key, value = line.strip().split('=', 1)
            # Try to convert the value to a float if possible
            try:
                value = float(value)
            except ValueError:
                pass  # Keep the value as a string if it cannot be converted to a float
            # Store the key-value pair in the config dictionary
            config[key] = value
    return config

#Find config file
def find_file(file_name, search_path):
    # Walk through the directory and its subdirectories
    for root, dirs, files in os.walk(search_path):
        # Check if the file name is in the list of files in the current directory
        if file_name in files:
            # Return the full path to the file
            return os.path.join(root, file_name)
    
    # If the file is not found, return None or handle as needed
    return None

# Create a new run file in the output folder
def create_run_file(output_file):
    with open(output_file, 'w+', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["-----------------------------------------------------------"])
        writer.writerow(["Third Harmonic Measurement. Make sure temperature data is being logged to file"])
        writer.writerow([datetime.now().strftime("%B %d %Y %I:%M%p")])
        writer.writerow(["-----------------------------------------------------------"])
        writer.writerow(['Timestamp', 'Temperature (K)', 'Vx1', 'Vy1', 'Vx3', 'Vy3'])
    return output_file

# Append new temperature and voltage data to the current run file
def append_to_run_file(filename, timestamp, temperature, voltage_data):
    with open(filename, 'a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([timestamp, temperature, voltage_data[0], voltage_data[1]])

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
                else:
                    data.append((latest_timestamp, temperature))
            except ValueError:
                continue
    return data, last_position

# Returns reading from Lock-in Data - A list with 4 values (X1, Y1, X3, Y3)
def read_lockin_data(address):
    rm = pyvisa.ResourceManager()
    lockin = rm.open_resource(address)
    try:
        # Query X1 (in-phase 1st Harmonic)
        x1 = float(lockin.query('OUTR? 1'))  
        # Query Y1 (out-of-phase 1st Harmonic)
        y1 = float(lockin.query('OUTR? 2'))
        
        # Query X3 (in-phase 3rd Harmonic)
        x3 = float(lockin.query('OUTR? 3'))
        # Query Y3 (out-of-phase 3rd Harmonic)
        y3 = float(lockin.query('OUTR? 4'))

        voltage_data = [x1, y1, x3, y3]
        return voltage_data
    except pyvisa.VisaIOError as e:
        print(f"An error occurred: {e}")
        return [None, None, None, None]
    finally:
        lockin.close()

def live_readout(lock_in_address, input_file, output_file, start_time):
    timestamps = []
    temperatures = []
    x1_vals = []
    y1_vals = []
    x3_vals = []
    y3_vals = []
    voltage_readings = []

    fig, (ax1, ax2, ax3) = plt.subplots(3, 1)
    fig.suptitle('Live Data Readout')
    
    line1, = ax1.plot([], [], 'm', marker='.', ls="")
    line2, = ax2.plot([], [], color='mediumseagreen', marker='.', ls="")
    line3, = ax3.plot([], [], color='steelblue', marker='.', ls="")
    ax1.set_ylabel('Temperature (K)')
    ax2.set_ylabel('First Harmonic Magnitude (V)')
    ax3.set_xlabel('Time (s)')
    ax3.set_ylabel('Third Harmonic Magnitude (V)')

    fig.show()

    #local variables
    last_position = 0
    plot_counter = 0

    # Matches the time stamps in the temperature log with lock-in readings
    def match_readings(temperature_data, voltage_readings, file):
        for temp_time, temp in temperature_data:
            closest_time = min(voltage_readings, key=lambda x: abs(x[0] - temp_time))
            append_to_run_file(file, temp_time, temp, closest_time[1])
            timestamps.append(temp_time)
            temperatures.append(temp)
            x1_vals.append(closest_time[1][0])
            y1_vals.append(closest_time[1][1])
            x3_vals.append(closest_time[1][2])
            y3_vals.append(closest_time[1][3])

            if len(timestamps) > 2000:
                timestamps.pop(0)
                temperatures.pop(0)
                x1_vals.pop(0)
                y1_vals.pop(0)
                x3_vals.pop(0)
                y3_vals.pop(0)

    while True:
        voltage_reading = read_lockin_data(lock_in_address)
        voltage_readings.append((datetime.now(), voltage_reading))
        new_data, last_position = get_new_temperature_lines(input_file, last_position, start_time)

        if new_data:
            match_readings(new_data, voltage_readings, output_file)
            time_elapsed = [(t - timestamps[0]).total_seconds() for t in timestamps]

            if plot_counter == 0:
                line1.set_data(time_elapsed, temperatures)
                line2.set_data(time_elapsed, np.sqrt(np.array(x1_vals)**2 + np.array(y1_vals)**2))
                line3.set_data(time_elapsed, np.sqrt(np.array(x3_vals)**2 + np.array(y3_vals)**2))

                ax1.relim()
                ax1.autoscale_view()
                ax1.set_title(f'Current Temperature: {temperatures[-1]:.2f} K')
                ax1.set_xticks([])

                ax2.relim()
                ax2.autoscale_view()
                ax2.set_title(f'X1: {x1_vals[-1]:.4f} V' + f', Y1: {y1_vals[-1]:.4f} V')
                ax2.set_xticks([])

                ax3.relim()
                ax3.autoscale_view()
                ax3.set_title(f'X1: {x3_vals[-1]:.4f} V' + f', Y1: {y3_vals[-1]:.4f} V')

                fig.canvas.draw()
                fig.canvas.flush_events()
                plot_counter = 0
            else:
                plot_counter += 1
        time.sleep(1)

#Paths and settings from settings.txt file
settings_file = os.path.abspath(find_file('settings.txt',os.path.dirname(__file__)))
settings = read_config(settings_file)

#Read from settings file
input_file=os.path.abspath(settings['input_file'])
output_file=os.path.abspath(settings['output_file'])
lock_in_address = str(settings['lock_in_address'])

start_time = datetime.now()  # Record the start time of the script

if __name__ == "__main__":
    #Create Full Data Log:
    create_run_file(output_file)
    #Data Logging and Plotting
    live_readout(lock_in_address, input_file, output_file, start_time)
