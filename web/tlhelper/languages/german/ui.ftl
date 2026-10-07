# The text of the page in German. english/ui.ftl is the complete catalog and
# has the notes on each message and on its variables. A message that is not
# here shows in English.
#
# A machine wrote the first version of this file. A person who speaks German
# must read it, the grammar terms most of all.

## The names of the languages

language-name-en = Englisch
language-name-hr = Kroatisch
language-name-de = Deutsch
language-name-fr = Französisch
language-name-it = Italienisch

language-hr-light-note = Das kleine kroatische Modell hat keine Rechtschreibprüfung und findet manche Kasusfehler nicht (Pijem kava). Die großen Modelle finden mehr.

language-en-tag-name = Penn-Treebank-Tag
language-hr-tag-name = MULTEXT-East-Tag
language-de-tag-name = STTS-Tag
language-it-tag-name = ISDT-Tag

## The top of the page

tab-breakdown = Analyse
tab-cards = Karteikarten
tab-progress = Fortschritt
locale-label = Sprache der Seite

## The breakdown tab

breakdown-title = Satzanalyse: { $language }
breakdown-intro = Geben Sie einen Satz in der Sprache { $language } ein, oder einen englischen Satz, um ihn in der Sprache { $language } zu bekommen. Jedes Wort bekommt eine Farbe für seine Wortart. Wählen Sie ein Wort für die Einzelheiten.
breakdown-language = Sprache
breakdown-source-study = Ich gebe { $language } ein
breakdown-source-english = Ich gebe Englisch ein und bekomme die Übersetzung: { $language }
option-heavy = Große Modelle (genauer, und die erste Anfrage wartet, bis sie geladen sind)
option-nonstandard = Umgangssprache oder Chat-Text (Modelle für Slang und fehlende diakritische Zeichen)
option-translate = Ins Englische übersetzen
option-time-limit = Zeitlimit
unit-seconds = s
breakdown-cancel = Abbrechen
breakdown-go = Analysieren
breakdown-no-translation = Keine Übersetzung: { $error }.
breakdown-side-label = { $language }:

status-working = In Arbeit.
status-working-heavy = In Arbeit. Die erste Anfrage mit den großen Modellen wartet, bis sie geladen sind, bis zu einer Minute.
status-canceled = Abgebrochen.
status-timeout = Keine Antwort nach { $seconds } s. Wenn der Server noch Modelle lädt, versuchen Sie es gleich noch einmal oder erhöhen Sie das Zeitlimit.
status-models = Modelle: { $models }.
status-loading-models = Der Server lädt die Modelle ({ $models }). Eine Anfrage wartet, bis sie bereit sind.
model-name = { $language }, { $variant ->
    [light] klein
    [heavy] groß
    [nonstandard] für Umgangssprache
   *[other] { $variant }
}

## The table of the selected word

detail-accent = Akzent
detail-accent-clitic = ein Klitikon: kein eigener Akzent, es lehnt sich an das nächste oder das vorige Wort an
detail-accent-dictionary = die Wörterbuchform. Der Akzent kann sich in dieser Form des Wortes verschieben
detail-accent-ambiguous = mehrere Lesarten, die Grammatik entscheidet nicht
detail-reading = Aussprache
detail-lemma = Grundform (Lemma)
detail-upos = Wortart
detail-seen = So oft wurde dieses Lemma gesehen
detail-dictionaries = Wörterbücher

accents-legend = Akzentzeichen: ȁ kurz fallend, ȃ lang fallend, à kurz steigend, á lang steigend, ā langer Vokal ohne Betonung. Eine Form in (Klammern) ist die Wörterbuchform, und der Akzent kann in der Form im Satz anders sein. Quelle: Wiktionary, CC BY-SA.

## The parts of speech

upos-NOUN = Substantiv
upos-PROPN = Eigenname
upos-VERB = Verb
upos-AUX = Hilfsverb
upos-ADJ = Adjektiv
upos-ADV = Adverb
upos-PRON = Pronomen
upos-DET = Artikelwort
upos-ADP = Präposition
upos-CCONJ = nebenordnende Konjunktion
upos-SCONJ = unterordnende Konjunktion
upos-PART = Partikel
upos-NUM = Zahlwort
upos-INTJ = Interjektion
upos-PUNCT = Satzzeichen
upos-SYM = Symbol
upos-X = Sonstiges

## The names of the features

feat-Case = Kasus
feat-Gender = Genus
feat-Number = Numerus
feat-Person = Person
feat-Tense = Tempus
feat-Mood = Modus
feat-VerbForm = Verbform
feat-Voice = Genus Verbi
feat-Degree = Steigerung
feat-Definite = Definitheit
feat-Animacy = Belebtheit
feat-PronType = Art des Pronomens
feat-Poss = Possessiv
feat-Reflex = Reflexiv
feat-Polarity = Polarität
feat-NumType = Art des Zahlworts
feat-Number-psor = Numerus des Besitzers
feat-Gender-psor = Genus des Besitzers
feat-Variant = Variante
feat-Foreign = Fremdwort
feat-Abbr = Abkürzung
feat-Clitic = Klitikon

