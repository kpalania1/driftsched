# adaptive_token_estimator.py

import os
import redis


class AdaptiveTokenEstimator:
    def __init__(self):
        self.client = redis.Redis(
            host="localhost",
            port=6379,
            db=0,
            decode_responses=True
        )

        self.alpha = 0.1
        self.bias_key_prefix = "token_bias"

        self.default_bias = {
            "short_qa": 1.0,
            "summary": 1.0,
            "technical": 1.0,
            "report": 1.0
        }

    def classify_prompt(self, prompt: str) -> str:
        text = prompt.lower()

        scores = {
            "summary": text.count("summarize") + text.count("summary"),
            "report": text.count("detailed") + text.count("report") + text.count("comprehensive"),
            "technical": text.count("architecture") + text.count("code") + text.count("technical"),
        }

        best_category = max(scores, key=scores.get)
        return best_category if scores[best_category] > 0 else "short_qa"

    def get_base_tokens(self, category: str) -> int:
        return {
            "short_qa": 64,
            "summary": 256,
            "technical": 384,
            "report": 512
        }.get(category, 64)

    def _bias_key(self, category: str) -> str:
        return f"{self.bias_key_prefix}:{category}"

    def get_bias(self, category: str) -> float:
        bias_mode = os.environ.get("BIAS_MODE", "on").lower()

        if bias_mode == "off":
            return 1.0

        value = self.client.get(self._bias_key(category))

        if value is None:
            return self.default_bias.get(category, 1.0)

        return float(value)

    def estimate_budget(self, prompt: str, tenant_type: str) -> dict:
        category = self.classify_prompt(prompt)
        base = self.get_base_tokens(category)

        bias = self.get_bias(category)

        safety_factor = {
            "premium": 1.2,
            "standard": 1.0,
            "batch": 0.8
        }.get(tenant_type, 1.0)

        input_factor = min(
            1.5,
            1.0 + (len(prompt.split()) / 1000)
        )

        estimated_output_tokens = int(
            base * bias * safety_factor * input_factor
        )

        return {
            "category": category,
            "estimated_output_tokens": estimated_output_tokens,
            "base_tokens": base,
            "bias": bias,
            "safety_factor": safety_factor,
            "input_factor": round(input_factor, 2)
        }

    def apply_feedback(self, category: str, actual_tokens: int):

        bias_mode = os.environ.get("BIAS_MODE", "on").lower()

        if bias_mode == "off":
            return {
                "category": category,
                "base_tokens": self.get_base_tokens(category),
                "actual_tokens": actual_tokens,
                "old_bias": 1.0,
                "measured_bias": 1.0,
                "new_bias": 1.0
            }

        base = self.get_base_tokens(category)

        if base <= 0:
            return

        current_bias = self.get_bias(category)

        measured_bias = actual_tokens / base

        measured_bias = max(
            0.25,
            min(measured_bias, 3.0)
        )

        new_bias = (
            ((1 - self.alpha) * current_bias)
            + (self.alpha * measured_bias)
        )

        self.client.set(
            self._bias_key(category),
            new_bias
        )

        return {
            "category": category,
            "base_tokens": base,
            "actual_tokens": actual_tokens,
            "old_bias": current_bias,
            "measured_bias": measured_bias,
            "new_bias": new_bias
        }
