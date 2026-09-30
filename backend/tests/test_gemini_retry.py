from types import SimpleNamespace

import pytest

from google.genai.errors import ClientError, ServerError

from app.services import gemini_service
from app.services.gemini_service import GeminiService


class RecordingEmbeddingModels:
    def __init__(self, fail_on_call=None, embedding_count_adjustment=0):
        self.calls = []
        self.fail_on_call = fail_on_call
        self.embedding_count_adjustment = embedding_count_adjustment
        self.next_embedding_index = 0

    def embed_content(self, model, contents):
        self.calls.append((model, list(contents)))
        if self.fail_on_call == len(self.calls):
            raise ServerError(400, {"error": {"message": "batch failed"}})
        result_count = max(0, len(contents) + self.embedding_count_adjustment)
        embeddings = [
            SimpleNamespace(values=[float(index), 1.0])
            for index in range(self.next_embedding_index, self.next_embedding_index + result_count)
        ]
        self.next_embedding_index += result_count
        return SimpleNamespace(embeddings=embeddings)


@pytest.mark.parametrize(
    ("input_count", "expected_batch_sizes"),
    [
        (1, [1]),
        (100, [100]),
        (101, [100, 1]),
        (200, [100, 100]),
        (201, [100, 100, 1]),
    ],
)
def test_embed_documents_batches_at_100_and_preserves_order(monkeypatch, input_count, expected_batch_sizes):
    service = GeminiService()
    models = RecordingEmbeddingModels()
    service.client = SimpleNamespace(models=models)
    texts = [f"chunk-{index}" for index in range(input_count)]

    embeddings = service.embed_documents(texts)

    assert [len(contents) for _, contents in models.calls] == expected_batch_sizes
    assert all(len(contents) <= 100 for _, contents in models.calls)
    assert [content for _, contents in models.calls for content in contents] == texts
    assert len(embeddings) == len(texts)
    assert embeddings == [[float(index), 1.0] for index in range(input_count)]


def test_embed_documents_rejects_batch_embedding_count_mismatch():
    service = GeminiService()
    service.client = SimpleNamespace(models=RecordingEmbeddingModels(embedding_count_adjustment=-1))

    with pytest.raises(ValueError, match=r"returned 99 embeddings for 100 chunks"):
        service.embed_documents([f"chunk-{index}" for index in range(100)])


def test_embed_documents_surfaces_failure_from_later_batch():
    service = GeminiService()
    models = RecordingEmbeddingModels(fail_on_call=2)
    service.client = SimpleNamespace(models=models)

    with pytest.raises(ServerError, match="batch failed"):
        service.embed_documents([f"chunk-{index}" for index in range(201)])

    assert [len(contents) for _, contents in models.calls] == [100, 100]


def test_transient_api_error_retries_then_returns_result(monkeypatch):
    service = GeminiService()
    attempts = 0
    delays = []

    def operation():
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise ServerError(503, {"error": {"message": "temporarily unavailable"}})
        return "real response"

    monkeypatch.setattr(gemini_service.time, "sleep", delays.append)
    monkeypatch.setattr(gemini_service.random, "uniform", lambda low, high: low)

    assert service._with_transient_retry(operation) == "real response"
    assert attempts == 3
    assert delays == [0.5, 1.0]


def test_transient_api_error_is_raised_after_retry_limit(monkeypatch):
    service = GeminiService()
    attempts = 0

    def operation():
        nonlocal attempts
        attempts += 1
        raise ServerError(503, {"error": {"message": "temporarily unavailable"}})

    monkeypatch.setattr(gemini_service.time, "sleep", lambda _: None)

    with pytest.raises(ServerError) as raised:
        service._with_transient_retry(operation)

    assert raised.value.code == 503
    assert attempts == 3


def test_permanent_api_error_is_not_retried(monkeypatch):
    service = GeminiService()
    attempts = 0
    monkeypatch.setattr(gemini_service.time, "sleep", lambda _: pytest.fail("unexpected retry"))

    def operation():
        nonlocal attempts
        attempts += 1
        raise ClientError(400, {"error": {"message": "invalid request"}})

    with pytest.raises(ClientError):
        service._with_transient_retry(operation)

    assert attempts == 1


def test_retry_uses_server_retry_info_delay(monkeypatch):
    service = GeminiService()
    attempts = 0
    delays = []

    def operation():
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise ServerError(
                429,
                {
                    "error": {
                        "message": "rate limited",
                        "details": [
                            {
                                "@type": "type.googleapis.com/google.rpc.RetryInfo",
                                "retryDelay": "2.5s",
                            }
                        ],
                    }
                },
            )
        return "retried response"

    monkeypatch.setattr(gemini_service.time, "sleep", delays.append)
    monkeypatch.setattr(gemini_service.random, "uniform", lambda low, high: low)

    assert service._with_transient_retry(operation) == "retried response"
    assert attempts == 2
    assert delays == [2.5]