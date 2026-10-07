// The flashcard tab, and the tabs themselves. Uses breakdown.js: $, el,
// makeView, renderSentences, drawLinks, views, languages, englishInfo and
// languagesLoaded, serverError. The text is in the catalogs of i18n.js.

// The keys of the ratings. The name of a rating is the message "rating-1".
const RATINGS = [1, 2, 3, 4];
const cardView = makeView($("card-result"), $("card-detail"));
// The deck and the card on the page, and the answer of the server to the
// text of the user (null before the user answers).
let deck = null;
let card = null;
let answered = null;
let shownAt = 0;
let promptChips = [];

// The tabs

function showTab(name) {
  // The CSS hides the legend and the accent note on the progress tab.
  document.body.dataset.tab = name;
  for (const section of document.querySelectorAll(".tab")) {
    section.hidden = section.id !== "tab-" + name;
  }
  for (const button of document.querySelectorAll("#tabs button")) {
    button.classList.toggle("current", button.dataset.tab === name);
  }
  // The accent note is for the language of the words on the tab.
  if (name === "breakdown") showSource(); else showDeckAccents();
  // The curves need the geometry, which a hidden tab does not have.
  views.forEach(drawLinks);
  if (name === "cards" && !deck) loadDecks();
  // Each time: the numbers change with each answer in the other tab.
  if (name === "progress") loadProgress();
}
// The list of decks has no words, so it has no accent note.
function showDeckAccents() {
  const info = deck && languages[deck.language];
  $("accents").hidden = !(info && info.has_accents);
}
function tabOfAddress() {
  const name = location.hash.slice(1);
  return name === "cards" || name === "progress" ? name : "breakdown";
}
for (const button of document.querySelectorAll("#tabs button")) {
  button.addEventListener("click", () => {
    // replaceState: a tab is not a step of the Back button.
    const name = button.dataset.tab;
    history.replaceState(null, "", name === "breakdown" ? location.pathname : "#" + name);
    showTab(button.dataset.tab);
  });
}
window.addEventListener("hashchange", () => showTab(tabOfAddress()));

// The server

// signal: an AbortSignal that stops the request, or undefined.
async function api(path, body, signal) {
  const options = body === undefined ? { signal } : {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
    signal,
  };
  const response = await fetch("/api/v1" + path, options);
  if (!response.ok) throw await serverError(response);
  return response.json();
}

function cardsStatus(text, isError) {
  $("cards-status").className = isError ? "error" : "";
  $("cards-status").textContent = text;
}

// Run an action of the page. An error goes to the status line.
async function attempt(action) {
  try {
    const working = t($("cards-heavy").checked ? "status-working-heavy" : "status-working");
    cardsStatus(working);
    await action();
    if ($("cards-status").textContent === working) cardsStatus("");
  } catch (error) {
    cardsStatus(error.message, true);
  }
}

function countsText(counts) {
  return t("cards-counts", { new: counts.new, learning: counts.learning, due: counts.due });
}

// The list of decks

async function loadDecks() {
  deck = card = answered = null;
  showDeckAccents();
  $("card").hidden = true;
  // A clip must not play on.
  showMedia($("card-media"), []);
  showMedia($("answer-media"), []);
  await attempt(async () => {
    const { decks } = await api("/decks");
    const list = $("deck-list");
    list.replaceChildren();
    list.hidden = false;
    if (!decks.length) {
      cardsStatus(t("cards-no-decks"));
    }
    // A subdeck has a path: the name of its package, then the parts of its
    // Anki name. The decks come in the order of the tree, so each heading
    // opens one group, and a deck goes into the group of its parent.
    const groups = new Map();
    for (const each of decks) {
      let parent = list;
      const inner = each.path.slice(0, -1);
      inner.forEach((part, depth) => {
        const key = JSON.stringify(inner.slice(0, depth + 1));
        if (!groups.has(key)) {
          const under = decks.filter((other) => JSON.stringify(other.path.slice(0, depth + 1)) === key);
          const heading = el("div", undefined, "deck-heading");
          heading.append(
            el(depth ? "h4" : "h3", part),
            el("span", t("cards-group-summary", {
              decks: under.length, counts: countsText(sumCounts(under)),
            })),
          );
          const group = el("div", undefined, "deck-group");
          parent.append(heading, group);
          groups.set(key, group);
        }
        parent = groups.get(key);
      });
      parent.append(deckButton(each));
    }
  });
}

function sumCounts(decks) {
  const sum = { total: 0, new: 0, learning: 0, due: 0 };
  for (const each of decks) {
    for (const key of Object.keys(sum)) sum[key] += each.counts[key];
  }
  return sum;
}

