#!/usr/bin/env python3
"""
Initialize deployments from deployments.json
Registers all instances in the Master DB
"""
import json
from pathlib import Path
from database import register_deployment

CONFIG_PATH = Path(__file__).parent / "deployments.json"


def init_deployments():
    """Load and register all deployments"""
    if not CONFIG_PATH.exists():
        print(f"❌ Config file not found: {CONFIG_PATH}")
        return

    with open(CONFIG_PATH) as f:
        config = json.load(f)

    for deployment in config["deployments"]:
        register_deployment(deployment["id"], deployment)
        print(f"✅ Registered: {deployment['id']} ({deployment['name']})")

    print(f"\n✅ Initialized {len(config['deployments'])} deployments")


if __name__ == "__main__":
    init_deployments()
