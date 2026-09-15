"""Guards against a real bug found live: saas/lang/eses.py (meant to be
Spanish, pt-pt/en-us/fr-fr's sibling for es-es) was almost entirely
French text (only 2 of ~600 entries were actually Spanish) - every
Spanish-locale user saw French instead. Checks structural parity
(same keys as ptpt.py, the reference file) and a light per-language
vocabulary heuristic (a handful of very common words each language
uses that its neighbours don't) so a language file silently containing
another language's text fails loudly instead of shipping unnoticed."""
import pytest

from django_resaas.saas.lang import ptpt, frfr, eses

pytestmark = pytest.mark.django_db

# A handful of common closed-class words unique enough to each language
# that seeing them in another language's file is a strong signal of a
# copy-paste mistake (this is exactly how the ptpt/eses mix-up in
# saas/lang/eses.py history would have been caught).
LANG_TELLS = {
    "pt-pt": (ptpt, ["não", "você", "utilizador", "ão "]),
    "fr-fr": (frfr, ["où", "être", "vous", "qu'", "n'est"]),
    "es-es": (eses, ["usted", "aquí", "también", "ñ"]),
}


def test_all_language_files_have_the_same_keys_as_ptpt():
    reference = set(ptpt.key_value.keys())
    for name, module in (("frfr", frfr), ("eses", eses)):
        keys = set(module.key_value.keys())
        missing = reference - keys
        assert not missing, f"{name}.py is missing keys present in ptpt.py: {sorted(missing)[:10]}"


@pytest.mark.parametrize("lang_name", ["pt-pt", "fr-fr", "es-es"])
def test_language_file_is_not_written_in_a_different_language(lang_name):
    module, tells = LANG_TELLS[lang_name]
    blob = " ".join(module.key_value.values()).lower()

    other_tells = {
        other: words
        for other, (_, words) in LANG_TELLS.items()
        if other != lang_name
    }

    for other_lang, words in other_tells.items():
        hits = sum(1 for w in words if w in blob)
        # one accidental match is expected (loanwords, short
        # substrings); two or more of another language's very common
        # closed-class tell-words showing up means the file is
        # actually (at least partly) written in it - this exact
        # threshold is what catches saas/lang/eses.py's real bug
        # (only 2/5 French tells "être"/"vous" happened to appear,
        # which was still enough to prove the file was French).
        assert hits < 2, (
            f"{lang_name} language file looks like it's written in "
            f"{other_lang} - found {hits}/{len(words)} {other_lang} tell-words"
        )
