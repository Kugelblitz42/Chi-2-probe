import pyvisa
import matplotlib.pyplot as plt
import numpy as np
import time
import csv
import os
from datetime import datetime
import pandas as pd
from scipy.signal import find_peaks, peak_prominences

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
def create_run_file(run_number, dc_offset, amplitude, frequency, run, output_folder, output_file):
    if run==True:
        filename = os.path.join(output_folder, f'Run_{run_number}.csv')
    else:
        filename = output_file
    with open(filename, 'w+', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["-----------------------------------------------------------"])
        writer.writerow([datetime.now().strftime("%B %d %Y %I:%M%p")])
        writer.writerow(["AC amplitude: "+str(amplitude)+" V. Frequency: "+str(frequency)+" Hz."])
        writer.writerow(["Run: "+ str(run_number) +". DC offset: "+str(dc_offset)+ " V."])
        writer.writerow(['Peak detected @ '+' K with prominence '+' V'])
        writer.writerow(["-----------------------------------------------------------"])
        writer.writerow(['Timestamp', 'Temperature (K)', 'Vx', 'Vy'])
    return filename

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
            except ValueError:
                continue
    return data, last_position

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

#Set Lock-in settings
def set_oscillator_parameters(address, dc_offset, ac_amplitude, frequency):
    rm = pyvisa.ResourceManager()
    # Open a connection to the SRS865A lock-in amplifier
    lockin = rm.open_resource(address)
    try:
        print('-----------------LOCK-IN-----------------')
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
        print('-----------------------------------------')
        lockin.close()

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
 
#Returns prominence of most prominent peak 
def find_most_prominent_peak(file_path, temperature_range):
    try:
        data = pd.read_csv(file_path, skiprows=5)  # Skip the first 6 rows of the header
    except pd.errors.ParserError as e:
        print(f"Error reading CSV file: {e}")
        return None, None
    b=np.polyfit(data['Temperature (K)'], data['Vx'], 0)
    data['Vx'] = data['Vx'] - b
    b=np.polyfit(data['Temperature (K)'], data['Vy'], 0)
    data['Vy'] = data['Vy'] - b

    #Record and append magnitudes to data frame
    magnitudes = np.sqrt(data['Vx']**2 + data['Vy']**2)
    data['Magnitude (V)'] = magnitudes
    
    base = data[(data['Temperature (K)'] >= ) & (data['Temperature (K)'] <= 6)]
    std_dev = np.std(base['Magnitude (V)'])
    offset=np.polyfit(base['Temperature (K)'], base['Magnitude (V)'], 0)[0]

    # Find peaks in the magnitudes data
    height_min=offset+1.2*std_dev # 1.2 std deviations is roughly 90% of data
    peaks, _ = find_peaks(magnitudes, height=height_min) 
    prominences = peak_prominences(magnitudes, peaks)[0]

    temperature = data['Temperature (K)'].values#numpy array
    # Assign 1 if there is a peak at the data point
    arr = [[0] * len(temperature), [0] * len(temperature)]
    p_count = 0
    for t in range(len(temperature)):
        if t in peaks:
            arr[0][t] = 1
            arr[1][t] = prominences[p_count]
            p_count += 1
        else:
            arr[0][t] = 0
            arr[1][t] = 0
    data['Peak?'] = arr[0]
    data['Prominences (V)'] = arr[1]

    data = data[(data['Temperature (K)'] >= temperature_range[0]) & (data['Temperature (K)'] <= temperature_range[1])]
    if data.empty:
        print("No data in the specified temperature range.")
        return None, None
    
    # Extract temperature and prominences after limiting the data
    temperature = data['Temperature (K)'].values
    magnitudes = data['Magnitude (V)'].values
    prominences = data['Prominences (V)'].values

    # Extract peaks in the limited data
    peaks = np.where(data['Peak?'] == 1)[0]

    # Get the position and prominence of the most prominent peak
    most_prominent_peak_idx = np.argmax(prominences)
    peak_position = temperature[most_prominent_peak_idx]
    peak_prominence = prominences[most_prominent_peak_idx]

    if len(peaks) == 0:
        print("No peaks found in range")
        return None, None

    print('----------------------------------------------')
    print('Peak detected @ '+ str("{:.3e}".format(peak_position))+' with prominence '+str("{:.3e}".format(peak_prominence))+' V')
    print('----------------------------------------------')
    return peak_position, peak_prominence

