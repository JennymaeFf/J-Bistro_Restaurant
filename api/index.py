# api/index.py  - Vercel serverless entry point
# Must live in the `api/` folder so Vercel's Python runtime picks it up.
# It imports the Flask `app` object from the project root.

import os
import sys

# Add the project root to sys.path so all imports resolve correctly.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app import app  # noqa: F401  (Vercel looks for a variable named `app`)
