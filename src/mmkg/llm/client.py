"""LLM/VLM OpenAI 兼容客户端：DeepSeek（纯文本）与百炼（看图）统一入口。

- 重试与 429 退避；JSON 输出自动剥壳解析
- usage 统计供运行报告与成本核算
"""

import base64
import json
import logging
import re
import time

from openai import APIError, OpenAI, RateLimitError

from mmkg.config import Settings

log = logging.getLogger(__name__)

_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


class LLMClient:
    def __init__(self, settings: Settings, model: str | None = None,
                 provider: str = "llm"):
        """provider: "llm"（DeepSeek 纯文本）或 "vlm"（看图，可配百炼/DeepSeek）。"""
        if provider == "llm":
            api_key, base_url = settings.llm_api_key, settings.llm_base_url
            default_model = settings.llm_model
        else:
            api_key = settings.vlm_api_key or settings.llm_api_key
            base_url = settings.vlm_base_url
            default_model = settings.vlm_model
        self.client = OpenAI(api_key=api_key, base_url=base_url, timeout=60)
        self.model = model or default_model
        self.usage = {"calls": 0, "prompt_tokens": 0, "completion_tokens": 0, "errors": 0}

    def chat_json(self, system: str, user_text: str,
                  image_path: str | None = None,
                  temperature: float = 0.0, max_retries: int = 3) -> dict | None:
        """图文（或纯文本）请求，返回解析后的 dict；失败返回 None。"""
        content: list[dict] = []
        if image_path:
            b64 = base64.b64encode(open(image_path, "rb").read()).decode()
            content.append({"type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{b64}"}})
        content.append({"type": "text", "text": user_text})

        delay = 2.0
        for attempt in range(1, max_retries + 1):
            try:
                resp = self.client.chat.completions.create(
                    model=self.model, temperature=temperature,
                    messages=[{"role": "system", "content": system},
                              {"role": "user", "content": content}])
                self.usage["calls"] += 1
                if resp.usage:
                    self.usage["prompt_tokens"] += resp.usage.prompt_tokens or 0
                    self.usage["completion_tokens"] += resp.usage.completion_tokens or 0
                return self._parse_json(resp.choices[0].message.content or "")
            except RateLimitError:
                self.usage["errors"] += 1
                if attempt == max_retries:
                    log.warning("限流放弃：%s", self.model)
                    return None
                time.sleep(delay)
                delay = min(delay * 2, 30)
            except (APIError, Exception) as e:  # noqa: BLE001
                self.usage["errors"] += 1
                if attempt == max_retries:
                    log.warning("调用失败放弃：%s: %s", type(e).__name__, str(e)[:120])
                    return None
                time.sleep(delay)
                delay = min(delay * 2, 30)
        return None

    @staticmethod
    def _parse_json(text: str) -> dict | None:
        """容错解析：剥掉 markdown 围栏、截取最外层 JSON 对象。"""
        m = _JSON_RE.search(text.strip())
        if not m:
            return None
        try:
            obj = json.loads(m.group(0))
            return obj if isinstance(obj, dict) else None
        except json.JSONDecodeError:
            return None
