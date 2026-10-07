# The text of the page in English. This is the complete catalog: a message
# that another ui.ftl does not have comes from this file.
#
# The format is Fluent (https://projectfluent.org/fluent/guide/). The page
# gets this file from /api/v1/locales/en/ui.ftl (static/js/i18n.js).
# Rules for this file: no attributes and no functions, because the page has a
# small formatter of its own for when the Fluent script does not load.
#
# A variable that ends in "Name" is the word for a raw value, from this
# catalog: $gotName is "accusative" when $got is "Acc". A translation can use
# the word, or select on the raw value for a word in another form.

## The names of the languages

language-name-en = English
language-name-hr = Croatian
language-name-de = German
language-name-fr = French
language-name-it = Italian

# What the light model of a language cannot do.
language-hr-light-note = The small Croatian model has no spelling check, and it misses some errors of case (Pijem kava). The large models find more.

# The name of the tag set of each language, in the table of a word.
language-en-tag-name = Penn Treebank tag
language-hr-tag-name = MULTEXT-East tag
language-de-tag-name = STTS tag
language-it-tag-name = ISDT tag

## The top of the page

tab-breakdown = Breakdown
tab-cards = Flashcards
tab-progress = Progress
locale-label = Language of the page

## The breakdown tab
## $language: the name of the study language.

breakdown-title = { $language } sentence breakdown
breakdown-intro = Enter a { $language } sentence, or an English sentence to get it in { $language }. Each word gets a color for its part of speech. Select a word for the details.
breakdown-language = Language
breakdown-source-study = I enter { $language }
breakdown-source-english = I enter English, and get the { $language } translation
option-heavy = Large models (more exact, and the first request waits for their load)
option-nonstandard = Casual or chat-style text (models for slang and missing diacritics)
option-translate = Translate to English
option-time-limit = Time limit
# The unit after the number of the time limit: seconds.
unit-seconds = s
breakdown-cancel = Cancel
breakdown-go = Break down
# $error: why, as a part of a sentence.
breakdown-no-translation = No translation: { $error }.
# Before the text of one side: "English: My hovercraft is full of eels."
breakdown-side-label = { $language }:

status-working = Working.
status-working-heavy = Working. The first request with the large models waits for their load, up to a minute.
status-canceled = Canceled.
status-timeout = No answer after { $seconds } s. If the server is still loading models, try again in a moment or raise the time limit.
# $models: a value of model-name.
status-models = Models: { $models }.
status-loading-models = The server is loading the { $models } models. A request waits until they are ready.
# The models of one language. $variant: light, heavy or nonstandard.
model-name = { $language } { $variant ->
    [light] light
    [heavy] heavy
    [nonstandard] nonstandard
   *[other] { $variant }
}

## The table of the selected word

detail-accent = Accent
detail-accent-clitic = a clitic: no accent of its own, it leans on the next or the last word
detail-accent-dictionary = the dictionary form. The accent can move in this form of the word
detail-accent-ambiguous = several readings, the grammar does not decide
detail-reading = Reading
detail-lemma = Base form (lemma)
detail-upos = Part of speech
detail-seen = Times this lemma was seen
detail-dictionaries = Dictionaries

# The page makes each accent letter bold. Keep a space on each side of it.
accents-legend = Accent marks: ȁ short falling, ȃ long falling, à short rising, á long rising, ā long vowel with no stress. A form in (parentheses) is the dictionary form, and the accent can differ in the form in the sentence. Source: Wiktionary, CC BY-SA.

## The parts of speech (Universal POS tags)

upos-NOUN = noun
upos-PROPN = proper noun
upos-VERB = verb
upos-AUX = auxiliary verb
upos-ADJ = adjective
upos-ADV = adverb
upos-PRON = pronoun
upos-DET = determiner
upos-ADP = preposition
upos-CCONJ = coordinating conjunction
upos-SCONJ = subordinating conjunction
upos-PART = particle
upos-NUM = numeral
upos-INTJ = interjection
upos-PUNCT = punctuation
upos-SYM = symbol
upos-X = other

## The names of the features (Universal features)

feat-Case = Case
feat-Gender = Gender
feat-Number = Number
feat-Person = Person
feat-Tense = Tense
feat-Mood = Mood
feat-VerbForm = Verb form
feat-Voice = Voice
feat-Degree = Degree
feat-Definite = Definiteness
feat-Animacy = Animacy
feat-PronType = Pronoun type
feat-Poss = Possessive
feat-Reflex = Reflexive
feat-Polarity = Polarity
feat-NumType = Numeral type
feat-Number-psor = Number of possessor
feat-Gender-psor = Gender of possessor
feat-Variant = Variant
feat-Foreign = Foreign
feat-Abbr = Abbreviation
feat-Clitic = Clitic

