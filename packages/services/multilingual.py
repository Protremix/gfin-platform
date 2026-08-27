"""GFIN Multilingual — Module 29.

Multilingual support: language detection, translation management,
locale handling, and cross-language entity matching.

Layer A: In-memory multilingual framework
Layer B: Real translation API integration (DeepL, Google Translate) (REQUIRES EXTERNAL INFRASTRUCTURE)
"""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class SupportedLanguage(StrEnum):
    EN = "EN"
    DE = "DE"
    FR = "FR"
    ES = "ES"
    IT = "IT"
    NL = "NL"
    PL = "PL"
    PT = "PT"
    RO = "RO"
    EL = "EL"
    CS = "CS"
    DA = "DA"
    FI = "FI"
    SV = "SV"
    BG = "BG"
    HR = "HR"
    HU = "HU"
    LT = "LT"
    LV = "LV"
    SK = "SK"
    SL = "SL"
    ET = "ET"
    JA = "JA"
    ZH = "ZH"
    KO = "KO"
    AR = "AR"
    RU = "RU"
    TR = "TR"
    UK = "UK"


class TranslationStatus(StrEnum):
    PENDING = "PENDING"
    TRANSLATED = "TRANSLATED"
    FAILED = "FAILED"
    CACHE_HIT = "CACHE_HIT"


class LanguageDetection(BaseModel):
    """Result of language detection."""

    text: str
    detected_language: str = ""
    confidence: float = 0.0
    alternatives: dict[str, float] = Field(default_factory=dict)


class TranslationRecord(BaseModel):
    """A translation record."""

    id: str
    source_text: str
    source_lang: str
    target_lang: str
    translated_text: str = ""
    status: str = TranslationStatus.PENDING.value
    translator: str = "internal"
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    quality_score: float = 0.0

    def complete(self, translated_text: str, quality_score: float = 0.0) -> None:
        self.translated_text = translated_text
        self.quality_score = quality_score
        self.status = TranslationStatus.TRANSLATED.value

    def fail(self) -> None:
        self.status = TranslationStatus.FAILED.value


