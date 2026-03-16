"""
AI Stock Report 配置向导
交互式引导用户完成初始配置
"""
import os
import sys
import shutil

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(PROJECT_DIR, 'config.yaml')
EXAMPLE_PATH = os.path.join(PROJECT_DIR, 'config.yaml.example')


def ask(prompt, default=None, required=True):
    """交互式输入"""
    if default:
        prompt = f"{prompt} [{default}]: "
    else:
        prompt = f"{prompt}: "

    while True:
        value = input(prompt).strip()
        if not value and default:
            return default
        if not value and required:
            print("  ⚠ 此项为必填，请输入。")
            continue
        return value


def ask_choice(prompt, choices, default=None):
    """选择题"""
    for i, (label, _) in enumerate(choices, 1):
        marker = " (推荐)" if i == 1 else ""
        print(f"  {i}. {label}{marker}")
    while True:
        value = ask(prompt, default=str(default or 1))
        try:
            idx = int(value)
            if 1 <= idx <= len(choices):
                return choices[idx - 1][1]
        except ValueError:
            pass
        print(f"  ⚠ 请输入 1-{len(choices)} 之间的数字")


def main():
    print()
    print("=" * 50)
    print("  AI Stock Report 配置向导")
    print("  跟着步骤填写，几分钟即可完成配置")
    print("=" * 50)
    print()

    if os.path.exists(CONFIG_PATH):
        overwrite = ask("已存在 config.yaml，是否覆盖？(y/n)", default="n")
        if overwrite.lower() != 'y':
            print("已取消。")
            return

    # ---- 1. 股票代码 ----
    print("\n📈 第1步：输入你关注的股票代码")
    print("  输入A股6位代码，多只股票用逗号或空格分隔")
    print("  例如: 600519, 000858, 601318")
    stocks_raw = ask("股票代码")
    stock_codes = [s.strip().zfill(6) for s in stocks_raw.replace(',', ' ').replace('，', ' ').split() if s.strip()]
    if not stock_codes:
        print("❌ 未输入有效股票代码，已取消。")
        return
    print(f"  ✅ 已添加 {len(stock_codes)} 只股票: {', '.join(stock_codes)}")

    # ---- 2. LLM 配置 ----
    print("\n🤖 第2步：配置AI大模型")
    print("  选择你使用的大模型服务商：")
    provider = ask_choice("选择", [
        ("DeepSeek（推荐，便宜好用）", "deepseek"),
        ("OpenRouter（聚合平台）", "openrouter"),
        ("硅基流动 SiliconFlow", "siliconflow"),
        ("通义千问", "qwen"),
        ("其他（自定义）", "custom"),
    ])

    provider_defaults = {
        'deepseek': ('https://api.deepseek.com/v1', 'deepseek-chat'),
        'openrouter': ('https://openrouter.ai/api/v1', 'deepseek/deepseek-chat'),
        'siliconflow': ('https://api.siliconflow.cn/v1', 'deepseek-ai/DeepSeek-V3'),
        'qwen': ('https://dashscope.aliyuncs.com/compatible-mode/v1', 'qwen-plus'),
        'custom': ('', ''),
    }
    base_url, model = provider_defaults.get(provider, ('', ''))

    if provider == 'custom':
        base_url = ask("API Base URL")
        model = ask("模型名称")
    else:
        print(f"  API地址: {base_url}")
        print(f"  模型: {model}")

    api_key = ask("API Key（输入后不会显示）")

    # ---- 3. 邮箱配置 ----
    print("\n📧 第3步：配置邮箱")
    print("  选择你的发件邮箱类型：")
    email_provider = ask_choice("选择", [
        ("QQ邮箱", "qq"),
        ("163邮箱", "163"),
        ("Gmail", "gmail"),
        ("其他", "custom"),
    ])

    email_defaults = {
        'qq': ('smtp.qq.com', 465, True),
        '163': ('smtp.163.com', 465, True),
        'gmail': ('smtp.gmail.com', 587, False),
        'custom': ('', 465, True),
    }
    smtp_host, smtp_port, use_ssl = email_defaults.get(email_provider, ('', 465, True))

    if email_provider == 'custom':
        smtp_host = ask("SMTP服务器地址")
        smtp_port = int(ask("SMTP端口", default="465"))
        use_ssl = ask("使用SSL？(y/n)", default="y").lower() == 'y'

    smtp_user = ask("发件邮箱地址")
    print("  💡 提示：授权码不是登录密码！")
    if email_provider == 'qq':
        print("     QQ邮箱：设置 → 账户 → POP3/SMTP → 开启 → 获取授权码")
    elif email_provider == '163':
        print("     163邮箱：设置 → POP3/SMTP/IMAP → 开启 → 设置授权码")
    elif email_provider == 'gmail':
        print("     Gmail：开启两步验证 → 应用专用密码")
    smtp_password = ask("邮箱授权码")

    to_email = ask("接收报告的邮箱", default=smtp_user)

    # ---- 4. 报告时间 ----
    print("\n⏰ 第4步：设置报告发送时间")
    report_time = ask("每天几点发送报告（HH:MM格式）", default="07:00")

    # ---- 5. 可选：搜索API ----
    print("\n🔍 第5步：搜索API配置（可选，直接回车跳过）")
    print("  填写后能获取更多网络新闻，不填也能用东财免费新闻")
    brave_key = ask("Brave Search API Key（免费申请，可选）", required=False) or ""
    tavily_key = ask("Tavily API Key（可选）", required=False) or ""

    # ---- 6. 可选：自定义提示词 ----
    print("\n✍️ 第6步：自定义分析指令（可选，直接回车跳过）")
    print("  例如：重点关注技术面分析、偏好价值投资、关注AI产业链等")
    custom_prompt = ask("自定义指令", required=False) or ""

    # ---- 生成配置文件 ----
    stocks_yaml = "\n".join(f'  - "{c}"' for c in stock_codes)

    config_content = f'''# AI Stock Report 配置文件（由配置向导生成）

stocks:
{stocks_yaml}

email:
  to: "{to_email}"
  smtp_host: "{smtp_host}"
  smtp_port: {smtp_port}
  smtp_user: "{smtp_user}"
  smtp_password: "{smtp_password}"
  use_ssl: {"true" if use_ssl else "false"}

report_time: "{report_time}"

llm:
  api_key: "{api_key}"
  base_url: "{base_url}"
  model: "{model}"
  temperature: 0.7
  timeout: 120
  max_retries: 3

search:
  brave_api_key: "{brave_key}"
  tavily_api_key: "{tavily_key}"
  max_results: 5

custom_prompt: "{custom_prompt}"

data:
  history_days: 30

research_workers: 3
'''

    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        f.write(config_content)

    print()
    print("=" * 50)
    print("  ✅ 配置完成！")
    print("=" * 50)
    print(f"\n  配置文件已保存到: {CONFIG_PATH}")
    print(f"\n  启动方式:")
    print(f"    python app.py          定时服务（每天 {report_time} 发送）")
    print(f"    python app.py --now    立即运行一次")
    print(f"\n  Windows用户也可以双击 start.bat 启动\n")


if __name__ == '__main__':
    main()
