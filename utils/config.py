"""Shared config loader for rss-flask.

Resolves config.yml from the project root first, then falls back to cwd.
Both cache_store and scheduler import from here to stay in sync.
"""

import logging
from pathlib import Path

import yaml

_root_dir = Path(__file__).resolve().parents[1]


def load_config() -> dict:
    """Load and parse config.yml, returning a dict of key-value pairs."""
    config_data: dict = {}
    config_path = _root_dir / "config.yml"

    if not config_path.exists():
        fallback_path = Path.cwd() / "config.yml"
        if fallback_path != config_path and fallback_path.exists():
            config_path = fallback_path

    if config_path.exists():
        try:
            with open(config_path) as config_file:
                config_data = yaml.safe_load(config_file) or {}
                logging.info(f"Loaded config.yml from {config_path}")
        except yaml.YAMLError as exc:
            logging.warning("Failed to parse config.yml at %s: %s", config_path, exc)
    else:
        logging.warning(
            "config.yml not found at %s or %s, using defaults.",
            _root_dir / "config.yml",
            Path.cwd() / "config.yml",
        )

    return config_data
