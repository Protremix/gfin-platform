"""GFIN Local AI — Module 21.

Self-hosted AI capabilities: text classification, embeddings, OCR, language detection.
Serves as fallback when OpenAI is unavailable and handles restricted/law-enforcement data.

Layer A: Mock/deterministic implementations (keyword matching, hash vectors, heuristics)
Layer B: Real local models via vLLM/Ollama, sentence-transformers, Tesseract (REQUIRES EXTERNAL INFRASTRUCTURE)
"""

import contextlib
import hashlib
import math
import struct
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

# ─── Enums ───


class LocalAIModel(str, Enum):
    CLASSIFIER = "local-classifier"
    EMBEDDING = "local-embedding"
    OCR = "local-ocr"
    LANGUAGE = "local-language"


class ModelHealth(str, Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNAVAILABLE = "UNAVAILABLE"


class LanguageCode(str, Enum):
    EN = "en"
    ES = "es"
    FR = "fr"
    DE = "de"
    RU = "ru"
    ZH = "zh"
    AR = "ar"
    PT = "pt"
    IT = "it"
    JA = "ja"
    UNKNOWN = "unknown"


# ─── Models ───


class ClassificationResult(BaseModel):
    """Result of a text classification."""

    label: str
    confidence: float
    model: str = LocalAIModel.CLASSIFIER.value
    all_scores: dict[str, float] = Field(default_factory=dict)


class EmbeddingResult(BaseModel):
    """Result of an embedding operation."""

    text: str
    vector: list[float]
    model: str = LocalAIModel.EMBEDDING.value
    dimensions: int = 0


class OCRResult(BaseModel):
    """Result of OCR text extraction."""

    text: str
    confidence: float
    model: str = LocalAIModel.OCR.value
    pages: int = 1


class LanguageResult(BaseModel):
    """Result of language detection."""

    language: str
    confidence: float
    model: str = LocalAIModel.LANGUAGE.value
    alternatives: dict[str, float] = Field(default_factory=dict)


class ModelInfo(BaseModel):
    """Information about a local model."""

    name: str
    model_type: str  # classifier, embedding, ocr, language
    health: str = ModelHealth.HEALTHY.value
    version: str = "1.0.0-layer-a"
    loaded: bool = True


# ─── Keyword dictionaries for Layer A classification ───

FRAUD_TYPE_KEYWORDS: dict[str, list[str]] = {
    "phishing": [
        "phishing",
        "fake email",
        "spoofed",
        "impersonation",
        "credential",
        "fake login",
        "fake website",
        "account suspended",
        "verify your",
        "click here to",
        "urgent action required",
    ],
    "advance_fee_fraud": [
        "advance fee",
        "lottery",
        "inheritance",
        "nigerian prince",
        "wire transfer",
        "upfront payment",
        "processing fee",
        "transfer funds",
        "beneficiary",
        "consignment",
    ],
    "romance_scam": [
        "romance",
        "love",
        "sweetheart",
        "dating",
        "lonely",
        "widow",
        "widower",
        "deployed soldier",
        "oil rig",
        "candy crush",
    ],
    "investment_fraud": [
        "investment",
        "crypto",
        "bitcoin",
        "trading",
        "forex",
        "double your",
        "guaranteed return",
        "mining",
        "ponzi",
        "get rich",
        "passive income",
    ],
    "tech_support_scam": [
        "tech support",
        "microsoft",
        "virus",
        "malware",
        "pop-up",
        "your computer is infected",
        "remote access",
        "refund",
        "security alert",
        "windows support",
    ],
    "shopping_scam": [
        "online store",
        "fake product",
        "never delivered",
        "counterfeit",
        "too good to be true",
        "discount",
        "free shipping",
        "marketplace",
        "order confirmation",
    ],
}

SEVERITY_KEYWORDS: dict[str, list[str]] = {
    "CRITICAL": [
        "bank",
        "financial",
        "stolen",
        "identity theft",
        "thousands",
        "life savings",
        "retirement",
        "mortgage",
    ],
    "HIGH": [
        "money",
        "fraud",
        "scam",
        "urgent",
        "police",
        "report",
        "victim",
        "loss",
        "stolen",
    ],
    "MEDIUM": [
        "suspicious",
        "concern",
        "unsure",
        "questionable",
        "might be",
        "possibly",
        "seems like",
    ],
    "LOW": [
        "spam",
        "annoying",
        "unwanted",
        "minor",
        "information",
        "inquiry",
        "checking",
    ],
}

SPAM_KEYWORDS = [
    "buy now",
    "limited offer",
    "click here",
    "act now",
    "free",
    "winner",
    "congratulations",
    "selected",
    "exclusive deal",
    "unsubscribe",
    "bitcoin doubler",
    "misspell",
    "guaranteed",
]

# Common words for language detection
LANGUAGE_WORDS: dict[str, set[str]] = {
    LanguageCode.EN.value: {
        "the",
        "and",
        "is",
        "are",
        "was",
        "were",
        "have",
        "has",
        "that",
        "this",
        "with",
        "for",
        "not",
        "but",
        "you",
        "from",
    },
    LanguageCode.ES.value: {
        "el",
        "la",
        "los",
        "las",
        "y",
        "es",
        "son",
        "fue",
        "que",
        "este",
        "con",
        "para",
        "no",
        "pero",
        "usted",
        "de",
    },
    LanguageCode.FR.value: {
        "le",
        "la",
        "les",
        "et",
        "est",
        "sont",
        "était",
        "que",
        "ce",
        "avec",
        "pour",
        "ne",
        "mais",
        "vous",
        "de",
    },
    LanguageCode.DE.value: {
        "der",
        "die",
        "das",
        "und",
        "ist",
        "sind",
        "war",
        "dass",
        "dies",
        "mit",
        "für",
        "nicht",
        "aber",
        "Sie",
        "von",
    },
    LanguageCode.RU.value: {
        "и",
        "в",
        "не",
        "на",
        "что",
        "это",
        "с",  # noqa: RUF001
        "по",
        "но",
        "от",
        "был",
        "для",
        "вы",
        "как",
    },
    LanguageCode.ZH.value: set(),  # Character-based detection
    LanguageCode.AR.value: set(),  # Character-based detection
    LanguageCode.PT.value: {
        "o",
        "a",
        "os",
        "as",
        "e",
        "é",
        "são",
        "foi",
        "que",
        "este",
        "com",
        "para",
        "não",
        "mas",
        "você",
        "de",
    },
    LanguageCode.IT.value: {
        "il",
        "la",
        "le",
        "e",
        "è",
        "sono",
        "era",
        "che",
        "questo",
        "con",
        "per",
        "non",
        "ma",
        "lei",
        "di",
    },
    LanguageCode.JA.value: set(),  # Character-based detection
}

# Unicode ranges for character-based language detection
LANGUAGE_RANGES: dict[str, tuple[int, int]] = {
    LanguageCode.ZH.value: (0x4E00, 0x9FFF),  # CJK Unified Ideographs
    LanguageCode.JA.value: (0x3040, 0x30FF),  # Hiragana + Katakana
    LanguageCode.AR.value: (0x0600, 0x06FF),  # Arabic
    LanguageCode.RU.value: (0x0400, 0x04FF),  # Cyrillic
}


# ─── Embedding Service ───


class EmbeddingService:
    """Local embedding service (Layer A: hash-based mock vectors)."""

    DIMENSIONS = 128

    def __init__(self, dimensions: int = 128) -> None:
        self.DIMENSIONS = dimensions

    def embed_text(self, text: str) -> list[float]:
        """Generate a mock embedding vector from text (hash-based)."""
        vector = [0.0] * self.DIMENSIONS
        tokens = text.lower().split()
        for token in tokens:
            h = hashlib.sha256(token.encode()).digest()
            for i in range(0, self.DIMENSIONS, 4):
                if i + 4 <= len(h):
                    val = struct.unpack("<I", h[i : i + 4])[0]
                    idx = i // 4
                    if idx < self.DIMENSIONS:
                        vector[idx] += (val % 1000) / 1000.0

        # L2 normalize
        norm = math.sqrt(sum(v * v for v in vector))
        if norm > 0:
            vector = [v / norm for v in vector]
        return vector

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts."""
        return [self.embed_text(t) for t in texts]

    @staticmethod
    def cosine_similarity(v1: list[float], v2: list[float]) -> float:
        """Compute cosine similarity between two vectors."""
        if len(v1) != len(v2):
            return 0.0
        dot = sum(a * b for a, b in zip(v1, v2, strict=False))
        norm1 = math.sqrt(sum(a * a for a in v1))
        norm2 = math.sqrt(sum(b * b for b in v2))
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot / (norm1 * norm2)

    def find_similar(
        self,
        query: list[float],
        vectors: list[tuple[str, list[float]]],
        top_k: int = 5,
    ) -> list[tuple[str, float]]:
        """Find the most similar vectors to a query."""
        scored = [(label, self.cosine_similarity(query, vec)) for label, vec in vectors]
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]


# ─── Classification Service ───


class ClassificationService:
    """Local text classification (Layer A: keyword-based)."""

    def classify_fraud_type(self, text: str) -> ClassificationResult:
        """Classify text into a fraud type based on keyword matching."""
        text_lower = text.lower()
        scores: dict[str, float] = {}

        for fraud_type, keywords in FRAUD_TYPE_KEYWORDS.items():
            score = 0.0
            for kw in keywords:
                if kw in text_lower:
                    score += 1.0 / len(keywords)
            scores[fraud_type] = score

        # Normalize
        total = sum(scores.values())
        if total > 0:
            scores = {k: v / total for k, v in scores.items()}

        best_label = max(scores, key=lambda k: scores[k]) if scores else "unknown"
        best_confidence = scores.get(best_label, 0.0)

        if total == 0:
            best_label = "unknown"
            best_confidence = 0.0

        return ClassificationResult(
            label=best_label,
            confidence=best_confidence,
            model=LocalAIModel.CLASSIFIER.value,
            all_scores=scores,
        )

    def classify_severity(self, text: str) -> ClassificationResult:
        """Classify text severity based on keyword matching."""
        text_lower = text.lower()
        scores: dict[str, float] = {}

        for severity, keywords in SEVERITY_KEYWORDS.items():
            score = 0.0
            for kw in keywords:
                if kw in text_lower:
                    score += 1.0 / len(keywords)
            scores[severity] = score

        total = sum(scores.values())
        if total > 0:
            scores = {k: v / total for k, v in scores.items()}

        best_label = max(scores, key=lambda k: scores[k]) if scores else "LOW"
        best_confidence = scores.get(best_label, 0.0)

        if total == 0:
            best_label = "LOW"
            best_confidence = 0.5

        return ClassificationResult(
            label=best_label,
            confidence=best_confidence,
            model=LocalAIModel.CLASSIFIER.value,
            all_scores=scores,
        )

    def detect_spam(self, text: str) -> tuple[bool, float]:
        """Detect if text is spam. Returns (is_spam, confidence)."""
        text_lower = text.lower()
        hits = sum(1 for kw in SPAM_KEYWORDS if kw in text_lower)
        confidence = min(hits / 5.0, 1.0)
        return (hits >= 3, confidence)


# ─── OCR Service ───


class OCRService:
    """Local OCR service (Layer A: mock text extraction)."""

    def extract_text(self, image_bytes: bytes) -> OCRResult:
        """Extract text from image bytes (mock in Layer A)."""
        # Layer A: return a mock result
        # In Layer B, this would use Tesseract/EasyOCR
        text = "[Mock OCR output — Layer A does not perform real OCR]"
        return OCRResult(
            text=text,
            confidence=0.0,
            model=LocalAIModel.OCR.value,
            pages=1,
        )

    def extract_text_from_file(self, file_path: str) -> OCRResult:
        """Extract text from a file (mock in Layer A)."""
        # Read file size for mock
        try:
            with open(file_path, "rb") as f:
                data = f.read()
            return self.extract_text(data)
        except Exception:
            return OCRResult(
                text="",
                confidence=0.0,
                model=LocalAIModel.OCR.value,
                pages=0,
            )


# ─── Language Detector ───


class LanguageDetector:
    """Local language detection (Layer A: heuristic)."""

    def detect(self, text: str) -> LanguageResult:
        """Detect the language of a text."""
        if not text.strip():
            return LanguageResult(
                language=LanguageCode.UNKNOWN.value,
                confidence=0.0,
                model=LocalAIModel.LANGUAGE.value,
            )

        # Check character-based ranges first (more reliable)
        char_scores: dict[str, int] = {}
        for lang, (start, end) in LANGUAGE_RANGES.items():
            count = sum(1 for ch in text if start <= ord(ch) <= end)
            if count > 0:
                char_scores[lang] = count

        if char_scores:
            total_chars = sum(char_scores.values())
            best_lang = max(char_scores, key=lambda k: char_scores[k])
            confidence = char_scores[best_lang] / max(len(text), 1)
            alternatives = {k: v / total_chars for k, v in char_scores.items()}
            return LanguageResult(
                language=best_lang,
                confidence=min(confidence, 1.0),
                model=LocalAIModel.LANGUAGE.value,
                alternatives=alternatives,
            )

        # Word-based detection
        words = text.lower().split()
        word_scores: dict[str, int] = {}
        for lang, common_words in LANGUAGE_WORDS.items():
            if not common_words:
                continue
            count = sum(1 for w in words if w in common_words)
            if count > 0:
                word_scores[lang] = count

        if word_scores:
            total_words = sum(word_scores.values())
            best_lang = max(word_scores, key=lambda k: word_scores[k])
            confidence = word_scores[best_lang] / max(len(words), 1)
            alternatives = {k: v / total_words for k, v in word_scores.items()}
            return LanguageResult(
                language=best_lang,
                confidence=min(confidence, 1.0),
                model=LocalAIModel.LANGUAGE.value,
                alternatives=alternatives,
            )

        return LanguageResult(
            language=LanguageCode.UNKNOWN.value,
            confidence=0.0,
            model=LocalAIModel.LANGUAGE.value,
        )


# ─── Local AI Adapter ───


class LocalAIAdapter:
    """Adapter for all local AI capabilities."""

    def __init__(self) -> None:
        self._embedding = EmbeddingService()
        self._classifier = ClassificationService()
        self._ocr = OCRService()
        self._language = LanguageDetector()
        self._models: list[ModelInfo] = [
            ModelInfo(name=LocalAIModel.CLASSIFIER.value, model_type="classifier"),
            ModelInfo(name=LocalAIModel.EMBEDDING.value, model_type="embedding"),
            ModelInfo(name=LocalAIModel.OCR.value, model_type="ocr"),
            ModelInfo(name=LocalAIModel.LANGUAGE.value, model_type="language"),
        ]

    def classify(
        self, text: str, model: str = LocalAIModel.CLASSIFIER.value
    ) -> ClassificationResult:
        """Classify text."""
        return self._classifier.classify_fraud_type(text)

    def classify_severity(self, text: str) -> ClassificationResult:
        """Classify severity."""
        return self._classifier.classify_severity(text)

    def detect_spam(self, text: str) -> tuple[bool, float]:
        """Detect spam."""
        return self._classifier.detect_spam(text)

    def embed(self, text: str, model: str = LocalAIModel.EMBEDDING.value) -> EmbeddingResult:
        """Generate embedding."""
        vector = self._embedding.embed_text(text)
        return EmbeddingResult(
            text=text,
            vector=vector,
            model=model,
            dimensions=len(vector),
        )

    def embed_batch(self, texts: list[str]) -> list[EmbeddingResult]:
        """Generate embeddings for multiple texts."""
        vectors = self._embedding.embed_batch(texts)
        return [
            EmbeddingResult(
                text=t,
                vector=v,
                model=LocalAIModel.EMBEDDING.value,
                dimensions=len(v),
            )
            for t, v in zip(texts, vectors, strict=False)
        ]

    def ocr(self, image_bytes: bytes, model: str = LocalAIModel.OCR.value) -> OCRResult:
        """Extract text from image."""
        return self._ocr.extract_text(image_bytes)

    def detect_language(self, text: str) -> LanguageResult:
        """Detect language."""
        return self._language.detect(text)

    def health_check(self) -> dict[str, str]:
        """Check health of all local models."""
        return {m.name: m.health for m in self._models}

    def list_models(self) -> list[ModelInfo]:
        """List available local models."""
        return list(self._models)


# ─── Local AI Gateway ───


class LocalAIGateway:
    """Classification-aware routing between Local AI and OpenAI."""

    # Data classification routing rules
    ROUTING_RULES: dict[str, str] = {
        "PUBLIC": "openai",  # Primary: OpenAI; Local as fallback
        "COMMUNITY": "openai",  # Primary: OpenAI (minimized); Local as fallback
        "RESTRICTED": "local",  # Primary: Local AI
        "LAW_ENFORCEMENT": "local",  # Local only
        "HIGHLY_RESTRICTED": "local",  # Local only, isolated
    }

    def __init__(
        self,
        local_adapter: LocalAIAdapter | None = None,
        openai_gateway: Any | None = None,
        event_bus: Any | None = None,
    ) -> None:
        self._local = local_adapter or LocalAIAdapter()
        self._openai = openai_gateway
        self._event_bus = event_bus
        self._fallback_count = 0
        self._local_count = 0
        self._openai_count = 0

    def route(
        self,
        request: dict[str, Any],
        classification: str = "PUBLIC",
    ) -> dict[str, Any]:
        """Route a request based on data classification."""
        target = self.ROUTING_RULES.get(classification, "local")

        if target == "local":
            return self._handle_local(request)
        else:
            return self._handle_openai(request, classification)

    def fallback(self, request: dict[str, Any]) -> dict[str, Any]:
        """Fall back to Local AI when OpenAI is unavailable."""
        self._fallback_count += 1

        if self._event_bus:
            with contextlib.suppress(Exception):
                self._event_bus.publish(
                    topic="ai.fallback",
                    event={
                        "provider": "local",
                        "reason": "openai_unavailable",
                        "timestamp": datetime.now(UTC).isoformat(),
                    },
                )

        return self._handle_local(request)

    def _handle_local(self, request: dict[str, Any]) -> dict[str, Any]:
        """Handle request with local AI."""
        self._local_count += 1
        operation = request.get("operation", "classify")

        result: Any
        if operation == "classify":
            result = self._local.classify(request.get("text", ""))
            return {"provider": "local", "result": result}
        elif operation == "embed":
            result = self._local.embed(request.get("text", ""))
            return {"provider": "local", "result": result}
        elif operation == "ocr":
            result = self._local.ocr(request.get("image_bytes", b""))
            return {"provider": "local", "result": result}
        elif operation == "detect_language":
            result = self._local.detect_language(request.get("text", ""))
            return {"provider": "local", "result": result}
        elif operation == "classify_severity":
            result = self._local.classify_severity(request.get("text", ""))
            return {"provider": "local", "result": result}
        else:
            return {"provider": "local", "result": None, "error": f"Unknown operation: {operation}"}

    def _handle_openai(self, request: dict[str, Any], classification: str) -> dict[str, Any]:
        """Handle request with OpenAI (or fallback to local)."""
        if self._openai is None:
            # No OpenAI gateway configured → fallback to local
            return self.fallback(request)

        try:
            self._openai_count += 1
            # In Layer A, the OpenAI gateway is a mock or the real adapter
            # The actual call depends on the operation
            result = self._openai.process(request)
            return {"provider": "openai", "result": result}
        except Exception:
            return self.fallback(request)

    @property
    def statistics(self) -> dict[str, int]:
        """Get routing statistics."""
        return {
            "total": self._local_count + self._openai_count,
            "local": self._local_count,
            "openai": self._openai_count,
            "fallbacks": self._fallback_count,
        }

    @property
    def local_adapter(self) -> LocalAIAdapter:
        return self._local
