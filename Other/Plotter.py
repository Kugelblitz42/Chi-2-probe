import os
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

def list_files(folder_path):
    files = [f for f in os.listdir(folder_path) if f.startswith("Run_") and f.endswith(".csv")]
    # Sort files by the run number extracted from the filename
    files.sort(key=lambda f: int(f.split('_')[1].split('.')[0]))
    return files

def extract_dc_offset(file_path):
    with open(file_path, 'r') as file:
        for line in file:
            if "DC_offset" in line:
                dc_offset = float(line.split("DC_offset:")[1].strip().replace("V", ""))
                return dc_offset
    return None

def plot_runs(file_paths, plot_option):
    num_runs = len(file_paths)
    num_cols = 1
    num_rows = num_runs
    
    fig, axs = plt.subplots(num_rows, num_cols, figsize=(10, 5 * num_rows))
    
    # Ensure axs is always an array, even if there is only one subplot
    if num_runs == 1:
        axs = np.array([axs])

    for i, file_path in enumerate(file_paths):
        try:
            dc_offset = extract_dc_offset(file_path)
            data = pd.read_csv(file_path, skiprows=4)  # Skip the first 4 lines of metadata
            
            if 'Temperature (K)' not in data.columns or 'Vx' not in data.columns or 'Vy' not in data.columns:
                raise ValueError("The file does not have the required columns: 'Temperature (K)', 'Vx', 'Vy'.")

            ax = axs[i]
            
            if plot_option == 'Vx':
                ax.scatter(data['Temperature (K)'], data['Vx'], label=f'Vx vs Temperature (Run {i+1})', alpha=0.5, c='green', marker='.')
                ax.set_ylabel('Vx')
            elif plot_option == 'Vy':
                ax.scatter(data['Temperature (K)'], data['Vy'], label=f'Vy vs Temperature (Run {i+1})', alpha=0.5, c='red', marker='.')
                ax.set_ylabel('Vy')
            elif plot_option == 'Magnitude':
                magnitude = np.sqrt(data['Vx']**2 + data['Vy']**2)
                ax.scatter(data['Temperature (K)'], magnitude, label=f'Magnitude vs Temperature (Run {i+1})', alpha=0.5, c='blue', marker='.')
                ax.set_ylabel('Magnitude')

            ax.set_xlabel('Temperature (K)')
            ax.set_title(f'Data from {os.path.basename(file_path)} (DC offset: {dc_offset}V)')
        except Exception as e:
            print(f"Error plotting file {file_path}: {e}")
            continue
    
    plt.tight_layout()
    plt.show()

def main():
    folder_path = input("Enter the folder path containing the data files: ").strip()
    
    while True:
        try:
            files = list_files(folder_path)
            if not files:
                raise ValueError("No files found in the specified folder.")
            
            print("Available files:")
            for i, file in enumerate(files):
                print(f"{i + 1}. {file}")

            file_indices = input("Enter the numbers of the files you want to plot (comma separated): ")
            file_indices = [int(x) - 1 for x in file_indices.split(",")]

            plot_option = input("Enter the plot option (Vx, Vy, Magnitude): ").strip()

            valid_plots = {'Vx', 'Vy', 'Magnitude'}
            if plot_option not in valid_plots:
                raise ValueError("Invalid plot option provided.")

            selected_files = [files[index] for index in file_indices if 0 <= index < len(files)]

            if not selected_files:
                raise ValueError("No valid files selected.")

            plot_runs([os.path.join(folder_path, file) for file in selected_files], plot_option)

        except Exception as e:
            print(f"Error: {e}")
            retry = input("Would you like to try again? (yes/no): ").strip().lower()
            if retry != 'yes':
                break
        else:
            another_plot = input("Would you like to plot another set of runs? (yes/no): ").strip().lower()
            if another_plot != 'yes':
                break

if __name__ == "__main__":
    main()
