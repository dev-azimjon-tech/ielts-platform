const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('app/static/js/exam-session.js','utf8');

function setup() {
    const handlers = {}, intervals = [], calls = [], replies = [];
    const essay = {name:'essay',value:'initial',dispatchEvent() {}};
    const version = {name:'_exam_revision',value:'0'};
    const status = {textContent:''}, timerStatus = {textContent:'',dataset:{}};
    const form = {dataset:{},elements:[essay,version],nativeSubmissions:0,confirmations:0,cancel:false,
        addEventListener(type,fn) { (handlers[type] ||= []).push(fn); },
        querySelector(selector) { return selector === '[name=essay]' ? essay : version; },
        requestSubmit(button) {
            const event = {submitter:button,defaultPrevented:false,preventDefault(){this.defaultPrevented=true;}};
            for (const listener of handlers.submit) listener(event);
            // Mimic exam.js: canceled autosave events must not prompt, accepted events prompt once.
            if (!event.defaultPrevented) { this.confirmations++; if (this.cancel) event.preventDefault(); }
            if (!event.defaultPrevented) { this.nativeSubmissions++; this.sentVersion=version.value; this.sentEssay=essay.value; }
        }
    };
    const config = {revision:0,draft:{essay:'initial'},restore:true,session:1,stage:2,csrf:'csrf',
        serverNow:new Date().toISOString(),deadline:new Date(Date.now()+3600000).toISOString(),draftUrl:'/draft'};
    const output = {textContent:''};
    const banner = {querySelector:()=>output};
    const win = {addEventListener(){},dispatchEvent(){}};
    const doc = {getElementById(id) { return {'exam-config':{textContent:JSON.stringify(config)},'exam-save-status':status,'exam-timer-status':timerStatus}[id]; },
        querySelector(selector){return selector==='[data-exam-deadline]'?banner:form;},addEventListener(){}};
    function FakeFormData(f) { this[Symbol.iterator] = function*(){for(const input of f.elements)yield [input.name,input.value];}; }
    vm.runInNewContext(source,{document:doc,window:win,performance:{now:()=>0},Date,JSON,FormData:FakeFormData,
        Event:class {constructor(type){this.type=type;}},queueMicrotask,
        setTimeout:()=>1,clearTimeout(){},setInterval:fn=>intervals.push(fn),
        fetch:(url,options)=>{calls.push(JSON.parse(options.body));return replies.shift()();}});
    return {form,essay,version,status,win,calls,replies};
}
const reply = version => Promise.resolve({ok:true,json:async()=>({revision:version})});
async function flush() { for(let i=0;i<30;i++)await Promise.resolve(); }

(async()=>{
    const state = setup();
    let finishFirst;
    state.replies.push(()=>new Promise(resolve=>finishFirst=resolve),()=>reply(2));
    state.essay.value='first edit';
    const pending = state.win.ieltsSaveExamDraft();
    state.essay.value='latest edit';
    state.form.requestSubmit();
    assert.equal(state.form.nativeSubmissions,0);
    finishFirst({ok:true,json:async()=>({revision:1})});
    await pending; await flush();
    assert.equal(state.calls.length,2);
    assert.equal(state.calls[1].revision,1);
    assert.equal(state.calls[1].draft.essay,'latest edit');
    assert.equal(state.form.nativeSubmissions,1);
    assert.equal(state.form.sentVersion,2);
    assert.equal(state.form.sentEssay,'latest edit');
    assert.equal(state.form.confirmations,1);

    const conflict = setup();
    conflict.replies.push(()=>Promise.resolve({ok:false,status:409,json:async()=>({error:'A newer draft exists'})}));
    conflict.essay.value='stale text'; conflict.form.requestSubmit(); await flush();
    conflict.form.requestSubmit(); await flush();
    assert.equal(conflict.form.nativeSubmissions,0);
    assert.equal(conflict.calls.length,1);
    assert.match(conflict.status.textContent,/newer draft/);

    const cancel = setup();
    cancel.form.cancel=true; cancel.form.requestSubmit(); await flush();
    assert.equal(cancel.form.nativeSubmissions,0);
    cancel.form.cancel=false; cancel.form.requestSubmit(); await flush();
    assert.equal(cancel.form.nativeSubmissions,1);
    assert.equal(cancel.form.confirmations,2);
    console.log('Exam autosave serialization, stale-draft blocking, and canceled-confirmation recovery passed.');
})().catch(error=>{console.error(error);process.exitCode=1;});
