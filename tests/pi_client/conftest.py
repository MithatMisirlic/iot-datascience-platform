"""Make the independently runnable Pi client package importable in tests."""

from pathlib import Path
import sys


PI_CLIENT_ROOT = Path(__file__).resolve().parents[2] / "pi-client"
sys.path.insert(0, str(PI_CLIENT_ROOT))
