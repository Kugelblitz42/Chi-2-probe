import pandas as pd
import time
import os

# Paths to source and destination files, #the r keyword allows \ and \\
# to be part of the string without being an escape character
source_file = r'\\SourceComputer\SharedFolder\data.csv'
processed_file = r'C:\Path\To\Destination\data.csv'

#To not read the file every iteration we will keep track of the last read
#position

last_position=0

def read_incremental(file_path, start_position):
    with open(file_path, 'r') as log:
        log.seek(start_position)
        new_data = log.read()
        new_position = log.tell()
    return new_data, new_position

while True:
    try:
        # Read new data from the source file
        new_data, new_position = read_incremental(source_file, last_position)

        if new_data:
            # Convert the new data into a DataFrame
            new_lines = new_data.splitlines()
            new_df = pd.DataFrame([line.split(',') for line in new_lines[1:]], columns=new_lines[0].split(','))

            # Extract the timestamp and temperature columns
            # Adjust column names as per your actual CSV file
            extracted_data = new_df[['Timestamp', 'Temperature']]

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
