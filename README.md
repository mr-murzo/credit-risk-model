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

```md
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

## 🚀 Running Locally Without Docker

### Prerequisites
You'll need to install these locally:
1. *Python 3.11* (as specified in the Dockerfile)
2. *PostgreSQL 15* (as specified in docker-compose.yml)

### Step 1: Set up PostgreSQL Database

*Install PostgreSQL:*
bash
# On macOS with Homebrew
brew install postgresql@15
brew services start postgresql@15

# On Ubuntu/Debian
sudo apt update
sudo apt install postgresql-15 postgresql-client-15
sudo systemctl start postgresql


*Create database and user:*
bash
# Connect to PostgreSQL
psql postgres

# In PostgreSQL shell:
CREATE DATABASE credit_risk_db;
CREATE USER credit_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE credit_risk_db TO credit_user;
\q


### Step 2: Create Environment File

Create a .env file in the project root:
bash
# .env
POSTGRES_USER=credit_user
POSTGRES_PASSWORD=your_password
POSTGRES_DB=credit_risk_db
POSTGRES_HOSTNAME=localhost
POSTGRES_PORT=5432
UPLOAD_PASSWORD=admin123


### Step 3: Install Python Dependencies

bash
# Create virtual environment (recommended)
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt


### Step 4: Initialize Database Schema

bash
# Run the SQL initialization script
psql -h localhost -U credit_user -d credit_risk_db -f initdb/01_init.sql


### Step 6: Run the Application

bash
# Start the Streamlit app
streamlit run app.py --server.enableCORS false --server.enableXsrfProtection false


The app will be available at http://localhost:8501

