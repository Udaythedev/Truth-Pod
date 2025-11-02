import os
import sys

# Ensure SDK src path is available for tests when package isn't installed.
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
SDK_SRC = os.path.join(ROOT, 'device_sdk', 'src')
if os.path.isdir(SDK_SRC) and SDK_SRC not in sys.path:
    sys.path.insert(0, SDK_SRC)
