// The text of the page is in the catalogs of i18n.js: t, tOr, tagId,
// languageName, formatList, setL10nArgs, uiLocale and localeLoaded.

// The fixed palette: one color for each Universal POS tag. The name of a tag
// is the message "upos-NOUN".
const UPOS = {
  NOUN:  "#9ecbff",
  PROPN: "#6fa8ff",
  VERB:  "#ff9e9e",
  AUX:   "#ffc3a0",
  ADJ:   "#a8e6a1",
  ADV:   "#d4f0a0",
  PRON:  "#d9b3ff",
  DET:   "#f0b8e8",
  ADP:   "#ffe08a",
  CCONJ: "#ffd0b0",
  SCONJ: "#f5c28a",
  PART:  "#a0e8e0",
  NUM:   "#b8d8d0",
  INTJ:  "#ffb0d0",
  PUNCT: "#d8d8d2",
  SYM:   "#c8c8c0",
  X:     "#bdbdb5",
};
function uposName(upos) { return t(tagId("upos", upos in UPOS ? upos : "X")); }

// The study languages by code, and English, from /api/v1/languages. Each one
// has: code, name, tag_name (the name of its xpos tag set), placeholder,
// variants, has_accents, direction, dictionary_links.
let languages = {};
let englishInfo = {
  code: "en", name: "English", tag_name: "Penn Treebank tag", direction: "ltr", dictionary_links: [],
};
// True when the server sets TLHELPER_ALWAYS_LARGE, as the compose file does.
let largeByDefault = false;

// Readable names for the feature names and values that the taggers return:
// the messages "feat-Case" and "featval-Nom". A tag with no message shows as
// it is. "Ind" is the indicative of a verb, but for German "ein" it is
// indefinite: a message with the feature name ("featval-Definite-Ind") wins
// over the plain value.
function featName(name) { return tOr(tagId("feat", name), null, name); }
function featValue(name, value) {
  return tOr(tagId("featval", name + "-" + value), null, tOr(tagId("featval", value), null, value));
}

// A problem that a check found. The server gives the English sentence, and
// the id and the parameters of the message (problem_messages, in the order
// of problems). A parameter is a raw value, and Fluent cannot look up the
// word for the value of a variable, so this adds the words:
//   got: "Acc"       also gotName: "accusative" (the message "featval-Acc")
//   language: "de"   also languageName: "German"
//   want: [tags]     "the accusative or the dative", from "problem-case-in-list"
// A message can still select on the raw value, for a word with another form.
function problemText(word, index) {
  const message = (word.problem_messages || [])[index];
  if (!message) return word.problems[index];
  const named = (tag) => tOr(tagId("featval", String(tag)), null, "");
  const args = {};
  for (const [name, value] of Object.entries(message.params)) {
    if (Array.isArray(value)) {
      const items = value.map((tag) => t("problem-case-in-list", { case: tag, caseName: named(tag) }));
      args[name] = formatList(items, "disjunction");
      continue;
    }
    args[name] = value;
    if (named(value)) args[name + "Name"] = named(value);
    if (name === "language") {
      const info = languages[value] || (value === englishInfo.code ? englishInfo : null);
      args.languageName = info ? languageName(info) : value;
    }
  }
  return tOr(message.key, args, word.problems[index]);
}

const $ = (id) => document.getElementById(id);

function el(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (className) node.className = className;
  return node;
}

// The browser selects the font and the letter shapes from lang: without it,
// Japanese text can get the Chinese shapes. dir is for a script that goes
// from right to left.
function inLanguage(node, info) {
  node.lang = info.code || "";
  node.dir = info.direction || "ltr";
  return node;
}
// A text in a language, for the middle of an English line: the direction of
// the text then has no effect on the punctuation around it.
function bdi(text, info) { return inLanguage(el("bdi", text), info); }

function color(upos) { return UPOS[upos] || UPOS.X; }

