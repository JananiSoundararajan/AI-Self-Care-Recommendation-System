"""
ML inference service.

Loads the trained RandomForest pipeline and exposes a single
`classify_wellness(features) -> str` function used by the route layer.
Falls back to a rule-based classifier if the model file is missing.
"""

import numpy as np
import joblib
import os
import logging
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

LABEL_NAMES = ["low", "medium", "high"]
_model = None  # module-level singleton


def _load_model():
    global _model
    if _model is not None:
        return _model

    path = settings.model_path
    if os.path.exists(path):
        _model = joblib.load(path)
        logger.info(f"ML model loaded from {path}")
    else:
        logger.warning(
            f"Model not found at {path}. Using rule-based fallback. "
            "Run: python -m app.ml.train"
        )
        _model = None
    return _model


def _rule_based_classify(mood: int, sleep_hours: float,
                          stress_level: int, activity_level: int) -> str:
    """
    Deterministic fallback when the trained model is unavailable.
    Computes a simple wellness score and maps it to a label.
    """
    # Normalise each feature to 0-1, stress is inverted (high stress = low wellness)
    mood_norm = (mood - 1) / 9
    sleep_norm = min(sleep_hours / 8, 1.0)
    stress_norm = 1 - (stress_level - 1) / 9
    activity_norm = (activity_level - 1) / 9

    score = (mood_norm * 0.3 + sleep_norm * 0.25 +
             stress_norm * 0.3 + activity_norm * 0.15)

    if score < 0.4:
        return "low"
    elif score < 0.65:
        return "medium"
    else:
        return "high"


def classify_wellness(mood: int, sleep_hours: float,
                      stress_level: int, activity_level: int) -> str:
    """
    Returns wellness label: 'low' | 'medium' | 'high'
    """
    model = _load_model()

    if model is None:
        label = _rule_based_classify(mood, sleep_hours, stress_level, activity_level)
        logger.info(f"Rule-based classification → {label}")
        return label

    features = np.array([[mood, sleep_hours, stress_level, activity_level]], dtype=float)
    prediction = model.predict(features)[0]
    label = LABEL_NAMES[int(prediction)]
    probas = model.predict_proba(features)[0]
    logger.info(f"ML classification → {label} (probas: {dict(zip(LABEL_NAMES, probas.round(2)))})")
    return label
