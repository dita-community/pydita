import os, sys

# Add the python dir to the import path
# so local module imports will work

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
libDir = os.path.abspath(os.path.join(SCRIPT_DIR, '..'))
sys.path.append(libDir)
