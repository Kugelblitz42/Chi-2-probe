import os
import time
import pandas as pd
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class FileHandler(FileSystemEventHandler):
    def __init__(self, file_path, csv_path):
        self.file_path = file_path
        self.csv_path = csv_path

    def on_modified(self, event):
        if event.src_path == self.file_path:
            self.process_file()

    def process_file(self):
        try:
            with open(self.file_path, 'r') as file:
                lines = file.readlines()
                
                # Find the start of the [Data] section
                data_start_idx = lines.index("[Data]\n") + 1
                
                # Get the header and data lines
                headers = lines[data_start_idx].strip().split(',')
                data_lines = lines[data_start_idx + 1:]
                
                # Create a DataFrame from the data lines
                data = [line.strip().split(',') for line in data_lines if len(line.strip().split(',')) == len(headers)]
                df = pd.DataFrame(data, columns=headers)
                
                # Extracting Time and Temperature (K) columns
                df['Time'] = pd.to_numeric(df['Time'])
                df['Temperature (K)'] = pd.to_numeric(df['Temperature (K)'])
                
                # Get the most recent entry
                latest_entry = df.iloc[-1]
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                temperature = latest_entry['Temperature (K)']
                
                # Append the data to the CSV file
                self.append_to_csv(current_time, temperature)
        except Exception as e:
            print(f"Error processing file: {e}")

    def append_to_csv(self, current_time, temperature):
        try:
            df = pd.DataFrame([[current_time, temperature]], columns=["Timestamp", "Temperature (K)"])
            if not os.path.isfile(self.csv_path):
                df.to_csv(self.csv_path, index=False)
            else:
                df.to_csv(self.csv_path, mode='a', header=False, index=False)
        except Exception as e:
            print(f"Error writing to CSV: {e}")

if __name__ == "__main__":
    # Path to the shared file being updated every second
    shared_file_path = "/path/to/shared/file.txt"
    # Path to the CSV file to store the time and temperature data
    csv_file_path = "/path/to/output/temperature_data.csv"
    
    event_handler = FileHandler(shared_file_path, csv_file_path)
    observer = Observer()
    observer.schedule(event_handler, path=os.path.dirname(shared_file_path), recursive=False)
    
    observer.start()
    print(f"Monitoring {shared_file_path} for changes...")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()

    observer.join()