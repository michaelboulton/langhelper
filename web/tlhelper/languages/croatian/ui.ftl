# The text of the page in Croatian. english/ui.ftl is the complete catalog and
# has the notes on each message and on its variables. A message that is not
# here shows in English.
#
# A machine wrote the first version of this file. A person who speaks
# Croatian must read it, the grammar terms most of all.

## The names of the languages

language-name-en = engleski
language-name-hr = hrvatski
language-name-de = njemački
language-name-fr = francuski
language-name-it = talijanski

language-hr-light-note = Mali model za hrvatski nema provjeru pravopisa i ne nalazi neke pogreške u padežu (Pijem kava). Veliki modeli nalaze više.

language-en-tag-name = Oznaka Penn Treebank
language-hr-tag-name = Oznaka MULTEXT-East
language-de-tag-name = Oznaka STTS
language-it-tag-name = Oznaka ISDT

## The top of the page

tab-breakdown = Raščlamba
tab-cards = Kartice
tab-progress = Napredak
locale-label = Jezik stranice

## The breakdown tab

breakdown-title = Raščlamba rečenice: { $language }
breakdown-intro = Unesite rečenicu na jeziku { $language }, ili rečenicu na engleskom da dobijete prijevod na jezik { $language }. Svaka riječ dobiva boju svoje vrste riječi. Odaberite riječ za pojedinosti.
breakdown-language = Jezik
breakdown-source-study = Unosim jezik: { $language }
breakdown-source-english = Unosim engleski i dobivam prijevod na jezik: { $language }
option-heavy = Veliki modeli (točniji su, a prvi zahtjev čeka da se učitaju)
option-nonstandard = Neformalan tekst ili tekst iz poruka (modeli za žargon i tekst bez dijakritičkih znakova)
option-translate = Prevedi na engleski
option-time-limit = Vremensko ograničenje
unit-seconds = s
breakdown-cancel = Odustani
breakdown-go = Raščlani
breakdown-no-translation = Nema prijevoda: { $error }.
breakdown-side-label = { $language }:

status-working = Radim.
status-working-heavy = Radim. Prvi zahtjev s velikim modelima čeka da se učitaju, do jedne minute.
status-canceled = Prekinuto.
status-timeout = Nema odgovora nakon { $seconds } s. Ako poslužitelj još učitava modele, pokušajte ponovno za trenutak ili povećajte vremensko ograničenje.
status-models = Modeli: { $models }.
status-loading-models = Poslužitelj učitava modele ({ $models }). Zahtjev čeka dok ne budu spremni.
model-name = { $language }, { $variant ->
    [light] mali
    [heavy] veliki
    [nonstandard] za neformalan tekst
   *[other] { $variant }
}

## The table of the selected word

detail-accent = Naglasak
detail-accent-clitic = klitika: nema svoj naglasak, naslanja se na sljedeću ili na prethodnu riječ
detail-accent-dictionary = rječnički oblik. Naglasak se može pomaknuti u ovom obliku riječi
detail-accent-ambiguous = više čitanja, gramatika ne odlučuje
detail-reading = Izgovor
detail-lemma = Osnovni oblik (lema)
detail-upos = Vrsta riječi
detail-seen = Koliko je puta ova lema viđena
detail-dictionaries = Rječnici

accents-legend = Znakovi naglaska: ȁ kratkosilazni, ȃ dugosilazni, à kratkouzlazni, á dugouzlazni, ā dugi nenaglašeni slog. Oblik u (zagradama) je rječnički oblik, a naglasak može biti drukčiji u obliku u rečenici. Izvor: Wiktionary, CC BY-SA.

## The parts of speech

upos-NOUN = imenica
upos-PROPN = vlastita imenica
upos-VERB = glagol
upos-AUX = pomoćni glagol
upos-ADJ = pridjev
upos-ADV = prilog
upos-PRON = zamjenica
upos-DET = determinator
upos-ADP = prijedlog
upos-CCONJ = nezavisni veznik
upos-SCONJ = zavisni veznik
upos-PART = čestica
upos-NUM = broj
upos-INTJ = uzvik
upos-PUNCT = interpunkcija
upos-SYM = simbol
upos-X = ostalo

## The names of the features

feat-Case = Padež
feat-Gender = Rod
feat-Number = Broj
feat-Person = Lice
feat-Tense = Vrijeme
feat-Mood = Način
feat-VerbForm = Glagolski oblik
feat-Voice = Stanje
feat-Degree = Stupanj
feat-Definite = Određenost
feat-Animacy = Živost
feat-PronType = Vrsta zamjenice
feat-Poss = Posvojnost
feat-Reflex = Povratnost
feat-Polarity = Polarnost
feat-NumType = Vrsta broja
feat-Number-psor = Broj posjednika
feat-Gender-psor = Rod posjednika
feat-Variant = Varijanta
feat-Foreign = Strana riječ
feat-Abbr = Kratica
feat-Clitic = Klitika

