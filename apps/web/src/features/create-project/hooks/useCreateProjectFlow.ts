"use client";

import { useCallback, useReducer } from "react";
import {
  createProject,
  parseMetadataFreeText,
  parseSpreadsheet,
  suggestNumber,
} from "../mock";
import type {
  CreateProjectResponse,
  CreateProjectState,
  ProjectMetadata,
  ValidationResult,
} from "../types";


type FlowAction =
  | { type: "RESET" }
  | { type: "START_REQUESTED" }
  | { type: "NUMBER_SUGGESTED"; suggested: number }
  | { type: "NUMBER_CONFIRMED"; confirmed: number }
  | { type: "SPREADSHEET_RECEIVED"; fileName: string; spreadsheetId: string }
  | { type: "PARSING_STARTED" }
  | { type: "VALIDATION_DONE"; result: ValidationResult }
  | { type: "VALIDATION_DECISION_PENDING" }
  | { type: "USER_DECIDED_CONTINUE" }
  | { type: "USER_DECIDED_FIX" }
  | { type: "METADATA_RECEIVED"; metadata: ProjectMetadata }
  | { type: "CREATING" }
  | { type: "CREATED"; result: CreateProjectResponse }
  | { type: "ERROR"; message: string };


const INITIAL_STATE: CreateProjectState = { step: "idle" };


function reducer(
  state: CreateProjectState,
  action: FlowAction,
): CreateProjectState {
  switch (action.type) {
    case "RESET":
      return INITIAL_STATE;
    case "START_REQUESTED":
      return { step: "awaiting_number_confirmation" };
    case "NUMBER_SUGGESTED":
      return { ...state, suggestedNumber: action.suggested };
    case "NUMBER_CONFIRMED":
      return {
        ...state,
        confirmedNumber: action.confirmed,
        step: "awaiting_spreadsheet",
      };
    case "SPREADSHEET_RECEIVED":
      return {
        ...state,
        spreadsheetFileName: action.fileName,
        spreadsheetId: action.spreadsheetId,
        step: "parsing_spreadsheet",
      };
    case "VALIDATION_DONE":
      return {
        ...state,
        validationResult: action.result,
        step: action.result.ok ? "awaiting_metadata" : "awaiting_validation_decision",
      };
    case "USER_DECIDED_CONTINUE":
      return { ...state, step: "awaiting_metadata" };
    case "USER_DECIDED_FIX":
      return { ...state, step: "awaiting_spreadsheet" };
    case "METADATA_RECEIVED":
      return { ...state, metadata: action.metadata, step: "creating" };
    case "CREATED":
      return { ...state, finalResult: action.result, step: "success" };
    case "ERROR":
      return { ...state, errorMessage: action.message, step: "error" };
    default:
      return state;
  }
}


export type FlowMessageEmitter = (content: string) => void;


export interface UseCreateProjectFlowOptions {
  onAssistantMessage: FlowMessageEmitter;
  onUserMessage: FlowMessageEmitter;
}


export interface UseCreateProjectFlowReturn {
  state: CreateProjectState;
  isActive: boolean;
  start: () => Promise<void>;
  submitUserText: (text: string) => Promise<void>;
  submitFile: (file: File) => Promise<void>;
  decideContinue: () => Promise<void>;
  decideFix: () => void;
  reset: () => void;
}


