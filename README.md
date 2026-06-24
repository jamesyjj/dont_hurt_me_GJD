# ETF份额数据分析工具

上海证券交易所ETF份额历史数据采集与分析工具。

## 功能特性

- 自动采集ETF每日份额数据（支持全量800+只ETF）
- SQLite本地数据库存储
- 智能分页处理
- 节假日自动跳过
- 并发加速采集
- 份额趋势HTML可视化
- 支持简称/全称切换展示

## 项目结构

```
etf-project/
├── src/etf/              # ETF核心包
│   ├── __init__.py
│   ├── database.py       # 数据库操作
│   ├── fetcher.py        # 数据拉取
│   ├── queries.py        # 数据查询
│   └── cli.py            # 命令行入口
├── src/macro_economy/    # 宏观经济数据
│   ├── __init__.py
│   └── usa.py            # FRED数据获取
├── scripts/              # 独立脚本
│   ├── etf_trend.py      # 趋势图生成
│   └── etf_compare.py    # ETF对比工具
├── data/                 # 数据目录
│   └── etf_data.db       # SQLite数据库
├── tests/                # 测试目录
├── docs/                 # 文档目录
├── .claude/skills/etf/   # Claude Code技能
├── README.md
├── requirements.txt
└── pyproject.toml
```

## 安装依赖

```bash
pip install -r requirements.txt
```

## 使用方法

### 命令行工具（推荐）

```bash
# 采集数据
python -m src.etf.cli fetch 5

# 查询份额上升的ETF
python -m src.etf.cli query 126

# 查看证券ETF份额变化（支持排序 + 近N日跨度）
python -m src.etf.cli securities change 5

# 查看某行业ETF份额变化（支持排序 + 近N日跨度）
python -m src.etf.cli industry 医药 change 300

# 份额增加前10名
python -m src.etf.cli top 10

# 份额增幅前10名
python -m src.etf.cli top_pct 10

# 查看某ETF趋势
python -m src.etf.cli trend 563360

# 查看ETF份额-价格详细走势（含日变化/日收益/排名）
python -m src.etf.cli detail 513180 30

# 检查数据完整性
python -m src.etf.cli check [天数]    # 检查数据完整性（默认20天）

# 更新ETF完整名称
python -m src.etf.cli update_names

# 采集所有ETF十大持有人（从新浪财经）
python -m src.etf.cli holders      

# 查看某ETF十大持有人        
python -m src.etf.cli holders 510300   

# 按持有人类型查询（如：保险/信托/私募） 
python -m src.etf.cli holders_type 汇金    

# 汇金系持仓ETF份额/价格走势（控制台Top10+CSV全量）
python -m src.etf.cli huijin 20

```

### 独立脚本

```bash
# 生成ETF趋势HTML图
python scripts/etf_trend.py 513180 500

# ETF价格-份额双折线图
python scripts/etf_price_volume.py 512010 2025-05-01 2026-06-03

# 对比两只ETF
python scripts/etf_compare.py 512880 512070

# 查询某ETF的汇金系持仓及估算买卖情况
python scripts/huijin_etf.py 510330

# 汇金系ETF买卖趋势分析（基准日2025.12.31，固定）
python scripts/huijin_analysis.py

# 汇金系买卖趋势分析（自定义起始日/结束日）
python scripts/huijin_trade.py 2025-12-31 2026-06-09
python scripts/huijin_trade.py 2026-06-04 2026-06-10


```

### 宏观数据（FRED）

```bash
# 获取FRED数据并存入macro_index表（编辑usa.py切换series_id）
python -m src.macro_economy.usa

# 可用指标：
#   CPIAUCSL  - 消费者物价指数（CPI，月频）
#   UNRATE    - 失业率（月频）
#   FEDFUNDS  - 联邦基金利率（月频）
#
# 建表DDL：data/sqlite3.sql
```

## 数据库表结构

### etf_info - ETF基本信息
| 字段 | 类型 | 说明 |
|------|------|------|
| sec_code | TEXT | ETF代码 (PK) |
| sec_name | TEXT | ETF简称 |
| full_name | TEXT | ETF全称（含公司） |
| etf_type | TEXT | ETF类型 |

### etf_daily_share - 每日份额
| 字段        | 类型    | 说明           |
| ----------- | ------- | -------------- |
| sec_code    | TEXT    | ETF代码 (PK)   |
| stat_date   | TEXT    | 日期 (PK)      |
| tot_vol     | REAL    | 总份额（万份） |
| num         | INTEGER | 排名           |
| close_price | REAL    | 收盘价         |
| market      | TEXT    | 交易所         |

### etf_top_holders - ETF十大持有人
| 字段        | 类型    | 说明               |
| ----------- | ------- | ------------------ |
| sec_code    | TEXT    | ETF代码            |
| stat_date   | TEXT    | 报告期（如2025-12-31） |
| rank        | INTEGER | 排名（1-10）      |
| holder_name | TEXT    | 持有人名称         |
| holder_share| REAL    | 持有份额（份）     |
| holder_pct  | REAL    | 占总份额比（%）    |
| create_at | TEXT | 日期 |

*数据来源：新浪财经基金档案页，每年4-5月更新年报，8-9月更新半年报。实时性约滞后4-5个月。*

### macro_index - 宏观经济指标

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 自增主键 |
| country | TEXT | 国家代码（US / CN / EU）|
| indicator_code | TEXT | 指标代码（如 CPIAUCSL / UNRATE / FEDFUNDS）|
| indicator_name | TEXT | 指标英文名 |
| indicator_name_cn | TEXT | 指标中文名 |
| frequency | TEXT | 频率（D=日 / W=周 / M=月 / Q=季），默认 'M' |
| observation_date | DATE | 数据日期（核心维度）|
| value | REAL | 数值 |
| source | TEXT | 数据来源，默认 'FRED' |
| create_time | TEXT | 创建时间 |

> 唯一约束：(country, indicator_code, observation_date)，重复时更新全部字段。建表DDL：`data/sqlite3.sql`

## 数据来源

上海证券交易所 (SSE) 官方接口
- 份额接口: `commonQuery.do?sqlId=COMMON_SSE_ZQPZ_ETFZL_XXPL_ETFGM_SEARCH_L`
- 全称接口: `security/stock/queryExpandName.do`
- 每日更新频率: 收盘后清算完成后（约20:00-22:00）
