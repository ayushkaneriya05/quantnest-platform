// Runs before styles paint. Keep the key and choices aligned with shared/context/theme.js.
(function () {
  var preference = "system";
  try {
    var saved = localStorage.getItem("quantnest.theme");
    if (["light", "dark", "system"].indexOf(saved) !== -1) preference = saved;
  } catch (_) { /* Storage can be unavailable in private or restricted contexts. */ }
  var dark = preference === "dark" || (preference === "system" && window.matchMedia("(prefers-color-scheme: dark)").matches);
  var root = document.documentElement;
  root.classList.toggle("dark", dark);
  root.dataset.theme = dark ? "dark" : "light";
  root.dataset.themePreference = preference;
  root.style.colorScheme = dark ? "dark" : "light";
})();
