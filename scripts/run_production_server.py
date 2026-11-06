"""
Groww SIP Insight Lab — Local Production Server Runner
======================================================
Simulates the Vercel production environment locally by serving:
1. Static Edge UI from `public/` at root `/`
2. Serverless API routes from `api.index:app` at `/api`

Usage:
    python scripts/run_production_server.py
    python scripts/run_production_server.py --port 3000 --host 0.0.0.0
"""

import sys
import argparse
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Starlette 1.x / FastAPI compatibility patch
try:
    import starlette.routing
    _orig_router_init = starlette.routing.Router.__init__
    def _safe_router_init(self, *args, **kwargs):
        kwargs.pop("on_startup", None)
        kwargs.pop("on_shutdown", None)
        return _orig_router_init(self, *args, **kwargs)
    starlette.routing.Router.__init__ = _safe_router_init
except Exception:
    pass

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from api.index import app as api_app

# Main production wrapper application
prod_app = FastAPI(
    title="Groww SIP Insight Lab (Production Gateway)",
    docs_url=None,
    redoc_url=None,
)

# Mount API routes
prod_app.mount("/api", api_app)

# Mount Static Files from public directory
PUBLIC_DIR = PROJECT_ROOT / "public"
if PUBLIC_DIR.exists():
    prod_app.mount("/", StaticFiles(directory=str(PUBLIC_DIR), html=True), name="static")


def main():
    parser = argparse.ArgumentParser(description="Run Groww SIP Insight Lab Production Server")
    parser.add_argument("--host", default="127.0.0.1", help="Host interface to bind (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=3000, help="Port to listen on (default: 3000)")
    parser.add_argument("--reload", action="store_true", help="Enable live code reload")
    args = parser.parse_args()

    print("=" * 65)
    print("📈 Groww SIP Insight Lab — AI Discovery Engine (Production)")
    print("=" * 65)
    print(f" • Local Web Application : http://{args.host}:{args.port}")
    print(f" • REST API Health Check : http://{args.host}:{args.port}/api/health")
    print(f" • Research Data Endpoint: http://{args.host}:{args.port}/api/stats")
    print("=" * 65)

    uvicorn.run(
        prod_app,
        host=args.host,
        port=args.port,
        log_level="info",
    )


if __name__ == "__main__":
    main()

