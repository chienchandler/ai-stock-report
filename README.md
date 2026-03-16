<p align="center">
  <h1 align="center">AI Stock Report</h1>
  <p align="center">
    <strong>散户也能有自己的 AI 研究员</strong><br>
    每天自动分析你的 A 股持仓，生成专业报告发送到邮箱
  </p>
  <p align="center">
    <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License"></a>
    <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.10+-blue.svg" alt="Python"></a>
    <a href="https://github.com/chienchandler/ai-stock-report/stargazers"><img src="https://img.shields.io/github/stars/chienchandler/ai-stock-report.svg?style=social" alt="Stars"></a>
  </p>
  <p align="center">
    <a href="README_EN.md">English</a> | 中文
  </p>
</p>

---

机构有研究员团队、有 Wind 终端、有实时数据流。散户呢？只能靠自己一只只翻。

**AI Stock Report** 就是你的私人 AI 研究员 —— 每天自动综合 K 线走势、技术指标、新闻资讯、估值数据，对你关注的每只股票给出评分和分析要点，生成一份报告发到你的邮箱。

上班路上打开邮件，几分钟看完所有持仓。

> **开源、免费、数据全在本地。** 你的股票代码、API Key 等个人信息全部保存在你自己的电脑上，不经过任何第三方服务器。代码完全公开，随时可审查。

> **免责声明：** AI 分析结果仅供参考，不构成任何投资建议。评分用"偏乐观""偏谨慎"表述，而非"看多""看空"。最终买卖决策，由你自己做主。

## 报告长什么样？

每天到了你设定的时间，系统自动运行分析，生成 HTML 格式的报告邮件，手机上打开就能看：

| 评分概览 | 逐只分析 |
|:---:|:---:|
| 一眼看清哪些偏乐观、哪些偏谨慎 | 每只股票一张卡片：评分 + 分析 + 风险提示 |

<!-- 如果有报告截图，取消注释下面这行 -->
<!-- <p align="center"><img src="docs/screenshot.png" width="300"></p> -->

**报告包含三个部分：**
- **评分概览** — 乐观 / 中性 / 谨慎数量统计，一目了然
- **重点关注** — 评分波动较大的股票高亮提示，帮你快速聚焦
- **逐只分析** — 每只股票的评分（-5 到 +5）、详细分析和潜在风险

## 它做了什么？不只是涨跌播报

**不是简单的价格提醒。** 它会综合多个维度做分析：

| 维度 | 数据来源 |
|------|---------|
| K 线走势 & 技术指标 | MA 均线、RSI、量能变化 |
| 估值水平 | PE / PB 等 |
| 最新新闻 | 东方财富 + 雪球（免费），Brave / Tavily（可选） |
| 资金动向 | 北向资金、板块轮动 |

所有数据汇总后交给大模型做综合判断，给出评分和分析要点。

**费用极低：** 分析 50 只股票，每天仅需约 ￥0.5（DeepSeek API）。新闻数据默认使用免费接口，零额外费用。

## 快速开始

准备两样东西（3 分钟搞定）：

