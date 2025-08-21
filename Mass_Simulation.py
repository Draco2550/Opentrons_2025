import subprocess
import os
from Randomized_RTP import find_parameters, print_param_details
import pprint

"""
This script automates the testing of Opentrons protocol files by running the 
`opentrons_simulate` command on each Python script in a specified directory. 
It captures the output, reports successes or failures, and for failed protocols, 
it extracts and displays the parameter combination that caused the error.
"""

# --- Configuration ---
# The folder containing the generated protocol files to be tested.
target_directory = "generated_protocols"
# Get the absolute path to the target directory, making the script runnable from any location.
current_script_dir = os.path.dirname(__file__)
absolute_protocols_path = os.path.join(current_script_dir, target_directory)

# --- User Preferences ---
# Ask the user if they want to see the output for successful simulations.
show_all_results = input("\nPlease enter (y/n) if you would like to see successful results: ").lower().strip() == 'y'
# If true it will show both successful and failed protocols, default only shows errors.


# --- Initialization ---
# Counters and lists to track the results of the simulation run.
failure_count = 0
failed_file_names = []

# --- Main Simulation Loop ---
# Iterate through every file in the target directory.
for filename in os.listdir(absolute_protocols_path):
    try:
        # Process only Python files, excluding '__init__.py'.
        if filename.endswith('.py') and filename != '__init__.py':
            # Execute the 'opentrons_simulate' command for the current file.
            result = subprocess.run(
                ["opentrons_simulate", filename],
                cwd=absolute_protocols_path,  # Run the command from within the target directory.
                capture_output=True,          # Capture the stdout and stderr streams.
                text=True,                    # Decode stdout/stderr as text (instead of bytes).
                check=True                    # If the command returns a non-zero exit code (fails), raise an exception.
            )
            
            # This part will only run if the simulation is successful (because check=True did not raise an error).
            if show_all_results:
                print("--- Simulation Successful ---")
                print(f"{filename}\n")
                print(f"{result.stdout}\n\n\n")

    except subprocess.CalledProcessError as e:
        # This block catches errors when the simulation itself fails (e.g., a bug in the protocol).
        # The actual Opentrons error message is in stderr.
        print("\n--- Simulator Error Output (stderr) ---")
        print(f"{filename}\n")
        print(f"{e.stderr}\n\n")
        
        # For the failed file, find and print its parameters for easier debugging.
        current_protocol_info = find_parameters(filename, absolute_protocols_path)
        print_param_details(current_protocol_info)
        
        # Record the failure.
        failure_count += 1
        failed_file_names.append(filename)
        
    except FileNotFoundError:
        # This runs if the 'opentrons_simulate' command itself isn't found in the system's PATH.
        print("Error: 'opentrons_simulate' command not found.")
        print("Is the Opentrons software installed and in your system's PATH?")
        break # Exit the loop as no further simulations can be run.

# --- Final Report ---
# Print the total number of failures.
print(f"\nNumber of failures: {failure_count}")

# Ask the user if they want to see the list of failed files.
view_failed_files = input("Would you like to see which files failed in an ordered list? (y/n): ").lower().strip() == 'y'
if view_failed_files:

    def get_numeric_part(filename):
        """
        Extracts the leading integer from a filename for numerical sorting.
        
        For example, from '12_protocol.py', it returns 12.
        
        Args:
            filename (str): The filename to parse.
            
        Returns:
            int: The extracted number, or -1 if no number is found.
        """
        try:
            # Split the filename by '_' and convert the first part to an integer.
            return int(filename.split('_')[0])
        except (ValueError, IndexError):
            # If splitting or conversion fails (e.g., for '.DS_Store'),
            # return -1 to place it at the beginning of the sorted list.
            return -1

    # Sort the list of failed files numerically based on their prefix.
    failed_file_names.sort(key=get_numeric_part)

    # Pretty-print the sorted list of failed files.
    pprint.pprint(failed_file_names)
