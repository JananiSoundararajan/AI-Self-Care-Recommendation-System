"""
Train a lightweight mood/wellness classifier using synthetic data.

Features  : mood (1-10), sleep_hours (0-24), stress_level (1-10), activity_level (1-10)
Target    : wellness_label — 0=low  1=medium  2=high

Run once before starting the server:
    python -m app.ml.train
"""

import numpy as np
import joblib
import os
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.metrics import classification_report

RANDOM_STATE = 42
N_SAMPLES = 2000
MODEL_DIR = os.path.dirname(__file__)
MODEL_PATH = os.path.join(MODEL_DIR, "mood_classifier.joblib")
LABEL_NAMES = ["low", "medium", "high"]


def generate_synthetic_data(n: int = N_SAMPLES):
    """
    Rule-based synthetic dataset.
    Low   → high stress, low mood, poor sleep, low activity
    High  → low stress, high mood, good sleep, active
    """
    rng = np.random.default_rng(RANDOM_STATE)

    X, y = [], []

    for _ in range(n):
        label = rng.integers(0, 3)  # 0=low 1=medium 2=high

        if label == 0:  # poor wellness
            mood = rng.integers(1, 5)
            sleep = rng.uniform(3, 6)
            stress = rng.integers(7, 11)
            activity = rng.integers(1, 4)
        elif label == 1:  # moderate wellness
            mood = rng.integers(4, 8)
            sleep = rng.uniform(5.5, 7.5)
            stress = rng.integers(4, 8)
            activity = rng.integers(3, 7)
        else:  # high wellness
            mood = rng.integers(7, 11)
            sleep = rng.uniform(7, 9)
            stress = rng.integers(1, 5)
            activity = rng.integers(6, 11)

        # Add gaussian noise to prevent perfect linear separability
        features = [
            float(mood) + rng.normal(0, 0.3),
            float(sleep) + rng.normal(0, 0.2),
            float(stress) + rng.normal(0, 0.3),
            float(activity) + rng.normal(0, 0.3),
        ]
        X.append(features)
        y.append(label)

    return np.array(X), np.array(y)


def train():
    print("Generating synthetic training data …")
    X, y = generate_synthetic_data()

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=RANDOM_STATE, stratify=y
    )

    pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("clf", RandomForestClassifier(
            n_estimators=100,
            max_depth=8,
            random_state=RANDOM_STATE,
            class_weight="balanced",
        )),
    ])

    print("Training RandomForest classifier …")
    pipeline.fit(X_train, y_train)

    y_pred = pipeline.predict(X_test)
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred, target_names=LABEL_NAMES))

    os.makedirs(MODEL_DIR, exist_ok=True)
    joblib.dump(pipeline, MODEL_PATH)
    print(f"\nModel saved → {MODEL_PATH}")
    return pipeline


if __name__ == "__main__":
    train()
