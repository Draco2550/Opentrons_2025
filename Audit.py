import ast
import importlib
import os

"""
This script is a comprehensive static analysis tool for a batch of Opentrons 
protocol files. It iterates through a specified directory, and for each protocol, it:
1.  Imports the script as a module to access its metadata and functions.
2.  Extracts information like author, protocol name, robot type, and API level.
3.  Analyzes the `add_parameters` function to summarize user-configurable parameters.
4.  Scans the file content to identify all loaded hardware modules.
5.  Uses Abstract Syntax Trees (AST) to find deprecated labware and check for
    potentially problematic z-height values in `.bottom()` and `.top()` calls.
6.  Prints a detailed report for each file and a final summary of all findings.
"""

# --- Data Structures and Configuration ---

class MockParameters:
    """
    A mock class that simulates the behavior of the Opentrons `Parameters` object.
    
    When a protocol's `add_parameters` function is called with an instance of this
    class, it captures the definitions of each parameter without actually
    running the full protocol context.
    """
    def __init__(self):
        """Initializes the mock object with an empty list to store parameter definitions."""
        self.added_parameters = []

    def add_bool(self, variable_name, **kwargs):
        """Captures a boolean parameter definition."""
        self.added_parameters.append({"name": variable_name, "type": "bool", **kwargs})

    def add_int(self, variable_name, **kwargs):
        """Captures an integer parameter definition."""
        self.added_parameters.append({"name": variable_name, "type": "int", **kwargs})

    def add_str(self, variable_name=None, **kwargs):
        """Captures a string parameter definition."""
        self.added_parameters.append({"name": variable_name, "type": "str", **kwargs})

    def add_float(self, variable_name, **kwargs):
        """Captures a float parameter definition."""
        self.added_parameters.append({"name": variable_name, "type": "float", **kwargs})

    def add_csv_file(self, variable_name, **kwargs):
        """Captures a CSV file parameter definition."""
        self.added_parameters.append({"name": variable_name, "type": "csv", **kwargs})


# A map of raw search strings to their standardized, human-readable module names.
MODULE_SEARCH_MAP = {
    "NYI": "Absorbance Plate Reader Module",
    "thermocycler module gen2": "Thermocycler Module GEN 2",
    "thermocyclerModuleV2": "Thermocycler Module GEN 2",
    "flexStackerModuleV1": "Flex Stacker Module V1",
    "magneticBlockV1": "Magnetic Block V1",
    "heaterShakerModuleV1": "Heater-Shaker Module GEN 1",
    "temperature module gen2": "Temperature Module GEN 2",
    "temperatureModuleV2" : "Temperature Module GEN 2",
    "opentrons_tough_pcr_auto_sealing_lid": "PCR Auto Sealing Lid"
}

# A counter to aggregate the total usage of each module across all protocols.
module_counter = {
    "Absorbance Plate Reader Module": 0, 
    "Thermocycler Module GEN 2": 0,
    "Flex Stacker Module V1": 0,
    "Magnetic Block V1": 0,
    "Heater-Shaker Module GEN 1": 0,
    "Temperature Module GEN 2": 0,
    "PCR Auto Sealing Lid": 0,
}

# A dictionary for looking up z-height offset variables in the AST.
z_height_dictionary = {
    "PCRPlate_Z_50_offset" : 0,
    "Deepwell_Z_50_offset" : 0,
    "Deep384_Z_50_offset" : 0,
    "PCRPlate_Z_200_offset" : 0,
    "Deepwell_Z_200_offset" : 0,
    "Deep384_Z_200_offset" : 0,
    "PCRPlate_Z_offset" : 0,
    "Deepwell_Z_offset" : 0,
    "p300_offset_Deck" : 0,
    "p300_offset_Res" : 0,
    "p300_offset_Tube" : 0,
    "p20_offset_Deck" : 0,
    "p20_offset_Res" : 0,
    "p20_offset_Tube" : 0
}

# Dictionaries to track the usage of old vs. new reservoir labware.
old_reservoirs= {
    "nest_1_reservoir_195ml" : 0,
    "nest_12_reservoir_15ml" : 0,
    "nest_1_reservoir_290ml" : 0,
    "armadillo_96_wellplate_200ul_pcr_full_skirt" : 0,
    "nest_96_wellplate_2ml_deep" : 0,
    "No pre-existing Standard" : 0
}
new_reservoirs= {
    "opentrons_96_wellplate_200ul_pcr_full_skirt" : 0,
    "opentrons_tough_12_reservoir_22ml" : 0,
    "opentrons_tough_1_reservoir_300ml" : 0,
    "opentrons_tough_4_reservoir_72ml" : 0,
    "opentrons_tough_universal_lid" : 0
}

