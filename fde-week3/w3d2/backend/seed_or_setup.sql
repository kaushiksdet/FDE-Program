-- One-step database setup. Run from the repository root:
--   psql -U postgres -f backend/seed_or_setup.sql
--
-- Creates the fde_db database (if missing), connects to it, and applies schema.sql.
-- Encounter rows are NOT inserted here; load them with `python backend/data_loader.py`.

SELECT 'CREATE DATABASE fde_db'
WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = 'fde_db')
\gexec

\connect fde_db

\ir schema.sql

-- Verification queries (useful for the PostgreSQL screenshot after loading data):
--   SELECT COUNT(*) FROM patient_encounters;
--   SELECT risk_level, COUNT(*) FROM patient_encounters GROUP BY risk_level;
--   SELECT status, COUNT(*) FROM care_interventions GROUP BY status;
--   SELECT * FROM patient_encounters ORDER BY risk_score DESC LIMIT 10;
