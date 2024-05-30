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
    try_blocks = 0
    catch_blocks = 0
    finally_blocks = 0
    if_branches_with_logs = 0
    else_branches_with_logs = 0
    switch_cases_with_logs = 0
    try_blocks_with_logs = 0
    catch_blocks_with_logs = 0
    finally_blocks_with_logs = 0
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

    if isinstance(node, javalang.tree.TryStatement):
        try_blocks += 1
        if any(contains_slf4j_logging(stmt, slf4j_loggers) for stmt in node.block):
            try_blocks_with_logs += 1
            for stmt in node.block:
                log_positions.extend(find_logging_positions(stmt, slf4j_loggers))
        if node.catches:
            for catch_clause in node.catches:
                catch_blocks += 1
                if any(contains_slf4j_logging(stmt, slf4j_loggers) for stmt in catch_clause.block):
                    catch_blocks_with_logs += 1
                    for stmt in catch_clause.block:
                        log_positions.extend(find_logging_positions(stmt, slf4j_loggers))
                        
        if node.finally_block:
            finally_blocks += 1
            if any(contains_slf4j_logging(stmt, slf4j_loggers) for stmt in node.finally_block):
                finally_blocks_with_logs += 1
                for stmt in node.finally_block:
                    log_positions.extend(find_logging_positions(stmt, slf4j_loggers))

    if hasattr(node, 'children'):
        for child in node.children:
            if isinstance(child, list):
                for sub_child in child:
                    ib, eb, sb, tb, cb, fb, ibwl, ebwl, sbwl, tbwl, cbwl, fbwl, lp = count_branches(sub_child, slf4j_loggers)
                    if_branches += ib
                    else_branches += eb
                    switch_cases += sb
                    try_blocks += tb
                    catch_blocks += cb
                    finally_blocks += fb
                    if_branches_with_logs += ibwl
                    else_branches_with_logs += ebwl
                    switch_cases_with_logs += sbwl
                    try_blocks_with_logs += tbwl
                    catch_blocks_with_logs += cbwl
                    finally_blocks_with_logs += fbwl
                    log_positions.extend(lp)
            elif child:
                ib, eb, sb, tb, cb, fb, ibwl, ebwl, sbwl, tbwl, cbwl, fbwl, lp = count_branches(child, slf4j_loggers)
                if_branches += ib
                else_branches += eb
                switch_cases += sb
                try_blocks += tb
                catch_blocks += cb
                if_branches_with_logs += ibwl
                else_branches_with_logs += ebwl
                switch_cases_with_logs += sbwl
                try_blocks_with_logs += tbwl
                catch_blocks_with_logs += cbwl
                log_positions.extend(lp)

    return (if_branches, else_branches, switch_cases, try_blocks, catch_blocks, finally_blocks,
            if_branches_with_logs, else_branches_with_logs, switch_cases_with_logs,
            try_blocks_with_logs, catch_blocks_with_logs, finally_blocks_with_logs, log_positions)

def parse_java_files(directory):
    if_branches = 0
    else_branches = 0
    switch_cases = 0
    try_blocks = 0
    catch_blocks = 0
    finally_blocks = 0
    if_branches_with_logs = 0
    else_branches_with_logs = 0
    switch_cases_with_logs = 0
    try_blocks_with_logs = 0
    catch_blocks_with_logs = 0
    finally_blocks_with_logs = 0
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
                            ib, eb, sb, tb, cb, fb, ibwl, ebwl, sbwl, tbwl, cbwl, fbwl, lp = count_branches(node, slf4j_loggers)
                            if_branches += ib
                            else_branches += eb
                            switch_cases += sb
                            try_blocks += tb
                            catch_blocks += cb
                            finally_blocks += fb
                            if_branches_with_logs += ibwl
                            else_branches_with_logs += ebwl
                            switch_cases_with_logs += sbwl
                            try_blocks_with_logs += tbwl
                            catch_blocks_with_logs += cbwl
                            finally_blocks_with_logs += fbwl
                            for pos in lp:
                                branches_with_log_positions.append((file, pos))
                    except (javalang.parser.JavaSyntaxError, IndexError) as e:
                        print(f"Error parsing {file_path}: {e}")

    return (if_branches, else_branches, switch_cases, try_blocks, catch_blocks, finally_blocks,
            if_branches_with_logs, else_branches_with_logs, switch_cases_with_logs,
            try_blocks_with_logs, catch_blocks_with_logs, finally_blocks_with_logs, branches_with_log_positions)
    
