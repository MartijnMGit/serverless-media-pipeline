import importlib.util
import sys
from pathlib import Path

LAMBDAS_DIR = Path(__file__).parent.parent / "lambdas"


def load_lambda_handler(function_dir: str):
    """Load a Lambda's handler.py as an isolated module.

    Every Lambda has a file literally named handler.py, so a plain
    `import handler` would collide between test files via sys.modules.
    Loading each one under a unique name avoids that.
    """
    module_name = f"{function_dir}_handler"
    path = LAMBDAS_DIR / function_dir / "handler.py"
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module
