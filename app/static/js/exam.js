(() => {
    'use strict';

    const completed = document.querySelector('[data-completed-draft-key]');
    if (completed) {
        try { localStorage.removeItem(completed.dataset.completedDraftKey); } catch (_) { /* Storage is optional. */ }
    }
    const root = document.getElementById('exam-root');
    if (!root) return;

    const form = document.getElementById('mock-form');
    const steps = [...root.querySelectorAll('.exam-step')];
    const questions = [...form.querySelectorAll('[data-question-number]')];
    const tabs = [...root.querySelectorAll('.exam-step-tab')];
    const jumps = [...root.querySelectorAll('[data-go-question]')];
    const previous = document.getElementById('previous-step');
    const next = document.getElementById('next-step');
    const submit = document.getElementById('submit-mock');
    const notesPanel = document.getElementById('exam-notes');
    const notesInput = document.getElementById('section-notes');
    const notesToggle = document.getElementById('toggle-notes');
    const studyStatus = document.getElementById('study-status');
    const draftStatus = document.getElementById('draft-status');
    const audioScripts = JSON.parse(document.getElementById('listening-scripts').textContent);
    const regions = new Map([...root.querySelectorAll('[data-highlight-id]')].map(element => [
        element.dataset.highlightId, { element, text: element.textContent },
    ]));
    const draft = { answers: {}, notes: {}, highlights: {}, activeStep: 0, notesOpen: false };
    let activeStep = 0;
    let selectedText = null;
    let allowExit = false;
    let submitting = false;
    let saveTimer;
    let audioTimer;
    let activeAudio = null;
    let utterance = null;

    // Store text and offsets only. Never restore saved HTML into the page.
    function saveDraft() {
        clearTimeout(saveTimer);
        // Read the current form as well as input events: browser restoration and
        // assistive input can update fields without dispatching an input event.
        draft.answers = {};
        form.querySelectorAll('input[name^="question_"]').forEach(input => {
            if (input.type !== 'radio' || input.checked) draft.answers[input.name] = input.value;
        });
        draft.activeStep = activeStep;
        draft.notes[activeStep] = notesInput.value;
        draft.notesOpen = !notesPanel.hidden;
        try {
            localStorage.setItem(root.dataset.draftKey, JSON.stringify(draft));
            draftStatus.textContent = 'Saved on this device';
            return true;
        } catch (_) {
            draftStatus.textContent = 'Saving unavailable — keep this tab open';
            return false;
        }
    }

    function scheduleSave() {
        draftStatus.textContent = 'Saving…';
        clearTimeout(saveTimer);
        saveTimer = setTimeout(saveDraft, 350);
    }

    function mergedRanges(ranges, length) {
        const sorted = (Array.isArray(ranges) ? ranges : []).filter(range =>
            Number.isInteger(range.start) && Number.isInteger(range.end) &&
            range.start >= 0 && range.end <= length && range.start < range.end
        ).sort((a, b) => a.start - b.start);
        const result = [];
        for (const range of sorted) {
            const previousRange = result[result.length - 1];
            if (previousRange && range.start <= previousRange.end) {
                previousRange.end = Math.max(previousRange.end, range.end);
            } else result.push({ start: range.start, end: range.end });
        }
        return result;
    }

    function renderHighlights(id) {
        const region = regions.get(id);
        if (!region) return;
        const ranges = mergedRanges(draft.highlights[id], region.text.length);
        draft.highlights[id] = ranges;
        const fragment = document.createDocumentFragment();
        let offset = 0;
        for (const range of ranges) {
            fragment.append(document.createTextNode(region.text.slice(offset, range.start)));
            const mark = document.createElement('mark');
            mark.className = 'study-highlight';
            mark.textContent = region.text.slice(range.start, range.end);
            fragment.append(mark);
            offset = range.end;
        }
        fragment.append(document.createTextNode(region.text.slice(offset)));
        region.element.replaceChildren(fragment);
    }

    function updateProgress() {
        let answered = 0;
        const counts = steps.map(() => 0);
        const answeredNumbers = new Set();
        for (const question of questions) {
            const inputs = [...question.querySelectorAll('input')];
            const input = inputs.find(field => field.type === 'radio' ? field.checked : field.value.trim());
            if (input) {
                answered++;
                counts[Number(question.dataset.step)]++;
                answeredNumbers.add(question.dataset.questionNumber);
            }
        }
        document.getElementById('answered-progress').textContent = `${answered} / ${questions.length} answered`;
        steps.forEach((step, index) => {
            const label = step.querySelector('.step-answer-count');
            label.textContent = `${counts[index]} / ${label.dataset.total} answered`;
        });
        jumps.forEach(button => {
            const isAnswered = answeredNumbers.has(button.dataset.goQuestion);
            button.classList.toggle('is-answered', isAnswered);
            button.setAttribute('aria-label', `Question ${button.dataset.goQuestion}, ${isAnswered ? 'answered' : 'unanswered'}`);
        });
        return answered;
    }

    function stopPlayback() {
        clearInterval(audioTimer);
        if (activeAudio) {
            activeAudio.disabled = false;
            activeAudio.textContent = activeAudio.dataset.played ? 'Play again ▶' : 'Start audio ▶';
            activeAudio.closest('.audio-panel').querySelector('.audio-status').textContent = 'Audio stopped. Press Start audio or Play again when ready.';
        }
        activeAudio = null;
        if (utterance && 'speechSynthesis' in window) window.speechSynthesis.cancel();
        utterance = null;
    }

    function showStep(index, focus = true) {
        if (!steps.length || !Number.isInteger(index) || index < 0 || index >= steps.length) return;
        draft.notes[activeStep] = notesInput.value;
        stopPlayback();
        selectedText = null;
        activeStep = index;
        steps.forEach((step, i) => {
            step.classList.toggle('is-active', i === index);
            step.setAttribute('aria-hidden', String(i !== index));
        });
        tabs.forEach((tab, i) => {
            tab.classList.toggle('is-active', i === index);
            tab.setAttribute('aria-current', i === index ? 'step' : 'false');
        });
        notesInput.value = typeof draft.notes[index] === 'string' ? draft.notes[index] : '';
        document.getElementById('notes-label').textContent = `Notes for ${root.dataset.skill === 'reading' ? 'passage' : 'section'} ${index + 1}`;
        previous.disabled = index === 0;
        next.hidden = index === steps.length - 1;
        submit.hidden = !next.hidden;
        document.getElementById('step-progress').textContent = `${root.dataset.skill === 'reading' ? 'Passage' : 'Section'} ${index + 1} of ${steps.length}`;
        if (focus) steps[index].querySelector('h2').focus({ preventScroll: true });
        scheduleSave();
    }

    function toggleNotes(open) {
        notesPanel.hidden = !open;
        root.classList.toggle('notes-open', open);
        notesToggle.setAttribute('aria-expanded', String(open));
        if (open) notesInput.focus({ preventScroll: window.innerWidth > 1100 });
        else notesToggle.focus({ preventScroll: true });
        scheduleSave();
    }

    function captureSelection() {
        const selection = window.getSelection();
        if (!selection || selection.isCollapsed || !selection.rangeCount) { selectedText = null; return; }
        const range = selection.getRangeAt(0);
        const parent = range.startContainer.nodeType === Node.ELEMENT_NODE ? range.startContainer : range.startContainer.parentElement;
        const region = parent.closest('[data-highlight-id]');
        if (!region || !steps[activeStep].contains(region) || !region.contains(range.endContainer)) {
            selectedText = null;
            return;
        }
        const prefix = document.createRange();
        prefix.selectNodeContents(region);
        prefix.setEnd(range.startContainer, range.startOffset);
        const start = prefix.toString().length;
        selectedText = { id: region.dataset.highlightId, start, end: start + range.toString().length, text: range.toString() };
    }

    function highlightSelection() {
        captureSelection();
        if (!selectedText) {
            studyStatus.textContent = 'Select text inside a passage, question, or answer option first.';
            return;
        }
        const id = selectedText.id;
        draft.highlights[id] = [...(draft.highlights[id] || []), { start: selectedText.start, end: selectedText.end }];
        renderHighlights(id);
        window.getSelection().removeAllRanges();
        selectedText = null;
        studyStatus.textContent = 'Text highlighted. Open Notes to clear this section’s highlights.';
        scheduleSave();
    }

    function startAudio(button) {
        if (!('speechSynthesis' in window)) {
            button.closest('.audio-panel').querySelector('.audio-status').textContent = 'Audio is unavailable in this browser. Please try a browser with speech playback.';
            return;
        }
        if (activeAudio === button) { stopPlayback(); return; }
        stopPlayback();
        activeAudio = button;
        const status = button.closest('.audio-panel').querySelector('.audio-status');
        function play() {
            clearInterval(audioTimer);
            button.disabled = false;
            button.textContent = 'Stop audio ■';
            button.dataset.played = 'true';
            status.textContent = 'Audio is playing. Answer the questions as you listen.';
            utterance = new SpeechSynthesisUtterance(audioScripts[Number(button.dataset.stepIndex)]);
            utterance.lang = 'en-GB';
            utterance.rate = 0.88;
            const voice = window.speechSynthesis.getVoices().find(item => item.lang === 'en-GB');
            if (voice) utterance.voice = voice;
            const thisUtterance = utterance;
            utterance.onend = () => {
                if (utterance !== thisUtterance) return;
                stopPlayback();
                status.textContent = 'Audio finished. Review your answers, then continue.';
            };
            utterance.onerror = () => {
                if (utterance !== thisUtterance) return;
                stopPlayback();
                status.textContent = 'Playback was interrupted. Press Play again to retry.';
            };
            window.speechSynthesis.speak(utterance);
        }
        if (button.dataset.played) { play(); return; }
        const startAt = Date.now() + 20000;
        button.disabled = true;
        button.textContent = 'Read questions: 20s';
        status.textContent = 'You have 20 seconds to read. Audio will start automatically.';
        audioTimer = setInterval(() => {
            const remaining = Math.max(0, Math.ceil((startAt - Date.now()) / 1000));
            button.textContent = `Read questions: ${remaining}s`;
            if (!remaining) play();
        }, 250);
    }

    try {
        const saved = JSON.parse(localStorage.getItem(root.dataset.draftKey));
        if (saved && typeof saved === 'object') {
            for (const name of ['answers', 'notes', 'highlights']) {
                if (saved[name] && typeof saved[name] === 'object' && !Array.isArray(saved[name])) draft[name] = saved[name];
            }
            draft.activeStep = Number.isInteger(saved.activeStep) ? saved.activeStep : 0;
            draft.notesOpen = saved.notesOpen === true;
        }
    } catch (_) { /* An unavailable or stale draft must never block a test. */ }
    form.querySelectorAll('input[name^="question_"]').forEach(input => {
        const value = document.getElementById('exam-config') ? undefined : draft.answers[input.name];
        if (typeof value !== 'string') return;
        if (input.type === 'radio') input.checked = input.value === value;
        else input.value = value.slice(0, 500);
    });
    for (const id of regions.keys()) renderHighlights(id);
    notesInput.value = typeof draft.notes[0] === 'string' ? draft.notes[0] : '';
    notesPanel.hidden = !draft.notesOpen;
    root.classList.toggle('notes-open', draft.notesOpen);
    notesToggle.setAttribute('aria-expanded', String(draft.notesOpen));
    showStep(Math.min(Math.max(draft.activeStep, 0), steps.length - 1), false);
    updateProgress();

    form.addEventListener('input', event => {
        const input = event.target;
        if (input.matches('input[name^="question_"]')) {
            draft.answers[input.name] = input.value;
            updateProgress();
            scheduleSave();
        }
    });
    notesInput.addEventListener('input', scheduleSave);
    tabs.forEach(tab => tab.addEventListener('click', () => showStep(Number(tab.dataset.goStep))));
    previous.addEventListener('click', () => showStep(activeStep - 1));
    next.addEventListener('click', () => showStep(activeStep + 1));
    jumps.forEach(button => button.addEventListener('click', () => {
        const question = document.getElementById(`question-${button.dataset.goQuestion}`);
        showStep(Number(question.dataset.step));
        question.scrollIntoView({ block: 'center', behavior: 'auto' });
        question.focus({ preventScroll: true });
    }));
    notesToggle.addEventListener('click', () => toggleNotes(notesPanel.hidden));
    document.getElementById('close-notes').addEventListener('click', () => toggleNotes(false));
    document.addEventListener('selectionchange', captureSelection);
    for (const id of ['highlight-selection', 'quote-selection']) {
        document.getElementById(id).addEventListener('mousedown', event => event.preventDefault());
    }
    document.getElementById('highlight-selection').addEventListener('click', highlightSelection);
    document.addEventListener('keydown', event => {
        if (event.altKey && event.key.toLowerCase() === 'h') { event.preventDefault(); highlightSelection(); }
    });
    document.getElementById('quote-selection').addEventListener('click', () => {
        captureSelection();
        if (!selectedText) { studyStatus.textContent = 'Select some text to add it to your notes.'; return; }
        notesInput.value = `${notesInput.value}${notesInput.value ? '\n\n' : ''}${selectedText.text}`.slice(0, 20000);
        toggleNotes(true);
        studyStatus.textContent = 'Selection added to your notes.';
    });
    document.getElementById('clear-highlights').addEventListener('click', () => {
        if (!window.confirm('Clear all highlights in this section? Your notes and answers will stay.')) return;
        steps[activeStep].querySelectorAll('[data-highlight-id]').forEach(element => {
            const id = element.dataset.highlightId;
            delete draft.highlights[id];
            renderHighlights(id);
        });
        selectedText = null;
        studyStatus.textContent = 'Highlights cleared for this section.';
        scheduleSave();
    });
    root.querySelectorAll('.start-audio').forEach(button => button.addEventListener('click', () => startAudio(button)));
    document.getElementById('exit-mock').addEventListener('click', event => {
        const saved = saveDraft();
        const message = saved
            ? 'You have not submitted this mock yet. Do you really want to exit? Your saved work will remain on this device.'
            : 'Saving is unavailable. Leaving will discard your current answers, notes, and highlights. Do you really want to exit?';
        if (!window.confirm(message)) {
            event.preventDefault();
            return;
        }
        allowExit = true;
        stopPlayback();
    });
    form.addEventListener('submit', event => {
        if (event.defaultPrevented) return;
        if (submitting) { event.preventDefault(); return; }
        const remaining = questions.length - updateProgress();
        if (!form.dataset.timedSubmit && !window.confirm(remaining ? `You have ${remaining} unanswered question${remaining === 1 ? '' : 's'}. Submit this mock for scoring?` : 'Submit this mock for scoring?')) {
            event.preventDefault();
            return;
        }
        saveDraft();
        allowExit = true;
        submitting = true;
        submit.disabled = true;
        submit.textContent = 'Submitting…';
        stopPlayback();
    });
    window.addEventListener('beforeunload', event => {
        saveDraft();
        if (allowExit) return;
        event.preventDefault();
        event.returnValue = '';
    });
    window.addEventListener('pagehide', () => { saveDraft(); stopPlayback(); });
    window.addEventListener('pageshow', event => {
        if (event.persisted) { allowExit = false; submitting = false; submit.disabled = false; submit.textContent = 'Submit mock →'; }
    });
})();
