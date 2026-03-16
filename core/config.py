import os
import yaml

_config = None


def get_config(config_path=None):
    global _config
    if _config is not None and config_path is None:
        return _config

    if config_path is None:
        config_path = os.path.join(os.path.dirname(__file__), '..', 'config.yaml')

    if not os.path.exists(config_path):
        raise FileNotFoundError(
            f"配置文件不存在: {config_path}\n"
            "请运行 python setup_wizard.py 生成配置，或复制 config.yaml.example 为 config.yaml 后手动填写。"
        )

    with open(config_path, 'r', encoding='utf-8') as f:
        _config = yaml.safe_load(f)

    # Set project root
    _config['project_root'] = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

    # Resolve API keys: config.yaml value > env var
    _config['llm_api_key'] = _config.get('llm', {}).get('api_key', '') or os.getenv('LLM_API_KEY', '')
    _config['brave_search_api_key'] = (
        _config.get('search', {}).get('brave_api_key', '') or os.getenv('BRAVE_SEARCH_API_KEY', '')
    )
    _config['tavily_api_key'] = (
        _config.get('search', {}).get('tavily_api_key', '') or os.getenv('TAVILY_API_KEY', '')
    )

    return _config


def get_data_dir():
    config = get_config()
    return os.path.join(config['project_root'], 'data')
