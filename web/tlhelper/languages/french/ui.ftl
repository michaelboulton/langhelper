# The text of the page in French. english/ui.ftl is the complete catalog and
# has the notes on each message and on its variables. A message that is not
# here shows in English.
#
# A machine wrote the first version of this file. A person who speaks French
# must read it, the grammar terms most of all.

## The names of the languages

language-name-en = anglais
language-name-hr = croate
language-name-de = allemand
language-name-fr = français
language-name-it = italien

language-hr-light-note = Le petit modèle du croate n'a pas de correcteur orthographique, et il ne trouve pas certaines fautes de cas (Pijem kava). Les grands modèles en trouvent plus.

language-en-tag-name = Étiquette Penn Treebank
language-hr-tag-name = Étiquette MULTEXT-East
language-de-tag-name = Étiquette STTS
language-it-tag-name = Étiquette ISDT

## The top of the page

tab-breakdown = Analyse
tab-cards = Cartes
tab-progress = Progrès
locale-label = Langue de la page

## The breakdown tab

breakdown-title = Analyse de phrases en { $language }
breakdown-intro = Écrivez une phrase en { $language }, ou une phrase en anglais pour l'avoir en { $language }. Chaque mot prend une couleur selon sa nature. Choisissez un mot pour voir les détails.
breakdown-language = Langue
breakdown-source-study = J'écris en { $language }
breakdown-source-english = J'écris en anglais, et j'obtiens la traduction en { $language }
option-heavy = Grands modèles (plus précis, et la première requête attend leur chargement)
option-nonstandard = Texte familier ou de messagerie (modèles pour l'argot et les signes diacritiques manquants)
option-translate = Traduire en anglais
option-time-limit = Délai
unit-seconds = s
breakdown-cancel = Annuler
breakdown-go = Analyser
breakdown-no-translation = Pas de traduction : { $error }.
breakdown-side-label = { $language } :

status-working = En cours.
status-working-heavy = En cours. La première requête avec les grands modèles attend leur chargement, jusqu'à une minute.
status-canceled = Annulé.
status-timeout = Pas de réponse après { $seconds } s. Si le serveur charge encore des modèles, réessayez dans un instant ou augmentez le délai.
status-models = Modèles : { $models }.
status-loading-models = Le serveur charge les modèles ({ $models }). Une requête attend qu'ils soient prêts.
model-name = { $language }, { $variant ->
    [light] petit
    [heavy] grand
    [nonstandard] non standard
   *[other] { $variant }
}

## The table of the selected word

detail-accent = Accent
detail-accent-clitic = un clitique : pas d'accent propre, il s'appuie sur le mot suivant ou précédent
detail-accent-dictionary = la forme du dictionnaire. L'accent peut se déplacer dans cette forme du mot
detail-accent-ambiguous = plusieurs lectures, la grammaire ne tranche pas
detail-reading = Lecture
detail-lemma = Forme de base (lemme)
detail-upos = Nature
detail-seen = Nombre de fois que ce lemme a été vu
detail-dictionaries = Dictionnaires

accents-legend = Signes d'accent : ȁ bref descendant, ȃ long descendant, à bref montant, á long montant, ā voyelle longue sans accent. Une forme entre (parenthèses) est la forme du dictionnaire, et l'accent peut différer dans la forme de la phrase. Source : Wiktionary, CC BY-SA.

## The parts of speech

upos-NOUN = nom
upos-PROPN = nom propre
upos-VERB = verbe
upos-AUX = auxiliaire
upos-ADJ = adjectif
upos-ADV = adverbe
upos-PRON = pronom
upos-DET = déterminant
upos-ADP = préposition
upos-CCONJ = conjonction de coordination
upos-SCONJ = conjonction de subordination
upos-PART = particule
upos-NUM = numéral
upos-INTJ = interjection
upos-PUNCT = ponctuation
upos-SYM = symbole
upos-X = autre

## The names of the features

feat-Case = Cas
feat-Gender = Genre
feat-Number = Nombre
feat-Person = Personne
feat-Tense = Temps
feat-Mood = Mode
feat-VerbForm = Forme verbale
feat-Voice = Voix
feat-Degree = Degré
feat-Definite = Définitude
feat-Animacy = Animéité
feat-PronType = Type de pronom
feat-Poss = Possessif
feat-Reflex = Réfléchi
feat-Polarity = Polarité
feat-NumType = Type de numéral
feat-Number-psor = Nombre du possesseur
feat-Gender-psor = Genre du possesseur
feat-Variant = Variante
feat-Foreign = Mot étranger
feat-Abbr = Abréviation
feat-Clitic = Clitique

## The values of the features

featval-Nom = nominatif
featval-Gen = génitif
featval-Dat = datif
featval-Acc = accusatif
featval-Voc = vocatif
featval-Loc = locatif
featval-Ins = instrumental
featval-Masc = masculin
featval-Fem = féminin
featval-Neut = neutre
featval-Sing = singulier
featval-Plur = pluriel
featval-Pres = présent
featval-Past = passé
featval-Fut = futur
featval-Imp = imparfait / impératif
featval-Aor = aoriste
featval-Ind = indicatif
featval-Cnd = conditionnel
featval-Fin = fini
featval-Inf = infinitif
featval-Part = participe
featval-Ger = gérondif
featval-Conv = converbe
featval-Act = actif
featval-Pass = passif
featval-Pos = positif
featval-Cmp = comparatif
featval-Sup = superlatif
featval-Abs = superlatif absolu
featval-Neg = négatif
featval-Def = défini
featval-Anim = animé
featval-Inan = inanimé
featval-Prs = personnel
featval-Dem = démonstratif
featval-Int = interrogatif
featval-Rel = relatif
featval-Tot = total
featval-Card = cardinal
featval-Ord = ordinal
featval-Mult = multiplicatif
featval-Yes = oui
featval-Short = forme courte
featval-Art = article
featval-Sub = subjonctif
featval-Indef = indéfini
featval-Definite-Ind = indéfini

## The problems that the checks find

problem-repeat = « { $words } » se répète.
problem-spelling = La liste de mots en { $languageName } n'a pas ce mot.
problem-spelling-suggestion = La liste de mots en { $languageName } n'a pas ce mot. Vouliez-vous dire « { $better } » ?
problem-hr-lexicon = Le lexique (hrLex) n'a pas ce mot. Ce peut être une faute d'orthographe, un mot rare ou un nom.
problem-hr-genitive-adjective = « { $word } » demande un nom au génitif (puna vode), mais cette forme est au { $gotName }.
problem-preposition-case = La préposition « { $word } » demande ici le { $wantName }, mais cette forme est au { $gotName }.
problem-preposition-cases = La préposition « { $word } » demande { $want }, mais cette forme est au { $gotName }.
problem-case-in-list = le { $caseName }
problem-agreement = Ne s'accorde pas avec « { $noun } » : cette forme est au { $mineName }, mais le nom est au { $theirsName } ({ $feat ->
    [Case] cas
    [Gender] genre
   *[Number] nombre
}).
problem-hr-object = Le sujet est déjà dans le verbe « { $verb } », donc ce nom n'est pas le sujet. Un complément d'objet est en général à l'accusatif, mais cette forme est au nominatif.
problem-de-adjective-ending = La terminaison -{ $ending } ne convient pas à « { $noun } » ({ $formName }, { $caseName }). { $kind ->
    [weak] Après un mot comme der
    [mixed] Après un mot comme ein
   *[strong] Sans article
}, la terminaison est -{ $expected }.
problem-en-agreement = « { $verb } » ne s'accorde pas avec { $subject ->
    [first] le sujet « I »
    [singular] un sujet au singulier
   *[plural] un sujet au pluriel
}. { $fix ->
    [form] La forme correcte est « { $correct } ».
    [add-s] Le verbe a besoin de la terminaison -s.
   *[no-s] Le verbe n'a pas de terminaison -s ici.
}

