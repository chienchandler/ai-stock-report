import os
import json
import logging
from core.config import get_data_dir
from core.models import ResearchReport

logger = logging.getLogger(__name__)


def _ensure_dir(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)


def _write_json(path, data):
    _ensure_dir(path)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    logger.info(f"已保存: {path}")


def _read_json(path):
    if not os.path.exists(path):
        return None
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_research_report(report: ResearchReport):
    data_dir = get_data_dir()
    path = os.path.join(data_dir, 'research', f'{report.date}.json')
    _write_json(path, report.to_dict())


def load_research_report(date_str):
    data_dir = get_data_dir()
    path = os.path.join(data_dir, 'research', f'{date_str}.json')
    data = _read_json(path)
    if data is None:
        return None
    return ResearchReport.from_dict(data)
