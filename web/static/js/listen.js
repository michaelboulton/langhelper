// The "Listen" buttons: the voice service of the server (tlhelper/speech)
// reads the text that the user entered, or its translation, and the page
// plays the mp3. /api/v1/speech says if there is such a service and which
// languages it reads. The text goes to that service, so a request goes out
// only on a click.
// Uses $, el, serverError, languageName (breakdown.js), api (flashcards.js)
// and t, localeLoaded (i18n.js).

// The server stops the voice service after TLHELPER_VOICE_TIMEOUT seconds
// (180 by default, speech/base.py): a CPU needs a while for a long text.
let listenTimeoutMs = 190_000;
// Null until the answer is there. With no service, no panel shows.
let listenInfo = null;
// For each panel (the id of its element): the texts that it can read.
const listenTargets = {};

// targets: a list of { text, language, info } or null for nothing to read.
//   text, language  what goes to the server
//   info            the language entry, for the name on the button
function setListen(id, targets) {
  const key = JSON.stringify(targets && targets.map((each) => [each.text, each.language]));
  // The same targets again (an automatic send): keep the sound on the page.
  if (listenTargets[id] && listenTargets[id].key === key) return;
  listenTargets[id] = { key, targets };
  drawListen(id);
}

function drawListen(id) {
  const panel = $(id);
  const { targets } = listenTargets[id] || {};
  panel.replaceChildren();
  const readable = (targets || []).filter((each) =>
    each.text && listenInfo && listenInfo.languages.includes(each.language));
  panel.hidden = !listenInfo || !listenInfo.available || readable.length === 0;
  if (panel.hidden) return;

  const buttons = el("div", undefined, "row");
  buttons.append(el("span", t("listen-label"), "sub"));
  const audio = el("audio");
  audio.controls = true;
  audio.hidden = true;
  const note = el("p", undefined, "sub");
  for (const target of readable) {
    const button = el("button", languageName(target.info), "plain");
    button.type = "button";
    button.dataset.language = target.language;
    button.addEventListener("click", async () => {
      const all = buttons.querySelectorAll("button");
      all.forEach((each) => { each.disabled = true; });
      note.className = "sub";
      note.textContent = t("listen-working");
      // abort(reason) makes fetch reject with that reason.
      const controller = new AbortController();
      const seconds = Math.round(listenTimeoutMs / 1000);
      const timer = setTimeout(() => controller.abort("timeout"), listenTimeoutMs);
      try {
        // Not api(): the answer is the sound, and not JSON. A GET, so the
        // browser answers a repeat from its cache (README.md, "Listen").
        const query = new URLSearchParams({ text: target.text, language: target.language });
        const response = await fetch(`/api/v1/speech/audio?${query}`, {
          signal: controller.signal,
        });
        if (!response.ok) throw await serverError(response);
        const blob = await response.blob();
        // A newer text has the panel now.
        if (!audio.isConnected) return;
        if (audio.src) URL.revokeObjectURL(audio.src);
        audio.src = URL.createObjectURL(blob);
        audio.hidden = false;
        const model = response.headers.get("x-voice-model") || listenInfo.model;
        note.textContent = t("listen-made-by", { model });
        // After a click, so the browser allows it. A browser that refuses
        // still shows the controls.
        await audio.play().catch(() => {});
      } catch (error) {
        note.className = "sub error";
        note.textContent = error === "timeout"
          ? t("listen-timeout", { seconds }) : error.message;
      } finally {
        clearTimeout(timer);
        all.forEach((each) => { each.disabled = false; });
      }
    });
    buttons.append(button);
  }
  panel.append(buttons, audio, note);
}

async function loadListen() {
  try {
    listenInfo = await api("/speech");
  } catch {
    // No answer: the page works with no such buttons.
    return;
  }
  Object.keys(listenTargets).forEach(drawListen);
}

// The panel has text, so it waits for the catalog.
localeLoaded.then(loadListen);
