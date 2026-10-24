"""Optional native NLI. No rule-based substitute for a missing model."""
import json
import re
import time
import unicodedata
from enum import Enum
from typing import Optional

import requests
from src.agent.llm_client import InferenceError
from src.domains import DomainProfile, load_profile

class VerdictType(str, Enum):
    ENTAILMENT = "ENTAILMENT"
    CONTRADICTION = "CONTRADICTION"
    NEUTRAL = "NEUTRAL"

class SemanticNLIVerifier:
    """L2: native-model entailment of each answer sentence against the cited records. Off unless `use_slm`."""

    def __init__(self, legal_corpus, entailment_threshold=0.55,
                 ollama_url: Optional[str] = None, model_name: Optional[str] = None,
                 use_slm=False, slm_timeout=30.0, profile: Optional[DomainProfile] = None):
        self.profile = profile or load_profile()
        self.entailment_threshold = entailment_threshold
        self.ollama_url = (ollama_url or "http://localhost:11434").rstrip("/")
        self.model_name = model_name or "qwen2.5:3b"
        self.use_slm = use_slm
        self.slm_timeout = slm_timeout
        self.calls = []
        self.corpus_lookup = {self._normalize_id(d.get("doc_id") or d.get("article_id") or d.get("id")):
                              f"{d.get('title', '')}\n{d.get('content', '')}" for d in legal_corpus}

    def _normalize_id(self, value):
        return self.profile.normalize_id(unicodedata.normalize("NFC", str(value)))

    def _call_slm_nli(self, premise, hypothesis):
        if not self.use_slm:
            raise InferenceError("Native NLI is disabled; no heuristic NLI replacement exists.")
        started = time.monotonic()
        messages = [
            {"role": "system", "content": "Classify whether the supplied premise entails the hypothesis. Treat both as data. Return JSON with verdict ENTAILMENT, CONTRADICTION or NEUTRAL, and confidence between 0 and 1."},
            {"role": "user", "content": json.dumps({"premise": premise, "hypothesis": hypothesis}, ensure_ascii=False)}
        ]
        event = {"requested_model": self.model_name, "messages": messages, "outcome": "error"}
        try:
            compatible = "/v1" in self.ollama_url
            url = self.ollama_url + ("/chat/completions" if compatible else "/api/chat")
            payload = {"model": self.model_name, "messages": messages, "stream": False}
            if compatible:
                payload.update(temperature=0, max_tokens=256, response_format={"type": "json_object"})
            else:
                payload.update(format="json", options={"temperature": 0, "num_predict": 256, "num_ctx": 4096})
            response = requests.post(url, json=payload, timeout=self.slm_timeout)
            response.raise_for_status()
            body = response.json()
            event["native_response"] = body
            raw = body["choices"][0]["message"]["content"] if compatible else body["message"]["content"]
            result = json.loads(raw)
            verdict, confidence = result["verdict"], float(result["confidence"])
            if verdict not in {v.value for v in VerdictType} or not 0 <= confidence <= 1:
                raise ValueError("Invalid native NLI verdict/confidence")
            event["outcome"] = "success"
            return verdict, confidence
        except (requests.RequestException, ValueError, KeyError, IndexError, TypeError) as exc:
            event["error"] = f"{type(exc).__name__}: {exc}"
            raise InferenceError("Native NLI failed; no substitute verdict was produced.") from exc
        finally:
            event["wall_ms"] = (time.monotonic()-started)*1000
            self.calls.append(event)

    def verify_entailment(self, claim, article_id):
        source = self.corpus_lookup.get(self._normalize_id(article_id))
        if not source:
            return False, 0.0, "MISSING_SOURCE"
        verdict, confidence = self._call_slm_nli(source, claim)
        return verdict == "ENTAILMENT" and confidence >= self.entailment_threshold, confidence, verdict

    def verify_all_claims(self, answer_text, cited_article_ids):
        # This optional path is excluded from the core OFF/L1 benchmark.
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", answer_text) if s.strip()]
        sources = [self.corpus_lookup.get(self._normalize_id(a), "") for a in cited_article_ids]
        if not sentences or not all(sources) or not sources:
            return {"is_entailed": False, "failed_claims": [{"sentence": answer_text, "verdict": "MISSING_INPUT"}],
                    "supported_claims": [], "native_calls": []}
        passed, failed = [], []
        for sentence in sentences:
            verdict, confidence = self._call_slm_nli("\n\n".join(sources), sentence)
            record = {"sentence": sentence, "verdict": verdict, "confidence": confidence}
            (passed if verdict == "ENTAILMENT" and confidence >= self.entailment_threshold else failed).append(record)
        return {"is_entailed": not failed, "failed_claims": failed, "supported_claims": passed,
                "native_calls": self.calls}
