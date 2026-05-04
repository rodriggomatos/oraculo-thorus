"use client";

import { useCallback, useReducer } from "react";
import {
  createProject,
  parseSpreadsheet,
  suggestNumber,
} from "../mock";
import type {
  CreateProjectResponse,
  CreateProjectState,
  CreateProjectStep,
  ProjectMetadata,
  ValidationResult,
} from "../types";


const METADATA_PROMPT = "Pra finalizar, me passa os dados do projeto.";


const RUNNING_STEPS: ReadonlySet<CreateProjectStep> = new Set([
  "awaiting_number_confirmation",
  "awaiting_spreadsheet",
  "parsing_spreadsheet",
  "showing_validation",
  "awaiting_validation_decision",
  "awaiting_metadata",
  "creating",
]);


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
  | { type: "METADATA_SUBMIT_FAILED"; message: string }
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
      return { ...state, finalResult: action.result, step: "success", errorMessage: undefined };
    case "METADATA_SUBMIT_FAILED":
      return { ...state, step: "awaiting_metadata", errorMessage: action.message };
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
  confirmNumber: (confirmed: number) => void;
  submitMetadata: (metadata: ProjectMetadata, cityId?: number | null) => Promise<void>;
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
    if (RUNNING_STEPS.has(state.step)) return;
    if (state.step !== "idle") {
      dispatch({ type: "RESET" });
    }
    dispatch({ type: "START_REQUESTED" });
    onAssistantMessage("Consultando próximo número disponível…");
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
  }, [state.step, onAssistantMessage]);

  const confirmNumber = useCallback(
    (confirmed: number): void => {
      if (state.step !== "awaiting_number_confirmation") return;
      if (!Number.isInteger(confirmed) || confirmed <= 0) {
        onAssistantMessage(
          "Número inválido. Use 5 dígitos (ex: 26024).",
        );
        return;
      }
      onUserMessage(
        confirmed === state.suggestedNumber
          ? `Confirmar ${confirmed}`
          : `Usar ${confirmed}`,
      );
      dispatch({ type: "NUMBER_CONFIRMED", confirmed });
      onAssistantMessage(
        `Perfeito, número **${confirmed}**. Agora me envia a planilha de orçamento. Você pode:\n\n` +
          "- Arrastar o arquivo `.gsheet` aqui na conversa\n" +
          "- Clicar em **Anexar arquivo** no menu `+`\n" +
          "- Colar a URL do Google Sheets diretamente",
      );
    },
    [state.step, state.suggestedNumber, onAssistantMessage, onUserMessage],
  );

  const submitMetadata = useCallback(
    async (metadata: ProjectMetadata, cityId: number | null = null): Promise<void> => {
      if (state.step !== "awaiting_metadata") return;
      onUserMessage(
        `Cliente: ${metadata.cliente} • Empreendimento: ${metadata.empreendimento} • Cidade: ${metadata.cidade}` +
          (metadata.estado ? ` • Estado: ${metadata.estado}` : ""),
      );
      dispatch({ type: "METADATA_RECEIVED", metadata });
      dispatch({ type: "CREATING" });
      onAssistantMessage("Criando projeto…");
      try {
        const result = await createProject({
          spreadsheetId: state.spreadsheetId ?? "mock-spreadsheet",
          confirmedNumber: state.confirmedNumber!,
          metadata,
          cityId,
        });
        dispatch({ type: "CREATED", result });
        const valor = result.totalContratado.toLocaleString("pt-BR", {
          minimumFractionDigits: 2,
          maximumFractionDigits: 2,
        });
        const margemPercent = (result.margem * 100).toFixed(2);
        onAssistantMessage(
          `✅ Projeto **${result.projectNumber}** criado.\n\n` +
            `- Cliente: ${metadata.cliente || "—"}\n` +
            `- Empreendimento: ${metadata.empreendimento || "—"}\n` +
            `- Cidade: ${metadata.cidade || "—"}\n` +
            (metadata.estado ? `- Estado: ${metadata.estado}\n` : "") +
            `- Total contratado: R$ ${valor}\n` +
            `- Margem: ${margemPercent}%\n\n` +
            `⚠️ A pasta no Drive ainda precisa ser criada manualmente. No próximo sprint isso será automático.`,
        );
      } catch (e) {
        const message = e instanceof Error ? e.message : "Falha ao criar projeto";
        dispatch({ type: "METADATA_SUBMIT_FAILED", message });
        onAssistantMessage(
          `Não consegui criar o projeto: ${message}. O formulário voltou — ajusta e tenta de novo.`,
        );
      }
    },
    [state.step, state.confirmedNumber, state.spreadsheetId, onAssistantMessage, onUserMessage],
  );

  const processSpreadsheet = useCallback(
    async (spreadsheetId: string, fileName: string): Promise<void> => {
      dispatch({
        type: "SPREADSHEET_RECEIVED",
        fileName,
        spreadsheetId,
      });
      onAssistantMessage("Analisando a planilha de orçamento…");
      try {
        const result = await parseSpreadsheet(spreadsheetId);
        dispatch({ type: "VALIDATION_DONE", result });
        if (result.warnings.length === 0 && result.errors.length === 0) {
          onAssistantMessage(`Recebi a planilha sem inconsistências. ${METADATA_PROMPT}`);
          return;
        }
        const issueCount = result.warnings.length + result.errors.length;
        const lines: string[] = [`Recebi a planilha. Encontrei ${issueCount} inconsistência(s):`, ""];
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
    [onAssistantMessage],
  );

  const submitUserText = useCallback(
    async (text: string): Promise<void> => {
      onUserMessage(text);
      switch (state.step) {
        case "awaiting_number_confirmation":
          onAssistantMessage(
            "Use os botões acima pra confirmar o número sugerido ou escolher outro.",
          );
          return;
        case "awaiting_spreadsheet": {
          const urlMatch = text.match(
            /docs\.google\.com\/spreadsheets\/d\/([a-zA-Z0-9_-]+)/,
          );
          if (urlMatch) {
            const spreadsheetId = urlMatch[1];
            await processSpreadsheet(spreadsheetId, `Sheets ${spreadsheetId}`);
            return;
          }
          onAssistantMessage(
            "Não reconheci essa mensagem como uma planilha. Você pode:\n\n" +
              "- Arrastar o arquivo `.gsheet` aqui na conversa\n" +
              "- Clicar em **Anexar arquivo** no menu `+`\n" +
              "- Colar a URL completa do Google Sheets (ex: `https://docs.google.com/spreadsheets/d/.../edit`)",
          );
          return;
        }
        case "awaiting_validation_decision":
          onAssistantMessage(
            "Use os botões acima pra escolher: continuar mesmo assim ou corrigir antes.",
          );
          return;
        case "awaiting_metadata":
          onAssistantMessage(
            "Use o formulário acima pra mandar Cliente, Empreendimento e Cidade.",
          );
          return;
        default:
          return;
      }
    },
    [
      state.step,
      processSpreadsheet,
      onAssistantMessage,
      onUserMessage,
    ],
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
      await processSpreadsheet(spreadsheetId, file.name);
    },
    [state.step, processSpreadsheet, onAssistantMessage, onUserMessage],
  );

  const decideContinue = useCallback(async (): Promise<void> => {
    if (state.step !== "awaiting_validation_decision") return;
    onUserMessage("Continuar mesmo assim");
    dispatch({ type: "USER_DECIDED_CONTINUE" });
    onAssistantMessage(`Combinado. ${METADATA_PROMPT}`);
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
    confirmNumber,
    submitMetadata,
    decideContinue,
    decideFix,
    reset,
  };
}
