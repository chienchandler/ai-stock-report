<p align="center">
  <h1 align="center">AI Stock Report</h1>
  <p align="center">
    <strong>Your Personal AI Stock Analyst</strong><br>
    Automated daily analysis of your China A-share portfolio, delivered to your inbox
  </p>
  <p align="center">
    <a href="LICENSE"><img src="https://img.shields.io/badge/license-Apache%202.0-blue.svg" alt="License"></a>
    <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.10+-blue.svg" alt="Python"></a>
    <a href="https://github.com/chienchandler/ai-stock-report/stargazers"><img src="https://img.shields.io/github/stars/chienchandler/ai-stock-report.svg?style=social" alt="Stars"></a>
  </p>
  <p align="center">
    English | <a href="README.md">中文</a>
  </p>
</p>

---

Institutional investors have research teams, Bloomberg terminals, and real-time data feeds. Retail investors? We're on our own, scrolling through news one stock at a time.

**AI Stock Report** is your personal AI research analyst — it automatically analyzes your watchlist every day by combining price action, technical indicators, news, and valuation data, then delivers a scored report straight to your inbox.

Check your email on the morning commute, and you're caught up on all your holdings in minutes.

> **Open source, free, data stays local.** Your stock codes, API keys, and email credentials are stored entirely on your own machine. No third-party servers. Full source code available for audit.

> **Disclaimer:** AI analysis is for informational purposes only and does not constitute investment advice. Scores use "leaning bullish" / "leaning cautious" language, not "buy" / "sell". All investment decisions are yours alone.

## What Does the Report Look Like?

At your scheduled time each day, the system runs its analysis and sends an HTML email report — mobile-friendly, readable at a glance:

- **Score Overview** — Quick count of bullish / neutral / cautious ratings
- **Watch List** — Stocks with significant score changes are highlighted
- **Per-Stock Analysis** — Each stock gets a card with score (-5 to +5), analysis, and risk notes

## What Does It Actually Do?

**This isn't a simple price alert.** It synthesizes multiple dimensions:

| Dimension | Data Sources |
|-----------|-------------|
| Price Action & Technicals | Moving averages, RSI, volume trends |
| Valuation | PE / PB ratios |
| News | Eastmoney + Xueqiu (free), Brave / Tavily (optional) |
| Capital Flow | Northbound capital, sector rotation |

All data is fed to an LLM for comprehensive analysis, producing a score and key takeaways for each stock.

**Ultra-low cost:** Analyzing 50 stocks costs ~¥0.5/day (~$0.07) with DeepSeek API. News data uses free sources by default.

## Quick Start

You'll need two things (~3 minutes):

