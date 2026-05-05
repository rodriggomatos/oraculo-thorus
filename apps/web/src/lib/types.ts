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

export type ThreadAgentResult = {
  projectId: string;
  projectNumber: number;
  projectName: string;
  driveFolderId: string | null;
  ldpSheetsId: string | null;
  definitionsCount: number;
};


export type Thread = {
  thread_id: string;
  titulo: string;
  created_at: string;
  messages: Message[];
  agent_result?: ThreadAgentResult | null;
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