# --- Analysis Functions ---

def evaluate_expression(node, variables):
    """
    Recursively evaluates an AST node representing a simple arithmetic expression.

    This function can handle constants, variables (looked up in the `variables` 
    dictionary), and binary operations (+, -). It's used to calculate the 
    final numeric value of z-heights defined with variables (e.g., `z_offset + 5`).

    Args:
        node (ast.AST): The AST node to evaluate.
        variables (dict): A dictionary mapping variable names (str) to their values.

    Returns:
        float or int: The calculated result of the expression, or None if it's
                      an unsupported type or operation.
    """
    # Targets Binary Operations and returns the sum of the operation using the variables (i.e. a provided dictionary) 
    # and compares the provided values with the found variable.
    
    # Base case 1: A constant number
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value
        else:
            return None # Not a num
        
    # Base Case 2: A variable name, looked up in the provided dictionary.
    elif isinstance(node, ast.Name):
        return variables.get(node.id)
    
    # Recursive Case: A binary operation like '+' or '-'.
    elif isinstance(node, ast.BinOp):
        left_val = evaluate_expression(node.left, variables)
        right_val = evaluate_expression(node.right, variables)

        if left_val is None or right_val is None:
            return None
        
        if isinstance(node.op, ast.Add):
            return left_val + right_val
        elif isinstance(node.op, ast.Sub):
            return left_val - right_val
        else:
            return None # Unsupported operation
    else:
        return None # Unsupported node type


def check_z(file_path, threshold = 0.5):
    """
    Scans a Python script for z-height values that are below a given threshold.

    This function parses the script into an AST and walks through it, looking for
    `.bottom()` and `.top()` method calls and `z=` keyword arguments. It reports
    any numeric values that are considered potentially risky.

    Args:
        file_path (str): The full path to the Python script to check.
        threshold (float, optional): The minimum allowed value for `.bottom()` z-heights.
                                     Defaults to 0.5.
    """
    bottom_issues = 0
    z_issues = 0
    top_issues= 0

    with open(file_path, 'r') as f:
        content = f.read()

    tree = ast.parse(content)

    # Walk through every node in the abstract syntax tree.
    for node in ast.walk(tree):
        # We only care about attribute calls, like `well.bottom()`.
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
            continue

        # --- Check `.bottom()` calls ---
        if node.func.attr == 'bottom':
            # Case 1: Handle positional arguments like .bottom(-1)
            if node.args:
                arg_node = node.args[0]
                z_value = None
                if isinstance(arg_node, ast.Constant):
                    z_value = arg_node.value
                # Handle negative numbers, which are parsed as UnaryOp(USub(...))
                elif isinstance(arg_node, ast.UnaryOp) and isinstance(arg_node.op, ast.USub):
                    z_value = -arg_node.operand.value

                if isinstance(z_value, (int, float)) and z_value < threshold:
                    print(f"Warning: Positional z-value of {z_value} on line {node.lineno} is below threshold.")
                    z_issues += 1
            
            # Case 2: Handle keyword arguments like .bottom(z=-1)
            if node.keywords:
                for keyword in node.keywords:
                    if keyword.arg == 'z':
                        z_value = None
                        # Check for simple numbers (positive and negative)
                        if isinstance(keyword.value, ast.Constant):
                            z_value = keyword.value.value
                        elif isinstance(keyword.value, ast.UnaryOp) and isinstance(keyword.value.op, ast.USub):
                            z_value = -keyword.value.operand.value
                        else:
                             # Try to evaluate complex expressions like `z_offset + 1`
                             z_value = evaluate_expression(keyword.value, z_height_dictionary)
                             if isinstance(z_value, (int, float)) and z_value < threshold : 
                                print(f"Warning: Calculated z-value of {z_value} on line {node.lineno} is below threshold.")

                        if isinstance(z_value, (int, float)) and z_value < threshold:
                            print(f"Warning: Keyword z-value of {z_value} on line {node.lineno} is below threshold.")
                            z_issues += 1

        # --- Check `.top()` calls ---
        elif node.func.attr == 'top':
            if node.args: # Check for positional arguments
                arg = node.args[0]
                z_value = None
                # Handle positive numbers, ex: top(10)
                if isinstance(arg, ast.Constant) and isinstance(arg.value, (int, float)):
                    z_value = arg.value
                # Handle negative numbers, ex: top(-11)
                elif (isinstance(arg, ast.UnaryOp) and
                      isinstance(arg.op, ast.USub) and
                      isinstance(arg.operand, ast.Constant)):
                    z_value = -arg.operand.value

                # Check if the value is too far below the top of the well.
                if z_value is not None and z_value < -7:
                    print(f"Warning: .top() call on line {node.lineno} has a value ({z_value}) below the threshold of -7.")
                    top_issues += 1

    print(f"Total .bottom() z-value issues: {z_issues}")
    print(f"Total empty .bottom() issues: {bottom_issues}")
    print(f"Total .top() value issues: {top_issues}")


