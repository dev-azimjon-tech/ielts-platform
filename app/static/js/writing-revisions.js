(() => {
    const form = document.getElementById('revision-form');
    if (!form) return;
    const essay = document.getElementById('revision-essay');
    const versionInput = document.getElementById('revision-draft-version');
    const status = document.getElementById('revision-draft-status');
    const wordCount = document.getElementById('revision-word-count');
    let conflict = form.dataset.conflict === 'true';
    let lastSaved = conflict || form.dataset.saved === 'false' ? null : essay.value;
    let pending = null, timer, submitting = false, allowSubmit = false, leaving = false;

    function countWords() { return essay.value.trim().split(/\s+/).filter(Boolean).length; }
    function updateCount() { wordCount.textContent = `${countWords()} words`; }
    async function saveDraft() {
        if (conflict || essay.value.length > 50000) return false;
        if (pending) {
            const success = await pending;
            if (!success) return false;
            return saveDraft();
        }
        if (essay.value === lastSaved) return true;
        const text = essay.value;
        status.textContent = 'Saving draft…';
        pending = (async () => {
            try {
                const response = await fetch(form.dataset.draftUrl, {
                    method: 'POST', headers: {'Content-Type':'application/json', 'X-CSRF-Token':form.elements.csrf_token.value},
                    body: JSON.stringify({essay:text, version:Number(versionInput.value)})
                });
                const payload = await response.json();
                if (!response.ok) {
                    if (response.status === 409) conflict = true;
                    throw new Error(payload.error || 'Draft could not be saved. Keep this page open and try again.');
                }
                versionInput.value = payload.version;
                lastSaved = text;
                status.textContent = 'Draft saved. No AI check used.';
                return true;
            } catch (error) {
                status.textContent = error.message || 'Connection interrupted. Keep this page open; saving will retry.';
                return false;
            } finally { pending = null; }
        })();
        return pending;
    }
    essay.addEventListener('input', () => {
        updateCount();
        if (conflict) return;
        status.textContent = 'Unsaved changes…';
        clearTimeout(timer); timer = setTimeout(saveDraft,700);
    });
    window.addEventListener('online', () => { if (!submitting) saveDraft(); });
    setInterval(() => { if (!submitting) saveDraft(); },5000);
    form.addEventListener('submit', async event => {
        if (allowSubmit) { allowSubmit = false; return; }
        event.preventDefault();
        if (submitting || conflict) return;
        const button = event.submitter;
        const action = button && button.value || 'check';
        if (action === 'check' && countWords() < 50) {
            await saveDraft();
            status.textContent = 'Write at least 50 words before checking. You can save a shorter draft.';
            essay.focus(); return;
        }
        submitting = true; clearTimeout(timer);
        const saved = await saveDraft();
        // Explicit submission also saves on the server; a network failure keeps the text in the editor.
        if (!saved) { submitting = false; return; }
        leaving = true; allowSubmit = true; form.setAttribute('aria-busy','true');
        status.textContent = action === 'save' ? 'Saving draft…' : 'Checking your revision. Your draft is saved…';
        form.requestSubmit(button || undefined);
        essay.readOnly = true;
        for (const control of form.querySelectorAll('button')) control.disabled = true;
    });
    window.addEventListener('beforeunload', event => {
        if (!leaving && essay.value !== lastSaved) { event.preventDefault(); event.returnValue = ''; }
    });
    window.addEventListener('pageshow', event => {
        if (event.persisted) window.location.reload();
    });
    updateCount();
})();
