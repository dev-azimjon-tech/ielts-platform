(() => {
    const review = document.querySelector('[data-speaking-review]');
    if (!review) return;
    const players = [...review.querySelectorAll('[data-answer-audio]')];
    const status = review.querySelector('[data-speaking-status]');
    const speed = review.querySelector('[data-speaking-speed]');
    if (speed) speed.addEventListener('change', () => {
        const rate = Number(speed.value);
        if (![0.75,1,1.25,1.5].includes(rate)) return;
        for (const player of players) player.playbackRate = rate;
        status.textContent = `Playback speed: ${rate}×.`;
    });
    for (const answer of review.querySelectorAll('[data-speaking-answer]')) {
        const audio = answer.querySelector('[data-answer-audio]');
        if (!audio) continue;
        const replay = answer.querySelector('[data-answer-replay]');
        const loop = answer.querySelector('[data-answer-loop]');
        const error = answer.querySelector('[data-answer-error]');
        audio.addEventListener('play', () => {
            for (const other of players) if (other !== audio) other.pause();
            status.textContent = `Playing answer ${answer.dataset.answerNumber}.`;
        });
        loop.addEventListener('change', () => { audio.loop = loop.checked; });
        replay.addEventListener('click', async () => {
            try { audio.currentTime = 0; } catch (_) { /* An unloaded recording starts at zero. */ }
            try { await audio.play(); }
            catch (_) { status.textContent = 'Playback could not start. Try the native player controls or download this recording.'; }
        });
        function showAudioError() {
            error.hidden = false;
            replay.disabled = true; loop.disabled = true;
        }
        audio.addEventListener('error', showAudioError);
        for (const source of audio.querySelectorAll('source')) source.addEventListener('error', showAudioError);
        if (audio.error) showAudioError();
    }
    window.addEventListener('pagehide', () => { for (const audio of players) audio.pause(); });
})();