// The short note after the tag, with the first letter of each feature value.
// A noun, an adjective, a pronoun or a determiner such as "moj":
// case/gender/number, so "Acc", "Fem", "Sing" is "A/F/S". A verb: the verb form ("Inf" is "I"), then
// person/number for a finite verb or gender/number for a participle. A missing
// feature is "–". A word with none of the features has no note.
const NOMINAL_UPOS = ["NOUN", "PROPN", "ADJ", "DET", "PRON"];
const NOMINAL_FEATS = ["Case", "Gender", "Number"];
const VERB_FORM_FEATS = { Fin: ["Person", "Number"], Part: ["Gender", "Number"] };
function noteFeats(word) {
  const feats = word.feats || {};
  if (NOMINAL_UPOS.includes(word.upos)) return NOMINAL_FEATS;
  if (["VERB", "AUX"].includes(word.upos) && feats.VerbForm) {
    return ["VerbForm", ...(VERB_FORM_FEATS[feats.VerbForm] || [])];
  }
  return [];
}
function featNote(word) {
  const feats = word.feats || {};
  const names = noteFeats(word);
  if (!names.some((name) => feats[name])) return "";
  const letters = names.map((name) =>
    feats[name] ? feats[name].split(",").map((value) => value[0]).join(",") : "–");
  return letters.join("/");
}
function featNoteTitle(word) {
  const feats = word.feats || {};
  return noteFeats(word).filter((name) => feats[name])
    .map((name) => featName(name) + ": " + featValue(name, feats[name])).join(", ");
}

// The error of a response that is not ok. The server gives an English
// `detail`, and for an error with a message also its `code` and `params`.
async function serverError(response) {
  const body = await response.json().catch(() => null);
  let detail = body && typeof body.detail === "string" ? body.detail : "";
  if (body && body.code) detail = tOr("error-" + body.code, body.params, detail);
  return new Error(t("error-server", { status: response.status }) + (detail ? " " + detail : ""));
}

// A view is one place that shows sentences: `result` holds the chips and the
// curves, `detail` shows the selected word, and `linked` is the list of chip
// pairs for the curves. The breakdown tab and the flashcard tab have one each.
const views = [];
function makeView(result, detail) {
  const view = { result, detail, linked: [] };
  views.push(view);
  return view;
}
const breakdownView = makeView($("result"), $("detail"));

// info: the language of the word.
function showDetail(word, chip, info, view) {
  document.querySelectorAll(".chip.selected").forEach((c) => c.classList.remove("selected"));
  chip.classList.add("selected");
  // The selected word gets a thick curve.
  drawLinks(view);

  const detail = view.detail;
  const problems = word.problems || [];
  const heading = el("h2", undefined, problems.length ? "problem" : "");
  heading.append(bdi(word.text, info));
  detail.replaceChildren(heading);
  if (problems.length) {
    const list = el("ul", undefined, "problems");
    problems.forEach((problem, index) => list.append(el("li", problemText(word, index))));
    detail.append(list);
  }
  const table = el("table");
  const addRow = (name, value, note) => {
    const tr = el("tr");
    tr.append(el("th", name));
    const td = el("td", value);
    if (note) td.append(" ", el("small", note));
    tr.append(td);
    table.append(tr);
  };
  if (word.accent) {
    const accent = word.accent;
    addRow(t("detail-accent"), accent.form,
      accent.clitic ? t("detail-accent-clitic")
      : !accent.exact ? t("detail-accent-dictionary")
      : accent.ambiguous ? t("detail-accent-ambiguous")
      : "");
  }
  if (word.reading) addRow(t("detail-reading"), word.reading);
  addRow(t("detail-lemma"), word.lemma);
  addRow(t("detail-upos"), uposName(word.upos), word.upos);
  if (word.xpos) addRow(tOr("language-" + info.code + "-tag-name", null, info.tag_name), word.xpos);
  for (const [name, value] of Object.entries(word.feats)) {
    addRow(featName(name), featValue(name, value), name + "=" + value);
  }
  if (word.seen !== null && word.seen !== undefined) {
    addRow(t("detail-seen"), String(word.seen));
  }
  if (info.dictionary_links.length) {
    // "{lemma}" in a label or an address stands for the lemma of the word.
    const tr = el("tr");
    const td = el("td");
    for (const [label, href] of info.dictionary_links) {
      const link = el("a", label.replace("{lemma}", word.lemma));
      link.href = href.replace("{lemma}", encodeURIComponent(word.lemma));
      link.target = "_blank";
      link.rel = "noopener";
      if (td.childNodes.length) td.append(" · ");
      td.append(link);
    }
    tr.append(el("th", t("detail-dictionaries")), td);
    table.append(tr);
  }
  detail.append(table);
}