## Errors

error-server = Le serveur a répondu { $status }.
error-no-languages = La liste des langues ne s'est pas chargée.
error-not-admin = Seul un administrateur peut voir les cartes d'un autre utilisateur.
error-ai-no-key = le serveur n'a pas de clé pour un service d'IA
error-ai-limit = la limite est de { $limit } questions par jour
error-ai-needs-review = la question { $question } demande la réponse à une carte
error-ai-timeout = le service d'IA n'a pas répondu à temps
error-ai-busy = le service d'IA a trop de requêtes, ou plus de crédit
error-ai-http = le service d'IA a répondu HTTP { $status }
error-ai-empty = le service d'IA a donné une réponse vide
error-translator-timeout = { $service } n'a pas répondu à temps
error-translator-quota = le quota de { $service } pour ce mois est épuisé
error-translator-busy = { $service } a trop de requêtes, réessayez
error-translator-http = { $service } a répondu HTTP { $status }
error-voice-no-service = le serveur n'a pas de service vocal
error-voice-timeout = le service vocal n'a pas répondu à temps
error-voice-http = le service vocal a répondu HTTP { $status }
error-voice-language = le service vocal ne lit pas cette langue

## The flashcard tab

cards-title = Cartes
cards-intro = Une carte montre un texte. Écrivez-le dans l'autre langue. Vous voyez ensuite l'analyse de votre réponse et de la bonne réponse, et la carte revient plus tard : peu après une mauvaise réponse, et après un temps plus long à chaque bonne réponse.
cards-language-note = Les cartes restent dans les langues où elles ont été écrites. Celles-ci peuvent différer de la langue de la page.
cards-all-decks = Tous les paquets
cards-give-up = Je ne sais pas
cards-check = Vérifier
cards-speak = Lire à voix haute
cards-next = Carte suivante
cards-no-decks = Aucun paquet. L'administrateur les ajoute sur le serveur (voir le README).
cards-counts = { $new } nouvelles · { $learning } en cours · { $due } à revoir
cards-group-summary = { $decks ->
    [one] { $decks } paquet
   *[other] { $decks } paquets
} · { $counts }
cards-deck-summary = { $language } · { $cards ->
    [one] { $cards } carte
   *[other] { $cards } cartes
}
cards-done = Plus de cartes pour le moment.
cards-done-next = Plus de cartes pour le moment. La prochaine revient { $when }.
cards-task-text = Écrivez ceci en { $language }.
cards-task-media = Écrivez en { $language } ce que vous voyez ou entendez.
cards-your-answer = Votre réponse
cards-no-answer = Pas de réponse
cards-correct-answer = La bonne réponse
cards-accepted-answers = Toutes les réponses acceptées :
cards-next-due = { $rating } : cette carte revient { $when }.
time-now = maintenant

