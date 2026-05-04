import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MetadataForm } from "../MetadataForm";


describe("<MetadataForm />", () => {
  it("renders 4 inputs with labels", () => {
    render(<MetadataForm onConfirm={() => undefined} />);
    expect(screen.getByText(/cliente/i)).toBeInTheDocument();
    expect(screen.getByText(/empreendimento/i)).toBeInTheDocument();
    expect(screen.getByText(/cidade/i)).toBeInTheDocument();
    expect(screen.getByText(/estado/i)).toBeInTheDocument();
  });

  it("disables submit until required fields are filled", async () => {
    const user = userEvent.setup();
    render(<MetadataForm onConfirm={() => undefined} />);
    const button = screen.getByRole("button", { name: /confirmar/i });
    expect(button).toBeDisabled();

    const inputs = screen.getAllByRole("textbox");
    await user.type(inputs[0], "Acme");
    await user.type(inputs[1], "Torre A");
    expect(button).toBeDisabled();

    await user.type(inputs[2], "Florianópolis");
    expect(button).toBeEnabled();
  });

  it("calls onConfirm with trimmed values and uppercase estado", async () => {
    const user = userEvent.setup();
    const onConfirm = vi.fn();
    render(<MetadataForm onConfirm={onConfirm} />);

    const inputs = screen.getAllByRole("textbox");
    await user.type(inputs[0], "  Acme  ");
    await user.type(inputs[1], "Torre A");
    await user.type(inputs[2], "Florianópolis");
    await user.type(inputs[3], "sc");

    await user.click(screen.getByRole("button", { name: /confirmar/i }));

    expect(onConfirm).toHaveBeenCalledWith({
      cliente: "Acme",
      empreendimento: "Torre A",
      cidade: "Florianópolis",
      estado: "SC",
    });
  });

  it("submits without estado when left blank", async () => {
    const user = userEvent.setup();
    const onConfirm = vi.fn();
    render(<MetadataForm onConfirm={onConfirm} />);

    const inputs = screen.getAllByRole("textbox");
    await user.type(inputs[0], "Acme");
    await user.type(inputs[1], "Torre A");
    await user.type(inputs[2], "Floripa");

    await user.click(screen.getByRole("button", { name: /confirmar/i }));

    expect(onConfirm).toHaveBeenCalledWith({
      cliente: "Acme",
      empreendimento: "Torre A",
      cidade: "Floripa",
      estado: undefined,
    });
  });

  it("limits estado to 2 characters and uppercases on input", async () => {
    const user = userEvent.setup();
    render(<MetadataForm onConfirm={() => undefined} />);
    const inputs = screen.getAllByRole("textbox");
    const estadoInput = inputs[3] as HTMLInputElement;
    await user.type(estadoInput, "abcdef");
    expect(estadoInput.value).toBe("AB");
  });

  it("submit on Enter from last field when valid", async () => {
    const user = userEvent.setup();
    const onConfirm = vi.fn();
    render(<MetadataForm onConfirm={onConfirm} />);
    const inputs = screen.getAllByRole("textbox");
    await user.type(inputs[0], "Acme");
    await user.type(inputs[1], "Torre A");
    await user.type(inputs[2], "Floripa");
    await user.type(inputs[3], "SC{Enter}");
    expect(onConfirm).toHaveBeenCalledTimes(1);
  });

  it("renders loading state with spinner and disables submit", () => {
    render(<MetadataForm onConfirm={() => undefined} loading />);
    expect(screen.getByText(/Criando…/)).toBeInTheDocument();
    expect(screen.getByRole("button")).toBeDisabled();
  });

  it("disables all inputs when loading", () => {
    render(<MetadataForm onConfirm={() => undefined} loading />);
    const inputs = screen.getAllByRole("textbox");
    for (const input of inputs) expect(input).toBeDisabled();
  });

  it("shows errorMessage inline when provided", () => {
    render(
      <MetadataForm
        onConfirm={() => undefined}
        errorMessage="Falha ao criar projeto: 500 Internal Server Error"
      />,
    );
    expect(screen.getByRole("alert")).toHaveTextContent(/500 Internal Server Error/);
  });

  it("does not call onConfirm when loading=true even with valid inputs", async () => {
    const user = userEvent.setup();
    const onConfirm = vi.fn();
    const { rerender } = render(<MetadataForm onConfirm={onConfirm} />);
    const inputs = screen.getAllByRole("textbox");
    await user.type(inputs[0], "Acme");
    await user.type(inputs[1], "Torre A");
    await user.type(inputs[2], "Floripa");

    rerender(<MetadataForm onConfirm={onConfirm} loading />);
    await user.click(screen.getByRole("button"));
    expect(onConfirm).not.toHaveBeenCalled();
  });
});
