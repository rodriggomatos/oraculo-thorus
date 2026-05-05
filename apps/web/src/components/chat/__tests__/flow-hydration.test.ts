import { describe, expect, it } from "vitest";

import { shouldHydrateFlow } from "../flow-hydration";


describe("shouldHydrateFlow", () => {
  it("does not hydrate when threadId did not change (agentState echo)", () => {
    expect(
      shouldHydrateFlow({ prevThreadId: "A", currentThreadId: "A", isRunning: true }),
    ).toBe(false);
    expect(
      shouldHydrateFlow({ prevThreadId: null, currentThreadId: null, isRunning: false }),
    ).toBe(false);
  });

  it("does NOT hydrate on internal append (null → UUID while running)", () => {
    // Flow chamou onAssistantMessage na primeira mensagem dele — useChat
    // gerou threadId. Hidratar aqui zeraria o reducer.
    expect(
      shouldHydrateFlow({ prevThreadId: null, currentThreadId: "fresh", isRunning: true }),
    ).toBe(false);
  });

  it("hydrates on null → UUID when flow is idle (initial restore from storage)", () => {
    // Page reload, useChat carrega thread do storage; flow ainda está idle.
    expect(
      shouldHydrateFlow({ prevThreadId: null, currentThreadId: "A", isRunning: false }),
    ).toBe(true);
  });

  it("hydrates when switching between two threads (UUID → UUID)", () => {
    // Sidebar click. Mesmo que flow esteja em running step da thread antiga,
    // o user mudou de conversa: o flow tem que assumir o state da nova.
    expect(
      shouldHydrateFlow({ prevThreadId: "A", currentThreadId: "B", isRunning: true }),
    ).toBe(true);
    expect(
      shouldHydrateFlow({ prevThreadId: "A", currentThreadId: "B", isRunning: false }),
    ).toBe(true);
  });

  it("hydrates on UUID → null (new chat / delete current thread)", () => {
    expect(
      shouldHydrateFlow({ prevThreadId: "A", currentThreadId: null, isRunning: true }),
    ).toBe(true);
    expect(
      shouldHydrateFlow({ prevThreadId: "A", currentThreadId: null, isRunning: false }),
    ).toBe(true);
  });
});
