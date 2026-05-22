"""
SmartCRM — Churn Prediction ML Model
Bonus Task (Shared Responsibility)

Model: Random Forest Classifier
Features:
  - total_spent
  - days_inactive
  - order_count

Output: high / medium / low churn risk + probability
"""

import os
import pickle
import psycopg2
import psycopg2.extras
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
from sklearn.preprocessing import LabelEncoder
from dotenv import load_dotenv

load_dotenv()

MODEL_PATH = os.path.join(os.path.dirname(__file__), "churn_model.pkl")
ENCODER_PATH = os.path.join(os.path.dirname(__file__), "label_encoder.pkl")


# ── Data Loader ──────────────────────────────────────────────

def load_training_data():
    conn = psycopg2.connect(
        os.getenv("POSTGRES_URL"),
        cursor_factory=psycopg2.extras.RealDictCursor
    )
    cur = conn.cursor()
    cur.execute("""
        SELECT total_spent, days_inactive, order_count, churn_risk
        FROM churn_features
    """)
    rows = cur.fetchall()
    cur.close(); conn.close()

    X, y = [], []
    for row in rows:
        X.append([
            float(row["total_spent"]   or 0),
            float(row["days_inactive"] or 0),
            float(row["order_count"]   or 0),
        ])
        y.append(row["churn_risk"])

    return np.array(X), y


# ── Training ─────────────────────────────────────────────────

def train_model():
    print("📊 Loading training data from PostgreSQL...")
    X, y_raw = load_training_data()

    le = LabelEncoder()
    y  = le.fit_transform(y_raw)   # high=0, low=1, medium=2 (alphabetical)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    model = RandomForestClassifier(
        n_estimators=100,
        max_depth=5,
        random_state=42
    )
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    print("\n📈 Model Performance:")
    print(classification_report(y_test, y_pred, target_names=le.classes_))

    # Save model and encoder
    with open(MODEL_PATH, "wb") as f:
        pickle.dump(model, f)
    with open(ENCODER_PATH, "wb") as f:
        pickle.dump(le, f)

    print(f"✅ Model saved to {MODEL_PATH}")
    return model, le


# ── Inference ────────────────────────────────────────────────

def load_model():
    with open(MODEL_PATH, "rb") as f:
        model = pickle.load(f)
    with open(ENCODER_PATH, "rb") as f:
        le = pickle.load(f)
    return model, le


def predict_churn(total_spent: float, days_inactive: float, order_count: float) -> dict:
    """
    Predict churn risk for a single customer.
    Returns label and probabilities.
    """
    try:
        model, le = load_model()
    except FileNotFoundError:
        return {"error": "Model not trained yet. Run train_model() first."}

    features = np.array([[total_spent, days_inactive, order_count]])
    label_idx  = model.predict(features)[0]
    proba      = model.predict_proba(features)[0]

    label   = le.inverse_transform([label_idx])[0]
    classes = le.classes_

    return {
        "churn_risk":    label,
        "confidence":    round(float(proba[label_idx]) * 100, 1),
        "probabilities": {
            cls: round(float(p) * 100, 1)
            for cls, p in zip(classes, proba)
        }
    }


def predict_churn_batch(customers: list[dict]) -> list[dict]:
    """Predict churn for a list of customer dicts from postgres_service."""
    try:
        model, le = load_model()
    except FileNotFoundError:
        return [{"error": "Model not trained. Run train_model() first."}]

    results = []
    for c in customers:
        features = np.array([[
            float(c.get("total_spent", 0)),
            float(c.get("days_inactive", 0)),
            float(c.get("order_count", 0))
        ]])
        label_idx = model.predict(features)[0]
        proba     = model.predict_proba(features)[0]
        label     = le.inverse_transform([label_idx])[0]

        results.append({
            "id":          c.get("id"),
            "name":        c.get("name"),
            "email":       c.get("email"),
            "churn_risk":  label,
            "confidence":  round(float(proba[label_idx]) * 100, 1)
        })

    return results


if __name__ == "__main__":
    train_model()
    print("\n🔍 Sample prediction:")
    print(predict_churn(total_spent=50, days_inactive=120, order_count=1))
    print(predict_churn(total_spent=3000, days_inactive=5, order_count=15))
