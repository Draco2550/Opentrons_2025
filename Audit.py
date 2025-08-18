print('\n'*100) # This can be removed, this is simply a spacer for myself to make it more visually seperated when running the program multiple times.

import ast
import importlib
import os
#import opentrons


# Mock Parameters class (needed to analyze the add_parameters function)
class MockParameters:
    def __init__(self):
        self.added_parameters = []

    def add_bool(self, variable_name, **kwargs):
        self.added_parameters.append({"name": variable_name, "type": "bool", **kwargs})

    def add_int(self, variable_name, **kwargs):
        self.added_parameters.append({"name": variable_name, "type": "int", **kwargs})

    def add_str(self=None, variable_name=None, **kwargs):
        self.added_parameters.append({"name": variable_name, "type": "str", **kwargs})

    def add_float(self, variable_name, **kwargs):
        self.added_parameters.append({"name": variable_name, "type": "float", **kwargs})

    def add_csv_file(self, variable_name, **kwargs): # remove if broken.
        self.added_parameters.append({"name": variable_name, "type": "csv", **kwargs})


# A map of search strings to the desired final module names
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

module_counter = {
    "Absorbance Plate Reader Module": 0, 
    "Thermocycler Module GEN 2": 0,
    "Flex Stacker Module V1": 0,
    "Magnetic Block V1": 0,
    "Heater-Shaker Module GEN 1": 0,
    "Temperature Module GEN 2": 0,
    "PCR Auto Sealing Lid": 0,
}


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

def evaluate_expression(node, variables): # Targets Binary Operations and returns the sum of the operation using the variables (i.e. a provided dictionary) 
    # and compares the provided values with the found variable.
    
    # Base case 1: A constant number
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value
        else:
            return None # Not a num
        

    #Base Case 2: A variable name like the ones in the dictionary.
    elif isinstance(node, ast.Name):
        return variables.get(node.id)
    
    # Recursive Case: A binary operation.
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
            return None
    else:
        return None
    



def check_z(file_path, threshold = 0.5):
    bottom_issues = 0
    z_issues = 0
    top_issues= 0

    with open(file_path, 'r') as f:
            content = f.read()

    tree = ast.parse(content)

    for node in ast.walk(tree):
        
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
            continue

        # **IGNORE** 
        # Case 1: Handle empty calls like .bottom()
        # if not node.args and not node.keywords:
        #     print(f"Warning: Empty .bottom() call on line {node.lineno}. May use a default value less than {threshold}.")
        #     bottom_issues += 1
        #     continue

        # Case 1: Handle positional arguments like .bottom(-1)
        if node.args and node.func.attr == 'bottom':
            arg_node = node.args[0]
            z_value = None
            if isinstance(arg_node, ast.Constant):
                z_value = arg_node.value
            elif isinstance(arg_node, ast.UnaryOp) and isinstance(arg_node.op, ast.USub):
                z_value = -arg_node.operand.value # Re-apply the negative sign

            if isinstance(z_value, (int, float)) and z_value < threshold:
                print(f"Warning: Positional z-value of {z_value} on line {node.lineno} is below threshold.")
                z_issues += 1
        
        # Case 2: Handle keyword arguments like .bottom(z=-1)
        if node.keywords and node.func.attr == 'bottom':
            is_z_found = False
            for keyword in node.keywords:
                if keyword.arg == 'z':
                    is_z_found = True
                    z_value = None
                    # Check for positive numbers
                    if isinstance(keyword.value, ast.Constant):
                        z_value = keyword.value.value
                    # Check for negative numbers
                    elif isinstance(keyword.value, ast.UnaryOp) and isinstance(keyword.value.op, ast.USub):
                        z_value = -keyword.value.operand.value # Re-apply the negative sign
                    else:
                         z_value = evaluate_expression(keyword.value, z_height_dictionary)
                         if isinstance(z_value, (int, float)) and z_value < threshold : 
                            print(f"Warning: Total z value of {z_value} on line {node.lineno} is below threshold.")

                    if isinstance(z_value, (int, float)) and z_value < threshold:
                        print(f"Warning: Keyword z-value of {z_value} on line {node.lineno} is below threshold.")
                        z_issues += 1
            
            if not is_z_found:
                print(f"Info: .bottom() call with no 'z' keyword on line {node.lineno}. May use default.")

        elif node.func.attr == 'top':
            if node.args: # Check if there are arguments
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

                # If a valid number was found, check it against the threshold
                if z_value is not None and z_value < -7:
                    print(f"Warning: .top() call on line {node.lineno} has a value ({z_value}) below the threshold of {-7}.")
                    top_issues += 1

    print(f"Total .bottom() z-value issues: {z_issues}")
    print(f"Total empty .bottom() issues: {bottom_issues}")
    print(f"Total .top() value issues: {top_issues}")
        
            

    if isinstance(node, ast.keyword) and node.arg == 'z':
                # This handles cases like 'z=0.4'
                if isinstance(node.value, ast.Constant):
                    z_value = node.value.value
                    if float(z_value) < threshold and float(z_value) > 0:
                        print(f"Warning: Z-value of {z_value} on line {node.value.lineno} is below the threshold of {threshold}.")
                        z_issues += 1


