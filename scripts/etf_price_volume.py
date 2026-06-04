"""
ETF价格与份额双折线图 + 逐日对比表 (Plotly版)
用法: python scripts/etf_price_volume.py [ETF代码] [开始日期] [结束日期]
示例: python scripts/etf_price_volume.py 513180 2026-05-01 2026-06-03
      python scripts/etf_price_volume.py 512880 2026-01-01 2026-06-03

依赖: pip install plotly
"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sqlite3
from datetime import datetime
from collections import OrderedDict

try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False


def get_etf_data(etf_code, start_date, end_date):
    """从数据库获取指定日期范围的ETF份额和价格数据"""
    db_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'data', 'etf_data.db'
    )
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute('''
        SELECT d.stat_date, d.tot_vol, d.close_price, i.sec_name, i.full_name
        FROM etf_daily_share d
        JOIN etf_info i ON d.sec_code = i.sec_code
        WHERE d.sec_code = ? AND d.stat_date BETWEEN ? AND ?
        ORDER BY d.stat_date
    ''', (etf_code, start_date, end_date))

    rows = cur.fetchall()
    conn.close()

    if not rows:
        return None, None, OrderedDict()

    sec_name = rows[0][3]
    full_name = rows[0][4]

    data = OrderedDict()
    for row in rows:
        data[row[0]] = {
            'tot_vol': float(row[1]),
            'close_price': float(row[2]) if row[2] else None,
        }

    return sec_name, full_name, data


def print_comparison_table(etf_code, sec_name, data):
    """打印逐日对比表"""
    if not data:
        print("无数据")
        return

    dates = list(data.keys())
    base_vol = data[dates[0]]['tot_vol']
    base_price = data[dates[0]]['close_price']
    prev_vol = None
    prev_price = None

    # 表头
    print(f"\n{'='*105}")
    print(f"  {sec_name} ({etf_code})  逐日份额-价格对比")
    print(f"{'='*105}")
    print(f"{'日期':<12} {'份额(万份)':>14} {'日变化':>12} {'累计变化':>12} {'价格':>8} {'日收益':>8} {'累计收益':>9}")
    print(f"{'-'*105}")

    for d in dates:
        v = data[d]['tot_vol']
        p = data[d]['close_price']

        # 份额日变化
        if prev_vol is not None and v != prev_vol:
            daily_chg = v - prev_vol
            chg_str = f"{daily_chg:>+12,.0f}"
        else:
            chg_str = "           ·"

        # 份额累计变化
        cum_chg = v - base_vol
        cum_str = f"{cum_chg:>+12,.0f}"

        # 价格日收益
        if prev_price and p and prev_price:
            daily_ret = (p - prev_price) / prev_price * 100
            ret_str = f"{daily_ret:>+7.2f}%"
        else:
            ret_str = "      ·"

        # 价格累计收益
        if p and base_price:
            cum_ret = (p - base_price) / base_price * 100
            cum_ret_str = f"{cum_ret:>+8.2f}%"
        else:
            cum_ret_str = "       ·"

        print(f"{d:<12} {v:>14,.0f} {chg_str} {cum_str} {p:>8.3f} {ret_str} {cum_ret_str}")

        prev_vol = v
        prev_price = p

    # 汇总
    print(f"{'-'*105}")
    final_vol = data[dates[-1]]['tot_vol']
    final_price = data[dates[-1]]['close_price']
    vol_change = final_vol - base_vol
    price_change = (final_price - base_price) / base_price * 100 if base_price else 0
    print(f"  区间: {dates[0]} → {dates[-1]}  |  "
          f"份额变化: {vol_change:+,.0f}万 ({vol_change/base_vol*100:+.2f}%)  |  "
          f"价格变化: {price_change:+.2f}%")
    print(f"{'='*105}\n")


def generate_html(etf_code, sec_name, full_name, data, output_path):
    """生成双折线图HTML (Plotly版)"""
    if not HAS_PLOTLY:
        print("错误: 需要安装 plotly，请运行: pip install plotly")
        return None

    if not data:
        print("无数据，跳过HTML生成")
        return None

    dates = list(data.keys())
    volumes = [data[d]['tot_vol'] for d in dates]
    prices = [data[d]['close_price'] for d in dates]

    # 份额变化量
    vol_changes = [0]
    for i in range(1, len(dates)):
        if volumes[i] != volumes[i-1]:
            vol_changes.append(volumes[i] - volumes[i-1])
        else:
            vol_changes.append(0)

    # 统计
    vol_change_pct = (volumes[-1] - volumes[0]) / volumes[0] * 100 if volumes[0] else 0
    price_change_pct = (prices[-1] - prices[0]) / prices[0] * 100 if prices and prices[0] else 0
    valid_prices = [p for p in prices if p]
    max_price = max(valid_prices) if valid_prices else 0
    min_price = min(valid_prices) if valid_prices else 0

    # 格式化标签的函数
    def fmt_yi(v):
        return f'{v/10000:.2f}亿'

    # ── 用 make_subplots 创建双行布局 ──
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.08,
        row_heights=[0.7, 0.3],
        specs=[[{"secondary_y": True}], [{"secondary_y": False}]],
    )

    # ── 行1: 份额面积线(左Y) + 价格折线(右Y) ──
    fig.add_trace(
        go.Scatter(
            x=dates, y=volumes,
            name='份额',
            mode='lines+markers',
            line=dict(color='#00d4ff', width=2),
            marker=dict(size=4, color='#00d4ff'),
            fill='tozeroy',
            fillcolor='rgba(0, 212, 255, 0.15)',
            hovertemplate='<b>%{{x}}</b><br>份额: %{{customdata:.2f}}亿<extra></extra>',
            customdata=[v / 10000 for v in volumes],
        ),
        row=1, col=1, secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=dates, y=prices,
            name='价格',
            mode='lines+markers',
            line=dict(color='#ff6b6b', width=2.5),
            marker=dict(size=5, symbol='diamond', color='#ff6b6b'),
            hovertemplate='<b>%{{x}}</b><br>价格: %{{y:.3f}}<extra></extra>',
        ),
        row=1, col=1, secondary_y=True,
    )

    # ── 行2: 份额变化柱状图 ──
    bar_colors = ['#00d4ff' if v >= 0 else '#ff4757' for v in vol_changes]
    fig.add_trace(
        go.Bar(
            x=dates, y=vol_changes,
            name='份额变化',
            marker_color=bar_colors,
            hovertemplate='<b>%{{x}}</b><br>份额变化: %{{y:+,.0f}}万<extra></extra>',
        ),
        row=2, col=1,
    )

    # ── 布局 & 暗色主题 ──
    title_text = f'{sec_name} ({etf_code})<br><span style="font-size:13px;color:#888">{full_name} | {dates[0]} ~ {dates[-1]} | {len(dates)}个交易日</span>'

    fig.update_layout(
        template='plotly_dark',
        title=dict(text=title_text, x=0.5, font=dict(size=20)),
        height=750,
        hovermode='x unified',
        legend=dict(
            orientation='h', y=1.08, x=0.5, xanchor='center',
            font=dict(size=12),
        ),
        margin=dict(l=60, r=60, t=100, b=40),
    )

    # ── 行1 Y轴 ──
    fig.update_yaxes(
        title_text='份额 (亿)',
        title_font=dict(color='#00d4ff', size=12),
        tickfont=dict(color='#00d4ff'),
        tickformat=',.0f',
        gridcolor='rgba(255,255,255,0.08)',
        zeroline=False,
        row=1, col=1, secondary_y=False,
    )
    fig.update_yaxes(
        title_text='价格 (元)',
        title_font=dict(color='#ff6b6b', size=12),
        tickfont=dict(color='#ff6b6b'),
        tickformat='.3f',
        zeroline=False,
        row=1, col=1, secondary_y=True,
    )

    # ── 行2 Y轴 ──
    fig.update_yaxes(
        title_text='变化 (万份)',
        title_font=dict(color='#888', size=11),
        tickfont=dict(color='#888'),
        tickformat=',.0f',
        gridcolor='rgba(255,255,255,0.05)',
        zeroline=True,
        zerolinecolor='rgba(255,255,255,0.2)',
        row=2, col=1,
    )

    # ── X轴 ──
    fig.update_xaxes(
        tickformat='%m-%d',
        tickangle=-45,
        gridcolor='rgba(255,255,255,0.06)',
        row=2, col=1,
    )

    # ── 添加注释：统计卡片 ──
    annotations = [
        dict(
            x=0.02, y=1.08, xref='paper', yref='paper',
            text=(
                f'<b>最新份额</b><br>'
                f'<span style="color:#00d4ff;font-size:16px">{volumes[-1]/10000:.2f}亿</span><br>'
                f'<span style="color:#888;font-size:10px">{dates[-1]}</span>'
            ),
            showarrow=False, align='left',
            bordercolor='rgba(255,255,255,0.1)', borderwidth=1, borderpad=10,
            bgcolor='rgba(255,255,255,0.05)',
        ),
        dict(
            x=0.16, y=1.08, xref='paper', yref='paper',
            text=(
                f'<b>份额变化</b><br>'
                f'<span style="color:{"#00d4ff" if vol_change_pct >= 0 else "#ff4757"};font-size:16px">{vol_change_pct:+.2f}%</span><br>'
                f'<span style="color:#888;font-size:10px">{volumes[-1]-volumes[0]:+,.0f}万份</span>'
            ),
            showarrow=False, align='left',
            bordercolor='rgba(255,255,255,0.1)', borderwidth=1, borderpad=10,
            bgcolor='rgba(255,255,255,0.05)',
        ),
        dict(
            x=0.30, y=1.08, xref='paper', yref='paper',
            text=(
                f'<b>最新价格</b><br>'
                f'<span style="color:#ff6b6b;font-size:16px">{prices[-1]:.3f}</span><br>'
                f'<span style="color:#888;font-size:10px">{dates[-1]}</span>'
            ),
            showarrow=False, align='left',
            bordercolor='rgba(255,255,255,0.1)', borderwidth=1, borderpad=10,
            bgcolor='rgba(255,255,255,0.05)',
        ),
        dict(
            x=0.44, y=1.08, xref='paper', yref='paper',
            text=(
                f'<b>价格变化</b><br>'
                f'<span style="color:{"#00d4ff" if price_change_pct >= 0 else "#ff4757"};font-size:16px">{price_change_pct:+.2f}%</span><br>'
                f'<span style="color:#888;font-size:10px">{prices[0]:.3f} → {prices[-1]:.3f}</span>'
            ),
            showarrow=False, align='left',
            bordercolor='rgba(255,255,255,0.1)', borderwidth=1, borderpad=10,
            bgcolor='rgba(255,255,255,0.05)',
        ),
        dict(
            x=0.58, y=1.08, xref='paper', yref='paper',
            text=(
                f'<b>份额区间</b><br>'
                f'<span style="color:#00d4ff;font-size:16px">{min(volumes)/10000:.2f}~{max(volumes)/10000:.2f}亿</span><br>'
                f'<span style="color:#888;font-size:10px">振幅: {(max(volumes)-min(volumes))/10000:.2f}亿</span>'
            ),
            showarrow=False, align='left',
            bordercolor='rgba(255,255,255,0.1)', borderwidth=1, borderpad=10,
            bgcolor='rgba(255,255,255,0.05)',
        ),
        dict(
            x=0.72, y=1.08, xref='paper', yref='paper',
            text=(
                f'<b>价格区间</b><br>'
                f'<span style="color:#ff6b6b;font-size:16px">{min_price:.3f}~{max_price:.3f}</span><br>'
                f'<span style="color:#888;font-size:10px">振幅: {max_price-min_price:.3f}</span>'
            ),
            showarrow=False, align='left',
            bordercolor='rgba(255,255,255,0.1)', borderwidth=1, borderpad=10,
            bgcolor='rgba(255,255,255,0.05)',
        ),
    ]
    fig.update_layout(annotations=annotations)

    # ── 范围滑块 ──
    fig.update_xaxes(
        rangeslider=dict(visible=True, thickness=0.05, bgcolor='rgba(0,0,0,0.3)'),
        row=1, col=1,
    )

    fig.write_html(output_path, include_plotlyjs='cdn')
    print(f"HTML已保存: {output_path}")
    return output_path


if __name__ == '__main__':
    PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    etf_code = sys.argv[1] if len(sys.argv) > 1 else '513180'
    start_date = sys.argv[2] if len(sys.argv) > 2 else '2026-05-01'
    end_date = sys.argv[3] if len(sys.argv) > 3 else '2026-06-03'

    print(f"查询 {etf_code}  {start_date} ~ {end_date} ...")
    sec_name, full_name, data = get_etf_data(etf_code, start_date, end_date)

    if not data:
        print(f"未找到 {etf_code} 在 {start_date}~{end_date} 的数据")
        print("提示: 运行 python -m src.etf.cli fetch 先拉取数据")
        sys.exit(1)

    # 1. 控制台打印逐日对比表
    print_comparison_table(etf_code, sec_name, data)

    # 2. 生成双折线图HTML (Plotly)
    if not HAS_PLOTLY:
        print("\n⚠ 未安装 plotly，跳过HTML生成。安装方法: pip install plotly\n")
    else:
        output_path = os.path.join(PROJECT_DIR, 'data', f'etf_{etf_code}_price_vol.html')
        generate_html(etf_code, sec_name, full_name, data, output_path)
