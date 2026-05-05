export type Citation = {
  item_code: string;
  disciplina: string;
  tipo: string | null;
  node_id: string;
  score: number;
};

export type Message = {
  role: "user" | "assistant";
  content: string;
  sources?: Citation[];
  timestamp: string;
};

/**
 * Agent state persistido por thread. Mantém o tipo opaco aqui pra não criar
 * dependência circular com `features/create-project`. O caller é responsável
 * pelo formato — hoje é `CreateProjectState` (reducer state inteiro). Inclui
 * step intermediário, números/URLs já confirmados, validation result e
 * metadata parcial — tudo necessário pra reconstruir a UI ao reabrir.
 *
 * TODO sprint futura: TTL pra purgar flows abandonados (>30 dias) que ficam
 * no localStorage indefinidamente.
 */
export type ThreadAgentState = unknown;


export type Thread = {
  thread_id: string;
  titulo: string;
  created_at: string;
  messages: Message[];
  agent_state?: ThreadAgentState | null;
};

export type QueryRequest = {
  question: string;
  thread_id?: string;
  project_number?: number;
  top_k?: number;
};

export type QueryResponse = {
  answer: string;
  sources: Citation[];
  found_relevant: boolean;
  thread_id: string;
};

export type ProjectDTO = {
  project_number: number;
  name: string;
  client: string | null;
};
