"use client";

import type { CityDTO } from "@/app/api/cities/route";


let _citiesPromise: Promise<CityDTO[]> | null = null;


export async function fetchCities(): Promise<CityDTO[]> {
  if (_citiesPromise) return _citiesPromise;

  _citiesPromise = (async (): Promise<CityDTO[]> => {
    const response = await fetch("/api/cities");
    if (!response.ok) {
      _citiesPromise = null;
      throw new Error(`GET /api/cities falhou (${response.status})`);
    }
    const body = (await response.json()) as { cities: CityDTO[] };
    return body.cities;
  })();

  return _citiesPromise;
}


export function stripAccents(text: string): string {
  return text.normalize("NFD").replace(/\p{Diacritic}/gu, "");
}