rating-1 = À revoir
rating-2 = Difficile
rating-3 = Correct
rating-4 = Facile
rating-button-1 = 1 { rating-1 }
rating-button-2 = 2 { rating-2 }
rating-button-3 = 3 { rating-3 }
rating-button-4 = 4 { rating-4 }

speech-no-voice = Ce navigateur n'a pas de voix en { $language }.
speech-no-voices = Ce navigateur n'a pas de voix, donc il ne peut pas lire un texte à voix haute.
speech-error = Le navigateur ne peut pas lire ceci à voix haute ({ $error }).

## The questions to the AI

explain-ask = Demander à l'IA :
explain-context-placeholder = Facultatif : plus sur votre question, par exemple « pourquoi ce verbe ? »
explain-working = L'IA écrit une réponse.
explain-timeout = Pas de réponse après { $seconds } s. Réessayez.
explain-written-by = { $model } a écrit ceci. Cela peut être faux.
explain-question-meaning = Qu'est-ce que cela veut dire ?
explain-question-grammar = Explique la grammaire
explain-question-register = Est-ce familier ?
explain-question-why_wrong = Pourquoi ma réponse est-elle fausse ?
explain-question-also_right = Ma réponse est-elle aussi correcte ?
explain-question-difference = Quelle est la différence ?

## The "Listen" buttons

listen-label = Écouter :
listen-working = Le service vocal lit le texte.
listen-timeout = Pas de son après { $seconds } s. Réessayez.
listen-made-by = { $model } a lu ceci.

## The progress tab

progress-cards-of = Cartes de
progress-own-cards = Mes cartes
progress-no-answers = Pas encore de réponses.
progress-answers = Réponses
progress-passed = Pas « { rating-1 } »
progress-lapses = Oubliées après avoir été sues
progress-streak = Jours d'affilée
progress-cards = Cartes
progress-cards-value = { $total } ({ $counts })
progress-days-note = Réponses par jour, 90 derniers jours. La partie foncée est la part qui n'était pas « { rating-1 } ».
progress-rate-note = La part qui n'était pas « { rating-1 } », chaque jour. Un jour sans réponse n'a pas de barre.
progress-day-answers = { $date } : { $answers ->
    [one] { $answers } réponse
   *[other] { $answers } réponses
}, dont { $passed } pas « { rating-1 } »
progress-day-rate = { $date } : { $rate }
progress-day-none = { $date } : aucune réponse
