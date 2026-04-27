# Evals

Aqui ficam as **golden questions** (perguntas com resposta esperada e citação esperada) usadas pra medir a qualidade do agente Q&A do Oráculo.

## Estrutura prevista

- `golden/` — pares pergunta/resposta validados manualmente, agrupados por projeto.
- `runs/` — saídas de execuções de avaliação (timestamp, modelo, métricas).
- `scripts/` — runners que executam o agente contra o conjunto golden.

## Métricas iniciais (Fase 1)

- **Acerto factual** — a resposta bate com a esperada.
- **Citação correta** — a fonte (projeto, aba, linha) está correta.
- **Abstenção** — quando a resposta não está na base, o agente diz "não sei" em vez de inventar.

> Vazio por enquanto. Será populado quando o agente Q&A da Fase 1 estiver rodando ponta-a-ponta.
