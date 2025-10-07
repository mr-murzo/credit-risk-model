import pandas as pd
from sqlalchemy import create_engine, text
from config import POSTGRES_PASSWORD, POSTGRES_USER, POSTGRES_DB
import logging

def get_connection():
    logging.info(f"postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}@localhost:5432/{POSTGRES_DB}")
    engine = create_engine(f"postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}@localhost:5432/{POSTGRES_DB}")
    return engine

def run_query(query, params=None):
    conn = get_connection().connect()
    try:
        result = conn.execute(text(query), params or {})
        return result.fetchall()
    finally:
        conn.close()

def run_etl():
    conn = get_connection().connect()
    try:
        conn.execute(text("CALL etl_clean_to_fact_loans()"))
        conn.commit()
        conn.close()
    finally:
        conn.close()

def insert_raw_loans(df: pd.DataFrame):
    df = df.dropna(how="all")  # drop completely empty rows
    engine = get_connection()
    df.to_sql("loans", engine, schema="raw", if_exists="append", index=False)


