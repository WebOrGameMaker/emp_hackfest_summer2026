from typing import Optional

from .. import config
from ..models import AIStatus
from .demo import DemoAnalyzer

_analyzer: Optional[object] = None


def get_analyzer():
    global _analyzer
    if _analyzer is None:
        if config.AI_KEY:
            from .openai_provider import OpenAIAnalyzer
            _analyzer = OpenAIAnalyzer()
        else:
            _analyzer = DemoAnalyzer()
    return _analyzer


def get_status() -> AIStatus:
    analyzer = get_analyzer()
    is_demo = getattr(analyzer, "name", "demo") == "demo"
    if is_demo:
        return AIStatus(
            provider="demo",
            is_demo=True,
            model=None,
            note=(
                "No AI key configured, so reports use the built-in analyzer. "
                "Clustering and confidence are still real; photos use the demo scenes."
            ),
        )
    return AIStatus(
        provider="openai",
        is_demo=False,
        model=config.AI_MODEL,
        note=(
            "Reports are classified by a hosted vision and language model. "
            "If that fails, the built-in analyzer is used instead."
        ),
    )