## The values of the features

featval-Nom = Nominativ
featval-Gen = Genitiv
featval-Dat = Dativ
featval-Acc = Akkusativ
featval-Voc = Vokativ
featval-Loc = Lokativ
featval-Ins = Instrumental
featval-Masc = Maskulinum
featval-Fem = Femininum
featval-Neut = Neutrum
featval-Sing = Singular
featval-Plur = Plural
featval-Pres = Präsens
featval-Past = Vergangenheit
featval-Fut = Futur
featval-Imp = Imperfekt / Imperativ
featval-Aor = Aorist
featval-Ind = Indikativ
featval-Cnd = Konditional
featval-Fin = finit
featval-Inf = Infinitiv
featval-Part = Partizip
featval-Ger = Gerundium
featval-Conv = Konverb
featval-Act = Aktiv
featval-Pass = Passiv
featval-Pos = Positiv
featval-Cmp = Komparativ
featval-Sup = Superlativ
featval-Abs = absoluter Superlativ
featval-Neg = verneint
featval-Def = bestimmt
featval-Anim = belebt
featval-Inan = unbelebt
featval-Prs = Personalpronomen
featval-Dem = Demonstrativpronomen
featval-Int = Interrogativpronomen
featval-Rel = Relativpronomen
featval-Tot = Gesamtpronomen
featval-Card = Kardinalzahl
featval-Ord = Ordinalzahl
featval-Mult = Multiplikativzahl
featval-Yes = ja
featval-Short = Kurzform
featval-Art = Artikel
featval-Sub = Konjunktiv
featval-Indef = unbestimmt
featval-Definite-Ind = unbestimmt

## The problems that the checks find

problem-repeat = '{ $words }' wiederholt sich.
problem-spelling = Die Wortliste für { $languageName } hat dieses Wort nicht.
problem-spelling-suggestion = Die Wortliste für { $languageName } hat dieses Wort nicht. Meinten Sie '{ $better }'?
problem-hr-lexicon = Das Lexikon (hrLex) hat dieses Wort nicht. Es kann ein Rechtschreibfehler, ein seltenes Wort oder ein Name sein.
problem-hr-genitive-adjective = '{ $word }' verlangt ein Substantiv im Genitiv (puna vode), aber diese Form ist { $gotName }.
problem-preposition-case = Die Präposition '{ $word }' verlangt hier den { $wantName }, aber diese Form ist { $gotName }.
problem-preposition-cases = Die Präposition '{ $word }' verlangt { $want }, aber diese Form ist { $gotName }.
problem-case-in-list = den { $caseName }
problem-agreement = Stimmt nicht mit '{ $noun }' überein: diese Form ist { $mineName }, aber das Substantiv ist { $theirsName } ({ $feat ->
    [Case] Kasus
    [Gender] Genus
   *[Number] Numerus
}).
problem-hr-object = Das Subjekt steckt schon im Verb '{ $verb }', also ist dieses Substantiv nicht das Subjekt. Ein Objekt steht meist im Akkusativ, aber diese Form ist Nominativ.
problem-de-adjective-ending = Die Endung -{ $ending } passt nicht zu '{ $noun }' ({ $formName }, { $caseName }). { $kind ->
    [weak] Nach einem Wort wie der
    [mixed] Nach einem Wort wie ein
   *[strong] Ohne Artikel
} ist die Endung -{ $expected }.
problem-en-agreement = '{ $verb }' stimmt nicht mit { $subject ->
    [first] dem Subjekt 'I'
    [singular] einem Subjekt im Singular
   *[plural] einem Subjekt im Plural
} überein. { $fix ->
    [form] Die richtige Form ist '{ $correct }'.
    [add-s] Das Verb braucht die Endung -s.
   *[no-s] Das Verb hat hier keine Endung -s.
}

## Errors

error-server = Der Server hat { $status } zurückgegeben.
error-no-languages = Die Liste der Sprachen wurde nicht geladen.
error-not-admin = Nur ein Administrator kann die Karten eines anderen Benutzers sehen.
error-ai-no-key = der Server hat keinen Schlüssel für einen KI-Dienst
error-ai-limit = das Limit ist { $limit } Fragen pro Tag
error-ai-needs-review = die Frage { $question } braucht die Antwort auf eine Karteikarte
error-ai-timeout = der KI-Dienst hat nicht rechtzeitig geantwortet
error-ai-busy = der KI-Dienst hat zu viele Anfragen oder kein Guthaben
error-ai-http = der KI-Dienst hat HTTP { $status } zurückgegeben
error-ai-empty = der KI-Dienst hat eine leere Antwort gegeben
error-translator-timeout = { $service } hat nicht rechtzeitig geantwortet
error-translator-quota = das Kontingent von { $service } für diesen Monat ist verbraucht
error-translator-busy = { $service } hat zu viele Anfragen, versuchen Sie es noch einmal
error-translator-http = { $service } hat HTTP { $status } zurückgegeben
error-voice-no-service = der Server hat keinen Sprachdienst
error-voice-timeout = der Sprachdienst hat nicht rechtzeitig geantwortet
error-voice-http = der Sprachdienst hat HTTP { $status } zurückgegeben
error-voice-language = der Sprachdienst liest diese Sprache nicht vor

