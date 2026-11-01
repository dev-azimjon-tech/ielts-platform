(() => {
    const config = JSON.parse(document.getElementById('speaking-config').textContent);
    const aiCsrfToken = config.csrf;
    const speakingPlan = config.plan;
    const turnUrl = config.turnUrl;
    const completeUrl = config.completeUrl;
    const examConfigElement = document.getElementById('exam-config');
    const examConfig = examConfigElement ? JSON.parse(examConfigElement.textContent) : null;
    let recoveredSpeaking = examConfig && examConfig.draft || {};
    if (!examConfig) {
        try {
            const saved = JSON.parse(sessionStorage.getItem(config.storageKey));
            if (saved && Date.now()-saved.savedAt < 86400000 && Array.isArray(saved.turns)
                && saved.turns.length <= speakingPlan.length && Number.isInteger(saved.index)
                && saved.index >= 0 && saved.index < speakingPlan.length
                && saved.turns.every(t => t && typeof t.question==='string' && typeof t.transcript==='string')
                && (!saved.next || typeof saved.next.question==='string')) recoveredSpeaking=saved;
        } catch (_) { /* Recording remains usable when storage is blocked. */ }
    }
    function saveProgress() {
        if (!examConfig) try { sessionStorage.setItem(config.storageKey,JSON.stringify({...window.ieltsSpeakingDraft,savedAt:Date.now()})); } catch (_) {}
    }
    window.ieltsSpeakingDraft = recoveredSpeaking;
    let currentIndex = Number.isInteger(recoveredSpeaking.index) ? Math.min(recoveredSpeaking.index, speakingPlan.length-1) : 0;
    if (recoveredSpeaking.next) speakingPlan[currentIndex] = recoveredSpeaking.next;
    let currentQuestion = speakingPlan[currentIndex].question;
    let history = Array.isArray(recoveredSpeaking.turns) ? recoveredSpeaking.turns : [];
    let finishing = false;
    let uploading = false;
    let pendingBlob = null;
    let discardRecording = false;
    let examTimedOut = false;
    let mediaRecorder = null;
    let recordingChunks = [];
    let microphoneStream = null;
    let prepTimer = null;
    let allowExit = false;

    const partLabel = document.getElementById('speaking-part-label');
    const progressLabel = document.getElementById('speaking-progress-label');
    const questionLabel = document.getElementById('speaking-question');
    const instructionLabel = document.getElementById('speaking-instruction');
    const recordButton = document.getElementById('record-button');
    const stopButton = document.getElementById('stop-button');
    const retryButton = document.getElementById('retry-upload');
    const finishSavedButton = document.getElementById('finish-saved-speaking');
    const statusMessage = document.getElementById('recording-message');
    const transcriptBox = document.getElementById('speaking-transcript');
    const transcriptText = document.getElementById('transcript-text');
    const errorBox = document.getElementById('speaking-error');
    const prepBox = document.getElementById('speaking-prep');
    const prepCountdown = document.getElementById('prep-countdown');

    function announceQuestion() {
        if ('speechSynthesis' in window) {
            window.speechSynthesis.cancel();
            const voice = new SpeechSynthesisUtterance(currentQuestion);
            voice.rate = 0.9;
            window.speechSynthesis.speak(voice);
        }
    }

    function showError(message) {
        errorBox.hidden = false;
        errorBox.textContent = message;
        statusMessage.textContent = 'Something went wrong. You can try this answer again.';
        recordButton.disabled = false;
        recordButton.hidden = false;
        retryButton.hidden = !pendingBlob;
        retryButton.disabled = false;
        stopButton.hidden = true;
        if (window.ieltsSpeakingDraft.finished) { recordButton.hidden = true; finishSavedButton.hidden = false; }
    }

    function renderQuestion(item, index, announce = true) {
        currentIndex = index;
        currentQuestion = item.question;
        partLabel.textContent = `Part ${item.part}`;
        progressLabel.textContent = `Question ${index + 1} of ${speakingPlan.length}`;
        questionLabel.textContent = currentQuestion;
        instructionLabel.textContent = item.instruction;
        prepBox.hidden = true;
        delete prepBox.dataset.completed;
        errorBox.hidden = true;
        recordButton.disabled = false;
        recordButton.hidden = false;
        stopButton.hidden = true;
        statusMessage.textContent = item.prep_seconds ? 'Start when ready. You will get one minute to prepare.' : 'Ready when you are.';
        if (announce) announceQuestion();
    }

    function startRecording() {
        if (uploading || finishing || prepTimer) return;
        const requestedAfterExpiry = examTimedOut;
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia || !window.MediaRecorder) {
            showError('Recording is unavailable in this browser. Use a browser with microphone recording support.');
            return;
        }
        const item = speakingPlan[currentIndex];
        if (!examTimedOut && item.prep_seconds && !prepBox.dataset.completed) {
            let seconds = item.prep_seconds;
            prepBox.hidden = false;
            prepCountdown.textContent = seconds;
            recordButton.disabled = true;
            statusMessage.textContent = 'Prepare your answer. Recording will start automatically.';
            prepTimer = window.setInterval(() => {
                seconds -= 1;
                prepCountdown.textContent = seconds;
                if (seconds <= 0) {
                    window.clearInterval(prepTimer);
                    prepTimer = null;
                    prepBox.dataset.completed = 'true';
                    prepBox.hidden = true;
                    recordButton.disabled = false;
                    startRecording();
                }
            }, 1000);
            return;
        }
        recordButton.disabled = true;
        navigator.mediaDevices.getUserMedia({audio: true}).then((stream) => {
            microphoneStream = stream;
            if (examTimedOut && !requestedAfterExpiry) {
                stream.getTracks().forEach(track => track.stop());
                recordButton.disabled = false;
                statusMessage.textContent = 'Time ended before recording began. You can end the section or record an untimed answer.';
                return;
            }
            recordingChunks = [];
            discardRecording = false;
            const supported = ['audio/webm;codecs=opus','audio/mp4','audio/ogg;codecs=opus'].find(type => MediaRecorder.isTypeSupported && MediaRecorder.isTypeSupported(type));
            mediaRecorder = new MediaRecorder(stream, supported ? {mimeType:supported} : undefined);
            mediaRecorder.addEventListener('dataavailable', (event) => recordingChunks.push(event.data));
            mediaRecorder.addEventListener('stop', submitRecording, {once: true});
            mediaRecorder.addEventListener('error', () => {
                discardRecording = true;
                if (microphoneStream) microphoneStream.getTracks().forEach(track => track.stop());
                if (mediaRecorder.state !== 'inactive') mediaRecorder.stop();
                showError('Recording was interrupted. Check your microphone and record this answer again.');
            });
            if ('speechSynthesis' in window) window.speechSynthesis.cancel();
            mediaRecorder.start();
            pendingBlob = null; retryButton.hidden = true;
            recordButton.hidden = true;
            stopButton.hidden = false;
            statusMessage.textContent = 'Recording… speak naturally, then press Stop answer.';
        }).catch(() => {
            if (microphoneStream) microphoneStream.getTracks().forEach(track => track.stop());
            showError('The microphone could not start. Check browser microphone permission and recording support, then try again.');
        });
    }

    function stopRecording() {
        if (mediaRecorder && mediaRecorder.state !== 'inactive') mediaRecorder.stop();
        if (microphoneStream) microphoneStream.getTracks().forEach((track) => track.stop());
        stopButton.hidden = true;
        statusMessage.textContent = 'Sending your answer to the AI examiner…';
    }

    async function submitRecording() {
        if (discardRecording) return;
        pendingBlob = new Blob(recordingChunks, {type: mediaRecorder.mimeType || 'audio/webm'});
        await uploadRecording();
    }

    async function uploadRecording() {
        if (uploading || !pendingBlob) return;
        const blob = pendingBlob;
        if (!blob.size || blob.size > 15*1024*1024) {
            pendingBlob=null;
            showError('The recording is empty or too large. Record a shorter answer under 15 MB.'); return;
        }
        uploading = true; recordButton.disabled = true; retryButton.disabled = true;
        errorBox.hidden = true;
        statusMessage.textContent = 'Uploading and transcribing your answer…';
        const form = new FormData();
        const extension = blob.type.startsWith('audio/mp4') ? 'm4a' : blob.type.startsWith('audio/ogg') ? 'ogg' : 'webm';
        form.append('audio', blob, `speaking-${currentIndex}.${extension}`);
        form.append('plan_index', currentIndex);
        form.append('question', currentQuestion);
        form.append('history', JSON.stringify(history));
        if (examConfig) { form.append('_exam_session',examConfig.session); form.append('_exam_stage',examConfig.stage); form.append('_exam_revision',window.ieltsExamRevision ?? examConfig.revision); }
        try {
            const response = await fetch(turnUrl, {method: 'POST', headers:{'X-CSRF-Token':aiCsrfToken}, body: form});
            const payload = await response.json().catch(() => { throw new Error('The server could not process this request. Check your connection or sign in again in another tab, then retry.'); });
            if (!response.ok) throw new Error(payload.error || 'The AI could not process this answer.');
            if (payload.redirect) { allowExit = true; window.location.href = payload.redirect; return; }
            history = payload.turns;
            pendingBlob = null; retryButton.hidden = true;
            transcriptText.textContent = payload.transcript;
            transcriptBox.hidden = false;
            window.ieltsSpeakingDraft = {turns:history,index:payload.finished ? currentIndex : currentIndex+1,next:payload.next || speakingPlan[currentIndex],finished:payload.finished};
            saveProgress();
            window.dispatchEvent(new Event('exam:changed'));
            if (window.ieltsSaveExamDraft) await window.ieltsSaveExamDraft();
            if (payload.finished) {
                await finishSession();
                return;
            }
            const next = payload.next;
            speakingPlan[currentIndex + 1] = next;
            renderQuestion(next, currentIndex + 1);
            if (payload.notice) statusMessage.textContent = payload.notice;
        } catch (error) {
            showError(error.message);
        } finally { uploading=false; retryButton.disabled=false; }
    }

    async function finishSession() {
        if (finishing) return;
        finishing = true;
        finishSavedButton.disabled = true;
        recordButton.hidden = true;
        statusMessage.textContent = 'Preparing feedback for your saved answers…';
        try {
            const body = {turns:history};
            if (examConfig) { body._exam_session = examConfig.session; body._exam_stage = examConfig.stage; body._exam_revision = window.ieltsExamRevision ?? examConfig.revision; }
            const response = await fetch(completeUrl,{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':aiCsrfToken},body:JSON.stringify(body)});
            const payload = await response.json().catch(() => { throw new Error('The server could not process this request. Check your connection or sign in again in another tab, then retry.'); });
            if (window.ieltsSetExamRevision && Number.isInteger(payload.exam_revision)) window.ieltsSetExamRevision(payload.exam_revision);
            if (!response.ok) throw new Error(payload.error || 'Feedback is unavailable. Your saved answers can be retried.');
            allowExit = true;
            if (!examConfig) try { sessionStorage.removeItem(config.storageKey); } catch (_) {}
            window.location.href = payload.redirect;
        } catch(error) {
            showError(error.message);
            finishSavedButton.hidden = false;
            finishSavedButton.disabled = false;
        } finally { finishing = false; }
    }
    retryButton.addEventListener('click',uploadRecording);
    finishSavedButton.addEventListener('click',finishSession);
    if (history.length) {
        renderQuestion(speakingPlan[currentIndex],currentIndex,false);
        transcriptText.textContent=history[history.length-1].transcript; transcriptBox.hidden=false;
        statusMessage.textContent = 'Your completed answers were restored. Any recording interrupted before upload must be recorded again.';
        if (recoveredSpeaking.finished) { recordButton.hidden = true; finishSavedButton.hidden = false; }
    }

    window.addEventListener('exam:expired', () => {
        examTimedOut = true;
        if (prepTimer) { window.clearInterval(prepTimer); prepTimer = null; prepBox.hidden = true; recordButton.disabled = false; }
        if (mediaRecorder && mediaRecorder.state !== 'inactive') stopRecording();
        statusMessage.textContent = 'Section time has ended. Finish this answer for your practice feedback, or end the session from Session details.';
    });
    recordButton.addEventListener('click', startRecording);
    stopButton.addEventListener('click', stopRecording);
    document.getElementById('repeat-question').addEventListener('click', announceQuestion);
    window.addEventListener('pagehide', () => {
        if (prepTimer) window.clearInterval(prepTimer);
        if (microphoneStream) microphoneStream.getTracks().forEach(track => track.stop());
        if ('speechSynthesis' in window) window.speechSynthesis.cancel();
    });
    window.addEventListener('beforeunload', (event) => { if (!allowExit) { event.preventDefault(); event.returnValue = 'Leave Speaking practice? An interrupted recording or upload cannot be restored.'; } });

})();
