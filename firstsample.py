import re
import json

INPUT_FILE = "example.sv"
OUTPUT_FILE = "class_ast.json"

def parse_arguments(arg_str):
    """
    Parse SystemVerilog function/task arguments into a list of dictionaries.
    """
    args = []
    arg_str = arg_str.strip()
    if not arg_str:
        return args
    for arg in arg_str.split(","):
        arg = arg.strip()
        match = re.match(r'(rand\s+)?(\w+)(\s*\[.*?\])?\s+(\w+)', arg)
        if match:
            is_rand = bool(match.group(1))
            data_type = match.group(2)
            width = match.group(3).strip() if match.group(3) else None
            name = match.group(4)
            args.append({
                "type": "argument",
                "name": name,
                "data_type": data_type,
                "width": width,
                "rand": is_rand
            })
    return args

def parse_class_refs(content):
    """
    Parse top-level classes fully but represent nested class declarations as references only.
    """
    classes = []

    # Match classes with optional extends
    class_pattern = re.compile(
        r'class\s+(\w+)(?:\s+extends\s+(\w+))?\s*;([\s\S]*?)endclass', re.MULTILINE
    )

    for class_match in class_pattern.finditer(content):
        class_name = class_match.group(1)
        extends_name = class_match.group(2) if class_match.group(2) else None
        class_body = class_match.group(3)

        children = []

        # Parse signals
        signal_pattern = re.compile(
            r'\b(rand\s+)?(int|logic|reg|string|bit|byte|shortint|longint)\b\s*(\[[^\]]+\]\s*)?(\w+)\s*;',
            re.MULTILINE
        )
        for sig_match in signal_pattern.finditer(class_body):
            is_rand = bool(sig_match.group(1))
            data_type = sig_match.group(2)
            width = sig_match.group(3).strip() if sig_match.group(3) else None
            signal_name = sig_match.group(4)
            children.append({
                "type": "signal",
                "name": signal_name,
                "data_type": data_type,
                "width": width,
                "rand": is_rand
            })

        # Parse functions
        func_pattern = re.compile(r'function\s+[\w\s]*\s+(\w+)\s*\((.*?)\)\s*;', re.MULTILINE | re.DOTALL)
        for f_match in func_pattern.finditer(class_body):
            func_name = f_match.group(1)
            arg_str = f_match.group(2)
            func_children = parse_arguments(arg_str)
            children.append({
                "type": "function",
                "name": func_name,
                "children": func_children
            })

        # Parse tasks
        task_pattern = re.compile(r'task\s+(\w+)\s*\((.*?)\)\s*;', re.MULTILINE | re.DOTALL)
        for t_match in task_pattern.finditer(class_body):
            task_name = t_match.group(1)
            arg_str = t_match.group(2)
            task_children = parse_arguments(arg_str)
            children.append({
                "type": "task",
                "name": task_name,
                "children": task_children
            })

        # Parse **nested class declarations as references only**
        nested_class_pattern = re.compile(r'class\s+(\w+)', re.MULTILINE)
        for nested_match in nested_class_pattern.finditer(class_body):
            nested_name = nested_match.group(1)
            if nested_name != class_name:  # avoid including itself
                children.append({
                    "type": "class",
                    "name": nested_name
                })

        classes.append({
            "type": "class",
            "name": class_name,
            "extends": extends_name,
            "children": children
        })

    return classes

def main():
    with open(INPUT_FILE, "r") as f:
        content = f.read()

    ast = parse_class_refs(content)

    with open(OUTPUT_FILE, "w") as f:
        json.dump(ast, f, indent=4)

    print(f"AST dumped to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