function deckButton(each) {
  const info = languages[each.language];
  const button = el("button", undefined, "deck plain");
  button.type = "button";
  button.append(
    // In a group, the headings over it give the first parts of the name.
    el("strong", each.path.length ? each.path[each.path.length - 1] : each.name),
    el("span", t("cards-deck-summary", {
      language: info ? languageName(info) : each.language, cards: each.counts.total,
    })),
    el("span", countsText(each.counts)),
  );
  button.addEventListener("click", () => { deck = each; showDeckAccents(); nextCard(); });
  return button;
}

// A card

// The language of the prompt and the language of the answer.
function sides() {
  const study = languages[card.language];
  return card.direction === "to_study" ? [englishInfo, study] : [study, englishInfo];
}

// The images and the sound clips of one side of a card. play: start the
// first clip at once.
function showMedia(container, media, play) {
  container.replaceChildren(...(media || []).map((each) => {
    if (each.kind === "image") {
      const image = el("img");
      image.src = each.url;
      image.alt = "";
      return image;
    }
    const audio = el("audio");
    audio.src = each.url;
    audio.controls = true;
    audio.preload = play ? "auto" : "none";
    return audio;
  }));
  const first = container.querySelector("audio");
  // A browser can refuse a clip that no click started. The controls stay.
  if (play && first) first.play().catch(() => {});
}

async function nextCard() {
  await attempt(async () => {
    const heavy = $("cards-heavy").checked;
    const data = await api("/decks/" + deck.id + "/next?heavy=" + heavy);
    answered = null;
    $("deck-list").hidden = true;
    $("card").hidden = false;
    $("answered").hidden = true;
    $("deck-name").textContent = deck.path.length ? deck.path.join(" › ") : deck.name;
    $("deck-counts").textContent = countsText(data.counts);
    cardView.result.replaceChildren();
    cardView.detail.replaceChildren();
    cardView.linked = [];
    drawLinks(cardView);
    showMedia($("card-media"), data.media, true);
    showMedia($("answer-media"), []);
    setExplain("card-explain", null);
    if (data.done) {
      card = null;
      $("answer-form").hidden = true;
      $("card-task").textContent = data.next_due
        ? t("cards-done-next", { when: when(data.next_due) })
        : t("cards-done");
      return;
    }
    card = data;
    const [promptInfo, answerInfo] = sides();
    // A card can have a picture or a clip as its whole prompt.
    $("card-task").textContent = t(card.prompt ? "cards-task-text" : "cards-task-media", {
      language: languageName(answerInfo),
    });
    promptChips = renderSentences(cardView.result, card.prompt_sentences, promptInfo, cardView);
    $("answer-form").hidden = false;
    $("answer").value = "";
    inLanguage($("answer"), answerInfo);
    // The tag with the region, if there is one: a keyboard can use it.
    if (answerInfo.speech) $("answer").lang = answerInfo.speech;
    $("answer").focus();
    shownAt = performance.now();
  });
}

// "in 5 minutes", in the words of the locale.
function when(isoTime) {
  const minutes = Math.round((new Date(isoTime) - Date.now()) / 60000);
  if (minutes < 1) return t("time-now");
  const [amount, unit] = minutes < 90 ? [minutes, "minute"]
    : minutes < 36 * 60 ? [Math.round(minutes / 60), "hour"]
    : [Math.round(minutes / 1440), "day"];
  return new Intl.RelativeTimeFormat(uiLocale).format(amount, unit);
}

async function check(typed) {
  if (!card || answered) return;
  await attempt(async () => {
    answered = await api("/cards/" + card.card_id + "/answer", {
      typed,
      heavy: $("cards-heavy").checked,
      elapsed_ms: Math.round(performance.now() - shownAt),
    });
    showAnswer(typed);
  });
}