export function useCreateProjectFlow(
  options: UseCreateProjectFlowOptions,
): UseCreateProjectFlowReturn {
  const [state, dispatch] = useReducer(reducer, INITIAL_STATE);
  const { onAssistantMessage, onUserMessage } = options;

  const start = useCallback(async (): Promise<void> => {
    dispatch({ type: "START_REQUESTED" });
    try {
      const { suggested } = await suggestNumber();
      dispatch({ type: "NUMBER_SUGGESTED", suggested });
      onAssistantMessage(
        `Vamos criar um projeto novo. Olhei os projetos cadastrados e sugiro o número **${suggested}**. Confirma esse número ou prefere outro?`,
      );
    } catch (e) {
      const message = e instanceof Error ? e.message : "Falha ao sugerir número";
      dispatch({ type: "ERROR", message });
      onAssistantMessage(`Não consegui sugerir um número agora: ${message}.`);
    }
  }, [onAssistantMessage]);

  const advanceFromNumberConfirmation = useCallback(
    (text: string): void => {
      const numberMatch = text.match(/\b(\d{4,6})\b/);
      const confirmed = numberMatch
        ? Number.parseInt(numberMatch[1], 10)
        : state.suggestedNumber;
      if (typeof confirmed !== "number" || Number.isNaN(confirmed)) {
        onAssistantMessage(
          "Não consegui identificar um número de projeto na sua resposta. Pode confirmar com um número (ex: 26024)?",
        );
        return;
      }
      dispatch({ type: "NUMBER_CONFIRMED", confirmed });
      onAssistantMessage(
        `Perfeito, número **${confirmed}**. Agora me envia a planilha de orçamento — você pode arrastar o arquivo \`.gsheet\` aqui na conversa ou clicar em "Anexar arquivo" no menu \`+\`.`,
      );
    },
    [state.suggestedNumber, onAssistantMessage],
  );

  const advanceFromMetadata = useCallback(
    async (text: string): Promise<void> => {
      const metadata = parseMetadataFreeText(text);
      if (!metadata.cliente && !metadata.empreendimento && !metadata.cidade) {
        onAssistantMessage(
          "Não consegui extrair Cliente, Empreendimento e Cidade da sua resposta. Pode mandar nesse formato?\n\n- Cliente: Acme\n- Empreendimento: Torre A\n- Cidade: Florianópolis",
        );
        return;
      }
      dispatch({ type: "METADATA_RECEIVED", metadata });
      dispatch({ type: "CREATING" });
      try {
        const result = await createProject({
          spreadsheetId: state.spreadsheetId ?? "mock-spreadsheet",
          confirmedNumber: state.confirmedNumber!,
          metadata,
        });
        dispatch({ type: "CREATED", result });
        const valor = result.totalContratado.toLocaleString("pt-BR", {
          minimumFractionDigits: 2,
          maximumFractionDigits: 2,
        });
        onAssistantMessage(
          `✅ Projeto **${result.projectNumber}** criado.\n\n` +
            `- Cliente: ${metadata.cliente || "—"}\n` +
            `- Empreendimento: ${metadata.empreendimento || "—"}\n` +
            `- Cidade: ${metadata.cidade || "—"}\n` +
            `- Total contratado: R$ ${valor} (mock)\n` +
            `- Margem: ${result.margem.toFixed(2)}% (mock)\n\n` +
            `⚠️ A pasta no Drive ainda precisa ser criada manualmente. No próximo sprint isso será automático.`,
        );
      } catch (e) {
        const message = e instanceof Error ? e.message : "Falha ao criar projeto";
        dispatch({ type: "ERROR", message });
        onAssistantMessage(`Não consegui criar o projeto: ${message}.`);
      }
    },
    [state.confirmedNumber, state.spreadsheetId, onAssistantMessage],
  );

  const submitUserText = useCallback(
    async (text: string): Promise<void> => {
      onUserMessage(text);
      switch (state.step) {
        case "awaiting_number_confirmation":
          advanceFromNumberConfirmation(text);
          return;
        case "awaiting_spreadsheet":
          onAssistantMessage(
            "Estou aguardando a planilha — você pode arrastar o arquivo `.gsheet` aqui ou usar o menu `+` → Anexar arquivo.",
          );
          return;
        case "awaiting_validation_decision":
          onAssistantMessage(
            "Use os botões acima pra escolher: continuar mesmo assim ou corrigir antes.",
          );
          return;
        case "awaiting_metadata":
          await advanceFromMetadata(text);
          return;
        default:
          return;
      }
    },
    [state.step, advanceFromNumberConfirmation, advanceFromMetadata, onAssistantMessage, onUserMessage],
  );

  const submitFile = useCallback(
    async (file: File): Promise<void> => {
      if (state.step !== "awaiting_spreadsheet") {
        onAssistantMessage(
          "Recebi o arquivo, mas não estou esperando upload nesse momento.",
        );
        return;
      }
      onUserMessage(`📎 ${file.name}`);
      const spreadsheetId = `mock-${file.name}-${Date.now()}`;
      dispatch({
        type: "SPREADSHEET_RECEIVED",
        fileName: file.name,
        spreadsheetId,
      });
      try {
        const result = await parseSpreadsheet(spreadsheetId);
        dispatch({ type: "VALIDATION_DONE", result });
        if (result.warnings.length === 0 && result.errors.length === 0) {
          onAssistantMessage(
            "Recebi a planilha sem inconsistências. Pra finalizar, preciso de:\n- Cliente?\n- Empreendimento?\n- Cidade?",
          );
          return;
        }
        const lines: string[] = ["Recebi a planilha. Encontrei 2 inconsistências:", ""];
        for (const w of result.warnings) lines.push(`⚠️ ${w.message}`);
        for (const e of result.errors) lines.push(`❌ ${e.message}`);
        lines.push("");
        lines.push("Continuo mesmo assim, ou você quer corrigir antes?");
        onAssistantMessage(lines.join("\n"));
      } catch (e) {
        const message = e instanceof Error ? e.message : "Falha ao validar planilha";
        dispatch({ type: "ERROR", message });
        onAssistantMessage(`Não consegui validar a planilha: ${message}.`);
      }
    },
    [state.step, onAssistantMessage, onUserMessage],
  );

  const decideContinue = useCallback(async (): Promise<void> => {
    if (state.step !== "awaiting_validation_decision") return;
    onUserMessage("Continuar mesmo assim");
    dispatch({ type: "USER_DECIDED_CONTINUE" });
    onAssistantMessage(
      "Combinado. Pra finalizar, preciso de:\n- Cliente?\n- Empreendimento?\n- Cidade?",
    );
  }, [state.step, onAssistantMessage, onUserMessage]);

  const decideFix = useCallback((): void => {
    if (state.step !== "awaiting_validation_decision") return;
    onUserMessage("Vou corrigir");
    dispatch({ type: "RESET" });
    onAssistantMessage(
      "Ok, quando estiver corrigida arrasta de novo. Pra recomeçar o fluxo, abra o menu `+` → Agente → Criar projeto novo.",
    );
  }, [state.step, onAssistantMessage, onUserMessage]);

  const reset = useCallback((): void => {
    dispatch({ type: "RESET" });
  }, []);

  return {
    state,
    isActive: state.step !== "idle",
    start,
    submitUserText,
    submitFile,
    decideContinue,
    decideFix,
    reset,
  };
}