1. **大模型 API Key**（~1 分钟）— 打开 [platform.deepseek.com](https://platform.deepseek.com)，注册并创建 API Key。新用户有免费额度，充 10 块能用很久。
2. **邮箱授权码**（~2 分钟）— 以 QQ 邮箱为例：网页版 → 设置 → 账户 → POP3/SMTP 服务 → 开启并生成授权码。

> 嫌邮箱配置麻烦？可选「快速体验」模式 — 用项目内置的公共邮箱发送，只需填收件地址。

---

### 方式一：AI 助手一键安装（最潮）

把下面这段话发给 **OpenClaw / Claude / ChatGPT** 等 AI 助手，它会帮你自动完成全部安装和配置：

> 帮我安装配置「A股持仓AI分析报告」（GitHub: https://github.com/chienchandler/ai-stock-report ），这是一个每天自动用AI分析A股持仓并发邮件报告的开源工具。请克隆项目、安装依赖、帮我完成配置并测试运行。

把股票代码、API Key、邮箱信息告诉 AI 助手，剩下的它来搞定。

**用 AI 配置 AI 工具，给你的 AI 助手找到第一份正经工作。**

---

### 方式二：双击启动，浏览器填表（零代码）

**适合 Windows 用户，不需要写任何代码。**

1. 安装 [Python 3.10+](https://www.python.org/downloads/)（勾选 "Add Python to PATH"）
2. [下载项目 ZIP](../../archive/refs/heads/main.zip) 并解压
3. 双击 `start.bat`（Mac/Linux 运行 `./start.sh`）
4. 浏览器自动打开配置页面，像填表单一样填写信息
5. 点击「保存配置并启动」— 搞定！

保持命令行窗口不关，每天到设定时间就能收到邮件报告。

---

### 方式三：命令行（面向开发者）

```bash
git clone https://github.com/chienchandler/ai-stock-report.git
cd ai-stock-report
pip install -r requirements.txt
python app.py            # 启动定时服务（首次自动打开配置页）
```

更多命令：

```bash
python app.py --now          # 立即运行一次分析
python app.py --setup        # 重新打开配置页面
python app.py --date 2026-03-14  # 分析指定日期
```

`--quick-config` 支持 JSON 一键配置，详见 [AGENT_SETUP.md](AGENT_SETUP.md)。

## 配置说明

### 必填项

| 配置项 | 说明 |
|--------|------|
| `stocks` | 关注的股票代码（6 位数字，如 600519） |
| `llm.api_key` | 大模型 API 密钥 |
| `email` | 邮箱地址 + SMTP 配置 |
| `report_time` | 报告发送时间（如 `07:00`） |

### 可选项

| 配置项 | 说明 |
|--------|------|
| `search.brave_api_key` | Brave Search API — 更多新闻来源 |
| `search.tavily_api_key` | Tavily API — AI 搜索摘要 |
| `custom_prompt` | 自定义分析指令（如偏好价值投资 / 技术面） |

### 推荐的 LLM

| 服务商 | 推荐理由 | 参考价格 |
|--------|----------|----------|
| **DeepSeek**（推荐） | 便宜、中文好、理解 A 股 | ￥1 / 百万 token |
| OpenRouter | 聚合多模型，可切换 | 按模型计费 |
| 硅基流动 | 国内访问快 | ￥1 / 百万 token |

## 技术架构

```
定时触发 → 获取行情数据 → 搜索新闻 → 计算技术指标 → LLM 综合分析 → 生成 HTML 报告 → 邮件发送
```

几个值得一提的设计：

- **多源数据容错** — 主数据源失败自动切备用源，带重试和超时保护
- **断点续传** — 分析到一半中断？重启自动从断点继续
- **API 限速退避** — 遇到 429 自动等待重试，长时间运行稳定可靠
- **零依赖配置界面** — 基于 Python 内置 `http.server`，不需要安装额外框架

### 项目结构

```
ai-stock-report/
├── app.py                # 主入口：定时调度 + CLI
├── web_config.py         # Web 配置界面
├── setup_wizard.py       # 命令行配置向导（备用）
├── start.bat / start.sh  # 一键启动
├── config.bat / config.sh # 一键修改配置
├── config.yaml.example   # 配置文件模板
├── requirements.txt      # Python 依赖
└── core/
    ├── data_provider.py    # 行情数据（AkShare + 新浪）
    ├── search_provider.py  # 新闻搜索（Brave + Tavily + 东财）
    ├── llm_client.py       # LLM 调用（OpenAI 兼容接口）
    ├── research.py         # 研究分析引擎
    ├── report_formatter.py # HTML 报告生成
    ├── notifier.py         # 邮件发送
    └── ...
```

## 常见问题

<details>
<summary><b>需要什么技术基础？</b></summary>
不需要。安装 Python 后双击 start.bat，在浏览器里填写信息就行。
</details>

<details>
<summary><b>费用多少？</b></summary>
DeepSeek API 分析 10 只股票约 ￥0.1/天，50 只约 ￥0.5/天。新闻数据默认免费。
</details>

<details>
<summary><b>支持哪些股票？</b></summary>
A 股全部股票（沪市 + 深市 + 创业板 + 科创板）。
</details>

<details>
<summary><b>报告准确吗？</b></summary>
AI 分析仅供参考，不构成投资建议。它的价值在于帮你省去每天翻资讯的时间，把散落各处的信息汇总成一页纸。
</details>

<details>
<summary><b>怎么修改配置？</b></summary>
双击 config.bat（打开配置页面），或直接编辑 config.yaml。
</details>

<details>
<summary><b>怎么设置开机自启？</b></summary>
Windows：将 start.bat 的快捷方式放入启动文件夹（Win+R 输入 <code>shell:startup</code>）。
</details>

## Roadmap

- [ ] 接入更多免费数据源，提升分析质量
- [ ] 历史评分追踪，观察 AI 评分变化趋势
- [ ] 云端运行方案（免开电脑）
- [ ] 港股 & 美股支持

## 参与贡献

欢迎提 [Issue](https://github.com/chienchandler/ai-stock-report/issues) 和 [Pull Request](https://github.com/chienchandler/ai-stock-report/pulls)！

作为个人业余项目，精力有限，非常欢迎感兴趣的开发者一起共建。

如果觉得有用，请给项目点个 **Star** 支持一下 :)

## License

[MIT](LICENSE)
