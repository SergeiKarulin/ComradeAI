def translate_dsl(dsl_commands):
    python_lines = []  # Store the translated Python lines
    for line in dsl_commands.split('\n'):
        if 'pass' in line and 'iterate' in line:  # Check if line uses the DSL keywords
            # Split the line based on the DSL keywords
            parts = line.split(' pass ')
            operation_part = parts[0].strip()
            func_and_result = parts[1].split(' iterate ')
            func_name = func_and_result[0].strip()
            result_var = func_and_result[1].strip()
            
            # Process the operations part for list operations and string addition
            ops_parts = operation_part.split(' + ')
            list_vars = ops_parts[:-1]  # Extract list variables
            string_var = ops_parts[-1].strip()  # Isolate the string variable
            
            # Correctly format the .extend() and .append() operation without leading spaces
            extend_operation = f"{list_vars[0]}.extend({list_vars[1]})"
            append_operation = f"{list_vars[0]}.append({string_var})"
            
            # Prepare operations and the final function call
            python_lines.append(extend_operation)
            python_lines.append(append_operation)
            python_line = f"{result_var} = {func_name}({list_vars[0]})"
            python_lines.append(python_line)
        else:
            # Directly append lines that don't need translation
            python_lines.append(line)
    
    return '\n'.join(python_lines)

# DSL Input using "pass" and "iterate" as the keywords
dsl_input = """
list1 = ["str1", "str2"]
list2 = ["str3", "str4"]
string = "hello"
list1 + list2 + string pass myfunc iterate result
"""

# Translate DSL to Python
translated_python = translate_dsl(dsl_input)
print(translated_python)
exec(translated_python)