BEGIN;

CREATE TABLE users (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT users_email_canonical CHECK (
        email <> '' AND email = lower(btrim(email))
    )
);

CREATE TABLE commitments (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    type TEXT NOT NULL,
    date DATE NOT NULL,
    start_time TIME,
    end_time TIME,
    description TEXT,
    completed BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT commitments_title_length CHECK (
        char_length(btrim(title)) BETWEEN 1 AND 200
    ),
    CONSTRAINT commitments_type_allowed CHECK (
        type IN ('assignment', 'work', 'event', 'personal')
    ),
    CONSTRAINT commitments_description_length CHECK (
        description IS NULL OR char_length(description) <= 5000
    ),
    CONSTRAINT commitments_time_order CHECK (
        start_time IS NULL OR end_time IS NULL OR end_time > start_time
    )
);

CREATE INDEX commitments_user_date_idx
    ON commitments (user_id, date, start_time, id);

COMMIT;
