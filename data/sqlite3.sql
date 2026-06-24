DROP TABLE IF EXISTS macro_index;

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