"""
SIP Insight Lab — Dashboard Runner (Phase 5)
============================================
Launches the Streamlit discovery dashboard:
    python scripts/run_dashboard.py [--port 8501]
"""

import sys
import subprocess
import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
APP_PATH = PROJECT_ROOT / "src" / "dashboard" / "app.py"


def main():
    parser = argparse.ArgumentParser(description="Run SIP Insight Lab Streamlit Dashboard")
    parser.add_argument("--port", type=int, default=8501, help="Port to run Streamlit on")
    parser.add_argument("--host", type=str, default="localhost", help="Host address")
    args = parser.parse_args()

    cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(APP_PATH),
        "--server.port",
        str(args.port),
        "--server.address",
        args.host,
    ]
    print(f"Launching Streamlit dashboard at http://{args.host}:{args.port} ...")
    subprocess.run(cmd)


if __name__ == "__main__":
    main()

