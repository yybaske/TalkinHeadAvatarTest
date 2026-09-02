CREATE TABLE IF NOT EXISTS feature_flags (
    feature_key TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    description TEXT,
    category TEXT NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT FALSE,
    sort_order INTEGER NOT NULL DEFAULT 0,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


INSERT INTO feature_flags (
    feature_key,
    display_name,
    description,
    category,
    enabled,
    sort_order
)
VALUES
    (
        'local_rag',
        '社内文書検索',
        'PostgreSQLおよびpgvectorに登録された社内文書を検索します。',
        'core',
        TRUE,
        10
    ),
    (
        'mcp',
        'MCP連携',
        'MCPサーバーを利用した外部システム連携を有効にします。',
        'integration',
        FALSE,
        20
    ),
    (
        'mcp_servicenow',
        'ServiceNow',
        'MCPを経由してServiceNowを利用します。',
        'mcp',
        FALSE,
        30
    ),
    (
        'mcp_aws',
        'AWS',
        'MCPを経由してAWSを利用します。',
        'mcp',
        FALSE,
        40
    ),
    (
        'mcp_github',
        'GitHub',
        'MCPを経由してGitHubを利用します。',
        'mcp',
        FALSE,
        50
    ),
    (
        'mcp_sharepoint',
        'SharePoint',
        'MCPを経由してSharePointを利用します。',
        'mcp',
        FALSE,
        60
    ),
    (
        'external_actions',
        '外部システム更新',
        '外部システムへの登録・更新などの操作を許可します。',
        'security',
        FALSE,
        100
    )
ON CONFLICT (feature_key)
DO NOTHING;

INSERT INTO feature_flags (
    feature_key,
    display_name,
    description,
    category,
    enabled,
    sort_order
)
VALUES (
    'mcp_local',
    'ローカルMCP',
    'MCP動作確認用のローカルToolを利用します。',
    'mcp',
    TRUE,
    25
)
ON CONFLICT (feature_key)
DO UPDATE SET
    display_name = EXCLUDED.display_name,
    description = EXCLUDED.description,
    category = EXCLUDED.category,
    enabled = EXCLUDED.enabled,
    sort_order = EXCLUDED.sort_order,
    updated_at = NOW();