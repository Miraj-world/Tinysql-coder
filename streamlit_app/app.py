"""Cloud entry point for the TinySQL Lab portfolio demo."""

from pathlib import Path
import runpy


runpy.run_path(Path(__file__).resolve().parents[1] / "app.py", run_name="__main__")
