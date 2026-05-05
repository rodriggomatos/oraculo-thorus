"use client";

import { useEffect, useRef } from "react";
import { FolderOpen, ListTodo, Search } from "lucide-react";
import { InputArea } from "./chat/InputArea";
import { CreateDriveFolderButton } from "./chat/CreateDriveFolderButton";
import { CreateLdpSheetButton } from "./chat/CreateLdpSheetButton";
import { FlowDecisionBar } from "./chat/FlowDecisionBar";
import { NumberConfirmBar } from "./chat/NumberConfirmBar";
import { Message as MessageComponent } from "./Message";
import { ThinkingIndicator } from "./ThinkingIndicator";
import { MetadataForm } from "@/features/create-project/MetadataForm";
import { useUserPermissions } from "@/features/create-project/hooks/useUserPermissions";
import { useCreateProjectFlow } from "@/features/create-project/hooks/useCreateProjectFlow";
import type { CreateProjectState } from "@/features/create-project/types";
import type { Message, ThreadAgentState } from "@/lib/types";


type Props = {
  threadId: string | null;
  messages: Message[];
  agentState: ThreadAgentState | null;
  isLoading: boolean;
  onSend: (content: string) => Promise<void>;
  onAppendUser: (content: string) => void;
  onAppendAssistant: (content: string) => void;
  onAgentState: (state: ThreadAgentState | null) => void;
};


function asFlowState(agent: ThreadAgentState | null): CreateProjectState | null {
  // Storage trata o agent state como opaco; aqui fazemos o cast pra ler como
  // CreateProjectState. Não há validação de runtime — se algum dia o schema do
  // reducer mudar de forma incompatível, há que purgar localStorage do user.
  return (agent as CreateProjectState | null) ?? null;
}


type Suggestion = {
  icon: React.ReactNode;
  label: string;
  prompt: string;
};


const SUGGESTIONS: Suggestion[] = [
  {
    icon: <FolderOpen className="h-4 w-4 text-[var(--sidebar-text-muted)]" />,
    label: "Listar projetos",
    prompt: "Quais projetos temos cadastrados?",
  },
  {
    icon: <Search className="h-4 w-4 text-[var(--sidebar-text-muted)]" />,
    label: "Buscar definição",
    prompt: "Qual o material da tubulação de gás @26002?",
  },
  {
    icon: <ListTodo className="h-4 w-4 text-[var(--sidebar-text-muted)]" />,
    label: "Definições pendentes",
    prompt: "Quais definições estão pendentes em @26002?",
  },
];


