CREATE TABLE IF NOT EXISTS import_batches (
    batch_id TEXT PRIMARY KEY,
    product_type TEXT NOT NULL CHECK(product_type IN ('SPA','FNB')),
    source_filename TEXT NOT NULL,
    period_label TEXT,
    imported_at TEXT NOT NULL,
    file_hash TEXT NOT NULL,
    status TEXT NOT NULL,
    rows_seen INTEGER NOT NULL DEFAULT 0,
    rows_inserted INTEGER NOT NULL DEFAULT 0,
    rows_skipped INTEGER NOT NULL DEFAULT 0,
    notes TEXT
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_batches_file_hash_product
ON import_batches(file_hash, product_type);

CREATE TABLE IF NOT EXISTS conversations (
    conversation_key TEXT PRIMARY KEY,
    external_conversation_id TEXT NOT NULL,
    product_type TEXT NOT NULL CHECK(product_type IN ('SPA','FNB')),
    first_batch_id TEXT NOT NULL,
    started_at TEXT,
    ended_at TEXT,
    message_count INTEGER NOT NULL DEFAULT 0,
    customer_message_count INTEGER NOT NULL DEFAULT 0,
    staff_message_count INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY(first_batch_id) REFERENCES import_batches(batch_id)
);

CREATE INDEX IF NOT EXISTS idx_conversations_product ON conversations(product_type);
CREATE INDEX IF NOT EXISTS idx_conversations_started ON conversations(started_at);

CREATE TABLE IF NOT EXISTS messages (
    message_hash TEXT PRIMARY KEY,
    conversation_key TEXT NOT NULL,
    batch_id TEXT NOT NULL,
    sender_type TEXT NOT NULL CHECK(sender_type IN ('customer','staff','unknown')),
    sender_raw TEXT,
    message_text TEXT NOT NULL,
    sent_at TEXT,
    source_file TEXT,
    FOREIGN KEY(conversation_key) REFERENCES conversations(conversation_key) ON DELETE CASCADE,
    FOREIGN KEY(batch_id) REFERENCES import_batches(batch_id)
);

CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_key);
CREATE INDEX IF NOT EXISTS idx_messages_sent_at ON messages(sent_at);
CREATE INDEX IF NOT EXISTS idx_messages_sender ON messages(sender_type);

CREATE TABLE IF NOT EXISTS conversation_metrics (
    conversation_key TEXT PRIMARY KEY,
    first_response_minutes REAL,
    conversation_duration_minutes REAL,
    avg_staff_response_minutes REAL,
    is_dropoff INTEGER NOT NULL DEFAULT 0,
    has_purchase_signal INTEGER NOT NULL DEFAULT 0,
    purchase_signal_count INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(conversation_key) REFERENCES conversations(conversation_key) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS conversation_tags (
    conversation_key TEXT NOT NULL,
    tag_type TEXT NOT NULL CHECK(tag_type IN ('need','interest','pain_point','purchase_signal')),
    tag_name TEXT NOT NULL,
    hit_count INTEGER NOT NULL DEFAULT 1,
    PRIMARY KEY(conversation_key, tag_type, tag_name),
    FOREIGN KEY(conversation_key) REFERENCES conversations(conversation_key) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_tags_type_name ON conversation_tags(tag_type, tag_name);
CREATE INDEX IF NOT EXISTS idx_messages_batch_conversation
ON messages(batch_id, conversation_key);

CREATE TABLE IF NOT EXISTS analysis_runs (
    batch_id TEXT PRIMARY KEY,
    analyzed_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'completed',
    conversations_analyzed INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY(batch_id) REFERENCES import_batches(batch_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS batch_conversation_metrics (
    batch_id TEXT NOT NULL,
    conversation_key TEXT NOT NULL,
    product_type TEXT NOT NULL,
    external_conversation_id TEXT NOT NULL,
    started_at TEXT,
    ended_at TEXT,
    message_count INTEGER NOT NULL DEFAULT 0,
    customer_message_count INTEGER NOT NULL DEFAULT 0,
    staff_message_count INTEGER NOT NULL DEFAULT 0,
    first_response_minutes REAL,
    conversation_duration_minutes REAL,
    avg_staff_response_minutes REAL,
    is_dropoff INTEGER NOT NULL DEFAULT 0,
    has_purchase_signal INTEGER NOT NULL DEFAULT 0,
    purchase_signal_count INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY(batch_id, conversation_key),
    FOREIGN KEY(batch_id) REFERENCES import_batches(batch_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS batch_conversation_tags (
    batch_id TEXT NOT NULL,
    conversation_key TEXT NOT NULL,
    tag_type TEXT NOT NULL,
    tag_name TEXT NOT NULL,
    hit_count INTEGER NOT NULL DEFAULT 1,
    PRIMARY KEY(batch_id, conversation_key, tag_type, tag_name),
    FOREIGN KEY(batch_id) REFERENCES import_batches(batch_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_batch_metrics_batch ON batch_conversation_metrics(batch_id);
CREATE INDEX IF NOT EXISTS idx_batch_tags_batch_type ON batch_conversation_tags(batch_id, tag_type, tag_name);
