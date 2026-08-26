"""Tests for Local AI — Module 21.

Tests cover:
- LocalAIAdapter: classify, embed, ocr, detect_language, health_check
- EmbeddingService: embed, batch, cosine similarity, find_similar
- ClassificationService: fraud type, severity, spam detection
- OCRService: extract_text, file
- LanguageDetector: 10+ languages, character-based and word-based
- LocalAIGateway: routing by classification, fallback, statistics
- Integration: full classification-aware routing pipeline
"""

from unittest.mock import MagicMock

from services.local_ai import (
    ClassificationResult,
    ClassificationService,
    EmbeddingResult,
    EmbeddingService,
    LanguageCode,
    LanguageDetector,
    LanguageResult,
    LocalAIAdapter,
    LocalAIGateway,
    LocalAIModel,
    ModelHealth,
    OCRResult,
    OCRService,
)

# ─── EmbeddingService Tests ───


class TestEmbeddingService:
    def test_embed_text(self):
        svc = EmbeddingService()
        vec = svc.embed_text("hello world")
        assert len(vec) == svc.DIMENSIONS
        assert any(v != 0.0 for v in vec)  # Not all zeros

    def test_embed_empty(self):
        svc = EmbeddingService()
        vec = svc.embed_text("")
        assert len(vec) == svc.DIMENSIONS
        assert all(v == 0.0 for v in vec)

    def test_embed_same_text_same_vector(self):
        svc = EmbeddingService()
        v1 = svc.embed_text("fraud alert")
        v2 = svc.embed_text("fraud alert")
        assert v1 == v2

    def test_embed_different_text_different_vector(self):
        svc = EmbeddingService()
        v1 = svc.embed_text("phishing email")
        v2 = svc.embed_text("crypto scam")
        assert v1 != v2

    def test_embed_normalized(self):
        svc = EmbeddingService()
        vec = svc.embed_text("normalized vector test")
        norm = sum(v * v for v in vec)
        assert abs(norm - 1.0) < 0.01  # L2 normalized

    def test_embed_batch(self):
        svc = EmbeddingService()
        texts = ["hello", "world", "test"]
        vectors = svc.embed_batch(texts)
        assert len(vectors) == 3
        assert all(len(v) == svc.DIMENSIONS for v in vectors)

    def test_cosine_similarity_identical(self):
        svc = EmbeddingService()
        v1 = svc.embed_text("fraud detection")
        sim = svc.cosine_similarity(v1, v1)
        assert abs(sim - 1.0) < 0.01

    def test_cosine_similarity_different(self):
        svc = EmbeddingService()
        v1 = svc.embed_text("phishing email")
        v2 = svc.embed_text("crypto investment")
        sim = svc.cosine_similarity(v1, v2)
        assert sim < 0.99

    def test_cosine_similarity_zero_vectors(self):
        svc = EmbeddingService()
        sim = svc.cosine_similarity([0.0] * 128, [0.0] * 128)
        assert sim == 0.0

    def test_cosine_similarity_different_dimensions(self):
        svc = EmbeddingService()
        sim = svc.cosine_similarity([1.0] * 64, [1.0] * 128)
        assert sim == 0.0

    def test_find_similar(self):
        svc = EmbeddingService()
        query = svc.embed_text("phishing scam")
        vectors = [
            ("doc1", svc.embed_text("phishing email fraud")),
            ("doc2", svc.embed_text("crypto investment")),
            ("doc3", svc.embed_text("phishing attack detected")),
        ]
        results = svc.find_similar(query, vectors, top_k=2)
        assert len(results) == 2
        assert results[0][0] in ("doc1", "doc3")

    def test_custom_dimensions(self):
        svc = EmbeddingService(dimensions=256)
        vec = svc.embed_text("test")
        assert len(vec) == 256


# ─── ClassificationService Tests ───