## The values of the features. The words are also parts of the sentences of
## the problems, so they start with a small letter.

featval-Nom = nominative
featval-Gen = genitive
featval-Dat = dative
featval-Acc = accusative
featval-Voc = vocative
featval-Loc = locative
featval-Ins = instrumental
featval-Masc = masculine
featval-Fem = feminine
featval-Neut = neuter
featval-Sing = singular
featval-Plur = plural
featval-Pres = present
featval-Past = past
featval-Fut = future
featval-Imp = imperfect / imperative
featval-Aor = aorist
featval-Ind = indicative
featval-Cnd = conditional
featval-Fin = finite
featval-Inf = infinitive
featval-Part = participle
featval-Ger = gerund
featval-Conv = converb
featval-Act = active
featval-Pass = passive
featval-Pos = positive
featval-Cmp = comparative
featval-Sup = superlative
featval-Abs = absolute superlative
featval-Neg = negative
featval-Def = definite
featval-Anim = animate
featval-Inan = inanimate
featval-Prs = personal
featval-Dem = demonstrative
featval-Int = interrogative
featval-Rel = relative
featval-Tot = total
featval-Card = cardinal
featval-Ord = ordinal
featval-Mult = multiplicative
featval-Yes = yes
featval-Short = short form
featval-Art = article
featval-Sub = subjunctive
featval-Indef = indefinite
# "Ind" is the indicative of a verb, but for the German "ein" it is
# indefinite. A message with the name of the feature wins.
featval-Definite-Ind = indefinite

## The problems that the checks find (tlhelper/languages/*). Python names the
## message and gives the parameters.

# $words: the word or the phrase that is there two times.
problem-repeat = '{ $words }' repeats.
# $languageName: the name of the language of the word list.
problem-spelling = The { $languageName } word list does not have this word.
problem-spelling-suggestion = The { $languageName } word list does not have this word. Did you mean '{ $better }'?
problem-hr-lexicon = The lexicon (hrLex) does not have this word. It can be a spelling error, a rare word, or a name.
# $word: the adjective. $got: the case of the noun.
problem-hr-genitive-adjective = '{ $word }' takes a genitive noun (puna vode), but this form is { $gotName }.
# $word: the preposition. $want and $got: cases.
problem-preposition-case = The preposition '{ $word }' takes the { $wantName } here, but this form is { $gotName }.
# $want: the cases that the preposition can take, as a list of
# problem-case-in-list with "or" between them.
problem-preposition-cases = The preposition '{ $word }' takes { $want }, but this form is { $gotName }.
problem-case-in-list = the { $caseName }
# $mine and $theirs: values of the feature $feat (Case, Gender or Number).
problem-agreement = Does not agree with '{ $noun }': this form is { $mineName }, but the noun is { $theirsName } ({ $feat ->
    [Case] case
    [Gender] gender
   *[Number] number
}).
# $verb: the verb that holds the subject.
problem-hr-object = The subject is already in the verb '{ $verb }', so this noun is not the subject. An object is usually accusative, but this form is nominative.
# $form: the gender of the noun, or Plur. $kind: weak, mixed or strong.
problem-de-adjective-ending = The ending -{ $ending } does not fit '{ $noun }' ({ $formName } { $caseName }). { $kind ->
    [weak] After a word like der
    [mixed] After a word like ein
   *[strong] With no article
}, the ending is -{ $expected }.
# $subject: first, singular or plural. $fix: form, add-s or no-s.
problem-en-agreement = '{ $verb }' does not agree with { $subject ->
    [first] 'I'
    [singular] a singular subject
   *[plural] a plural subject
}. { $fix ->
    [form] The correct form is '{ $correct }'.
    [add-s] The verb needs the ending -s.
   *[no-s] The verb has no ending -s here.
}

## Errors. The text of an error of the server comes after error-server.

