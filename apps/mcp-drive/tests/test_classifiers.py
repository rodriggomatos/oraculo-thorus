"""Unit tests pra classifier registry e blacklist."""

from mcp_drive.classifiers import (
    CATEGORY_VOF_REVISAO,
    category_matches_name,
    get_classifier,
    is_blacklisted_file,
    is_blacklisted_folder,
    is_excluded_path,
    list_categories,
)


def test_all_5_categories_registered() -> None:
    expected = {
        "lista_definicoes",
        "ata_reuniao",
        "vof_revisao",
        "entrega_executivo_pdf",
        "arquivo_externo",
    }
    assert set(list_categories()) == expected


def test_vof_classifier_matches_name() -> None:
    classifier = get_classifier(CATEGORY_VOF_REVISAO)
    assert category_matches_name(classifier, "26009-VOF-HID-R02.pdf")
    assert category_matches_name(classifier, "26009-VOF-CLI_TEC OK.pdf")
    assert not category_matches_name(classifier, "ata reuniao.pdf")


def test_vof_excluded_path_obsoletos() -> None:
    classifier = get_classifier(CATEGORY_VOF_REVISAO)
    assert is_excluded_path(classifier, ["03 OBSOLETOS", "VOFs antigos"])
    assert not is_excluded_path(classifier, ["02 TRABALHO", "VOFs"])


def test_blacklist_modelos_at_depth_1() -> None:
    assert is_blacklisted_folder("05 MODELOS", depth_from_project=1)


def test_blacklist_modelos_at_depth_0() -> None:
    assert is_blacklisted_folder("05 MODELOS", depth_from_project=0)


def test_blacklist_xx_xx_xx_pattern() -> None:
    assert is_blacklisted_folder("xx-xx-xx-cliente")
    assert is_blacklisted_folder("XX-XX-XX-VAZIO")


def test_blacklist_limpando_etc() -> None:
    assert is_blacklisted_folder("LIMPANDO")
    assert is_blacklisted_folder("Limpo")
    assert is_blacklisted_folder("Nova pasta")


def test_blacklist_extensions() -> None:
    assert is_blacklisted_file("modelo.rvt")
    assert is_blacklisted_file("backup.bak")
    assert is_blacklisted_file("temp.tmp")
    assert is_blacklisted_file("arquivo.dwl")
    assert is_blacklisted_file("arquivo.dwl2")


def test_normal_files_not_blacklisted() -> None:
    assert not is_blacklisted_file("planilha.xlsx")
    assert not is_blacklisted_file("documento.pdf")
