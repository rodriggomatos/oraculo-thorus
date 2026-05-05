"""Filtra a Master R04 pelas categorias LDP ativas pra um projeto."""

from collections.abc import Iterable

from oraculo_ai.ldp.master_reader import MasterRow


def filter_master_for_active(
    master: Iterable[MasterRow],
    active_discipline_names: Iterable[str],
) -> list[MasterRow]:
    """Mantém apenas as perguntas cuja disciplina bate com alguma categoria ativa.

    Comparação case-insensitive, ignorando whitespace nas pontas — defensivo
    contra inconsistência sutil entre master e ldp_discipline.
    """
    active = {name.strip().casefold() for name in active_discipline_names}
    return [row for row in master if row.disciplina.strip().casefold() in active]
