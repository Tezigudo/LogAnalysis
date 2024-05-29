import os
import javalang

def contains_slf4j_logging(node, slf4j_loggers):
    if isinstance(node, javalang.tree.StatementExpression):
        if isinstance(node.expression, javalang.tree.MethodInvocation):
            if node.expression.qualifier in slf4j_loggers:
                return True
    return False

def collect_slf4j_loggers(node, slf4j_loggers):
    if isinstance(node, javalang.tree.VariableDeclarator):
        if isinstance(node.initializer, javalang.tree.MethodInvocation):
            if (node.initializer.qualifier == 'LoggerFactory' and
                node.initializer.member == 'getLogger'):
                slf4j_loggers.add(node.name)
    
    if hasattr(node, 'children'):
        for child in node.children:
            if isinstance(child, list):
                for sub_child in child:
                    collect_slf4j_loggers(sub_child, slf4j_loggers)
            elif child:
                collect_slf4j_loggers(child, slf4j_loggers)

def count_branches(node, slf4j_loggers):
    if_branches = 0
    else_branches = 0
    switch_cases = 0
    if_branches_with_logs = 0
    else_branches_with_logs = 0
    switch_cases_with_logs = 0

    if isinstance(node, javalang.tree.IfStatement):
        if_branches += 1
        if hasattr(node.then_statement, 'statements'):
            if any(contains_slf4j_logging(stmt, slf4j_loggers) for stmt in node.then_statement.statements):
                if_branches_with_logs += 1
        else:
            if contains_slf4j_logging(node.then_statement, slf4j_loggers):
                if_branches_with_logs += 1
        if node.else_statement is not None:
            else_branches += 1
            if hasattr(node.else_statement, 'statements'):
                if any(contains_slf4j_logging(stmt, slf4j_loggers) for stmt in node.else_statement.statements):
                    else_branches_with_logs += 1
            else:
                if contains_slf4j_logging(node.else_statement, slf4j_loggers):
                    else_branches_with_logs += 1

    if isinstance(node, javalang.tree.SwitchStatementCase):
        switch_cases += 1
        if any(contains_slf4j_logging(stmt, slf4j_loggers) for stmt in node.statements):
            switch_cases_with_logs += 1

    if hasattr(node, 'children'):
        for child in node.children:
            if isinstance(child, list):
                for sub_child in child:
                    ib, eb, sb, ibwl, ebwl, sbwl = count_branches(sub_child, slf4j_loggers)
                    if_branches += ib
                    else_branches += eb
                    switch_cases += sb
                    if_branches_with_logs += ibwl
                    else_branches_with_logs += ebwl
                    switch_cases_with_logs += sbwl
            elif child:
                ib, eb, sb, ibwl, ebwl, sbwl = count_branches(child, slf4j_loggers)
                if_branches += ib
                else_branches += eb
                switch_cases += sb
                if_branches_with_logs += ibwl
                else_branches_with_logs += ebwl
                switch_cases_with_logs += sbwl

    return (if_branches, else_branches, switch_cases,
            if_branches_with_logs, else_branches_with_logs, switch_cases_with_logs)

def parse_java_files(directory):
    if_branches = 0
    else_branches = 0
    switch_cases = 0
    if_branches_with_logs = 0
    else_branches_with_logs = 0
    switch_cases_with_logs = 0
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.java'):
                file_path = os.path.join(root, file)
                with open(file_path, 'r') as f:
                    code = f.read()
                    try:
                        tree = javalang.parse.parse(code)
                        slf4j_loggers = set()
                        if any('org.slf4j.Logger' in str(imp) or 'org.slf4j.LoggerFactory' in str(imp) for imp in tree.imports):
                            for path, node in tree.filter(javalang.tree.VariableDeclarator):
                                collect_slf4j_loggers(node, slf4j_loggers)
                        for path, node in tree:
                            ib, eb, sb, ibwl, ebwl, sbwl = count_branches(node, slf4j_loggers)
                            if_branches += ib
                            else_branches += eb
                            switch_cases += sb
                            if_branches_with_logs += ibwl
                            else_branches_with_logs += ebwl
                            switch_cases_with_logs += sbwl
                    except (javalang.parser.JavaSyntaxError, IndexError) as e:
                        print(f"Error parsing {file_path}: {e}")

    return (if_branches, else_branches, switch_cases,
            if_branches_with_logs, else_branches_with_logs, switch_cases_with_logs)

repository_path = './wro4j'

if_branches, else_branches, switch_cases, if_branches_with_logs, else_branches_with_logs, switch_cases_with_logs = parse_java_files(repository_path)

total_branches = if_branches + else_branches + switch_cases
branches_with_logs = if_branches_with_logs + else_branches_with_logs + switch_cases_with_logs

if total_branches > 0:
    percent_with_logs = (branches_with_logs / total_branches) * 100
else:
    percent_with_logs = 0

print(f"Number of if branches with SLF4J logging: {if_branches_with_logs}/{if_branches}")
print(f"Number of else branches with SLF4J logging: {else_branches_with_logs}/{else_branches}")
print(f"Number of switch cases with SLF4J logging: {switch_cases_with_logs}/{switch_cases}")
print(f"Number of total branches with SLF4J logging: {branches_with_logs}/{total_branches}")
print('-'*60)
print(f"Percentage of if branches with SLF4J logging: {if_branches_with_logs/if_branches*100:.2f}%")
print(f"Percentage of else branches with SLF4J logging: {else_branches_with_logs/else_branches*100:.2f}%")
print(f"Percentage of switch cases with SLF4J logging: {switch_cases_with_logs/switch_cases*100:.2f}%")
print(f"Percentage of branches with SLF4J logging: {percent_with_logs:.2f}%")
