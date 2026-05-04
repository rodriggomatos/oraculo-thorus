"use client";

import { useEffect, useMemo, useState } from "react";
import { Loader2 } from "lucide-react";
import type { ProjectMetadata } from "./types";
import { BR_STATES } from "./br-states";
import { fetchCities, stripAccents } from "./cities-client";
import { Combobox, type ComboboxOption } from "@/components/ui/combobox";


export type MetadataFormProps = {
  onConfirm: (metadata: ProjectMetadata, cityId: number | null) => void;
  loading?: boolean;
  errorMessage?: string | null;
  disabled?: boolean;
};


type CityRow = { id: number; nome: string; estado: string };


const FIELD_CLASSES =
  "w-full rounded-md border border-[var(--sidebar-border,rgba(255,255,255,0.15))] bg-[var(--sidebar-popover-bg,rgba(0,0,0,0.4))] px-3 py-2 text-sm text-[var(--sidebar-text)] placeholder:text-[var(--sidebar-text-muted)] outline-none transition-colors focus:border-[var(--sidebar-active,#3b82f6)] disabled:opacity-60";

const FIELD_INVALID_CLASSES = "border-red-500/70 focus:border-red-500";


const STATE_OPTIONS: ComboboxOption[] = BR_STATES.map((s) => ({
  value: s.code,
  label: `${s.code} - ${s.nome}`,
  searchTerms: stripAccents(s.nome).toLowerCase(),
}));


