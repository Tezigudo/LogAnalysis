import os
import javalang

# Define a function to check if a statement contains SLF4J logging
def contains_slf4j_logging(node, slf4j_loggers):
    if isinstance(node, javalang.tree.StatementExpression):
        if isinstance(node.expression, javalang.tree.MethodInvocation):
            if node.expression.qualifier in slf4j_loggers:
                return True
    return False

# Function to collect SLF4J logger variable names
def collect_slf4j_loggers(node, slf4j_loggers):
    if isinstance(node, javalang.tree.VariableDeclarator):
        if isinstance(node.initializer, javalang.tree.MethodInvocation):
            if node.initializer.qualifier == 'LoggerFactory' and node.initializer.member == 'getLogger':
                slf4j_loggers.add(node.name)

    if hasattr(node, 'children'):
        for child in node.children:
            if isinstance(child, list):
                for sub_child in child:
                    collect_slf4j_loggers(sub_child, slf4j_loggers)
            elif child:
                collect_slf4j_loggers(child, slf4j_loggers)

# Function to recursively count all conditional branches and those with logs
def count_branches(node, slf4j_loggers):
    total_branches = 0
    branches_with_logs = 0
    
    if isinstance(node, (javalang.tree.IfStatement, javalang.tree.SwitchStatementCase)):
        total_branches += 1
        if any(contains_slf4j_logging(stmt, slf4j_loggers) for stmt in node.body):
            branches_with_logs += 1
    
    # Recursively check child nodes
    if hasattr(node, 'children'):
        for child in node.children:
            if isinstance(child, list):
                for sub_child in child:
                    tb, bwl = count_branches(sub_child, slf4j_loggers)
                    total_branches += tb
                    branches_with_logs += bwl
            elif child:
                tb, bwl = count_branches(child, slf4j_loggers)
                total_branches += tb
                branches_with_logs += bwl
    
    return total_branches, branches_with_logs

# Function to parse Java files in a directory
def parse_java_files(directory):
    total_branches = 0
    branches_with_logs = 0
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.java'):
                file_path = os.path.join(root, file)
                with open(file_path, 'r') as f:
                    code = f.read()
                    try:
                        tree = javalang.parse.parse(code)
                        import_declarations = [imp.path for imp in tree.imports]
                        slf4j_loggers = set()

                        if any('org.slf4j.Logger' in imp or 'org.slf4j.LoggerFactory' in imp for imp in import_declarations):
                            # Collect SLF4J logger variable names
                            collect_slf4j_loggers(tree, slf4j_loggers)
                        # Count all branches and branches with SLF4J logging
                        tb, bwl = count_branches(tree, slf4j_loggers)
                        total_branches += tb
                        branches_with_logs += bwl
                    except (javalang.parser.JavaSyntaxError, IndexError) as e:
                        print(f"Error parsing {file_path}: {e}")
    
    return total_branches, branches_with_logs

# Define the path to your Java repository
repository_path = './jodd/'

# Get the count of all conditional branches and those with SLF4J logging
total_branches, branches_with_logs = parse_java_files(repository_path)

# Calculate percentage
if total_branches > 0:
    percent_with_logs = (branches_with_logs / total_branches) * 100
else:
    percent_with_logs = 0

print(f"Total number of conditional branches: {total_branches}")
print(f"Number of conditional branches with SLF4J logging: {branches_with_logs}")
print(f"Percentage of branches with SLF4J logging: {percent_with_logs:.2f}%")
