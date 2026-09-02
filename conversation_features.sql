CREATE TABLE IF NOT EXISTS conversation_features (
    conversation_id UUID NOT NULL
        REFERENCES conversations(id)
        ON DELETE CASCADE,

    feature_key TEXT NOT NULL
        REFERENCES feature_flags(feature_key)
        ON DELETE CASCADE,

    enabled BOOLEAN NOT NULL DEFAULT FALSE,

    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    PRIMARY KEY (
        conversation_id,
        feature_key
    )
);


CREATE INDEX IF NOT EXISTS
idx_conversation_features_conversation_id
ON conversation_features (
    conversation_id
);


CREATE INDEX IF NOT EXISTS
idx_conversation_features_feature_key
ON conversation_features (
    feature_key
);