def find_all_reservoirs(file_path, old_reservoirs, new_reservoirs):
    """
    Scans a script for `load_labware` calls to identify old and new reservoirs.

    Args:
        file_path (str): The full path to the Python script.
        old_reservoirs (dict): A dictionary counter for old labware.
        new_reservoirs (dict): A dictionary counter for new labware.
    """
    with open(file_path, 'r') as f:
        content = f.read()
    # `occured` prevents double-counting the same labware type if loaded multiple times in one file.
    occured = {""}
    
    tree = ast.parse(content)

    for node in ast.walk(tree):
        # Find calls to the 'load_labware' function.
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == 'load_labware':
            if node.args and isinstance(node.args[0],ast.Constant):
                load_name = node.args[0].value
                # Check if the labware name is in our list of old reservoirs.
                if load_name in old_reservoirs:
                    if load_name not in occured:
                        old_reservoirs[load_name] += 1
                        print(f"Old reservoir: {load_name}")
                    occured.add(load_name)
                # Check if the labware name is in our list of new reservoirs.
                if load_name in new_reservoirs:
                    if load_name not in occured:
                        new_reservoirs[load_name] += 1
                        print(f"New reservoir: {load_name}")
                    occured.add(load_name)


def find_all_modules_in_file(file_path, module_map):
    """
    Reads a file once and finds all module strings defined in a map.

    Arguments:
        file_path (str): The full path to the file to search.
        module_map (dict): A dictionary where keys are the strings to search for
                           and values are the module names to return.

    Returns:
        list: A list of human-readable names for all modules found in the file.
    """
    found_modules = []
    try:
        # Read the entire file content into memory.
        with open(file_path, 'r') as f:
            content = f.read()
            
            # Check for the presence of each search key from the map.
            for search_key, module_name in module_map.items():
                if search_key in content:
                    found_modules.append(module_name)
    
    except FileNotFoundError:
        print(f"Error: The file '{file_path}' was not found.")
    
    return found_modules


