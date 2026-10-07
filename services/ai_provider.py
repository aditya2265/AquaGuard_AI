"""
AI provider abstraction for AquaGuard.

Default: LocalAIProvider (rule-based, no external calls).
When IBM_API_KEY / IBM_PROJECT_ID / IBM_URL env vars are all present,
get_ai_provider() returns IBMWatsonxProvider instead.
"""
import os
from abc import ABC, abstractmethod


class AIProvider(ABC):
    @abstractmethod
    def generate_explanation(self, factors: dict, risk_level: str) -> str:
        """Return a human-readable risk explanation."""

    @abstractmethod
    def generate_recommendations(self, factors: dict, risk_level: str, region_name: str) -> list:
        """Return a list of recommendation dicts."""


class LocalAIProvider(AIProvider):
    """
    Rule-based provider — no external API calls.
    Delegates to risk_engine and recommendation_service.
    """

    def generate_explanation(self, factors: dict, risk_level: str) -> str:
        from ml.risk_engine import generate_explanation
        return generate_explanation(factors, risk_level)

    def generate_recommendations(self, factors: dict, risk_level: str, region_name: str) -> list:
        from services.recommendation_service import generate_recommendations
        return generate_recommendations(factors, risk_level, region_name)


def get_ai_provider() -> AIProvider:
    """
    Return the appropriate AI provider.
    Uses IBM watsonx.ai when all three env vars are set,
    otherwise falls back to LocalAIProvider.
    """
    api_key = os.environ.get('IBM_API_KEY', '')
    project_id = os.environ.get('IBM_PROJECT_ID', '')
    ibm_url = os.environ.get('IBM_URL', '')

    if api_key and project_id and ibm_url:
        try:
            from services.ibm_provider import IBMWatsonxProvider
            return IBMWatsonxProvider()
        except ImportError:
            pass

    return LocalAIProvider()
