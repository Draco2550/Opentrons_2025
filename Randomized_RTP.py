import importlib.util
import os
import itertools
import pprint
import ast
from pathlib import Path

class MockParameters:
    """
    A mock class to capture parameter definitions from a protocol script.
    
    This class simulates the behavior of a parameter-handling interface by 
    providing `add_*` methods. When a script calls these methods, instead of 
    configuring a real application, this class simply records the parameter's 
    details (name, type, default value, etc.) in a list for later inspection.
    """
    def __init__(self):
        """Initializes the MockParameters instance with an empty list to store parameters."""
        self.added_parameters = []

    def add_bool(self, variable_name, default=None, **kwargs):
        """Stores the definition of a boolean parameter."""
        self.added_parameters.append({"name": variable_name, "type": "bool", "default_value": default, **kwargs})

    def add_int(self, variable_name, default=None, minimum=None, maximum=None, **kwargs):
        """Stores the definition of an integer parameter."""
        self.added_parameters.append({"name": variable_name, "type": "int", "default_value": default, "minimum": minimum, "maximum": maximum, **kwargs})

    def add_str(self, variable_name=None, default=None, choices=None, **kwargs):
        """Stores the definition of a string parameter."""
        self.added_parameters.append({"name": variable_name, "type": "str", "default_value": default, "choices": choices, **kwargs})

    def add_float(self, variable_name, default=None, minimum=None, maximum=None, **kwargs):
        """Stores the definition of a float parameter."""
        self.added_parameters.append({"name": variable_name, "type": "float", "default_value": default, "minimum": minimum, "maximum": maximum, **kwargs})

    def add_csv_file(self, variable_name, default=None, **kwargs):
        """Stores the definition of a CSV file parameter."""
        self.added_parameters.append({"name": variable_name, "type": "csv", "default_value": default, **kwargs})

def find_parameters(filename, absolute_protocols_path):
    """
    Dynamically loads a Python protocol script and extracts its parameter definitions.

    This function loads a Python file as a module in memory, finds the 
    `add_parameters` function within it, and executes it using a `MockParameters` 
    instance to capture the defined parameters.

    Args:
        filename (str): The name of the Python script file (e.g., 'my_protocol.py').
        absolute_protocols_path (str): The absolute path to the directory containing the script.

    Returns:
        dict: A dictionary containing details of the extracted parameters under the 
              key 'parameter_details', or an error message under 'parameters_error'.
        None: Returns None if the script file does not contain an `add_parameters` function.
    """
    original_filepath = Path(absolute_protocols_path) / filename #changed
    if not original_filepath.exists():
        print(f"Error: The file was not found at the specified path: {original_filepath}")
        # Exit gracefully if the file doesn't exist.
        exit()
    
    # Process only Python files, excluding '__init__.py'.
    if filename.endswith('.py') and filename != '__init__.py':
            # Create a specification for the module from its file path.
            # This spec tells Python how to load the module.
            #module_name = filename[:-3]
            in_memory_module_name = "module" # Give the module a valid in-memory name, e.g., "protocol_module".
            spec = importlib.util.spec_from_file_location(in_memory_module_name, original_filepath)
            
            if not spec or not spec.loader:
                raise ImportError(f"Could not create module spec from file: {original_filepath}")

            # Create a new module object based on the spec.
            module = importlib.util.module_from_spec(spec)
            # Execute the module's code in the newly created module object.
            # This makes its functions and variables available.
            spec.loader.exec_module(module)

            # full_module_import_path = f"{protocols_directory}.{module_name}"
            #full_module_import_path = f"Archive.{module_name}"
            #module = importlib.import_module(full_module_import_path)

            # Initialize a dictionary to store data for this specific protocol
            current_protocol_info = {"filename": filename}
            # Check if the module has the 'add_parameters' function.
            if hasattr(module, 'add_parameters') and callable(module.add_parameters):
                mock_params = MockParameters()
                try:
                    current_protocol_info = {}
                    mock_params = MockParameters()
                    
                    # Call the script's 'add_parameters' function with our mock object.
                    # This will populate mock_params.added_parameters.
                    module.add_parameters(mock_params)

                    # A dictionary to store all details for each parameter
                    parameter_details = {}
                    for param in mock_params.added_parameters:
                        name = param.get("name", "Unnamed")
                        parameter_details[name] = {
                            "type": param.get("type", "unknown"),
                            "default": param.get("default_value"),
                            "min": param.get("minimum"),
                            "max": param.get("maximum"),
                            "choices": param.get("choices")
                        }
                    current_protocol_info["parameter_details"] = parameter_details

                except Exception as e:
                    # If any error occurs during parameter extraction, record it.
                    current_protocol_info["parameters_error"] = f"Error processing parameters: {e}"
                return current_protocol_info

