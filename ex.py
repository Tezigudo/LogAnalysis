import javalang

# Java source code
java_code = """
public class Example {
    public void test(int x) {
        if (x > 0) {
            System.out.println("Positive");
        } else {
            System.out.println("Non-positive");
        }
    }
}
"""

# Parse the Java code
tokens = javalang.tokenizer.tokenize(java_code)
parser = javalang.parser.Parser(tokens)
tree = parser.parse()

# Traverse the AST to find the if statement
for path, node in tree:
    if isinstance(node, javalang.tree.IfStatement):
        print("Found an if statement")
        print(f"Condition: {node.condition}")
        print(f"Then statement: {node.then_statement}")
        print(f"Else statement: {node.else_statement}")