// info: the language of the sentences. Returns the chips of all sentences in
// order, which is the order of the indexes in translation.links.
function renderSentences(container, sentences, info, view) {
  const chips = [];
  for (const sentence of sentences) {
    // A flex row follows dir, so the first word of a right-to-left sentence
    // is on the right.
    const line = inLanguage(el("div", undefined, "sentence"), info);
    for (const word of sentence.words) {
      const chip = el("button", undefined, "chip");
      chip.type = "button";
      chip.style.background = color(word.upos);
      // A red wavy line under a word that fails a grammar check.
      if (word.problems && word.problems.length) chip.classList.add("problem");
      chip.append(el("span", word.text, "w"));
      // Only a language with accent data has the accent key. No data for a
      // word shows as a dash.
      // A dictionary form that is not this form of the word is in parentheses.
      if ("accent" in word) {
        const accent = word.accent;
        const shown = !accent ? "–" : accent.exact ? accent.form : "(" + accent.form + ")";
        chip.append(el("span", shown, accent && !accent.exact ? "a approx" : "a"));
      }
      // How to say the word, for a script that does not show it.
      if (word.reading) chip.append(el("span", word.reading, "r"));
      const tag = el("span", word.upos, "p");
      const note = featNote(word);
      if (note) {
        tag.append(" ", el("span", "(" + note + ")", "f"));
        tag.title = featNoteTitle(word);
      }
      chip.append(el("span", word.lemma, "l"), tag);
      chip.addEventListener("click", () => showDetail(word, chip, info, view));
      line.append(chip);
      chips.push(chip);
    }
    container.append(line);
  }
  return chips;
}

// One curve for each pair in view.linked: from the bottom of the upper chip
// to the top of the lower chip. The curve leaves and arrives vertically, so
// crossed links stay readable.
function drawLinks(view) {
  const result = view.result;
  const old = result.querySelector(":scope > svg.links");
  if (old) old.remove();
  // A hidden tab has no geometry. The tab draws again when it shows.
  if (!view.linked.length || !result.offsetParent) return;
  const NS = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(NS, "svg");
  svg.setAttribute("class", "links");
  const box = result.getBoundingClientRect();
  for (const [from, to, guess] of view.linked) {
    const a = from.getBoundingClientRect();
    const b = to.getBoundingClientRect();
    const x1 = a.left + a.width / 2 - box.left, y1 = a.bottom - box.top;
    const x2 = b.left + b.width / 2 - box.left, y2 = b.top - box.top;
    const bend = Math.max(24, (y2 - y1) / 2);
    const path = document.createElementNS(NS, "path");
    path.setAttribute("d", `M ${x1} ${y1} C ${x1} ${y1 + bend}, ${x2} ${y2 - bend}, ${x2} ${y2}`);
    const selected = from.classList.contains("selected") || to.classList.contains("selected");
    path.setAttribute("class", (guess ? "guess " : "") + (selected ? "selected" : ""));
    svg.append(path);
  }
  result.append(svg);
}

window.addEventListener("resize", () => views.forEach(drawLinks));

