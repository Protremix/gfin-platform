# MODULE 21 — Local AI

**Status:** IN_PROGRESS
**Started:** 2026-08-26
**Spec by:** GPT Luna (GFIN-CEA)

---

## 1. Purpose

Module 21 implements self-hosted/local AI capabilities for GFIN. Per the
GFIN AI Policy §7:

- **PUBLIC / COMMUNITY** data → External AI (OpenAI) or Local AI
- **RESTRICTED** data → Local AI preferred; external only if authorized
- **LAW_ENFORCEMENT / HIGHLY_RESTRICTED** → Local AI only (within jurisdiction)

Local AI is also the **fallback** when OpenAI is unavailable (Constitution: "OpenAI
must never be the sole operational dependency").

### Capabilities:
1. **Text Classification** — fraud type, severity, spam detection
2. **Embeddings** — similarity search, clustering, dedup
3. **OCR** — extract text from images/screenshots
4. **Language Detection** — detect language for multilingual processing

---

## 2. Architecture — Two Layers

### Layer A (In-Memory MVP — Sandbox)
- `LocalAIAdapter` — mock local model adapter with deterministic responses
- `EmbeddingService` — mock embeddings (hash-based vectors)
- `ClassificationService` — rule-based classification (keyword matching)
- `OCRService` — mock OCR (returns placeholder text)
- `LanguageDetector` — heuristic language detection (character set analysis)
- `LocalAIGateway` — integrates with Model Gateway for fallback routing

### Layer B (Production — REQUIRES EXTERNAL INFRASTRUCTURE)
- Real local models (Llama 3, Mistral, etc.) via vLLM/Ollama
- Sentence-transformer embeddings (all-MiniLM-L6-v2)
- Tesseract OCR / EasyOCR
- fastText language detection
- GPU inference hardware
- Model versioning and evaluation pipeline

---

## 3. Key Components

### 3.1 LocalAIAdapter
- `classify(text, model)` → classification result (label + confidence)
- `embed(text, model)` → embedding vector
- `ocr(image_bytes, model)` → extracted text
- `detect_language(text)` → language code + confidence
- `health_check()` → model availability status
- `list_models()` → available local models

### 3.2 EmbeddingService
- `embed_text(text)` → vector (mock: hash-based)
- `embed_batch(texts)` → list of vectors
- `cosine_similarity(v1, v2)` → float
- `find_similar(query, vectors, top_k)` → ranked results

### 3.3 ClassificationService
- `classify_fraud_type(text)` → fraud type label + confidence
- `classify_severity(text)` → severity label
- `detect_spam(text)` → bool + confidence
- Rule-based with keyword dictionaries (Layer A)

### 3.4 OCRService
- `extract_text(image_bytes)` → extracted text (mock)
- `extract_text_from_file(file_path)` → extracted text
- Supported formats: PNG, JPG, PDF (Layer B)

### 3.5 LanguageDetector
- `detect(text)` → language code (ISO 639-1) + confidence
- Heuristic: character set analysis, common word matching
- Supports: EN, ES, FR, DE, RU, ZH, AR, PT, IT, JA

### 3.6 LocalAIGateway
- `route(request, classification)` → LocalAI or OpenAI
  - Classification-aware routing per AI Policy
  - RESTRICTED+ → Local AI
  - PUBLIC/COMMUNITY → can use either (default: OpenAI for advanced, Local for basic)
- `fallback(request)` → if OpenAI fails, route to Local AI
- Integrates with Module 19 (Model Gateway)

---

## 4. Classification-Aware Routing

```
Request arrives with data classification:
  PUBLIC        → OpenAI (primary), Local AI (fallback)
  COMMUNITY     → OpenAI (minimized), Local AI (fallback)
  RESTRICTED    → Local AI (primary)
  LAW_ENFORCEMENT → Local AI (only)
  HIGHLY_RESTRICTED → Local AI (only, isolated)
```

---

## 5. Acceptance Criteria

1. LocalAIAdapter returns classification results with label + confidence
2. EmbeddingService produces vectors and computes cosine similarity
3. ClassificationService classifies fraud type, severity, spam
4. OCRService extracts text (mock in Layer A)
5. LanguageDetector detects 10+ languages
6. LocalAIGateway routes by data classification
7. LocalAIGateway falls back to Local AI when OpenAI unavailable
8. HIGHLY_RESTRICTED data never routes to external AI
9. Health check reports model availability
10. Events published for AI operations

---

## 6. Test Plan

- Unit: LocalAIAdapter (classify, embed, ocr, detect_language, health_check)
- Unit: EmbeddingService (embed, batch, similarity, find_similar)
- Unit: ClassificationService (fraud type, severity, spam)
- Unit: OCRService (extract_text, file)
- Unit: LanguageDetector (10+ languages)
- Unit: LocalAIGateway (routing, fallback, classification enforcement)
- Integration: full classification-aware routing pipeline

---

## 7. Dependencies

- Module 19 (Model Gateway) — provider abstraction, fallback
- Module 20 (OpenAI) — primary AI provider
- Module 03 (Core Data Model) — data classification
