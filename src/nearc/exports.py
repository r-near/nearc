import ast
from pathlib import Path

from .utils import console


def inject_contract_exports(contract_path: Path) -> Path:
    """
    Inject code to instantiate contract class and export its methods.

    Args:
        contract_path: Path to the contract file

    Returns:
        Path to the possibly modified contract file
    """
    # First read the file
    with open(contract_path) as f:
        content = f.read()

    # Check if we already have any contract exports (assume we don't need to add if present)
    if "# Auto-generated contract exports" in content:
        return contract_path

    # Parse the Python code to find contract classes
    tree = ast.parse(content)

    # Look for classes that might be contracts
    contract_classes = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue

        # Check if this class has methods with export decorators
        has_decorated_methods = False
        for item in node.body:
            if not isinstance(item, ast.FunctionDef):
                continue

            # Check for decorators like @view, @call, @init, @near.export
            export_decorators = {
                "export",
                "view",
                "call",
                "init",
                "callback",
                "multi_callback",
                "near.export",
            }
            for decorator in item.decorator_list:
                name = None

                # Simple name: @export
                if isinstance(decorator, ast.Name):
                    name = decorator.id
                # Call: @export()
                elif isinstance(decorator, ast.Call) and isinstance(
                    decorator.func, ast.Name
                ):
                    name = decorator.func.id
                # Attribute: @near.export
                elif isinstance(decorator, ast.Attribute) and isinstance(
                    decorator.value, ast.Name
                ):
                    if decorator.value.id == "near" and decorator.attr == "export":
                        name = "near.export"

                if name in export_decorators:
                    has_decorated_methods = True
                    break

            if has_decorated_methods:
                break

        if has_decorated_methods:
            contract_classes.append(node.name)

    # If no contract classes found, return the original file
    if not contract_classes:
        return contract_path

    # Generate code to instantiate and export
    export_code = "\n\n# Auto-generated contract exports\n"
    for class_name in contract_classes:
        export_code += f"{class_name.lower()} = {class_name}()\n"

        # Add exports for methods
        # We need to re-analyze the class to find its methods
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef) or node.name != class_name:
                continue

            for item in node.body:
                if not isinstance(item, ast.FunctionDef):
                    continue

                # Skip methods that start with underscore
                if item.name.startswith("_"):
                    continue

                # Check if it has any of our decorators
                has_decorator = False
                export_decorators = {
                    "export",
                    "view",
                    "call",
                    "init",
                    "callback",
                    "multi_callback",
                    "near.export",
                }
                for decorator in item.decorator_list:
                    name = None

                    # Simple name: @export
                    if isinstance(decorator, ast.Name):
                        name = decorator.id
                    # Call: @export()
                    elif isinstance(decorator, ast.Call) and isinstance(
                        decorator.func, ast.Name
                    ):
                        name = decorator.func.id
                    # Attribute: @near.export
                    elif isinstance(decorator, ast.Attribute) and isinstance(
                        decorator.value, ast.Name
                    ):
                        if decorator.value.id == "near" and decorator.attr == "export":
                            name = "near.export"

                    if name in export_decorators:
                        has_decorator = True
                        break

                if has_decorator:
                    export_code += f"{item.name} = {class_name.lower()}.{item.name}\n"

    # Create a modified file with the appended exports
    modified_path = contract_path.parent / f"{contract_path.stem}_with_exports.py"
    with open(modified_path, "w") as f:
        f.write(content)
        f.write(export_code)

    console.print("[cyan]Added contract exports to file[/]")
    return modified_path
