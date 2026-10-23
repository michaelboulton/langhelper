// The audio lessons tab: the courses, the player of a lesson, and its script.
// Uses breakdown.js ($, el, inLanguage, languages, englishInfo) and
// flashcards.js (api). showTab of flashcards.js calls loadAudioCourses each
// time the tab opens.

// The answer of /audio-lessons. null before the first load.
let audioCourses = null;

function audioStatus(text, isError) {
  $("audio-status").className = isError ? "error" : "";
  $("audio-status").textContent = text;
}

async function loadAudioCourses() {
  if (audioCourses) return;
  try {
    audioCourses = (await api("/audio-lessons")).courses;
  } catch (error) {
    audioStatus(error.message, true);
    return;
  }
  audioStatus(audioCourses.length ? "" : t("audio-no-courses"));
  $("audio-courses").replaceChildren(...audioCourses.map((course) => {
    const box = el("div");
    box.append(el("h2", course.name));
    const list = el("ol");
    for (const lesson of course.lessons) {
      const button = el("button", lesson.title, "plain");
      button.type = "button";
      button.addEventListener("click", () => openLesson(course, lesson));
      const item = el("li");
      item.value = lesson.number;
      item.append(button);
      list.append(item);
    }
    box.append(list);
    return box;
  }));
}

async function openLesson(course, lesson) {
  const path = "/audio-lessons/" + encodeURIComponent(course.id) + "/" + lesson.number;
  let lessonScript;
  try {
    lessonScript = await api(path);
  } catch (error) {
    audioStatus(error.message, true);
    return;
  }
  audioStatus("");
  $("audio-lesson-title").textContent = lessonScript.title;
  $("audio-lesson-grammar").textContent = lessonScript.grammar;
  const player = $("audio-player");
  player.hidden = lesson.audio === "none";
  if (player.hidden) player.removeAttribute("src");
  else player.src = "/api/v1" + path + ".mp3";
  $("audio-note").hidden = lesson.audio === "ready";
  if (lesson.audio !== "ready") $("audio-note").textContent = t("audio-state-" + lesson.audio);
  const study = languages[course.language] || { code: course.language };
  $("audio-script").replaceChildren(...lessonScript.lines.map((line) => {
    if (line.speaker === "pause") {
      return el("p", t("audio-pause", { seconds: line.seconds }), "pause");
    }
    const row = el("p");
    const text = inLanguage(el("span", line.text), line.speaker === "narrator" ? englishInfo : study);
    row.append(el("strong", t("audio-speaker-" + line.speaker.replace(" ", "-")) + " "), text);
    return row;
  }));
  $("audio-courses").hidden = true;
  $("audio-lesson").hidden = false;
}

$("audio-back").addEventListener("click", () => {
  $("audio-player").pause();
  $("audio-lesson").hidden = true;
  $("audio-courses").hidden = false;
});