# --- Main Execution Block ---
if __name__ == "__main__":
    # The subdirectory containing your protocol files.
    protocols_directory = 'Protocol Full Batch'  
    all_protocols_data = {}

    # Get the absolute path to the protocols directory to ensure it works from any location.
    current_script_dir = os.path.dirname(__file__)
    absolute_protocols_path = os.path.join(current_script_dir, protocols_directory)

    print(f"Scanning for protocol files in: {absolute_protocols_path}\n")

    # Iterate through all files in the specified directory.
    for filename in os.listdir(absolute_protocols_path):
        # Only process Python files and exclude __init__.py.
        if filename.endswith('.py') and filename != '__init__.py':
            module_name = filename[:-3]  # Remove the '.py' extension
            full_module_import_path = f"{protocols_directory}.{module_name}"
            full_file_path = os.path.join(absolute_protocols_path, filename)

            print(f"--- Processing {filename} ---")
            try:
                # Dynamically import the protocol file as a Python module to access its contents.
                module = importlib.import_module(full_module_import_path)
                current_protocol_info = {"filename": filename}

                # 1. Extract from metadata dictionary.
                if hasattr(module, 'metadata') and isinstance(module.metadata, dict):
                    current_protocol_info["author"] = module.metadata.get("author", "N/A")
                    current_protocol_info["protocolName"] = module.metadata.get("protocolName", "N/A")
                    current_protocol_info["source"] = module.metadata.get("source", "N/A (not specified)")
                    # Set defaults that might be overridden by 'requirements'.
                    current_protocol_info["robotType"] = module.metadata.get("robotType", "N/A")
                    current_protocol_info["apiLevel"] = module.metadata.get("apiLevel", "N/A")
                else:
                    current_protocol_info["metadata_error"] = "Metadata dictionary not found or invalid."
                    current_protocol_info["robotType"] = "N/A"
                    current_protocol_info["apiLevel"] = "N/A"

                # 2. Extract from requirements, which takes precedence over metadata.
                if hasattr(module, 'requirements') and isinstance(module.requirements, dict):
                    req_robot_type = module.requirements.get("robotType")
                    req_api_level = module.requirements.get("apiLevel")
                    if req_robot_type is not None:
                        current_protocol_info["robotType"] = req_robot_type
                    if req_api_level is not None:
                        current_protocol_info["apiLevel"] = req_api_level
                else:
                    current_protocol_info["requirements_error"] = "Requirements dictionary not found or invalid."

                # 3. Analyze parameters from the add_parameters function.
                if hasattr(module, 'add_parameters') and callable(module.add_parameters):
                    mock_params = MockParameters()
                    try:
                        # Call the function with our mock object to capture parameter data.
                        module.add_parameters(mock_params) 
                        current_protocol_info["total_parameters"] = len(mock_params.added_parameters)
                        
                        # Group parameters by their type for a summary.
                        parameter_types_summary = {}
                        for param in mock_params.added_parameters:
                            param_type = param.get("type", "unknown")
                            parameter_types_summary.setdefault(param_type, []).append(param.get("name", "Unnamed"))
                        
                        current_protocol_info["parameter_types"] = parameter_types_summary
                    except Exception as e:
                        current_protocol_info["parameters_error"] = f"Error calling add_parameters: {e}"
                else:
                    current_protocol_info["parameters_error"] = "add_parameters function not found."

                # 4. Find all loaded hardware modules by scanning the file's text.
                loaded_modules = find_all_modules_in_file(full_file_path, MODULE_SEARCH_MAP)
                current_protocol_info["loaded_modules"] = loaded_modules

                # Store the extracted data for this protocol.
                all_protocols_data[module_name] = current_protocol_info
                
                # --- Print Live Results for Current File ---
                print(f"  Protocol Name: {current_protocol_info.get('protocolName', 'N/A')}")
                print(f"  Author: {current_protocol_info.get('author', 'N/A')}")
                print(f"  Robot Type: {current_protocol_info.get('robotType', 'N/A')}")
                print(f"  Total Parameters: {current_protocol_info.get('total_parameters', 'N/A')}")

                print("\n  Incorrect heights of z:")
                check_z(full_file_path, 0.5)
                
                print("\n  Reservoir Analysis:")
                find_all_reservoirs(full_file_path, old_reservoirs, new_reservoirs)
                print("\n")

            except ImportError as e:
                print(f"Error: Could not import module '{full_module_import_path}'. Ensure file exists and is valid Python. Error: {e}")
            except Exception as e:
                print(f"An unexpected error occurred while processing {filename}: {e}")
            print("-" * 30) # Separator 

    # --- Final Summary Report ---
    print("\n=== Comprehensive Report ===")
    print(f"Total files processed: {len(all_protocols_data)}\n")

    # Detailed breakdown for each protocol.
    for module_name, data in all_protocols_data.items():
        print(f"Protocol Module: {module_name}")
        print(f"  - File: {data.get('filename', 'N/A')}")
        print(f"  - Protocol Name: {data.get('protocolName', 'N/A')}")
        print(f"  - Author: {data.get('author', 'N/A')}")
        print(f"  - Robot Type: {data.get('robotType', 'N/A')}")
        print(f"  - API Level: {data.get('apiLevel', 'N/A')}")
        
        # Display parameter breakdown.
        if 'parameter_types' in data:
            print("  - Parameter Types:")
            for p_type, p_names in data['parameter_types'].items():
                print(f"    - {p_type.capitalize()}: {len(p_names)} ({', '.join(p_names)})")
        elif 'parameters_error' in data:
            print(f"  - Parameters Error: {data['parameters_error']}")
        
        # Check for filename consistency.
        if module_name != data.get('protocolName', 'N/A'):
            print("\n  ^^Protocol Name and File name mismatch.^^") 
        
        # Display loaded modules and update the global counter.
        if 'loaded_modules' in data:
            print("\n  - Loaded Modules:")
            if not data["loaded_modules"]:
                print("    - N/A")
            else:
                for installed_module in data['loaded_modules']:
                    print(f"    - {installed_module}")
                    module_counter[installed_module] += 1
            print("\n")

    # Final aggregated counts.
    print("\n--- Final Summary Counts ---")
    print("\nTotal Module Usage:")
    for key, value in module_counter.items():
        print(f"  - {key}: {value}")

    print("\nOld Reservoir Usage:")
    for key, value in old_reservoirs.items():
        print(f"  - {key}: {value}")

    print("\nNew Reservoir Usage:")
    for key, value in new_reservoirs.items():
        print(f"  - {key}: {value}")

'''
**NOTE**
    Use terminal on mac if the output is too great for the ide/text editor terminal.
'''
