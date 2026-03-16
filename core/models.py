from dataclasses import dataclass, field, asdict


@dataclass
class StockInfo:
    code: str
    name: str

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, d):
        return cls(code=d['code'], name=d['name'])


@dataclass
class StockScore:
    date: str
    stock_code: str
    stock_name: str
    score: float  # -5.00 ~ +5.00
    summary: str
    raw_llm_response: str = ""

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, d):
        return cls(**{k: d[k] for k in cls.__dataclass_fields__ if k in d})


@dataclass
class ResearchReport:
    date: str
    scores: list  # list of StockScore
    run_timestamp: str
    model_used: str
    errors: list

    def to_dict(self):
        return {
            'date': self.date,
            'scores': [s.to_dict() if hasattr(s, 'to_dict') else s for s in self.scores],
            'run_timestamp': self.run_timestamp,
            'model_used': self.model_used,
            'errors': self.errors,
        }

    @classmethod
    def from_dict(cls, d):
        scores = [StockScore.from_dict(s) for s in d.get('scores', [])]
        return cls(
            date=d['date'], scores=scores,
            run_timestamp=d.get('run_timestamp', ''),
            model_used=d.get('model_used', ''),
            errors=d.get('errors', []),
        )