#Sets the dc_offset using previous peak prominence data
def set_dc_offset(dc_range, setting, current_dc_offset):
    if setting== '0': #Initialize settings
        current_dc_offset = dc_range[0]+(dc_range[1] - dc_range[0])/2
        setting = '+'
    elif setting == '+':
        current_dc_offset += (dc_range[1] - dc_range[0])/2
        setting = '-'
    elif setting=='-':
        current_dc_offset -= (dc_range[1] - dc_range[0])
        setting = 'Change_range'    
    return current_dc_offset, setting

# Records live data to file and plots newly added data
def live_readout(dc_range, lock_in_address, input_file, output_file, output_folder, temp_min, temp_max, ac_voltage, frequency, tolerance, peak_range, start_time):
    timestamps = []
    temperatures = []
    x2_vals = []
    y2_vals = []
    voltage_readings = []
    peak_data = []

    fig, ((ax1, ax4), (ax2, ax5), (ax3, ax6)) = plt.subplots(3, 2, figsize=(10, 7))
    fig.suptitle('Live Data Readout')
    line1, = ax1.plot([], [], '.-', color='coral')
    line2, = ax2.plot([], [], '.-', color='mediumseagreen')
    line3, = ax3.plot([], [], '.-', color='steelblue')
    line4, = ax4.plot([], [], 'm', marker='.', ls="")
    line5, = ax5.plot([], [], color='mediumseagreen', marker='.', ls="")
    line6, = ax6.plot([], [], color='steelblue', marker='.', ls="")
    ax1.set_ylabel('Temperature (K)')
    ax2.set_ylabel('In-phase (V)')
    ax3.set_xlabel('Time (s)')
    ax3.set_ylabel('Out-of-phase (V)')
    #ax4.title.set_text('Magnitude (V)')
    #ax5.title.set_text('In-phase (V)')
    ax6.set_xlabel('Temperature (K)')
    #ax6.title.set_text('Out-of-phase (V)')
    fig.show()

    #local variables
    last_position = 0
    plot_counter = 0
    trend_counter = 0
    current_dc_offset = 0
    run_number = 1
    recording = False
    current_run_file = None
    grid_state = '0'
    trend = 'Not enough data'

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

            if plot_counter == 0:#Change if plotting is too resource intensive
                line1.set_data(time_elapsed, temperatures)#temperatures
                line2.set_data(time_elapsed, x2_vals)#Chi-2 in phase vs time
                line3.set_data(time_elapsed, y2_vals)#Chi-2 out of phase vs time
                R=np.sqrt(np.array(x2_vals)**2 + np.array(y2_vals)**2)
                line4.set_data(temperatures, R)#R
                line5.set_data(temperatures, x2_vals)#'' vs temperature
                line6.set_data(temperatures, y2_vals)#'' vs temperature

                ax1.relim()
                ax1.autoscale_view()
                ax1.set_title(f'Current Temperature: {"{:.2f}".format(temperatures[-1])} K')
                #ax1.set_xticks([])

                ax2.relim()
                ax2.autoscale_view()
                ax2.set_title(f'X: {"{:.3e}".format(x2_vals[-1])} V')
                #ax2.set_xticks([])

                ax3.relim()
                ax3.autoscale_view()
                ax3.set_title(f'Y: {"{:.3e}".format(x2_vals[-1])} V')

                ax4.relim()
                ax4.autoscale_view()
                #ax4.set_xticks([])
                ax4.set_title(f'R: {"{:.3e}".format(R[-1])} V')

                ax5.relim()
                ax5.autoscale_view()
                #ax5.set_xticks([])

                ax6.relim()
                ax6.autoscale_view()
                plt.tight_layout()
                fig.canvas.draw()
                fig.canvas.flush_events()
                plot_counter = 0
            else:
                plot_counter += 1

            if trend_counter == 10:
                previous_trend = trend
                trend = detect_trend(temperatures, tolerance)
                if trend != previous_trend:
                    print(trend+': '+str(datetime.now()))
                if trend == "steady":
                    if not recording and abs(temperatures[-1]-temp_min)<=0.2:
                        #Set offset value
                        current_dc_offset, grid_state =set_dc_offset(dc_range, grid_state, current_dc_offset)
                        set_oscillator_parameters(lock_in_address, current_dc_offset, ac_voltage, frequency)
                        #Recording values and conditions
                        current_run_file = create_run_file(run_number, current_dc_offset, ac_voltage, frequency, True, output_folder, output_file)
                        recording = True
                        run_number += 1
                    elif recording and abs(temperatures[-1]-temp_max) <= 0.2:
                        #Ends recording and sets cooling lock-in parameters
                        recording = False
                        set_oscillator_parameters(lock_in_address, current_dc_offset, 1e-9, frequency)#Ask Richard what would be best
                        peak_position, peak_prominence =find_most_prominent_peak(current_run_file, peak_range)
                        with open(current_run_file, 'r') as file:
                            lines = file.readlines()
                        if peak_prominence ==None:
                            peak_position = 'None'
                            peak_prominence = 'None'
                            lines[4] = 'Peak detected @ '+ str(peak_position)+' K with prominence '+str(peak_prominence)+' V'
                        else:
                            lines[4] = 'Peak detected @ '+ str("{:.3e}".format(peak_position))+' K with prominence '+str("{:.3e}".format(peak_prominence))+' V'
                        with open(current_run_file, 'w') as file:
                            file.writelines(lines)
        
                        peak_data.append((current_dc_offset, peak_prominence))
                elif trend =='cooling' and grid_state=='Change_range':
                        #Finds peak of least prominence in last range and cuts the range in half
                        prominences = [t[1] for t in peak_data[-3:]]
                        min_peak_idx = np.argmin(prominences)
                        current_dc_offset = peak_data[-3:][min_peak_idx][0]
                        peak_data.append((current_dc_offset, peak_data[-3:][min_peak_idx][1]))
                        range= dc_range[1]-dc_range[0]
                        dc_range[0] = current_dc_offset - 0.3*range
                        dc_range[1] = current_dc_offset + 0.3*range
                        grid_state = '+'                 
                trend_counter = 0
            else:
                trend_counter += 1

        time.sleep(1)