class TestClassificationService:
    def test_classify_phishing(self):
        svc = ClassificationService()
        result = svc.classify_fraud_type("This is a phishing email asking for credentials")
        assert result.label == "phishing"
        assert result.confidence > 0.0

    def test_classify_investment_fraud(self):
        svc = ClassificationService()
        result = svc.classify_fraud_type(
            "Double your bitcoin with guaranteed return crypto trading"
        )
        assert result.label == "investment_fraud"

    def test_classify_tech_support(self):
        svc = ClassificationService()
        result = svc.classify_fraud_type(
            "Your computer is infected call microsoft tech support virus"
        )
        assert result.label == "tech_support_scam"

    def test_classify_unknown(self):
        svc = ClassificationService()
        result = svc.classify_fraud_type("Hello, how are you today?")
        assert result.label == "unknown"
        assert result.confidence == 0.0

    def test_classify_severity_critical(self):
        svc = ClassificationService()
        result = svc.classify_severity("They stole my life savings from the bank identity theft")
        assert result.label == "CRITICAL"

    def test_classify_severity_high(self):
        svc = ClassificationService()
        result = svc.classify_severity("I lost money to a scam, need to report this fraud")
        assert result.label == "HIGH"

    def test_classify_severity_low(self):
        svc = ClassificationService()
        result = svc.classify_severity("Just an annoying spam message, minor issue")
        assert result.label in ("LOW", "MEDIUM")

    def test_classify_severity_default(self):
        svc = ClassificationService()
        result = svc.classify_severity("Hello world")
        assert result.label == "LOW"
        assert result.confidence == 0.5

    def test_detect_spam_true(self):
        svc = ClassificationService()
        text = "Buy now! Limited offer! Click here! Act now! Winner!"
        is_spam, confidence = svc.detect_spam(text)
        assert is_spam is True
        assert confidence > 0.5

    def test_detect_spam_false(self):
        svc = ClassificationService()
        text = "I would like to report a suspicious email I received."
        is_spam, _ = svc.detect_spam(text)
        assert is_spam is False

    def test_classify_result_has_model(self):
        svc = ClassificationService()
        result = svc.classify_fraud_type("phishing test")
        assert result.model == LocalAIModel.CLASSIFIER.value

    def test_classify_result_has_all_scores(self):
        svc = ClassificationService()
        result = svc.classify_fraud_type("phishing email credential")
        assert len(result.all_scores) > 0


# ─── OCRService Tests ───


class TestOCRService:
    def test_extract_text(self):
        svc = OCRService()
        result = svc.extract_text(b"fake image bytes")
        assert isinstance(result, OCRResult)
        assert result.model == LocalAIModel.OCR.value

    def test_extract_text_from_file(self, tmp_path):
        svc = OCRService()
        f = tmp_path / "test.png"
        f.write_bytes(b"fake image")
        result = svc.extract_text_from_file(str(f))
        assert isinstance(result, OCRResult)

    def test_extract_text_from_nonexistent_file(self):
        svc = OCRService()
        result = svc.extract_text_from_file("/nonexistent/path.png")
        assert result.text == ""
        assert result.pages == 0


# ─── LanguageDetector Tests ───


class TestLanguageDetector:
    def test_detect_english(self):
        det = LanguageDetector()
        result = det.detect("The quick brown fox jumps over the lazy dog")
        assert result.language == LanguageCode.EN.value

    def test_detect_spanish(self):
        det = LanguageDetector()
        result = det.detect("El gato es muy bonito y está en la casa")
        assert result.language == LanguageCode.ES.value

    def test_detect_french(self):
        det = LanguageDetector()
        result = det.detect("Le chat est très mignon et est dans la maison")
        assert result.language == LanguageCode.FR.value

    def test_detect_german(self):
        det = LanguageDetector()
        result = det.detect("Der Hund ist sehr groß und läuft schnell")
        assert result.language == LanguageCode.DE.value

    def test_detect_russian(self):
        det = LanguageDetector()
        result = det.detect("Это текст на русском языке для проверки")
        assert result.language == LanguageCode.RU.value

    def test_detect_chinese(self):
        det = LanguageDetector()
        result = det.detect("这是一个中文文本用于测试")
        assert result.language == LanguageCode.ZH.value

    def test_detect_arabic(self):
        det = LanguageDetector()
        result = det.detect("هذا نص باللغة العربية للاختبار")
        assert result.language == LanguageCode.AR.value

    def test_detect_portuguese(self):
        det = LanguageDetector()
        result = det.detect("O gato é muito bonito e está na casa")
        assert result.language == LanguageCode.PT.value

    def test_detect_italian(self):
        det = LanguageDetector()
        result = det.detect("Il gatto è molto carino e è in casa")
        assert result.language == LanguageCode.IT.value

    def test_detect_japanese(self):
        det = LanguageDetector()
        result = det.detect("これはテスト用の日本語テキストです")
        assert result.language == LanguageCode.JA.value

    def test_detect_empty(self):
        det = LanguageDetector()
        result = det.detect("")
        assert result.language == LanguageCode.UNKNOWN.value
        assert result.confidence == 0.0

    def test_detect_has_alternatives(self):
        det = LanguageDetector()
        result = det.detect("The cat is on the table and el perro")
        # Should have alternatives for at least EN
        assert len(result.alternatives) > 0

    def test_detect_result_has_model(self):
        det = LanguageDetector()
        result = det.detect("Hello world")
        assert result.model == LocalAIModel.LANGUAGE.value


