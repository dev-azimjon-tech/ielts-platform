/* Dependency-free behavior regressions for the platform's small browser controllers. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

function element(extra = {}) {
    return Object.assign({events: {}, dataset: {}, attributes: {}, hidden: false, disabled: false, value: '', textContent: '',
        classList: {toggle() {}}, addEventListener(name, fn) { this.events[name] = fn; },
        setAttribute(name, value) { this.attributes[name] = value; }, removeAttribute(name) { delete this.attributes[name]; },
        focus() { this.focused = (this.focused || 0) + 1; }, scrollIntoView() {}}, extra);
}
function run(name, context) {
    vm.runInNewContext(fs.readFileSync(path.join(__dirname, '../../app/static/js/', name), 'utf8'), context);
}
function event(extra = {}) { return {defaultPrevented: false, preventDefault() { this.defaultPrevented = true; }, ...extra}; }

function examEnvironment() {
    const text = element({name: 'question_1', type: 'text'});
    const radioA = element({name: 'question_2', type: 'radio', value: 'A', checked: false});
    const radioB = element({name: 'question_2', type: 'radio', value: 'B', checked: false});
    const inputs = [text, radioA, radioB];
    const question1 = element({dataset: {step: '0', questionNumber: '1'}, querySelectorAll: () => [text]});
    const question2 = element({dataset: {step: '0', questionNumber: '2'}, querySelectorAll: () => [radioA, radioB]});
    const heading = element(), count = element({dataset: {total: '2'}});
    const step = element({querySelector: selector => selector === 'h2' ? heading : count,
        querySelectorAll: () => [], contains: () => true});
    const tab = element({dataset: {goStep: '0'}});
    const jumps = [1, 2].map(number => element({dataset: {goQuestion: String(number)}}));
    const form = element({querySelectorAll: selector => selector === '[data-question-number]' ? [question1, question2] : inputs});
    const root = element({dataset: {skill: 'reading', draftKey: 'draft'}, querySelectorAll: selector => ({
        '.exam-step': [step], '.exam-step-tab': [tab], '[data-go-question]': jumps,
        '[data-highlight-id]': [], '.start-audio': []}[selector] || [])});
    const ids = {'exam-root': root, 'mock-form': form, 'question-1': question1, 'question-2': question2,
        'listening-scripts': element({textContent: '[]'}), 'exam-config': null};
    for (const id of ['previous-step', 'next-step', 'submit-mock', 'exam-notes', 'section-notes', 'toggle-notes',
        'study-status', 'draft-status', 'answered-progress', 'step-progress', 'notes-label', 'close-notes',
        'highlight-selection', 'quote-selection', 'clear-highlights', 'exit-mock']) ids[id] = element();
    ids['exam-notes'].hidden = true;
    const storage = {value: null, getItem() { return this.value; }, setItem(key, value) { if (this.blocked) throw new Error('Storage unavailable'); this.value = value; }, removeItem() {}};
    const win = element({innerWidth: 1200, confirms: 0, messages: [], confirm(message) { this.confirms++; this.messages.push(message); return true; }, getSelection: () => null});
    run('exam.js', {document: {getElementById: id => ids[id], querySelector: () => null, addEventListener() {}},
        window: win, localStorage: storage, setTimeout: () => 1, clearTimeout() {}, clearInterval() {},
        setInterval: () => 1, Node: {ELEMENT_NODE: 1}});
    return {form, ids, text, radioA, radioB, storage, win};
}
function examTests() {
    const cancelled = examEnvironment();
    cancelled.form.events.submit(event({defaultPrevented: true}));
    assert.equal(cancelled.win.confirms, 0);
    assert.equal(cancelled.ids['submit-mock'].disabled, false);
    const leaving = event(); cancelled.win.events.beforeunload(leaving);
    assert.equal(leaving.defaultPrevented, true, 'An already-cancelled submit must retain leave protection');

    const draft = examEnvironment();
    draft.text.value = 'Browser-restored text without an input event';
    draft.radioB.checked = true;
    draft.win.events.pagehide();
    let saved = JSON.parse(draft.storage.value);
    assert.equal(saved.answers.question_1, draft.text.value);
    assert.equal(saved.answers.question_2, 'B');
    draft.radioB.checked = false;
    draft.win.events.pagehide(); saved = JSON.parse(draft.storage.value);
    assert.equal('question_2' in saved.answers, false, 'An unchecked radio answer must not remain in the saved draft');

    const blocked = examEnvironment(); blocked.storage.blocked = true;
    blocked.ids['exit-mock'].events.click(event());
    assert.match(blocked.win.messages.at(-1), /Saving is unavailable.*discard/);

    const duplicate = examEnvironment();
    duplicate.form.events.submit(event());
    assert.equal(duplicate.win.confirms, 1);
    const second = event(); duplicate.form.events.submit(second);
    assert.equal(second.defaultPrevented, true); assert.equal(duplicate.win.confirms, 1);
    duplicate.win.events.pageshow({persisted: true});
    duplicate.form.events.submit(event());
    assert.equal(duplicate.win.confirms, 2, 'Returning through the browser back cache must permit a fresh submit');
}

function themeTests() {
    const button = element({querySelector: () => label}), label = element(), root = {dataset: {}};
    const system = element({matches: false});
    const document = element({documentElement: root, querySelectorAll: () => [button]});
    let storageReads = 0;
    const win = element({matchMedia: () => system});
    Object.defineProperty(win, 'localStorage', {get() { storageReads++; throw new Error('Storage blocked'); }});
    run('theme.js', {window: win, document});
    document.events.DOMContentLoaded(); button.events.click();
    assert.equal(root.dataset.theme, 'dark'); assert.equal(button.hidden, false);
    assert.doesNotThrow(() => win.events.storage({key: null, storageArea: {}}));
    assert.equal(storageReads, 1, 'Storage events must not re-access a blocked localStorage getter');
    assert.equal(root.dataset.theme, 'dark');
}

async function guideTests() {
    let rejectPlay;
    const source = element();
    const video = element({readyState: 1, duration: 100, currentTime: 0, networkState: 1, error: null, playCalls: 0,
        querySelector: () => source, play() { this.playCalls++; return new Promise((resolve, reject) => { rejectPlay = reject; }); }});
    const links = [0, 30].map(start => element({dataset: {guideStart: String(start)}}));
    const status = element(), error = element({hidden: true});
    run('guide.js', {document: {getElementById: id => ({'platform-guide-video': video,
        'guide-playback-status': status, 'guide-video-error': error}[id]), querySelectorAll: () => links},
        window: {matchMedia: () => ({matches: true})}});
    assert.equal(video.playCalls, 0);
    const modified = event({ctrlKey: true}); links[1].events.click(modified);
    assert.equal(modified.defaultPrevented, false); assert.equal(video.playCalls, 0);
    links[1].events.click(event()); assert.equal(video.currentTime, 30);
    source.events.error(); rejectPlay(new Error('Video missing'));
    await Promise.resolve(); await Promise.resolve();
    assert.equal(error.hidden, false);
    assert.match(status.textContent, /unavailable.*written steps/);
    const fallback = event(); links[1].events.click(fallback);
    assert.equal(fallback.defaultPrevented, false, 'A failed video must leave written-guide anchors usable');
}

function flashcardTests() {
    const summary = element(), card = element({open: true, querySelector: () => summary});
    const ids = {'flashcard-data': element({textContent: JSON.stringify([
        {term: 'First', meaning: 'One', example: ''}, {term: 'Second', meaning: 'Two', example: 'Example'}])}),
        'study-card': card};
    for (const id of ['study-term', 'study-meaning', 'study-example', 'study-progress', 'study-progress-bar',
        'previous-card', 'next-card', 'shuffle-cards', 'study-controls']) ids[id] = element();
    run('flashcards.js', {document: {getElementById: id => ids[id]}});
    assert.equal(summary.focused, undefined, 'Loading flashcards must not steal initial keyboard focus');
    ids['next-card'].events.click();
    assert.equal(summary.focused, 1); assert.equal(card.open, false); assert.equal(ids['study-term'].textContent, 'Second');
    assert.equal(ids['next-card'].textContent, 'Start again');
    ids['previous-card'].events.click();
    assert.equal(summary.focused, 2); assert.equal(ids['previous-card'].disabled, true);
    ids['shuffle-cards'].events.click(); assert.equal(summary.focused, 3);
}

(async () => {
    const tests = {exam: examTests, theme: themeTests, guide: guideTests, flashcards: flashcardTests};
    const selected = process.argv[2];
    if (!tests[selected]) throw new Error('Choose a frontend controller to test');
    await tests[selected]();
    console.log(`${selected}: behavior checks passed`);
})().catch(error => { console.error(error); process.exitCode = 1; });
