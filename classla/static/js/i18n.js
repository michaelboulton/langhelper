// The text of the page in the language of the user. The messages are Fluent
// files (projectfluent.org) from /api/v1/locales/{code}/ui.ftl: they are in
// the folders of the languages on the server (tlhelper/languages/*/ui.ftl).
// The first script of the page: the other ones use t, tOr, tagId,
// languageName, formatList, uiLocale and localeLoaded.
//
// index.html loads the Fluent runtime from a CDN, as the global FluentBundle.
// If that script did not load, the page shows the English catalog with the
// small formatter at the end of this file, and has no other language.

const LOCALE_KEY = "classla.locale";
// The locale of the page, and the catalogs to look in: the selected one,
// then the default one (English) for a message that the first does not have.
let uiLocale = "en";
let catalogs = [];
const missingIds = new Set();

// A catalog is { has(id), format(id, args) }.
function fluentCatalog(code, source) {
  // No isolation marks around a parameter: a text in another language is in
  // a <bdi> element on this page, and the marks end up in copied text.
  const bundle = new FluentBundle.FluentBundle(code, { useIsolating: false });
  for (const error of bundle.addResource(new FluentBundle.FluentResource(source))) {
    console.warn("i18n: " + code + ": " + error.message);
  }
  return {
    has: (id) => Boolean(bundle.hasMessage(id) && bundle.getMessage(id).value),
    format: (id, args) => {
      const errors = [];
      const text = bundle.formatPattern(bundle.getMessage(id).value, args || {}, errors);
      for (const error of errors) console.warn("i18n: " + id + ": " + error.message);
      return text;
    },
  };
}

// fallback: the text for an id with no message. Without it, the id shows,
// and the console names the id one time.
function tOr(id, args, fallback) {
  for (const catalog of catalogs) {
    if (catalog.has(id)) return catalog.format(id, args);
  }
  if (fallback !== undefined) return fallback;
  if (!missingIds.has(id)) {
    missingIds.add(id);
    console.warn("i18n: no message " + id);
  }
  return id;
}
function t(id, args) { return tOr(id, args); }

// The id of the message for a tag of a tagger: "feat-Number-psor" for
// ("feat", "Number[psor]"). A Fluent id has only letters, digits, "_", "-".
function tagId(prefix, tag) {
  return prefix + "-" + tag.replace(/[^A-Za-z0-9_-]+/g, "-").replace(/-$/, "");
}

// info: a language of /api/v1/languages.
function languageName(info) { return tOr("language-name-" + info.code, null, info.name); }

// "the accusative or the dative", in the grammar of the locale.
function formatList(items, type) {
  try {
    return new Intl.ListFormat(uiLocale, { type: type || "conjunction" }).format(items);
  } catch {
    return items.join(", ");
  }
}

// The messages of the markup: data-l10n-id is the text of an element, and
// data-l10n-placeholder and data-l10n-title are those attributes.
// data-l10n-args has the parameters, as JSON.
function translatePage(root) {
  const args = (node) => (node.dataset.l10nArgs ? JSON.parse(node.dataset.l10nArgs) : null);
  for (const node of root.querySelectorAll("[data-l10n-id]")) {
    node.textContent = t(node.dataset.l10nId, args(node));
  }
  for (const name of ["placeholder", "title"]) {
    const key = "l10n" + name[0].toUpperCase() + name.slice(1);
    for (const node of root.querySelectorAll("[data-l10n-" + name + "]")) {
      node.setAttribute(name, t(node.dataset[key], args(node)));
    }
  }
}
// Change the parameters of one element of the markup.
function setL10nArgs(node, args) {
  node.dataset.l10nArgs = JSON.stringify(args);
  if (node.dataset.l10nId) node.textContent = t(node.dataset.l10nId, args);
}

// The choice of the user is in the address (?locale=hr) or in localStorage.
// Without one, it is the first language of the browser that has a catalog.
function pickLocale(available, fallback) {
  const wanted = [new URLSearchParams(location.search).get("locale")];
  try { wanted.push(localStorage.getItem(LOCALE_KEY)); } catch {}
  wanted.push(...(navigator.languages || [navigator.language]));
  for (const tag of wanted) {
    if (!tag) continue;
    // "de-AT" gets "de".
    const found = [tag, tag.split("-")[0]].find((code) => available.includes(code));
    if (found) return found;
  }
  return fallback;
}

async function fetchCatalog(code) {
  const response = await fetch("/api/v1/locales/" + encodeURIComponent(code) + "/ui.ftl");
  if (!response.ok) throw new Error("no catalog " + code + ": " + response.status);
  return response.text();
}

