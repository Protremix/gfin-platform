"""Tests for Multilingual — Module 29."""

import pytest

from services.multilingual import (
    MultilingualService,
    SupportedLanguage,
    TranslationRecord,
    TranslationStatus,
)


@pytest.fixture
def service():
    return MultilingualService()


class TestLanguageDetection:
    def test_detect_english(self, service):
        result = service.detect_language("the quick brown fox is running")
        assert result.detected_language == SupportedLanguage.EN.value
        assert result.confidence > 0

    def test_detect_empty(self, service):
        result = service.detect_language("")
        assert result.detected_language == SupportedLanguage.EN.value
        assert result.confidence == 0

    def test_detect_with_alternatives(self, service):
        result = service.detect_language("the der die das and is")
        assert len(result.alternatives) >= 1


class TestTranslationRecord:
    def test_complete(self):
        r = TranslationRecord(id="R1", source_text="hello", source_lang="EN", target_lang="DE")
        r.complete("hallo", quality_score=0.9)
        assert r.status == TranslationStatus.TRANSLATED.value
        assert r.translated_text == "hallo"

    def test_fail(self):
        r = TranslationRecord(id="R1", source_text="hello", source_lang="EN", target_lang="DE")
        r.fail()
        assert r.status == TranslationStatus.FAILED.value


class TestMultilingualService:
    def test_request_translation_same_lang(self, service):
        r = service.request_translation("hello", "EN", "EN")
        assert r.translated_text == "hello"
        assert r.quality_score == 1.0

    def test_request_translation_different_lang(self, service):
        r = service.request_translation("hello", "EN", "DE")
        assert r.status == TranslationStatus.TRANSLATED.value
        assert "[DE]" in r.translated_text

    def test_request_translation_cache_hit(self, service):
        service.request_translation("hello", "EN", "DE")
        r2 = service.request_translation("hello", "EN", "DE")
        assert r2.status == TranslationStatus.CACHE_HIT.value

    def test_get_translation(self, service):
        r = service.request_translation("test", "EN", "DE")
        assert service.get_translation(r.id) is not None
        assert service.get_translation("nonexistent") is None

    def test_list_translations(self, service):
        service.request_translation("a", "EN", "DE")
        service.request_translation("b", "EN", "FR")
        assert len(service.list_translations()) == 2
        assert len(service.list_translations(target_lang="DE")) == 1

    def test_list_translations_by_status(self, service):
        service.request_translation("a", "EN", "DE")
        service.request_translation("a", "EN", "DE")  # cache hit
        cache_hits = service.list_translations(status=TranslationStatus.CACHE_HIT.value)
        assert len(cache_hits) == 1

    def test_batch_translate(self, service):
        results = service.batch_translate(["hello", "world"], "EN", "DE")
        assert len(results) == 2

    def test_normalize_entity_name(self, service):
        assert service.normalize_entity_name("  Hello World  ", "EN") == "hello world"

    def test_cross_language_match_exact(self, service):
        score = service.cross_language_match("scam", "EN", "scam", "EN")
        assert score == 1.0

    def test_cross_language_match_partial(self, service):
        score = service.cross_language_match("scammer", "EN", "scam", "EN")
        assert 0 < score < 1

    def test_cross_language_match_different(self, service):
        score = service.cross_language_match("xyz", "EN", "abc", "EN")
        assert score >= 0

    def test_get_supported_languages(self, service):
        langs = service.get_supported_languages()
        assert len(langs) >= 20
        assert "EN" in langs

    def test_is_language_supported(self, service):
        assert service.is_language_supported("EN") is True
        assert service.is_language_supported("XX") is False

    def test_translation_count(self, service):
        service.request_translation("a", "EN", "DE")
        assert service.translation_count == 1

    def test_cache_size(self, service):
        service.request_translation("a", "EN", "DE")
        assert service.cache_size == 1

    def test_get_summary(self, service):
        service.request_translation("a", "EN", "DE")
        service.request_translation("a", "EN", "DE")  # cache hit
        summary = service.get_summary()
        assert summary["total_translations"] == 2
        assert summary["cache_hits"] == 1
        assert summary["supported_languages"] >= 20

    def test_summary_empty(self, service):
        summary = service.get_summary()
        assert summary["total_translations"] == 0