function showAnswer(typed) {
  const [, answerInfo] = sides();
  const result = cardView.result;
  // The answer of the user goes over the prompt, and the correct answer
  // under it. A link is [word of the study language, English word], and
  // drawLinks needs the upper chip first.
  const toStudy = card.direction === "to_study";
  const pairs = (side, chips, above) => ["links", "guesses"].flatMap((kind) =>
    (side[kind] || []).map(([i, j]) => {
      const [answer, prompt] = toStudy ? [chips[i], promptChips[j]] : [chips[j], promptChips[i]];
      return above ? [answer, prompt, kind === "guesses"] : [prompt, answer, kind === "guesses"];
    }).filter(([from, to]) => from && to));

  const typedLines = document.createDocumentFragment();
  typedLines.append(el("p", t(typed.trim() ? "cards-your-answer" : "cards-no-answer"), "note"));
  const typedChips = renderSentences(typedLines, answered.typed.sentences, answerInfo, cardView);
  const promptLines = [...result.children];
  result.prepend(typedLines);
  // A prompt with only a picture has no line.
  if (typedChips.length && promptLines.length) promptLines[0].classList.add("translated");

  const correctLines = document.createDocumentFragment();
  const correctChips = renderSentences(correctLines, answered.correct.sentences, answerInfo, cardView);
  if (correctLines.firstChild) correctLines.firstChild.classList.add("translated");
  result.append(correctLines, el("p", t("cards-correct-answer"), "note"));

  cardView.linked = [
    ...pairs(answered.typed, typedChips, true),
    ...pairs(answered.correct, correctChips, false),
  ];

  // Wrong letters are struck out, and missing ones are marked.
  const diff = $("diff");
  diff.replaceChildren();
  inLanguage(diff, answerInfo);
  for (const [op, text] of answered.diff) diff.append(el("span", text, op));
  // A label with answers after it, so each answer keeps its own direction.
  $("other-answers").hidden = answered.answers.length < 2;
  $("other-answers").replaceChildren(t("cards-accepted-answers") + " ");
  answered.answers.forEach((answer, index) => {
    $("other-answers").append(index ? " · " : "", bdi(answer, answerInfo));
  });

  showMedia($("answer-media"), answered.media, true);
  $("answer-form").hidden = true;
  $("answered").hidden = false;
  $("speak").hidden = !("speechSynthesis" in window) || !languages[card.language].speech;
  showRating(answered.rating, answered.next_due);
  setExplain("card-explain", {
    path: "/reviews/" + answered.review_id + "/explain", body: {}, where: ["card", "sentence"],
  });
  drawLinks(cardView);
  $("next").focus();
}

function showRating(rating, nextDue) {
  for (const button of document.querySelectorAll("#ratings button")) {
    button.classList.toggle("current", Number(button.dataset.rating) === rating);
  }
  $("next-due").textContent = t("cards-next-due", {
    rating: t("rating-" + rating), when: when(nextDue),
  });
}

async function changeRating(rating) {
  if (!answered) return;
  await attempt(async () => {
    const data = await api("/reviews/" + answered.review_id + "/rating", { rating });
    showRating(data.rating, data.next_due);
  });
}

// Always the text in the study language: the answer, or for a card that asks
// for the English, the prompt.
// The browser loads its voices in the background, so the first list can be
// empty. Waits for the list, but not for long: some browsers have no voice.
function loadVoices() {
  const voices = speechSynthesis.getVoices();
  if (voices.length) return Promise.resolve(voices);
  return new Promise((resolve) => {
    const done = () => resolve(speechSynthesis.getVoices());
    speechSynthesis.addEventListener("voiceschanged", done, { once: true });
    setTimeout(done, 1000);
  });
}

async function speak() {
  const info = languages[card.language];
  const text = card.direction === "to_study" ? answered.correct.sentences.map((s) => s.text).join(" ")
    : card.prompt;
  const voices = await loadVoices();
  const voice = voices.find((each) => each.lang.replace("_", "-").startsWith(info.code));
  if (!voice) {
    // The voices come from the operating system. On Linux, that is Speech
    // Dispatcher, and a browser in a Flatpak often cannot reach it.
    cardsStatus(voices.length ? t("speech-no-voice", { language: languageName(info) })
      : t("speech-no-voices"), true);
    return;
  }
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = info.speech;
  utterance.voice = voice;
  utterance.addEventListener("error", (event) => {
    if (event.error !== "canceled" && event.error !== "interrupted") {
      cardsStatus(t("speech-error", { error: event.error }), true);
    }
  });
  speechSynthesis.cancel();
  speechSynthesis.speak(utterance);
}

// In an input method (IME), Enter accepts a word. That Enter must not send
// the answer. keyCode 229 is what Safari gives, where isComposing is late.
$("answer").addEventListener("keydown", (event) => {
  if (event.key === "Enter" && (event.isComposing || event.keyCode === 229)) event.preventDefault();
});
$("answer-form").addEventListener("submit", (event) => {
  event.preventDefault();
  check($("answer").value);
});
$("give-up").addEventListener("click", () => check(""));
$("next").addEventListener("click", nextCard);
$("speak").addEventListener("click", speak);
$("to-decks").addEventListener("click", loadDecks);
for (const button of document.querySelectorAll("#ratings button")) {
  button.addEventListener("click", () => changeRating(Number(button.dataset.rating)));
}
// 1 to 4 change the rating, like in Anki. Enter is "Next card": that button
// has the focus.
document.addEventListener("keydown", (event) => {
  if ($("tab-cards").hidden || !answered || $("answered").hidden) return;
  if (event.target instanceof HTMLInputElement || event.ctrlKey || event.metaKey || event.altKey) return;
  if (RATINGS.includes(Number(event.key))) changeRating(Number(event.key));
});

// The deck list shows the names of the languages, so the list must be there.
languagesLoaded.then(() => showTab(tabOfAddress()));
