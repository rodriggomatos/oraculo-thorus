import { NextResponse } from "next/server";
import { getServerSupabase } from "@/lib/supabase/server";


export type CityDTO = {
  id: number;
  nome: string;
  estado: string;
};


type CityRow = {
  ibge_code: string;
  nome: string;
  estado: string;
};


export const revalidate = 86400;


export async function GET(): Promise<NextResponse> {
  let supabase;
  try {
    supabase = await getServerSupabase();
  } catch (error) {
    return NextResponse.json(
      {
        detail: `Supabase não configurado: ${
          error instanceof Error ? error.message : String(error)
        }`,
      },
      { status: 500 },
    );
  }

  const { data, error } = await supabase
    .from("city")
    .select("ibge_code, nome, estado")
    .order("estado", { ascending: true })
    .order("nome", { ascending: true });

  if (error) {
    return NextResponse.json(
      { detail: `Falha ao ler cidades: ${error.message}` },
      { status: 502 },
    );
  }

  const rows = (data ?? []) as CityRow[];
  const cities: CityDTO[] = rows.map((r) => ({
    id: Number.parseInt(r.ibge_code, 10),
    nome: r.nome,
    estado: r.estado,
  }));

  return NextResponse.json(
    { cities },
    {
      headers: {
        "Cache-Control":
          "public, max-age=86400, stale-while-revalidate=604800",
      },
    },
  );
}
