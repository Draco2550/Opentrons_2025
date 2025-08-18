import ast
import importlib
import os
import astunparse

    

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
    # This function now reads, transforms, and WRITES back to the file.

    with open(file_path, 'r') as f:
            content = f.read()

    tree = ast.parse(content)

    class Z_Changer(ast.NodeTransformer):
            def visit_keyword(self, node):
                if node.arg == 'z' and isinstance(node.value, ast.Constant):
                    # Using node.value.value to get the actual value
                    z_value = node.value.value
                    if isinstance(z_value, (int, float)) and z_value < threshold:
                        # Return a new node with the corrected value
                        return ast.keyword(arg='z', value=ast.Constant(value = threshold))
                return super().generic_visit(node)

            def visit_Call(self, node):
                node = super().generic_visit(node)

                if isinstance(node.func, ast.Attribute) and node.func.attr == 'bottom':
                    if node.args and isinstance(node.args[0], ast.Constant):
                        z_value = node.args[0].value
                        if isinstance(z_value, (int, float)) and z_value < threshold: # Missed this need to adjust.
                            node.args[0] = ast.Constant(value = threshold)

                elif isinstance(node.func, ast.Attribute) and node.func.attr == 'top':
                    if node.args: # Check if there are arguments
                        arg = node.args[0]
                        z_value = None

                        # Handle positive numbers, e.g., top(10)
                        if isinstance(arg, ast.Constant) and isinstance(arg.value, (int, float)):
                            z_value = arg.value
                        # Handle negative numbers, e.g., top(-11)
                        elif (isinstance(arg, ast.UnaryOp) and
                            isinstance(arg.op, ast.USub) and
                            isinstance(arg.operand, ast.Constant)):
                            z_value = -arg.operand.value

                        # If a valid number was found, check it against the threshold
                        if z_value is not None and z_value < -7:
                            # Replace the argument node with a new, corrected constant.
                            #node.args[0] = ast.Constant(value=-7) #Remove the comment to make it replace instantances less than -7.
                            print(f"Top value with large negative: {node.lineno}")

                # 3. Return the fully processed (and possibly modified) node.
                return node
    transformer = Z_Changer()
    new_tree = transformer.visit(tree)
    ast.fix_missing_locations(new_tree)

    # --- REPLACEMENT FOR COMPILE AND EXEC ---
    # 1. Unparse the modified tree back into a string of code
    new_code = astunparse.unparse(new_tree)

    # 2. Open the file in write mode ('w') and save the new code  
    directory_path = "/Users/matt.jednacz/Desktop/Summer_Project/Z_Test/"
    new_filename = "AUDIT_" + os.path.basename(file_path) # Use os.path.basename to be safe
    new_filepath = os.path.join(directory_path, new_filename)

    # 3. Use the new file path string to open the file and write to it
    try:
        with open(new_filepath, 'w') as f: 
            f.write(new_code)
        print(f"Successfully created and wrote to '{new_filename}'")
    except FileExistsError:
        print(f"Error: The file '{new_filename}' already exists. Skipping.")

        print(f"File '{os.path.basename(file_path)}' has been checked and updated.")
    
protocols_directory = 'Z_Test'  # The subdirectory containing your protocol files, please change it to where it is located on your machine. 
# NOTE Not sure if it works on Windows. (test machine = Macboook pro m3, macOS = 14.2)
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

        # Construct the full import path (e.g., 'protocols.protocol_1')
        full_module_import_path = f"{protocols_directory}.{module_name}"

        full_file_path = os.path.join(absolute_protocols_path, filename)
        print(f"--- Processing {filename} ---")
        try:
            # Dynamically import the module
            module = importlib.import_module(full_module_import_path)

            # Initialize a dictionary to store data for this specific protocol
            current_protocol_info = {"filename": filename}
            print("\n Incorrect heights of z:")
            check_z(full_file_path, 0.5)
            print("\n")

        except ImportError as e:
            print(f"Error: Could not import module '{full_module_import_path}'. Ensure file exists and is valid Python. Error: {e}")
        except Exception as e:
            print(f"An unexpected error occurred while processing {filename}: {e}")
        print("-" * 30) # Separator 