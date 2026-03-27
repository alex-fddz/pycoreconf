from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Resolve file paths relative to project root
def resolve_filepath(p):
    """Return an absolute filesystem path for a path relative to the project root.
    If p is None, returns None.
    """
    return str((PROJECT_ROOT / p).resolve()) if p is not None else None
