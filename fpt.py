import serial.tools.list_ports as port_list
import serial
import time


def probe_autohome():
    serial_instance.write("00-".encode('utf-8'))

    # Wait for Arduino's response
    while True:
        if serial_instance.in_waiting:
            response = serial_instance.readline().decode('utf-8').strip()
            print("Response from Arduino:", response)
            if response == "11":
                print("Home reached.")
                return
            else:
                print("Waiting for Autohome")
        time.sleep(1)  # Wait for 1 second before checking again


def send_coordinates_to_arduino(xa_value, ya_value, za_value, xb_value, yb_value, zb_value):
    # Prepare the data string in the required format
    data_string = f"01-{xa_value},{ya_value},{za_value}:{xb_value},{yb_value},{zb_value}:"

    print(f"Sent data to Arduino: {data_string}")
    # Encode the string as bytes for serial communication

    encoded_data = data_string.encode('utf-8')

    # Send the data to Arduino through the serial port
    serial_instance.write(encoded_data)

    # Wait for acknowledgment
    ack = wait_for_acknowledgment()

    return ack


def send_coordinates(coord1_values, coord2_values, measurement_info, min_range, max_range, c_name):
    # Check if xa is greater than xb, and swap the coordinates if necessary
    if coord1_values[0] > coord2_values[0]:
        coord1_values, coord2_values = coord2_values, coord1_values
        if measurement_info.lower() == "voltage":
            command_code = "04-20:"
        elif measurement_info.lower() == "current":
            command_code = "04-21:"
        elif measurement_info.lower() == "impedance":
            command_code = "04-22:"

        else:
            print("Error: Invalid measurement info:", measurement_info)
            return False  # Indicate processing failure
    else:
        if measurement_info.lower() == "voltage":
            command_code = "03-20:"
        elif measurement_info.lower() == "current":
            command_code = "03-21:"
        elif measurement_info.lower() == "impedance":
            command_code = "03-22:"

        else:
            print("Error: Invalid measurement info:", measurement_info)
            return False  # Indicate processing failure

    serial_instance.write(command_code.encode('utf-8'))

    # Multiply the coordinates by 25
    multiplied_coord1_values = [int(value * 25) for value in coord1_values]
    multiplied_coord2_values = [int(value * 25) for value in coord2_values]
    xa_value, ya_value, za_value = multiplied_coord1_values
    xb_value, yb_value, zb_value = multiplied_coord2_values

    # Send x and y coordinates
    ack = send_coordinates_to_arduino(xa_value, ya_value, 0, xb_value, yb_value, 0)
    time.sleep(2)

    # Send x, y, and z coordinates
    ack = send_coordinates_to_arduino(xa_value, ya_value, za_value, xb_value, yb_value, zb_value)

    time.sleep(2)

    # Send x and y coordinates
    ack = send_coordinates_to_arduino(xa_value, ya_value, 0, xb_value, yb_value, 0)
    time.sleep(2)

    return ack


def wait_for_acknowledgment():
    # Wait for acknowledgment
    while True:
        if serial_instance.in_waiting:
            ack = serial_instance.readline().decode('utf-8').strip()
            print(ack)
            if ack == "12":
                print("Received acknowledgment:", ack)
                return ack
            elif ack == "13":
                print("Error: Process disturbed")
                raise SystemExit


def process_data(data):
    components = data.strip().split(':')
    if len(components) != 6:
        print("Error: Data format incorrect. Expected 6 components, found", len(components))
        return False  # Indicate processing failure
    else:
        # Extract individual components
        c_name, measurement_info, coord1, coord2, max_range, min_range = components
        valid_measurement_info = {"voltage", "current", "impedance"}
        if measurement_info.lower() not in valid_measurement_info:
            print("Error: Invalid measurement info:", measurement_info)
            return False

        # Convert coordinate values to floats
        try:
            coord1_values = [round(float(value), 2) for value in coord1.split(',')]
            coord2_values = [round(float(value), 2) for value in coord2.split(',')]
        except ValueError:
            print("Error: Unable to convert coordinate values to float.")
            return False  # Indicate processing failure

        # Check if each coordinate pair contains exactly three values
        if len(coord1_values) != 3 or len(coord2_values) != 3:
            print("Error: Each coordinate pair must contain exactly three values.")
            return False  # Indicate processing failure

        print("Component Name:", c_name)
        print("Measurement Info:", measurement_info)
        print("Coordinates 1:", coord1_values)
        print("Coordinates 2:", coord2_values)
        print("Max Range:", max_range)
        print("Min Range:", min_range)

        # Send coordinates to Arduino with acknowledgment
        ack = send_coordinates(coord1_values, coord2_values, measurement_info, min_range, max_range, c_name)
        if ack == "13":
            print("Error: Process disturbed")
            raise SystemExit  # Exit the program if acknowledgment "13" is received

        return ack  # Indicate successful processing


# Find available serial ports
ports = port_list.comports()
portsList = []

for one in ports:
    portsList.append(str(one))
    print(str(one))

# Select COM port for Arduino
com = input("Select Com Port for Arduino #: ")

# Open serial connection with selected port
use = "COM" + com
serial_instance = serial.Serial(use, 9600)  # Initialize serial instance with the selected COM port

# Wait for serial connection to be established
time.sleep(2)
probe_autohome()
time.sleep(2)

send_coordinates_to_arduino(0, 0, 0, 0, 0, 0)
time.sleep(5)

file_path = "D:\sample_datamove.txt"  # Path to your text file

try:
    with open(file_path, 'r') as file:
        file_empty = True  # Flag to check if the file is empty
        error_occurred = False  # Flag to track if an error occurred

        for line in file:
            if error_occurred:
                break  # Stop processing if an error occurred
            file_empty = False  # The file is not empty if we are iterating over lines
            line = ' '.join(line.split())  # Remove leading/trailing whitespace
            if not line:  # Check if line is empty
                break  # Exit loop if empty line is encountered
            elif '//' in line:  # Check for line ending indicator '//'
                ack = process_data(line.split('//')[0])
                if ack == "13":
                    error_occurred = True
                    print("Error: Process disturbed")
                    exit()
                elif not ack:
                    print("Error: Invalid measurement info encountered. Halting processing.")
                    break
        if file_empty:
            print("Error: File is empty")
            file.close()
except FileNotFoundError:
    print("Error: File not found at path:", file_path)

# Close serial communication
serial_instance.close()
print("Serial connection closed.")