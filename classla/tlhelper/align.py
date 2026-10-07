"""Link each word of the study language to the English word with the same
meaning. The examples are Croatian.

DeepL does not say which word became which. So this uses the English glosses
of Wiktionary (Language.glosses): "kuća" links to the English word whose lemma
is "house". A word with no counterpart gets no link. That is correct for a
word that only exists for the grammar of one language: "se", or the English
"the" and "do".
"""

from .languages import Language

NO_LINK_UPOS = {"PUNCT", "SYM"}
# guesses() only pairs words with a meaning of their own. A free "se" or "the"
# has no counterpart.
GUESS_UPOS = {"NOUN", "PROPN", "VERB", "ADJ", "ADV", "NUM"}
# How far a guess can be from the place that the links near it give. English
# adds words ("na tržnici" is "at the market"), so the place is not exact.
MAX_SHIFT = 2
# How much one step of gloss rank costs, against the distance in the text
# (0 to 1). The main meaning of a word wins over a side meaning that is a
# little closer: "ići" is "go", not "do".
RANK_COST = 0.05
MAX_RANK = 10
# With no sentence pairs, a link must stay this close to its place in the text.
MAX_DISTANCE = 0.2


def match_rank(study: dict, english: dict, glosses: dict[str, int]) -> int | None:
    """None for no match, else the rank of the match. 0 is the best."""
    if study["upos"] in NO_LINK_UPOS or english["upos"] in NO_LINK_UPOS:
        return None
    text, lemma = english["text"].lower(), english["lemma"].lower()
    # A name and a number stay the same in both languages.
    if text in (study["text"].lower(), study["lemma"].lower()):
        return 0
    # The "to" of an infinitive and the "do" of a question or a negation have
    # no meaning of their own. "must" and "will" do: "morate", "ću".
    if english["upos"] == "PART" and lemma != "not":
        return None
    if english["upos"] == "AUX" and lemma == "do":
        return None
    # "dugo" is "for a long time": the link goes to "long", not to "for". A
    # Croatian case often stands for an English preposition ("vlakom", by
    # train), and that preposition has no word to link to.
    if english["upos"] == "ADP" and study["upos"] != "ADP":
        return None
    # "jutros" is "this morning": the link goes to "morning", not to "this".
    if english["upos"] == "DET" and study["upos"] not in ("DET", "PRON"):
        return None
    ranks = [glosses[word] for word in (lemma, text) if word in glosses]
    return min(min(ranks), MAX_RANK) if ranks else None


def align(language: Language, study: list[dict], english: list[dict]) -> dict:
    """The links and the guesses for a whole text. study and english are lists
    of sentences ({"words": [...]}). The pairs hold indexes over the words of
    all sentences in order, the study language first.

    DeepL mostly keeps the sentences. If both sides have the same number of
    sentences, a word only links inside its own sentence. If not, the text is
    one long sentence, and a link must stay close to its place in the text."""
    if len(study) == len(english):
        blocks = [(s["words"], t["words"], None) for s, t in zip(study, english)]
    else:
        source = [word for s in study for word in s["words"]]
        target = [word for t in english for word in t["words"]]
        blocks = [(source, target, MAX_DISTANCE)]
    result = {"links": [], "guesses": []}
    start_source = start_target = 0
    for source, target, max_distance in blocks:
        found = links(language, source, target, max_distance)
        for name, pairs in (
            ("links", found),
            ("guesses", guesses(source, target, found)),
        ):
            result[name] += [[i + start_source, j + start_target] for i, j in pairs]
        start_source += len(source)
        start_target += len(target)
    return result


def links(
    language: Language,
    study: list[dict],
    english: list[dict],
    max_distance: float | None = None,
) -> list[list[int]]:
    """Pairs [study index, english index]. A word is in one pair at most.
    If a word matches in several places ("je" and two times "is"), the pair
    with the closest relative position wins, because a translation mostly
    keeps the order. The distance is 0 to 1, and max_distance is its limit."""
    # For each study word, its English candidates with the best one first.
    options: dict[int, list[int]] = {}
    costs = {}
    for i, source in enumerate(study):
        glosses = dict(
            language.glosses(source["text"], source["lemma"], source["upos"])
        )
        extra = language.extra_glosses.get(source["lemma"].lower(), [])
        for rank, word in enumerate(extra):
            glosses.setdefault(word, rank)
        for j, target in enumerate(english):
            rank = match_rank(source, target, glosses)
            distance = abs(i / len(study) - j / len(english))
            if rank is not None and (max_distance is None or distance <= max_distance):
                costs[i, j] = distance + rank * RANK_COST
                options.setdefault(i, []).append(j)
    for i, found in options.items():
        found.sort(key=lambda j: costs[i, j])

    # "morate imati" and "must have": morati is also "have to", and "have" is
    # a little closer to it. A plain best-first choice gives "have" to morate
    # and leaves imati with nothing. So a word can take an English word from
    # another word, if that one then finds another (Kuhn's matching).
    owner: dict[int, int] = {}

    def assign(i: int, seen: set[int]) -> bool:
        for j in options[i]:
            if j in seen:
                continue
            seen.add(j)
            if j not in owner or assign(owner[j], seen):
                owner[j] = i
                return True
        return False

    # The words with the best first choice go first, so they keep it if they can.
    for i in sorted(options, key=lambda i: costs[i, options[i][0]]):
        assign(i, set())
    return sorted([i, j] for j, i in owner.items())


def guesses(
    study: list[dict], english: list[dict], pairs: list[list[int]]
) -> list[list[int]]:
    """More pairs, for words that the glosses do not have ("plutajući" and
    "floating"). The links near a free word say where its English word is:

        moj   plutajući  čamac
        My    floating   boat

    "plutajući" is one word after "moj", so its English word is about one word
    after "My". A free English word with the same part of speech, at most
    MAX_SHIFT words from that place, is a pair. The closest pairs go first,
    and a word is in one pair at most. The page draws a guess as a dashed
    line."""
    # The start and the end of both texts are links too.
    anchors = [(-1, -1), *pairs, (len(study), len(english))]
    used_source = {i for i, _ in pairs}
    used_target = {j for _, j in pairs}
    candidates = []
    for i, source in enumerate(study):
        if i in used_source or source["upos"] not in GUESS_UPOS:
            continue
        before = max((a for a in anchors if a[0] < i), key=lambda a: a[0])
        after = min((a for a in anchors if a[0] > i), key=lambda a: a[0])
        for j, target in enumerate(english):
            if j in used_target or target["upos"] != source["upos"]:
                continue
            shift = min(abs(j - (a[1] + i - a[0])) for a in (before, after))
            if shift <= MAX_SHIFT:
                candidates.append((shift, i, j))

    found = []
    for _, i, j in sorted(candidates):
        if i not in used_source and j not in used_target:
            used_source.add(i)
            used_target.add(j)
            found.append([i, j])
    return sorted(found)
