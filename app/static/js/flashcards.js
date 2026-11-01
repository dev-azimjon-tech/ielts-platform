(() => {
    "use strict";

    const data = document.getElementById("flashcard-data");
    if (!data) return;
    const words = JSON.parse(data.textContent);
    if (!words.length) return;

    const card = document.getElementById("study-card");
    const term = document.getElementById("study-term");
    const meaning = document.getElementById("study-meaning");
    const example = document.getElementById("study-example");
    const progress = document.getElementById("study-progress");
    const progressBar = document.getElementById("study-progress-bar");
    const previous = document.getElementById("previous-card");
    const next = document.getElementById("next-card");
    const shuffle = document.getElementById("shuffle-cards");
    let index = 0;

    function showCard(focus = false) {
        const word = words[index];
        card.open = false;
        term.textContent = word.term;
        meaning.textContent = word.meaning;
        example.textContent = word.example;
        example.hidden = !word.example;
        progress.textContent = `Card ${index + 1} of ${words.length}`;
        progressBar.value = index + 1;
        previous.disabled = index === 0;
        next.textContent = index === words.length - 1 ? "Start again" : "Next card →";
        if (focus) card.querySelector("summary").focus();
    }

    previous.addEventListener("click", () => {
        if (index > 0) index -= 1;
        showCard(true);
    });
    next.addEventListener("click", () => {
        index = (index + 1) % words.length;
        showCard(true);
    });
    shuffle.addEventListener("click", () => {
        for (let position = words.length - 1; position > 0; position -= 1) {
            const other = Math.floor(Math.random() * (position + 1));
            [words[position], words[other]] = [words[other], words[position]];
        }
        index = 0;
        showCard(true);
    });
    shuffle.hidden = words.length < 2;
    document.getElementById("study-controls").hidden = false;
    showCard();
})();
