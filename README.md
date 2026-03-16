# A股持仓AI分析报告

每天自动分析你关注的A股股票，AI生成分析报告发送到邮箱。

**散户的AI分析助手** — 输入股票代码和邮箱，每天定时收到AI分析报告，帮你节省信息搜集时间。

> 你的股票代码、API Key 等个人信息全部保存在本地电脑，不会上传到任何服务器。
> AI分析结果仅供参考，AI可能出错，请自主判断，不构成投资建议。

## 功能特点

- **AI深度分析** — 大模型综合K线、新闻、技术指标、估值，给出评分和分析观点
- **邮件推送** — 每天定时发送HTML格式报告，手机端阅读友好
- **多源新闻** — Brave Search + Tavily + 东财免费新闻，信息全面
- **技术指标** — MA均线、RSI、量能趋势，零额外API调用
- **稳定可靠** — 断点续传、自动重试、异常邮件通知
- **费用极低** — DeepSeek API 分析50只股票约￥0.5，可用免费搜索
- **零门槛配置** — 浏览器填表单即可完成配置，不需要任何代码知识

## 快速开始

### Windows 用户（最简单）

1. 安装 [Python 3.10+](https://www.python.org/downloads/)（安装时勾选 "Add Python to PATH"）
2. 下载本项目（[点击下载ZIP](../../archive/refs/heads/main.zip)）
3. 解压后双击 `start.bat`
4. 浏览器自动打开配置页面，填写信息后保存
5. 完成！每天自动收报告

### Mac / Linux 用户

```bash
# 1. 克隆项目
git clone https://github.com/ChandlerChien/ai-stock-report.git
cd ai-stock-report

# 2. 一键启动（自动安装依赖 + 打开浏览器配置）
chmod +x start.sh
./start.sh
```

或手动启动：

```bash
pip install -r requirements.txt
python app.py
```

### 配置页面截图

首次启动会自动打开浏览器配置页面：

```
+----------------------------------+
|     AI Stock Report 配置          |
|                                  |
|  1. 关注的股票                    |
|     [600519, 000858          ]   |
|                                  |
|  2. AI大模型                      |
|     [DeepSeek] [OpenRouter]      |
|     API Key: [sk-...         ]   |
|                                  |
|  3. 邮箱配置                      |
|     [QQ邮箱] [163] [Gmail]       |
|     发件邮箱: [xxx@qq.com    ]   |
|     授权码:   [************  ]   |
|                                  |
|  4. 报告时间                      |
|     [07:00                   ]   |
|                                  |
|  [      保存配置并启动      ]     |
+----------------------------------+
```

## 配置说明

### 必填项（4个）

| 配置项 | 说明 |
|--------|------|
| `stocks` | 关注的股票代码列表（6位数字） |
| `email` | 邮箱配置（收件地址 + SMTP） |
| `report_time` | 报告发送时间（如 `07:00`） |
| `llm.api_key` | 大模型API密钥 |

### 可选项

| 配置项 | 说明 |
|--------|------|
| `search.brave_api_key` | Brave Search API（更多新闻来源） |
| `search.tavily_api_key` | Tavily API（AI搜索摘要） |
| `custom_prompt` | 自定义分析指令（偏好价值投资/技术面等） |

### 推荐的LLM选择

| 服务商 | 推荐理由 | 参考价格 |
|--------|----------|----------|
| **DeepSeek**（推荐） | 便宜、中文好、支持A股 | ￥1/百万token |
| OpenRouter | 聚合多模型可切换 | 按模型计费 |
| 硅基流动 | 国内访问快 | ￥1/百万token |

## 使用方式

```bash
python app.py                # 启动定时服务（首次自动打开配置页）
python app.py --now          # 立即运行一次分析
python app.py --setup        # 重新打开配置页面
python app.py --date 2026-03-14  # 分析指定日期
```

Windows 用户也可以直接双击 `start.bat`。

## AI助手一键配置

不想手动填表？把下面这段话发给 **OpenClaw / Claude / ChatGPT** 等 AI 助手，让它帮你自动完成安装和配置。

**复制以下内容，替换 `[...]` 中的信息后发送：**

> 帮我安装配置「A股持仓AI分析报告」（GitHub: https://github.com/ChandlerChien/ai-stock-report ），这是一个每天自动用AI分析A股持仓并发邮件报告的开源工具。请执行以下步骤：
>
> 1. 克隆项目并安装依赖：
> ```
> git clone https://github.com/ChandlerChien/ai-stock-report.git
> cd ai-stock-report
> pip install -r requirements.txt
> ```
>
> 2. 配置（替换方括号中的内容）：
> ```
> python app.py --quick-config '{"stocks":"[600519,000858]","api_key":"[sk-你的DeepSeek密钥]","email":"[你的邮箱@qq.com]","smtp_password":"[你的邮箱授权码]"}'
> ```
>
> 3. 测试运行：`python app.py --now`
>
> DeepSeek API Key 在 platform.deepseek.com 注册获取；QQ邮箱授权码在邮箱设置→账户→POP3/SMTP服务中生成。

`--quick-config` 支持的完整参数见 [AGENT_SETUP.md](AGENT_SETUP.md)。

## 邮件报告示例

报告包含：
- **评分概览** — 乐观/中性/谨慎数量统计
- **重点关注** — 评分波动较大的股票高亮提示
- **逐只分析** — 每只股票的评分、评分条、分析观点

## 常见问题

**Q: 需要什么技术基础？**
A: 不需要。安装Python后双击 `start.bat`，在浏览器里填写信息就行。

**Q: 费用多少？**
A: DeepSeek API 分析10只股票约 ￥0.1/天，50只约 ￥0.5/天。搜索API可选免费方案。

**Q: 支持哪些股票？**
A: A股全部股票（上海+深圳+创业板+科创板）。

**Q: 报告准确吗？**
A: AI分析仅供参考，不构成投资建议。帮你节省信息搜集时间，最终决策请自行判断。

**Q: 怎么修改配置？**
A: 双击 `config.bat`（打开配置页面），或直接编辑 `config.yaml`。

**Q: 怎么设置开机自启？**
A: Windows：将 `start.bat` 的快捷方式放入启动文件夹（Win+R 输入 `shell:startup`）。

## 项目结构

```
ai-stock-report/
├── app.py              # 主入口：定时调度 + CLI
├── web_config.py       # Web 配置界面（浏览器填表单）
├── setup_wizard.py     # 命令行配置向导（备用）
├── start.bat           # Windows 一键启动
├── config.bat          # Windows 一键修改配置
├── start.sh            # Mac/Linux 一键启动
├── config.sh           # Mac/Linux 一键修改配置
├── config.yaml.example # 配置文件模板
├── requirements.txt    # Python 依赖
└── core/
    ├── config.py       # 配置加载
    ├── models.py       # 数据模型
    ├── data_provider.py  # 行情数据（AkShare + 新浪）
    ├── search_provider.py # 新闻搜索（Brave + Tavily + 东财）
    ├── llm_client.py   # LLM 调用（OpenAI 兼容接口）
    ├── prompts.py      # 分析提示词
    ├── research.py     # 研究分析引擎
    ├── report_formatter.py # HTML/文本报告生成
    ├── notifier.py     # 邮件发送
    └── storage.py      # 数据持久化
```

## License

MIT License
