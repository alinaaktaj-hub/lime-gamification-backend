import os


# Keep imports deterministic in tests that load app settings.
os.environ.setdefault("SECRET_KEY", "test-secret-key")
