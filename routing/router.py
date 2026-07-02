"""
ComplexityRouter — classify a prompt and map it to a model_id via routing_config.yaml.
"""

from __future__ import annotations

import pathlib
from dataclasses import dataclass
from typing import Optional, List
import yaml

from classifier.classifier import classify

_CONFIG_PATH = pathlib.Path(__file__).parent / "routing_config.yaml"
_config_cache: Optional[dict] = None


def _load_config() -> dict:
    global _config_cache
    if _config_cache is None:
        with open(_CONFIG_PATH) as f:
            raw = yaml.safe_load(f)
        _config_cache = {int(k): v for k, v in raw["routing"].items()}
    return _config_cache


@dataclass
class RoutingDecision:
    tier: int
    tier_name: str
    model_id: str
    fallback_models: List[str]
    description: str

    @property
    def fallback_model_id(self) -> str:
        """First fallback — kept for backward compatibility."""
        return self.fallback_models[0] if self.fallback_models else ""


def route(prompt: str) -> RoutingDecision:
    """Classify prompt complexity and return the routing decision."""
    tier = classify(prompt)
    config = _load_config()
    entry = config[tier]
    return RoutingDecision(
        tier=tier,
        tier_name=entry["tier_name"],
        model_id=entry["primary"],
        fallback_models=entry.get("fallbacks", []),
        description=entry["description"],
    )


def reload_config() -> None:
    """Force a reload of the YAML routing config (useful after hot-swap edits)."""
    global _config_cache
    _config_cache = None
    _load_config()