def report_number(topics):
    for topic in topics:
        try:
            print(f"Number of {topic} with SLF4J logging: {topics[topic][1]}/{topics[topic][0]}")
        except ZeroDivisionError:
            print(f"Number of {topic} with SLF4J logging: 0/0")

def report_percentage(topics):
    for topic in topics:
        try:
            print(f"Percentage of {topic} with SLF4J logging: {topics[topic][1]/topics[topic][0]*100:.2f}%")
        except ZeroDivisionError:
            print(f"Percentage of {topic} with SLF4J logging: 0.00%")

def analyze_repository(repository_path):
    total_if_branches = 0
    total_else_branches = 0
    total_switch_cases = 0
    total_try_blocks = 0
    total_catch_blocks = 0
    total_finally_blocks = 0
    total_if_branches_with_logs = 0
    total_else_branches_with_logs = 0
    total_switch_cases_with_logs = 0
    total_try_blocks_with_logs = 0
    total_catch_blocks_with_logs = 0
    total_finally_blocks_with_logs = 0
    total_log_positions = []

    jacoco_reports = find_jacoco_reports(repository_path)
    covered_lines = set()
    for report in jacoco_reports:
        covered_lines.update(parse_jacoco_report(report))

    java_dirs = [d for d in os.listdir(repository_path) if os.path.isdir(os.path.join(repository_path, d))]
    for java_dir in java_dirs:
        full_java_dir = os.path.join(repository_path, java_dir)
        if_branches, else_branches, switch_cases, try_blocks, catch_blocks, finally_block, if_branches_with_logs, else_branches_with_logs, switch_cases_with_logs, try_blocks_with_logs, catch_blocks_with_logs, finally_blocks_with_logs, log_positions = parse_java_files(full_java_dir)

        total_if_branches += if_branches
        total_else_branches += else_branches
        total_switch_cases += switch_cases
        total_try_blocks += try_blocks
        total_catch_blocks += catch_blocks
        total_finally_blocks += finally_block
        total_if_branches_with_logs += if_branches_with_logs
        total_else_branches_with_logs += else_branches_with_logs
        total_switch_cases_with_logs += switch_cases_with_logs
        total_try_blocks_with_logs += try_blocks_with_logs
        total_catch_blocks_with_logs += catch_blocks_with_logs
        total_finally_blocks_with_logs += finally_blocks_with_logs
        total_log_positions.extend(log_positions)

    total_branches = total_if_branches + total_else_branches + total_switch_cases + total_try_blocks + total_catch_blocks + total_finally_blocks
    branches_with_logs = total_if_branches_with_logs + total_else_branches_with_logs + total_switch_cases_with_logs + total_try_blocks_with_logs + total_catch_blocks_with_logs + total_finally_blocks_with_logs

    covered_log_branches = sum(1 for file, line in total_log_positions if (file, line) in covered_lines)

    if total_branches > 0:
        percent_with_logs = (branches_with_logs / total_branches) * 100
    else:
        percent_with_logs = 0

    if branches_with_logs > 0:
        percent_covered = (covered_log_branches / branches_with_logs) * 100
    else:
        percent_covered = 0
        
    topics = {'if branches': (total_if_branches, total_if_branches_with_logs),
              'else branches': (total_else_branches, total_else_branches_with_logs),
              'switch cases': (total_switch_cases, total_switch_cases_with_logs),
              'try blocks': (total_try_blocks, total_try_blocks_with_logs),
              'catch blocks': (total_catch_blocks, total_catch_blocks_with_logs),
              'finally blocks': (total_finally_blocks, total_finally_blocks_with_logs),
              'total branches': (total_branches, branches_with_logs)}

    
    report_number(topics)
    print('-'*60)
    report_percentage(topics)
    print('-'*60)
    print(f"Total number of branches with SLF4J logging: {branches_with_logs}")
    print(f"Number of branches with SLF4J logging covered by tests: {covered_log_branches}")
    print(f"Percentage of branches with SLF4J logging covered by tests: {percent_covered:.2f}%")

# Specify the root directory of your project
repository_path = './wro4j'
analyze_repository(repository_path)
