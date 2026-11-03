const fs=require('fs'),path=require('path');
const root=path.join(process.env.LOCALAPPDATA,'OmniForge','noVNC');
const original=path.join(root,'vnc.original.html');
const html=fs.readFileSync(fs.existsSync(original)?original:path.join(root,'vnc.html'),'utf8');
if(!fs.existsSync(path.join(root,'vnc.original.html')))fs.writeFileSync(path.join(root,'vnc.original.html'),html);
const boot=`import './app/error-handler.js';
import UI from './app/ui.js';
(async function(){
const timeout=(p,name)=>Promise.race([p,new Promise((_,reject)=>setTimeout(()=>reject(new Error(name+' timed out. Check Tailscale, then reload.')),15000))]);
try{
const settings=async name=>{try{const r=await timeout(fetch('./'+name,{cache:'no-store'}),name);return r.ok?await r.json():{};}catch(e){console.warn(e);return {};}};
const defaults=await settings('defaults.json'),mandatory=await settings('mandatory.json');
await timeout(UI.start({settings:{defaults,mandatory}}),'Desktop startup');
}catch(e){document.documentElement.classList.remove('noVNC_loading');let m=document.createElement('pre');m.id='omniforge_startup_error';m.style='position:fixed;z-index:10000;inset:20px;background:#171717;color:white;padding:20px;white-space:pre-wrap';m.textContent='Desktop startup failed: '+e.message+'\\nReload this page. If this repeats, share this message.';document.body.appendChild(m);}
})();`;
fs.writeFileSync(path.join(root,'omniforge-bootstrap.js'),boot);
const replacement=html.replace(/<script type="module" crossorigin="anonymous" src="app\/error-handler.js"><\/script>/,'').replace(/<script type="module">[\s\S]*?<\/script>/,'<script defer src="omniforge-bundle.js?v=20261103a"></script>');
fs.writeFileSync(path.join(root,'vnc.bundled.html'),replacement);
console.log('Prepared bundled startup; original page preserved.');
