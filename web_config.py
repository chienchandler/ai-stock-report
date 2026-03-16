"""
AI Stock Report Web 配置界面
基于 Python 内置 http.server，零额外依赖
浏览器中填写表单 → 自动生成 config.yaml
"""
import json
import os
import smtplib
import socket
import sys
import threading
import time
import webbrowser
from email.mime.text import MIMEText
from html import escape as _esc
from http.server import HTTPServer, BaseHTTPRequestHandler

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except (AttributeError, OSError):
    pass

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(PROJECT_DIR, 'config.yaml')

# ============================================================
# 项目公共邮箱配置（项目维护者填写，用户可"快速体验"）
# 也可通过 project_smtp.yaml 文件配置
# ============================================================
PROJECT_SMTP = {
    'smtp_host': '',
    'smtp_user': '',
    'smtp_password': '',
    'smtp_port': 465,
    'use_ssl': True,
}


def _json_dumps_safe(obj):
    return json.dumps(obj, ensure_ascii=False)


def _load_project_smtp():
    """加载项目公共邮箱配置"""
    # 优先从文件加载
    path = os.path.join(PROJECT_DIR, 'project_smtp.yaml')
    if os.path.exists(path):
        try:
            import yaml
            with open(path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f) or {}
            if data.get('smtp_host') and data.get('smtp_user') and data.get('smtp_password'):
                return data
        except Exception:
            pass
    # 回退到代码中的常量
    if PROJECT_SMTP.get('smtp_host') and PROJECT_SMTP.get('smtp_user'):
        return PROJECT_SMTP
    return None


# ============================================================
# HTML 模板
# ============================================================