def print_param_details(current_protocol_info):
    """
    Prints a formatted summary of the extracted parameter details.

    Args:
        current_protocol_info (dict): The dictionary returned by find_parameters.
    """
    # Printing the details below:
    print("Parameter Details:")
    if "parameter_details" in current_protocol_info:
        for name, details in current_protocol_info["parameter_details"].items():
            # Start building the output string for the current parameter
            output = f"  - {name} ({details['type']}): "
            
            # Handle string with choices
            if details['type'] == 'str' and details['choices']:
                # Extract the 'display_name' for a cleaner look
                choice_names = [c['display_name'] for c in details['choices']]
                output += f"Default: '{details['default']}', Choices: [{', '.join(choice_names)}]"
            
            # Handle int/float with min/max values
            elif details['type'] in ['int', 'float']:
                parts = []
                if details['min'] is not None:
                    parts.append(f"Min: {details['min']}")
                if details['default'] is not None:
                    parts.append(f"Default: {details['default']}")
                if details['max'] is not None:
                    parts.append(f"Max: {details['max']}")
                output += ", ".join(parts)
                
            # Handle bool and other types that only have a default value
            else:
                output += f"Default: {details['default']}"
                
            print(output)
    elif "parameters_error" in current_protocol_info:
        print(f"  Error: {current_protocol_info['parameters_error']}")

    print("-" * 30) # Seperator

def generate_combinations(protocol_info):
    """
    Generates all possible combinations of parameter values based on their
    defined ranges, choices, or boolean states.

    Args:
        protocol_info (dict): A dictionary containing the parameter details.

    Returns:
        list[dict]: A list of dictionaries, where each dictionary represents
                    one unique combination of parameter values.
    """
    parameter_details = protocol_info.get("parameter_details")
    if not parameter_details:
        return []

    # Get the names of the parameters in a fixed order to ensure consistency.
    param_names = list(parameter_details.keys())
    value_sets = []

    # For each parameter, create a set of interesting values to test
    for name in param_names:
        details = parameter_details[name]
        current_values = set()

        param_type = details.get("type")
        if param_type in ['int', 'float']:
            # Use min, default, and max as the points of interest.
            # A set automatically handles duplicates (e.g., if default is the same as min).
            if details.get('min') is not None:
                current_values.add(details['min'])
            if details.get('default') is not None:
                current_values.add(details['default'])
            if details.get('max') is not None:
                current_values.add(details['max'])

        elif param_type == 'str' and details.get('choices'):
            # Use all available choices.
            for choice in details['choices']:
                current_values.add(choice['value'])

        elif param_type == 'bool':
            # Test both True and False, regardless of the default.
            current_values.add(True)
            current_values.add(False)
        
        else:
            # For other types (like csv_file), just use the default value.
            if details.get('default') is not None:
                current_values.add(details['default'])

        # If no specific values were found, use the default as a fallback.
        if not current_values:
             value_sets.append([details.get('default')])
        else:
            value_sets.append(list(current_values))

    # Calculate the Cartesian product of all value sets.
    # This creates all possible combinations of parameter values.
    combinations_tuples = itertools.product(*value_sets)

    # Convert the tuples of values back into dictionaries with parameter names.
    combinations_list = [dict(zip(param_names, combo)) for combo in combinations_tuples]

    return combinations_list

class ParameterTransformer(ast.NodeTransformer):
    """
    Navigates an Abstract Syntax Tree (AST) of a Python script and modifies the 
    'default' value in function calls like `add_int`, `add_str`, etc.
    
    This allows for programmatic alteration of the default values in a script's
    parameter definitions without simple text replacement, making it robust
    against formatting changes.
    """
    def __init__(self, new_defaults: dict):
        """
        Initializes the transformer with the new default values to apply.
        
        Args:
            new_defaults (dict): A dictionary mapping parameter variable names
                                 to their new default values.
        """
        self.new_defaults = new_defaults

    def visit_Call(self, node: ast.Call):
        """
        Visits every function call node in the AST.

        If the node is a call to an `add_*` method, it identifies the parameter by
        its `variable_name` and, if a new default is specified in `self.new_defaults`,
        it replaces the `default` keyword argument's value with the new one.
        """
        # We are looking for calls to add_int, add_str, etc.
        # These are attribute calls on an object, e.g., `parameters.add_int`.
        if isinstance(node.func, ast.Attribute) and node.func.attr.startswith('add_'):
            variable_name = None
            # Find the 'variable_name' argument to identify which parameter this is.
            for keyword in node.keywords:
                if keyword.arg == 'variable_name':
                    # ast.Constant stores its value in the .value attribute
                    variable_name = keyword.value.value 
                    break
            
            # If this parameter is one we want to change...
            if variable_name in self.new_defaults:
                # ...find the 'default' keyword argument and change its value.
                for keyword in node.keywords:
                    if keyword.arg == 'default':
                        new_value = self.new_defaults[variable_name]
                        # Replace the old value node with a new constant node.
                        keyword.value = ast.Constant(value=new_value)
                        break
        # Continue traversing the rest of the tree to visit other nodes.
        return self.generic_visit(node)

