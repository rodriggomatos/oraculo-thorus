export type BrState = {
  code: string;
  nome: string;
};


export const BR_STATES: readonly BrState[] = [
  { code: "AC", nome: "Acre" },
  { code: "AL", nome: "Alagoas" },
  { code: "AP", nome: "Amapá" },
  { code: "AM", nome: "Amazonas" },
  { code: "BA", nome: "Bahia" },
  { code: "CE", nome: "Ceará" },
  { code: "DF", nome: "Distrito Federal" },
  { code: "ES", nome: "Espírito Santo" },
  { code: "GO", nome: "Goiás" },
  { code: "MA", nome: "Maranhão" },
  { code: "MT", nome: "Mato Grosso" },
  { code: "MS", nome: "Mato Grosso do Sul" },
  { code: "MG", nome: "Minas Gerais" },
  { code: "PA", nome: "Pará" },
  { code: "PB", nome: "Paraíba" },
  { code: "PR", nome: "Paraná" },
  { code: "PE", nome: "Pernambuco" },
  { code: "PI", nome: "Piauí" },
  { code: "RJ", nome: "Rio de Janeiro" },
  { code: "RN", nome: "Rio Grande do Norte" },
  { code: "RS", nome: "Rio Grande do Sul" },
  { code: "RO", nome: "Rondônia" },
  { code: "RR", nome: "Roraima" },
  { code: "SC", nome: "Santa Catarina" },
  { code: "SP", nome: "São Paulo" },
  { code: "SE", nome: "Sergipe" },
  { code: "TO", nome: "Tocantins" },
] as const;
