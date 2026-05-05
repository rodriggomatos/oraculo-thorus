/**
 * Decide quando re-hidratar o useCreateProjectFlow ao receber novos
 * `threadId`/`agentState` em ChatWindow.
 *
 * Há dois caminhos que mudam essas props:
 *
 *   - **Internal append**: o próprio flow chama `appendUserMessage` /
 *     `appendAssistantMessage` no useChat e este gera um `threadId` novo
 *     (estava `null`) pra persistir a primeira mensagem da conversa.
 *     Aqui a hidratação destruiria o flow no meio.
 *
 *   - **External switch**: usuário clica numa thread diferente na sidebar,
 *     usa "Novo chat" ou (na 1ª render) o useChat restaura state do
 *     localStorage. O flow precisa ser remontado pro state da nova
 *     conversa — qualquer step, inclusive `null` (= idle).
 *
 * Distinção: internal append é o único caso em que `prev` era null e
 * `current` é não-null COM o flow em running step. Nos demais casos,
 * sempre re-hidrata.
 */
export function shouldHydrateFlow(args: {
  prevThreadId: string | null;
  currentThreadId: string | null;
  isRunning: boolean;
}): boolean {
  const { prevThreadId, currentThreadId, isRunning } = args;

  // Effect disparou só por mudança de agentState (nosso próprio echo de
  // persistência). threadId não mudou → nenhuma hidratação.
  if (prevThreadId === currentThreadId) return false;

  // Internal append: flow gerou threadId pra sua primeira mensagem. Não
  // clobbar o reducer.
  if (prevThreadId === null && currentThreadId !== null && isRunning) {
    return false;
  }

  // Tudo o mais (switch externo, novo chat, restore inicial): hidrata.
  return true;
}
