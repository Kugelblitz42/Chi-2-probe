import shutil
import time

# Paths to source and destination files
source_file = r'\\SourceComputer\SharedFolder\data.csv'
destination_file = r'C:\Path\To\Destination\data.csv'

while True:
    try:
        shutil.copy(source_file, destination_file)
        print(f"Copied at {time.ctime()}")
    except Exception as e:
        print(f"Error: {e}")
    time.sleep(1)  # Wait for 1 second before next copy
