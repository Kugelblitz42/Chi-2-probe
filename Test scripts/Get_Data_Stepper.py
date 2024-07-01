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

# Create a new run file in the output folder
def create_run_file(run_number, dc_offset, run):
    if run==True:
        filename = os.path.join(output_folder, f'Run_{run_number}.csv')
    else:
        filename = output_file
    with open(filename, 'w+', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["-----------------------------------------------------------"])
        writer.writerow([datetime.now().strftime("%B %d %Y %I:%M%p")])
        writer.writerow(["Run: "+ str(run_number)+". DC_offset: "+str(dc_offset)+ str("V")])
        writer.writerow(["-----------------------------------------------------------"])
        writer.writerow(['Timestamp', 'Temperature (K)', 'Vx', 'Vy'])
    return filename

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

# Append new temperature and voltage data to the current run file
def append_to_run_file(filename, timestamp, temperature, voltage_data):
    with open(filename, 'a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([timestamp, temperature, voltage_data[0], voltage_data[1]])

# Returns reading from Lock-in Data - A list with 2 values
def read_lockin_data(address):
    #rm = pyvisa.ResourceManager()
    #lockin = rm.open_resource(address)
    try:
        x2 = 5#float(lockin.query('OUTP? 0'))  # Query X2 (in-phase 2nd Harm)
        y2 = 5#float(lockin.query('OUTP? 1'))  # Query Y2 (out-of-phase 2nd Harm)
        voltage_data = [x2, y2]
        return voltage_data
    except pyvisa.VisaIOError as e:
        print(f"An error occurred: {e}")
        return [None, None]
    #finally:
        #lockin.close()

# Detects trend in temperature data
def detect_trend(temperatures, tolerance):
    last_60_temps = temperatures[-60:]
    if len(last_60_temps) < 2:
        return "Not enough data"
    
    x_values = np.arange(len(last_60_temps))
    y_values = np.array(last_60_temps)
    slope, _ = np.polyfit(x_values, y_values, 1)

    if abs(slope) < tolerance:
        return "steady"
    elif slope > 0:
        return "warming"
    else:
        return "cooling"
    
#Set Lock-in settings
def set_oscillator_parameters(address, dc_offset, ac_amplitude, frequency):
    """
    Set the internal oscillator parameters for the SRS865A lock-in amplifier.
    
    Parameters:
    address (str): GPIB address of the lock-in amplifier.
    dc_offset (float): DC offset voltage in volts.
    ac_amplitude (float): AC amplitude voltage in volts.
    frequency (float): Frequency in hertz.
    """
    # Initialize the VISA resource manager
    rm = pyvisa.ResourceManager()
    
    # Open a connection to the SRS865A lock-in amplifier
    lockin = rm.open_resource(address)
    
    try:
        # Set DC offset
        lockin.write(f'SOFF {dc_offset}')
        print(f'Set DC offset to {dc_offset} V')
        
        # Set AC amplitude
        lockin.write(f'SLVL {ac_amplitude}')
        print(f'Set AC amplitude to {ac_amplitude} V')
        
        # Set frequency
        lockin.write(f'FREQ {frequency}')
        print(f'Set frequency to {frequency} Hz')

    except pyvisa.VisaIOError as e:
        print(f"An error occurred: {e}")
    finally:
        # Close the connection to the lock-in amplifier
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
    trend_counter = 0
    current_dc_offset = dc_offset
    run_number = 1
    recording = False
    current_run_file = None

    # Matches the time stamps in the temperature log with lock-in readings
    def match_readings(temperature_data, voltage_readings, file):
        for temp_time, temp in temperature_data:
            closest_time = min(voltage_readings, key=lambda x: abs(x[0] - temp_time))
            append_to_run_file(file, temp_time, temp, closest_time[1])
            timestamps.append(temp_time)
            temperatures.append(temp)
            x2_vals.append(closest_time[1][0])
            y2_vals.append(closest_time[1][1])

            if len(timestamps) > 2000:
                timestamps.pop(0)
                temperatures.pop(0)
                x2_vals.pop(0)
                y2_vals.pop(0)

    while True:
        voltage_reading = read_lockin_data(lock_in_address)
        voltage_readings.append((datetime.now(), voltage_reading))
        new_data, last_position = get_new_temperature_lines(input_file, last_position, start_time)

        if new_data:
            match_readings(new_data, voltage_readings, output_file)
            if recording:
                match_readings(new_data, voltage_readings, current_run_file)

            time_elapsed = [(t - timestamps[0]).total_seconds() for t in timestamps]

            if plot_counter == 0:
                line1.set_data(time_elapsed, temperatures)
                line2.set_data(time_elapsed, x2_vals)
                line3.set_data(time_elapsed, y2_vals)

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

            if trend_counter == 15:
                trend = detect_trend(temperatures, tolerance)
                print(trend+': '+str(datetime.now()))
                if trend == "steady":
                    if not recording and abs(temperatures[-1]-temp_min)<=0.01:
                        set_oscillator_parameters(lock_in_address, current_dc_offset, ac_voltage, frequency)
                        current_run_file = create_run_file(run_number, current_dc_offset, True)
                        recording = True
                        run_number += 1
                    elif recording and abs(temperatures[-1]-temp_max) <= 0.01:
                        recording = False
                        set_oscillator_parameters(lock_in_address, 0.001, 0.001, frequency)
                        current_dc_offset += dc_step
                        print("DC offset set to: "+str(current_dc_offset))
                trend_counter = 0
            else:
                trend_counter += 1

        time.sleep(0.5)

#Paths and settings from settings.txt file
settings_file = r'C:\Users\bpkro\OneDrive\Escritorio\Chi-2\settings.txt'
settings = read_config(settings_file)

input_file=r'C:\Users\bpkro\OneDrive\Escritorio\Chi-2\log.csv'
output_file=r'C:\Users\bpkro\OneDrive\Escritorio\Chi-2\Full_Data.csv'
output_folder=r'C:\Users\bpkro\OneDrive\Escritorio\Chi-2\Run Files'

temp_min = float(settings['temp_min'])
temp_max = float(settings['temp_max'])
ac_voltage = float(settings['ac_voltage'])
dc_offset = float(settings['dc_offset'])
dc_step = float(settings['dc_step'])
frequency = float(settings['frequency'])

# GPIB address of the lock-in amplifier
lock_in_address = 'GPIB0::13::INSTR'
start_time = datetime.now()  # Record the start time of the script
tolerance = float(settings['warming_ramp_rate'])/60*0.2  #Tolerance for temperature change(20% of smallest expected slope)


if __name__ == "__main__":
    #Create Full Data Log:
    create_run_file(0,0,False)
    #Creat run log folder
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    #Data Logging and Plotting
    live_readout()
