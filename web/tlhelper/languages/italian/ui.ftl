# The text of the page in Italian. english/ui.ftl is the complete catalog and
# has the notes on each message and on its variables. A message that is not
# here shows in English.
#
# A machine wrote the first version of this file. A person who speaks Italian
# must read it, the grammar terms most of all.

## The names of the languages

language-name-en = inglese
language-name-hr = croato
language-name-de = tedesco
language-name-fr = francese
language-name-it = italiano

language-hr-light-note = Il modello piccolo del croato non ha un correttore ortografico e non trova alcuni errori di caso (Pijem kava). I modelli grandi ne trovano di più.

language-en-tag-name = Etichetta Penn Treebank
language-hr-tag-name = Etichetta MULTEXT-East
language-de-tag-name = Etichetta STTS
language-it-tag-name = Etichetta ISDT

## The top of the page

tab-breakdown = Analisi
tab-cards = Carte
tab-progress = Progressi
locale-label = Lingua della pagina

## The breakdown tab

breakdown-title = Analisi di frasi in { $language }
breakdown-intro = Scrivi una frase in { $language }, oppure una frase in inglese per averla in { $language }. Ogni parola prende un colore secondo la sua parte del discorso. Scegli una parola per vedere i dettagli.
breakdown-language = Lingua
breakdown-source-study = Scrivo in { $language }
breakdown-source-english = Scrivo in inglese e ottengo la traduzione in { $language }
option-heavy = Modelli grandi (più precisi, e la prima richiesta aspetta il loro caricamento)
option-nonstandard = Testo colloquiale o di chat (modelli per il gergo e i segni diacritici mancanti)
option-translate = Traduci in inglese
option-time-limit = Tempo massimo
unit-seconds = s
breakdown-cancel = Annulla
breakdown-go = Analizza
breakdown-no-translation = Nessuna traduzione: { $error }.
breakdown-side-label = { $language }:

status-working = In corso.
status-working-heavy = In corso. La prima richiesta con i modelli grandi aspetta il loro caricamento, fino a un minuto.
status-canceled = Annullato.
status-timeout = Nessuna risposta dopo { $seconds } s. Se il server sta ancora caricando i modelli, riprova tra un momento o aumenta il tempo massimo.
status-models = Modelli: { $models }.
status-loading-models = Il server sta caricando i modelli ({ $models }). Una richiesta aspetta che siano pronti.
model-name = { $language }, { $variant ->
    [light] piccolo
    [heavy] grande
    [nonstandard] non standard
   *[other] { $variant }
}

## The table of the selected word

detail-accent = Accento
detail-accent-clitic = un clitico: nessun accento proprio, si appoggia alla parola che segue o che precede
detail-accent-dictionary = la forma del dizionario. L'accento può spostarsi in questa forma della parola
detail-accent-ambiguous = più letture, la grammatica non decide
detail-reading = Lettura
detail-upos = Parte del discorso
detail-lemma = Forma base (lemma)
detail-seen = Quante volte questo lemma è stato visto
detail-dictionaries = Dizionari

accents-legend = Segni di accento: ȁ breve discendente, ȃ lungo discendente, à breve ascendente, á lungo ascendente, ā vocale lunga senza accento. Una forma tra (parentesi) è la forma del dizionario, e l'accento può differire nella forma della frase. Fonte: Wiktionary, CC BY-SA.

## The parts of speech

upos-NOUN = nome
upos-PROPN = nome proprio
upos-VERB = verbo
upos-AUX = ausiliare
upos-ADJ = aggettivo
upos-ADV = avverbio
upos-PRON = pronome
upos-DET = determinante
upos-ADP = preposizione
upos-CCONJ = congiunzione coordinante
upos-SCONJ = congiunzione subordinante
upos-PART = particella
upos-NUM = numerale
upos-INTJ = interiezione
upos-PUNCT = punteggiatura
upos-SYM = simbolo
upos-X = altro

## The names of the features

feat-Case = Caso
feat-Gender = Genere
feat-Number = Numero
feat-Person = Persona
feat-Tense = Tempo
feat-Mood = Modo
feat-VerbForm = Forma verbale
feat-Voice = Diatesi
feat-Degree = Grado
feat-Definite = Determinatezza
feat-Animacy = Animatezza
feat-PronType = Tipo di pronome
feat-Poss = Possessivo
feat-Reflex = Riflessivo
feat-Polarity = Polarità
feat-NumType = Tipo di numerale
feat-Number-psor = Numero del possessore
feat-Gender-psor = Genere del possessore
feat-Variant = Variante
feat-Foreign = Parola straniera
feat-Abbr = Abbreviazione
feat-Clitic = Clitico

