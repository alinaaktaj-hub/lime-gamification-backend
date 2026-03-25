import os
import sys
from pathlib import Path


# Keep imports deterministic in tests that load app settings.
os.environ.setdefault("SECRET_KEY", "test-secret-key")

# Make the repo root importable when pytest is launched via its console script.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