function render(data) {
  const view = breakdownView;
  const result = view.result;
  result.replaceChildren();
  view.detail.replaceChildren();
  view.linked = [];
  // The questions to the AI are about the text in the study language. A
  // translation that failed has no such text.
  setExplain("explain", data.text
    ? { path: "/explain", body: { text: data.text, language: data.language }, where: ["sentence"] }
    : null);
  const translation = data.translation;
  // The voice service can read each side (listen.js). data.text is always
  // the study language, and translation.text the English.
  setListen("listen", [
    { text: data.text, language: data.language, info: languages[data.language] },
    {
      text: translation && !translation.error ? translation.text : "",
      language: englishInfo.code,
      info: englishInfo,
    },
  ]);
  // The text that the user entered is on top, and its translation is under
  // it. data.sentences is always the side of the study language.
  const sides = {
    study: { sentences: data.sentences, info: languages[data.language], chips: [] },
    en: { sentences: (translation && translation.sentences) || [], info: englishInfo, chips: [] },
  };
  const [top, bottom] = data.source === "en" ? [sides.en, sides.study] : [sides.study, sides.en];
  top.chips = renderSentences(result, top.sentences, top.info, view);
  if (!translation) return;
  if (translation.error) {
    const error = translation.error_code
      ? tOr("error-" + translation.error_code, translation.error_params, translation.error)
      : translation.error;
    result.append(el("p", t("breakdown-no-translation", { error }), "note"));
    return;
  }
  // Each translated sentence goes directly under its source sentence, with
  // room for the curves. That keeps the curves short. It needs the same
  // number of sentences on both sides. If not, all the translation comes last.
  const lines = [...result.children];
  bottom.sentences.forEach((sentence, index) => {
    const holder = document.createDocumentFragment();
    bottom.chips.push(...renderSentences(holder, [sentence], bottom.info, view));
    const line = holder.firstChild;
    const paired = lines.length === bottom.sentences.length;
    if (paired || index === 0) line.classList.add("translated");
    if (paired) lines[index].after(line);
    else result.append(line);
  });
  const note = el("p", t("breakdown-side-label", { language: languageName(bottom.info) }) + " ", "note");
  note.append(bdi(data.source === "en" ? data.text : translation.text, bottom.info));
  result.append(note);
  // A pair is [study index, English index]. drawLinks needs the upper chip
  // first.
  const chips = (pairs, guess) => (pairs || [])
    .map(([i, j]) => [sides.study.chips[i], sides.en.chips[j], guess])
    .map(([study, en, guess]) => (top === sides.study ? [study, en, guess] : [en, study, guess]))
    .filter(([from, to]) => from && to);
  view.linked = [...chips(translation.links, false), ...chips(translation.guesses, true)];
  drawLinks(view);
}

async function submit(event) {
  event.preventDefault();
  send(true);
}

// track: count the lemmas. Only an explicit submit counts them, so the
// half-typed words of an automatic send do not end up in the counts.
async function send(track) {
  clearTimeout(debounce);
  const text = $("text").value.trim();
  const heavy = hasVariant("heavy") && $("heavy").checked;
  // The nonstandard models are heavy ones, so they need that checkbox too.
  const nonstandard = heavy && hasVariant("nonstandard") && $("nonstandard").checked;
  const translate = $("translate").checked;
  const source = sourceLanguage();
  const language = $("language").value;
  // No language: the list did not load.
  if (!text || !language) return;
  const sentKey = JSON.stringify([text, heavy, nonstandard, translate, source, language]);
  if (!track && sentKey === lastSent) return;
  lastSent = sentKey;
  const status = $("status");
  status.className = "";
  status.textContent = t(heavy ? "status-working-heavy" : "status-working");
  // The note names the models while they load. Not at once: the server
  // starts the load a moment after it gets the request.
  if (heavy) {
    clearTimeout(modelsTimer);
    modelsTimer = setTimeout(pollModels, MODELS_POLL_MS);
  }
  $("cancel").hidden = false;
  // abort(reason) makes fetch reject with that reason, so the catch block can
  // tell a time-out from the Cancel button and from a newer request.
  if (inFlight) inFlight.abort("superseded");
  const seconds = Math.max(1, Number($("timeout").value) || 5);
  const controller = inFlight = new AbortController();
  const timer = setTimeout(() => controller.abort("timeout"), seconds * 1000);
  try {
    const response = await fetch("/api/v1/classify", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ text, heavy, nonstandard, track, translate, source, language }),
      signal: controller.signal,
    });
    if (!response.ok) throw await serverError(response);
    const data = await response.json();
    render(data);
    status.textContent = t("status-models", { models: modelName(data.language, data.type) });
  } catch (error) {
    if (error === "superseded") return;
    lastSent = null;
    status.className = "error";
    if (error === "timeout") {
      status.textContent = t("status-timeout", { seconds });
      pollModels();
    } else if (error === "cancel") {
      status.className = "";
      status.textContent = t("status-canceled");
    } else {
      status.textContent = error.message;
    }
  } finally {
    clearTimeout(timer);
    // A newer request owns the page state if this one was superseded.
    if (inFlight === controller) {
      inFlight = null;
      $("cancel").hidden = true;
    }
  }
}

