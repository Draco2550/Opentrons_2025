import subprocess
import os

target_directory = "generated_protocols"
current_script_dir = os.path.dirname(__file__)
absolute_protocols_path = os.path.join(current_script_dir, target_directory)
show_all_results = input("\nPlease enter (y/n) if you would like to successful results: ").lower().strip() == 'y'
# If true it will show both successful and failed protocols, default only shows errors.

failure_count = 0
failed_file_names = []

for filename in os.listdir(absolute_protocols_path):
    try:
        result = subprocess.run(
            ["opentrons_simulate", filename],
            cwd= absolute_protocols_path,
            capture_output=True,
            text=True,
            check=True  
        )
        if show_all_results == True:
            # This part will only run if the simulation is successful
            print("--- Simulation Successful ---")
            print(filename + "\n")
            print(result.stdout + "\n\n\n")

    except subprocess.CalledProcessError as e:
        # The actual Opentrons error message is in stderr
        print("\n--- Simulator Error Output (stderr) ---")
        print(filename + "\n")
        print(e.stderr + "\n\n\n")
        failure_count += 1
        failed_file_names.append(filename)

    except FileNotFoundError:
        # This runs if the opentrons_simulate command itself isn't found
        print("Error: 'opentrons_simulate' command not found.")
        print("Is the Opentrons software installed and in your system's PATH?")


print(f"\nNumber of failures: {failure_count}")
view_failed_files = input("Would you like to see which files failed in an ordered list? (y/n): ").lower().strip() == 'y'
if view_failed_files == True:
    
    def get_numeric_part(filename):
        try:
            
            return int(filename.split('_')[0])
        except (ValueError, IndexError):
            # If it's not a number (like '.DS_Store'), place it at the beginning
            return -1

        # Sort the list using the function as the key
    failed_file_names.sort(key=get_numeric_part)

    print(failed_file_names)