import os

# Version shown in generated reports. Update this when cutting a new release.
ASTRA_VERSION = "0.3.3"

# The project folder (the one holding main.py and the JSON data files).
# Paths are built from here so ASTRA works no matter which folder it is run from.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def project_path(*parts):
    """Returns an absolute path inside the project folder."""
    return os.path.join(PROJECT_ROOT, *parts)