def modify_script_with_new_defaults(source_code: str, new_defaults: dict) -> str:
    """
    Parses source code, applies new defaults using an AST transformer,
    and returns the modified source code.
    
    Args:
        source_code (str): The original Python script content.
        new_defaults (dict): The combination of new default values to apply.

    Returns:
        str: The modified Python script content.
    """
    # Parse the source code into an Abstract Syntax Tree.
    tree = ast.parse(source_code)
    # Create an instance of our transformer with the new default values.
    transformer = ParameterTransformer(new_defaults)
    # Apply the transformer to the tree.
    new_tree = transformer.visit(tree)
    # Fix any missing line numbers/locations for unparsing.
    ast.fix_missing_locations(new_tree)
    # Convert the modified tree back into source code.
    return ast.unparse(new_tree)

# --- Main execution block ---
if __name__ == '__main__':
    # --- Configuration ---
    protocols_directory = 'Archive' # Directory name where the files you intend to work with.
    # The directory where new protocol files will be saved
    OUTPUT_DIR = Path("generated_protocols")
    # Get the absolute path to the protocols directory, relative to this script's location.
    current_script_dir = os.path.dirname(__file__)
    absolute_protocols_path = os.path.join(current_script_dir, protocols_directory)
    
    filename = 'file.py' # Specify the file in the provided folder that you want to analyze.

    # --- Step 1: Extract Parameters ---
    print(f"Finding parameters in '{filename}'...")
    current_protocol_info = find_parameters(filename, absolute_protocols_path)
    print_param_details(current_protocol_info)

    # --- Step 2: Read Original Script Content ---
    original_filepath = Path(absolute_protocols_path) / filename 
    if not original_filepath.exists():
        print(f"Error: The file was not found at the specified path: {original_filepath}")
        # Exit gracefully if the file doesn't exist.
        exit()
    # Read the entire content of the script into a string.
    source_script_content = original_filepath.read_text()

    # --- Step 3: Generate Parameter Combinations ---
    print("\n--- Generating Combinations ---")
    combinations = generate_combinations(current_protocol_info)
    
    # Loop through the combinations to print each one with an index
    for index, combo in enumerate(combinations, 1):
        print(f"Combination #{index}:")
        pprint.pprint(combo) # Pretty print the list of combination dictionaries
        print() 

    print(f"\nTotal combinations generated: {len(combinations)}")

    # --- Step 4: User Prompts for File Generation ---
    print("\n")
    create_txt_doc = input("Do you want to create a .txt doc of all the combinations? (y/n): ").lower().strip() == 'y'
    print("\n")
    create_combo_files = input("Do you want to create the files for all combinations? (y/n): ").lower().strip() == 'y'

    # --- Step 5: Generate Output Files (if requested) ---
    if create_txt_doc:
        print(f"\n--- Generating output.txt file in '{OUTPUT_DIR}' directory... ---")
        OUTPUT_DIR.mkdir(exist_ok=True) # Create the output directory if it doesn't exist
        new_filename = "output.txt"
        new_filepath = OUTPUT_DIR / new_filename
        output = ""
        # Build a single string with all combination details.
        for index, combo in enumerate(combinations, 1):
            output += f"\nCombination #{index}:\n"
            output += pprint.pformat(combo)
        
        # Write the formatted string to the output file.
        new_filepath.write_text(output)
        print(f"   Generated: {new_filepath}")

    if create_combo_files:
        print(f"\n--- Generating files in '{OUTPUT_DIR}' directory... ---")
        OUTPUT_DIR.mkdir(exist_ok=True) # Create the output directory if it doesn't exist

        # Iterate through each generated combination.
        for i, combo in enumerate(combinations, 1):
            # Modify the original script content with the new default values from the current combination.
            modified_code = modify_script_with_new_defaults(source_script_content, combo) # Changed
            
            # Define the new filename (e.g., "1_my_protocol.py").
            new_filename = f"{i}_{filename}"
            new_filepath = OUTPUT_DIR / new_filename
            
            # Write the modified content to the new file.
            new_filepath.write_text(modified_code)
            print(f"  Generated: {new_filepath}")

        print("\n--- All files generated successfully! ---")