## The flashcard tab

cards-title = Karteikarten
cards-intro = Eine Karte zeigt einen Text. Geben Sie ihn in der anderen Sprache ein. Dann sehen Sie die Analyse Ihrer Antwort und der richtigen Antwort, und die Karte kommt später wieder: bald nach einer falschen Antwort, und nach längerer Zeit mit jeder richtigen.
cards-language-note = Die Karten bleiben in den Sprachen, in denen sie geschrieben wurden. Diese können von der Sprache der Seite abweichen.
cards-all-decks = Alle Stapel
cards-give-up = Ich weiß es nicht
cards-check = Prüfen
cards-speak = Vorlesen
cards-next = Nächste Karte
cards-no-decks = Keine Stapel. Der Administrator fügt sie auf dem Server hinzu (siehe README).
cards-counts = { $new } neu · { $learning } im Lernen · { $due } fällig
cards-group-summary = { $decks ->
    [one] { $decks } Stapel
   *[other] { $decks } Stapel
} · { $counts }
cards-deck-summary = { $language } · { $cards ->
    [one] { $cards } Karte
   *[other] { $cards } Karten
}
cards-done = Im Moment keine Karten mehr.
cards-done-next = Im Moment keine Karten mehr. Die nächste ist { $when } fällig.
cards-task-text = Geben Sie das in dieser Sprache ein: { $language }.
cards-task-media = Geben Sie in dieser Sprache ein, was Sie sehen oder hören: { $language }.
cards-your-answer = Ihre Antwort
cards-no-answer = Keine Antwort
cards-correct-answer = Die richtige Antwort
cards-accepted-answers = Alle akzeptierten Antworten:
cards-next-due = { $rating }: Diese Karte kommt { $when } wieder.
time-now = jetzt

rating-1 = Nochmal
rating-2 = Schwer
rating-3 = Gut
rating-4 = Einfach
rating-button-1 = 1 { rating-1 }
rating-button-2 = 2 { rating-2 }
rating-button-3 = 3 { rating-3 }
rating-button-4 = 4 { rating-4 }

speech-no-voice = Dieser Browser hat keine Stimme für diese Sprache: { $language }.
speech-no-voices = Dieser Browser hat keine Stimmen, also kann er keinen Text vorlesen.
speech-error = Der Browser kann das nicht vorlesen ({ $error }).

## The questions to the AI

explain-ask = Die KI fragen:
explain-context-placeholder = Optional: mehr zu Ihrer Frage, zum Beispiel „warum dieses Verb?“
explain-working = Die KI schreibt eine Antwort.
explain-timeout = Keine Antwort nach { $seconds } s. Versuchen Sie es noch einmal.
explain-written-by = { $model } hat das geschrieben. Es kann falsch sein.
explain-question-meaning = Was bedeutet das?
explain-question-grammar = Erkläre die Grammatik
explain-question-register = Ist das umgangssprachlich?
explain-question-why_wrong = Warum ist meine Antwort falsch?
explain-question-also_right = Ist meine Antwort auch richtig?
explain-question-difference = Was ist der Unterschied?

## The "Listen" buttons

listen-label = Anhören:
listen-working = Der Sprachdienst liest den Text vor.
listen-timeout = Kein Ton nach { $seconds } s. Versuchen Sie es noch einmal.
listen-made-by = { $model } hat das vorgelesen.

## The progress tab

progress-cards-of = Karten von
progress-own-cards = Meine Karten
progress-no-answers = Noch keine Antworten.
progress-answers = Antworten
progress-passed = Nicht „{ rating-1 }“
progress-lapses = Vergessen, nachdem eine Karte gelernt war
progress-streak = Tage in Folge
progress-cards = Karten
progress-cards-value = { $total } ({ $counts })
progress-days-note = Antworten pro Tag, letzte 90 Tage. Der dunkle Teil ist der Anteil, der nicht „{ rating-1 }“ war.
progress-rate-note = Der Anteil, der nicht „{ rating-1 }“ war, für jeden Tag. Ein Tag ohne Antwort hat keinen Balken.
progress-day-answers = { $date }: { $answers ->
    [one] { $answers } Antwort
   *[other] { $answers } Antworten
}, davon { $passed } nicht „{ rating-1 }“
progress-day-rate = { $date }: { $rate }
progress-day-none = { $date }: keine Antworten
