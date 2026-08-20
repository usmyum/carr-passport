#!/bin/bash
# Runs once when the Postgres volume is first created.
# Gives the test suite its own database so it can drop/recreate tables freely.
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE DATABASE car_passport_test OWNER $POSTGRES_USER;
EOSQL
