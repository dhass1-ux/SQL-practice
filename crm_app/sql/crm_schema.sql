-- =============================================================
-- crm_schema.sql: the CRM app's OWN database, separate from dealer_practice.
--
-- Run this ONCE in MySQL Workbench while connected as your Azure ADMIN user.
-- Paste the whole file into a query tab and run all of it.
--
-- Why a separate database?
--   * Re-running sql/01_create_schema.sql (which drops dealer_practice)
--     does not wipe your duplicate decisions.
--   * The app's user can write here, and ONLY here. The original customer,
--     deal and service rows in dealer_practice stay read-only for the app.
--
-- Safe to re-run: nothing below deletes existing data.
-- =============================================================

CREATE DATABASE IF NOT EXISTS crm;

-- One row per EXTRA customer record that belongs to a main record.
-- Example: duplicate_id 2847 (Bill Rogers) -> primary_id 34 (William Rogers).
-- Unlinking = deleting the row. The customers table itself is never changed.
CREATE TABLE IF NOT EXISTS crm.customer_links (
    duplicate_id  INT          PRIMARY KEY,          -- a record can belong to only ONE main record
    primary_id    INT          NOT NULL,             -- the main record it belongs to
    match_reason  VARCHAR(60)  NOT NULL,             -- e.g. 'same email, same phone' or 'linked by hand'
    linked_at     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT link_not_to_self CHECK (duplicate_id <> primary_id),
    INDEX idx_primary (primary_id)
);

-- Pairs you reviewed and decided are DIFFERENT people,
-- so they stop showing up in the review list.
-- Each pair is stored one way only: smaller id first.
CREATE TABLE IF NOT EXISTS crm.not_duplicates (
    customer_id_low   INT       NOT NULL,
    customer_id_high  INT       NOT NULL,
    decided_at        DATETIME  NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (customer_id_low, customer_id_high),
    CONSTRAINT pair_in_order CHECK (customer_id_low < customer_id_high)
);

-- -------------------------------------------------------------
-- The app's login. Replace the password text with a NEW long password
-- (16+ characters of letters, numbers, - and _), and save it in your
-- password manager. Then put the same password in crm_app/.env.
-- -------------------------------------------------------------
CREATE USER IF NOT EXISTS 'crm_app'@'%' IDENTIFIED BY 'replace-with-a-new-long-password';

-- Read the source data, but never change it:
GRANT SELECT ON dealer_practice.* TO 'crm_app'@'%';

-- Read and write only the app's own tables (no UPDATE needed: unlinking deletes a row):
GRANT SELECT, INSERT, DELETE ON crm.* TO 'crm_app'@'%';

-- Check: this should list exactly the two GRANT lines above (plus USAGE).
SHOW GRANTS FOR 'crm_app'@'%';
