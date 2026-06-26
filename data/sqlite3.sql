-- DROP TABLE IF EXISTS macro_index;

CREATE TABLE macro_index (
    id INTEGER PRIMARY KEY,

    country TEXT NOT NULL,                 -- US / CN / EU

    indicator_code TEXT NOT NULL,          -- CPIAUCSL / UNRATE / FEDFUNDS

    indicator_name TEXT NOT NULL,          -- 英文名

    indicator_name_cn TEXT NOT NULL,       -- 中文名

    frequency TEXT DEFAULT 'M',            -- D / W / M / Q

    observation_date DATE NOT NULL,        -- 数据日期（核心维度）

    value REAL NOT NULL,                   -- 数值

    source TEXT DEFAULT 'FRED',           -- 来源

    create_time TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(country, indicator_code, observation_date)
);

ALTER TABLE macro_index
ADD COLUMN yoy_growth REAL;

ALTER TABLE macro_index
ADD COLUMN mom_growth REAL;


-- DROP TABLE IF EXISTS index_info;
--
-- DROP TABLE IF EXISTS index_daily;


CREATE TABLE IF NOT EXISTS index_info (
    index_code     TEXT PRIMARY KEY,                    -- 指数代码，例如：000300、399006
    index_name     TEXT NOT NULL,                       -- 指数名称
    market         TEXT NOT NULL,                       -- SH、SZ、HK、US
    publisher      TEXT,                                -- 发布机构，例如：中证指数有限公司
    category       TEXT,                                -- 宽基、行业、主题、策略等
    currency       TEXT NOT NULL DEFAULT 'CNY',         -- 币种

    create_time    TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_time    TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS index_daily (
    index_code      TEXT NOT NULL,                      -- 指数代码（逻辑关联 index_info.index_code）
    trade_date      INTEGER NOT NULL,                   -- YYYYMMDD，例如：20260626

    open            REAL NOT NULL,
    high            REAL NOT NULL,
    low             REAL NOT NULL,
    close           REAL NOT NULL,

    volume          REAL,                               -- 成交量
    amount          REAL,                               -- 成交额

    amplitude       REAL,                               -- 振幅（%）
    change_percent  REAL,                               -- 涨跌幅（%）
    change_amount   REAL,                               -- 涨跌额

    turnover_rate   REAL,                               -- 换手率（指数通常为空）

    source          TEXT NOT NULL,                      -- 数据来源：akshare、eastmoney、manual...

    create_time     TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_time     TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (index_code, trade_date)
);

CREATE TABLE IF NOT EXISTS update_log (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,

    module           TEXT NOT NULL,                     -- index、macro、etf、stock...
    target_code      TEXT NOT NULL,                     -- 例如：000300、CPIAUCSL

    update_type      TEXT NOT NULL,                     -- full、increment、manual

    start_time       TEXT NOT NULL,
    end_time         TEXT,

    last_trade_date  INTEGER,                           -- 更新到的数据日期（YYYYMMDD）

    status           INTEGER NOT NULL,                  -- 1=成功 0=失败

    message          TEXT,                              -- 错误信息或备注

    create_time      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_index_daily_trade_date
ON index_daily(trade_date);

CREATE INDEX IF NOT EXISTS idx_index_daily_source
ON index_daily(source);

CREATE INDEX IF NOT EXISTS idx_update_log_module
ON update_log(module);

CREATE INDEX IF NOT EXISTS idx_update_log_target_code
ON update_log(target_code);

CREATE INDEX IF NOT EXISTS idx_update_log_create_time
ON update_log(create_time);

CREATE INDEX IF NOT EXISTS idx_update_log_status
ON update_log(status);