"""
IBM watsonx.ai provider for AquaGuard.

Reads credentials from environment:
  IBM_API_KEY, IBM_PROJECT_ID, IBM_URL

Falls back to LocalAIProvider on any IBM API error.
"""
import os
import json
import logging

import requests

from services.ai_provider import AIProvider, LocalAIProvider

logger = logging.getLogger(__name__)

_WATSONX_GENERATE_PATH = '/ml/v1/text/generation?version=2023-05-29'
_DEFAULT_MODEL = 'ibm/granite-13b-instruct-v2'


class IBMWatsonxProvider(AIProvider):
    def __init__(self):
        self.api_key = os.environ['IBM_API_KEY']
        self.project_id = os.environ['IBM_PROJECT_ID']
        self.base_url = os.environ['IBM_URL'].rstrip('/')
        self._access_token = None
        self._fallback = LocalAIProvider()

    # ------------------------------------------------------------------
    # Auth
    # ------------------------------------------------------------------

    def _get_token(self) -> str:
        """Obtain an IAM bearer token (cached for the lifetime of the instance)."""
        if self._access_token:
            return self._access_token
        resp = requests.post(
            'https://iam.cloud.ibm.com/identity/token',
            data={
                'grant_type': 'urn:ibm:params:oauth:grant-type:apikey',
                'apikey': self.api_key,
            },
            timeout=15,
        )
        resp.raise_for_status()
        self._access_token = resp.json()['access_token']
        return self._access_token

    def _call_generate(self, prompt: str, max_tokens: int = 300) -> str:
        """Call the watsonx.ai text generation endpoint."""
        url = self.base_url + _WATSONX_GENERATE_PATH
        payload = {
            'model_id': _DEFAULT_MODEL,
            'input': prompt,
            'parameters': {
                'max_new_tokens': max_tokens,
                'temperature': 0.3,
            },
            'project_id': self.project_id,
        }
        headers = {
            'Authorization': f'Bearer {self._get_token()}',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }
        logger.info("IBM watsonx API call: model=%s tokens=%d", _DEFAULT_MODEL, max_tokens)
        resp = requests.post(url, json=payload, headers=headers, timeout=30)
        resp.raise_for_status()
        result = resp.json()
        logger.debug("IBM watsonx response: %s", json.dumps(result)[:500])
        return result['results'][0]['generated_text'].strip()

    # ------------------------------------------------------------------
    # AIProvider interface
    # ------------------------------------------------------------------

    def generate_explanation(self, factors: dict, risk_level: str) -> str:
        prompt = (
            f"You are a water resource management expert.\n"
            f"Risk level: {risk_level}\n"
            f"Factors (0-100 scale): {json.dumps(factors, indent=2)}\n"
            f"Write a concise 2-3 sentence explanation of the water shortage risk "
            f"for a municipal water authority."
        )
        try:
            return self._call_generate(prompt, max_tokens=200)
        except Exception as exc:
            logger.warning("IBMWatsonxProvider.generate_explanation failed: %s — using fallback", exc)
            return self._fallback.generate_explanation(factors, risk_level)

    def generate_recommendations(self, factors: dict, risk_level: str, region_name: str) -> list:
        prompt = (
            f"You are a water resource management expert.\n"
            f"Region: {region_name}\n"
            f"Risk level: {risk_level}\n"
            f"Factors: {json.dumps(factors)}\n"
            f"Provide 3 specific, actionable water management recommendations. "
            f"Return a JSON array of objects with keys: title, description, action_required, priority, category."
        )
        try:
            raw = self._call_generate(prompt, max_tokens=400)
            # Strip markdown fences if present
            raw = raw.strip()
            if raw.startswith('```'):
                raw = raw.split('```')[1]
                if raw.startswith('json'):
                    raw = raw[4:]
            recommendations = json.loads(raw)
            if isinstance(recommendations, list):
                return recommendations
        except Exception as exc:
            logger.warning("IBMWatsonxProvider.generate_recommendations failed: %s — using fallback", exc)

        return self._fallback.generate_recommendations(factors, risk_level, region_name)
