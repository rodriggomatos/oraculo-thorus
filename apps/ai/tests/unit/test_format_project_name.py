"""Unit tests pro format_project_name — padrão Thórus do projects.name."""

from oraculo_ai.projects import format_project_name


def test_full_format_with_all_fields():
    assert (
        format_project_name(
            project_number=26033,
            client="Teste rodrigo",
            empreendimento="teste empreendimento",
            cidade="Pocrane",
            estado="MG",
        )
        == "26033 - Teste rodrigo - teste empreendimento - Pocrane - MG"
    )


def test_replaces_missing_fields_with_dash():
    assert (
        format_project_name(
            project_number=26000,
            client=None,
            empreendimento="Stylo",
            cidade=None,
            estado="SC",
        )
        == "26000 - — - Stylo - — - SC"
    )


def test_treats_whitespace_only_as_missing():
    assert (
        format_project_name(
            project_number=26001,
            client="Acme",
            empreendimento="Torre A",
            cidade="   ",
            estado="",
        )
        == "26001 - Acme - Torre A - — - —"
    )


def test_preserves_internal_spaces_and_unicode():
    assert (
        format_project_name(
            project_number=26012,
            client="João da Silva & Cia.",
            empreendimento="Edifício São José",
            cidade="São José",
            estado="SC",
        )
        == "26012 - João da Silva & Cia. - Edifício São José - São José - SC"
    )
