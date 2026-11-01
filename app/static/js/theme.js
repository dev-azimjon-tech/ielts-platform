(() => {
    "use strict";

    const storageKey = "ielts:theme";
    const root = document.documentElement;
    const systemTheme = window.matchMedia("(prefers-color-scheme: dark)");
    const validTheme = (value) => value === "light" || value === "dark";
    let preference = null;
    let storage = null;

    try {
        storage = window.localStorage;
        const saved = storage.getItem(storageKey);
        if (validTheme(saved)) preference = saved;
    } catch {
        // The toggle still works when browser storage is unavailable.
    }

    function applyTheme() {
        const theme = preference || (systemTheme.matches ? "dark" : "light");
        root.dataset.theme = theme;
        document.querySelectorAll("[data-theme-toggle]").forEach((button) => {
            const nextMode = theme === "dark" ? "light" : "dark";
            const label = `Switch to ${nextMode} mode`;
            button.setAttribute("aria-label", label);
            button.setAttribute("title", label);
            button.querySelector("[data-theme-label]").textContent = `${nextMode === "dark" ? "Dark" : "Light"} mode`;
        });
    }

    // Run before styles load so a saved dark theme never flashes light.
    applyTheme();

    document.addEventListener("DOMContentLoaded", () => {
        applyTheme();
        document.querySelectorAll("[data-theme-toggle]").forEach((button) => {
            button.hidden = false;
            button.addEventListener("click", () => {
                preference = root.dataset.theme === "dark" ? "light" : "dark";
                applyTheme();
                try {
                    if (storage) storage.setItem(storageKey, preference);
                } catch {
                    // Keep the selected theme for this page without storage.
                }
            });
        });
    });

    systemTheme.addEventListener("change", () => {
        if (!preference) applyTheme();
    });

    window.addEventListener("storage", (event) => {
        if (event.key !== storageKey && event.key !== null) return;
        if (!storage || event.storageArea !== storage) return;
        preference = validTheme(event.newValue) ? event.newValue : null;
        applyTheme();
    });
})();
