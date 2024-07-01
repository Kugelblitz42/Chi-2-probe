import pyvisa

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

if __name__ == "__main__":
    # Define the parameters you want to set
    address = 'GPIB0::13::INSTR'  # Replace with your actual GPIB address
    dc_offset = 0.5  # Example DC offset in Volts
    ac_amplitude = 1  # Example AC amplitude in Volts
    frequency = 808e3  # Example frequency in Hz

    # Set the oscillator parameters on the lock-in amplifier

    set_oscillator_parameters(address, dc_offset, ac_amplitude, frequency)



