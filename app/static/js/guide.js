(() => {
    "use strict";

    const video = document.getElementById("platform-guide-video");
    const links = Array.from(document.querySelectorAll("[data-guide-chapter]"));
    if (!video || !links.length) return;

    const status = document.getElementById("guide-playback-status");
    const error = document.getElementById("guide-video-error");
    const chapters = links.map((link) => ({ link, start: Number(link.dataset.guideStart) }));
    let pendingStart = null;
    let failed = false;

    function updateChapter() {
        let current = chapters[0];
        for (const chapter of chapters) {
            if (video.currentTime >= chapter.start) current = chapter;
        }
        for (const chapter of chapters) {
            const active = chapter === current;
            chapter.link.classList.toggle("is-active", active);
            if (active) chapter.link.setAttribute("aria-current", "true");
            else chapter.link.removeAttribute("aria-current");
        }
    }

    function seekToChapter() {
        if (pendingStart === null || video.readyState < 1) return;
        const end = Number.isFinite(video.duration) ? Math.max(0, video.duration - 0.1) : pendingStart;
        video.currentTime = Math.min(pendingStart, end);
        pendingStart = null;
        updateChapter();
    }

    function showError() {
        failed = true;
        if (error) error.hidden = false;
        if (status) status.textContent = "The video is unavailable. Chapter links now open the written steps.";
    }

    for (const chapter of chapters) {
        chapter.link.addEventListener("click", (event) => {
            if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
            if (failed || !Number.isFinite(chapter.start)) return;
            event.preventDefault();
            pendingStart = Math.max(0, chapter.start);
            seekToChapter();
            if (status) status.textContent = "Playing the selected chapter.";
            const playback = video.play();
            if (playback && typeof playback.catch === "function") {
                playback.catch(() => {
                    if (!failed && status) status.textContent = "Chapter selected. Press play in the video controls to continue.";
                });
            }
            video.focus({ preventScroll: true });
            const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
            video.scrollIntoView({ behavior: reducedMotion ? "auto" : "smooth", block: "center" });
        });
    }

    video.addEventListener("loadedmetadata", seekToChapter);
    video.addEventListener("timeupdate", updateChapter);
    video.addEventListener("seeked", updateChapter);
    video.addEventListener("error", showError);
    const source = video.querySelector("source");
    if (source) source.addEventListener("error", showError);
    // A cached load failure can happen before this deferred script runs.
    if (video.error || video.networkState === 3) showError();
    updateChapter();
})();
