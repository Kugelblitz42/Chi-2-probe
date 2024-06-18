import pandas as pd
import time
import os

# Paths to the CSV file and the processed file
source_file = r'\\SourceComputer\SharedFolder\data.csv'  # Adjust with your actual network path
processed_file = r'C:\Path\To\Destination\processed_data.csv'  # Path for the processed CSV

# Track the last read position
last_position = 0

def read_incremental(file_path, start_position):
    with open(file_path, 'r') as f:
        f.seek(start_position)
        new_data = f.read()
        new_position = f.tell()
    return new_data, new_position

def process_data(new_data):
    lines = new_data.splitlines()
    data_started = False
    data = []

    for line in lines:
        if data_started:
            data.append(line.split(','))
        elif '[Data]' in line:
            data_started = True

    if not data:
        return None

    # Create DataFrame from the new data
    columns = ["Time", "Temperature (K)", "Field (Oe)", "Helium Level (%)", "Impedance Heater",
               "Driver2 Select", "Helium Meter (V)", "High Res. Current (V)", "Low Res. Current (V)",
               "TC gauge (V)", "Not Assigned (V)", "Long. SQUID (V)", "Trans. SQUID (V)",
               "External Input (V)", "Bridge 1 (K)", "Bridge 2 (K)", "Bridge 3 (K)", "Bridge 4 (K)",
               "Driver 1 (mW/ohm)", "Driver 2 (mW/ohm)", "", ""]
    
    new_df = pd.DataFrame(data, columns=columns)

    # Extract the timestamp and temperature columns
    extracted_data = new_df[['Time', 'Temperature (K)']]
    return extracted_data

while True:
    try:
        # Read new data from the source file
        new_data, new_position = read_incremental(source_file, last_position)

        if new_data:
            # Process the new data
            extracted_data = process_data(new_data)

            if extracted_data is not None:
                # Append the extracted data to the processed file
                if not os.path.isfile(processed_file):
                    extracted_data.to_csv(processed_file, index=False)
                else:
                    extracted_data.to_csv(processed_file, mode='a', header=False, index=False)
                
                print(f"Processed and saved at {time.ctime()}")

        # Update the last read position
        last_position = new_position

    except Exception as e:
        print(f"Error processing file: {e}")

    time.sleep(1)  # Wait for 1 second before next read
