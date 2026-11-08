CREATE TABLE IF NOT EXISTS queue (
 event_key TEXT PRIMARY KEY, payload TEXT NOT NULL, urgent INTEGER NOT NULL DEFAULT 0,
 created_at INTEGER NOT NULL, expires_at INTEGER NOT NULL,
 status TEXT NOT NULL DEFAULT 'ready', claimed_at INTEGER, sent_at INTEGER,
 slot TEXT UNIQUE, message_id INTEGER
);
CREATE TABLE IF NOT EXISTS events (
 id INTEGER PRIMARY KEY AUTOINCREMENT, at INTEGER NOT NULL, code TEXT NOT NULL,
 event_key TEXT, slot TEXT
);
CREATE INDEX IF NOT EXISTS queue_ready ON queue(status,urgent,created_at);
CREATE INDEX IF NOT EXISTS queue_sent ON queue(status,sent_at);
