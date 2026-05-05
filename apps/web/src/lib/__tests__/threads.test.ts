import { afterEach, beforeEach, describe, expect, it } from "vitest";

import {
  deleteThread,
  getThread,
  listThreads,
  upsertThread,
} from "../threads";
import type { Message } from "../types";


function clearStorage(): void {
  window.localStorage.clear();
}


function userMsg(content: string): Message {
  return { role: "user", content, timestamp: new Date().toISOString() };
}


function assistantMsg(content: string): Message {
  return { role: "assistant", content, timestamp: new Date().toISOString() };
}


describe("threads storage", () => {
  beforeEach(clearStorage);
  afterEach(clearStorage);

  it("upsertThread creates a new thread with title derived from first user message", () => {
    upsertThread("t-1", [assistantMsg("Olá!"), userMsg("Quero criar projeto")]);
    const list = listThreads();
    expect(list).toHaveLength(1);
    expect(list[0].titulo).toBe("Quero criar projeto");
    expect(list[0].agent_state).toBeNull();
  });

  it("derives title from first message when no user message yet (agent flow)", () => {
    upsertThread("t-1", [assistantMsg("Estou montando seu projeto…")]);
    const t = getThread("t-1");
    expect(t?.titulo).toMatch(/Estou montando/);
  });

  it("preserves existing title and updates messages on update", () => {
    upsertThread("t-1", [userMsg("Olá")], { titleHint: "Olá" });
    upsertThread("t-1", [userMsg("Olá"), assistantMsg("Resposta")]);
    const t = getThread("t-1");
    expect(t?.titulo).toBe("Olá");
    expect(t?.messages).toHaveLength(2);
  });

  it("persists agent_state when provided", () => {
    const state = {
      step: "awaiting_metadata",
      confirmedNumber: 26033,
      spreadsheetId: "abc",
    };
    upsertThread("t-1", [userMsg("create")], { agentState: state });
    expect(getThread("t-1")?.agent_state).toEqual(state);
  });

  it("preserves agent_state when only updating messages (undefined override)", () => {
    const state = { step: "awaiting_spreadsheet", confirmedNumber: 1 };
    upsertThread("t-1", [userMsg("a")], { agentState: state });
    upsertThread("t-1", [userMsg("a"), assistantMsg("b")]);
    expect(getThread("t-1")?.agent_state).toEqual(state);
  });

  it("can clear agent_state by passing null", () => {
    upsertThread("t-1", [userMsg("a")], {
      agentState: { step: "awaiting_metadata" },
    });
    upsertThread("t-1", [userMsg("a")], { agentState: null });
    expect(getThread("t-1")?.agent_state).toBeNull();
  });

  it("listThreads returns most recent first", () => {
    upsertThread("t-old", [userMsg("old")]);
    // Force a later timestamp
    const raw = JSON.parse(window.localStorage.getItem("threads") ?? "[]");
    raw[0].created_at = new Date(Date.now() - 10000).toISOString();
    window.localStorage.setItem("threads", JSON.stringify(raw));

    upsertThread("t-new", [userMsg("new")]);
    expect(listThreads().map((t) => t.thread_id)).toEqual(["t-new", "t-old"]);
  });

  it("deleteThread removes the thread", () => {
    upsertThread("t-1", [userMsg("a")]);
    deleteThread("t-1");
    expect(listThreads()).toEqual([]);
  });
});
