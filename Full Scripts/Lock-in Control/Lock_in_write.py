import pyvisa
import os

def read_settings(file_path):
    settings = {}
    with open(file_path, 'r') as file:
        for line in file:
            line = line.strip()  # Remove leading and trailing whitespace
            if line and not line.startswith('#'):  # Ignore empty lines and comments
                if '=' in line:
                    key, value = line.split('=', 1)  # Split only on the first '='
                    key = key.strip()
                    value = value.strip()
                    if value:  # Only add to settings if a value is provided
                        settings[key] = eval(value)
    return settings

def find_file(file_name, search_path):
    # Walk through the directory 
    for root, dirs, files in os.walk(search_path):
        # Check if the file name is in the list of files in the current folder
        if file_name in files:
            # Return the full path to the file
            return os.path.join(root, file_name)  
    # If the file is not found, return None or handle as needed
    return None

def set_oscillator_parameters(address, dc_offset, ac_amplitude, frequency, harmonic, sensitivity):
    """
    Set the internal oscillator parameters for the SRS865A lock-in amplifier.
    
    Parameters:
    address (str): GPIB address of the lock-in amplifier.
    dc_offset (float): DC offset voltage in volts.
    ac_amplitude (float): AC amplitude voltage in volts.
    frequency (float): Frequency in hertz.
    harmonic (int): Harmonic number.
    sensitivity (float): Sensitivity in volts.
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
        
        # Set harmonic
        lockin.write(f'HARM {harmonic}')
        print(f'Lock into to Harmonic #{harmonic}')
        
        # Set sensitivity
        lockin.write(f'SCAL {sensitivity}')
        print(f'Set sensitivity to {sensitivity} V')
        
    except pyvisa.VisaIOError as e:
        print(f"An error occurred: {e}")
    finally:
        # Close the connection to the lock-in amplifier
        lockin.close()

if __name__ == "__main__":
    # Read settings from the text file
    settings_file = os.path.abspath(find_file('lock_in_settings.txt',__file__))
    settings = read_settings(settings_file)
    
    # Set the oscillator parameters on the lock-in amplifier
    set_oscillator_parameters(
        address=settings['address'],
        dc_offset=settings['dc_offset'],
        ac_amplitude=settings['ac_amplitude'],
        frequency=settings['frequency'],
        harmonic=settings['harmonic'],
        sensitivity=settings['sensitivity']
    )
