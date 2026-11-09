"""Client robuste pour l'API locale Ollama et mémoire conversationnelle."""
from __future__ import annotations

import json
import logging
import time
from datetime import datetime
from pathlib import Path

import requests

logger = logging.getLogger("llm_client")


class LLMError(Exception):
    """Erreur définitive du client LLM."""


class LLMClient:
    RETRYABLE_STATUS = {408, 429, 500, 502, 503, 504}

    def __init__(self, model, base_url="http://localhost:11434", temperature=0.1,
                 timeout=120, max_retries=3, backoff_factor=1.0, num_ctx=8192,
                 log_file=None):
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.url = self.base_url + "/api/chat"
        self.temperature = temperature
        self.timeout = timeout
        self.max_retries = max(1, int(max_retries))
        self.backoff_factor = backoff_factor
        self.num_ctx = num_ctx
        self.log_file = Path(log_file) if log_file else None
        self.session = requests.Session()

    def chat(self, messages: list[dict], json_mode: bool = False) -> str:
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": self.temperature, "num_ctx": self.num_ctx},
        }
        if json_mode:
            payload["format"] = "json"
        start = time.perf_counter()
        data = self._post_with_retry(payload)
        duration = time.perf_counter() - start
        try:
            answer = data["message"]["content"]
            if not isinstance(answer, str):
                raise TypeError("message.content n'est pas du texte")
        except (KeyError, TypeError) as exc:
            raise LLMError(f"Réponse Ollama inattendue : {exc}") from exc
        self._log_exchange(messages, answer, duration, data)
        logger.info("LLM %s : %.2f s, %s tokens lus, %s générés", self.model,
                    duration, data.get("prompt_eval_count", 0), data.get("eval_count", 0))
        return answer

    def _post_with_retry(self, payload: dict) -> dict:
        last_error = None
        for attempt in range(1, self.max_retries + 1):
            try:
                response = self.session.post(self.url, json=payload, timeout=self.timeout)
                if response.status_code in self.RETRYABLE_STATUS:
                    raise requests.HTTPError(f"HTTP {response.status_code}", response=response)
                if response.status_code >= 400:
                    detail = ""
                    try:
                        detail = response.json().get("error", "")
                    except (ValueError, AttributeError):
                        pass
                    raise LLMError(f"Erreur HTTP {response.status_code}: {detail}".rstrip())
                try:
                    return response.json()
                except ValueError as exc:
                    raise LLMError("Réponse Ollama invalide (JSON attendu).") from exc
            except LLMError:
                raise
            except (requests.ConnectionError, requests.Timeout, requests.HTTPError) as exc:
                last_error = exc
                if isinstance(exc, requests.HTTPError):
                    status = getattr(getattr(exc, "response", None), "status_code", "?")
                    logger.warning("Ollama HTTP %s, tentative %s/%s", status, attempt, self.max_retries)
                else:
                    logger.warning("Appel Ollama échoué, tentative %s/%s : %s", attempt, self.max_retries, exc)
                if attempt < self.max_retries:
                    time.sleep(self.backoff_factor * (2 ** (attempt - 1)))
        raise LLMError(f"Impossible de joindre Ollama après {self.max_retries} tentative(s) : {last_error}. Vérifiez Ollama ou lancez « ollama serve ».") from last_error

    def _log_exchange(self, messages, answer, duration, raw):
        if not self.log_file:
            return
        entry = {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "model": self.model,
            "duration_s": round(duration, 3),
            "prompt_tokens": raw.get("prompt_eval_count"),
            "completion_tokens": raw.get("eval_count"),
            "messages": messages,
            "answer": answer,
        }
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        with self.log_file.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def is_available(self) -> bool:
        try:
            return self.session.get(self.base_url + "/api/tags", timeout=3).ok
        except requests.RequestException:
            return False


class Conversation:
    """System prompt stable et fenêtre glissante des derniers tours."""

    def __init__(self, system_prompt: str, max_turns: int = 6) -> None:
        self.system_prompt = system_prompt
        self.max_turns = max(0, int(max_turns))
        self.history: list[dict] = []

    def add_user(self, content: str) -> None:
        self.history.append({"role": "user", "content": content})

    def add_assistant(self, content: str) -> None:
        self.history.append({"role": "assistant", "content": content})

    def messages(self) -> list[dict]:
        tail = self.history[-2 * self.max_turns:] if self.max_turns else []
        return [{"role": "system", "content": self.system_prompt}, *tail]

    def estimated_tokens(self) -> int:
        return sum(len(str(m["content"])) for m in self.messages()) // 4

    def reset(self) -> None:
        self.history.clear()
