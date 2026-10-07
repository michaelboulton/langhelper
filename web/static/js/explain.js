// The "explain with AI" buttons: /api/v1/explain/questions has the questions,
// and the server writes the prompt. The page sends only the id of a question
// and what the user adds to it. A request goes out only on a click, because
// the text goes to an AI service.
// Uses $, el (breakdown.js) and api (flashcards.js).

// The server stops the AI service after 30 s (explain/base.py TIMEOUT), and the
// tagger can load a model first. A request with no answer after this time (a
// proxy that holds the connection) stops, so the user can ask again.
let explainTimeoutMs = 60_000;
// Null until the list is there. With no key on the server, no panel shows.
let explainQuestions = null;
// For each panel (the id of its element): what the questions are about.
const explainTargets = {};

// target: { path, body, where } or null for nothing to ask about.
//   path, body  the route and the fixed part of its request
//   where       the kinds of question that the route can answer
function setExplain(id, target) {
  const key = JSON.stringify(target);
  // The same target again (an automatic send): keep the answer on the page.
  if (explainTargets[id] && explainTargets[id].key === key) return;
  explainTargets[id] = { key, target };
  drawExplain(id);
}

function drawExplain(id) {
  const panel = $(id);
  const { target } = explainTargets[id] || {};
  panel.replaceChildren();
  panel.hidden = !target || !explainQuestions || !explainQuestions.available;
  if (panel.hidden) return;

  const context = el("input");
  context.type = "text";
  context.maxLength = explainQuestions.max_context_chars;
  context.placeholder = t("explain-context-placeholder");
  const output = el("p", undefined, "explain-text");
  const note = el("p", undefined, "sub");
  const buttons = el("div", undefined, "row");
  buttons.append(el("span", t("explain-ask"), "sub"));
  for (const question of explainQuestions.questions) {
    if (!target.where.includes(question.where)) continue;
    // The server has the English label, for a question with no message.
    const label = tOr(tagId("explain-question", question.id), null, question.label);
    const button = el("button", label, "plain");
    button.type = "button";
    button.dataset.question = question.id;
    button.addEventListener("click", async () => {
      const all = buttons.querySelectorAll("button");
      all.forEach((each) => { each.disabled = true; });
      output.className = "explain-text";
      output.textContent = t("explain-working");
      note.textContent = "";
      // abort(reason) makes fetch reject with that reason.
      const controller = new AbortController();
      const seconds = Math.round(explainTimeoutMs / 1000);
      const timer = setTimeout(() => controller.abort("timeout"), explainTimeoutMs);
      try {
        // The AI answers in the language of the page.
        const data = await api(target.path, {
          ...target.body, question: question.id, user_context: context.value.trim(),
          locale: uiLocale,
        }, controller.signal);
        // A newer card or text has the panel now.
        if (!output.isConnected) return;
        // Only as text: the answer of a model is never HTML.
        output.textContent = data.text;
        output.lang = uiLocale;
        note.textContent = t("explain-written-by", { model: data.model });
      } catch (error) {
        output.className = "explain-text error";
        output.textContent = error === "timeout"
          ? t("explain-timeout", { seconds }) : error.message;
      } finally {
        clearTimeout(timer);
        all.forEach((each) => { each.disabled = false; });
      }
    });
    buttons.append(button);
  }
  panel.append(buttons, context, output, note);
}

async function loadExplain() {
  try {
    explainQuestions = await api("/explain/questions");
  } catch {
    // No list: the page works with no such buttons.
    return;
  }
  Object.keys(explainTargets).forEach(drawExplain);
}

// The panel has text, so it waits for the catalog.
localeLoaded.then(loadExplain);