async function loadLocale() {
  const select = document.getElementById("locale");
  try {
    const response = await fetch("/api/v1/locales");
    if (!response.ok) throw new Error("no list of locales: " + response.status);
    const list = await response.json();
    const hasFluent = typeof FluentBundle !== "undefined";
    if (!hasFluent) console.warn("i18n: the Fluent script did not load. The page is in English.");
    const make = hasFluent ? fluentCatalog : simpleCatalog;
    const codes = list.locales.map((each) => each.code);
    const code = hasFluent ? pickLocale(codes, list.default) : list.default;
    const wanted = code === list.default ? [code] : [code, list.default];
    const sources = await Promise.allSettled(wanted.map(fetchCatalog));
    catalogs = [];
    sources.forEach((source, index) => {
      if (source.status === "fulfilled") catalogs.push(make(wanted[index], source.value));
      else console.warn("i18n: " + source.reason.message);
    });
    uiLocale = code;
    const chosen = list.locales.find((each) => each.code === code);
    document.documentElement.lang = code;
    document.documentElement.dir = chosen ? chosen.direction : "ltr";
    for (const each of list.locales) {
      const option = document.createElement("option");
      option.value = each.code;
      option.textContent = each.name;
      // The name of a language is in that language.
      option.lang = each.code;
      select.append(option);
    }
    select.value = code;
    select.parentElement.hidden = !hasFluent || list.locales.length < 2;
  } catch (error) {
    // The markup has the English text, so the page still works.
    console.warn("i18n: " + error.message);
  }
  if (catalogs.length) translatePage(document);
}

// Each script made its text with the old locale, so the page loads again. The
// breakdown tab keeps its entry in localStorage. The address keeps the choice
// for a browser with no storage.
document.getElementById("locale").addEventListener("change", (event) => {
  const code = event.target.value;
  try { localStorage.setItem(LOCALE_KEY, code); } catch {}
  const address = new URL(location.href);
  address.searchParams.set("locale", code);
  location.replace(address);
});

// A formatter for the English catalog, only for a page with no Fluent script.
// It knows what ui.ftl uses: text, { $name }, { message }, { -term(name: $x) },
// "text", and a selector with its variants. It has no functions and no
// attributes.
function simpleCatalog(code, source) {
  const entries = new Map();
  let last = null;
  for (const line of source.split("\n")) {
    const start = /^(-?[A-Za-z][\w-]*)\s*=\s?(.*)$/.exec(line);
    if (start) {
      last = start[1];
      entries.set(last, start[2]);
    } else if (last && /^(\s+\S|\})/.test(line)) {
      // An indented line, or the "}" that ends a selector.
      entries.set(last, entries.get(last) + "\n" + line.trim());
    } else if (line.trim()) {
      last = null;
    }
  }
  const plural = new Intl.PluralRules(code);

  function format(id, args) {
    const text = entries.get(id);
    let pos = 0;
    const space = () => { while (/\s/.test(text[pos] || "")) pos++; };
    const word = () => {
      const found = /^[\w-]+/.exec(text.slice(pos));
      pos += found ? found[0].length : 0;
      return found ? found[0] : "";
    };
    // A value in braces, or the value of a parameter of a term.
    function value() {
      space();
      if (text[pos] === "\"") {
        const end = text.indexOf("\"", pos + 1);
        const literal = text.slice(pos + 1, end);
        pos = end + 1;
        return literal;
      }
      if (text[pos] === "$") {
        pos++;
        return args[word()];
      }
      const name = word();
      const inner = {};
      space();
      if (text[pos] === "(") {
        pos++;
        for (space(); text[pos] !== ")" && pos < text.length; space()) {
          const key = word();
          space();
          pos++; // ":"
          inner[key] = value();
          space();
          if (text[pos] === ",") pos++;
        }
        pos++;
      }
      return entries.has(name) ? format(name, inner) : name;
    }
    // inVariant: the text of a variant ends before the next "[key]" line.
    function pattern(inVariant) {
      let out = "";
      while (pos < text.length && text[pos] !== "}") {
        if (inVariant && text[pos] === "\n" && /^\s*\*?\[/.test(text.slice(pos + 1))) break;
        if (text[pos] !== "{") {
          out += text[pos++];
          continue;
        }
        pos++;
        const selector = value();
        space();
        if (text.startsWith("->", pos)) {
          pos += 2;
          let chosen = null;
          let otherwise = "";
          for (space(); text[pos] !== "}" && pos < text.length; space()) {
            const isDefault = text[pos] === "*";
            pos += isDefault ? 2 : 1;
            const key = text.slice(pos, text.indexOf("]", pos)).trim();
            pos = text.indexOf("]", pos) + 1;
            const variant = pattern(true).trim();
            if (isDefault) otherwise = variant;
            const matches = key === String(selector)
              || (typeof selector === "number" && key === plural.select(selector));
            if (matches && chosen === null) chosen = variant;
          }
          out += chosen === null ? otherwise : chosen;
        } else {
          out += selector === undefined ? "" : String(selector);
        }
        space();
        pos++; // "}"
      }
      return out;
    }
    return pattern(false);
  }
  return {
    has: (id) => entries.has(id) && !id.startsWith("-"),
    format: (id, args) => format(id, args || {}),
  };
}

const localeLoaded = loadLocale();