## The values of the features

featval-Nom = nominativo
featval-Gen = genitivo
featval-Dat = dativo
featval-Acc = accusativo
featval-Voc = vocativo
featval-Loc = locativo
featval-Ins = strumentale
featval-Masc = maschile
featval-Fem = femminile
featval-Neut = neutro
featval-Sing = singolare
featval-Plur = plurale
featval-Pres = presente
featval-Past = passato
featval-Fut = futuro
featval-Imp = imperfetto / imperativo
featval-Aor = aoristo
featval-Ind = indicativo
featval-Cnd = condizionale
featval-Fin = finito
featval-Inf = infinito
featval-Part = participio
featval-Ger = gerundio
featval-Conv = converbo
featval-Act = attivo
featval-Pass = passivo
featval-Pos = positivo
featval-Cmp = comparativo
featval-Sup = superlativo
featval-Abs = superlativo assoluto
featval-Neg = negativo
featval-Def = determinativo
featval-Anim = animato
featval-Inan = inanimato
featval-Prs = personale
featval-Dem = dimostrativo
featval-Int = interrogativo
featval-Rel = relativo
featval-Tot = totale
featval-Card = cardinale
featval-Ord = ordinale
featval-Mult = moltiplicativo
featval-Yes = sì
featval-Short = forma breve
featval-Art = articolo
featval-Sub = congiuntivo
featval-Indef = indeterminativo
featval-Definite-Ind = indeterminativo

## The problems that the checks find

problem-repeat = « { $words } » si ripete.
problem-spelling = L'elenco di parole in { $languageName } non ha questa parola.
problem-spelling-suggestion = L'elenco di parole in { $languageName } non ha questa parola. Volevi dire « { $better } »?
problem-hr-lexicon = Il lessico (hrLex) non ha questa parola. Può essere un errore di ortografia, una parola rara o un nome.
problem-hr-genitive-adjective = « { $word } » richiede un nome al genitivo (puna vode), ma questa forma è al { $gotName }.
problem-preposition-case = La preposizione « { $word } » richiede qui il { $wantName }, ma questa forma è al { $gotName }.
problem-preposition-cases = La preposizione « { $word } » richiede { $want }, ma questa forma è al { $gotName }.
problem-case-in-list = il { $caseName }
problem-agreement = Non concorda con « { $noun } »: questa forma è { $mineName }, ma il nome è { $theirsName } ({ $feat ->
    [Case] caso
    [Gender] genere
   *[Number] numero
}).
problem-hr-object = Il soggetto è già nel verbo « { $verb } », quindi questo nome non è il soggetto. Un complemento oggetto è di solito all'accusativo, ma questa forma è al nominativo.
problem-de-adjective-ending = La desinenza -{ $ending } non va con « { $noun } » ({ $formName }, { $caseName }). { $kind ->
    [weak] Dopo una parola come der
    [mixed] Dopo una parola come ein
   *[strong] Senza articolo
}, la desinenza è -{ $expected }.
problem-en-agreement = « { $verb } » non concorda con { $subject ->
    [first] il soggetto « I »
    [singular] un soggetto singolare
   *[plural] un soggetto plurale
}. { $fix ->
    [form] La forma corretta è « { $correct } ».
    [add-s] Il verbo ha bisogno della desinenza -s.
   *[no-s] Il verbo qui non ha la desinenza -s.
}

## Errors

error-server = Il server ha risposto { $status }.
error-no-languages = L'elenco delle lingue non si è caricato.
error-not-admin = Solo un amministratore può vedere le carte di un altro utente.
error-ai-no-key = il server non ha una chiave per un servizio di IA
error-ai-limit = il limite è di { $limit } domande al giorno
error-ai-needs-review = la domanda { $question } richiede la risposta a una carta
error-ai-timeout = il servizio di IA non ha risposto in tempo
error-ai-busy = il servizio di IA ha troppe richieste, o non ha più credito
error-ai-http = il servizio di IA ha risposto HTTP { $status }
error-ai-empty = il servizio di IA ha dato una risposta vuota
error-translator-timeout = { $service } non ha risposto in tempo
error-translator-quota = la quota di { $service } per questo mese è esaurita
error-translator-busy = { $service } ha troppe richieste, riprova
error-translator-http = { $service } ha risposto HTTP { $status }
error-voice-no-service = il server non ha un servizio vocale
error-voice-timeout = il servizio vocale non ha risposto in tempo
error-voice-http = il servizio vocale ha risposto HTTP { $status }
error-voice-language = il servizio vocale non legge questa lingua

