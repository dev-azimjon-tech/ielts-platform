const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const source=fs.readFileSync('app/static/js/speaking-practice.js','utf8');
function node(extra={}){return Object.assign({hidden:false,disabled:false,dataset:{},textContent:'',events:{},addEventListener(n,f){this.events[n]=f}},extra)}
function setup(saved=null){
 const nodes={},events={},storage=new Map();
 if(saved)storage.set('practice',JSON.stringify(saved));
 const plan=[{part:1,question:'First?',instruction:'Answer',prep_seconds:0},{part:2,question:'Next?',instruction:'Describe',prep_seconds:0}];
 nodes['speaking-config']=node({textContent:JSON.stringify({csrf:'token',plan,turnUrl:'/turn',completeUrl:'/complete',storageKey:'practice'})});
 nodes['exam-config']=null;
 for(const id of ['speaking-part-label','speaking-progress-label','speaking-question','speaking-instruction','record-button','stop-button','finish-saved-speaking','retry-upload','recording-message','speaking-transcript','transcript-text','speaking-error','speaking-prep','prep-countdown','repeat-question'])nodes[id]=node();
 const requests=[];let recorder,tracksStopped=0;
 class Recorder{static isTypeSupported(){return true}constructor(){this.events={};this.mimeType='audio/webm';this.state='inactive';recorder=this}addEventListener(n,f){this.events[n]=f}start(){this.state='recording'}stop(){this.state='inactive';this.events.dataavailable({data:new Blob(['voice'])});this.events.stop()}}
 const state={nodes,events,storage,requests,get recorder(){return recorder},get stopped(){return tracksStopped},reply:async()=>({ok:false,json:async()=>({error:'Temporary network failure'})})};
 const window={MediaRecorder:Recorder,addEventListener:(n,f)=>events[n]=f,dispatchEvent:()=>{},location:{href:''},setInterval:()=>1,clearInterval:()=>{}};
 const sandbox={document:{getElementById:id=>nodes[id]},window,MediaRecorder:Recorder,Blob,FormData:class{constructor(){this.values={}}append(n,v){this.values[n]=v}},navigator:{mediaDevices:{getUserMedia:async()=>({getTracks:()=>[{stop(){tracksStopped++}}]})}},sessionStorage:{getItem:k=>storage.get(k)||null,setItem:(k,v)=>storage.set(k,v),removeItem:k=>storage.delete(k)},Date,Event:class{},fetch:async(url,args)=>{requests.push({url,args});return state.reply(url,args)}};
 vm.runInNewContext(source,sandbox);return state;
}
async function settle(){for(let i=0;i<30;i++)await Promise.resolve()}
(async()=>{
 const s=setup();s.nodes['record-button'].events.click();await settle();s.nodes['stop-button'].events.click();await settle();
 assert.equal(s.requests.length,1);assert.equal(s.nodes['record-button'].hidden,false);assert.equal(s.nodes['retry-upload'].hidden,false);
 s.reply=async()=>({ok:true,json:async()=>({transcript:'Saved answer',turns:[{part:1,question:'First?',transcript:'Saved answer',recording_id:'id'}],finished:false,next:{part:2,question:'Next?',instruction:'Describe',prep_seconds:0}})});
 await s.nodes['retry-upload'].events.click();await settle();assert.equal(s.requests.length,2);assert.equal(s.nodes['speaking-question'].textContent,'Next?');assert.equal(s.nodes['speaking-transcript'].hidden,false);
 assert.equal(JSON.parse(s.storage.get('practice')).index,1);
 const resumed=setup(JSON.parse(s.storage.get('practice')));assert.equal(resumed.nodes['speaking-question'].textContent,'Next?');assert.equal(resumed.nodes['transcript-text'].textContent,'Saved answer');
 const broken=setup();broken.nodes['record-button'].events.click();await settle();broken.recorder.events.error();await settle();assert.equal(broken.requests.length,0);assert.equal(broken.nodes['record-button'].hidden,false);assert.ok(broken.stopped>0);
 const finished=setup({savedAt:Date.now(),index:1,finished:true,turns:[{part:1,question:'Q',transcript:'A'}]});
 assert.equal(finished.nodes['finish-saved-speaking'].hidden,false);assert.equal(finished.nodes['record-button'].hidden,true);
 console.log('Speaking upload retry, interruption, transcript persistence, and recovery checks passed.');
})().catch(error=>{console.error(error);process.exitCode=1});
