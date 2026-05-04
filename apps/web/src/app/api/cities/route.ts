import { NextResponse } from "next/server";


export type CityDTO = {
  id: number;
  nome: string;
  estado: string;
};


type IbgeMunicipio = {
  id: number;
  nome: string;
  microrregiao?: {
    mesorregiao?: {
      UF?: {
        sigla?: string;
      };
    };
  };
};


const IBGE_URL = "https://servicodados.ibge.gov.br/api/v1/localidades/municipios";


export async function GET(): Promise<NextResponse> {
  let payload: IbgeMunicipio[];
  try {
    const upstream = await fetch(IBGE_URL, {
      next: { revalidate: 86400 },
    });
    if (!upstream.ok) {
      return NextResponse.json(
        { detail: `IBGE retornou ${upstream.status}` },
        { status: 502 },
      );
    }
    payload = (await upstream.json()) as IbgeMunicipio[];
  } catch (error) {
    return NextResponse.json(
      {
        detail: `Falha ao consultar IBGE: ${
          error instanceof Error ? error.message : String(error)
        }`,
      },
      { status: 502 },
    );
  }

  const cities: CityDTO[] = [];
  for (const m of payload) {
    const sigla = m.microrregiao?.mesorregiao?.UF?.sigla;
    if (!sigla) continue;
    cities.push({
      id: m.id,
      nome: m.nome,
      estado: sigla,
    });
  }

  cities.sort((a, b) => a.nome.localeCompare(b.nome, "pt-BR"));

  return NextResponse.json(
    { cities },
    {
      headers: {
        "Cache-Control": "public, max-age=86400, stale-while-revalidate=604800",
      },
    },
  );
}
