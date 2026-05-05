import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, renderHook, waitFor } from "@testing-library/react";


vi.mock("../mock", () => ({
  suggestNumber: vi.fn(),
  parseSpreadsheet: vi.fn(),
  createProject: vi.fn(),
}));


import * as mockApi from "../mock";
import { useCreateProjectFlow } from "../hooks/useCreateProjectFlow";


function renderFlow() {
  const onAssistantMessage = vi.fn();
  const onUserMessage = vi.fn();
  const utils = renderHook(() =>
    useCreateProjectFlow({ onAssistantMessage, onUserMessage }),
  );
  return { ...utils, onAssistantMessage, onUserMessage };
}


describe("useCreateProjectFlow hydration", () => {
  afterEach(() => {
    vi.resetAllMocks();
  });

  it("isRunning flips true during intermediate steps and false at terminal", async () => {
    vi.mocked(mockApi.suggestNumber).mockResolvedValueOnce({ suggested: 26040 });
    const { result } = renderHook(() =>
      useCreateProjectFlow({
        onAssistantMessage: vi.fn(),
        onUserMessage: vi.fn(),
      }),
    );
    expect(result.current.isRunning).toBe(false);
    await act(async () => {
      await result.current.start();
    });
    expect(result.current.isRunning).toBe(true);
    expect(result.current.state.step).toBe("awaiting_number_confirmation");
  });

  it("initialState awaiting_metadata restores form-ready step + parsed metadata", () => {
    const { result } = renderHook(() =>
      useCreateProjectFlow({
        onAssistantMessage: vi.fn(),
        onUserMessage: vi.fn(),
        initialState: {
          step: "awaiting_metadata",
          confirmedNumber: 26033,
          spreadsheetId: "sheet-abc",
          spreadsheetFileName: "orcamento.gsheet",
          validationResult: { ok: true, errors: [], warnings: [] },
        },
      }),
    );
    expect(result.current.state.step).toBe("awaiting_metadata");
    expect(result.current.state.confirmedNumber).toBe(26033);
    expect(result.current.state.spreadsheetId).toBe("sheet-abc");
    expect(result.current.isRunning).toBe(true);
    expect(result.current.isActive).toBe(true);
  });

  it("initialState awaiting_number_confirmation restores number bar", () => {
    const { result } = renderHook(() =>
      useCreateProjectFlow({
        onAssistantMessage: vi.fn(),
        onUserMessage: vi.fn(),
        initialState: {
          step: "awaiting_number_confirmation",
          suggestedNumber: 26050,
        },
      }),
    );
    expect(result.current.state.step).toBe("awaiting_number_confirmation");
    expect(result.current.state.suggestedNumber).toBe(26050);
  });

  it("initialState awaiting_spreadsheet restores after number confirmed", () => {
    const { result } = renderHook(() =>
      useCreateProjectFlow({
        onAssistantMessage: vi.fn(),
        onUserMessage: vi.fn(),
        initialState: {
          step: "awaiting_spreadsheet",
          confirmedNumber: 26050,
        },
      }),
    );
    expect(result.current.state.step).toBe("awaiting_spreadsheet");
    expect(result.current.state.confirmedNumber).toBe(26050);
  });

  it("initialState success keeps finalResult ready for action buttons", () => {
    const { result } = renderHook(() =>
      useCreateProjectFlow({
        onAssistantMessage: vi.fn(),
        onUserMessage: vi.fn(),
        initialState: {
          step: "success",
          confirmedNumber: 26033,
          finalResult: {
            projectId: "p-1",
            projectNumber: 26033,
            projectName: "26033 - X - Y - Z - SC",
            driveFolderPending: false,
            driveFolderId: "folder-x",
            ldpSheetsId: null,
            definitionsCount: 114,
          },
        },
      }),
    );
    expect(result.current.state.step).toBe("success");
    expect(result.current.state.finalResult?.driveFolderId).toBe("folder-x");
    expect(result.current.isRunning).toBe(false);
  });

  it("hydrate(null) resets to idle; hydrate(state) restores arbitrary step", () => {
    const { result } = renderHook(() =>
      useCreateProjectFlow({
        onAssistantMessage: vi.fn(),
        onUserMessage: vi.fn(),
      }),
    );
    expect(result.current.state.step).toBe("idle");

    act(() => {
      result.current.hydrate({
        step: "awaiting_metadata",
        confirmedNumber: 26034,
        spreadsheetId: "sid",
      });
    });
    expect(result.current.state.step).toBe("awaiting_metadata");
    expect(result.current.state.spreadsheetId).toBe("sid");

    act(() => {
      result.current.hydrate(null);
    });
    expect(result.current.state.step).toBe("idle");
  });

  it("patchFinalResult merges fields into existing finalResult only at success", () => {
    const { result } = renderHook(() =>
      useCreateProjectFlow({
        onAssistantMessage: vi.fn(),
        onUserMessage: vi.fn(),
        initialState: {
          step: "success",
          finalResult: {
            projectId: "p-1",
            projectNumber: 1,
            projectName: "n",
            driveFolderPending: true,
            driveFolderId: null,
            ldpSheetsId: null,
            definitionsCount: 0,
          },
        },
      }),
    );

    act(() => {
      result.current.patchFinalResult({ driveFolderId: "folder-x" });
    });
    expect(result.current.state.finalResult?.driveFolderId).toBe("folder-x");
    expect(result.current.state.finalResult?.projectId).toBe("p-1");

    act(() => {
      result.current.patchFinalResult({ ldpSheetsId: "sheet-y" });
    });
    expect(result.current.state.finalResult?.ldpSheetsId).toBe("sheet-y");
    expect(result.current.state.finalResult?.driveFolderId).toBe("folder-x");
  });

  it("patchFinalResult is no-op when no finalResult yet", () => {
    const { result } = renderHook(() =>
      useCreateProjectFlow({
        onAssistantMessage: vi.fn(),
        onUserMessage: vi.fn(),
        initialState: { step: "awaiting_metadata", confirmedNumber: 1 },
      }),
    );
    act(() => {
      result.current.patchFinalResult({ driveFolderId: "x" });
    });
    expect(result.current.state.finalResult).toBeUndefined();
    expect(result.current.state.step).toBe("awaiting_metadata");
  });
});


