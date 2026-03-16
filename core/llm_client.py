import json
import re
import time
import logging
from openai import OpenAI
from core.config import get_config

logger = logging.getLogger(__name__)

_client = None


def _get_client():
    global _client
    if _client is not None:
        return _client

    config = get_config()
    api_key = config.get('llm_api_key', '')
    if not api_key:
        raise ValueError(
            "LLM API Key 未设置。请在 config.yaml 的 llm.api_key 中填写，"
            "或设置环境变量 LLM_API_KEY。"
        )

    llm_cfg = config.get('llm', {})
    base_url = llm_cfg.get('base_url', 'https://api.deepseek.com/v1')
    timeout = llm_cfg.get('timeout', 120)

    _client = OpenAI(
        base_url=base_url,
        api_key=api_key,
        timeout=timeout,
    )
    return _client


def reset_client():
    """Reset cached client (e.g. after config change)."""
    global _client
    _client = None


def chat(messages, model=None, temperature=None):
    """Call LLM and return response text."""
    config = get_config()
    llm_cfg = config.get('llm', {})
    model = model or llm_cfg.get('model', 'deepseek-chat')
    temperature = temperature if temperature is not None else llm_cfg.get('temperature', 0.7)
    max_retries = llm_cfg.get('max_retries', 3)

    client = _get_client()

    for attempt in range(max_retries):
        try:
            completion = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
            )
            return completion.choices[0].message.content
        except Exception as e:
            logger.warning(f"LLM调用失败 (尝试 {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
            else:
                raise


def parse_json_response(content):
    """Extract JSON from LLM response."""
    if not content:
        logger.error("LLM响应内容为空")
        return None

    # Strip <think>...</think> blocks
    content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()

    # Direct parse
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass

    # Markdown code block
    if '```json' in content:
        try:
            start = content.index('```json') + 7
            end = content.index('```', start)
            return json.loads(content[start:end].strip())
        except (json.JSONDecodeError, ValueError):
            pass

    if '```' in content:
        try:
            start = content.index('```') + 3
            newline = content.index('\n', start)
            start = newline + 1
            end = content.index('```', start)
            return json.loads(content[start:end].strip())
        except (json.JSONDecodeError, ValueError):
            pass

    # Find JSON boundaries
    start = content.find('{')
    end = content.rfind('}')
    if start != -1 and end != -1:
        try:
            return json.loads(content[start:end + 1])
        except json.JSONDecodeError:
            pass

    logger.error(f"无法从LLM响应中解析JSON: {content[:200]}...")
    return None
