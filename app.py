import streamlit as st
import pandas as pd
import joblib
import db
from db import insert_raw_loans, run_etl
import plotly.express as px
from train_model import (
    train_and_save_models,
    bucket_age,
    bucket_emp_exp,
    normalize_gender,
    FEATURE_COLS,
)
from config import UPLOAD_PASSWORD

st.set_page_config(page_title="Loan Approval ML App", layout="wide")

page = st.sidebar.radio("Navigation", ["Upload Data", "Make Predictions", "Dashboard"])

if page == "Upload Data":
    st.title("Upload Loan Data & Retrain Models")
    password = st.text_input("Enter password:", type="password")

    if password == UPLOAD_PASSWORD:
        st.info("### INSTRUCTIONS FOR UPLOAD")
        st.info("Your CSV file should contain *only* these columns (order doesn’t matter):")
        required_columns = [
            "person_age", "person_gender", "person_education", "person_income",
            "person_emp_exp", "person_home_owner", "loan_amnt", "loan_intent",
            "loan_int_rate", "loan_percent_income", "cb_person_cred_hist_length",
            "credit_score", "previous_loan_defaults_on_file", "loan_status"
        ]
        st.code(", ".join(required_columns))

        # Display upload history
        query = "SELECT * FROM raw.etl_log;"
        dfd = pd.DataFrame(db.run_query(query))
        st.write("UPLOAD HISTORY:", dfd)

        uploaded_file = st.file_uploader("Upload CSV File", type=["csv"])

        if uploaded_file:
            try:
                df = pd.read_csv(uploaded_file)
                df.columns = df.columns.str.strip()  # remove spaces

                missing_cols = [c for c in required_columns if c not in df.columns]
                extra_cols = [c for c in df.columns if c not in required_columns]

                if missing_cols:
                    st.error(f"❌ Missing required columns: {missing_cols}")
                elif extra_cols:
                    st.error(f"❌ Extra columns found: {extra_cols}")
                else:
                    # Reorder columns to match required structure
                    df = df[required_columns]
                    st.success("✅ File validated successfully!")
                    st.write("Preview:", df.head())


                    df = df.astype(str)

                    if st.button("Insert → Run ETL → Retrain"):
                        try:
                            insert_raw_loans(df)
                            st.info("✅ Inserted to raw.loans")

                            run_etl()
                            st.info("✅ ETL run completed")

                            acc_lg, acc_rf = train_and_save_models()
                            st.success("✅ Models retrained and saved successfully.")
                            st.write(f"*Logistic Regression Accuracy:* {acc_lg:.2%}")
                            st.write(f"*Random Forest Accuracy:* {acc_rf:.2%}")

                        except Exception as e:
                            st.error(f"⚠️ Error during ETL or training: {e}")

            except Exception as e:
                st.error(f"⚠️ Failed to read file: {e}")

    else:
        if password:
            st.error("🚫 Wrong password.")

elif page == "Make Predictions":
    st.title("Loan Approval Prediction")

    try:
        logreg = joblib.load("loan_model_logreg.pkl")
        rf = joblib.load("loan_model_rf.pkl")
        scores = joblib.load("model_scores.pkl")
    except Exception:
        st.error("Models not found — train first.")
        st.stop()

    model_choice = st.radio("Choose model:", ["Logistic Regression", "Random Forest"])

    # Inputs
    person_age = st.number_input("Age", min_value=18, max_value=100, step=1)
    person_gender_sel = st.selectbox("Gender", ["Male", "Female"])
    person_education = st.selectbox("Education", ["High School", "Bachelor", "Master", "PhD", "Other"])
    person_income = st.number_input("Annual Income", min_value=0.0, step=1.0)
    person_emp_exp = st.number_input("Employment Experience (months)", min_value=0)
    person_home_owner = st.selectbox("Home Ownership", ["Rent", "Own", "Mortgage", "Other"])
    loan_amnt = st.number_input("Loan Amount", min_value=0.0)
    loan_intent = st.selectbox("Loan Intent", ["Personal", "Education", "Medical", "Venture", "Home", "Other"])
    loan_int_rate = st.number_input("Interest Rate (%)", min_value=0.0, max_value=100.0)
    loan_percent_income = st.number_input("Loan Percent of Income", min_value=0.0)
    cb_person_cred_hist_length = st.number_input("Credit History Length (years)", min_value=0)
    credit_score = st.number_input("Credit Score", min_value=300, max_value=850)
    previous_loan_defaults_on_file = st.selectbox("Previous Loan Default", ["yes", "no"])

    input_row = {
        "person_age": bucket_age(person_age),
        "person_gender": "M" if person_gender_sel == "Male" else "F",
        "person_education": person_education,
        "person_income": float(person_income),
        "person_emp_exp": bucket_emp_exp(person_emp_exp),
        "person_home_owner": person_home_owner,
        "loan_amnt": float(loan_amnt),
        "loan_intent": loan_intent,
        "loan_int_rate": float(loan_int_rate),
        "loan_percent_income": float(loan_percent_income),
        "cb_person_cred_hist_length": int(cb_person_cred_hist_length),
        "credit_score": float(credit_score),
        "previous_loan_defaults_on_file": previous_loan_defaults_on_file.lower(),
    }

    input_df = pd.DataFrame([input_row])[FEATURE_COLS]

    if st.button("Predict"):
        model = logreg if model_choice == "Logistic Regression" else rf
        try:
            pred = model.predict(input_df)[0]
            result = "✅ Loan Approved" if pred == 0 else "❌ Loan Denied"
            st.write(result)
            st.write(f"{model_choice} accuracy (on last train): {scores[model_choice]:.2%}")
        except Exception as e:
            st.error(f"Prediction error: {e}")