def find_all_reservoirs(file_path, old_reservoirs, new_reservoirs):
    with open(file_path, 'r') as f:
        content = f.read()
        occured = {""}

    
    tree = ast.parse(content)

    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == 'load_labware':
            if node.args and isinstance(node.args[0],ast.Constant):
                load_name = node.args[0].value
                if load_name in old_reservoirs:
                    if load_name not in occured:
                        old_reservoirs[load_name] += 1
                        print(f"Old reservoir: {load_name}")
                    occured.add(load_name)
                    
                    # print(f"Old reservoir: {load_name} found at line number: {node.args[0].lineno}.") # <-- comment or un-comment for debugging and finding the line where the instance is found.
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
        # Read the entire file into memory just one time
        with open(file_path, 'r') as f:
            content = f.read()
            
            # Check for the presence of each search key from the map
            for search_key, module_name in module_map.items():
                if search_key in content:
                    found_modules.append(module_name)
    
    except FileNotFoundError:
        print(f"Error: The file '{file_path}' was not found.")
    
    return found_modules



# Main file to manage the location of the protocol folder
protocols_directory = 'Protocol Full Batch'  # The subdirectory containing your protocol files, please change it to where it is located on your machine. Not sure if it works on Windows (test machine: Macboook pro m3)
all_protocols_data = {}

# Get the absolute path to the protocols directory
current_script_dir = os.path.dirname(__file__)
absolute_protocols_path = os.path.join(current_script_dir, protocols_directory)

print(f"Scanning for protocol files in: {absolute_protocols_path}\n") # This path/directory must have the Opentrons api and correct python version setup already (python 3.10.0)

# Iterate through all files in the specified directory
for filename in os.listdir(absolute_protocols_path):
    # Only process Python files and exclude __init__.py
    if filename.endswith('.py') and filename != '__init__.py':
        module_name = filename[:-3]  # Remove the '.py' extension

        # Construct the full import path 
        full_module_import_path = f"{protocols_directory}.{module_name}"

        print(f"--- Processing {filename} ---")
        try:
            # Dynamically import the module
            module = importlib.import_module(full_module_import_path)

            # Initialize a dictionary to store data for this specific protocol
            current_protocol_info = {"filename": filename}

           # 1. Extract from metadata
            if hasattr(module, 'metadata') and isinstance(module.metadata, dict):
                current_protocol_info["author"] = module.metadata.get("author", "N/A")
                current_protocol_info["protocolName"] = module.metadata.get("protocolName", "N/A")
                current_protocol_info["source"] = module.metadata.get("source", "N/A (not specified)")

                # Try to get robotType and apiLevel from metadata as a fallback
                # These will be overwritten if found in requirements below
                current_protocol_info["robotType"] = module.metadata.get("robotType", "N/A")
                current_protocol_info["apiLevel"] = module.metadata.get("apiLevel", "N/A")

            else:
                current_protocol_info["metadata_error"] = "Metadata dictionary not found or invalid."
                # Ensure these keys exist even if metadata is missing
                current_protocol_info["robotType"] = "N/A"
                current_protocol_info["apiLevel"] = "N/A"


            # 2. Extract from requirements, override from metadata if information is missing
            if hasattr(module, 'requirements') and isinstance(module.requirements, dict):
                # If requirements has these keys, they take precedence
                req_robot_type = module.requirements.get("robotType")
                req_api_level = module.requirements.get("apiLevel")

                if req_robot_type is not None:
                    current_protocol_info["robotType"] = req_robot_type
                if req_api_level is not None:
                    current_protocol_info["apiLevel"] = req_api_level
            else:
                current_protocol_info["requirements_error"] = "Requirements dictionary not found or invalid."
                # If requirements dictionary itself is missing or invalid,
                # the robotType and apiLevel would have already been set (or defaulted to "N/A") from metadata.

            # 3. Analyze parameters from the add_parameters function
            if hasattr(module, 'add_parameters') and callable(module.add_parameters):
                mock_params = MockParameters()
                try:
                    module.add_parameters(mock_params) # Call the function with our mock object
                    
                    current_protocol_info["total_parameters"] = len(mock_params.added_parameters)
                    
                    parameter_types_summary = {}
                    for param in mock_params.added_parameters:
                        param_type = param.get("type", "unknown")
                        if param_type not in parameter_types_summary:
                            parameter_types_summary[param_type] = []
                        parameter_types_summary[param_type].append(param.get("name", "Unnamed"))
                    
                    current_protocol_info["parameter_types"] = parameter_types_summary
                except Exception as e:
                    current_protocol_info["parameters_error"] = f"Error calling add_parameters: {e}"
            else:
                current_protocol_info["parameters_error"] = "add_parameters function not found."


            # 4. Analyze .load_module calls from the file content.
            if hasattr(module, 'run') and callable(module.run):
                # Construct the full path to the file being processed
                full_file_path = os.path.join(absolute_protocols_path, filename)
                loaded_modules = find_all_modules_in_file(full_file_path, MODULE_SEARCH_MAP)

                current_protocol_info["loaded_modules"] = loaded_modules


            # Store the extracted data for this protocol
            all_protocols_data[module_name] = current_protocol_info
            
            print(f"  Protocol Name: {current_protocol_info.get('protocolName', 'N/A')}")
            print(f"  Author: {current_protocol_info.get('author', 'N/A')}")
            print(f"  Robot Type: {current_protocol_info.get('robotType', 'N/A')}")
            print(f"  Total Parameters: {current_protocol_info.get('total_parameters', 'N/A')}")

            print("\n Incorrect heights of z:")
            check_z(full_file_path, 0.5)
            print("\n")
            find_all_reservoirs(full_file_path, old_reservoirs, new_reservoirs)
            print("\n")

        except ImportError as e:
            print(f"Error: Could not import module '{full_module_import_path}'. Ensure file exists and is valid Python. Error: {e}")
        except Exception as e:
            print(f"An unexpected error occurred while processing {filename}: {e}")
        print("-" * 30) # Separator 

