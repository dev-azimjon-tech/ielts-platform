(() => {
    const element = document.getElementById('exam-config');
    if (!element) return;
    const config = JSON.parse(element.textContent);
    const banner = document.querySelector('[data-exam-deadline]');
    const output = banner.querySelector('output');
    const saveStatus = document.getElementById('exam-save-status');
    const timerStatus = document.getElementById('exam-timer-status');
    const form = document.querySelector('#mock-form, #writing-form');
    const deadline = Date.parse(config.deadline);
    // Use elapsed monotonic time from the server timestamp, independent of device clock settings.
    let serverStart = Date.parse(config.serverNow), loadedAt = performance.now();
    let revision = config.revision, pending = null, conflict = Boolean(form && form.dataset.examConflict === 'true'), timer, expired = false;
    window.ieltsExamRevision = revision;
    const versionInput = form && form.querySelector('[name=_exam_revision]');
    window.ieltsSetExamRevision = value => {
        if (!Number.isInteger(value) || value < revision) return;
        revision = value; window.ieltsExamRevision = value;
        if (versionInput) versionInput.value = value;
    };
    let lastSaved = JSON.stringify(config.draft);
    if (form && config.restore) {
        for (const [name, value] of Object.entries(config.draft)) {
            for (const input of form.elements) {
                if (input.name !== name) continue;
                if (input.type === 'radio') input.checked = input.value === value;
                else input.value = value;
            }
        }
    }
    const restoredEssay = form && form.querySelector('[name=essay]');
    if (restoredEssay && config.restore) restoredEssay.dispatchEvent(new Event('input',{bubbles:true}));
    function collect() {
        if (!form) return window.ieltsSpeakingDraft || config.draft;
        const data = {};
        for (const [name,value] of new FormData(form)) {
            if (name === 'essay' || name.startsWith('question_')) data[name] = value;
        }
        return data;
    }
    async function save() {
        if (conflict) return false;
        if (pending) {
            if (!await pending) return false;
            return save();
        }
        const draft = collect(), serialized = JSON.stringify(draft);
        if (serialized === lastSaved) return true;
        saveStatus.textContent = 'Saving answers…';
        pending = (async () => {
            try {
                const response = await fetch(config.draftUrl, {
                    method:'POST', headers:{'Content-Type':'application/json','X-CSRF-Token':config.csrf},
                    body:JSON.stringify({stage:config.stage,revision,draft})
                });
                const payload = await response.json();
                if (!response.ok) {
                    if (response.status === 409) conflict = true;
                    throw new Error(payload.error || 'Answers could not be saved. Keep this page open and try again.');
                }
                window.ieltsSetExamRevision(payload.revision);
                lastSaved = serialized;
                saveStatus.textContent = 'Answers saved to your exam session.';
                return true;
            } catch(error) {
                saveStatus.textContent = error.message || 'Connection interrupted. Saving will retry while this page stays open.';
                return false;
            } finally { pending = null; }
        })();
        return pending;
    }
    window.ieltsSaveExamDraft = save;
    function changed() { clearTimeout(timer); timer = setTimeout(save,700); }
    let sending = false, allowSubmit = false;
    if (form) {
        form.addEventListener('input',changed); form.addEventListener('change',changed);
        form.addEventListener('submit',async event => {
            if (event.defaultPrevented) return;
            if (allowSubmit) {
                allowSubmit = false;
                queueMicrotask(() => { if (event.defaultPrevented) sending = false; });
                return;
            }
            event.preventDefault();
            if (sending) return;
            if (conflict) {
                saveStatus.textContent = 'A newer draft exists. Copy your current text before reloading; this stale form cannot be submitted.';
                return;
            }
            sending = true;
            clearTimeout(timer);
            if (!await save()) { sending = false; return; }
            allowSubmit = true;
            form.requestSubmit(event.submitter || undefined);
        });
    }
    if (conflict) saveStatus.textContent = 'Another tab saved newer answers. Copy your current text before reloading.';
    window.addEventListener('exam:changed',changed);
    window.addEventListener('online',save);
    setInterval(save,5000);
    async function syncClock() {
        try {
            const response = await fetch(config.draftUrl,{cache:'no-store'});
            if (!response.ok) return;
            const payload = await response.json();
            serverStart = Date.parse(payload.serverNow); loadedAt = performance.now();
            if (payload.completed || payload.stage !== config.stage) {
                conflict = true;
                saveStatus.textContent = 'This section has ended in another tab. Open Session details to continue.';
            }
        } catch (_) { /* Autosave status communicates connection errors. */ }
    }
    setInterval(syncClock,30000);
    document.addEventListener('visibilitychange',() => { if (!document.hidden) syncClock(); });
    function tick() {
        const remaining = Math.max(0,Math.ceil((deadline-(serverStart+performance.now()-loadedAt))/1000));
        output.textContent = `${Math.floor(remaining/60)}:${String(remaining%60).padStart(2,'0')}`;
        if (remaining <= 60 && remaining > 0 && !timerStatus.dataset.warned) {
            timerStatus.dataset.warned = 'true'; timerStatus.textContent = 'One minute or less remains in this section.';
        }
        if (remaining || expired) return;
        expired = true;
        window.dispatchEvent(new Event('exam:expired'));
        save();
        if (form && !conflict) {
            const essay = form.querySelector('[name=essay]');
            const short = essay && essay.value.trim().split(/\s+/).filter(Boolean).length < 50;
            timerStatus.textContent = !config.autoSubmit ? 'Section time has ended. Submit your saved response or end this section without a score.' : short ? 'Time ended. This response needs at least 50 words for AI feedback. End this section without a score to continue, or finish it as untimed practice.' : 'Time ended. Submitting your answers…';
            if (!short && config.autoSubmit) { form.dataset.timedSubmit = 'true'; form.requestSubmit(); }
        } else {
            timerStatus.textContent = conflict ? 'This section changed in another tab. Open Session details to continue.' : 'Time ended. Finish the current answer for feedback or end this section without a score.';
        }
    }
    tick(); setInterval(tick,1000);
})();
