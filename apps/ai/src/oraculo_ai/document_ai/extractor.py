"""Extractor LDP — Anthropic SDK direto + Instructor pra structured output.

Atenção: este módulo é a única exceção autorizada à diretriz "todo LLM via
LiteLLM" do CLAUDE.md. Razão: structured output multimodal (PDF nativo) com
Pydantic precisa de Instructor + Anthropic direto; LiteLLM não cobre bem.
"""

import base64
import json
import os
from typing import Any

import instructor

from oraculo_ai.core.config import get_settings
from oraculo_ai.document_ai.schemas import ExtractedLDP


_SYSTEM_PROMPT_TEMPLATE = """Você é um agente especializado em mapear documentos de clientes da Thórus Engenharia para a Lista de Definições (LDP) padrão da empresa.

CONTEXTO:
- A Thórus tem 134 itens canônicos em sua LDP, com perguntas, disciplinas, tipos e fases específicos.
- Clientes entregam documentos em formatos diversos com estruturas próprias.
- Sua tarefa: para cada item da LDP Thórus, encontrar a resposta correspondente no(s) documento(s) do cliente.

REGRAS CRÍTICAS:

1. MAPEAMENTO SEMÂNTICO:
   A pergunta do cliente raramente é idêntica à da Thórus. Use compreensão semântica.
   Ex: "Tipo de equipamento de ar" do cliente ≈ "Qual é o tipo de máquina de climatização preferencial..." da Thórus.

2. RESUMO DE TRÊS NÍVEIS quando o cliente dá MAIS detalhes que a LDP comporta:
   - opcao_escolhida: a resposta principal e mais resumida (frase curta)
   - observacoes: detalhes complementares ou nuances que o cliente especificou
   - informacao_auxiliar_extra: especificações técnicas detalhadas (espessuras, alturas, modelos)

3. CONFIANÇA:
   - "alta": cliente respondeu claramente, mapeamento óbvio
   - "media": cliente respondeu parcialmente ou de forma ambígua
   - "baixa": inferência forte, possível erro de mapeamento

4. DEIXE EM BRANCO QUANDO NÃO TIVER:
   - Se cliente não cobre o item Thórus, opcao_escolhida = null
   - NUNCA INVENTE respostas. Melhor deixar vazio.

5. ITEMS_NOT_COVERED:
   Liste os item_codes da Thórus que ficaram totalmente em branco.

6. fonte_no_documento:
   Quando preencher, cite a seção/numeração do documento de origem (ex: "DNA Otus - 1.1.1.2.1") para auditoria.

7. STATUS:
   Padrão "Em análise" para todos os itens. Marque "Validado" apenas se o cliente indicar explicitamente que aquela decisão é definitiva/aprovada/assinada.

SCHEMA THÓRUS (134 itens):
{schema_thorus_json}

DOCUMENTO(S) DO CLIENTE (texto):
{documents_text}

Retorne ExtractedLDP estruturado mapeando os 134 itens. Inclua TODOS os 134 item_codes (com opcao_escolhida=null para os não encontrados)."""


def _build_user_content(
    project_number: int,
    pdf_attachments: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    user_content: list[dict[str, Any]] = list(pdf_attachments)
    user_content.append(
        {
            "type": "text",
            "text": (
                f"Extraia a LDP estruturada para o projeto {project_number}. "
                "Inclua todos os 134 itens do schema (preenchidos ou vazios)."
            ),
        }
    )
    return user_content


async def extract_ldp_from_documents(
    project_number: int,
    documents: list[tuple[str, str, bytes | None]],
    schema_thorus: list[dict[str, Any]],
) -> ExtractedLDP:
    settings = get_settings()

    if not settings.llm_model_smart.startswith("anthropic/"):
        raise RuntimeError(
            f"Document AI exige modelo anthropic/* em LLM_MODEL_SMART, "
            f"recebido: {settings.llm_model_smart}"
        )
    if not settings.anthropic_api_key:
        raise RuntimeError("ANTHROPIC_API_KEY não configurada no .env")

    os.environ["ANTHROPIC_API_KEY"] = settings.anthropic_api_key

    pdf_attachments: list[dict[str, Any]] = []
    text_blocks: list[str] = []
    for filename, content_text, pdf_bytes in documents:
        if pdf_bytes is not None:
            pdf_attachments.append(
                {
                    "type": "document",
                    "source": {
                        "type": "base64",
                        "media_type": "application/pdf",
                        "data": base64.standard_b64encode(pdf_bytes).decode("utf-8"),
                    },
                }
            )
        if content_text:
            text_blocks.append(f"--- {filename} ---\n{content_text}")

    documents_text = "\n\n".join(text_blocks) if text_blocks else "(somente PDFs em anexo)"
    schema_json = json.dumps(schema_thorus, ensure_ascii=False, indent=2)
    system_prompt = _SYSTEM_PROMPT_TEMPLATE.format(
        schema_thorus_json=schema_json,
        documents_text=documents_text,
    )

    client = instructor.from_provider(
        settings.llm_model_smart,
        async_client=True,
        mode=instructor.Mode.ANTHROPIC_TOOLS,
    )

    user_content = _build_user_content(project_number, pdf_attachments)

    result = await client.create(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        response_model=ExtractedLDP,
        max_tokens=8192,
    )

    return result
