"""Definição do fluxo LangGraph do agente Q&A.

Aqui mora o StateGraph que orquestra os nós: recuperar chunks,
montar o prompt, chamar o LLM via LiteLLM, parsear citações e validar
que toda afirmação tem fonte. Implementação na Fase 1.
"""
