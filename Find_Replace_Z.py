import ast
import importlib
import os


"""
This script provides tools to statically analyze and modify Python files, 
specifically targeting Opentrons protocol scripts. It uses Abstract Syntax Trees (AST) 
to parse the source code, identify specific function calls and arguments related 
to Z-heights, and automatically correct values that fall below a defined threshold. 
The modified script is then written to a new file in a designated output directory.
"""

# A dictionary intended to hold z-height offset variables.
# This can be used with the `evaluate_expression` function to resolve variable values.
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

def evaluate_expression(node, variables):
    """
    Recursively evaluates an AST node representing a simple arithmetic expression.

    This function can handle constants, variables (looked up in the `variables` 
    dictionary), and binary operations (+, -). It's useful for calculating the 
    final numeric value of expressions like `z_offset + 5`.

    Args:
        node (ast.AST): The AST node to evaluate.
        variables (dict): A dictionary mapping variable names (str) to their 
                          numeric values.

    Returns:
        float or int: The calculated result of the expression.
        None: If the expression contains unsupported types or operations.
    """
    # Targets Binary Operations and returns the sum of the operation using the variables (i.e. a provided dictionary) 
    # and compares the provided values with the found variable.
    
    # Base case 1: A constant number (e.g., 5, 0.5)
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value
        else:
            return None # Not a number

    # Base Case 2: A variable name, looked up in the provided dictionary.
    elif isinstance(node, ast.Name):
        return variables.get(node.id)
    
    # Recursive Case: A binary operation like '+' or '-'.
    elif isinstance(node, ast.BinOp):
        # Evaluate the left and right sides of the operation first.
        left_val = evaluate_expression(node.left, variables)
        right_val = evaluate_expression(node.right, variables)

        # If either side could not be evaluated, the whole expression fails.
        if left_val is None or right_val is None:
            return None
        
        # Perform the operation based on its type.
        if isinstance(node.op, ast.Add):
            return left_val + right_val
        elif isinstance(node.op, ast.Sub):
            return left_val - right_val
        else:
            # Unsupported operation (e.g., multiplication, division).
            return None
    else:
        # Unsupported node type (e.g., a function call).
        return None