describe("useCreateProjectFlow.start", () => {
  beforeEach(() => {
    vi.mocked(mockApi.suggestNumber).mockResolvedValue({ suggested: 26024 });
  });

  afterEach(() => {
    vi.resetAllMocks();
  });

  it("transitions from idle to awaiting_number_confirmation on first start", async () => {
    const { result } = renderFlow();
    expect(result.current.state.step).toBe("idle");

    await act(async () => {
      await result.current.start();
    });

    expect(result.current.state.step).toBe("awaiting_number_confirmation");
    expect(result.current.state.suggestedNumber).toBe(26024);
    expect(mockApi.suggestNumber).toHaveBeenCalledTimes(1);
  });

  it("blocks restart while flow is running (double-click guard)", async () => {
    const { result } = renderFlow();

    await act(async () => {
      await result.current.start();
    });
    expect(result.current.state.step).toBe("awaiting_number_confirmation");

    await act(async () => {
      await result.current.start();
    });

    expect(mockApi.suggestNumber).toHaveBeenCalledTimes(1);
  });

  it("allows restart after a terminal success state by auto-resetting", async () => {
    vi.mocked(mockApi.suggestNumber).mockResolvedValue({ suggested: 26024 });
    const { result } = renderFlow();

    await act(async () => {
      await result.current.start();
    });

    act(() => {
      result.current.confirmNumber(26024);
    });

    // Manually drive flow to a fake success-equivalent terminal step:
    // We use submitFile to advance through parsing → validation_done (no warnings), then submitMetadata
    // Set up mock chain:
    vi.mocked(mockApi.parseSpreadsheet).mockResolvedValueOnce({
      ok: true,
      errors: [],
      warnings: [],
    });
    vi.mocked(mockApi.createProject).mockResolvedValueOnce({
      projectId: "p-1",
      projectNumber: 26024,
      projectName: "26024 - Acme - Torre A",
      driveFolderPending: true,
      driveFolderId: null,
      ldpSheetsId: null,
      definitionsCount: 0,
    });

    await act(async () => {
      await result.current.submitFile(new File([""], "orcamento.gsheet"));
    });
    expect(result.current.state.step).toBe("awaiting_metadata");

    await act(async () => {
      await result.current.submitMetadata({
        cliente: "Acme",
        empreendimento: "Torre A",
        cidade: "Floripa",
      });
    });
    await waitFor(() => expect(result.current.state.step).toBe("success"));

    // Now in terminal state. Click Criar projeto novo again:
    vi.mocked(mockApi.suggestNumber).mockResolvedValue({ suggested: 26025 });

    await act(async () => {
      await result.current.start();
    });

    expect(result.current.state.step).toBe("awaiting_number_confirmation");
    expect(result.current.state.suggestedNumber).toBe(26025);
    expect(result.current.state.finalResult).toBeUndefined();
    expect(result.current.state.confirmedNumber).toBeUndefined();
  });

  it("allows restart from error state", async () => {
    vi.mocked(mockApi.suggestNumber).mockRejectedValueOnce(new Error("network"));
    const { result } = renderFlow();

    await act(async () => {
      await result.current.start();
    });
    expect(result.current.state.step).toBe("error");

    vi.mocked(mockApi.suggestNumber).mockResolvedValueOnce({ suggested: 26100 });

    await act(async () => {
      await result.current.start();
    });

    expect(result.current.state.step).toBe("awaiting_number_confirmation");
    expect(result.current.state.suggestedNumber).toBe(26100);
    expect(result.current.state.errorMessage).toBeUndefined();
  });

  it("reset() returns step to idle", async () => {
    const { result } = renderFlow();
    await act(async () => {
      await result.current.start();
    });
    expect(result.current.state.step).toBe("awaiting_number_confirmation");

    act(() => {
      result.current.reset();
    });
    expect(result.current.state.step).toBe("idle");
  });
});
