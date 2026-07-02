"""Tests for Phase 2: Complexity Classifier and Router."""

import pytest
import numpy as np

from classifier.features import extract_features, FEATURE_NAMES
from classifier.dataset import LABELED_PROMPTS
from classifier.train import build_dataset, train
from classifier.classifier import ComplexityClassifier, classify
from routing.router import route, RoutingDecision


# ── Feature extraction ──────────────────────────────────────────────────────

def test_feature_vector_length():
    features = extract_features("What is the capital of France?")
    assert len(features) == len(FEATURE_NAMES)


def test_feature_names_match_vector():
    features = extract_features("Summarize this article.")
    assert len(features) == len(FEATURE_NAMES)


def test_simple_prompt_low_features():
    features = extract_features("What is 2 + 2?")
    tier3_ratio = features[5]  # tier3_keyword_ratio
    assert tier3_ratio == 0.0, "Simple math question should have no tier-3 keywords"


def test_complex_prompt_high_features():
    prompt = "Design a scalable microservices architecture for a real-time payment system."
    features = extract_features(prompt)
    tier3_ratio = features[5]  # tier3_keyword_ratio
    assert tier3_ratio > 0.0, "Complex prompt should hit tier-3 keywords"


def test_word_count_feature_scales():
    short = extract_features("Hello world")
    long = extract_features(" ".join(["word"] * 200))
    assert long[0] > short[0], "Longer prompt should have larger word_count_norm"


def test_question_mark_feature():
    features = extract_features("What is your name? And where are you from?")
    assert features[9] == 2.0


# ── Dataset ─────────────────────────────────────────────────────────────────

def test_dataset_has_200_plus_entries():
    assert len(LABELED_PROMPTS) >= 200


def test_dataset_labels_are_valid():
    for prompt, label in LABELED_PROMPTS:
        assert label in {1, 2, 3}, f"Invalid label {label} for: {prompt[:60]}"


def test_dataset_all_tiers_represented():
    labels = {label for _, label in LABELED_PROMPTS}
    assert labels == {1, 2, 3}


def test_dataset_prompts_are_nonempty():
    for prompt, _ in LABELED_PROMPTS:
        assert prompt.strip(), "Empty prompt found in dataset"


# ── Training ─────────────────────────────────────────────────────────────────

def test_build_dataset_shapes():
    X, y = build_dataset()
    assert X.shape[0] == len(LABELED_PROMPTS)
    assert X.shape[1] == len(FEATURE_NAMES)
    assert y.shape[0] == len(LABELED_PROMPTS)


def test_train_accuracy_above_threshold():
    _, acc = train(save=False)
    assert acc >= 0.80, f"Classifier accuracy {acc:.2%} is below the 80% target"


# ── Classifier ───────────────────────────────────────────────────────────────

def test_classifier_returns_valid_tier():
    clf = ComplexityClassifier()
    tier = clf.predict("What is the capital of Japan?")
    assert tier in {1, 2, 3}


def test_classifier_simple_prompt_predicts_tier1():
    clf = ComplexityClassifier()
    tier = clf.predict("What is 5 times 6?")
    assert tier == 1, f"Expected tier 1 for simple math, got {tier}"


def test_classifier_complex_prompt_predicts_tier3():
    clf = ComplexityClassifier()
    prompt = (
        "Design a globally distributed, fault-tolerant event sourcing system "
        "with CQRS for a banking application, analyzing trade-offs between "
        "strong and eventual consistency models."
    )
    tier = clf.predict(prompt)
    assert tier == 3, f"Expected tier 3 for complex prompt, got {tier}"


def test_classifier_predict_proba_sums_to_one():
    clf = ComplexityClassifier()
    proba = clf.predict_proba("Summarize this article in 3 bullet points.")
    total = sum(proba.values())
    assert abs(total - 1.0) < 1e-6


def test_classifier_predict_proba_keys():
    clf = ComplexityClassifier()
    proba = clf.predict_proba("What is the capital of France?")
    assert set(proba.keys()) == {1, 2, 3}


def test_module_level_classify():
    tier = classify("List the planets in the solar system.")
    assert tier in {1, 2, 3}


# ── Router ────────────────────────────────────────────────────────────────────

def test_route_returns_routing_decision():
    decision = route("What is the capital of France?")
    assert isinstance(decision, RoutingDecision)


def test_route_decision_has_valid_tier():
    decision = route("Summarize this article.")
    assert decision.tier in {1, 2, 3}


def test_route_decision_has_nonempty_model_ids():
    decision = route("Design a microservices architecture.")
    assert decision.model_id
    assert decision.fallback_model_id


def test_route_tier1_uses_cheap_model():
    decision = route("What is 2 + 2?")
    assert decision.tier == 1
    assert decision.model_id in {"gemini-flash", "gpt-4o-mini", "llama-3-8b", "qwen-coder-1.5b"}


def test_route_tier3_uses_powerful_model():
    prompt = (
        "Write a comprehensive multi-step strategy for designing "
        "a fault-tolerant, globally distributed database architecture "
        "that satisfies strong consistency requirements."
    )
    decision = route(prompt)
    assert decision.tier == 3
    assert decision.model_id in {"gpt-4o", "gemini-pro"}


def test_route_tier_name_matches_tier():
    tier_names = {1: "Simple", 2: "Moderate", 3: "Complex"}
    for tier_val, expected_name in tier_names.items():
        # find a representative prompt for the tier
        prompt = next(p for p, t in LABELED_PROMPTS if t == tier_val)
        decision = route(prompt)
        if decision.tier == tier_val:
            assert decision.tier_name == expected_name