# ─── LocalAIAdapter Tests ───


class TestLocalAIAdapter:
    def test_classify(self):
        adapter = LocalAIAdapter()
        result = adapter.classify("phishing email credential theft")
        assert isinstance(result, ClassificationResult)

    def test_classify_severity(self):
        adapter = LocalAIAdapter()
        result = adapter.classify_severity("stolen bank account life savings")
        assert isinstance(result, ClassificationResult)

    def test_detect_spam(self):
        adapter = LocalAIAdapter()
        is_spam, conf = adapter.detect_spam("Buy now! Limited offer! Click here! Act now! Winner!")
        assert is_spam is True

    def test_embed(self):
        adapter = LocalAIAdapter()
        result = adapter.embed("test text")
        assert isinstance(result, EmbeddingResult)
        assert result.dimensions > 0

    def test_embed_batch(self):
        adapter = LocalAIAdapter()
        results = adapter.embed_batch(["hello", "world"])
        assert len(results) == 2

    def test_ocr(self):
        adapter = LocalAIAdapter()
        result = adapter.ocr(b"image bytes")
        assert isinstance(result, OCRResult)

    def test_detect_language(self):
        adapter = LocalAIAdapter()
        result = adapter.detect_language("Hello world test")
        assert isinstance(result, LanguageResult)

    def test_health_check(self):
        adapter = LocalAIAdapter()
        health = adapter.health_check()
        assert len(health) == 4
        assert all(h == ModelHealth.HEALTHY.value for h in health.values())

    def test_list_models(self):
        adapter = LocalAIAdapter()
        models = adapter.list_models()
        assert len(models) == 4
        assert all(m.loaded for m in models)


# ─── LocalAIGateway Tests ───


