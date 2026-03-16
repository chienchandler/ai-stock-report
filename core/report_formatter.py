"""
HTML邮件报告格式化模块
将研究报告转换为美观的HTML邮件，适配手机端阅读
"""
from core.models import ResearchReport


def _score_color(score):
    """根据评分返回颜色"""
    if score >= 3.0:
        return '#c0392b'  # 深红（强烈看多）
    elif score >= 1.5:
        return '#e74c3c'  # 红色（看多）
    elif score >= 0.5:
        return '#e67e22'  # 橙色（偏多）
    elif score > -0.5:
        return '#7f8c8d'  # 灰色（中性）
    elif score > -1.5:
        return '#27ae60'  # 绿色（偏空）
    elif score > -3.0:
        return '#2ecc71'  # 浅绿（看空）
    else:
        return '#16a085'  # 深绿（强烈看空）


def _score_label(score):
    """评分文字标签（客观中性表述）"""
    if score >= 4.0:
        return '高度乐观'
    elif score >= 2.0:
        return '偏乐观'
    elif score >= 0.5:
        return '略偏乐观'
    elif score > -0.5:
        return '中性'
    elif score > -2.0:
        return '略偏谨慎'
    elif score > -4.0:
        return '偏谨慎'
    else:
        return '高度谨慎'


def _score_bar(score):
    """生成评分条HTML（-5到+5映射到0-100%）"""
    pct = (score + 5) / 10 * 100
    color = _score_color(score)
    return f'''<div style="background:#ecf0f1;border-radius:4px;height:8px;width:100%;margin:4px 0;">
        <div style="background:{color};border-radius:4px;height:8px;width:{pct:.0f}%;"></div>
    </div>'''


