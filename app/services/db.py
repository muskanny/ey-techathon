from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import List, Optional

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
DB_PATH = DATA_DIR / "loan.db"


def get_connection() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS loan_products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            purpose TEXT NOT NULL,
            min_amount REAL NOT NULL,
            max_amount REAL NOT NULL,
            interest_rate REAL NOT NULL,
            tenure_months INTEGER NOT NULL,
            description TEXT
        );
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS preapproved_offers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_pan TEXT NOT NULL,
            product_id INTEGER NOT NULL,
            preapproved_amount REAL NOT NULL,
            FOREIGN KEY(product_id) REFERENCES loan_products(id)
        );
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            pan TEXT UNIQUE NOT NULL,
            dob TEXT NOT NULL,
            phone TEXT NOT NULL,
            income REAL NOT NULL
        );
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS kyc_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pan TEXT NOT NULL,
            outcome TEXT NOT NULL,
            reason TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """
    )

    cur.execute("SELECT COUNT(*) FROM loan_products")
    if cur.fetchone()[0] == 0:
        sample_products = [
            ("Flexi Personal Loan", "travel", 50000, 1000000, 12.5, 48, "Ideal for vacations and experiences."),
            ("Smart Home Loan", "home", 100000, 2500000, 11.9, 60, "Renovations, furnishings, interiors."),
            ("Education Achiever", "education", 50000, 1500000, 10.5, 72, "Higher studies and certifications."),
            ("Medical Relief", "medical", 25000, 800000, 13.2, 36, "Emergency medical funding."),
        ]
        cur.executemany(
            """
            INSERT INTO loan_products (name, purpose, min_amount, max_amount, interest_rate, tenure_months, description)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            sample_products,
        )

    cur.execute("SELECT COUNT(*) FROM customers")
    if cur.fetchone()[0] == 0:
        sample_customers = [
            ("Asha Mehta", "ABCDE1234F", "1989-04-12", "+91-9000000001", 1200000),
            ("Rohan Singh", "BCDEF2345G", "1992-11-03", "+91-9000000002", 900000),
        ]
        cur.executemany(
            """
            INSERT INTO customers (name, pan, dob, phone, income) VALUES (?, ?, ?, ?, ?)
            """,
            sample_customers,
        )

    cur.execute("SELECT COUNT(*) FROM preapproved_offers")
    if cur.fetchone()[0] == 0:
        sample_offers = [
            ("ABCDE1234F", 1, 750000),
            ("BCDEF2345G", 2, 1500000),
        ]
        cur.executemany(
            """
            INSERT INTO preapproved_offers (customer_pan, product_id, preapproved_amount) VALUES (?, ?, ?)
            """,
            sample_offers,
        )

    conn.commit()
    conn.close()


def fetchall(query: str, params: tuple = ()) -> List[sqlite3.Row]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(query, params)
    rows = cur.fetchall()
    conn.close()
    return rows


def fetchone(query: str, params: tuple = ()) -> Optional[sqlite3.Row]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(query, params)
    row = cur.fetchone()
    conn.close()
    return row
