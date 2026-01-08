CREATE TABLE bots (
    id TEXT PRIMARY KEY,
    strategy TEXT NOT NULL,
    params JSONB NOT NULL,
    status TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bot_id TEXT REFERENCES bots(id) ON DELETE CASCADE,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,
    price NUMERIC NOT NULL,
    quantity NUMERIC NOT NULL,
    executed_at TIMESTAMP DEFAULT now()
);

CREATE TABLE bot_logs (
    id BIGSERIAL PRIMARY KEY,
    bot_id TEXT REFERENCES bots(id) ON DELETE CASCADE,
    level TEXT NOT NULL,
    message TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT now()
);