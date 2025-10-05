#!/usr/bin/env python3
"""
WARD OPS - Network Monitoring Dashboard
Entry point for the application
"""
import logging
import uvicorn

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=5001,
        reload=True,
        log_level="info",
        forwarded_allow_ips="*",  # Allow all IPs (for Docker/reverse proxy)
    )
