import pyvisa
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.animation import FuncAnimation
import time
import csv

def read_lockin_data(address):
    """
    Read the X and Y data from the SRS865A lock-in amplifier.
    
    Parameters:
    address (str): GPIB address of the lock-in amplifier.
    
    Returns:
    tuple: (x, y) where x is the in-phase component and y is the out-of-phase component.
    """
    rm = pyvisa.ResourceManager()
    lockin = rm.open_resource(address)
    
    try:
        x = float(lockin.query('OUTP? 0'))  # Query X (in-phase)
        y = float(lockin.query('OUTP? 1'))  # Query Y (out-of-phase)
        return x, y
    except pyvisa.VisaIOError as e:
        print(f"An error occurred: {e}")
        return None, None
    finally:
        lockin.close()

def update(frame, address, times, x_vals, y_vals, mag_vals, line1, line2, line3, start_time, csv_writer):
    current_time = time.time() - start_time
    x, y = read_lockin_data(address)
    
    if x is not None and y is not None:
        times.append(current_time)
        x_vals.append(x)
        y_vals.append(y)
        mag_vals.append(np.sqrt(x**2 + y**2))
        
        # Write data to CSV file
        csv_writer.writerow([current_time, x, y, np.sqrt(x**2 + y**2)])

        # Limit the lists to the last 1000 points for performance
        times = times[-1000:]
        x_vals = x_vals[-1000:]
        y_vals = y_vals[-1000:]
        mag_vals = mag_vals[-1000:]

        # Update data for each line
        line1.set_data(times, x_vals)
        line2.set_data(times, y_vals)
        line3.set_data(times, mag_vals)

        # Adjust the view limits
        ax1.relim()
        ax1.autoscale_view()

        ax2.relim()
        ax2.autoscale_view()

        ax3.relim()
        ax3.autoscale_view()

    return line1, line2, line3

if __name__ == "__main__":
    # GPIB address of the lock-in amplifier
    address = 'GPIB0::13::INSTR'  # Replace with your actual GPIB address
    
    # Lists to hold time, X, Y, and magnitude values
    times = []
    x_vals = []
    y_vals = []
    mag_vals = []

    # Setup the figure and axes
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(10, 8))
    fig.suptitle('Real-time Lock-in Amplifier Data')

    # Line objects for updating the plots
    line1, = ax1.plot([], [], 'r-', label='X (in-phase)')
    line2, = ax2.plot([], [], 'g-', label='Y (out-of-phase)')
    line3, = ax3.plot([], [], 'b-', label='Magnitude')

    ax1.set_ylabel('X (Volts)')
    ax2.set_ylabel('Y (Volts)')
    ax3.set_ylabel('Magnitude (Volts)')
    ax3.set_xlabel('Time (s)')

    ax1.legend()
    ax2.legend()
    ax3.legend()

    # Open CSV file for writing
    csv_file = open('lockin_data.csv', mode='w', newline='')
    csv_writer = csv.writer(csv_file)
    # Write the header row
    csv_writer.writerow(['Time (s)', 'X (V)', 'Y (V)', 'Magnitude (V)'])

    # Start time for measuring elapsed time
    start_time = time.time()

    # Create an animation object that updates the plot
    ani = FuncAnimation(fig, update, fargs=(address, times, x_vals, y_vals, mag_vals, line1, line2, line3, start_time, csv_writer), interval=500)

    plt.tight_layout()
    plt.show()

    # Close the CSV file when done
    csv_file.close()
