import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";


vi.mock("@/features/create-project/mock", () => ({
  createLdpSheet: vi.fn(),
}));


import { createLdpSheet } from "@/features/create-project/mock";
import { CreateLdpSheetButton } from "../CreateLdpSheetButton";


describe("<CreateLdpSheetButton />", () => {
  beforeEach(() => {
    vi.mocked(createLdpSheet).mockReset();
  });

  afterEach(() => {
    vi.resetAllMocks();
  });

  it("renders idle button when no sheet yet", () => {
    render(<CreateLdpSheetButton projectId="p-1" />);
    expect(screen.getByRole("button", { name: /Criar planilha LDP/i })).toBeEnabled();
  });

  it("starts in success state when initialSheetsId is provided", () => {
    render(<CreateLdpSheetButton projectId="p-1" initialSheetsId="sheet-123" />);
    expect(
      screen.getByRole("link", { name: /Planilha LDP criada — abrir no Sheets/i }),
    ).toHaveAttribute(
      "href",
      "https://docs.google.com/spreadsheets/d/sheet-123/edit",
    );
  });

  it("disabled state shows reason and blocks click", async () => {
    render(
      <CreateLdpSheetButton
        projectId="p-1"
        disabled
        disabledReason="Crie a pasta no Drive primeiro."
      />,
    );
    const button = screen.getByRole("button", { name: /Criar planilha LDP/i });
    expect(button).toBeDisabled();
    expect(screen.getByText(/Crie a pasta no Drive primeiro\./i)).toBeInTheDocument();

    const user = userEvent.setup();
    await act(async () => {
      await user.click(button);
    });
    expect(createLdpSheet).not.toHaveBeenCalled();
  });

  it("transitions idle → loading → success on click", async () => {
    let resolver: ((v: {
      sheetsId: string;
      sheetsUrl: string;
      sheetsName: string;
      rowsWritten: number;
    }) => void) | undefined;
    vi.mocked(createLdpSheet).mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          resolver = resolve;
        }),
    );

    const user = userEvent.setup();
    render(<CreateLdpSheetButton projectId="p-1" />);
    await act(async () => {
      await user.click(screen.getByRole("button", { name: /Criar planilha LDP/i }));
    });

    expect(screen.getByRole("button", { name: /Criando planilha LDP/i })).toHaveAttribute(
      "aria-busy",
      "true",
    );

    await act(async () => {
      resolver?.({
        sheetsId: "abc",
        sheetsUrl: "https://docs.google.com/spreadsheets/d/abc/edit",
        sheetsName: "Lista de definição - 26033",
        rowsWritten: 114,
      });
    });

    await waitFor(() =>
      expect(
        screen.getByRole("link", { name: /Planilha LDP criada — abrir no Sheets/i }),
      ).toBeInTheDocument(),
    );
  });

  it("shows backend error message in alert", async () => {
    vi.mocked(createLdpSheet).mockRejectedValueOnce(
      new Error("Estrutura de pastas incompleta. Pasta '02 TRABALHO/DEFINIÇÕES' não encontrada."),
    );
    const user = userEvent.setup();
    render(<CreateLdpSheetButton projectId="p-1" />);
    await act(async () => {
      await user.click(screen.getByRole("button", { name: /Criar planilha LDP/i }));
    });
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("DEFINIÇÕES");
  });
});