error-server = The server returned { $status }.
error-no-languages = The list of languages did not load.
error-not-admin = Only an admin can see the cards of another user.
error-ai-no-key = the server has no key for an AI service
error-ai-limit = the limit is { $limit } questions in a day
error-ai-needs-review = { $question } needs the review of a flashcard
error-ai-timeout = the AI service did not answer in time
error-ai-busy = the AI service has too many requests, or no credit
error-ai-http = the AI service returned HTTP { $status }
error-ai-empty = the AI service gave an empty answer
# $service: the name of the machine translator, for example DeepL.
error-translator-timeout = { $service } did not answer in time
error-translator-quota = the { $service } quota for this month is used up
error-translator-busy = { $service } has too many requests, try again
error-translator-http = { $service } returned HTTP { $status }
error-voice-no-service = the server has no voice service
error-voice-timeout = the voice service did not answer in time
error-voice-http = the voice service returned HTTP { $status }
error-voice-language = the voice service does not read this language

## The flashcard tab

cards-title = Flashcards
cards-intro = A card shows a text. Enter it in the other language. You then see the breakdown of your answer and of the correct answer, and the card comes back later: soon after a wrong answer, and after a longer time with each right one.
# The yellow note over the decks.
cards-language-note = The cards stay in the languages that they were written in. They can differ from the language of the page.
cards-all-decks = All decks
cards-give-up = I do not know
cards-check = Check
cards-speak = Read it aloud
cards-next = Next card
cards-no-decks = No decks. The admin adds them on the server (see the README).
# The cards of a deck: how many are new, in learning, and due.
cards-counts = { $new } new · { $learning } in learning · { $due } due
# $counts: a value of cards-counts.
cards-group-summary = { $decks ->
    [one] { $decks } deck
   *[other] { $decks } decks
} · { $counts }
cards-deck-summary = { $language } · { $cards ->
    [one] { $cards } card
   *[other] { $cards } cards
}
cards-done = No more cards for now.
# $when: a relative time from the browser, for example "in 5 minutes".
cards-done-next = No more cards for now. The next one is due { $when }.
# $language: the name of the language of the answer.
cards-task-text = Enter this in { $language }.
cards-task-media = Enter what you see or hear in { $language }.
cards-your-answer = Your answer
cards-no-answer = No answer
cards-correct-answer = The correct answer
# The answers come after this text.
cards-accepted-answers = All accepted answers:
# $rating: a value of rating-1 to rating-4.
cards-next-due = { $rating }: this card comes back { $when }.
time-now = now

# The ratings, as in Anki. The number on a button is its key.
rating-1 = Again
rating-2 = Hard
rating-3 = Good
rating-4 = Easy
rating-button-1 = 1 { rating-1 }
rating-button-2 = 2 { rating-2 }
rating-button-3 = 3 { rating-3 }
rating-button-4 = 4 { rating-4 }

speech-no-voice = This browser has no { $language } voice.
speech-no-voices = This browser has no voices, so it cannot read a text aloud.
speech-error = The browser cannot read this aloud ({ $error }).

## The questions to the AI

explain-ask = Ask the AI:
explain-context-placeholder = Optional: more about your question, for example "why this verb?"
explain-working = The AI writes an answer.
explain-timeout = No answer after { $seconds } s. Try again.
# $model: the name of the AI model.
explain-written-by = { $model } wrote this. It can be wrong.
explain-question-meaning = What does this mean?
explain-question-grammar = Explain the grammar
explain-question-register = Is this colloquial?
explain-question-why_wrong = Why is my answer wrong?
explain-question-also_right = Is my answer also correct?
explain-question-difference = What is the difference?

## The "Listen" buttons: the voice service reads a text aloud

listen-label = Listen:
listen-working = The voice service reads the text.
listen-timeout = No sound after { $seconds } s. Try again.
# $model: the name of the voice model.
listen-made-by = { $model } read this.

## The progress tab

progress-cards-of = Cards of
progress-own-cards = My cards
progress-no-answers = No answers yet.
progress-answers = Answers
progress-passed = Not "{ rating-1 }"
progress-lapses = Forgotten after a card was known
progress-streak = Days in a row
progress-cards = Cards
# $counts: a value of cards-counts.
progress-cards-value = { $total } ({ $counts })
progress-days-note = Answers a day, last 90 days. The dark part is the share that was not "{ rating-1 }".
progress-rate-note = The share that was not "{ rating-1 }", each day. A day with no answer has no bar.
# The text of one bar. $date: ISO 8601.
progress-day-answers = { $date }: { $answers ->
    [one] { $answers } answer
   *[other] { $answers } answers
}, { $passed } not "{ rating-1 }"
# $rate: a percentage from the browser, for example "80%".
progress-day-rate = { $date }: { $rate }
progress-day-none = { $date }: no answers
