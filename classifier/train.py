"""
Train the complexity classifier and persist it to disk.

Run directly:
    python -m classifier.train
"""

import pathlib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score
import joblib

from classifier.dataset import LABELED_PROMPTS
from classifier.features import extract_features

MODEL_PATH = pathlib.Path(__file__).parent / "model.joblib"


def build_dataset() -> tuple[np.ndarray, np.ndarray]:
    X = np.array([extract_features(prompt) for prompt, _ in LABELED_PROMPTS])
    y = np.array([label for _, label in LABELED_PROMPTS])
    return X, y


def train(save: bool = True) -> tuple[RandomForestClassifier, float]:
    X, y = build_dataset()
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    clf = RandomForestClassifier(
        n_estimators=200,
        max_depth=None,
        min_samples_split=2,
        random_state=42,
        class_weight="balanced",
    )
    clf.fit(X_train, y_train)

    y_pred = clf.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    print(f"Test accuracy: {acc:.2%}")
    print(classification_report(y_test, y_pred, target_names=["Tier1", "Tier2", "Tier3"]))

    if save:
        joblib.dump(clf, MODEL_PATH)
        print(f"Model saved to {MODEL_PATH}")

    return clf, acc


if __name__ == "__main__":
    clf, acc = train()
    if acc < 0.80:
        print(f"WARNING: accuracy {acc:.2%} is below the 80% target.")
