"""Carga perezosa del modelo de entidades y del diccionario de habilidades.

Se cargan una sola vez y se reutilizan (evita recargar el modelo en cada CV).
"""

from functools import lru_cache

import spacy
from spacy.matcher import PhraseMatcher

from src import config
from src.data_loader.skills_lexicon import build_skill_lexicon

UNUSED_PIPES = ["tagger", "parser", "attribute_ruler", "lemmatizer"]

MODELO_ENTIDADES = "ner_dataturks_sm"


@lru_cache(maxsize=1)
def get_nlp():
    """Modelo de entidades entrenado (carga única)."""
    nlp = spacy.load(config.MODELS_DIR / MODELO_ENTIDADES)
    for pipe in UNUSED_PIPES:
        if pipe in nlp.pipe_names:
            nlp.disable_pipe(pipe)
    return nlp


@lru_cache(maxsize=1)
def get_skill_lexicon() -> set[str]:
    return build_skill_lexicon(config.REFS_DIR, None, include_job_skills=False)


@lru_cache(maxsize=1)
def get_skill_matcher() -> PhraseMatcher:
    """Buscador de habilidades por diccionario (carga única)."""
    nlp = get_nlp()
    matcher = PhraseMatcher(nlp.vocab, attr="LOWER")
    matcher.add("HABILIDAD", [nlp.make_doc(t) for t in get_skill_lexicon() if len(t) >= 2])
    return matcher