def check_z(file_path, threshold=0.5):
    """
    Reads a Python script, corrects low Z-height values, and writes a new, audited file.

    This function parses the script into an AST and uses the `Z_Changer` class
    to find and modify z-heights in `z=` keyword arguments and in `.bottom()` and 
    `.top()` method calls.

    Args:
        file_path (str): The full path to the Python script to check.
        threshold (float, optional): The minimum allowed value for certain Z-heights. 
                                     Defaults to 0.5.
    """
    with open(file_path, 'r') as f:
            content = f.read()

    tree = ast.parse(content)

    class Z_Changer(ast.NodeTransformer):
        """
        An AST NodeTransformer that finds and modifies Z-height values in code.
        """
        def visit_keyword(self, node):
            """
            Visits keyword arguments, specifically looking for `z=...`.
            """
            # Check for a keyword argument named 'z' with a constant value.
            if node.arg == 'z' and isinstance(node.value, ast.Constant):
                z_value = node.value.value
                if isinstance(z_value, (int, float)) and z_value < threshold:
                    # If the value is below the threshold, return a new keyword node
                    # with the corrected value.
                    return ast.keyword(arg='z', value=ast.Constant(value=threshold))
            # Important: process other nodes as usual.
            return super().generic_visit(node)

        def visit_Call(self, node):
            """
            Visits function calls, specifically looking for `.bottom()` and `.top()`.
            """
            # First, visit all children of this node to ensure they are processed.
            node = super().generic_visit(node)
            
            # Check for method calls like `well.bottom(z=...)`
            if isinstance(node.func, ast.Attribute) and node.func.attr == 'bottom':
                # Check if the call has positional arguments.
                if node.args and isinstance(node.args[0], ast.Constant):
                    z_value = node.args[0].value
                    if isinstance(z_value, (int, float)) and z_value < threshold:
                        # If the value is too low, replace the argument node.
                        node.args[0] = ast.Constant(value=threshold)
            
            # Check for method calls like `well.top(z=...)`
            elif isinstance(node.func, ast.Attribute) and node.func.attr == 'top':
                if node.args: # Check if there are arguments
                    arg = node.args[0]
                    z_value = None

                    # Handle positive numbers, e.g., top(10)
                    if isinstance(arg, ast.Constant) and isinstance(arg.value, (int, float)):
                        z_value = arg.value
                    # Handle negative numbers, e.g., top(-11) by checking for a Unary Subtraction operation.
                    elif (isinstance(arg, ast.UnaryOp) and
                          isinstance(arg.op, ast.USub) and
                          isinstance(arg.operand, ast.Constant)):
                        z_value = -arg.operand.value

                    # If a valid number was found, check it against the threshold for large negative values.
                    if z_value is not None and z_value < -7:
                        #node.args[0] = ast.Constant(value=-7) #Remove the comment to make it replace instances less than -7.
                        print(f"Top value with large negative found on line: {node.lineno}")

            # Return the fully processed (and possibly modified) node.
            return node

    # --- Apply Transformation and Write New File ---
    transformer = Z_Changer()
    new_tree = transformer.visit(tree)
    ast.fix_missing_locations(new_tree)

    # Unparse the modified AST back into a string of Python code.
    new_code = ast.unparse(new_tree)

    # --- File Output Logic ---
    # Define the name for the output folder.
    output_folder_name = "Z_Test_Audited"
    # Get the directory of the currently running script.
    script_directory = os.path.dirname(os.path.abspath(__file__))
    # Create the full path for the output directory.
    audited_directory_path = os.path.join(script_directory, output_folder_name)
    # Create the directory if it doesn't already exist.
    os.makedirs(audited_directory_path, exist_ok=True)

    # Create the new file path inside the new directory, prefixed with "AUDIT_".
    new_filename = "AUDIT_" + os.path.basename(file_path)
    new_filepath = os.path.join(audited_directory_path, new_filename)

    # Write the modified code to the new file.
    try:
        with open(new_filepath, 'w') as f: 
            f.write(new_code)
        print(f"Successfully created and wrote to '{new_filename}' in '{output_folder_name}'")
    except Exception as e:
        print(f"Error writing file '{new_filename}': {e}")


# --- Main Execution Block ---
if __name__ == "__main__":
    # The subdirectory containing your protocol files.
    protocols_directory = 'Z_Test' # Change to your folder name.
    
    # Get the absolute path to the protocols directory to ensure it works from any location.
    current_script_dir = os.path.dirname(__file__)
    absolute_protocols_path = os.path.join(current_script_dir, protocols_directory)

    print(f"Scanning for protocol files in: {absolute_protocols_path}\n")

    # Iterate through all files in the specified directory.
    for filename in os.listdir(absolute_protocols_path):
        # Only process Python files, excluding __init__.py.
        if filename.endswith('.py') and filename != '__init__.py':
            full_file_path = os.path.join(absolute_protocols_path, filename)
            print(f"--- Processing {filename} ---")
            
            try:
                # The import logic is included here, though the `check_z` function
                # performs static analysis and does not require the module to be executed.
                # This could be used for other dynamic checks in the future.
                module_name = filename[:-3]
                full_module_import_path = f"{protocols_directory}.{module_name}"

                # Initialize a dictionary to store data for this specific protocol.
                current_protocol_info = {"filename": filename}
                
                print("Checking for incorrect z-heights:")
                check_z(full_file_path, 0.5)
                print("\n")

            except ImportError as e:
                print(f"Error: Could not import module '{full_module_import_path}'. Ensure file exists and is valid Python. Error: {e}")
            except Exception as e:
                print(f"An unexpected error occurred while processing {filename}: {e}")
            print("-" * 30) # Separator