1. **LLM API Key** (~1 min) — Sign up at [platform.deepseek.com](https://platform.deepseek.com) and create an API key. New users get free credits.
2. **Email SMTP credentials** (~2 min) — Enable SMTP in your email provider's settings and generate an app password.

---

### Option 1: AI Assistant Setup (Easiest)

Copy this prompt to **OpenClaw / Claude / ChatGPT** or any AI coding assistant, and it will handle the entire installation:

> Help me install and configure "AI Stock Report" (GitHub: https://github.com/chienchandler/ai-stock-report), an open-source tool that uses AI to analyze China A-share holdings daily and sends email reports. Please clone the project, install dependencies, help me configure it, and run a test.

Tell the AI assistant your stock codes, API key, and email info — it handles the rest.

---

### Option 2: One-Click Start (No Coding)

**For Windows users — zero code required.**

1. Install [Python 3.10+](https://www.python.org/downloads/) (check "Add Python to PATH")
2. [Download ZIP](../../archive/refs/heads/main.zip) and extract
3. Double-click `start.bat` (Mac: double-click `start.command`, Linux: run `./start.sh`)
4. Browser opens automatically — fill in the config form
5. Click "Save & Start" — done!

Keep the terminal window open. Reports arrive at your scheduled time.

---

### Option 3: Command Line (For Developers)

```bash
git clone https://github.com/chienchandler/ai-stock-report.git
cd ai-stock-report
pip install -r requirements.txt
python app.py            # Start scheduler (opens config on first run)
```

More commands:

```bash
python app.py --now          # Run analysis immediately
python app.py --setup        # Re-open config page
python app.py --date 2026-03-14  # Analyze a specific date
```

See [AGENT_SETUP.md](AGENT_SETUP.md) for `--quick-config` JSON options.

## Configuration

### Required

| Setting | Description |
|---------|-------------|
| `stocks` | Stock codes to watch (6-digit, e.g. 600519) |
| `llm.api_key` | LLM API key |
| `email` | Email address + SMTP config |
| `report_time` | Daily report time (e.g. `07:00`) |

### Optional

| Setting | Description |
|---------|-------------|
| `search.brave_api_key` | Brave Search API — additional news sources |
| `search.tavily_api_key` | Tavily API — AI-powered search summaries |
| `custom_prompt` | Custom analysis instructions (e.g. focus on value investing) |

### Recommended LLMs

| Provider | Why | Price |
|----------|-----|-------|
| **DeepSeek** (recommended) | Affordable, strong Chinese language, understands A-shares | ¥1 / 1M tokens |
| OpenRouter | Multi-model aggregator | Varies by model |
| SiliconFlow | Fast access from mainland China | ¥1 / 1M tokens |

## Architecture

```
Scheduler → Fetch market data → Search news → Calculate indicators → LLM analysis → Generate HTML → Send email
```

Key design decisions:

- **Multi-source failover** — Primary data source fails? Auto-switches to backup with retry and timeout protection
- **Resume from checkpoint** — Interrupted mid-analysis? Restart picks up where it left off
- **Rate limit backoff** — Auto-waits and retries on 429 errors for long-running stability
- **Zero-dependency config UI** — Built on Python's built-in `http.server`, no extra frameworks needed

### Project Structure

```
ai-stock-report/
├── app.py                # Entry point: scheduler + CLI
├── web_config.py         # Web config UI
├── setup_wizard.py       # CLI config wizard (backup)
├── start.bat / start.sh  # One-click start
├── config.bat / config.sh # One-click config edit
├── config.yaml.example   # Config template
├── requirements.txt      # Python dependencies
└── core/
    ├── data_provider.py    # Market data (AkShare + Sina)
    ├── search_provider.py  # News search (Brave + Tavily + Eastmoney)
    ├── llm_client.py       # LLM calls (OpenAI-compatible)
    ├── research.py         # Research & analysis engine
    ├── report_formatter.py # HTML report generation
    ├── notifier.py         # Email delivery
    └── ...
```

## FAQ

<details>
<summary><b>Do I need programming experience?</b></summary>
No. Install Python, double-click start.bat, and fill in a web form. That's it.
</details>

<details>
<summary><b>How much does it cost?</b></summary>
DeepSeek API: ~¥0.1/day for 10 stocks, ~¥0.5/day for 50 stocks (~$0.07). News data is free by default.
</details>

<details>
<summary><b>Which stocks are supported?</b></summary>
All China A-share stocks (Shanghai, Shenzhen, ChiNext, STAR Market).
</details>

<details>
<summary><b>How accurate are the reports?</b></summary>
AI analysis is for reference only — not investment advice. Its value is saving you the time of manually checking news across multiple sources every day.
</details>

<details>
<summary><b>How do I change settings later?</b></summary>
Double-click config.bat to reopen the config page, or edit config.yaml directly.
</details>

<details>
<summary><b>Can it run on startup?</b></summary>
Windows: Place a shortcut to start.bat in your Startup folder (Win+R → <code>shell:startup</code>).
</details>

## Roadmap

- [ ] More free data sources for better analysis quality
- [ ] Historical score tracking to observe AI score trends
- [ ] Cloud deployment option (no need to keep PC on)
- [ ] Hong Kong & US stock market support

## Contributing

[Issues](https://github.com/chienchandler/ai-stock-report/issues) and [Pull Requests](https://github.com/chienchandler/ai-stock-report/pulls) are welcome!

This is a side project with limited bandwidth — contributions from the community are especially appreciated.

If you find this useful, please consider giving the project a **Star** :)

## License

[Apache License 2.0](LICENSE)
