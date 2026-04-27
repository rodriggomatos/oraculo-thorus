"""Interface base pra conectores de fontes de conhecimento.

Cada conector concreto vive em um subdiretório de `ingestion/` e implementa
o contrato `Connector` aqui definido. O fluxo padrão é fetch → normalize →
persist, mas a interface permite implementações customizadas conforme a
fonte.
"""

from abc import ABC, abstractmethod


class Connector(ABC):
    """Contrato pra conectores de fontes de conhecimento.

    Implementações concretas devem normalizar dados externos em
    chunks + metadata + entities e persistir nas tabelas `chunks`
    (pgvector) e — quando aplicável — `entities`/`relations`
    (knowledge graph).
    """

    @abstractmethod
    async def fetch(self, project_id: str) -> None:
        """Busca dados da fonte externa pro projeto indicado."""

    @abstractmethod
    async def normalize(self) -> None:
        """Converte os dados brutos em chunks + metadata + entities."""

    @abstractmethod
    async def persist(self) -> None:
        """Persiste chunks no pgvector e entities no knowledge graph."""
