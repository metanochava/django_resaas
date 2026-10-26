"""Guards against a real bug found live: a language file (saas/lang/eses.py,
when Spanish still shipped) was almost entirely another language's text.
RESAAS ships pt-pt and en-us (English is the canonical key, so it needs no
file): this checks that ptpt.py is written in Portuguese, with a light
vocabulary heuristic (common words of neighbouring languages that
Portuguese doesn't use), so a copy-paste of another language fails loudly."""
from django_resaas.saas.lang import ptpt

# common closed-class words unique enough to Spanish / French that two of
# them in the Portuguese file mean it is (at least partly) in that language
OTHER_LANGUAGE_TELLS = {
    "es-es": ["usted", "aquí", "también", "ñ"],
    "fr-fr": ["où", "être", "vous", "qu'", "n'est"],
}


def test_ptpt_has_portuguese_text():
    blob = " ".join(ptpt.key_value.values()).lower()

    assert sum(1 for w in ["não", "você", "utilizador", "ão "] if w in blob) >= 2


def test_ptpt_is_not_written_in_a_different_language():
    blob = " ".join(ptpt.key_value.values()).lower()

    for other_lang, words in OTHER_LANGUAGE_TELLS.items():
        hits = sum(1 for w in words if w in blob)
        # one accidental match is expected (loanwords, short substrings)
        assert hits < 2, (
            f"ptpt.py looks like it's written in {other_lang} - "
            f"found {hits}/{len(words)} {other_lang} tell-words"
        )
