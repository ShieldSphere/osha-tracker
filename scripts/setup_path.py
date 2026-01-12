"""
Path setup for scripts.

Import this at the top of any script that needs to import from src:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))

Or simply run scripts from the project root directory.
"""
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
