"""Texto rico do chunk + hash de conteúdo."""

import hashlib

from oraculo_ai.ingestion.schema import Definition


def build_chunk_text(definition: Definition) -> str:
    parts: list[str] = []
    if definition.disciplina:
        parts.append(f"Disciplina: {definition.disciplina}")
    if definition.tipo:
        parts.append(f"Tipo: {definition.tipo}")
    if definition.fase:
        parts.append(f"Fase: {definition.fase}")
    parts.append(f"Item {definition.item_code}: {definition.pergunta}")
    if definition.opcao_escolhida:
        parts.append(f"Opção escolhida: {definition.opcao_escolhida}")
    if definition.status:
        parts.append(f"Status: {definition.status}")
    if definition.custo:
        parts.append(f"Custo: {definition.custo}")
    if definition.observacoes:
        parts.append(f"Observações: {definition.observacoes}")
    if definition.informacao_auxiliar:
        parts.append(f"Informação auxiliar: {definition.informacao_auxiliar}")
    if definition.apoio_1:
        parts.append(f"Apoio 1: {definition.apoio_1}")
    if definition.apoio_2:
        parts.append(f"Apoio 2: {definition.apoio_2}")
    parts.append(f"Validado: {'sim' if definition.validado else 'não'}")
    return "\n".join(parts)


def compute_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