export function ChatWindow({
  threadId,
  messages,
  agentState,
  isLoading,
  onSend,
  onAppendUser,
  onAppendAssistant,
  onAgentState,
}: Props): React.ReactElement {
  const scrollRef = useRef<HTMLDivElement>(null);
  const { canCreateProject } = useUserPermissions();

  const flow = useCreateProjectFlow({
    onAssistantMessage: onAppendAssistant,
    onUserMessage: onAppendUser,
    initialState: asFlowState(agentState),
  });

  // Ref guarda o estado fresh do flow sem entrar em deps do useEffect — assim
  // o efeito de hidratação não refira ao mudar de step.
  const flowIsRunningRef = useRef(flow.isRunning);
  flowIsRunningRef.current = flow.isRunning;

  const flowHydrate = flow.hydrate;
  useEffect(() => {
    // Thread mudou OU agentState mudou. Dois cenários distintos:
    //   1. Switch externo (sidebar): flow está idle/success/error → hidrata
    //      pra restaurar o estado da nova conversa.
    //   2. Append interno do flow (acabou de criar threadId pra persistir a
    //      primeira mensagem do agente): flow está em running step. Hidratar
    //      aqui resetaria o reducer pra idle e abortaria o flow no meio.
    if (flowIsRunningRef.current) return;
    flowHydrate(asFlowState(agentState));
  }, [threadId, agentState, flowHydrate]);

  // Persiste o reducer state inteiro toda vez que muda — restaura UI completa
  // (step intermediário + dados parciais) quando reabrir thread.
  useEffect(() => {
    onAgentState(flow.state.step === "idle" ? null : flow.state);
  }, [flow.state, onAgentState]);

  const driveFolderId = flow.state.finalResult?.driveFolderId ?? null;

  useEffect(() => {
    if (!scrollRef.current) return;
    scrollRef.current.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages, isLoading]);

  const handleSend = async (content: string): Promise<void> => {
    if (flow.isActive) {
      await flow.submitUserText(content);
      return;
    }
    await onSend(content);
  };

  const handleFileAccepted = async (file: File): Promise<void> => {
    if (!flow.isActive) {
      onAppendAssistant(
        "Recebi o arquivo, mas não há fluxo ativo aguardando upload. Inicie 'Criar projeto novo' no menu `+` → Agente.",
      );
      return;
    }
    await flow.submitFile(file);
  };

  const handleStartCreateProject = (): void => {
    void flow.start();
  };

  const acceptingFiles = flow.isActive;

  const showNumberBar =
    flow.state.step === "awaiting_number_confirmation" &&
    typeof flow.state.suggestedNumber === "number";
  const showDecisionBar = flow.state.step === "awaiting_validation_decision";
  const showMetadataForm =
    flow.state.step === "awaiting_metadata" || flow.state.step === "creating";
  const showDriveFolderButton =
    flow.state.step === "success" && flow.state.finalResult !== undefined;
  const isParsingSheet = flow.state.step === "parsing_spreadsheet";
  const isCreating = flow.state.step === "creating";

  const isEmpty = messages.length === 0 && !isLoading;

  const inputArea = (
    <InputArea
      onSend={handleSend}
      onFileAccepted={handleFileAccepted}
      onCreateProject={handleStartCreateProject}
      canCreateProject={canCreateProject}
      acceptingFiles={acceptingFiles}
      isLoading={isLoading}
      parsing={isParsingSheet}
    />
  );

  const fillSuggestion = (prompt: string): void => {
    void onSend(prompt);
  };

  return (
    <main className="flex-1 flex flex-col bg-[var(--main-bg)] text-[var(--sidebar-text)] overflow-hidden">
      {isEmpty ? (
        <div className="flex-1 flex items-center justify-center px-6">
          <div className="w-full max-w-2xl flex flex-col items-center gap-8">
            <h1 className="text-3xl font-medium tracking-tight text-[var(--sidebar-text)]">
              Como posso ajudar?
            </h1>
            <div className="w-full">{inputArea}</div>
            <div className="flex flex-wrap items-center justify-center gap-2">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s.label}
                  type="button"
                  onClick={() => fillSuggestion(s.prompt)}
                  className="flex items-center gap-2 rounded-full border border-[var(--sidebar-border)] px-3.5 py-2 text-sm text-[var(--sidebar-text)] hover:bg-[var(--sidebar-hover)] transition-colors"
                >
                  {s.icon}
                  <span>{s.label}</span>
                </button>
              ))}
            </div>
          </div>
        </div>
      ) : (
        <>
          <div ref={scrollRef} className="flex-1 overflow-y-auto px-6 pt-6 pb-4">
            <div className="max-w-3xl mx-auto space-y-4">
              {messages.map((m, i) => (
                <MessageComponent key={i} message={m} />
              ))}
              {isLoading && <ThinkingIndicator />}
              {showNumberBar && typeof flow.state.suggestedNumber === "number" ? (
                <div className="flex justify-start">
                  <div className="px-1">
                    <NumberConfirmBar
                      suggested={flow.state.suggestedNumber}
                      onConfirm={(n) => flow.confirmNumber(n)}
                    />
                  </div>
                </div>
              ) : null}
              {showDecisionBar ? (
                <div className="flex justify-start">
                  <div className="px-1">
                    <FlowDecisionBar
                      onContinue={() => void flow.decideContinue()}
                      onFix={() => flow.decideFix()}
                    />
                  </div>
                </div>
              ) : null}
              {showMetadataForm ? (
                <div className="flex justify-start">
                  <div className="px-1">
                    <MetadataForm
                      onConfirm={(m, cityId) => void flow.submitMetadata(m, cityId)}
                      loading={isCreating}
                      errorMessage={
                        flow.state.step === "awaiting_metadata"
                          ? flow.state.errorMessage ?? null
                          : null
                      }
                    />
                  </div>
                </div>
              ) : null}
              {showDriveFolderButton && flow.state.finalResult ? (
                <div className="flex flex-col gap-2 items-start">
                  <div className="px-1">
                    <CreateDriveFolderButton
                      projectId={flow.state.finalResult.projectId}
                      initialFolderId={flow.state.finalResult.driveFolderId}
                      onCreated={(id) =>
                        flow.patchFinalResult({ driveFolderId: id })
                      }
                    />
                  </div>
                  <div className="px-1">
                    <CreateLdpSheetButton
                      projectId={flow.state.finalResult.projectId}
                      initialSheetsId={flow.state.finalResult.ldpSheetsId}
                      disabled={!driveFolderId}
                      disabledReason={
                        !driveFolderId
                          ? "Crie a pasta no Drive primeiro."
                          : undefined
                      }
                      onCreated={(sheetsId) =>
                        flow.patchFinalResult({ ldpSheetsId: sheetsId })
                      }
                    />
                  </div>
                </div>
              ) : null}
            </div>
          </div>
          <div className="px-6 pb-4">
            <div className="max-w-3xl mx-auto">{inputArea}</div>
          </div>
        </>
      )}
    </main>
  );
}
