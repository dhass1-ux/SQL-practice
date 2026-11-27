-- =============================================================
-- crm_notes.sql: adds notes and follow-ups (Phase 5).
--
-- Run this ONCE in MySQL Workbench while connected as your Azure ADMIN user,
-- AFTER crm_schema.sql. Paste the whole file into a query tab and run all of it.
--
-- Each change to the database's structure gets its own script like this one,
-- run once, in order. Developers call these "migrations".
--
-- Safe to re-run: nothing below deletes existing data.
-- =============================================================

-- One row per note. A note with a follow_up_date is a follow-up;
-- it stays "open" until done_at is filled in.
-- Times are stored in UTC (the server's clock); the app shows them in Eastern time.
CREATE TABLE IF NOT EXISTS crm.customer_notes (
    note_id         INT            AUTO_INCREMENT PRIMARY KEY,  -- MySQL numbers each note: 1, 2, 3...
    customer_id     INT            NOT NULL,                    -- the person's main record when written
    body            VARCHAR(2000)  NOT NULL,
    follow_up_date  DATE           NULL,                        -- empty = plain note
    done_at         DATETIME       NULL,                        -- empty = follow-up still open
    created_at      DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_customer (customer_id),
    INDEX idx_open_follow_ups (done_at, follow_up_date)
);

-- crm_app can already SELECT, INSERT and DELETE in crm (from crm_schema.sql).
-- Marking a follow-up done changes one value, so allow UPDATE on ONLY that
-- column of ONLY this table. The text of a saved note can never be changed.
GRANT UPDATE (done_at) ON crm.customer_notes TO 'crm_app'@'%';

-- Check: the list should now include
--   GRANT UPDATE (`done_at`) ON `crm`.`customer_notes` TO `crm_app`@`%`
SHOW GRANTS FOR 'crm_app'@'%';