# Final Summary 
print("\n=== Comprehensive Report ===")
print(f"Total files processed: {len(all_protocols_data)}\n")


for module_name, data in all_protocols_data.items():
    print(f"Protocol Module: {module_name}")
    print(f"  File: {data.get('filename', 'N/A')}")
    print(f"  Protocol Name: {data.get('protocolName', 'N/A')}")
    print(f"  Author: {data.get('author', 'N/A')}")
    print(f"  Source: {data.get('source', 'N/A')}")
    print(f"  Robot Type: {data.get('robotType', 'N/A')}")
    print(f"  API Level: {data.get('apiLevel', 'N/A')}")
    print(f"  Total Parameters: {data.get('total_parameters', 'N/A')}")
    
    if 'parameter_types' in data:
        print("  Parameter Types Breakdown:")
        for p_type, p_names in data['parameter_types'].items():
            print(f"    - {p_type.capitalize()}: {len(p_names)} parameters ({', '.join(p_names)})")
    elif 'parameters_error' in data:
        print(f"  Parameters Error: {data['parameters_error']}")
    
    if module_name != data.get('protocolName', 'N/A'): # Note: Only permits exact matchs, anything that is not completely a match will trigger it. (Could be fixed with a little bit of regex or .lower)
        print("\n  ^^Protocol Name and File name mismatch.^^") 
        # Add functionality to make sure it warns to update the file name, or add functionality with g-sheets
    
    if 'loaded_modules' in data:
        print("\n  Loaded Modules:")
        if len(data["loaded_modules"]) == 0:
            print("  N/A")
        for installed_module in data['loaded_modules']:
            print(f"  - {installed_module}")
            module_counter[installed_module] += 1
        print("\n\n")
    
    

print("\nTotal modules: ")
for key, value in module_counter.items():
    print(f"  - {key}: {value}")

print("\nOld Reservoir Count: ")
for key, value in old_reservoirs.items():
    print(f"  - {key}: {value}")

print("\nNew Reservoir Count: ")
for key, value in new_reservoirs.items():
    print(f"  - {key}: {value}")
'''
**NOTE**
    Use terminal on mac if the output is too great for the ide/text editor terminal.

TODO:
- Add a flag before running if you want to generate the output in csv file (Some of the print orders might need to be changed.)
    - Consider using the format set in the google sheet. (Might allow for google sheets to read in the data easier.)
- Find the Rate of aspiration and dispurtion. (i.e. if the program uses rate or flow rate flag it as the rates now have been adjusted.)

'''