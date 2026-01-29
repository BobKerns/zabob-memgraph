"""
Embedding generation and management for semantic search.

Provides abstract interface for embedding providers and concrete
implementations for sentence transformers and OpenAI embeddings.
"""

from abc import ABC, abstractmethod
import logging
import numpy as np

logger = logging.getLogger(__name__)


class EmbeddingProvider(ABC):
    """
    Abstract interface for embedding generation.

    Providers convert text to dense vector representations for
    semantic similarity search.
    """

    @abstractmethod
    def generate(self, text: str) -> np.ndarray:
        """
        Generate embedding vector for a single text.

        Args:
            text: Input text to embed

        Returns:
            Embedding vector as numpy array
        """
        pass

    @abstractmethod
    def batch_generate(self, texts: list[str]) -> list[np.ndarray]:
        """
        Generate embeddings for multiple texts efficiently.

        Args:
            texts: List of input texts

        Returns:
            List of embedding vectors
        """
        pass

    @property
    @abstractmethod
    def dimensions(self) -> int:
        """Embedding vector dimensions."""
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Model identifier string."""
        pass


class SentenceTransformerProvider(EmbeddingProvider):
    """
    Embedding provider using sentence-transformers library.

    Runs locally, no API costs. Good default choice for most use cases.
    """

    _model_name: str
    _dimensions: int

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize with a sentence transformer model.

        Args:
            model_name: HuggingFace model identifier
                Default: all-MiniLM-L6-v2 (384 dims, ~80MB, good quality)
        """
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            raise ImportError(
                "sentence-transformers not installed. "
                "Install with: uv add sentence-transformers"
            ) from None

        self._model_name = model_name
        logger.info(f"Loading sentence transformer model: {model_name}")
        self.model = SentenceTransformer(model_name)
        dims = self.model.get_sentence_embedding_dimension()
        assert dims is not None, "Model dimensions cannot be None"
        self._dimensions = dims
        logger.info(f"Model loaded: {model_name} ({self._dimensions} dimensions)")

    def generate(self, text: str) -> np.ndarray:
        """Generate embedding for single text."""
        return self.model.encode(text, convert_to_numpy=True)

    def batch_generate(self, texts: list[str]) -> list[np.ndarray]:
        """Generate embeddings in batch for efficiency."""
        embeddings = self.model.encode(texts, convert_to_numpy=True)
        return [embeddings[i] for i in range(len(texts))]

    @property
    def dimensions(self) -> int:
        return self._dimensions

    @property
    def model_name(self) -> str:
        return self._model_name


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """
    Embedding provider using OpenAI's embedding API.

    Higher quality than local models but requires API key and has costs.
    """

    _model_name: str
    _dimensions: int

    def __init__(
        self,
        model_name: str = "text-embedding-3-small",
        api_key: str | None = None,
    ):
        """
        Initialize OpenAI embedding provider.

        Args:
            model_name: OpenAI embedding model
                Options: text-embedding-3-small (1536 dims, cheap)
                        text-embedding-3-large (3072 dims, better quality)
            api_key: OpenAI API key (or set OPENAI_API_KEY env var)
        """
        try:
            import openai  # type: ignore[import-not-found]
        except ImportError:
            raise ImportError(
                "openai not installed. "
                "Install with: uv add openai"
            ) from None

        self._model_name = model_name
        self.client = openai.OpenAI(api_key=api_key)

        # Set dimensions based on model
        if "3-small" in model_name:
            self._dimensions = 1536
        elif "3-large" in model_name:
            self._dimensions = 3072
        else:
            self._dimensions = 1536  # Default

        logger.info(f"Initialized OpenAI embeddings: {model_name}")

    def generate(self, text: str) -> np.ndarray:
        """Generate embedding via OpenAI API."""
        try:
            response = self.client.embeddings.create(
                model=self._model_name,
                input=text,
            )
            return np.array(response.data[0].embedding)
        except Exception as e:
            logger.error(f"OpenAI embedding generation failed: {e}")
            raise RuntimeError(f"OpenAI embedding generation failed: {e}") from e

    def batch_generate(self, texts: list[str]) -> list[np.ndarray]:
        """Generate embeddings in batch."""
        try:
            response = self.client.embeddings.create(
                model=self._model_name,
                input=texts,
            )
            return [np.array(data.embedding) for data in response.data]
        except Exception as e:
            logger.error(f"OpenAI batch embedding generation failed: {e}")
            raise RuntimeError(f"OpenAI batch embedding generation failed: {e}") from e

    @property
    def dimensions(self) -> int:
        return self._dimensions

    @property
    def model_name(self) -> str:
        return self._model_name


# Global provider instance
_provider: EmbeddingProvider | None = None


def get_embedding_provider() -> EmbeddingProvider:
    """
    Get the configured embedding provider.

    Returns the global provider instance, initializing with defaults
    if not yet configured.
    """
    global _provider
    if _provider is None:
        logger.info("No embedding provider configured, using default")
        _provider = SentenceTransformerProvider()
    return _provider


def set_embedding_provider(provider: EmbeddingProvider | None) -> None:
    """
    Set the global embedding provider.

    Args:
        provider: Configured embedding provider instance (or None to clear)
    """
    global _provider
    _provider = provider
    if provider is not None:
        logger.info(f"Set embedding provider: {provider.model_name}")
    else:
        logger.info("Cleared embedding provider")


def configure_from_dict(config: dict[str, str | None]) -> None:
    """
    Configure embedding provider from configuration dictionary.

    Args:
        config: Configuration dict with keys:
            - provider: "sentence-transformers" or "openai"
            - model: Model name
            - api_key: (OpenAI only) API key
    """
    provider = config.get("provider", "sentence-transformers")
    model = config.get("model")

    provider_instance: EmbeddingProvider
    if provider == "sentence-transformers":
        model = model or "all-MiniLM-L6-v2"
        provider_instance = SentenceTransformerProvider(model_name=model)
    elif provider == "openai":
        model = model or "text-embedding-3-small"
        api_key = config.get("api_key")
        provider_instance = OpenAIEmbeddingProvider(model_name=model, api_key=api_key)
    else:
        raise ValueError(f"Unknown provider type: {provider}")

    set_embedding_provider(provider_instance)
