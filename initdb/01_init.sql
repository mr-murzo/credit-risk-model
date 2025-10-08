CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS fact;
CREATE TABLE IF NOT EXISTS raw.loans (
    person_age TEXT,
    person_gender TEXT,
    person_education TEXT,
    person_income TEXT,
    person_emp_exp TEXT,
    person_home_owner TEXT,
    loan_amnt TEXT,
    loan_intent TEXT,
    loan_int_rate TEXT,
    loan_percent_income TEXT,
    cb_person_cred_hist_length TEXT,
    credit_score TEXT,
    previous_loan_defaults_on_file TEXT,
    loan_status TEXT,
    uploaded_at TIMESTAMP DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS fact.loans (
    loan_id BIGSERIAL PRIMARY KEY,
    person_age INT,
    person_gender TEXT,
    person_education TEXT,
    person_income FLOAT,
    person_emp_exp INT,
    person_home_owner TEXT,
    loan_amnt FLOAT,
    loan_intent TEXT,
    loan_int_rate FLOAT,
    loan_percent_income FLOAT,
    cb_person_cred_hist_length INT,
    credit_score FLOAT,
    previous_loan_defaults_on_file TEXT,
    loan_status INT
);
CREATE TABLE IF NOT EXISTS fact.loans_rejects (
    person_age TEXT,
    person_gender TEXT,
    person_education TEXT,
    person_income TEXT,
    person_emp_exp TEXT,
    person_home_owner TEXT,
    loan_amnt TEXT,
    loan_intent TEXT,
    loan_int_rate TEXT,
    loan_percent_income TEXT,
    cb_person_cred_hist_length TEXT,
    credit_score TEXT,
    previous_loan_defaults_on_file TEXT,
    loan_status TEXT,
    error_reason TEXT
);
CREATE TABLE IF NOT EXISTS raw.etl_log(
    date_time TIMESTAMP,
    status TEXT,
    success_count INT,
    reject_count INT,
    error_message TEXT
);
CREATE MATERIALIZED VIEW IF NOT EXISTS vw_ml_loan AS
SELECT *
FROM fact.loans;
CREATE OR REPLACE PROCEDURE etl_clean_to_fact_loans() LANGUAGE plpgsql AS $$
DECLARE v_success INT := 0;
v_reject INT := 0;
v_last_run TIMESTAMP;
BEGIN
SELECT MAX(date_time) INTO v_last_run
FROM raw.etl_log;
BEGIN WITH raw_loans_deduplicated AS (
    SELECT DISTINCT ON(
            person_age,
            person_gender,
            person_education,
            person_income,
            person_emp_exp,
            person_home_owner,
            loan_amnt,
            loan_intent,
            loan_int_rate,
            loan_percent_income,
            cb_person_cred_hist_length,
            credit_score,
            previous_loan_defaults_on_file,
            loan_status
        ) person_age,
        person_gender,
        person_education,
        person_income,
        person_emp_exp,
        person_home_owner,
        loan_amnt,
        loan_intent,
        loan_int_rate,
        loan_percent_income,
        cb_person_cred_hist_length,
        credit_score,
        previous_loan_defaults_on_file,
        loan_status,
        uploaded_at
    FROM raw.loans
    ORDER BY person_age,
        person_gender,
        person_education,
        person_income,
        person_emp_exp,
        person_home_owner,
        loan_amnt,
        loan_intent,
        loan_int_rate,
        loan_percent_income,
        cb_person_cred_hist_length,
        credit_score,
        previous_loan_defaults_on_file,
        loan_status,
        uploaded_at ASC
),
raw_loans_new AS (
    SELECT *
    FROM raw_loans_deduplicated
    WHERE (
            v_last_run IS NULL
            OR uploaded_at > v_last_run
        )
),
valid_data AS (
    SELECT person_gender,
        person_education,
        person_home_owner,
        loan_intent,
        LOWER(TRIM(previous_loan_defaults_on_file)) AS previous_loan_defaults_on_file,
        CAST(person_age AS INT) AS person_age,
        CAST(person_income AS NUMERIC) AS person_income,
        CAST(person_emp_exp AS INT) AS person_emp_exp,
        CAST(loan_amnt AS NUMERIC) AS loan_amnt,
        CAST(loan_int_rate AS NUMERIC) AS loan_int_rate,
        CAST(loan_percent_income AS NUMERIC) AS loan_percent_income,
        CAST(cb_person_cred_hist_length AS INT) AS cb_person_cred_hist_length,
        CAST(credit_score AS NUMERIC) AS credit_score,
        CAST(loan_status AS INT) AS loan_status
    FROM raw_loans_new
    WHERE person_age ~ '^[0-9]+$'
        AND person_income ~ '^[0-9]+(\.[0-9]+)?$'
        AND person_emp_exp ~ '^[0-9]+$'
        AND loan_amnt ~ '^[0-9]+(\.[0-9]+)?$'
        AND loan_int_rate ~ '^[0-9]+(\.[0-9]+)?$'
        AND loan_percent_income ~ '^[0-9]+(\.[0-9]+)?$'
        AND cb_person_cred_hist_length ~ '^[0-9]+$'
        AND credit_score ~ '^[0-9]+(\.[0-9]+)?$'
        AND loan_status ~ '^[0-1]$'
        AND CAST(person_age AS INT) >= 0
        AND CAST(person_income AS NUMERIC) >= 0
        AND CAST(person_emp_exp AS INT) >= 0
        AND CAST(loan_amnt AS NUMERIC) > 0
        AND CAST(loan_int_rate AS NUMERIC) >= 0
        AND CAST(loan_percent_income AS NUMERIC) >= 0
        AND CAST(cb_person_cred_hist_length AS INT) >= 0
        AND CAST(credit_score AS NUMERIC) BETWEEN 300 AND 850
)
INSERT INTO fact.loans (
        person_age,
        person_gender,
        person_education,
        person_income,
        person_emp_exp,
        person_home_owner,
        loan_amnt,
        loan_intent,
        loan_int_rate,
        loan_percent_income,
        cb_person_cred_hist_length,
        credit_score,
        previous_loan_defaults_on_file,
        loan_status
    )
SELECT person_age,
    person_gender,
    person_education,
    person_income,
    person_emp_exp,
    person_home_owner,
    loan_amnt,
    loan_intent,
    loan_int_rate,
    loan_percent_income,
    cb_person_cred_hist_length,
    credit_score,
    previous_loan_defaults_on_file,
    loan_status
FROM valid_data;
GET DIAGNOSTICS v_success = ROW_COUNT;
INSERT INTO fact.loans_rejects (
        person_age,
        person_gender,
        person_education,
        person_income,
        person_emp_exp,
        person_home_owner,
        loan_amnt,
        loan_intent,
        loan_int_rate,
        loan_percent_income,
        cb_person_cred_hist_length,
        credit_score,
        previous_loan_defaults_on_file,
        loan_status,
        error_reason
    )
SELECT person_age,
    person_gender,
    person_education,
    person_income,
    person_emp_exp,
    person_home_owner,
    loan_amnt,
    loan_intent,
    loan_int_rate,
    loan_percent_income,
    cb_person_cred_hist_length,
    credit_score,
    previous_loan_defaults_on_file,
    loan_status,
    CASE
        WHEN NOT (person_age ~ '^[0-9]+$') THEN 'Invalid person_age format: ' || person_age
        WHEN NOT (CAST(person_age AS INT) >= 0) THEN 'Invalid person_age value: ' || person_age
        WHEN NOT (person_income ~ '^[0-9]+(\.[0-9]+)?$') THEN 'Invalid person_income format: ' || person_income
        WHEN NOT (CAST(person_income AS NUMERIC) >= 0) THEN 'Invalid person_income value: ' || person_income
        WHEN NOT (person_emp_exp ~ '^[0-9]+$') THEN 'Invalid person_emp_exp format: ' || person_emp_exp
        WHEN NOT (CAST(person_emp_exp AS INT) >= 0) THEN 'Invalid person_emp_exp value: ' || person_emp_exp
        WHEN NOT (loan_amnt ~ '^[0-9]+(\.[0-9]+)?$') THEN 'Invalid loan_amnt format: ' || loan_amnt
        WHEN NOT (CAST(loan_amnt AS NUMERIC) > 0) THEN 'Invalid loan_amnt value: ' || loan_amnt
        WHEN NOT (loan_int_rate ~ '^[0-9]+(\.[0-9]+)?$') THEN 'Invalid loan_int_rate format: ' || loan_int_rate
        WHEN NOT (CAST(loan_int_rate AS NUMERIC) >= 0) THEN 'Invalid loan_int_rate value: ' || loan_int_rate
        WHEN NOT (loan_percent_income ~ '^[0-9]+(\.[0-9]+)?$') THEN 'Invalid loan_percent_income format: ' || loan_percent_income
        WHEN NOT (CAST(loan_percent_income AS NUMERIC) >= 0) THEN 'Invalid loan_percent_income value: ' || loan_percent_income
        WHEN NOT (cb_person_cred_hist_length ~ '^[0-9]+$') THEN 'Invalid cb_person_cred_hist_length format: ' || cb_person_cred_hist_length
        WHEN NOT (CAST(cb_person_cred_hist_length AS INT) >= 0) THEN 'Invalid cb_person_cred_hist_length value: ' || cb_person_cred_hist_length
        WHEN NOT (credit_score ~ '^[0-9]+(\.[0-9]+)?$') THEN 'Invalid credit_score format: ' || credit_score
        WHEN NOT (
            CAST(credit_score AS NUMERIC) BETWEEN 300 AND 850
        ) THEN 'Invalid credit_score range: ' || credit_score
        WHEN NOT (loan_status ~ '^[0-1]$') THEN 'Invalid loan_status: ' || loan_status
    END AS error_reason
FROM (
        SELECT DISTINCT ON(
                person_age,
                person_gender,
                person_education,
                person_income,
                person_emp_exp,
                person_home_owner,
                loan_amnt,
                loan_intent,
                loan_int_rate,
                loan_percent_income,
                cb_person_cred_hist_length,
                credit_score,
                previous_loan_defaults_on_file,
                loan_status
            ) person_age,
            person_gender,
            person_education,
            person_income,
            person_emp_exp,
            person_home_owner,
            loan_amnt,
            loan_intent,
            loan_int_rate,
            loan_percent_income,
            cb_person_cred_hist_length,
            credit_score,
            previous_loan_defaults_on_file,
            loan_status,
            uploaded_at
        FROM raw.loans
        ORDER BY person_age,
            person_gender,
            person_education,
            person_income,
            person_emp_exp,
            person_home_owner,
            loan_amnt,
            loan_intent,
            loan_int_rate,
            loan_percent_income,
            cb_person_cred_hist_length,
            credit_score,
            previous_loan_defaults_on_file,
            loan_status,
            uploaded_at ASC
    ) dedupe
WHERE (
        v_last_run IS NULL
        OR uploaded_at > v_last_run
    )
    AND NOT (
        person_age ~ '^[0-9]+$'
        AND person_income ~ '^[0-9]+(\.[0-9]+)?$'
        AND person_emp_exp ~ '^[0-9]+$'
        AND loan_amnt ~ '^[0-9]+(\.[0-9]+)?$'
        AND loan_int_rate ~ '^[0-9]+(\.[0-9]+)?$'
        AND loan_percent_income ~ '^[0-9]+(\.[0-9]+)?$'
        AND cb_person_cred_hist_length ~ '^[0-9]+$'
        AND credit_score ~ '^[0-9]+(\.[0-9]+)?$'
        AND loan_status ~ '^[0-1]$'
        AND CAST(person_age AS INT) >= 0
        AND CAST(person_income AS NUMERIC) >= 0
        AND CAST(person_emp_exp AS INT) >= 0
        AND CAST(loan_amnt AS NUMERIC) > 0
        AND CAST(loan_int_rate AS NUMERIC) >= 0
        AND CAST(loan_percent_income AS NUMERIC) >= 0
        AND CAST(cb_person_cred_hist_length AS INT) >= 0
        AND CAST(credit_score AS NUMERIC) BETWEEN 300 AND 850
    );
GET DIAGNOSTICS v_reject = ROW_COUNT;
EXCEPTION
WHEN OTHERS THEN RAISE NOTICE 'ETL failed with error: %',
SQLERRM;
INSERT INTO raw.etl_log(
        date_time,
        status,
        success_count,
        reject_count,
        error_message
    )
VALUES (NOW(), 'FAILED', 0, 0, SQLERRM);
RAISE;
END;
REFRESH MATERIALIZED VIEW vw_ml_loan;
INSERT INTO raw.etl_log(date_time, status, success_count, reject_count)
VALUES (NOW(), 'SUCCESS', v_success, v_reject);
END;
$$;