elif page == "Dashboard":
    st.title("📊 Loan Default Dashboard")
    query = "SELECT * FROM vw_ml_loan;"
    df = pd.DataFrame(db.run_query(query))

    def bucket_dti(dti):
        if dti <= 0.2:
            return "Low Leverage"
        elif dti <= 0.35:
            return "Moderate Leverage"
        elif dti <= 0.43:
            return "Medium Risk"
        elif dti <= 0.5:
            return "High Risk"
        else:
            return "Very High Risk"

    if not df.empty:
        df["loan_percent_income"] = pd.to_numeric(df["loan_percent_income"])
        df["person_emp_exp"] = pd.to_numeric(df["person_emp_exp"])
        df["dti_bucket"] = df["loan_percent_income"].apply(bucket_dti)
        df["default"] = df["loan_status"].apply(lambda x: 1 if x == 1 else 0)
        df["emp_exp_years"] = (df["person_emp_exp"] // 12).astype(int)

        total_loans = len(df)
        total_defaults = df["default"].sum()
        default_rate = round(total_defaults / total_loans * 100, 2)

        col1, col2, col3 = st.columns(3)
        col1.metric("Total Loans", f"{total_loans:,}")
        col2.metric("Total Defaults", f"{total_defaults:,}")
        col3.metric("Default Rate", f"{default_rate}%")

        st.markdown("---")

        default_counts = (
            df[df["default"] == 1]
            .groupby("person_gender")
            .size()
            .reset_index(name="count")
        )

        fig = px.pie(
            default_counts,
            names="person_gender",
            values="count",
            title="Number of Defaults by Gender",
            color_discrete_sequence=["#2ca02c", "#d62728"],
        )
        st.plotly_chart(fig, use_container_width=True)

        df["person_age"] = pd.to_numeric(df["person_age"])
        age_summary = (
            df.assign(default=df["default"].map({0: "No", 1: "Yes"}))
            .groupby(["person_gender", "default"])["person_age"]
            .agg(["min", "max", "mean"])
            .reset_index()
        )

        st.subheader("Age Distribution by Gender and Default Status")
        st.dataframe(age_summary)

        fig_age = px.histogram(
            df,
            x="person_age",
            color_discrete_sequence=["red", "green"],
            barmode="overlay",
            title="Age Distribution of Borrowers",
            nbins=30,
        )
        st.plotly_chart(fig_age, use_container_width=True)

        edu_summary = df.groupby("person_education")["default"].agg(
            total_default="sum",
            total_loans="count",
        ).reset_index()
        edu_summary["% default"] = round(
            edu_summary["total_default"] / edu_summary["total_loans"] * 100, 2
        )

        st.subheader("Defaults by Education Level")
        st.dataframe(edu_summary)

        fig_edu = px.bar(
            edu_summary,
            x="person_education",
            y="% default",
            title="Default Rate by Education Level",
            text="% default",
        )
        st.plotly_chart(fig_edu, use_container_width=True)

        exp_summary = df.groupby("emp_exp_years")["default"].agg(
            total_default="sum",
            total_loans="count",
        ).reset_index()
        exp_summary["% default"] = round(
            exp_summary["total_default"] / exp_summary["total_loans"] * 100, 2
        )

        st.subheader("Defaults by Years of Experience (Bucketed by Year)")
        st.dataframe(exp_summary)

        fig_exp = px.line(
            exp_summary,
            x="emp_exp_years",
            y="% default",
            title="Default Rate by Years of Experience (in Years)",
            markers=True,
        )
        st.plotly_chart(fig_exp, use_container_width=True)

        dti_summary = df.groupby("dti_bucket")["default"].agg(
            total_default="sum",
            total_loans="count",
        ).reset_index()
        dti_summary["% default"] = round(
            dti_summary["total_default"] / dti_summary["total_loans"] * 100, 2
        )

        st.subheader("Defaults by DTI Category")
        st.dataframe(dti_summary)

        fig_dti = px.bar(
            dti_summary,
            x="dti_bucket",
            y="% default",
            title="Default Rate by DTI Category",
            text="% default",
        )
        st.plotly_chart(fig_dti, use_container_width=True)

        if "previously_defaulted" in df.columns:
            prev_summary = df.groupby("previously_defaulted")["default"].agg(
                total_default="sum",
                total_loans="count",
            ).reset_index()
            prev_summary["% default"] = round(
                prev_summary["total_default"] / prev_summary["total_loans"] * 100, 2
            )

            st.subheader("Defaults by Previous Default History")
            st.dataframe(prev_summary)

            fig_prev = px.bar(
                prev_summary,
                x="previously_defaulted",
                y="% default",
                title="Default Rate by Previous Defaults",
                text="% default",
            )
            st.plotly_chart(fig_prev, use_container_width=True)
    else:
        st.info("No data available to display.")
