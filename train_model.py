import pandas as pd
import numpy as np
import joblib
from db import get_connection  # expects db.get_connection() returning SQLAlchemy engine

from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler, OneHotEncoder, FunctionTransformer
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score

from imblearn.pipeline import Pipeline as ImbPipeline  # IMPORTANT
from imblearn.over_sampling import SMOTE


# ================================================================
# Configuration
# ================================================================
FEATURE_COLS = [
    "person_age",
    "person_gender",
    "person_education",
    "person_income",
    "person_emp_exp",
    "person_home_owner",
    "loan_amnt",
    "loan_intent",
    "loan_int_rate",
    "loan_percent_income",
    "cb_person_cred_hist_length",
    "credit_score",
    "previous_loan_defaults_on_file"
]


# ================================================================
# Helper Functions
# ================================================================
def normalize_gender(x):
    """Standardize gender entries to 'M', 'F', or 'U'."""
    s = str(x).strip().lower() if pd.notna(x) else ""
    if s in ["male", "m"]:
        return "M"
    if s in ["female", "f"]:
        return "F"
    return "U"


def bucket_age(age):
    """Convert numeric age into categorical buckets."""
    try:
        a = int(age)
    except Exception:
        return "VERY-OLD"
    if 18 <= a <= 30:
        return "YOUNG"
    elif 31 <= a <= 50:
        return "MIDDLE-AGE"
    elif 51 <= a <= 80:
        return "OLD"
    else:
        return "VERY-OLD"


def bucket_emp_exp(exp):
    """Convert months of employment into categorical experience levels."""
    try:
        e = int(exp)
    except Exception:
        return "HIGH"
    if e <= 24:
        return "FRESH"
    elif 25 <= e <= 48:
        return "LOW"
    elif 49 <= e <= 96:
        return "MEDIUM"
    else:
        return "HIGH"


# ================================================================
# Preprocessing
# ================================================================
def preprocess_data(df: pd.DataFrame):
    """Clean, transform, and prepare the dataset for training."""

    required = set(FEATURE_COLS + ["loan_status"])
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns in dataframe: {missing}")

    df = df.copy()

    # Define numeric and categorical columns
    numeric_cols = [
        "person_income",
        "loan_amnt",
        "loan_int_rate",
        "loan_percent_income",
        "cb_person_cred_hist_length",
        "credit_score"
    ]

    categorical_cols = [
        "person_age",
        "person_gender",
        "person_education",
        "person_emp_exp",
        "person_home_owner",
        "loan_intent",
        "previous_loan_defaults_on_file"
    ]

    # Convert numeric columns safely
    for c in numeric_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    # Drop rows missing essential numeric or target fields
    df = df.dropna(subset=["loan_status"] + numeric_cols)
    df = df.reset_index(drop=True)

    # Apply categorical transformations
    df["person_gender"] = df["person_gender"].apply(normalize_gender)
    df["person_age"] = df["person_age"].apply(bucket_age)
    df["person_emp_exp"] = df["person_emp_exp"].apply(bucket_emp_exp)

    # Define X and y
    X = df[FEATURE_COLS].copy()
    y = df["loan_status"].astype(int).copy()

    # Build preprocessing pipeline
    log_transformer = FunctionTransformer(np.log1p, validate=True)
    numeric_transformer = Pipeline(steps=[
        ("log", log_transformer),
        ("scaler", StandardScaler())
    ])

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", numeric_transformer, numeric_cols),
            ("cat", OneHotEncoder(handle_unknown="ignore"), categorical_cols)
        ],
        remainder="drop"
    )

    return X, y, preprocessor


# ================================================================
# Training Function
# ================================================================
def train_and_save_models(df: pd.DataFrame = None):
    """Train both Logistic Regression and Random Forest with SMOTE handling."""

    # Load data from database if not provided
    if df is None:
        engine = get_connection()
        df = pd.read_sql("SELECT * FROM vw_ml_loan", con=engine)

    X, y, preprocessor = preprocess_data(df)

    # Split dataset
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )

    # Pipelines with SMOTE inside
    logreg_pipeline = ImbPipeline([
        ("preprocessor", preprocessor),
        ("smote", SMOTE(random_state=42)),
        ("clf", LogisticRegression(max_iter=1000))
    ])

    rf_pipeline = ImbPipeline([
        ("preprocessor", preprocessor),
        ("smote", SMOTE(random_state=42)),
        ("clf", RandomForestClassifier(n_estimators=200, random_state=42))
    ])

    # Train models
    logreg_pipeline.fit(X_train, y_train)
    rf_pipeline.fit(X_train, y_train)

    # Evaluate
    acc_logreg = accuracy_score(y_test, logreg_pipeline.predict(X_test))
    acc_rf = accuracy_score(y_test, rf_pipeline.predict(X_test))

    # Save models
    joblib.dump(logreg_pipeline, "loan_model_logreg.pkl")
    joblib.dump(rf_pipeline, "loan_model_rf.pkl")
    joblib.dump({"Logistic Regression": acc_logreg, "Random Forest": acc_rf}, "model_scores.pkl")

    print(f"✅ Models trained and saved successfully!")
    print(f"   Logistic Regression Accuracy: {acc_logreg:.4f}")
    print(f"   Random Forest Accuracy:       {acc_rf:.4f}")

    return acc_logreg, acc_rf

