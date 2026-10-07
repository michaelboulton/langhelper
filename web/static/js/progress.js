// The progress tab: the numbers and the graphs of a user. Uses breakdown.js
// ($, el) and flashcards.js (api, countsText). showTab of flashcards.js calls
// loadProgress each time the tab opens.

// The answer of /flashcards/users. null before the first load.
let progressUsers = null;

function progressStatus(text, isError) {
  $("progress-status").className = isError ? "error" : "";
  $("progress-status").textContent = text;
}

async function loadProgress() {
  const select = $("progress-user");
  try {
    if (!progressUsers) {
      const data = await api("/flashcards/users");
      progressUsers = data.users;
      select.replaceChildren(...progressUsers.map((each) => {
        // The entry of the user has an English name from the server.
        const option = el("option", each.id === data.me ? t("progress-own-cards") : each.name);
        option.value = each.id;
        return option;
      }));
    }
    const wanted = select.value;
    const stats = await api("/flashcards/stats?of=" + encodeURIComponent(wanted));
    // The user changed the choice during the request: a later call draws it.
    if (wanted !== select.value) return;
    drawProgress(stats);
    progressStatus(stats.reviews ? "" : t("progress-no-answers"));
  } catch (error) {
    $("stats").hidden = true;
    progressStatus(error.message, true);
  }
}

function drawProgress(stats) {
  $("stats").hidden = !stats.reviews;
  if (!stats.reviews) return;
  // A share from 0 to 1, as the locale writes a percentage: "100 %", "100%".
  const percent = (share) => new Intl.NumberFormat(uiLocale, {
    style: "percent", maximumFractionDigits: 0,
  }).format(share);
  const rows = [
    [t("progress-answers"), String(stats.reviews)],
    [t("progress-passed"), percent(stats.success_rate)],
    [t("progress-lapses"), String(stats.lapses)],
    [t("progress-streak"), String(stats.streak_days)],
    [t("progress-cards"), t("progress-cards-value", {
      total: stats.counts.total, counts: countsText(stats.counts),
    })],
  ];
  $("stats-table").replaceChildren(...rows.map(([name, value]) => {
    const tr = el("tr");
    tr.append(el("th", name), el("td", value));
    return tr;
  }));
  const most = Math.max(1, ...stats.days.map((day) => day.reviews));
  $("stats-days").replaceChildren(...stats.days.map((day) => {
    const bar = el("div", undefined, "day");
    bar.title = t("progress-day-answers", {
      date: day.date, answers: day.reviews, passed: day.passed,
    });
    bar.style.height = (day.reviews / most) * 100 + "%";
    const passed = el("div");
    passed.style.height = (day.reviews ? (day.passed / day.reviews) * 100 : 0) + "%";
    bar.append(passed);
    return bar;
  }));
  $("stats-rate").replaceChildren(...stats.days.map((day) => {
    const bar = el("div", undefined, "day");
    const rate = day.reviews ? Math.round((day.passed / day.reviews) * 100) : 0;
    bar.title = day.reviews
      ? t("progress-day-rate", { date: day.date, rate: percent(day.passed / day.reviews) })
      : t("progress-day-none", { date: day.date });
    bar.style.height = rate + "%";
    return bar;
  }));
}

$("progress-user").addEventListener("change", loadProgress);