class TestLocalAIGateway:
    def test_route_public_to_openai(self):
        mock_openai = MagicMock()
        mock_openai.process = MagicMock(return_value={"classification": "test"})
        gw = LocalAIGateway(openai_gateway=mock_openai)
        result = gw.route({"operation": "classify", "text": "test"}, classification="PUBLIC")
        assert result["provider"] == "openai"

    def test_route_restricted_to_local(self):
        gw = LocalAIGateway()
        result = gw.route(
            {"operation": "classify", "text": "phishing"}, classification="RESTRICTED"
        )
        assert result["provider"] == "local"

    def test_route_law_enforcement_to_local(self):
        gw = LocalAIGateway()
        result = gw.route(
            {"operation": "classify", "text": "fraud"}, classification="LAW_ENFORCEMENT"
        )
        assert result["provider"] == "local"

    def test_route_highly_restricted_to_local(self):
        gw = LocalAIGateway()
        result = gw.route(
            {"operation": "classify", "text": "data"}, classification="HIGHLY_RESTRICTED"
        )
        assert result["provider"] == "local"

    def test_route_no_openai_fallback(self):
        gw = LocalAIGateway()  # No openai_gateway
        result = gw.route({"operation": "classify", "text": "test"}, classification="PUBLIC")
        assert result["provider"] == "local"

    def test_fallback_on_openai_error(self):
        mock_openai = MagicMock()
        mock_openai.process = MagicMock(side_effect=Exception("OpenAI unavailable"))
        gw = LocalAIGateway(openai_gateway=mock_openai)
        result = gw.route({"operation": "classify", "text": "test"}, classification="PUBLIC")
        assert result["provider"] == "local"

    def test_fallback_increments_counter(self):
        mock_openai = MagicMock()
        mock_openai.process = MagicMock(side_effect=Exception("fail"))
        gw = LocalAIGateway(openai_gateway=mock_openai)
        gw.route({"operation": "classify", "text": "test"}, classification="PUBLIC")
        assert gw.statistics["fallbacks"] == 1

    def test_fallback_event_published(self):
        mock_openai = MagicMock()
        mock_openai.process = MagicMock(side_effect=Exception("fail"))
        mock_event_bus = MagicMock()
        gw = LocalAIGateway(openai_gateway=mock_openai, event_bus=mock_event_bus)
        gw.route({"operation": "classify", "text": "test"}, classification="PUBLIC")
        mock_event_bus.publish.assert_called()
        assert mock_event_bus.publish.call_args.kwargs["topic"] == "ai.fallback"

    def test_statistics(self):
        gw = LocalAIGateway()
        gw.route({"operation": "classify", "text": "test"}, classification="PUBLIC")
        gw.route({"operation": "classify", "text": "test"}, classification="RESTRICTED")
        stats = gw.statistics
        assert stats["total"] == 2
        assert (
            stats["local"] == 2
        )  # Both go to local (PUBLIC falls back, RESTRICTED routes directly)
        assert stats["openai"] == 0  # No openai configured
        assert stats["fallbacks"] == 1

    def test_local_adapter_accessible(self):
        gw = LocalAIGateway()
        assert isinstance(gw.local_adapter, LocalAIAdapter)

    def test_route_classify_operation(self):
        gw = LocalAIGateway()
        result = gw.route(
            {"operation": "classify", "text": "phishing email"}, classification="RESTRICTED"
        )
        assert result["provider"] == "local"
        assert result["result"] is not None

    def test_route_embed_operation(self):
        gw = LocalAIGateway()
        result = gw.route({"operation": "embed", "text": "test"}, classification="RESTRICTED")
        assert result["provider"] == "local"
        assert result["result"] is not None

    def test_route_detect_language_operation(self):
        gw = LocalAIGateway()
        result = gw.route(
            {"operation": "detect_language", "text": "Hello world"}, classification="RESTRICTED"
        )
        assert result["provider"] == "local"
        assert result["result"] is not None

    def test_route_unknown_operation(self):
        gw = LocalAIGateway()
        result = gw.route({"operation": "unknown_op", "text": "test"}, classification="RESTRICTED")
        assert result["provider"] == "local"
        assert "error" in result


# ─── Integration Tests ───


class TestIntegrationLocalAI:
    def test_full_classification_pipeline(self):
        """Classify text → detect language → check spam."""
        adapter = LocalAIAdapter()

        text = "I received a phishing email asking for my bank credentials urgently"
        fraud = adapter.classify(text)
        lang = adapter.detect_language(text)
        is_spam, _ = adapter.detect_spam(text)

        assert fraud.label == "phishing"
        assert lang.language == LanguageCode.EN.value
        assert is_spam is False  # Not spam keywords, it's a fraud report

    def test_full_routing_pipeline_restricted(self):
        """Restricted data routes to local AI, never to OpenAI."""
        mock_openai = MagicMock()
        gw = LocalAIGateway(openai_gateway=mock_openai)

        result = gw.route(
            {"operation": "classify", "text": "restricted fraud data"},
            classification="RESTRICTED",
        )
        assert result["provider"] == "local"
        mock_openai.process.assert_not_called()

    def test_full_routing_pipeline_public_with_fallback(self):
        """Public data → OpenAI fails → fallback to local."""
        mock_openai = MagicMock()
        mock_openai.process = MagicMock(side_effect=Exception("unavailable"))
        mock_event_bus = MagicMock()
        gw = LocalAIGateway(openai_gateway=mock_openai, event_bus=mock_event_bus)

        result = gw.route(
            {"operation": "classify", "text": "public data"},
            classification="PUBLIC",
        )
        assert result["provider"] == "local"
        assert gw.statistics["fallbacks"] == 1

    def test_embedding_similarity_pipeline(self):
        """Embed → compute similarity → find similar."""
        adapter = LocalAIAdapter()
        svc = EmbeddingService()

        query_vec = svc.embed_text("phishing scam")
        docs = [
            ("report1", svc.embed_text("phishing email fraud")),
            ("report2", svc.embed_text("crypto trading")),
            ("report3", svc.embed_text("phishing credential theft")),
        ]
        similar = svc.find_similar(query_vec, docs, top_k=2)
        assert len(similar) == 2
        # All results should have positive similarity
        assert all(sim > 0.0 for _, sim in similar)
