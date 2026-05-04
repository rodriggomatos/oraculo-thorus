import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { NumberConfirmBar } from "../NumberConfirmBar";


describe("<NumberConfirmBar />", () => {
  it("shows the suggested number on the confirm button", () => {
    render(<NumberConfirmBar suggested={26024} onConfirm={() => undefined} />);
    expect(screen.getByRole("button", { name: /Confirmar 26024/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Outro número/ })).toBeInTheDocument();
  });

  it("calls onConfirm with the suggested number when confirm is clicked", async () => {
    const user = userEvent.setup();
    const onConfirm = vi.fn();
    render(<NumberConfirmBar suggested={26024} onConfirm={onConfirm} />);
    await user.click(screen.getByRole("button", { name: /Confirmar 26024/ }));
    expect(onConfirm).toHaveBeenCalledWith(26024);
  });

  it("shows an input and confirm button when 'Outro número' is clicked", async () => {
    const user = userEvent.setup();
    render(<NumberConfirmBar suggested={26024} onConfirm={() => undefined} />);
    await user.click(screen.getByRole("button", { name: /Outro número/ }));
    expect(screen.getByLabelText(/Número do projeto/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Usar este número/ })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Confirmar 26024/ })).not.toBeInTheDocument();
  });

  it("disables 'Usar este número' until 5 digits are typed", async () => {
    const user = userEvent.setup();
    render(<NumberConfirmBar suggested={26024} onConfirm={() => undefined} />);
    await user.click(screen.getByRole("button", { name: /Outro número/ }));
    const submit = screen.getByRole("button", { name: /Usar este número/ });
    expect(submit).toBeDisabled();

    const input = screen.getByLabelText(/Número do projeto/i);
    await user.type(input, "2602");
    expect(submit).toBeDisabled();

    await user.type(input, "5");
    expect(submit).toBeEnabled();
  });

  it("strips non-digits from input and limits to 5 chars", async () => {
    const user = userEvent.setup();
    render(<NumberConfirmBar suggested={26024} onConfirm={() => undefined} />);
    await user.click(screen.getByRole("button", { name: /Outro número/ }));
    const input = screen.getByLabelText(/Número do projeto/i) as HTMLInputElement;
    await user.type(input, "abc26025xyz999");
    expect(input.value).toBe("26025");
  });

  it("calls onConfirm with the typed number on submit", async () => {
    const user = userEvent.setup();
    const onConfirm = vi.fn();
    render(<NumberConfirmBar suggested={26024} onConfirm={onConfirm} />);
    await user.click(screen.getByRole("button", { name: /Outro número/ }));
    const input = screen.getByLabelText(/Número do projeto/i);
    await user.type(input, "26025");
    await user.click(screen.getByRole("button", { name: /Usar este número/ }));
    expect(onConfirm).toHaveBeenCalledWith(26025);
  });

  it("submits on Enter when input is valid", async () => {
    const user = userEvent.setup();
    const onConfirm = vi.fn();
    render(<NumberConfirmBar suggested={26024} onConfirm={onConfirm} />);
    await user.click(screen.getByRole("button", { name: /Outro número/ }));
    const input = screen.getByLabelText(/Número do projeto/i);
    await user.type(input, "26099{Enter}");
    expect(onConfirm).toHaveBeenCalledWith(26099);
  });

  it("Escape cancels editing and returns to default state", async () => {
    const user = userEvent.setup();
    render(<NumberConfirmBar suggested={26024} onConfirm={() => undefined} />);
    await user.click(screen.getByRole("button", { name: /Outro número/ }));
    const input = screen.getByLabelText(/Número do projeto/i);
    await user.type(input, "260{Escape}");
    expect(screen.getByRole("button", { name: /Confirmar 26024/ })).toBeInTheDocument();
  });

  it("Cancel button returns to default state without calling onConfirm", async () => {
    const user = userEvent.setup();
    const onConfirm = vi.fn();
    render(<NumberConfirmBar suggested={26024} onConfirm={onConfirm} />);
    await user.click(screen.getByRole("button", { name: /Outro número/ }));
    await user.click(screen.getByRole("button", { name: /Cancelar/ }));
    expect(screen.getByRole("button", { name: /Confirmar 26024/ })).toBeInTheDocument();
    expect(onConfirm).not.toHaveBeenCalled();
  });
});
