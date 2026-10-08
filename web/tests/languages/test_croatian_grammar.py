"""Tests for the grammar checks. The words carry the tags that classla gives."""

from tlhelper.languages.croatian import grammar


def word(text, lemma, upos, **feats):
    return {"text": text, "lemma": lemma, "upos": upos, "feats": feats}


def verb(text, lemma, person="1"):
    return word(text, lemma, "VERB", VerbForm="Fin", Person=person, Number="Sing")


def noun(text, lemma, case, gender="Fem", number="Sing"):
    return word(text, lemma, "NOUN", Case=case, Gender=gender, Number=number)


def adj(text, lemma, case, gender="Fem", number="Sing"):
    return word(text, lemma, "ADJ", Case=case, Gender=gender, Number=number)


def flagged(words, lexicon=None):
    grammar.check(words, lexicon)
    return {w["text"]: w["problems"] for w in words if w["problems"]}


def lexicon(*tagged):
    """A lexicon from (form, tag) pairs, like the dictionaries of classla."""
    return grammar.Lexicon(
        {form: form for form, _ in tagged}, {pair: pair[0] for pair in tagged}
    )


def test_spelling():
    lex = lexicon(("moj", "Ps1msn"), ("čamac", "Ncmsn"))
    words = [
        word("Moj", "moj", "DET"),
        adj("lebdići", "lebdić", "Nom", gender="Masc"),
        noun("čamac", "čamac", "Nom", gender="Masc"),
        word("Zagrebb", "Zagrebb", "PROPN"),
        word("3", "3", "NUM"),
        word(".", ".", "PUNCT"),
    ]
    problems = flagged(words, lex)
    assert list(problems) == ["lebdići"]
    assert "hrLex" in problems["lebdići"][0]
    # No lexicon, no spelling check.
    assert flagged(words) == {}


def test_repeated_word():
    je = ("je", "biti", "AUX")
    words = [word(*je), word("Je", "biti", "AUX"), word(*je), word(",", ",", "PUNCT")]
    words += [word(",", ",", "PUNCT")]
    problems = flagged(words)
    # One reason for each word, also where "je je" repeats as a phrase.
    assert problems == {"Je": ["'Je' repeats."], "je": ["'je' repeats."]}
    assert [bool(w["problems"]) for w in words] == [False, True, True, False, False]


def test_repeated_phrase():
    pun = ("pun", "pun", "ADJ")
    je = ("je", "biti", "AUX")
    words = [word("čamac", "čamac", "NOUN")]
    words += [word(*pun), word(*je), word(*pun), word(*je), word(*pun), word(*je)]
    words += [word("jegulja", "jegulja", "NOUN")]
    flagged(words)
    assert [w["problems"] for w in words] == [
        [],
        [],
        [],
        ["'pun je' repeats."],
        ["'pun je' repeats."],
        ["'pun je' repeats."],
        ["'pun je' repeats."],
        [],
    ]
    # Punctuation between the copies is a normal sentence: "Da, da, znam."
    da = ("da", "da", "PART")
    comma = (",", ",", "PUNCT")
    assert flagged([word(*da), word(*comma), word(*da), word(*comma)]) == {}


def test_genitive_after_pun():
    pun = adj("pun", "pun", "Nom", gender="Masc")
    je = word("je", "biti", "AUX", VerbForm="Fin", Person="3")
    problems = flagged([pun, je, noun("kava", "kava", "Nom")])
    assert list(problems) == ["kava"]
    assert "genitive" in problems["kava"][0]
    # Correct: a genitive noun, and pun that agrees with its noun.
    assert flagged([adj("puna", "pun", "Nom"), noun("vode", "voda", "Gen")]) == {}
    assert flagged([pun, je, noun("čamac", "čamac", "Nom", gender="Masc")]) == {}


def test_a_form_with_a_second_reading_is_not_flagged():
    # The tagger says nominative singular, but "jegulja" is also the genitive
    # plural, so "pun je jegulja" is correct.
    lex = lexicon(("pun", "Agpmsny"), ("jegulja", "Ncfsn"), ("jegulja", "Ncfpg"))
    words = [adj("pun", "pun", "Nom", gender="Masc"), noun("jegulja", "jegulja", "Nom")]
    assert flagged(words, lex) == {}
    assert list(flagged(words)) == ["jegulja"]

    # "grad" is the nominative and the accusative.
    lex = lexicon(
        ("vidim", "Vmr1s"), ("u", "Sa"), ("grad", "Ncmsn"), ("grad", "Ncmsan")
    )
    grad = noun("grad", "grad", "Nom", gender="Masc")
    assert flagged([verb("Vidim", "vidjeti"), grad], lex) == {}
    assert flagged([word("u", "u", "ADP", Case="Acc"), grad], lex) == {}
    assert list(flagged([word("u", "u", "ADP", Case="Loc"), grad], lex)) == ["grad"]


