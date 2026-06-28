"""
ETF命令行工具
"""
import sys
import os
from .fetcher import fetch_data, update_full_names
from .fetcher_szse import fetch_data as fetch_szse_data
from .fetcher_holders import update_holders
from ..macro_economy.usa import query_series
from .queries import (
    query_rising_etfs,
    query_etf_trend,
    query_etf_detail,
    query_huijin_etf_trend,
    query_securities_etf,
    query_industry_etf,
    query_top_etfs,
    check_data_completeness, query_etf_info,
    query_top_holders, query_holders_by_type
)


def print_rising_etfs(results):
    """打印份额上升的ETF列表"""
    print("=" * 90)
    print(f"{'Code':<10} {'Name':<14} {'Days':<5} {'Start(亿)':<12} {'End(亿)':<12} {'Change%':<10} {'Period'}")
    print("-" * 90)

    for row in results:
        sec_code, sec_name, data_days, start_vol, latest_vol, change_pct, start_date, end_date = row
        name = sec_name[:12] if sec_name else sec_code
        period = f"{start_date[-5:]}~{end_date[-5:]}"
        print(f"{sec_code:<10} {name:<14} {data_days:<5} {start_vol/10000:<12.2f} {latest_vol/10000:<12.2f} {change_pct:>+8.2f}%  {period}")

    print("-" * 90)
    print(f"Total: {len(results)} ETFs with rising shares")


