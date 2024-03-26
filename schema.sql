CREATE TABLE IF NOT EXISTS cache (
    url TEXT PRIMARY KEY,
    data TEXT NOT NULL,
    expiry BIGINT NOT NULL,
    type TEXT NOT NULL
);

CREATE TRIGGER IF NOT EXISTS drop_old_cache AFTER INSERT ON cache
BEGIN
    DELETE FROM cache WHERE DATE('now') > DATE(expiry);
END;