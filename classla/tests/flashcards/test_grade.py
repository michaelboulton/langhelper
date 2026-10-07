import pytest

from tlhelper.flashcards.grade import AGAIN, GOOD, HARD, diff, grade
from tlhelper.languages import ENGLISH, LANGUAGES
from tlhelper.languages.base import Grading

HR, DE = LANGUAGES["hr"].info.grading, LANGUAGES["de"].info.grading
FR, IT = LANGUAGES["fr"].info.grading, LANGUAGES["it"].info.grading
# No language of the app has such a script yet: no spaces, and a combining
# mark makes another word.
NO_SPACES = Grading(spaces=False, slip_letters=0, marks="keep")
# Also no language of the app yet: nobody types the vowel marks, and some
# letters have a plain form.
VOWEL_MARKS = Grading(marks="ignore", ignored="ـ", plain_letters=(("ة", ("ه",)),))


@pytest.mark.parametrize(
    ("typed", "answers", "rating", "rules"),
    [
        ("Pijem kavu.", ["Pijem kavu."], GOOD, HR),
        ("  pijem   KAVU ", ["Pijem kavu."], GOOD, HR),
        ("Wie geht's?", ["Wie geht’s"], GOOD, DE),
        # No diacritics on the keyboard.
        ("kuca", ["kuća"], HARD, HR),
        ("medjutim", ["međutim"], HARD, HR),
        ("strasse", ["Straße"], HARD, DE),
        ("Maedchen", ["Mädchen"], HARD, DE),
        ("Madchen", ["Mädchen"], HARD, DE),
        ("J'ai ete a l'ecole", ["J’ai été à l’école."], HARD, FR),
        ("le coeur", ["le cœur"], HARD, FR),
        ("le garcon", ["le garçon"], HARD, FR),
        ("Perche la citta e bella?", ["Perché la città è bella?"], HARD, IT),
        # "dj" is only Croatian, and "ss" is only German.
        ("medjutim", ["međutim"], AGAIN, DE),
        ("strasse", ["Straße"], AGAIN, HR),
        ("le coeur", ["le cœur"], AGAIN, DE),
        # One wrong letter is a slip. A wrong ending, or two wrong words, is not.
        ("Pijem kavu svako jutre", ["Pijem kavu svako jutro."], HARD, HR),
        ("Idem u grad s prijatelj", ["Idem u grad s prijateljem."], AGAIN, HR),
        ("Pijem kava svaki jutro", ["Pijem kavu svako jutro."], AGAIN, HR),
        ("Pijem čaj.", ["Pijem kavu."], AGAIN, HR),
        ("", ["kuća"], AGAIN, HR),
        ("i drink cofee", ["I drink coffee."], HARD, ENGLISH.info.grading),
        # A script with no spaces: punctuation is nothing, and not a space.
        ("こんにちは田中さん", ["こんにちは、田中さん。"], GOOD, NO_SPACES),
        ("こんにちは 田中さん", ["こんにちは、田中さん。"], GOOD, NO_SPACES),
        # A mark makes another word: か for が, and "white" for "rice".
        ("か", ["が"], AGAIN, NO_SPACES),
        ("ขาว", ["ข้าว"], AGAIN, NO_SPACES),
        # One wrong sign is a wrong word, and not a slip.
        ("学生", ["先生"], AGAIN, NO_SPACES),
        # Vowel marks never count, in the answer of the deck or in the typed one.
        ("كتاب", ["كِتَابٌ"], GOOD, VOWEL_MARKS),
        ("كِتَاب", ["كتاب"], GOOD, VOWEL_MARKS),
        ("שלום", ["שָׁלוֹם"], GOOD, VOWEL_MARKS),
        # The tatweel only makes a word longer.
        ("كتـــاب", ["كتاب"], GOOD, VOWEL_MARKS),
        # A plain letter is right, but hard. Wrong letters are wrong.
        ("مدرسه", ["مَدْرَسَة"], HARD, VOWEL_MARKS),
        # The hamza on an alef is a combining mark for Unicode, so it goes
        # with the vowel marks.
        ("اكل", ["أَكَلَ"], GOOD, VOWEL_MARKS),
        ("كلب", ["كِتَابٌ"], AGAIN, VOWEL_MARKS),
    ],
)
def test_rating(typed, answers, rating, rules):
    assert grade(typed, answers, rules)["rating"] == rating


def test_the_default_rules_are_wrong_for_a_script_with_no_spaces():
    # Why Grading exists: a comma becomes a space, and a mark is "an accent".
    assert grade("こんにちは田中さん", ["こんにちは、田中さん"])["rating"] == HARD
    assert grade("か", ["が"])["rating"] == HARD


def test_the_closest_of_several_answers_counts():
    result = grade("zdravo", ["bok", "zdravo"])
    assert (result["rating"], result["answer"]) == (GOOD, "zdravo")
    assert grade("bog", ["bok", "zdravo"])["answer"] == "bok"


def test_a_mark_that_never_counts_is_no_error_in_the_diff():
    assert diff("كتاب", "كِتَابٌ", VOWEL_MARKS) == [["equal", "كِتَابٌ"]]
    # With the default rules, each mark is a missing letter.
    assert ["insert", "ِ"] in diff("كتاب", "كِتَابٌ")


def test_diff():
    assert diff("Pijem kava", "Pijem kavu") == [
        ["equal", "Pijem kav"],
        ["delete", "a"],
        ["insert", "u"],
    ]
    # Case is no difference, and the answer gives the letters.
    assert diff("pijem", "Pijem") == [["equal", "Pijem"]]
    assert diff("", "da") == [["insert", "da"]]
    # Punctuation is no error, as in the grade: missing, extra or different.
    assert diff("dobro jutro", "Dobro jutro.") == [["equal", "Dobro jutro."]]
    assert diff("dobro jutro!", "Dobro jutro") == [["equal", "Dobro jutro"]]
    assert diff("da - ne", "Da, ne.") == [["equal", "Da, ne."]]
    assert diff("da, na.", "Da, ne") == [
        ["equal", "Da, n"],
        ["delete", "a"],
        ["insert", "e"],
    ]
    assert diff("na", "Ne.") == [
        ["equal", "N"],
        ["delete", "a"],
        ["insert", "e"],
        ["equal", "."],
    ]