class MultilingualService:
    """Service for multilingual support.

    Per Master Spec: multilingual analysis, language detection.
    """

    # Simple language detection heuristics (Layer A simulation)
    LANGUAGE_KEYWORDS: dict[str, list[str]] = {
        SupportedLanguage.EN.value: ["the", "and", "is", "to", "of", "a", "in", "that"],
        SupportedLanguage.DE.value: ["der", "die", "das", "und", "ist", "nicht", "ein", "eine"],
        SupportedLanguage.FR.value: ["le", "la", "les", "et", "est", "une", "un", "de"],
        SupportedLanguage.ES.value: ["el", "la", "los", "las", "y", "es", "una", "un"],
        SupportedLanguage.IT.value: ["il", "la", "le", "e", "è", "una", "un", "di"],
        SupportedLanguage.NL.value: ["de", "het", "een", "en", "is", "van", "te", "dat"],
        SupportedLanguage.PT.value: ["o", "a", "os", "as", "e", "é", "uma", "um"],
        SupportedLanguage.PL.value: ["nie", "się", "jest", "to", "i", "na", "że", "się"],
        SupportedLanguage.RU.value: ["и", "в", "не", "на", "я", "что", "он", chr(1089)],
        SupportedLanguage.JA.value: ["の", "は", "を", "に", "が", "で", "と", "た"],
    }

    def __init__(self) -> None:
        self._translations: dict[str, TranslationRecord] = {}
        self._translation_cache: dict[str, str] = {}
        self._counter = 0

    def detect_language(self, text: str) -> LanguageDetection:
        """Detect the language of a text (simple heuristic)."""
        words = text.lower().split()
        if not words:
            return LanguageDetection(
                text=text, detected_language=SupportedLanguage.EN.value, confidence=0.0
            )

        scores: dict[str, float] = {}
        for lang, keywords in self.LANGUAGE_KEYWORDS.items():
            matches = sum(1 for w in words if w in keywords)
            scores[lang] = matches / len(words) if words else 0

        best_lang = max(scores, key=lambda k: scores[k])
        best_score = scores[best_lang]

        # Sort alternatives
        alternatives = dict(sorted(scores.items(), key=lambda x: x[1], reverse=True)[:3])

        return LanguageDetection(
            text=text,
            detected_language=best_lang,
            confidence=round(best_score, 4),
            alternatives=alternatives,
        )

    def request_translation(
        self,
        source_text: str,
        source_lang: str,
        target_lang: str,
    ) -> TranslationRecord:
        """Request a translation."""
        cache_key = f"{source_lang}:{target_lang}:{source_text}"

        self._counter += 1
        record = TranslationRecord(
            id=f"TR-{self._counter:06d}",
            source_text=source_text,
            source_lang=source_lang,
            target_lang=target_lang,
        )

        if cache_key in self._translation_cache:
            record.translated_text = self._translation_cache[cache_key]
            record.status = TranslationStatus.CACHE_HIT.value
        else:
            # Layer A: simulate translation (identity for same lang, placeholder for different)
            if source_lang == target_lang:
                record.complete(source_text, quality_score=1.0)
            else:
                # Simulated translation
                simulated = f"[{target_lang}] {source_text}"
                record.complete(simulated, quality_score=0.5)
                self._translation_cache[cache_key] = simulated

        self._translations[record.id] = record
        return record

    def get_translation(self, translation_id: str) -> TranslationRecord | None:
        return self._translations.get(translation_id)

    def list_translations(
        self,
        source_lang: str | None = None,
        target_lang: str | None = None,
        status: str | None = None,
    ) -> list[TranslationRecord]:
        records = list(self._translations.values())
        if source_lang:
            records = [r for r in records if r.source_lang == source_lang]
        if target_lang:
            records = [r for r in records if r.target_lang == target_lang]
        if status:
            records = [r for r in records if r.status == status]
        return records

    def batch_translate(
        self,
        texts: list[str],
        source_lang: str,
        target_lang: str,
    ) -> list[TranslationRecord]:
        """Translate a batch of texts."""
        return [self.request_translation(text, source_lang, target_lang) for text in texts]

    def normalize_entity_name(self, name: str, lang: str) -> str:
        """Normalize an entity name for cross-language matching."""
        # Simple normalization: lowercase, strip, remove diacritics placeholder
        normalized = name.strip().lower()
        # In Layer B, this would use proper transliteration/diacritics removal
        return normalized

    def cross_language_match(
        self,
        name_a: str,
        lang_a: str,
        name_b: str,
        lang_b: str,
    ) -> float:
        """Calculate cross-language entity match score (0-1)."""
        norm_a = self.normalize_entity_name(name_a, lang_a)
        norm_b = self.normalize_entity_name(name_b, lang_b)

        if norm_a == norm_b:
            return 1.0

        # Simple similarity: character overlap
        set_a = set(norm_a)
        set_b = set(norm_b)
        if not set_a or not set_b:
            return 0.0
        overlap = len(set_a & set_b)
        union = len(set_a | set_b)
        return round(overlap / union, 4) if union > 0 else 0.0

    def get_supported_languages(self) -> list[str]:
        """Get list of supported language codes."""
        return [lang.value for lang in SupportedLanguage]

    def is_language_supported(self, lang_code: str) -> bool:
        return lang_code in [lang.value for lang in SupportedLanguage]

    def get_summary(self) -> dict[str, Any]:
        """Get multilingual service summary."""
        records = list(self._translations.values())
        return {
            "total_translations": len(records),
            "cache_hits": sum(1 for r in records if r.status == TranslationStatus.CACHE_HIT.value),
            "translated": sum(1 for r in records if r.status == TranslationStatus.TRANSLATED.value),
            "supported_languages": len(SupportedLanguage),
            "by_target_lang": self._count_by_target(),
        }

    def _count_by_target(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for r in self._translations.values():
            counts[r.target_lang] = counts.get(r.target_lang, 0) + 1
        return counts

    @property
    def translation_count(self) -> int:
        return len(self._translations)

    @property
    def cache_size(self) -> int:
        return len(self._translation_cache)