// Show a note while the server loads models, for example in the first 10 to
// 20 seconds after a boot. Polls until the load ends, then stops.
const MODELS_POLL_MS = 1000;
let modelsTimer = null;
// "Croatian heavy": the models of one language and one model type.
function modelName(code, variant) {
  const info = languages[code] || (code === englishInfo.code ? englishInfo : { code, name: code });
  return t("model-name", { language: languageName(info), variant });
}
async function pollModels() {
  clearTimeout(modelsTimer);
  let loading = null;
  let again = false;
  try {
    const response = await fetch("/api/v1/status");
    if (response.ok) {
      const data = await response.json();
      // The server of before the locales gives only the English name.
      const model = data.loading_model;
      loading = model ? modelName(model.language, model.variant) : data.loading;
    } else again = true;
  } catch {
    // The server is not reachable, for example in the middle of a restart.
    again = true;
  }
  const note = $("models");
  note.hidden = !loading;
  if (loading) note.textContent = t("status-loading-models", { models: loading });
  if (loading || again) modelsTimer = setTimeout(pollModels, MODELS_POLL_MS);
}

const DEBOUNCE_MS = 500;
let inFlight = null;
let debounce = null;
let lastSent = null;
// The text, the language and the checkboxes stay in localStorage, so they
// are still there after a refresh or a later visit. Storage can be blocked,
// for example in a private window, and the page must work without it.
const STORAGE_KEY = "classla.entry";
// One "Large models" choice for the breakdown tab and the flashcard tab. With
// no choice yet, the server decides.
const HEAVY_KEY = "classla.heavy";
function heavyChoice() {
  try {
    const stored = localStorage.getItem(HEAVY_KEY);
    if (stored === "true" || stored === "false") return stored === "true";
  } catch {}
  return largeByDefault;
}
function setHeavy(checked) {
  $("heavy").checked = checked;
  $("cards-heavy").checked = checked;
  showSource();
}
// "study" or "en": which side the user enters.
function sourceLanguage() {
  return document.querySelector("input[name=source]:checked").value;
}
// name: a model type, "heavy" or "nonstandard".
function hasVariant(name) {
  const info = languages[$("language").value];
  return Boolean(info) && info.variants.includes(name);
}
// Fill the list of languages. With no answer, the list stays empty and
// send() does nothing.
async function loadLanguages() {
  try {
    const response = await fetch("/api/v1/languages");
    if (!response.ok) throw await serverError(response);
    const data = await response.json();
    englishInfo = data.english;
    largeByDefault = data.large_by_default === true;
    for (const info of data.languages) {
      languages[info.code] = info;
      const option = el("option", languageName(info));
      option.value = info.code;
      $("language").append(option);
    }
  } catch (error) {
    $("status").className = "error";
    $("status").textContent = t("error-no-languages") + " " + error.message;
  }
}
// The names and the controls that depend on the language and on the side that
// the user enters. An English text always gets its translation, and DeepL
// writes the standard language, so the two checkboxes have no effect there.
function showSource() {
  const info = languages[$("language").value];
  if (!info) return;
  const english = sourceLanguage() === "en";
  for (const id of ["nonstandard", "translate"]) {
    $(id).disabled = english;
    $(id).parentElement.classList.toggle("off", english);
  }
  const named = { language: languageName(info) };
  for (const node of document.querySelectorAll(".language-text")) setL10nArgs(node, named);
  document.title = t("breakdown-title", named);
  const heavy = hasVariant("heavy") && $("heavy").checked;
  $("heavy-row").hidden = !hasVariant("heavy");
  $("nonstandard-row").hidden = !heavy || !hasVariant("nonstandard");
  $("light-note").hidden = heavy || !info.light_note;
  $("light-note").textContent = tOr("language-" + info.code + "-light-note", null, info.light_note);
  // On the cards tab, the note is for the language of the deck (flashcards.js).
  if (document.body.dataset.tab !== "cards") $("accents").hidden = !info.has_accents;
  $("text").placeholder = english ? englishInfo.placeholder : info.placeholder;
  inLanguage($("text"), english ? englishInfo : info);
}
function saveEntry() {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({
      source: sourceLanguage(),
      language: $("language").value,
      text: $("text").value,
      nonstandard: $("nonstandard").checked,
      translate: $("translate").checked,
    }));
  } catch {}
}
function restoreEntry() {
  $("heavy").checked = $("cards-heavy").checked = heavyChoice();
  try {
    const entry = JSON.parse(localStorage.getItem(STORAGE_KEY)) || {};
    $("text").value = typeof entry.text === "string" ? entry.text : "";
    $("nonstandard").checked = entry.nonstandard === true;
    $("translate").checked = entry.translate === true;
    if (entry.source === "en") document.querySelector("input[name=source][value=en]").checked = true;
    // An entry from before the list of languages has no language: the first
    // one stays selected.
    if (entry.language in languages) $("language").value = entry.language;
  } catch {}
  showSource();
}
function sendSoon() {
  saveEntry();
  clearTimeout(debounce);
  debounce = setTimeout(() => send(false), DEBOUNCE_MS);
}
$("cancel").addEventListener("click", () => inFlight && inFlight.abort("cancel"));
$("form").addEventListener("submit", submit);
// An input method (IME) makes a word from many keys, for example kanji from
// Latin letters. The text in the middle of that is not what the user means.
$("text").addEventListener("input", (event) => { if (!event.isComposing) sendSoon(); });
$("text").addEventListener("compositionend", sendSoon);
$("nonstandard").addEventListener("change", sendSoon);
$("translate").addEventListener("change", sendSoon);
for (const id of ["heavy", "cards-heavy"]) {
  $(id).addEventListener("change", () => {
    try { localStorage.setItem(HEAVY_KEY, $(id).checked); } catch {}
    setHeavy($(id).checked);
  });
}
const showControls = [$("language"), $("heavy"), ...document.querySelectorAll("input[name=source]")];
for (const control of showControls) {
  control.addEventListener("change", () => { showSource(); sendSoon(); });
}
$("text").addEventListener("keydown", (event) => {
  if (event.isComposing) return;
  if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) $("form").requestSubmit();
});
// After the catalog: the legend of the colors, and the accent letters of the
// legend of the accents in bold. A letter is a word of its own there.
function showLegends() {
  for (const [tag, hex] of Object.entries(UPOS)) {
    const item = el("span", tag + " " + uposName(tag));
    item.style.background = hex;
    $("legend").append(item);
  }
  const parts = $("accents").textContent.split(/(?<=^|\s)([ȁȃàáā])(?=\s)/);
  $("accents").replaceChildren(...parts.map((part, index) => (index % 2 ? el("b", part) : part)));
}
// Every text waits for the catalog (i18n.js). The restored entry names a
// language, so the list must be there first. flashcards.js waits for this too.
const languagesLoaded = localeLoaded.then(() => {
  showLegends();
  pollModels();
  return loadLanguages();
});
languagesLoaded.then(() => {
  restoreEntry();
  // Show the breakdown of the restored text again, but do not count its lemmas.
  send(false);
});