## The values of the features

featval-Nom = nominativ
featval-Gen = genitiv
featval-Dat = dativ
featval-Acc = akuzativ
featval-Voc = vokativ
featval-Loc = lokativ
featval-Ins = instrumental
featval-Masc = muški rod
featval-Fem = ženski rod
featval-Neut = srednji rod
featval-Sing = jednina
featval-Plur = množina
featval-Pres = prezent
featval-Past = prošlo vrijeme
featval-Fut = futur
featval-Imp = imperfekt / imperativ
featval-Aor = aorist
featval-Ind = indikativ
featval-Cnd = kondicional
featval-Fin = finitni oblik
featval-Inf = infinitiv
featval-Part = particip
featval-Ger = gerund
featval-Conv = glagolski prilog
featval-Act = aktiv
featval-Pass = pasiv
featval-Pos = pozitiv
featval-Cmp = komparativ
featval-Sup = superlativ
featval-Abs = apsolutni superlativ
featval-Neg = niječno
featval-Def = određeno
featval-Anim = živo
featval-Inan = neživo
featval-Prs = osobna
featval-Dem = pokazna
featval-Int = upitna
featval-Rel = odnosna
featval-Tot = opća
featval-Card = glavni
featval-Ord = redni
featval-Mult = multiplikativni
featval-Yes = da
featval-Short = kratki oblik
featval-Art = član
featval-Sub = konjunktiv
featval-Indef = neodređeno
featval-Definite-Ind = neodređeno

## The problems that the checks find

problem-repeat = '{ $words }' se ponavlja.
problem-spelling = Popis riječi za jezik { $languageName } nema ovu riječ.
problem-spelling-suggestion = Popis riječi za jezik { $languageName } nema ovu riječ. Jeste li mislili '{ $better }'?
problem-hr-lexicon = Leksikon (hrLex) nema ovu riječ. To može biti pravopisna pogreška, rijetka riječ ili ime.
problem-hr-genitive-adjective = '{ $word }' traži imenicu u genitivu (puna vode), a padež ovog oblika je { $gotName }.
problem-preposition-case = Prijedlog '{ $word }' ovdje traži { $wantName }, a padež ovog oblika je { $gotName }.
problem-preposition-cases = Prijedlog '{ $word }' traži { $want }, a padež ovog oblika je { $gotName }.
problem-case-in-list = { $caseName }
problem-agreement = Ne slaže se s '{ $noun }': ovaj oblik je { $mineName }, a imenica je { $theirsName } ({ $feat ->
    [Case] padež
    [Gender] rod
   *[Number] broj
}).
problem-hr-object = Subjekt je već u glagolu '{ $verb }', pa ova imenica nije subjekt. Objekt je obično u akuzativu, a ovaj oblik je nominativ.
problem-de-adjective-ending = Nastavak -{ $ending } ne odgovara imenici '{ $noun }' ({ $formName }, { $caseName }). { $kind ->
    [weak] Nakon riječi kao što je der
    [mixed] Nakon riječi kao što je ein
   *[strong] Bez člana
} nastavak je -{ $expected }.
problem-en-agreement = '{ $verb }' se ne slaže sa { $subject ->
    [first] subjektom 'I'
    [singular] subjektom u jednini
   *[plural] subjektom u množini
}. { $fix ->
    [form] Točan oblik je '{ $correct }'.
    [add-s] Glagol treba nastavak -s.
   *[no-s] Glagol ovdje nema nastavak -s.
}

## Errors

error-server = Poslužitelj je vratio { $status }.
error-no-languages = Popis jezika nije učitan.
error-not-admin = Samo administrator može vidjeti kartice drugog korisnika.
error-ai-no-key = poslužitelj nema ključ za AI uslugu
error-ai-limit = ograničenje je { $limit } pitanja na dan
error-ai-needs-review = pitanje { $question } treba odgovor na karticu
error-ai-timeout = AI usluga nije odgovorila na vrijeme
error-ai-busy = AI usluga ima previše zahtjeva ili nema kredita
error-ai-http = AI usluga je vratila HTTP { $status }
error-ai-empty = AI usluga je dala prazan odgovor
error-translator-timeout = { $service } nije odgovorio na vrijeme
error-translator-quota = kvota za { $service } za ovaj mjesec je potrošena
error-translator-busy = { $service } ima previše zahtjeva, pokušajte ponovno
error-translator-http = { $service } je vratio HTTP { $status }
error-voice-no-service = poslužitelj nema uslugu za glas
error-voice-timeout = usluga za glas nije odgovorila na vrijeme
error-voice-http = usluga za glas vratila je HTTP { $status }
error-voice-language = usluga za glas ne čita ovaj jezik