## The flashcard tab

cards-title = Carte
cards-intro = Una carta mostra un testo. Scrivilo nell'altra lingua. Poi vedi l'analisi della tua risposta e della risposta giusta, e la carta torna più tardi: poco dopo una risposta sbagliata, e dopo un tempo più lungo a ogni risposta giusta.
cards-language-note = Le carte restano nelle lingue in cui sono state scritte. Queste possono differire dalla lingua della pagina.
cards-all-decks = Tutti i mazzi
cards-give-up = Non lo so
cards-check = Verifica
cards-speak = Leggi ad alta voce
cards-next = Carta successiva
cards-no-decks = Nessun mazzo. L'amministratore li aggiunge sul server (vedi il README).
cards-counts = { $new } nuove · { $learning } in corso · { $due } da ripassare
cards-group-summary = { $decks ->
    [one] { $decks } mazzo
   *[other] { $decks } mazzi
} · { $counts }
cards-deck-summary = { $language } · { $cards ->
    [one] { $cards } carta
   *[other] { $cards } carte
}
cards-done = Nessun'altra carta per ora.
cards-done-next = Nessun'altra carta per ora. La prossima torna { $when }.
cards-task-text = Scrivi questo in { $language }.
cards-task-media = Scrivi in { $language } quello che vedi o senti.
cards-your-answer = La tua risposta
cards-no-answer = Nessuna risposta
cards-correct-answer = La risposta giusta
cards-accepted-answers = Tutte le risposte accettate:
cards-next-due = { $rating }: questa carta torna { $when }.
time-now = adesso

rating-1 = Da rivedere
rating-2 = Difficile
rating-3 = Giusto
rating-4 = Facile
rating-button-1 = 1 { rating-1 }
rating-button-2 = 2 { rating-2 }
rating-button-3 = 3 { rating-3 }
rating-button-4 = 4 { rating-4 }

speech-no-voice = Questo browser non ha una voce in { $language }.
speech-no-voices = Questo browser non ha voci, quindi non può leggere un testo ad alta voce.
speech-error = Il browser non può leggere questo ad alta voce ({ $error }).

## The questions to the AI

explain-ask = Chiedi all'IA:
explain-context-placeholder = Facoltativo: altro sulla tua domanda, per esempio « perché questo verbo? »
explain-working = L'IA sta scrivendo una risposta.
explain-timeout = Nessuna risposta dopo { $seconds } s. Riprova.
explain-written-by = { $model } ha scritto questo. Può essere sbagliato.
explain-question-meaning = Che cosa vuol dire?
explain-question-grammar = Spiega la grammatica
explain-question-register = È colloquiale?
explain-question-why_wrong = Perché la mia risposta è sbagliata?
explain-question-also_right = Anche la mia risposta è giusta?
explain-question-difference = Qual è la differenza?

## The "Listen" buttons

listen-label = Ascolta:
listen-working = Il servizio vocale legge il testo.
listen-timeout = Nessun audio dopo { $seconds } s. Riprova.
listen-made-by = { $model } ha letto questo.

## The progress tab

progress-cards-of = Carte di
progress-own-cards = Le mie carte
progress-no-answers = Ancora nessuna risposta.
progress-answers = Risposte
progress-passed = Non « { rating-1 } »
progress-lapses = Dimenticate dopo essere state sapute
progress-streak = Giorni di seguito
progress-cards = Carte
progress-cards-value = { $total } ({ $counts })
progress-days-note = Risposte al giorno, ultimi 90 giorni. La parte scura è la quota che non era « { rating-1 } ».
progress-rate-note = La quota che non era « { rating-1 } », ogni giorno. Un giorno senza risposte non ha una barra.
progress-day-answers = { $date }: { $answers ->
    [one] { $answers } risposta
   *[other] { $answers } risposte
}, di cui { $passed } non « { rating-1 } »
progress-day-rate = { $date }: { $rate }
progress-day-none = { $date }: nessuna risposta
