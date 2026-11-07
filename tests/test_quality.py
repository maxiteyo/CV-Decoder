"""Pruebas de la métrica de parseabilidad (no requieren el modelo NER)."""

from src.parsing.quality import is_parseable, text_quality


def test_texto_con_palabras_suficientes_es_parseable():
    texto = "experiencia en java sql spring hibernate desarrollo backend " * 8
    assert is_parseable(texto) is True


def test_texto_muy_corto_no_es_parseable():
    assert is_parseable("Curriculum Vitae") is False


def test_texto_sin_letras_ni_numeros_no_es_parseable():
    texto = "!!!! ???? #### $$$$ %%%% &&&& **** " * 8
    assert is_parseable(texto) is False


def test_text_quality_mide_palabras_y_ratio():
    q = text_quality("uno dos tres 1234")
    assert q["palabras"] == 4
    assert 0.0 <= q["ratio_alfanumerico"] <= 1.0