## The flashcard tab

cards-title = Kartice
cards-intro = Kartica pokazuje tekst. Unesite ga na drugom jeziku. Zatim vidite raščlambu svog odgovora i točnog odgovora, a kartica se vraća kasnije: ubrzo nakon pogrešnog odgovora, a nakon duljeg vremena sa svakim točnim odgovorom.
cards-language-note = Kartice ostaju na jezicima na kojima su napisane. Oni se mogu razlikovati od jezika stranice.
cards-all-decks = Svi špilovi
cards-give-up = Ne znam
cards-check = Provjeri
cards-speak = Pročitaj naglas
cards-next = Sljedeća kartica
cards-no-decks = Nema špilova. Administrator ih dodaje na poslužitelju (vidi README).
cards-counts = novih: { $new } · u učenju: { $learning } · za ponavljanje: { $due }
cards-group-summary = { $decks ->
    [one] { $decks } špil
    [few] { $decks } špila
   *[other] { $decks } špilova
} · { $counts }
cards-deck-summary = { $language } · { $cards ->
    [one] { $cards } kartica
    [few] { $cards } kartice
   *[other] { $cards } kartica
}
cards-done = Zasad nema više kartica.
cards-done-next = Zasad nema više kartica. Sljedeća dolazi { $when }.
cards-task-text = Unesite ovo na jeziku: { $language }.
cards-task-media = Unesite ono što vidite ili čujete na jeziku: { $language }.
cards-your-answer = Vaš odgovor
cards-no-answer = Bez odgovora
cards-correct-answer = Točan odgovor
cards-accepted-answers = Svi prihvaćeni odgovori:
cards-next-due = { $rating }: ova se kartica vraća { $when }.
time-now = sada

rating-1 = Ponovno
rating-2 = Teško
rating-3 = Dobro
rating-4 = Lako
rating-button-1 = 1 { rating-1 }
rating-button-2 = 2 { rating-2 }
rating-button-3 = 3 { rating-3 }
rating-button-4 = 4 { rating-4 }

speech-no-voice = Ovaj preglednik nema glas za jezik: { $language }.
speech-no-voices = Ovaj preglednik nema glasove, pa ne može čitati tekst naglas.
speech-error = Preglednik ne može ovo pročitati naglas ({ $error }).

## The questions to the AI

explain-ask = Pitaj AI:
explain-context-placeholder = Neobavezno: više o vašem pitanju, na primjer „zašto ovaj glagol?”
explain-working = AI piše odgovor.
explain-timeout = Nema odgovora nakon { $seconds } s. Pokušajte ponovno.
explain-written-by = Ovo je napisao model { $model }. Može biti pogrešno.
explain-question-meaning = Što ovo znači?
explain-question-grammar = Objasni gramatiku
explain-question-register = Je li ovo razgovorno?
explain-question-why_wrong = Zašto je moj odgovor pogrešan?
explain-question-also_right = Je li i moj odgovor točan?
explain-question-difference = U čemu je razlika?

## The "Listen" buttons

listen-label = Poslušaj:
listen-working = Usluga za glas čita tekst.
listen-timeout = Nema zvuka nakon { $seconds } s. Pokušajte ponovno.
listen-made-by = Ovo je pročitao model { $model }.

## The progress tab

progress-cards-of = Kartice korisnika
progress-own-cards = Moje kartice
progress-no-answers = Još nema odgovora.
progress-answers = Odgovori
progress-passed = Nije „{ rating-1 }”
progress-lapses = Zaboravljeno nakon što je kartica bila naučena
progress-streak = Dana zaredom
progress-cards = Kartice
progress-cards-value = { $total } ({ $counts })
progress-days-note = Odgovori po danu, zadnjih 90 dana. Tamni dio je udio odgovora koji nisu „{ rating-1 }”.
progress-rate-note = Udio odgovora koji nisu „{ rating-1 }”, za svaki dan. Dan bez odgovora nema stupac.
progress-day-answers = { $date }: { $answers ->
    [one] { $answers } odgovor
    [few] { $answers } odgovora
   *[other] { $answers } odgovora
}, od toga { $passed } nije „{ rating-1 }”
progress-day-rate = { $date }: { $rate }
progress-day-none = { $date }: nema odgovora