def main():
    if len(sys.argv) < 2:
        print("""
ETF份额数据分析工具

用法:
    python -m src.etf.cli fetch [天数]         # 采集上交所数据
    python -m src.etf.cli fetch_szse [天数]    # 采集深交所数据
    python -m src.etf.cli query              # 查询份额上升的ETF
    python -m src.etf.cli trend [代码]       # 查看某ETF趋势
    python -m src.etf.cli detail [代码] [天数]  # 查看ETF份额-价格详细走势
    python -m src.etf.cli check [天数]         # 检查数据完整性（默认20天）
    python -m src.etf.cli securities [sort] [天数]     # 证券/保险ETF，可选近N日跨度
    python -m src.etf.cli industry <关键词> [sort] [天数]  # 行业ETF，可选近N日跨度
    python -m src.etf.cli top [n]           # 查看份额增加最多的n只ETF
    python -m src.etf.cli top_pct [n]       # 查看份额增幅最多的n只ETF
    python -m src.etf.cli update_names       # 更新ETF完整名称
    python -m src.etf.cli holders            # 采集所有ETF十大持有人数据
    python -m src.etf.cli holders [代码]     # 查看某ETF十大持有人
    python -m src.etf.cli holders_type [关键词] # 按持有人类型查询(如:保险/信托/私募)
    python -m src.etf.cli huijin [天数]      # 汇金系持仓ETF份额/价格走势（控制台Top10+CSV全量）
    python -m src.etf.cli macro [系列ID] [月份]  # 查询宏观数据系列值和同比/环比增长（默认当前月）
""")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == 'fetch':
        days = int(sys.argv[2]) if len(sys.argv) > 2 else 126
        fetch_data(days)
    elif cmd == 'fetch_szse':
        days = int(sys.argv[2]) if len(sys.argv) > 2 else 500
        fetch_szse_data(days)
    elif cmd == 'query':
        days = int(sys.argv[2]) if len(sys.argv) > 2 else 126
        results = query_rising_etfs(days)
        print_rising_etfs(results)
    elif cmd == 'trend':
        sec_code = sys.argv[2] if len(sys.argv) > 2 else '510050'
        days = int(sys.argv[3]) if len(sys.argv) > 3 else 100
        etf_info = query_etf_info(sec_code)
        if etf_info is None:
            print("ETF {} not found".format(sec_code))
            return
        results = query_etf_trend(sec_code, days)
        print(f"\nETF {sec_code} {etf_info['full_name']} {etf_info['sec_name']} {etf_info['etf_type']} trend (last {days} days):")
        print(f"{'Date':<12} {'Volume(万份)':>18}")
        print("-" * 35)
        for date, vol in results[-20:]:
            print(f"{date:<12} {vol:>18.2f}")
    elif cmd == 'detail':
        sec_code = sys.argv[2] if len(sys.argv) > 2 else '510050'
        days = int(sys.argv[3]) if len(sys.argv) > 3 else 30
        etf_info = query_etf_info(sec_code)
        if etf_info is None:
            print(f"ETF {sec_code} not found")
            return
        results = query_etf_detail(sec_code, days)
        print(f"\n{etf_info['full_name']} ({sec_code}) 份额-价格走势")
        print(f"{'='*115}")
        print(f"{'日期':<12} {'份额(万)':>14} {'日变化':>12} {'份额增幅':>9} {'价格':>8} {'日收益':>8} {'排名':>5}")
        print(f"{'-'*115}")
        for row in results:
            stat_date, tot_vol, daily_chg, daily_chg_pct, close_price, daily_ret, num = row
            chg_str   = f'{daily_chg:>+12,.0f}' if daily_chg else '           ·'
            pct_str   = f'{daily_chg_pct:>+8.2f}%' if daily_chg_pct is not None else '       ·'
            price_str = f'{close_price:>8.3f}' if close_price else '   N/A'
            ret_str   = f'{daily_ret:>+7.2f}%' if daily_ret is not None else '      ·'
            rank_str  = f'{num:>5}' if num else '    ·'
            print(f'{stat_date:<12} {tot_vol:>14,.0f} {chg_str} {pct_str} {price_str} {ret_str} {rank_str}')
        print(f"{'='*115}")
    elif cmd == 'huijin':
        days = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        results = query_huijin_etf_trend(days)
        if not results:
            print('未找到汇金系持仓ETF数据')
            return

        # 收集所有日期并去重排序
        all_dates = set()
        for _, _, _, data in results:
            for d, _, _ in data:
                all_dates.add(d)
        dates = sorted(all_dates)

        # 构建 {code: {date: (vol, price)}} 查找表
        etf_map = {}
        for code, name, pct, data in results:
            etf_map[code] = {
                'name': name, 'pct': pct,
                'dmap': {d: (v, p) for d, v, p in data}
            }

        # ── 控制台：前10只 ──
        top10 = results[:10]
        N = len(top10)
        COL_W = 15  # 每列宽度 "2819929/4.93"
        SEP_W = 12 + N * (COL_W + 1)  # 日期 + N列
        print(f'\n汇金系持仓ETF份额/价格走势 Top{N}（近{days}天）')
        print(f'{"="*SEP_W}')
        # 表头行1: 代码
        header1 = f'{"日期":<12}'
        header2 = f'{"":12}'
        for code, name, pct, _ in top10:
            short_name = name[:8] if name else code
            header1 += f' {code:<{COL_W}}'
            header2 += f' {f"{short_name}({pct:.1f}%)":<{COL_W}}'
        print(header1)
        print(header2)
        print(f'{"-"*SEP_W}')
        # 数据行
        for d in dates:
            row_str = f'{d:<12}'
            for code, _, _, _ in top10:
                entry = etf_map[code]['dmap'].get(d)
                if entry:
                    vol, price = entry
                    cell = f'{vol:,.0f}/{price:.3f}' if price else f'{vol:,.0f}/-'
                else:
                    cell = '-'
                row_str += f' {cell:>{COL_W}}'
            print(row_str)
        print(f'{"="*SEP_W}')
        print(f'共 {len(results)} 只ETF，控制台显示前{N}只')

        # ── CSV：全量导出 ──
        csv_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            'data', 'huijin_etf_trend.csv'
        )
        with open(csv_path, 'w', encoding='utf-8-sig') as f:
            # 表头: 日期, 代码(名称,汇金占比), ...
            headers = ['日期'] + [f'{code}({etf_map[code]["name"]},{etf_map[code]["pct"]:.1f}%)' for code, _, _, _ in results]
            f.write(','.join(headers) + '\n')
            for d in dates:
                cells = [d]
                for code, _, _, _ in results:
                    entry = etf_map[code]['dmap'].get(d)
                    if entry:
                        cells.append(f'{entry[0]:.0f}/{entry[1]:.3f}' if entry[1] else f'{entry[0]:.0f}/-')
                    else:
                        cells.append('-')
                f.write(','.join(cells) + '\n')
        print(f'全量数据已导出: {csv_path}')
    elif cmd == 'check':
        days = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else 20
        daily_counts = check_data_completeness(days)
        print(f"Data Completeness Check (近{days}天):")
        print("=" * 50)
        print(f"{'Date':<15} {'ETF Count':<10} {'Status'}")
        print("-" * 50)
        for date, cnt in daily_counts:
            status = "OK" if cnt > 800 else "LOW"
            print(f"{date:<15} {cnt:<10} {status}")
    elif cmd == 'securities':
        # 解析参数: [sort] [span]
        sort, span = 'volume', 1
        for a in sys.argv[2:]:
            if a in ('volume', 'change', 'pct'):
                sort = a
            elif a.isdigit():
                span = int(a)
        results, latest_date, prev_date = query_securities_etf(sort, span)
        if not results:
            print('数据不足')
            return
        sort_label = {'volume': '按份额从高到低', 'change': '按变化从高到低', 'pct': '按增幅从高到低'}.get(sort, '按份额')
        print(f'\n证券/保险ETF份额变化 {sort_label} ({prev_date} -> {latest_date}, 近{span}日):')
        print('=' * 120)
        print(f'{"代码":<10} {"名称":<20} {"上日份额(万)":>14} {"最新份额(万)":>14} {"变化(万)":>12} {"增幅":>10}')
        print('-' * 120)
        for row in results:
            name = (row[1] or row[0])[:18]
            print(f'{row[0]:<10} {name:<20} {row[3]:>14.2f} {row[2]:>14.2f} {row[4]:>+12.2f} {row[5]:>+9.2f}%')
        print('=' * 120)
    elif cmd == 'industry':
        keyword = sys.argv[2] if len(sys.argv) > 2 else None
        if not keyword:
            print('用法: python -m src.etf.cli industry <关键词> [volume|change|pct] [天数]')
            print('示例: python -m src.etf.cli industry 医药 change 5')
            return
        # 解析参数: [sort] [span]
        sort, span = 'volume', 1
        for a in sys.argv[3:]:
            if a in ('volume', 'change', 'pct'):
                sort = a
            elif a.isdigit():
                span = int(a)
        results, latest_date, prev_date = query_industry_etf(keyword, sort, span)
        if not results:
            print(f'未找到包含 "{keyword}" 的ETF')
            return
        sort_label = {'volume': '按份额从高到低', 'change': '按变化从高到低', 'pct': '按增幅从高到低'}.get(sort, '按份额')
        print(f'\n「{keyword}」行业ETF份额变化 {sort_label} ({prev_date} -> {latest_date}, 近{span}日)')
        print('=' * 120)
        print(f'{"代码":<10} {"名称":<20} {"上日份额(万)":>14} {"最新份额(万)":>14} {"变化(万)":>12} {"增幅":>10}')
        print('-' * 120)
        for row in results:
            name = (row[1] or row[0])[:18]
            print(f'{row[0]:<10} {name:<20} {row[3]:>14.2f} {row[2]:>14.2f} {row[4]:>+12.2f} {row[5]:>+9.2f}%')
        print('=' * 120)
        print(f'共 {len(results)} 只ETF')
    elif cmd == 'top':
        n = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        results, latest_date, prev_date = query_top_etfs(n, 'change')
        if not results:
            return
        print(f'\n份额增加前{n}名 ({prev_date} -> {latest_date}):')
        print('=' * 120)
        print(f'{"排名":<4} {"代码":<10} {"名称":<20} {"最新份额(万)":>16} {"变化(万)":>12} {"增幅":>10}')
        print('-' * 120)
        for i, row in enumerate(results, 1):
            name = (row[1] or row[0])[:18]
            print(f'{i:<4} {row[0]:<10} {name:<20} {row[2]:>16.2f} {row[4]:>+12.2f} {row[5]:>+9.2f}%')
        print('=' * 120)
    elif cmd == 'top_pct':
        n = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        results, latest_date, prev_date = query_top_etfs(n, 'pct')
        if not results:
            return
        print(f'\n份额增幅前{n}名 ({prev_date} -> {latest_date}):')
        print('=' * 120)
        print(f'{"排名":<4} {"代码":<10} {"名称":<20} {"最新份额(万)":>16} {"变化(万)":>12} {"增幅":>10}')
        print('-' * 120)
        for i, row in enumerate(results, 1):
            name = (row[1] or row[0])[:18]
            print(f'{i:<4} {row[0]:<10} {name:<20} {row[2]:>16.2f} {row[4]:>+12.2f} {row[5]:>+9.2f}%')
        print('=' * 120)
    elif cmd == 'update_names':
        update_full_names()
    elif cmd == 'holders':
        sec_code = sys.argv[2] if len(sys.argv) > 2 else None
        if sec_code:
            holders, stat_date = query_top_holders(sec_code)
            if not holders:
                print(f'没有找到 {sec_code} 的持有人数据，请先运行: python -m src.etf.cli holders')
                return
            etf_info = query_etf_info(sec_code)
            name = etf_info['full_name'] if etf_info else sec_code
            print(f'\n{name} 十大持有人 (报告期: {stat_date}):')
            print('=' * 80)
            print(f'{"排名":<6} {"持有人名称":<40} {"持有份额":>15} {"占比":>10}')
            print('-' * 80)
            for rank, holder_name, share, pct in holders:
                print(f'{rank:<6} {holder_name[:38]:<40} {share:>15,.0f} {pct:>9.2f}%')
            print('=' * 80)
        else:
            # 采集所有ETF十大持有人
            print('正在从新浪财经采集所有ETF十大持有人数据...')
            count = update_holders()
            print(f'完成，共采集 {count} 只ETF')
    elif cmd == 'holders_type':
        holder_type = sys.argv[2] if len(sys.argv) > 2 else None
        results = query_holders_by_type(holder_type, min_pct=0.5)
        if not results:
            print('没有找到符合条件的持有人数据')
            return
        print(f'\nETF十大持有人查询 (持有比例>=0.5%, 关键词: {holder_type or "全部"}):')
        print('=' * 110)
        print(f'{"Code":<10} {"ETF名称":<28} {"持有人名称":<36} {"占比":>8} {"报告期":<12}')
        print('-' * 110)
        for row in results[:50]:
            sec_code, full_name, holder_name, pct, stat_date = row
            name = (full_name or sec_code)[:26]
            print(f'{sec_code:<10} {name:<28} {holder_name[:34]:<36} {pct:>7.2f}% {stat_date}')
        print('=' * 110)
        print(f'共 {len(results)} 条结果（显示前50条）')
    elif cmd == 'macro':
        series_id = sys.argv[2] if len(sys.argv) > 2 else None
        if series_id is None:
            print("用法: python -m src.etf.cli macro <series_id> [月份]")
            print("系列ID: CPIAUCSL / UNRATE / FEDFUNDS / CPILFESL / PPIACO / PCEPI / PCEPILFE / DGS10")
            return
        month = sys.argv[3] if len(sys.argv) > 3 else None
        result = query_series(series_id, month=month)
        if result["value"] is not None:
            print(f"\n值: {result['value']}")
            print(f"同比增长: {result['yoy']:+.5f}%" if result['yoy'] is not None else "同比增长: N/A")
            print(f"环比增长: {result['mom']:+.5f}%" if result['mom'] is not None else "环比增长: N/A")
    else:
        print(f"Unknown command: {cmd}")
        print("Run without arguments to see usage")


if __name__ == '__main__':
    main()