#Paths and settings from settings.txt file
settings_file = os.path.abspath(find_file('settings.txt',os.path.dirname(__file__)))
settings = read_config(settings_file)

#Read from settings file
input_file=os.path.abspath(settings['input_file'])
output_file=os.path.abspath(settings['output_file'])
output_folder=os.path.abspath(settings['output_folder'])
temp_min = float(settings['temp_min'])
temp_max = float(settings['temp_max'])
ac_voltage = float(settings['ac_voltage'])
frequency = float(settings['frequency'])
dc_range =[float(settings['dc_range_min']), float(settings['dc_range_max'])]
peak_range=[float(settings['peak_min']), float(settings['peak_max'])]

# GPIB address of the lock-in amplifier
lock_in_address = str(settings['lock_in_address'])
start_time = datetime.now()  # Record the start time of the script
tolerance = float(settings['warming_ramp_rate'])/60*0.3  #Tolerance for temperature change(30% of smallest expected slope)

if __name__ == "__main__":
    #Creat run log folder
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    #Create Full Data Log:
    create_run_file('--','--', ac_voltage, frequency, False, output_folder, output_file)
    #Data Logging and Plotting
    live_readout(dc_range, lock_in_address, input_file, output_file, output_folder, temp_min, temp_max, ac_voltage, frequency, tolerance, peak_range, start_time)
