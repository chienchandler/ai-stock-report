"""
AI Stock Report - 主入口
每日定时分析你关注的股票，发送报告到邮箱

使用方式：
    python app.py                  # 启动定时服务
    python app.py --now            # 立即运行一次
    python app.py --date 2026-03-14  # 指定分析日期
"""
import argparse
import logging
import os
import sys
import time
import schedule
from datetime import datetime

# Windows 控制台中文输出修复
try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except (AttributeError, OSError):
    pass

# 确保项目根目录在 sys.path 中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.config import get_config
from core.data_provider import resolve_stock_names_batch, get_last_trading_day, is_trading_day, clear_caches
from core.research import run_research
from core.storage import save_research_report
from core.report_formatter import format_report_html, format_report_text
from core.notifier import send_email

logger = logging.getLogger('ai_stock_report')


def setup_logging():
    """配置日志"""
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
    os.makedirs(log_dir, exist_ok=True)

    log_file = os.path.join(log_dir, f'{datetime.now().strftime("%Y-%m-%d")}.log')

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout),
        ],
    )


def validate_config(config):
    """启动时校验配置"""
    errors = []

    # 检查股票列表
    stocks = config.get('stocks', [])
    if not stocks:
        errors.append("未配置股票代码（stocks 为空）")
    for code in stocks:
        code_str = str(code).zfill(6)
        if not code_str.isdigit() or len(code_str) != 6:
            errors.append(f"股票代码格式错误: {code}（应为6位数字）")

    # 检查邮件
    email_cfg = config.get('email', {})
    if not email_cfg.get('to'):
        errors.append("未配置收件邮箱（email.to）")
    if not email_cfg.get('smtp_host'):
        errors.append("未配置SMTP服务器（email.smtp_host）")
    if not email_cfg.get('smtp_user'):
        errors.append("未配置发件邮箱（email.smtp_user）")
    if not email_cfg.get('smtp_password'):
        errors.append("未配置邮箱授权码（email.smtp_password）")

    # 检查LLM
    api_key = config.get('llm_api_key', '')
    if not api_key:
        errors.append("未配置LLM API Key（llm.api_key）")

    # 检查报告时间
    report_time_raw = config.get('report_time', '')
    if not report_time_raw:
        errors.append("未配置报告时间（report_time）")
    else:
        report_times = report_time_raw if isinstance(report_time_raw, list) else [str(report_time_raw)]
        for rt in report_times:
            try:
                parts = rt.strip().split(':')
                h, m = int(parts[0]), int(parts[1])
                if not (0 <= h <= 23 and 0 <= m <= 59):
                    raise ValueError
            except (ValueError, IndexError):
                errors.append(f"报告时间格式错误: {rt}（应为 HH:MM，如 07:00）")

    if errors:
        print("\n❌ 配置校验失败：")
        for e in errors:
            print(f"  • {e}")
        print("\n请运行 python app.py --setup 打开配置页面修改。")
        print("也可以直接编辑 config.yaml 文件。")
        sys.exit(1)

    times_display = ', '.join(report_times) if isinstance(report_time_raw, list) else str(report_time_raw)
    print(f"✅ 配置校验通过 | {len(stocks)} 只股票 | 报告时间 {times_display}")


def run_analysis(config, date_str=None):
    """执行一次完整的分析+发送流程"""
    if date_str is None:
        date_str = get_last_trading_day()
    if not date_str:
        date_str = datetime.now().strftime('%Y-%m-%d')

    logger.info(f"=== 开始分析 === 日期: {date_str}")

    # 清除上次运行的数据缓存
    clear_caches()

    # 解析股票代码 → StockInfo
    stock_codes = [str(c).zfill(6) for c in config.get('stocks', [])]
    stock_map = resolve_stock_names_batch(stock_codes)
    stocks = [stock_map[c] for c in stock_codes if c in stock_map]

    if not stocks:
        logger.error("没有有效的股票可供分析")
        return

    logger.info(f"分析标的: {', '.join(f'{s.name}({s.code})' for s in stocks)}")

    try:
        # 执行研究
        report = run_research(stocks, date_str, config)

        # 保存报告
        save_research_report(report)

        # 生成邮件
        html = format_report_html(report)
        text = format_report_text(report)
        subject = f"A股持仓AI分析报告 {date_str} | {len(report.scores)}只股票"

        # 发送
        success = send_email(subject, html, text)
        if success:
            logger.info(f"✅ 报告已发送 | {len(report.scores)} 只成功, {len(report.errors)} 只失败")
        else:
            logger.error("❌ 邮件发送失败")

    except Exception as e:
        logger.exception(f"分析过程异常: {e}")
        # 尝试发送错误通知
        try:
            error_html = f'''<html><body>
            <h2>⚠ AI Stock Report 运行异常</h2>
            <p>日期: {date_str}</p>
            <p>错误: {str(e)}</p>
            <p>请检查日志文件了解详情。</p>
            </body></html>'''
            send_email(f"⚠ AI Stock Report 运行异常 {date_str}", error_html)
        except Exception:
            pass