export function MetadataForm({
  onConfirm,
  loading = false,
  errorMessage = null,
  disabled = false,
}: MetadataFormProps): React.ReactElement {
  const [cliente, setCliente] = useState("");
  const [empreendimento, setEmpreendimento] = useState("");
  const [cityId, setCityId] = useState<number | null>(null);
  const [estado, setEstado] = useState<string | null>(null);
  const [showErrors, setShowErrors] = useState(false);

  const [cities, setCities] = useState<CityRow[] | null>(null);
  const [citiesError, setCitiesError] = useState<string | null>(null);

  const isDisabled = disabled || loading;

  useEffect(() => {
    let mounted = true;
    void fetchCities()
      .then((data) => {
        if (mounted) setCities(data);
      })
      .catch((e: unknown) => {
        if (!mounted) return;
        const message = e instanceof Error ? e.message : "Falha ao carregar cidades";
        setCitiesError(message);
      });
    return () => {
      mounted = false;
    };
  }, []);

  const filteredCities = useMemo<CityRow[]>(() => {
    if (cities === null) return [];
    if (estado === null || cityId !== null) return cities;
    return cities.filter((c) => c.estado === estado);
  }, [cities, estado, cityId]);

  const cityOptions: ComboboxOption[] = useMemo(
    () =>
      filteredCities.map((c) => ({
        value: String(c.id),
        label: `${c.nome} - ${c.estado}`,
        searchTerms: stripAccents(c.nome).toLowerCase(),
      })),
    [filteredCities],
  );

  const selectedCity = useMemo<CityRow | null>(() => {
    if (cityId === null || cities === null) return null;
    return cities.find((c) => c.id === cityId) ?? null;
  }, [cityId, cities]);

  const cidadeNome = selectedCity?.nome ?? "";
  const stateLockedByCity = selectedCity !== null;

  const missingRequired: string[] = [];
  if (!cliente.trim()) missingRequired.push("cliente");
  if (!empreendimento.trim()) missingRequired.push("empreendimento");
  if (!cidadeNome) missingRequired.push("cidade");
  const isValid = missingRequired.length === 0;

  const handleCityChange = (next: string | null): void => {
    if (next === null) {
      setCityId(null);
      return;
    }
    const id = Number.parseInt(next, 10);
    if (Number.isNaN(id) || cities === null) return;
    const city = cities.find((c) => c.id === id);
    if (!city) return;
    setCityId(id);
    setEstado(city.estado);
  };

  const handleStateChange = (next: string | null): void => {
    if (stateLockedByCity) return;
    setEstado(next);
  };

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>): void => {
    event.preventDefault();
    if (isDisabled) return;
    if (!isValid) {
      setShowErrors(true);
      return;
    }
    const metadata: ProjectMetadata = {
      cliente: cliente.trim(),
      empreendimento: empreendimento.trim(),
      cidade: cidadeNome,
      estado: estado ?? undefined,
    };
    onConfirm(metadata, cityId);
  };

  const showClienteError = showErrors && cliente.trim().length === 0;
  const showEmpreendimentoError = showErrors && empreendimento.trim().length === 0;
  const showCidadeError = showErrors && cidadeNome.length === 0;

  const citiesLoading = cities === null && citiesError === null;

  return (
    <form
      onSubmit={handleSubmit}
      className="flex w-full max-w-md flex-col gap-3 rounded-2xl border border-[var(--sidebar-border,rgba(255,255,255,0.1))] bg-[var(--sidebar-popover-bg,rgba(0,0,0,0.3))] p-4"
      aria-label="Metadados do projeto"
      aria-busy={loading}
    >
      <label className="flex flex-col gap-1 text-xs text-[var(--sidebar-text-muted)]">
        <span>
          Cliente
          <span className="text-red-400"> *</span>
        </span>
        <input
          type="text"
          value={cliente}
          onChange={(e) => setCliente(e.target.value)}
          autoComplete="off"
          spellCheck={false}
          disabled={isDisabled}
          aria-invalid={showClienteError}
          aria-required
          className={`${FIELD_CLASSES} ${showClienteError ? FIELD_INVALID_CLASSES : ""}`}
        />
      </label>

      <label className="flex flex-col gap-1 text-xs text-[var(--sidebar-text-muted)]">
        <span>
          Empreendimento
          <span className="text-red-400"> *</span>
        </span>
        <input
          type="text"
          value={empreendimento}
          onChange={(e) => setEmpreendimento(e.target.value)}
          autoComplete="off"
          spellCheck={false}
          disabled={isDisabled}
          aria-invalid={showEmpreendimentoError}
          aria-required
          className={`${FIELD_CLASSES} ${showEmpreendimentoError ? FIELD_INVALID_CLASSES : ""}`}
        />
      </label>

      <div className="flex flex-col gap-1 text-xs text-[var(--sidebar-text-muted)]">
        <span>
          Cidade
          <span className="text-red-400"> *</span>
        </span>
        <Combobox
          options={cityOptions}
          value={cityId !== null ? String(cityId) : null}
          onChange={handleCityChange}
          placeholder={citiesError ? "Erro ao carregar cidades" : "Selecione a cidade"}
          searchPlaceholder="Buscar cidade…"
          emptyMessage="Nenhuma cidade encontrada."
          disabled={isDisabled || citiesLoading || citiesError !== null}
          loading={citiesLoading}
          loadingMessage="Carregando cidades…"
          ariaLabel="Cidade"
          triggerClassName={showCidadeError ? "border-red-500/70" : ""}
        />
      </div>

      <div className="flex flex-col gap-1 text-xs text-[var(--sidebar-text-muted)]">
        <span>
          Estado (opcional)
          {stateLockedByCity ? (
            <span className="ml-1 text-[10px] text-[var(--sidebar-text-muted)]">
              (definido pela cidade)
            </span>
          ) : null}
        </span>
        <Combobox
          options={STATE_OPTIONS}
          value={estado}
          onChange={handleStateChange}
          placeholder="Selecione o estado"
          searchPlaceholder="Buscar UF ou nome…"
          emptyMessage="Nenhum estado encontrado."
          disabled={isDisabled || stateLockedByCity}
          ariaLabel="Estado"
        />
      </div>

      {citiesError ? (
        <p
          role="alert"
          className="rounded-md border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-xs text-amber-300"
        >
          Não consegui carregar a lista de cidades: {citiesError}
        </p>
      ) : null}

      {errorMessage ? (
        <p
          role="alert"
          className="rounded-md border border-red-500/40 bg-red-500/10 px-3 py-2 text-xs text-red-300"
        >
          {errorMessage}
        </p>
      ) : null}

      <div className="flex items-center justify-end gap-2 pt-1">
        <button
          type="submit"
          disabled={isDisabled || !isValid}
          className="flex items-center gap-2 rounded-full bg-white px-4 py-2 text-sm font-medium text-zinc-900 transition-colors hover:bg-zinc-200 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {loading ? (
            <>
              <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden />
              <span>Criando…</span>
            </>
          ) : (
            <span>Confirmar</span>
          )}
        </button>
      </div>
    </form>
  );
}
