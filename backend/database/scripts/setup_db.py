#!/usr/bin/env python3
"""
Database setup script for the Warder Agentic System Infrastructure.
This script initializes the database with the required schema and extensions.
"""

import os
import sys
import argparse
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT


def parse_args():
    parser = argparse.ArgumentParser(description="Setup Warder database")
    parser.add_argument(
        "--host", default=os.environ.get("DB_HOST", "localhost"), help="Database host"
    )
    parser.add_argument(
        "--port", default=os.environ.get("DB_PORT", "5432"), help="Database port"
    )
    parser.add_argument(
        "--user", default=os.environ.get("DB_USER", "postgres"), help="Database user"
    )
    parser.add_argument(
        "--password",
        default=os.environ.get("DB_PASSWORD", "postgres"),
        help="Database password",
    )
    parser.add_argument(
        "--dbname", default=os.environ.get("DB_NAME", "warder"), help="Database name"
    )
    parser.add_argument("--drop", action="store_true", help="Drop database if exists")
    return parser.parse_args()


def execute_sql_file(conn, filepath):
    """Execute SQL statements from a file."""
    print(f"Executing SQL file: {filepath}")
    with open(filepath, "r") as f:
        sql = f.read()

    with conn.cursor() as cur:
        cur.execute(sql)
    conn.commit()


def main():
    args = parse_args()

    # Connect to PostgreSQL server
    try:
        conn = psycopg2.connect(
            host=args.host, port=args.port, user=args.user, password=args.password
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        print(f"Connected to PostgreSQL server at {args.host}:{args.port}")
    except Exception as e:
        print(f"Error connecting to PostgreSQL server: {e}")
        sys.exit(1)

    # Create or recreate database
    try:
        with conn.cursor() as cur:
            if args.drop:
                print(f"Dropping database {args.dbname} if exists...")
                cur.execute(f"DROP DATABASE IF EXISTS {args.dbname}")

            # Check if database exists
            cur.execute(f"SELECT 1 FROM pg_database WHERE datname = '{args.dbname}'")
            if cur.fetchone() is None:
                print(f"Creating database {args.dbname}...")
                cur.execute(f"CREATE DATABASE {args.dbname}")
                print(f"Database {args.dbname} created successfully")
            else:
                print(f"Database {args.dbname} already exists")
    except Exception as e:
        print(f"Error creating database: {e}")
        conn.close()
        sys.exit(1)

    # Close connection to server and connect to the new database
    conn.close()

    try:
        conn = psycopg2.connect(
            host=args.host,
            port=args.port,
            user=args.user,
            password=args.password,
            dbname=args.dbname,
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        print(f"Connected to database {args.dbname}")
    except Exception as e:
        print(f"Error connecting to database {args.dbname}: {e}")
        sys.exit(1)

    # Get the directory of the current script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    init_dir = os.path.join(os.path.dirname(script_dir), "init")

    # Execute initialization scripts
    try:
        # Use the basic initialization SQL file for testing
        basic_init_file = os.path.join(init_dir, "01-init-basic.sql")
        if os.path.exists(basic_init_file):
            execute_sql_file(conn, basic_init_file)
        else:
            print(f"Warning: Basic initialization file {basic_init_file} not found")
            # Fallback to using all SQL files
            sql_files = sorted([f for f in os.listdir(init_dir) if f.endswith(".sql")])
            for sql_file in sql_files:
                execute_sql_file(conn, os.path.join(init_dir, sql_file))

        print("Database initialization completed successfully")
    except Exception as e:
        print(f"Error initializing database: {e}")
        conn.close()
        sys.exit(1)

    conn.close()
    print("Database setup completed successfully")


if __name__ == "__main__":
    main()