HTML_PAGE = r'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>A股持仓AI分析报告</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "PingFang SC", "Microsoft YaHei", sans-serif;
    background: #f0f2f5; color: #1a1a2e; min-height: 100vh;
  }
  .container { max-width: 640px; margin: 0 auto; padding: 24px 16px 60px; }
  .header { text-align: center; padding: 32px 0 8px; }
  .header h1 { font-size: 26px; font-weight: 700; color: #1a1a2e; }
  .disclaimer {
    text-align: center; font-size: 12px; color: #999; line-height: 1.8;
    margin-bottom: 20px; padding: 0 16px;
  }

  .card {
    background: #fff; border-radius: 12px; padding: 24px;
    margin-bottom: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.08);
  }
  .card-title {
    font-size: 17px; font-weight: 600; color: #1a1a2e;
    margin-bottom: 16px; display: flex; align-items: center; gap: 8px;
  }
  .card-title .num {
    background: #4361ee; color: #fff; width: 24px; height: 24px;
    border-radius: 50%; display: inline-flex; align-items: center;
    justify-content: center; font-size: 13px; flex-shrink: 0;
  }
  .sub-title {
    font-size: 14px; font-weight: 600; color: #555;
    margin: 18px 0 10px; padding-top: 10px; border-top: 1px solid #f0f0f0;
  }
  .sub-title:first-of-type { margin-top: 0; padding-top: 0; border-top: none; }

  .field { margin-bottom: 14px; }
  .field label {
    display: block; font-size: 13px; font-weight: 500; color: #444;
    margin-bottom: 4px;
  }
  .field .hint { font-size: 12px; color: #999; margin-bottom: 4px; }
  .field input, .field select, .field textarea {
    width: 100%; padding: 10px 12px; border: 1px solid #d9d9d9;
    border-radius: 8px; font-size: 14px; outline: none;
    transition: border-color 0.2s; background: #fff;
  }
  .field input:focus, .field select:focus, .field textarea:focus {
    border-color: #4361ee; box-shadow: 0 0 0 2px rgba(67,97,238,0.15);
  }
  .field textarea { resize: vertical; min-height: 60px; }
  .field .required::after { content: " *"; color: #e74c3c; }

  .row { display: flex; gap: 12px; }
  .row .field { flex: 1; }

  .btn-grid {
    display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 14px;
  }
  .btn-grid-4 { grid-template-columns: repeat(4, 1fr); }
  .sel-btn {
    padding: 10px 12px; border: 2px solid #e8e8e8; border-radius: 8px;
    background: #fff; cursor: pointer; text-align: center;
    transition: all 0.2s; font-size: 13px;
  }
  .sel-btn:hover { border-color: #4361ee; background: #f8f9ff; }
  .sel-btn.active { border-color: #4361ee; background: #eef1ff; }
  .sel-btn.disabled { opacity: 0.45; pointer-events: none; }
  .sel-btn .name { font-weight: 600; }
  .sel-btn .desc { font-size: 11px; color: #999; margin-top: 2px; }
  .sel-btn .badge {
    display: inline-block; background: #4361ee; color: #fff;
    font-size: 10px; padding: 1px 6px; border-radius: 10px; margin-left: 4px;
  }

  .submit-btn {
    width: 100%; padding: 14px; background: #4361ee; color: #fff;
    border: none; border-radius: 10px; font-size: 16px; font-weight: 600;
    cursor: pointer; transition: background 0.2s; margin-top: 8px;
  }
  .submit-btn:hover { background: #3451d1; }
  .submit-btn:disabled { background: #a0aec0; cursor: not-allowed; }

  .test-btn {
    padding: 8px 16px; background: #27ae60; color: #fff;
    border: none; border-radius: 6px; cursor: pointer;
    font-size: 13px; transition: background 0.2s;
  }
  .test-btn:hover { background: #219a52; }
  .test-btn:disabled { background: #a0aec0; cursor: not-allowed; }

  .optional-tag {
    display: inline-block; background: #f0f0f0; color: #888;
    font-size: 10px; padding: 1px 6px; border-radius: 4px;
    margin-left: 6px; font-weight: 400;
  }

  .alert {
    padding: 12px 16px; border-radius: 8px; margin-bottom: 16px;
    font-size: 13px; display: none;
  }
  .alert-success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
  .alert-error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }

  .tips {
    background: #fffbeb; border: 1px solid #fde68a; border-radius: 8px;
    padding: 12px 16px; font-size: 12px; color: #92400e; margin-bottom: 14px;
  }
  .tips b { color: #78350f; }

  .footer { text-align: center; padding: 16px; font-size: 12px; color: #999; }

  @media (max-width: 480px) {
    .btn-grid { grid-template-columns: 1fr; }
    .btn-grid-4 { grid-template-columns: 1fr 1fr; }
    .row { flex-direction: column; gap: 0; }
  }
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>A股持仓AI分析报告</h1>
  </div>
  <div class="disclaimer">
    你关注的股票、API Key 等个人信息全部保存在你的本地电脑，不会上传到任何服务器。<br>
    本项目仅为公益开源项目。AI分析结果仅供参考，AI可能出错，请自主判断。
  </div>

  <div id="alert-success" class="alert alert-success"></div>
  <div id="alert-error" class="alert alert-error"></div>

  <form id="configForm" onsubmit="return submitForm(event)">

    <!-- 1. 股票代码 -->
    <div class="card">
      <div class="card-title"><span class="num">1</span> 关注的股票</div>
      <div class="field">
        <label class="required">股票代码</label>
        <div class="hint">输入A股6位代码，多只股票用逗号、空格或换行分隔。例如：600519, 000858</div>
        <textarea id="stocks" name="stocks" rows="3" placeholder="600519, 000858, 601318" required>{{STOCKS}}</textarea>
      </div>
    </div>

    <!-- 2. LLM配置 -->
    <div class="card">
      <div class="card-title"><span class="num">2</span> AI大模型</div>

      <div class="sub-title">API 服务商</div>
      <div class="btn-grid" id="provider-grid">
        <div class="sel-btn active" onclick="selectProvider(this,'deepseek')">
          <div class="name">DeepSeek</div>
          <div class="desc">性价比高，中文优秀</div>
        </div>
        <div class="sel-btn" onclick="selectProvider(this,'openrouter')">
          <div class="name">OpenRouter</div>
          <div class="desc">聚合平台，多种模型</div>
        </div>
        <div class="sel-btn" onclick="selectProvider(this,'siliconflow')">
          <div class="name">硅基流动</div>
          <div class="desc">国内访问快速稳定</div>
        </div>
        <div class="sel-btn" onclick="selectProvider(this,'custom')">
          <div class="name">其他服务商</div>
          <div class="desc">自定义API地址和模型</div>
        </div>
      </div>

      <div class="field">
        <label class="required">API Key</label>
        <div class="hint" id="api-key-hint">在 <a href="https://platform.deepseek.com/api_keys" target="_blank">DeepSeek 控制台</a> 获取</div>
        <input type="password" id="api_key" placeholder="sk-..." required value="{{API_KEY}}">
      </div>

      <div id="custom-url-field" style="display:none;">
        <div class="field">
          <label class="required">API 地址 (Base URL)</label>
          <input type="text" id="base_url" placeholder="https://api.example.com/v1" value="{{BASE_URL}}">
        </div>
      </div>

      <div class="sub-title">模型选择</div>
      <div class="field">
        <label class="required">模型</label>
        <div class="hint">选择与服务商匹配的模型</div>
        <select id="model_select" onchange="onModelChange(this)"></select>
      </div>
      <div class="field" id="custom-model-field" style="display:none;">
        <label>自定义模型名称</label>
        <input type="text" id="model_custom" placeholder="model-name" value="{{MODEL_CUSTOM}}">
      </div>
    </div>

    <!-- 3. 邮箱配置 -->
    <div class="card">
      <div class="card-title"><span class="num">3</span> 邮箱配置</div>

      <div class="btn-grid" id="email-mode-grid" style="margin-bottom:14px;">
        <div class="sel-btn active" onclick="selectEmailMode(this,'self')">
          <div class="name">自主配置 <span class="badge">推荐</span></div>
          <div class="desc">使用自己的邮箱发送报告</div>
        </div>
        <div class="sel-btn {{PROJECT_EMAIL_CLASS}}" onclick="selectEmailMode(this,'project')" id="projectEmailBtn">
          <div class="name">快速体验</div>
          <div class="desc">{{PROJECT_EMAIL_DESC}}</div>
        </div>
      </div>

      <!-- 自主配置 -->
      <div id="self-email-config">
        <div class="btn-grid btn-grid-4" style="margin-bottom:14px;">
          <div class="sel-btn active" onclick="selectEmailProvider(this,'qq')">QQ邮箱</div>
          <div class="sel-btn" onclick="selectEmailProvider(this,'163')">163邮箱</div>
          <div class="sel-btn" onclick="selectEmailProvider(this,'gmail')">Gmail</div>
          <div class="sel-btn" onclick="selectEmailProvider(this,'custom')">其他</div>
        </div>

        <div id="email-tips" class="tips">
          <b>QQ邮箱获取授权码：</b>登录QQ邮箱网页版 → 设置 → 账户 → POP3/IMAP/SMTP服务 → 开启SMTP → 生成授权码
        </div>

        <div class="field">
          <label class="required">发件邮箱地址</label>
          <input type="email" id="smtp_user" placeholder="your_email@qq.com" required value="{{SMTP_USER}}">
        </div>
        <div class="field">
          <label class="required">邮箱授权码</label>
          <div class="hint">注意：是授权码，不是登录密码！</div>
          <input type="password" id="smtp_password" placeholder="授权码" required value="{{SMTP_PASSWORD}}">
        </div>
        <div class="field">
          <label>收件邮箱 <span class="optional-tag">可选</span></label>
          <div class="hint">不填则与发件邮箱相同</div>
          <input type="email" id="to_email" placeholder="留空则与发件邮箱相同" value="{{TO_EMAIL}}">
        </div>

        <div style="margin: 8px 0 14px;">
          <button type="button" class="test-btn" onclick="testEmail()" id="testEmailBtn">发送测试邮件</button>
          <span id="testEmailResult" style="margin-left:8px; font-size:13px;"></span>
        </div>

        <div id="custom-email-fields" style="display:none;">
          <div class="row">
            <div class="field">
              <label class="required">SMTP 服务器</label>
              <input type="text" id="smtp_host" placeholder="smtp.example.com" value="{{SMTP_HOST}}">
            </div>
            <div class="field" style="max-width:120px;">
              <label>端口</label>
              <input type="number" id="smtp_port" value="{{SMTP_PORT}}">
            </div>
          </div>
          <div class="field">
            <label>加密方式</label>
            <select id="use_ssl">
              <option value="true">SSL (端口465)</option>
              <option value="false">STARTTLS (端口587)</option>
            </select>
          </div>
        </div>
      </div>

      <!-- 快速体验（项目公共邮箱） -->
      <div id="project-email-config" style="display:none;">
        <div class="tips">
          使用项目公共邮箱为你发送报告，方便快速体验。<br>
          <b>推荐自主配置邮箱</b>，公共邮箱可能有发送频率限制。
        </div>
        <div class="field">
          <label class="required">你的收件邮箱</label>
          <div class="hint">分析报告将发送到此邮箱</div>
          <input type="email" id="project_to_email" placeholder="your_email@example.com">
        </div>
        <div style="margin: 8px 0 14px;">
          <button type="button" class="test-btn" onclick="testEmail()" id="testEmailBtn2">发送测试邮件</button>
          <span id="testEmailResult2" style="margin-left:8px; font-size:13px;"></span>
        </div>
      </div>
    </div>

    <!-- 4. 报告时间 -->
    <div class="card">
      <div class="card-title"><span class="num">4</span> 报告时间</div>
      <div class="field">
        <label class="required">每天发送报告的时间</label>
        <div class="hint">支持多个时间，点击「+」添加（如早盘前 + 收盘后各一次）</div>
        <div id="time-list">
          <div class="time-row" style="display:flex;gap:8px;align-items:center;margin-bottom:6px;">
            <input type="time" class="report-time-input" value="{{REPORT_TIME}}" required style="flex:1;">
            <button type="button" class="test-btn" onclick="addTimeRow()" style="padding:6px 12px;">+</button>
          </div>
        </div>
      </div>
      <div class="tips" style="margin-top:4px;">
        <b>请注意：</b>需确保该时间前后，您的电脑处于开机状态且连接网络，否则无法正常生成报告。
      </div>
    </div>

    <!-- 5. 可选配置 -->
    <div class="card">
      <div class="card-title"><span class="num">5</span> 高级配置 <span class="optional-tag">可选</span></div>
      <div class="hint" style="margin-bottom:14px; font-size:12px; color:#27ae60;">
        以下配置均为可选，不填不会产生任何费用。不填也能正常使用（默认使用东方财富免费新闻数据）。
      </div>

      <div class="field">
        <label>自定义分析指令</label>
        <div class="hint">告诉AI你的投资风格偏好，不填则使用默认的全面分析策略</div>
        <textarea id="custom_prompt" rows="2" placeholder="例如：重点关注技术面分析、偏好价值投资、关注AI产业链等">{{CUSTOM_PROMPT}}</textarea>
      </div>

      <div class="field">
        <label>Brave Search API Key</label>
        <div class="hint">更多网络新闻来源。<a href="https://brave.com/search/api/" target="_blank">免费申请</a></div>
        <input type="text" id="brave_api_key" placeholder="可选" value="{{BRAVE_KEY}}">
      </div>

      <div class="field">
        <label>Tavily API Key</label>
        <div class="hint">AI搜索摘要。<a href="https://tavily.com/" target="_blank">免费额度</a></div>
        <input type="text" id="tavily_api_key" placeholder="可选" value="{{TAVILY_KEY}}">
      </div>
    </div>

    <button type="submit" class="submit-btn" id="submitBtn">保存配置并启动</button>
  </form>

  <div class="footer">
    A股持仓AI分析报告 &middot; 公益开源 &middot; 仅供参考，不构成投资建议
  </div>
</div>

<script>
const PROVIDERS = {
  deepseek: {
    url: 'https://api.deepseek.com/v1',
    hint: '在 <a href="https://platform.deepseek.com/api_keys" target="_blank">DeepSeek 控制台</a> 获取',
    models: [
      { label: 'DeepSeek V3.2', value: 'deepseek-chat' },
      { label: 'DeepSeek R1 (推理增强)', value: 'deepseek-reasoner' },
    ],
  },
  openrouter: {
    url: 'https://openrouter.ai/api/v1',
    hint: '在 <a href="https://openrouter.ai/keys" target="_blank">OpenRouter</a> 获取',
    models: [
      { label: 'DeepSeek V3.2', value: 'deepseek/deepseek-chat' },
      { label: 'DeepSeek R1', value: 'deepseek/deepseek-r1' },
      { label: 'Qwen3 Max', value: 'qwen/qwen3-max' },
      { label: 'GPT-5', value: 'openai/gpt-5' },
    ],
  },
  siliconflow: {
    url: 'https://api.siliconflow.cn/v1',
    hint: '在 <a href="https://cloud.siliconflow.cn" target="_blank">硅基流动</a> 获取',
    models: [
      { label: 'DeepSeek V3.2', value: 'deepseek-ai/DeepSeek-V3' },
      { label: 'DeepSeek R1', value: 'deepseek-ai/DeepSeek-R1' },
      { label: 'Qwen3 Max', value: 'Qwen/Qwen3-Max' },
    ],
  },
  custom: {
    url: '',
    hint: '填写你的 API Key',
    models: [],
  },
};

const EMAIL_PROVIDERS = {
  qq:     { host: 'smtp.qq.com',    port: 465, ssl: true,  tips: '<b>QQ邮箱获取授权码：</b>登录QQ邮箱网页版 → 设置 → 账户 → POP3/IMAP/SMTP服务 → 开启SMTP → 生成授权码' },
  '163':  { host: 'smtp.163.com',   port: 465, ssl: true,  tips: '<b>163邮箱获取授权码：</b>登录网页版 → 设置 → POP3/SMTP/IMAP → 开启 → 设置授权码' },
  gmail:  { host: 'smtp.gmail.com', port: 587, ssl: false, tips: '<b>Gmail设置：</b>开启两步验证 → Google账号 → 安全性 → 应用专用密码 → 生成密码' },
  custom: { host: '',               port: 465, ssl: true,  tips: '请手动填写SMTP服务器信息' },
};

const PROJECT_EMAIL_AVAILABLE = {{PROJECT_EMAIL_AVAILABLE}};
let currentProvider = '{{CURRENT_PROVIDER}}';
let currentEmailProvider = '{{CURRENT_EMAIL_PROVIDER}}';
let currentEmailMode = 'self';

/* --- Provider & Model --- */

function selectProvider(el, key) {
  document.querySelectorAll('#provider-grid .sel-btn').forEach(b => b.classList.remove('active'));
  el.classList.add('active');
  currentProvider = key;

  const p = PROVIDERS[key];
  document.getElementById('api-key-hint').innerHTML = p.hint;
  document.getElementById('custom-url-field').style.display = key === 'custom' ? 'block' : 'none';

  // Populate model dropdown
  const sel = document.getElementById('model_select');
  sel.innerHTML = '';
  p.models.forEach(m => {
    const opt = document.createElement('option');
    opt.value = m.value; opt.textContent = m.label;
    sel.appendChild(opt);
  });
  // Add "custom" option
  const customOpt = document.createElement('option');
  customOpt.value = '__custom__';
  customOpt.textContent = key === 'custom' ? '请输入模型名称' : '其他（手动输入）';
  sel.appendChild(customOpt);

  if (key === 'custom') {
    sel.value = '__custom__';
    document.getElementById('custom-model-field').style.display = 'block';
  } else {
    document.getElementById('custom-model-field').style.display = 'none';
  }
}

function onModelChange(sel) {
  document.getElementById('custom-model-field').style.display =
    sel.value === '__custom__' ? 'block' : 'none';
}

/* --- Email Mode --- */

function selectEmailMode(el, mode) {
  if (mode === 'project' && !PROJECT_EMAIL_AVAILABLE) return;
  document.querySelectorAll('#email-mode-grid .sel-btn').forEach(b => b.classList.remove('active'));
  el.classList.add('active');
  currentEmailMode = mode;

  document.getElementById('self-email-config').style.display = mode === 'self' ? 'block' : 'none';
  document.getElementById('project-email-config').style.display = mode === 'project' ? 'block' : 'none';

  const su = document.getElementById('smtp_user');
  const sp = document.getElementById('smtp_password');
  const pt = document.getElementById('project_to_email');
  if (mode === 'project') {
    su.removeAttribute('required'); sp.removeAttribute('required');
    pt.setAttribute('required', '');
  } else {
    su.setAttribute('required', ''); sp.setAttribute('required', '');
    pt.removeAttribute('required');
  }
}

function selectEmailProvider(el, key) {
  document.querySelectorAll('#self-email-config .btn-grid .sel-btn').forEach(b => b.classList.remove('active'));
  el.classList.add('active');
  currentEmailProvider = key;

  const e = EMAIL_PROVIDERS[key];
  document.getElementById('email-tips').innerHTML = e.tips;
  document.getElementById('custom-email-fields').style.display = key === 'custom' ? 'block' : 'none';
  if (key !== 'custom') {
    document.getElementById('smtp_host').value = e.host;
    document.getElementById('smtp_port').value = e.port;
    document.getElementById('use_ssl').value = e.ssl ? 'true' : 'false';
  }
}

/* --- Report Time --- */

function addTimeRow() {
  const list = document.getElementById('time-list');
  const row = document.createElement('div');
  row.className = 'time-row';
  row.style = 'display:flex;gap:8px;align-items:center;margin-bottom:6px;';
  row.innerHTML = '<input type="time" class="report-time-input" value="18:00" style="flex:1;">' +
    '<button type="button" class="test-btn" onclick="this.parentElement.remove()" style="padding:6px 12px;background:#e74c3c;">-</button>';
  list.appendChild(row);
}

function getReportTimes() {
  const inputs = document.querySelectorAll('.report-time-input');
  const times = [];
  inputs.forEach(inp => { if (inp.value) times.push(inp.value); });
  return [...new Set(times)];
}

/* --- Helpers --- */

function showAlert(type, msg) {
  const el = document.getElementById('alert-' + type);
  el.textContent = msg; el.style.display = 'block';
  window.scrollTo({ top: 0, behavior: 'smooth' });
  document.getElementById('alert-' + (type === 'success' ? 'error' : 'success')).style.display = 'none';
}

function getFormData() {
  let modelValue;
  if (currentProvider === 'custom') {
    modelValue = document.getElementById('model_custom').value;
  } else {
    const sel = document.getElementById('model_select');
    modelValue = sel.value === '__custom__'
      ? document.getElementById('model_custom').value
      : sel.value;
  }

  const data = {
    stocks: document.getElementById('stocks').value,
    api_key: document.getElementById('api_key').value,
    llm_provider: currentProvider,
    base_url: currentProvider === 'custom'
      ? document.getElementById('base_url').value
      : PROVIDERS[currentProvider].url,
    model: modelValue,
    report_time: getReportTimes().join(','),
    custom_prompt: document.getElementById('custom_prompt').value,
    brave_api_key: document.getElementById('brave_api_key').value,
    tavily_api_key: document.getElementById('tavily_api_key').value,
    email_mode: currentEmailMode,
  };

  if (currentEmailMode === 'project') {
    data.project_to_email = document.getElementById('project_to_email').value;
  } else {
    data.smtp_user = document.getElementById('smtp_user').value;
    data.smtp_password = document.getElementById('smtp_password').value;
    data.to_email = document.getElementById('to_email').value;
    data.smtp_host = document.getElementById('smtp_host').value || EMAIL_PROVIDERS[currentEmailProvider].host;
    data.smtp_port = document.getElementById('smtp_port').value || EMAIL_PROVIDERS[currentEmailProvider].port;
    data.use_ssl = document.getElementById('use_ssl').value;
  }
  return data;
}

/* --- Test Email --- */

async function testEmail() {
  const isProject = currentEmailMode === 'project';
  const btn = document.getElementById(isProject ? 'testEmailBtn2' : 'testEmailBtn');
  const result = document.getElementById(isProject ? 'testEmailResult2' : 'testEmailResult');
  btn.disabled = true;
  result.textContent = '发送中...'; result.style.color = '#666';

  const data = getFormData();
  if (isProject && !data.project_to_email) {
    result.textContent = '请填写收件邮箱'; result.style.color = '#e74c3c';
    btn.disabled = false; return;
  }
  if (!isProject && (!data.smtp_user || !data.smtp_password)) {
    result.textContent = '请先填写发件邮箱和授权码'; result.style.color = '#e74c3c';
    btn.disabled = false; return;
  }

  try {
    const resp = await fetch('/test-email', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    const json = await resp.json();
    result.textContent = json.ok ? '测试邮件已发送，请检查收件箱' : (json.error || '发送失败');
    result.style.color = json.ok ? '#27ae60' : '#e74c3c';
  } catch (err) {
    result.textContent = '网络错误: ' + err.message;
    result.style.color = '#e74c3c';
  }
  btn.disabled = false;
}

/* --- Submit --- */

async function submitForm(e) {
  e.preventDefault();
  const btn = document.getElementById('submitBtn');
  btn.disabled = true; btn.textContent = '保存中...';

  try {
    const data = getFormData();

    // Validate stocks
    const codes = data.stocks.replace(/[,，\s]+/g, ' ').trim().split(/\s+/).filter(Boolean);
    if (!codes.length) { showAlert('error', '请至少输入一个股票代码'); btn.disabled=false; btn.textContent='保存配置并启动'; return false; }
    for (const c of codes) { if (!/^\d{1,6}$/.test(c)) { showAlert('error','股票代码格式错误: '+c); btn.disabled=false; btn.textContent='保存配置并启动'; return false; } }
    if (!data.api_key) { showAlert('error','请填写 API Key'); btn.disabled=false; btn.textContent='保存配置并启动'; return false; }
    if (!data.model) { showAlert('error','请选择或输入模型名称'); btn.disabled=false; btn.textContent='保存配置并启动'; return false; }

    if (data.email_mode === 'project') {
      if (!data.project_to_email) { showAlert('error','请填写收件邮箱'); btn.disabled=false; btn.textContent='保存配置并启动'; return false; }
    } else {
      if (!data.smtp_user) { showAlert('error','请填写发件邮箱'); btn.disabled=false; btn.textContent='保存配置并启动'; return false; }
      if (!data.smtp_password) { showAlert('error','请填写邮箱授权码'); btn.disabled=false; btn.textContent='保存配置并启动'; return false; }
    }

    const resp = await fetch('/save', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
    const result = await resp.json();
    if (result.ok) {
      showAlert('success', '配置保存成功！服务正在启动，此页面可以关闭。');
      btn.textContent = '已保存';
    } else {
      showAlert('error', result.error || '保存失败');
      btn.disabled = false; btn.textContent = '保存配置并启动';
    }
  } catch (err) {
    showAlert('error', '网络错误: ' + err.message);
    btn.disabled = false; btn.textContent = '保存配置并启动';
  }
  return false;
}

/* --- Init --- */
(function init() {
  // Provider
  const provBtns = document.querySelectorAll('#provider-grid .sel-btn');
  provBtns.forEach(btn => {
    const key = btn.getAttribute('onclick')?.match(/'(\w+)'/)?.[1];
    if (key === currentProvider) { selectProvider(btn, key); }
    else { btn.classList.remove('active'); }
  });

  // Pre-select model
  const curModel = '{{CURRENT_MODEL}}';
  if (curModel) {
    const sel = document.getElementById('model_select');
    let found = false;
    for (let i = 0; i < sel.options.length; i++) {
      if (sel.options[i].value === curModel) { sel.selectedIndex = i; found = true; break; }
    }
    if (!found && curModel !== '__custom__') {
      for (let i = 0; i < sel.options.length; i++) {
        if (sel.options[i].value === '__custom__') { sel.selectedIndex = i; break; }
      }
      document.getElementById('model_custom').value = curModel;
      document.getElementById('custom-model-field').style.display = 'block';
    }
  }

  // Email provider
  const emailBtns = document.querySelectorAll('#self-email-config .btn-grid .sel-btn');
  emailBtns.forEach(btn => {
    const key = btn.getAttribute('onclick')?.match(/'(\w+)'/)?.[1];
    if (key === currentEmailProvider) { btn.classList.add('active'); selectEmailProvider(btn, key); }
    else { btn.classList.remove('active'); }
  });

  // Extra report times
  const extraTimes = {{EXTRA_TIMES_JSON}};
  extraTimes.forEach(t => {
    const list = document.getElementById('time-list');
    const row = document.createElement('div');
    row.className = 'time-row';
    row.style = 'display:flex;gap:8px;align-items:center;margin-bottom:6px;';
    row.innerHTML = '<input type="time" class="report-time-input" value="' + t + '" style="flex:1;">' +
      '<button type="button" class="test-btn" onclick="this.parentElement.remove()" style="padding:6px 12px;background:#e74c3c;">-</button>';
    list.appendChild(row);
  });

  // Project email availability
  if (!PROJECT_EMAIL_AVAILABLE) {
    const pb = document.getElementById('projectEmailBtn');
    pb.classList.add('disabled');
    pb.querySelector('.desc').textContent = '暂未配置';
  }
})();
</script>
</body>
</html>'''


# ============================================================
# Python 逻辑
# ============================================================

def _load_existing_config():
    if not os.path.exists(CONFIG_PATH):
        return {}
    try:
        import yaml
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}


def _render_html():
    """渲染 HTML 页面，所有值经 HTML 转义"""
    config = _load_existing_config()

    stocks = config.get('stocks', [])
    stocks_str = ', '.join(str(s) for s in stocks) if stocks else ''

    llm = config.get('llm', {})
    api_key = llm.get('api_key', '')
    base_url = llm.get('base_url', '')
    model = llm.get('model', '')

    provider = 'deepseek'
    if 'openrouter' in base_url:
        provider = 'openrouter'
    elif 'siliconflow' in base_url:
        provider = 'siliconflow'
    elif base_url and 'deepseek' not in base_url:
        provider = 'custom'

    email = config.get('email', {})
    smtp_host = email.get('smtp_host', '')
    smtp_port = email.get('smtp_port', 465)
    smtp_user = email.get('smtp_user', '')
    smtp_password = email.get('smtp_password', '')
    to_email = email.get('to', '')
    if to_email == smtp_user:
        to_email = ''

    email_provider = 'qq'
    if '163' in smtp_host:
        email_provider = '163'
    elif 'gmail' in smtp_host:
        email_provider = 'gmail'
    elif smtp_host and 'qq' not in smtp_host:
        email_provider = 'custom'

    report_time_raw = config.get('report_time', '07:00')
    if isinstance(report_time_raw, list):
        report_times = report_time_raw
    else:
        report_times = [str(report_time_raw)]
    report_time = report_times[0] if report_times else '07:00'
    extra_times = report_times[1:] if len(report_times) > 1 else []
    custom_prompt = config.get('custom_prompt', '')
    brave_key = config.get('search', {}).get('brave_api_key', '')
    tavily_key = config.get('search', {}).get('tavily_api_key', '')

    # 过滤模板默认值
    defaults = {'your_api_key_here', 'your_sender@qq.com', 'your_app_password', 'your_email@example.com'}
    if api_key in defaults: api_key = ''
    if smtp_user in defaults: smtp_user = ''
    if smtp_password in defaults: smtp_password = ''
    if to_email in defaults: to_email = ''

    # 项目公共邮箱
    project_smtp = _load_project_smtp()
    project_avail = 'true' if project_smtp else 'false'
    project_class = '' if project_smtp else 'disabled'
    project_desc = '使用项目公共邮箱发送' if project_smtp else '暂未配置'

    replacements = {
        '{{STOCKS}}': _esc(stocks_str),
        '{{API_KEY}}': _esc(api_key),
        '{{BASE_URL}}': _esc(base_url),
        '{{CURRENT_PROVIDER}}': _esc(provider),
        '{{CURRENT_MODEL}}': _esc(model),
        '{{MODEL_CUSTOM}}': '',
        '{{SMTP_HOST}}': _esc(smtp_host),
        '{{SMTP_PORT}}': _esc(str(smtp_port)),
        '{{SMTP_USER}}': _esc(smtp_user),
        '{{SMTP_PASSWORD}}': _esc(smtp_password),
        '{{TO_EMAIL}}': _esc(to_email),
        '{{CURRENT_EMAIL_PROVIDER}}': _esc(email_provider),
        '{{REPORT_TIME}}': _esc(report_time),
        '{{CUSTOM_PROMPT}}': _esc(custom_prompt),
        '{{BRAVE_KEY}}': _esc(brave_key),
        '{{TAVILY_KEY}}': _esc(tavily_key),
        '{{PROJECT_EMAIL_AVAILABLE}}': project_avail,
        '{{PROJECT_EMAIL_CLASS}}': project_class,
        '{{PROJECT_EMAIL_DESC}}': project_desc,
        '{{EXTRA_TIMES_JSON}}': _json_dumps_safe(extra_times),
    }

    page = HTML_PAGE
    for k, v in replacements.items():
        page = page.replace(k, v)
    return page


def _yaml_escape(s):
    return (str(s)
            .replace('\\', '\\\\')
            .replace('"', '\\"')
            .replace('\n', '\\n')
            .replace('\r', '')
            .replace('\t', '\\t'))


def _generate_config_yaml(data):
    stocks_raw = data.get('stocks', '')
    stock_codes = [s.strip().zfill(6)
                   for s in stocks_raw.replace(',', ' ').replace('\uff0c', ' ').split()
                   if s.strip()]

    api_key = data.get('api_key', '')
    base_url = data.get('base_url', '')
    model = data.get('model', '')

    smtp_user = data.get('smtp_user', '')
    smtp_password = data.get('smtp_password', '')
    to_email = data.get('to_email', '') or smtp_user
    smtp_host = data.get('smtp_host', '')
    smtp_port = int(data.get('smtp_port', 465) or 465)
    use_ssl = data.get('use_ssl', 'true')

    report_time_raw = data.get('report_time', '07:00')
    report_times = [t.strip() for t in report_time_raw.split(',') if t.strip()]
    if not report_times:
        report_times = ['07:00']
    custom_prompt = data.get('custom_prompt', '')
    brave_key = data.get('brave_api_key', '')
    tavily_key = data.get('tavily_api_key', '')

    stocks_yaml = '\n'.join(f'  - "{c}"' for c in stock_codes)
    y = _yaml_escape

    # report_time: 单个时间用字符串，多个用列表
    if len(report_times) == 1:
        report_time_yaml = f'report_time: "{y(report_times[0])}"'
    else:
        lines = '\n'.join(f'  - "{y(t)}"' for t in report_times)
        report_time_yaml = f'report_time:\n{lines}'

    return f'''# AI Stock Report 配置文件

stocks:
{stocks_yaml}

email:
  to: "{y(to_email)}"
  smtp_host: "{y(smtp_host)}"
  smtp_port: {smtp_port}
  smtp_user: "{y(smtp_user)}"
  smtp_password: "{y(smtp_password)}"
  use_ssl: {use_ssl}

{report_time_yaml}

llm:
  api_key: "{y(api_key)}"
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


def _send_test_email(data):
    smtp_host = data.get('smtp_host', '')
    smtp_port = int(data.get('smtp_port', 465) or 465)
    smtp_user = data.get('smtp_user', '')
    smtp_password = data.get('smtp_password', '')
    to_email = data.get('to_email', '') or smtp_user
    use_ssl = str(data.get('use_ssl', 'true')).lower() == 'true'

    if not smtp_host:
        return '请选择邮箱类型或填写SMTP服务器地址'
    if not smtp_user:
        return '请填写发件邮箱地址'
    if not smtp_password:
        return '请填写邮箱授权码'

    msg = MIMEText('''<html><body>
        <div style="font-family:sans-serif;max-width:400px;margin:40px auto;text-align:center;padding:20px;">
            <h2 style="color:#27ae60;">邮箱配置成功！</h2>
            <p style="color:#333;">这是 A股持仓AI分析报告 的测试邮件。</p>
            <p style="color:#666;font-size:14px;">你将在每天设定时间收到AI分析报告。</p>
        </div>
    </body></html>''', 'html', 'utf-8')
    msg['Subject'] = 'A股持仓AI分析报告 - 测试邮件'
    msg['From'] = smtp_user
    msg['To'] = to_email

    try:
        if use_ssl:
            with smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=15) as server:
                server.login(smtp_user, smtp_password)
                server.sendmail(smtp_user, [to_email], msg.as_string())
        else:
            with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as server:
                server.starttls()
                server.login(smtp_user, smtp_password)
                server.sendmail(smtp_user, [to_email], msg.as_string())
        return True
    except smtplib.SMTPAuthenticationError:
        return '邮箱授权码错误，请检查是否使用了正确的授权码（非登录密码）'
    except smtplib.SMTPConnectError:
        return f'无法连接SMTP服务器 {smtp_host}:{smtp_port}'
    except socket.timeout:
        return '连接SMTP服务器超时，请检查网络'
    except Exception as e:
        return f'发送失败: {str(e)}'


_config_saved_event = threading.Event()


class ConfigHandler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        pass

    def do_GET(self):
        if self.path == '/' or self.path.startswith('/?'):
            page = _render_html()
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(page.encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        length = int(self.headers.get('Content-Length', 0))
        if length > 1_000_000:
            self.send_error(413, 'Request body too large')
            return
        body = self.rfile.read(length).decode('utf-8')
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            self._json(400, {'ok': False, 'error': '无效的请求数据'})
            return

        if self.path == '/save':
            self._handle_save(data)
        elif self.path == '/test-email':
            self._handle_test_email(data)
        else:
            self.send_response(404)
            self.end_headers()

    def _handle_save(self, data):
        codes = [s.strip() for s in data.get('stocks', '').replace(',', ' ').replace('\uff0c', ' ').split() if s.strip()]
        if not codes:
            self._json(400, {'ok': False, 'error': '请至少输入一个股票代码'}); return
        if not data.get('api_key'):
            self._json(400, {'ok': False, 'error': '请填写 API Key'}); return

        # 处理邮箱模式
        if data.get('email_mode') == 'project':
            ps = _load_project_smtp()
            if not ps:
                self._json(400, {'ok': False, 'error': '项目公共邮箱未配置'}); return
            data['smtp_host'] = ps['smtp_host']
            data['smtp_user'] = ps['smtp_user']
            data['smtp_password'] = ps['smtp_password']
            data['smtp_port'] = ps.get('smtp_port', 465)
            data['use_ssl'] = 'true' if ps.get('use_ssl', True) else 'false'
            data['to_email'] = data.get('project_to_email', '')
            if not data['to_email']:
                self._json(400, {'ok': False, 'error': '请填写收件邮箱'}); return
        else:
            if not data.get('smtp_user'):
                self._json(400, {'ok': False, 'error': '请填写发件邮箱'}); return
            if not data.get('smtp_password'):
                self._json(400, {'ok': False, 'error': '请填写邮箱授权码'}); return

        try:
            content = _generate_config_yaml(data)
            with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
                f.write(content)
            self._json(200, {'ok': True})
            _config_saved_event.set()
        except Exception as e:
            self._json(500, {'ok': False, 'error': f'保存失败: {e}'})

    def _handle_test_email(self, data):
        if data.get('email_mode') == 'project':
            ps = _load_project_smtp()
            if not ps:
                self._json(200, {'ok': False, 'error': '项目公共邮箱未配置'}); return
            data['smtp_host'] = ps['smtp_host']
            data['smtp_user'] = ps['smtp_user']
            data['smtp_password'] = ps['smtp_password']
            data['smtp_port'] = ps.get('smtp_port', 465)
            data['use_ssl'] = 'true' if ps.get('use_ssl', True) else 'false'
            data['to_email'] = data.get('project_to_email', '')

        result = _send_test_email(data)
        self._json(200, {'ok': True} if result is True else {'ok': False, 'error': str(result)})

    def _json(self, status, data):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))


def _find_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        return s.getsockname()[1]


def run_config_server(open_browser=True, wait_for_save=True):
    port = _find_free_port()
    server = HTTPServer(('127.0.0.1', port), ConfigHandler)
    url = f'http://127.0.0.1:{port}'

    print(f'\n  +------------------------------------------+')
    print(f'  |   A股持仓AI分析报告 - 配置向导           |')
    print(f'  |                                          |')
    print(f'  |   请在浏览器中完成配置:                  |')
    print(f'  |   {url:<40} |')
    print(f'  |                                          |')
    print(f'  |   按 Ctrl+C 退出                         |')
    print(f'  +------------------------------------------+\n')

    if open_browser:
        def _open():
            time.sleep(0.5)
            webbrowser.open(url)
        threading.Thread(target=_open, daemon=True).start()

    if wait_for_save:
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()
        try:
            while not _config_saved_event.is_set():
                _config_saved_event.wait(timeout=1)
            print('\n  配置已保存！正在启动服务...\n')
            time.sleep(1)
            server.shutdown()
            return True
        except KeyboardInterrupt:
            print('\n  已取消配置。')
            server.shutdown()
            return False
    else:
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        server.shutdown()
        return _config_saved_event.is_set()


if __name__ == '__main__':
    saved = run_config_server()
    if saved:
        print('配置已保存到 config.yaml')
    sys.exit(0 if saved else 1)