def test_every_word_gets_a_problems_list():
    words = [verb("Pijem", "piti"), noun("kavu", "kava", "Acc")]
    assert flagged(words) == {}
    assert [w["problems"] for w in words] == [[], []]


def test_nominative_object():
    problems = flagged([verb("Pijem", "piti"), noun("kava", "kava", "Nom")])
    assert list(problems) == ["kava"]
    assert "'Pijem'" in problems["kava"][0]
    assert "nominative" in problems["kava"][0]


def test_nominative_object_after_a_participle():
    words = [
        word("Pio", "piti", "VERB", VerbForm="Part", Gender="Masc", Number="Sing"),
        word("sam", "biti", "AUX", VerbForm="Fin", Person="1", Number="Sing"),
        noun("kava", "kava", "Nom"),
    ]
    assert list(flagged(words)) == ["kava"]


def test_third_person_subject_is_not_flagged():
    words = [noun("Žena", "žena", "Nom"), verb("pije", "piti", person="3")]
    assert flagged(words) == {}


def test_verbs_with_a_second_nominative_are_not_flagged():
    words = [
        word("Postao", "postati", "VERB", VerbForm="Part"),
        word("sam", "biti", "AUX", VerbForm="Fin", Person="1"),
        noun("učitelj", "učitelj", "Nom", gender="Masc"),
    ]
    assert flagged(words) == {}
    words = [
        word("Ja", "ja", "PRON", Case="Nom"),
        word("sam", "biti", "AUX", VerbForm="Fin", Person="1"),
        noun("učitelj", "učitelj", "Nom", gender="Masc"),
    ]
    assert flagged(words) == {}


def test_nominative_after_kao_is_not_flagged():
    words = [
        verb("Radim", "raditi"),
        word("kao", "kao", "SCONJ"),
        noun("učitelj", "učitelj", "Nom", gender="Masc"),
    ]
    assert flagged(words) == {}


def test_two_finite_verbs_are_not_checked():
    # "Mislim da je kava dobra": kava is the subject of the second clause.
    words = [
        verb("Mislim", "misliti"),
        word("da", "da", "SCONJ"),
        word("je", "biti", "AUX", VerbForm="Fin", Person="3"),
        noun("kava", "kava", "Nom"),
        adj("dobra", "dobar", "Nom"),
    ]
    assert flagged(words) == {}


def test_preposition_case():
    words = [
        verb("Razgovaram", "razgovarati"),
        word("s", "sa", "ADP", Case="Ins"),
        adj("dobar", "dobar", "Nom", gender="Masc"),
        noun("prijatelj", "prijatelj", "Nom", gender="Masc"),
    ]
    problems = flagged(words)
    assert list(problems) == ["dobar", "prijatelj"]
    # One reason for each word: the object check leaves "prijatelj" alone.
    assert problems["prijatelj"] == [
        "The preposition 's' takes the instrumental here, but this form is nominative."
    ]


def test_preposition_check_stops_at_the_noun_and_at_a_number():
    words = [
        word("s", "sa", "ADP", Case="Ins"),
        noun("prijateljem", "prijatelj", "Ins", gender="Masc"),
        noun("Ane", "Ana", "Gen"),
    ]
    assert flagged(words) == {}
    words = [
        word("s", "sa", "ADP", Case="Ins"),
        word("dva", "dva", "NUM", NumType="Card"),
        noun("prijatelja", "prijatelj", "Gen", gender="Masc"),
    ]
    assert flagged(words) == {}


def test_agreement():
    words = [
        verb("Vidim", "vidjeti"),
        adj("lijepa", "lijep", "Nom"),
        noun("kuću", "kuća", "Acc"),
    ]
    problems = flagged(words)
    assert problems == {
        "lijepa": [
            (
                "Does not agree with 'kuću': this form is nominative, but the noun is"
                " accusative (case)."
            )
        ]
    }


def test_agreement_reaches_over_a_second_adjective():
    words = [
        adj("moj", "moj", "Nom", gender="Masc"),
        adj("lijepa", "lijep", "Nom"),
        noun("kuća", "kuća", "Nom"),
    ]
    words[0]["upos"] = "DET"
    problems = flagged(words)
    assert list(problems) == ["moj"]
    assert "(gender)" in problems["moj"][0]


def test_adjective_without_a_noun_is_not_checked():
    words = [
        noun("Kuća", "kuća", "Nom"),
        word("je", "biti", "AUX", VerbForm="Fin", Person="3"),
        adj("lijepa", "lijep", "Nom"),
        word(".", ".", "PUNCT"),
    ]
    assert flagged(words) == {}
