import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";


vi.mock("../cities-client", () => ({
  fetchCities: vi.fn(),
  stripAccents: (s: string) => s.normalize("NFD").replace(/\p{Diacritic}/gu, ""),
}));


import * as citiesClient from "../cities-client";
import { MetadataForm } from "../MetadataForm";


const FAKE_CITIES = [
  { id: 4205407, nome: "Florianópolis", estado: "SC" },
  { id: 4313409, nome: "Porto Alegre", estado: "RS" },
  { id: 3550308, nome: "São Paulo", estado: "SP" },
];


describe("<MetadataForm />", () => {
  beforeEach(() => {
    vi.mocked(citiesClient.fetchCities).mockResolvedValue(FAKE_CITIES);
  });

  afterEach(() => {
    vi.resetAllMocks();
  });

  async function renderAndWait() {
    const utils = render(<MetadataForm onConfirm={() => undefined} />);
    await waitFor(() =>
      expect(citiesClient.fetchCities).toHaveBeenCalledTimes(1),
    );
    return utils;
  }

  it("renders cliente, empreendimento inputs and city + estado comboboxes", async () => {
    await renderAndWait();
    expect(screen.getByText(/^cliente/i)).toBeInTheDocument();
    expect(screen.getByText(/^empreendimento/i)).toBeInTheDocument();
    expect(screen.getByRole("combobox", { name: /cidade/i })).toBeInTheDocument();
    expect(screen.getByRole("combobox", { name: /estado/i })).toBeInTheDocument();
  });

  it("disables submit until cliente/empreendimento filled and city selected", async () => {
    const user = userEvent.setup();
    await renderAndWait();
    const submit = screen.getByRole("button", { name: /confirmar/i });
    expect(submit).toBeDisabled();

    const inputs = screen.getAllByRole("textbox");
    await user.type(inputs[0], "Acme");
    await user.type(inputs[1], "Torre A");
    expect(submit).toBeDisabled();
  });

  it("renders loading state with spinner and disables submit", async () => {
    render(<MetadataForm onConfirm={() => undefined} loading />);
    expect(screen.getByText(/Criando…/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Criando…/ })).toBeDisabled();
  });

  it("disables text inputs when loading", async () => {
    render(<MetadataForm onConfirm={() => undefined} loading />);
    const inputs = screen.getAllByRole("textbox");
    for (const input of inputs) expect(input).toBeDisabled();
  });

  it("shows errorMessage inline when provided", async () => {
    render(
      <MetadataForm
        onConfirm={() => undefined}
        errorMessage="Falha ao criar projeto: 500 Internal Server Error"
      />,
    );
    expect(screen.getByRole("alert")).toHaveTextContent(/500 Internal Server Error/);
  });

  it("shows amber alert when fetchCities fails", async () => {
    vi.mocked(citiesClient.fetchCities).mockRejectedValueOnce(new Error("offline"));
    render(<MetadataForm onConfirm={() => undefined} />);
    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(/cidades/i);
      expect(screen.getByRole("alert")).toHaveTextContent(/offline/);
    });
  });

  it("opens cidade combobox and lists cities by name", async () => {
    const user = userEvent.setup();
    await renderAndWait();
    const cityCombobox = screen.getByRole("combobox", { name: /cidade/i });
    await user.click(cityCombobox);
    const option = await screen.findByRole("option", { name: /Florianópolis/ });
    expect(option).toBeInTheDocument();
    expect(screen.getByRole("option", { name: /Porto Alegre/ })).toBeInTheDocument();
  });

  it("selecting city autofills the estado combobox label", async () => {
    const user = userEvent.setup();
    await renderAndWait();
    await user.click(screen.getByRole("combobox", { name: /cidade/i }));
    await user.click(await screen.findByRole("option", { name: /Florianópolis/ }));
    const estadoCombobox = screen.getByRole("combobox", { name: /estado/i });
    expect(estadoCombobox).toHaveTextContent("SC - Santa Catarina");
  });

  it("calls onConfirm with metadata + cityId when valid", async () => {
    const user = userEvent.setup();
    const onConfirm = vi.fn();
    const { rerender: _rerender } = render(<MetadataForm onConfirm={onConfirm} />);
    await waitFor(() =>
      expect(citiesClient.fetchCities).toHaveBeenCalledTimes(1),
    );

    const inputs = screen.getAllByRole("textbox");
    await user.type(inputs[0], "  Acme  ");
    await user.type(inputs[1], "Torre A");

    await user.click(screen.getByRole("combobox", { name: /cidade/i }));
    await user.click(await screen.findByRole("option", { name: /Florianópolis/ }));

    await user.click(screen.getByRole("button", { name: /confirmar/i }));

    expect(onConfirm).toHaveBeenCalledTimes(1);
    expect(onConfirm).toHaveBeenCalledWith(
      {
        cliente: "Acme",
        empreendimento: "Torre A",
        cidade: "Florianópolis",
        estado: "SC",
      },
      4205407,
    );
  });

  it("clearing city via X unlocks estado combobox for editing", async () => {
    const user = userEvent.setup();
    await renderAndWait();

    await user.click(screen.getByRole("combobox", { name: /cidade/i }));
    await user.click(await screen.findByRole("option", { name: /Florianópolis/ }));

    expect(screen.getByRole("combobox", { name: /estado/i })).toBeDisabled();

    await user.click(screen.getByRole("button", { name: /limpar seleção/i }));

    expect(screen.getByRole("combobox", { name: /estado/i })).not.toBeDisabled();
  });
});
