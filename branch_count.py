import os
import xml.etree.ElementTree as ET
import javalang

def find_jacoco_reports(root_dir):
    jacoco_reports = []
    for root, dirs, files in os.walk(root_dir):
        if 'pom.xml' in files:
            report_path = os.path.join(root, 'target', 'site', 'jacoco', 'jacoco.xml')
            if os.path.exists(report_path):
                jacoco_reports.append(report_path)
    return jacoco_reports

def parse_jacoco_report(jacoco_report_path):
    covered_lines = set()
    tree = ET.parse(jacoco_report_path)
    root = tree.getroot()

    for package in root.findall('package'):
        for sourcefile in package.findall('sourcefile'):
            for line in sourcefile.findall('line'):
                if line.get('ci') != '0':  # 'ci' attribute indicates covered instructions
                    line_number = int(line.get('nr'))
                    covered_lines.add((sourcefile.get('name'), line_number))
    return covered_lines

def contains_slf4j_logging(node, slf4j_loggers):
    if isinstance(node, javalang.tree.StatementExpression):
        if isinstance(node.expression, javalang.tree.MethodInvocation):
            if node.expression.qualifier in slf4j_loggers:
                return True
    return False

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

def find_logging_positions(node, slf4j_loggers):
    log_positions = []
    if contains_slf4j_logging(node, slf4j_loggers):
        if node.position:
            log_positions.append(node.position.line)
    
    if hasattr(node, 'children'):
        for child in node.children:
            if isinstance(child, list):
                for sub_child in child:
                    log_positions.extend(find_logging_positions(sub_child, slf4j_loggers))
            elif child:
                log_positions.extend(find_logging_positions(child, slf4j_loggers))
    
    return log_positions

def count_branches(node, slf4j_loggers):
    if_branches = 0
    else_branches = 0
    switch_cases = 0
    if_branches_with_logs = 0
    else_branches_with_logs = 0
    switch_cases_with_logs = 0
    log_positions = []

    if isinstance(node, javalang.tree.IfStatement):
        if_branches += 1
        if hasattr(node.then_statement, 'statements'):
            if any(contains_slf4j_logging(stmt, slf4j_loggers) for stmt in node.then_statement.statements):
                if_branches_with_logs += 1
                for stmt in node.then_statement.statements:
                    log_positions.extend(find_logging_positions(stmt, slf4j_loggers))
        else:
            if contains_slf4j_logging(node.then_statement, slf4j_loggers):
                if_branches_with_logs += 1
                log_positions.extend(find_logging_positions(node.then_statement, slf4j_loggers))
        if node.else_statement is not None:
            else_branches += 1
            if hasattr(node.else_statement, 'statements'):
                if any(contains_slf4j_logging(stmt, slf4j_loggers) for stmt in node.else_statement.statements):
                    else_branches_with_logs += 1
                    for stmt in node.else_statement.statements:
                        log_positions.extend(find_logging_positions(stmt, slf4j_loggers))
            else:
                if contains_slf4j_logging(node.else_statement, slf4j_loggers):
                    else_branches_with_logs += 1
                    log_positions.extend(find_logging_positions(node.else_statement, slf4j_loggers))

    if isinstance(node, javalang.tree.SwitchStatementCase):
        switch_cases += 1
        if any(contains_slf4j_logging(stmt, slf4j_loggers) for stmt in node.statements):
            switch_cases_with_logs += 1
            for stmt in node.statements:
                log_positions.extend(find_logging_positions(stmt, slf4j_loggers))

    if hasattr(node, 'children'):
        for child in node.children:
            if isinstance(child, list):
                for sub_child in child:
                    ib, eb, sb, ibwl, ebwl, sbwl, lp = count_branches(sub_child, slf4j_loggers)
                    if_branches += ib
                    else_branches += eb
                    switch_cases += sb
                    if_branches_with_logs += ibwl
                    else_branches_with_logs += ebwl
                    switch_cases_with_logs += sbwl
                    log_positions.extend(lp)
            elif child:
                ib, eb, sb, ibwl, ebwl, sbwl, lp = count_branches(child, slf4j_loggers)
                if_branches += ib
                else_branches += eb
                switch_cases += sb
                if_branches_with_logs += ibwl
                else_branches_with_logs += ebwl
                switch_cases_with_logs += sbwl
                log_positions.extend(lp)

    return if_branches, else_branches, switch_cases, if_branches_with_logs, else_branches_with_logs, switch_cases_with_logs, log_positions

def parse_java_files(directory):
    if_branches = 0
    else_branches = 0
    switch_cases = 0
    if_branches_with_logs = 0
    else_branches_with_logs = 0
    switch_cases_with_logs = 0
    branches_with_log_positions = []
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
                            ib, eb, sb, ibwl, ebwl, sbwl, lp = count_branches(node, slf4j_loggers)
                            if_branches += ib
                            else_branches += eb
                            switch_cases += sb
                            if_branches_with_logs += ibwl
                            else_branches_with_logs += ebwl
                            switch_cases_with_logs += sbwl
                            for pos in lp:
                                branches_with_log_positions.append((file, pos))
                    except (javalang.parser.JavaSyntaxError, IndexError) as e:
                        print(f"Error parsing {file_path}: {e}")

    return if_branches, else_branches, switch_cases, if_branches_with_logs, else_branches_with_logs, switch_cases_with_logs, branches_with_log_positions

def check_log_coverage(branches_with_log_positions, covered_lines):
    covered_log_branches = 0
    for file, line in branches_with_log_positions:
        if (file, line) in covered_lines:
            covered_log_branches += 1
    return covered_log_branches

# Define the root directory containing all the project directories
root_directory = '.'

jacoco_reports = find_jacoco_reports(root_directory)
all_covered_lines = set()

for report in jacoco_reports:
    covered_lines = parse_jacoco_report(report)
    all_covered_lines.update(covered_lines)

if_branches = 0
else_branches = 0
switch_cases = 0
if_branches_with_logs = 0
else_branches_with_logs = 0
switch_cases_with_logs = 0
branches_with_log_positions = []

for root, dirs, files in os.walk(root_directory):
    if 'pom.xml' in files:
        java_dir = os.path.join(root, 'src')
        if os.path.exists(java_dir):
            ib, eb, sb, ibwl, ebwl, sbwl, log_positions = parse_java_files(java_dir)
            if_branches += ib
            else_branches += eb
            switch_cases += sb
            if_branches_with_logs += ibwl
            else_branches_with_logs += ebwl
            switch_cases_with_logs += sbwl
            branches_with_log_positions.extend(log_positions)

print(branches_with_log_positions)

covered_log_branches = check_log_coverage(branches_with_log_positions, all_covered_lines)
total_log_branches = len(branches_with_log_positions)

if total_log_branches > 0:
    percent_covered = (covered_log_branches / total_log_branches) * 100
else:
    percent_covered = 0

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
print('-'*60)
print(f"Total number of branches with SLF4J logging: {total_log_branches}")
print(f"Number of branches with SLF4J logging covered by tests: {covered_log_branches}")
print(f"Percentage of branches with SLF4J logging covered by tests: {percent_covered:.2f}%")
