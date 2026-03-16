# AI助手一键配置指南

你可以把下面的提示词发给 OpenClaw、Claude、ChatGPT 等 AI 助手，让它帮你自动完成配置。

## 使用方式

1. 复制下面引用框中的内容
2. **修改其中的个人信息**（股票代码、API Key、邮箱、授权码）
3. 发给你的 AI 助手

---

## 提示词模板

> 帮我配置「A股持仓AI分析报告」，一个开源的AI股票分析工具。
>
> 项目已下载到我的电脑，路径是：`[你的项目路径，例如 C:\ai-stock-report]`
>
> 请帮我执行以下命令完成配置：
>
> ```
> cd [项目路径]
> pip install -r requirements.txt
> python app.py --quick-config '{"stocks":"600519,000858","api_key":"sk-你的API密钥","email":"你的邮箱@qq.com","smtp_password":"你的邮箱授权码","report_time":"07:00"}'
> ```
>
> 说明：
> - stocks：我关注的A股代码，逗号分隔
> - api_key：我的 DeepSeek API Key（在 platform.deepseek.com 获取）
> - email：我接收报告的邮箱
> - smtp_password：邮箱授权码（QQ邮箱在设置→账户→POP3/SMTP服务中获取）
> - report_time：每天收报告的时间
>
> 配置完成后，运行 `python app.py` 启动定时服务，或 `python app.py --now` 立即测试一次。

---

## 可选参数

在 JSON 中还可以添加：

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `provider` | 服务商：`deepseek`/`openrouter`/`siliconflow` | `deepseek` |
| `model` | 模型名称 | 按服务商自动选择 |
| `smtp_user` | 发件邮箱（如果和收件不同） | 同 email |
| `to_email` | 收件邮箱（如果和发件不同） | 同 email |
| `custom_prompt` | 自定义分析指令 | 空 |
| `brave_api_key` | Brave Search API Key | 空 |
| `tavily_api_key` | Tavily API Key | 空 |

## 完整示例

使用 OpenRouter + 自定义分析风格：

```
python app.py --quick-config '{"stocks":"600519,000858,601318","api_key":"sk-or-xxx","provider":"openrouter","email":"test@163.com","smtp_password":"ABCDEF","report_time":"18:00","custom_prompt":"重点关注技术面和量价关系"}'
```