def format_report_html(report: ResearchReport) -> str:
    """将研究报告格式化为HTML邮件"""
    date_str = report.date
    scores = sorted(report.scores, key=lambda s: s.score, reverse=True)
    n_total = len(scores)

    # 统计摘要（以 ±2 为分界线，客观表述）
    optimistic = sum(1 for s in scores if s.score >= 2.0)
    cautious = sum(1 for s in scores if s.score <= -2.0)
    neutral = n_total - optimistic - cautious

    # 评分波动较大的股票（|score| >= 2.0）
    attention_stocks = [s for s in scores if abs(s.score) >= 2.0]

    # 构建HTML
    stocks_html = ""
    for s in scores:
        color = _score_color(s.score)
        label = _score_label(s.score)
        bar = _score_bar(s.score)
        stocks_html += f'''
        <div style="background:#fff;border-radius:8px;padding:12px 16px;margin:8px 0;border-left:4px solid {color};box-shadow:0 1px 3px rgba(0,0,0,0.08);">
            <div style="display:flex;justify-content:space-between;align-items:center;">
                <div style="font-weight:600;font-size:15px;color:#2c3e50;">{s.stock_name}
                    <span style="color:#95a5a6;font-weight:400;font-size:13px;">({s.stock_code})</span>
                </div>
                <div style="font-size:18px;font-weight:700;color:{color};">{s.score:+.2f}
                    <span style="font-size:11px;font-weight:400;">{label}</span>
                </div>
            </div>
            {bar}
            <div style="color:#555;font-size:13px;line-height:1.5;margin-top:6px;">{s.summary}</div>
        </div>'''

    # 评分波动较大，建议关注
    attention_html = ""
    if attention_stocks:
        attention_items = ""
        for s in attention_stocks:
            marker = "+" if s.score > 0 else ""
            attention_items += f'<li style="margin:4px 0;font-size:14px;"><strong>{s.stock_name}</strong>（{marker}{s.score:.2f}）: {s.summary[:60]}</li>'
        attention_html = f'''
        <div style="background:#fef9e7;border-radius:8px;padding:14px 16px;margin:12px 0;border:1px solid #f9e79f;">
            <div style="font-weight:600;font-size:15px;color:#d68910;margin-bottom:8px;">以下标的评分波动较大，建议关注</div>
            <ul style="margin:0;padding-left:20px;">{attention_items}</ul>
        </div>'''

    # 错误提示
    error_html = ""
    if report.errors:
        error_list = "".join(f"<li>{e}</li>" for e in report.errors[:5])
        error_html = f'''
        <div style="background:#fdedec;border-radius:8px;padding:12px 16px;margin:12px 0;border:1px solid #f5b7b1;">
            <div style="font-weight:600;color:#e74c3c;margin-bottom:4px;">⚠ 分析异常</div>
            <ul style="margin:0;padding-left:20px;font-size:13px;color:#922b21;">{error_list}</ul>
        </div>'''

    html = f'''<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#f5f6fa;margin:0;padding:0;">
<div style="max-width:600px;margin:0 auto;padding:16px;">

    <!-- 标题 -->
    <div style="text-align:center;padding:20px 0 10px;">
        <div style="font-size:22px;font-weight:700;color:#2c3e50;">A股持仓AI分析报告</div>
        <div style="font-size:14px;color:#7f8c8d;margin-top:4px;">{date_str}</div>
    </div>

    <!-- 概览 -->
    <div style="display:flex;justify-content:space-around;background:#fff;border-radius:8px;padding:14px;margin:12px 0;box-shadow:0 1px 3px rgba(0,0,0,0.08);">
        <div style="text-align:center;">
            <div style="font-size:24px;font-weight:700;color:#e74c3c;">{optimistic}</div>
            <div style="font-size:12px;color:#95a5a6;">乐观(&gt;2)</div>
        </div>
        <div style="text-align:center;">
            <div style="font-size:24px;font-weight:700;color:#7f8c8d;">{neutral}</div>
            <div style="font-size:12px;color:#95a5a6;">中性</div>
        </div>
        <div style="text-align:center;">
            <div style="font-size:24px;font-weight:700;color:#27ae60;">{cautious}</div>
            <div style="font-size:12px;color:#95a5a6;">谨慎(&lt;-2)</div>
        </div>
        <div style="text-align:center;">
            <div style="font-size:24px;font-weight:700;color:#2c3e50;">{n_total}</div>
            <div style="font-size:12px;color:#95a5a6;">总计</div>
        </div>
    </div>

    {attention_html}
    {error_html}

    <!-- 详细分析 -->
    <div style="font-size:16px;font-weight:600;color:#2c3e50;margin:16px 0 8px;">详细分析</div>
    {stocks_html}

    <!-- 页脚 -->
    <div style="text-align:center;padding:20px 0;font-size:12px;color:#bdc3c7;border-top:1px solid #ecf0f1;margin-top:16px;">
        A股持仓AI分析报告 · 评分范围 -5 至 +5，仅代表AI模型分析结果<br>
        不构成任何投资建议，请结合自身判断 · 模型: {report.model_used}
    </div>

</div>
</body>
</html>'''

    return html


def format_report_text(report: ResearchReport) -> str:
    """纯文本格式报告（HTML不支持时的fallback）"""
    lines = [
        f"=== A股持仓AI分析报告 ===",
        f"日期: {report.date}",
        f"分析股票: {len(report.scores)} 只",
        "",
    ]

    scores = sorted(report.scores, key=lambda s: s.score, reverse=True)

    # 评分波动较大，建议关注
    attention = [s for s in scores if abs(s.score) >= 2.0]
    if attention:
        lines.append("【评分波动较大，建议关注】")
        for s in attention:
            lines.append(f"  {s.stock_name}({s.stock_code}) {s.score:+.2f}: {s.summary[:60]}")
        lines.append("")

    lines.append("【全部评分】")
    for s in scores:
        lines.append(f"  {s.stock_name}({s.stock_code}) {s.score:+.2f} | {s.summary[:50]}")

    if report.errors:
        lines.append("")
        lines.append("【分析异常】")
        for e in report.errors[:5]:
            lines.append(f"  - {e}")

    lines.extend([
        "",
        f"模型: {report.model_used}",
        "评分范围 -5 至 +5，仅代表AI分析结果，不构成任何投资建议。",
    ])

    return "\n".join(lines)
