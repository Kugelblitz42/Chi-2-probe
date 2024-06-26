import pyvisa
import matplotlib.pyplot as plt
import numpy as np
import time
import csv
from datetime import datetime, timedelta
from threading import Thread, Lock
import queue

class DataCollector:
    def __init__(self, input_file, output_file, lock_in_address, start_time):
        self.input_file = input_file
        self.output_file = output_file
        self.lock_in_address = lock_in_address
        self.start_time = start_time
        self.running = True
        self.data_lock = Lock()
        self.data_queue = queue.Queue()
        self.timestamps = []
        self.temperatures = []
        self.x2_vals = []
        self.y2_vals = []
        self.voltage_readings = []

    def start(self):
        self.create_log_file()
        self.live_readout()

    def create_log_file(self):
        with open(self.output_file, 'w', newline='') as file:
            writer = csv.writer(file)
            current_time = self.start_time.strftime("%B %d %Y %I:%M%p")
            writer.writerow(["-----------------------------------------------------------"])
            writer.writerow([current_time])
            writer.writerow(["Entire Data from session is collected in file. No distinction between runs is made."])
            writer.writerow(["-----------------------------------------------------------"])
            writer.writerow(['Timestamp', 'Temperature (K)', 'Vx', 'Vy'])

    def get_new_temperature_lines(self, file_path, last_position, start_time):
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

    def append_to_data_log(self, timestamp, temperature, voltage_data):
        with open(self.output_file, 'a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow([timestamp, temperature, voltage_data[0], voltage_data[1]])

    def read_lockin_data(self, address):
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

    def live_readout(self):
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
                self.append_to_data_log(temp_time, temp, closest_time[1])
                self.timestamps.append(temp_time)
                self.temperatures.append(temp)
                self.x2_vals.append(closest_time[1][0])
                self.y2_vals.append(closest_time[1][1])

                # Keep only the last 2000 data points for plotting
                if len(self.timestamps) > 2000:
                    self.timestamps.pop(0)
                    self.temperatures.pop(0)
                    self.x2_vals.pop(0)
                    self.y2_vals.pop(0)

        while self.running:
            voltage_reading = self.read_lockin_data(self.lock_in_address)
            self.voltage_readings.append((datetime.now(), voltage_reading))

            new_data, last_position = self.get_new_temperature_lines(self.input_file, last_position, self.start_time)
            if new_data:
                match_readings(new_data, self.voltage_readings)

                time_elapsed = [(t - self.timestamps[0]).total_seconds() for t in self.timestamps]

                if plot_counter == 2:
                    line1.set_data(time_elapsed, self.temperatures)
                    line2.set_data(time_elapsed, self.x2_vals)
                    line3.set_data(time_elapsed, self.y2_vals)

                    ax1.set_xlim(0, max(time_elapsed) + 1)
                    ax1.set_ylim(min(self.temperatures) - 1, max(self.temperatures) + 1)
                    ax1.set_title(f'Current Temperature: {self.temperatures[-1]:.2f} K')
                    ax1.set_xticks([])

                    ax2.set_xlim(0, max(time_elapsed) + 1)
                    ax2.set_ylim(min(self.x2_vals), max(self.x2_vals))
                    ax2.set_title(f'Current Reading: {self.x2_vals[-1]:.2f} V')
                    ax2.set_xticks([])

                    ax3.set_xlim(0, max(time_elapsed) + 1)
                    ax3.set_ylim(min(self.y2_vals), max(self.y2_vals))
                    ax3.set_title(f'Current Reading: {self.y2_vals[-1]:.2f} V')

                    fig.canvas.draw()
                    fig.canvas.flush_events()
                    plot_counter = 0
                else:
                    plot_counter += 1

            time.sleep(1)

    def stop(self):
        self.running = False

# Example usage
if __name__ == "__main__":
    input_file = r'C:\Users\bpkro\OneDrive\Escritorio\Chi-2\log.csv'
    output_file = r'C:\Users\bpkro\OneDrive\Escritorio\Chi-2\Full_Data.csv'
    lock_in_address = 'GPIB0::13::INSTR'
    start_time = datetime.now()

    data_collector = DataCollector(input_file, output_file, lock_in_address, start_time)
    data_collector_thread = Thread(target=data_collector.start)
    data_collector_thread.start()

    try:
        while True:
            time.sleep(1)  # Simulate main program running
    except KeyboardInterrupt:
        data_collector.stop()
        data_collector_thread.join()
        print("Data collection stopped.")