def run_scheduler(config):
    """启动定时调度"""
    report_time_raw = config.get('report_time', '07:00')
    if isinstance(report_time_raw, list):
        report_times = report_time_raw
    else:
        report_times = [str(report_time_raw)]

    def scheduled_job():
        today = datetime.now().strftime('%Y-%m-%d')
        # 非交易日：仅在尚无报告时补发（避免周末重复发送）
        if not is_trading_day(today):
            last_td = get_last_trading_day(before_date=today)
            if last_td:
                from core.storage import load_research_report
                existing = load_research_report(last_td)
                if existing:
                    logger.info(f"非交易日（{today}），{last_td} 的报告已存在，跳过")
                    return
                logger.info(f"今日非交易日，补发最近交易日报告: {last_td}")
                run_analysis(config, date_str=last_td)
            else:
                logger.info(f"今日非交易日（{today}），跳过分析")
            return
        run_analysis(config)

    for t in report_times:
        schedule.every().day.at(t.strip()).do(scheduled_job)

    times_str = '、'.join(report_times)
    print(f"\n🚀 AI Stock Report 已启动")
    print(f"   报告时间: 每天 {times_str}")
    print(f"   股票数量: {len(config.get('stocks', []))} 只")
    print(f"   收件邮箱: {config.get('email', {}).get('to', 'N/A')}")
    print(f"\n   ⚠ 请不要关闭此窗口！关闭后将无法定时发送报告。")
    print(f"   修改配置请双击 config.bat 或运行 python app.py --setup")
    print(f"   按 Ctrl+C 停止服务\n")

    while True:
        try:
            schedule.run_pending()
            time.sleep(30)
        except KeyboardInterrupt:
            print("\n👋 服务已停止")
            break


