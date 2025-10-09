# 🚀 Loan Default Prediction — End-to-End ML System (SQL → ELT → ML → Streamlit + Docker)

An **end-to-end Loan Default Prediction System** that automates data ingestion, ELT, model training, and interactive analytics — all deployed via **Docker**.

---

## 🌟 Overview

This project demonstrates how **Data Engineering + Machine Learning + MLOps** come together in a production-style workflow.  
It handles everything — from CSV uploads and database ELT, to retraining ML models and visualizing predictions in a Streamlit dashboard.

**Core Stack:**  
- 🐍 Python (pandas, scikit-learn, imblearn, plotly, streamlit)  
- 🗄️ PostgreSQL (ETL + data validation + warehouse)  
- 🐳 Docker & Docker Compose (deployment)  
- ⚙️ SQL Stored Procedures for ELT  
- 🔐 Environment variables via `.env`

---

## 🧱 Architecture

**Schemas:**
- **raw:** Incoming unvalidated uploads  
- **fact:** Clean, validated tables ready for ML  
- **etl_log:** Tracks each ELT run  
- **loans_rejects:** Stores rejected rows with reasons  

**ELT Highlights:**
- Deduplication via `DISTINCT ON` and `ON CONFLICT DO NOTHING`  
- Logs every run in `etl_log` (with timestamps + counts)  
- Invalid rows (bad types, missing data) moved to `fact.loans_rejects`

---

## 🧠 Machine Learning Pipeline

**Models:**  
- Logistic Regression  
- Random Forest  

**Preprocessing Includes:**  
- Age bucketing (YOUNG, MIDDLE-AGE, OLD, VERY-OLD)  
- Employment experience bucketed into year bins  
- DTI (loan_percent_income) bucketed by leverage  
- Log transformation on skewed features (e.g. income, loan amount)  
- `ColumnTransformer` for scaling + one-hot encoding  
- **SMOTE applied** to balance class distribution before training  

---

## 💻 Streamlit App

**Pages:**
1. **Upload Data** → password-protected → inserts raw CSV → triggers ETL → retrains model  
2. **Make Predictions** → select model → input borrower details → view prediction  
3. **Dashboard** → KPIs + visuals  
   - Total loans, defaults, default rate  
   - Default rate by age, education, DTI

**UI flow:**  
Upload → ELT → Retrain → Predict → Analyze 📊

---

## 🔁 Duplicate & Reupload Protection

**How it works:**
- Only new uploads processed (based on latest ETL timestamp).  
- Duplicates in the same file removed via `DISTINCT ON`.  
- Re-inserts prevented via `ON CONFLICT (loan_uuid) DO NOTHING`.  
- Faulty rows logged to rejects table for inspection.  

Result: **ELT is idempotent, auditable, and safe**.

---

## 🧠 Sample Dataset

A sample CSV (`sample_loans.csv`) is provided to simulate real loan applications.  
Upload it in the app to test the full ETL + retrain + predict pipeline.

A sample CSV (`invalid_sample_loans.csv`) is provided to test if faulty to check if 
it is being rejected or not.

---

## ⚙️ Run Locally (Dockerized Setup)

```bash
# 1️⃣ Clone the repo
git clone https://github.com/mr-murzo/credit-risk-model.git

# 2️⃣ Navigate into project
cd credit-risk-model

# 3️⃣ Set file permissions (for init scripts)
chmod -R 755 ./initdb

# 4️⃣ Start the full stack
docker compose up -d --build

# 5️⃣ Visit Streamlit app
http://localhost:8501



