#!/bin/sh
set -eu
# PostgreSQL's bootstrap administrator is separate from the application role.
psql --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
  --set=app_user="$DB_USER" --set=app_password="$DB_PASSWORD" --set=database="$POSTGRES_DB" \
  --set=ON_ERROR_STOP=1 <<'SQL'
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;
SELECT format('CREATE ROLE %I LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD %L', :'app_user', :'app_password') \gexec
SELECT format('ALTER DATABASE %I OWNER TO %I', :'database', :'app_user') \gexec
SELECT format('GRANT USAGE, CREATE ON SCHEMA public TO %I', :'app_user') \gexec
SQL
