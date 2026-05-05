import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, renderHook } from "@testing-library/react";


vi.mock("@/lib/api", () => ({
  sendQuery: vi.fn(),
}));


vi.mock("sonner", () => ({
  toast: { error: vi.fn() },
}));


import { sendQuery } from "@/lib/api";
import { useChat } from "../useChat";
import { listThreads } from "@/lib/threads";


function clearStorage(): void {
  window.localStorage.clear();
}


describe("useChat — agent flow persistence", () => {
  beforeEach(() => {
    clearStorage();
    vi.mocked(sendQuery).mockReset();
  });

  afterEach(clearStorage);

  it("appendUserMessage persists to localStorage and creates a new thread", () => {
    const { result } = renderHook(() => useChat());
    expect(listThreads()).toEqual([]);

    act(() => {
      result.current.appendUserMessage("Quero criar projeto");
    });

    const stored = listThreads();
    expect(stored).toHaveLength(1);
    expect(stored[0].titulo).toBe("Quero criar projeto");
    expect(result.current.threadId).toBe(stored[0].thread_id);
    expect(result.current.messages).toHaveLength(1);
  });

  it("appendAssistantMessage persists when starting a thread (agent opens conversation)", () => {
    const { result } = renderHook(() => useChat());

    act(() => {
      result.current.appendAssistantMessage("Vamos criar um projeto novo…");
    });

    const stored = listThreads();
    expect(stored).toHaveLength(1);
    expect(stored[0].titulo).toMatch(/Vamos criar/);
    expect(result.current.threadId).toBeTruthy();
  });

  it("setAgentResult persists agent_result on existing thread", () => {
    const { result } = renderHook(() => useChat());

    act(() => {
      result.current.appendAssistantMessage("Iniciando…");
    });

    const tid = result.current.threadId!;
    act(() => {
      result.current.setAgentResult({
        projectId: "p-1",
        projectNumber: 26033,
        projectName: "26033 - X - Y - Z - SC",
        driveFolderId: null,
        ldpSheetsId: null,
        definitionsCount: 114,
      });
    });

    const stored = listThreads().find((t) => t.thread_id === tid);
    expect(stored?.agent_result?.projectNumber).toBe(26033);
    expect(result.current.agentResult?.projectNumber).toBe(26033);
  });

  it("switchThread restores agent_result", () => {
    const { result } = renderHook(() => useChat());

    act(() => {
      result.current.appendAssistantMessage("Iniciando…");
    });
    const tid = result.current.threadId!;
    act(() => {
      result.current.setAgentResult({
        projectId: "p-1",
        projectNumber: 1,
        projectName: "n",
        driveFolderId: "folder-x",
        ldpSheetsId: null,
        definitionsCount: 0,
      });
    });

    act(() => {
      result.current.newThread();
    });
    expect(result.current.agentResult).toBeNull();

    act(() => {
      result.current.switchThread(tid);
    });
    expect(result.current.agentResult?.driveFolderId).toBe("folder-x");
  });

  it("after newThread, append again creates a NEW thread", () => {
    const { result } = renderHook(() => useChat());

    act(() => {
      result.current.appendAssistantMessage("a");
    });
    const first = result.current.threadId;

    act(() => {
      result.current.newThread();
    });

    act(() => {
      result.current.appendAssistantMessage("b");
    });
    expect(result.current.threadId).not.toBe(first);
    expect(listThreads()).toHaveLength(2);
  });
});
