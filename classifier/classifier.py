"""
ComplexityClassifier — load (or auto-train) the sklearn model and predict tiers.
"""

from __future__ import annotations

import pathlib
import numpy as np
from typing import Optional

MODEL_PATH = pathlib.Path(__file__).parent / "model.joblib"


class ComplexityClassifier:
    def __init__(self):
        self._clf = None

    def _load_or_train(self):
        import joblib
        if MODEL_PATH.exists():
            self._clf = joblib.load(MODEL_PATH)
        else:
            from classifier.train import train
            self._clf, _ = train(save=True)

    def predict(self, prompt: str) -> int:
        """Return complexity tier: 1, 2, or 3."""
        if self._clf is None:
            self._load_or_train()

        from classifier.features import extract_features
        features = np.array(extract_features(prompt)).reshape(1, -1)
        return int(self._clf.predict(features)[0])

    def predict_proba(self, prompt: str) -> dict:
        """Return class probabilities keyed by tier."""
        if self._clf is None:
            self._load_or_train()

        from classifier.features import extract_features
        features = np.array(extract_features(prompt)).reshape(1, -1)
        proba = self._clf.predict_proba(features)[0]
        classes = self._clf.classes_
        return {int(cls): float(prob) for cls, prob in zip(classes, proba)}


# Module-level singleton — reuses the loaded model across calls
_default_classifier: Optional[ComplexityClassifier] = None


def classify(prompt: str) -> int:
    global _default_classifier
    if _default_classifier is None:
        _default_classifier = ComplexityClassifier()
    return _default_classifier.predict(prompt)
