"""
Feature extraction for complexity classification.

Features are deliberately cheap to compute — no external calls, no tokenizers.
"""

import re

# Keywords that signal increasing cognitive load
_TIER1_KEYWORDS = [
    "what is", "who is", "when did", "where is", "how many", "convert",
    "translate", "list", "extract", "format", "spell", "correct",
    "capitalize", "define", "name", "give me", "tell me",
]

_TIER2_KEYWORDS = [
    "summarize", "summary", "compare", "contrast", "classify", "categorize",
    "analyze", "analysis", "identify", "outline", "rewrite", "describe",
    "generate", "create a list", "pros and cons", "bullet point",
    "structure", "review", "evaluate criteria",
]

_TIER3_KEYWORDS = [
    "design", "architect", "develop a strategy", "comprehensive",
    "multi-step", "trade-off", "trade off", "implications",
    "consequences", "critically", "nuanced", "propose",
    "deep dive", "long-term", "reasoning", "justify", "argue",
    "essay", "framework", "roadmap", "in-depth", "explain why",
    "debate", "proof", "optimize", "algorithm",
    "ethical", "fault-tolerant", "fault tolerant", "distributed",
    "scalable", "real-time", "business plan", "strategic",
    "geopolitical", "socioeconomic", "philosophical",
]

# Verbs that typically appear in complex requests
_REASONING_VERBS = re.compile(
    r"\b(design|architect|evaluate|argue|justify|critique|synthesize"
    r"|theorize|hypothesize|debate|derive|prove|reason|infer)\b",
    re.IGNORECASE,
)

# Structural complexity markers
_MULTI_PART = re.compile(
    r"(step[- ]by[- ]step|multiple steps?|first.+then.+finally"
    r"|considering.+and.+|including.+and.+|both.+and.+)",
    re.IGNORECASE,
)

_CONSTRAINT_PATTERN = re.compile(
    r"\b(must|should|ensure|require|constraint|limit|budget|deadline"
    r"|while maintaining|without|except|only if)\b",
    re.IGNORECASE,
)


def extract_features(prompt: str) -> list[float]:
    """
    Return a fixed-length feature vector for a prompt.

    Index  Feature
    -----  -------
    0      Word count (normalized by 100)
    1      Sentence count
    2      Avg words per sentence
    3      Tier-1 keyword hits (normalized)
    4      Tier-2 keyword hits (normalized)
    5      Tier-3 keyword hits (normalized)
    6      Reasoning-verb hit count
    7      Multi-part / sequential instruction flag (0/1)
    8      Constraint keyword hit count (normalized)
    9      Question mark count
    10     Output-size signal: "essay" / "report" / "story" / "plan" etc.
    """
    lower = prompt.lower()
    words = lower.split()
    word_count = len(words)
    sentences = re.split(r"[.!?]+", prompt.strip())
    sentence_count = max(len([s for s in sentences if s.strip()]), 1)

    t1_hits = sum(1 for kw in _TIER1_KEYWORDS if kw in lower)
    t2_hits = sum(1 for kw in _TIER2_KEYWORDS if kw in lower)
    t3_hits = sum(1 for kw in _TIER3_KEYWORDS if kw in lower)

    reasoning_hits = len(_REASONING_VERBS.findall(prompt))
    multi_part = 1.0 if _MULTI_PART.search(prompt) else 0.0
    constraint_hits = len(_CONSTRAINT_PATTERN.findall(prompt))

    question_marks = prompt.count("?")

    long_output_words = ["essay", "report", "story", "novel", "proposal",
                         "plan", "guide", "curriculum", "chapter", "playbook"]
    long_output_signal = sum(1 for w in long_output_words if w in lower)

    return [
        word_count / 100.0,
        float(sentence_count),
        word_count / sentence_count,
        t1_hits / max(len(_TIER1_KEYWORDS), 1),
        t2_hits / max(len(_TIER2_KEYWORDS), 1),
        t3_hits / max(len(_TIER3_KEYWORDS), 1),
        float(reasoning_hits),
        multi_part,
        constraint_hits / 10.0,
        float(question_marks),
        float(long_output_signal),
    ]


FEATURE_NAMES = [
    "word_count_norm",
    "sentence_count",
    "avg_words_per_sentence",
    "tier1_keyword_ratio",
    "tier2_keyword_ratio",
    "tier3_keyword_ratio",
    "reasoning_verb_count",
    "multi_part_flag",
    "constraint_ratio",
    "question_mark_count",
    "long_output_signal",
]
