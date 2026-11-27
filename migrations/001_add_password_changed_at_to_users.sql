-- =====================================================================
-- CompBench AI: Database Migration 001
-- Description: Add password_changed_at column to users table
-- Target: MySQL 5.7+ / MySQL 8.0+ / MariaDB / Cloud SQL / AWS RDS
-- Idempotency: Safe to execute repeatedly without error
-- DO NOT EXECUTE AUTOMATICALLY IN PRODUCTION WITHOUT BACKUP
-- =====================================================================

-- Purpose:
-- Supports distributed, persistent session revocation across multiple worker processes
-- and server restarts. When a user changes or resets their password, password_changed_at
-- is updated to the current UTC timestamp, invalidating all session tokens issued prior
-- to that timestamp across all instances.

-- ---------------------------------------------------------------------
-- Idempotent Migration Execution via Dynamic SQL & INFORMATION_SCHEMA
-- ---------------------------------------------------------------------

SET @dbname = DATABASE();
SET @tablename = 'users';
SET @columnname = 'password_changed_at';

SET @preparedStatement = (SELECT IF(
    (
        SELECT COUNT(*)
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE
            TABLE_SCHEMA = @dbname
            AND TABLE_NAME = @tablename
            AND COLUMN_NAME = @columnname
    ) > 0,
    'SELECT 1 /* Notice: column password_changed_at already exists in users table - skipping */',
    'ALTER TABLE `users` ADD COLUMN `password_changed_at` DATETIME NULL DEFAULT NULL AFTER `is_verified`'
));

PREPARE addColumnIfNotExists FROM @preparedStatement;
EXECUTE addColumnIfNotExists;
DEALLOCATE PREPARE addColumnIfNotExists;

-- ---------------------------------------------------------------------
-- Verification Query
-- ---------------------------------------------------------------------
-- Run this query after migration to verify column presence:
-- SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT
-- FROM INFORMATION_SCHEMA.COLUMNS
-- WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'users' AND COLUMN_NAME = 'password_changed_at';

-- ---------------------------------------------------------------------
-- Rollback / Down Migration (Manual Emergency Reference)
-- ---------------------------------------------------------------------
-- To roll back this migration, execute:
-- ALTER TABLE `users` DROP COLUMN `password_changed_at`;