def _handle_quick_config(json_str):
    """处理 --quick-config 参数，供AI助手（OpenClaw等）自动化配置"""
    import json as _json
    try:
        data = _json.loads(json_str)
    except _json.JSONDecodeError as e:
        print(f"❌ JSON 解析失败: {e}")
        sys.exit(1)

    # 必填字段校验
    required = {
        'stocks': '股票代码列表（如 "600519,000858"）',
        'api_key': 'LLM API Key',
        'email': '收件邮箱地址',
    }
    missing = [f"{desc}" for key, desc in required.items() if not data.get(key)]
    if missing:
        print(f"❌ 缺少必填字段: {', '.join(missing)}")
        print(f'格式: python app.py --quick-config \'{{\"stocks\":\"600519,000858\",\"api_key\":\"sk-...\",\"email\":\"you@qq.com\",\"smtp_password\":\"授权码\"}}\'')
        sys.exit(1)

    # 解析股票代码
    stocks_raw = data['stocks']
    if isinstance(stocks_raw, list):
        stock_codes = [str(s).strip().zfill(6) for s in stocks_raw]
    else:
        stock_codes = [s.strip().zfill(6) for s in str(stocks_raw).replace(',', ' ').replace('\uff0c', ' ').split() if s.strip()]

    # LLM 配置（有智能默认值）
    provider = data.get('provider', 'deepseek').lower()
    provider_defaults = {
        'deepseek':    {'base_url': 'https://api.deepseek.com/v1', 'model': 'deepseek-chat'},
        'openrouter':  {'base_url': 'https://openrouter.ai/api/v1', 'model': 'deepseek/deepseek-chat'},
        'siliconflow': {'base_url': 'https://api.siliconflow.cn/v1', 'model': 'deepseek-ai/DeepSeek-V3'},
    }
    defaults = provider_defaults.get(provider, provider_defaults['deepseek'])
    base_url = data.get('base_url', defaults['base_url'])
    model = data.get('model', defaults['model'])

    # 邮箱配置（智能检测邮箱类型）
    email_addr = data['email']
    smtp_password = data.get('smtp_password', '')
    smtp_user = data.get('smtp_user', email_addr)
    to_email = data.get('to_email', email_addr)

    # 根据邮箱自动推断 SMTP
    smtp_host = data.get('smtp_host', '')
    smtp_port = data.get('smtp_port', 465)
    use_ssl = data.get('use_ssl', True)
    if not smtp_host:
        if 'qq.com' in email_addr:
            smtp_host = 'smtp.qq.com'
        elif '163.com' in email_addr:
            smtp_host = 'smtp.163.com'
        elif 'gmail.com' in email_addr:
            smtp_host, smtp_port, use_ssl = 'smtp.gmail.com', 587, False
        elif '126.com' in email_addr:
            smtp_host = 'smtp.126.com'
        elif 'outlook.com' in email_addr or 'hotmail.com' in email_addr:
            smtp_host, smtp_port, use_ssl = 'smtp.office365.com', 587, False
        else:
            smtp_host = f'smtp.{email_addr.split("@")[1]}'

    report_time = data.get('report_time', '07:00')
    custom_prompt = data.get('custom_prompt', '')
    brave_key = data.get('brave_api_key', '')
    tavily_key = data.get('tavily_api_key', '')

    # 生成 config.yaml
    from web_config import _yaml_escape
    y = _yaml_escape
    stocks_yaml = '\n'.join(f'  - "{c}"' for c in stock_codes)
    use_ssl_str = 'true' if use_ssl else 'false'

    config_content = f'''# AI Stock Report 配置文件（由 AI 助手自动生成）

stocks:
{stocks_yaml}

email:
  to: "{y(to_email)}"
  smtp_host: "{y(smtp_host)}"
  smtp_port: {smtp_port}
  smtp_user: "{y(smtp_user)}"
  smtp_password: "{y(smtp_password)}"
  use_ssl: {use_ssl_str}

report_time: "{y(report_time)}"

llm:
  api_key: "{y(data['api_key'])}"
  base_url: "{y(base_url)}"
  model: "{y(model)}"
  temperature: 0.7
  timeout: 120
  max_retries: 3

search:
  brave_api_key: "{y(brave_key)}"
  tavily_api_key: "{y(tavily_key)}"
  max_results: 5

custom_prompt: "{y(custom_prompt)}"

data:
  history_days: 30

research_workers: 3
'''

    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.yaml')
    with open(config_path, 'w', encoding='utf-8') as f:
        f.write(config_content)

    print(f"✅ 配置已生成: {config_path}")
    print(f"   股票: {', '.join(stock_codes)}")
    print(f"   模型: {model} ({provider})")
    print(f"   邮箱: {to_email}")
    print(f"   报告时间: {report_time}")
    if not smtp_password:
        print(f"\n⚠ 未提供邮箱授权码（smtp_password），邮件发送功能暂不可用。")
        print(f"  请编辑 config.yaml 补充，或运行 python app.py --setup 在界面中配置。")
    print(f"\n下一步: python app.py        # 启动定时服务")
    print(f"       python app.py --now  # 立即运行一次")


def main():
    parser = argparse.ArgumentParser(
        description='AI Stock Report - AI持仓分析报告',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python app.py               启动定时服务，每天按时发送报告
  python app.py --now          立即运行一次分析并发送报告
  python app.py --date 2026-03-14  分析指定日期的数据
  python app.py --quick-config '{"stocks":"600519,000858","api_key":"sk-...","email":"you@qq.com","smtp_password":"授权码"}'
        """,
    )
    parser.add_argument('--now', action='store_true', help='立即运行一次分析')
    parser.add_argument('--date', type=str, help='指定分析日期（YYYY-MM-DD）')
    parser.add_argument('--config', type=str, help='指定配置文件路径')
    parser.add_argument('--setup', action='store_true', help='打开Web配置页面')
    parser.add_argument('--quick-config', type=str, metavar='JSON',
                        help='快速配置（JSON格式），供AI助手自动化调用')

    args = parser.parse_args()

    setup_logging()

    # --setup 模式：打开 Web 配置页面
    if args.setup:
        from web_config import run_config_server
        run_config_server(open_browser=True, wait_for_save=False)
        return

    # --quick-config 模式：AI助手自动化配置
    if args.quick_config:
        _handle_quick_config(args.quick_config)
        return

    # 加载配置（如果配置不存在，自动打开 Web 配置向导）
    config_path = args.config or os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.yaml')
    if not os.path.exists(config_path):
        print('\n📋 未检测到配置文件，启动 Web 配置向导...')
        from web_config import run_config_server
        saved = run_config_server(open_browser=True, wait_for_save=True)
        if not saved:
            sys.exit(1)

    try:
        config = get_config(args.config)
    except FileNotFoundError as e:
        print(f"\n❌ {e}")
        sys.exit(1)

    validate_config(config)

    if args.now or args.date:
        run_analysis(config, date_str=args.date)
    else:
        run_scheduler(config)


if __name__ == '__main__':
    main()
