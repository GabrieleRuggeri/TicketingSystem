-- Add timestamp columns to rooms table
ALTER TABLE rooms
ADD COLUMN created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
ADD COLUMN last_modified_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

-- Add timestamp columns to users table
ALTER TABLE users
ADD COLUMN created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
ADD COLUMN last_modified_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

INSERT INTO schema_migrations (migration_id) VALUES ('02_add_timestamps_to_rooms_and_users.sql');
