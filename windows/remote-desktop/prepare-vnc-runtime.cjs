const fs=require('fs'),path=require('path');
const root=path.join(process.env.LOCALAPPDATA,'OmniForge','noVNC');
let html=fs.readFileSync(path.join(root,'vnc.bundled.html'),'utf8');
html=html.replace(/<link rel="stylesheet" href="([^"]+)">/g,(_,file)=>'<style>'+fs.readFileSync(path.join(root,file),'utf8')+'</style>');
html=html.replace(/<link rel="preload"[^>]+>/g,'');
html=html.replace(/<script defer src="omniforge-bundle.js[^"]*"><\/script>/,'');
const prelude=`<aside id="of_runtime" style="position:fixed;left:8px;top:8px;z-index:30000;background:#fff;color:#000;padding:10px;font:14px monospace;max-width:90vw;max-height:35vh;overflow:auto;white-space:pre-wrap;touch-action:auto"><strong>Desktop runtime check</strong><div id="of_runtime_text">Page parsed. Starting viewer...</div><button onclick="document.getElementById('of_runtime').style.display='none'">Hide status</button></aside><script>
(function(){
var messages=[],last='',panel=document.getElementById('of_runtime'),text=document.getElementById('of_runtime_text');
function report(s){messages.push(s);text.textContent=messages.slice(-8).join('\\n');}
window.addEventListener('error',function(e){report('ERROR: '+e.message+' @ '+e.lineno);});
window.addEventListener('unhandledrejection',function(e){report('REJECTION: '+String(e.reason));});
report('Inline script started.');
var tick=0,timer=setInterval(function(){tick++;
var classes=document.documentElement.className;var status=document.getElementById('noVNC_status');var error=document.getElementById('omniforge_startup_error');var fallback=document.getElementById('noVNC_fallback_errormsg');
var state='State: '+(classes||'(none)')+(status&&status.textContent?' | '+status.textContent:'')+(error?' | '+error.textContent:'')+(fallback&&fallback.textContent?' | '+fallback.textContent:'');
if(state!==last){report(state);last=state;}
if(classes.indexOf('noVNC_connected')>=0){clearInterval(timer);panel.style.display='none';}
if(tick===15)report('15 seconds elapsed. If no password form appears, share this status.');
if(tick>=30)clearInterval(timer);
},1000);
})();
<\/script>`;
html=html.replace('<body>','<body>'+prelude);
const bundle=fs.readFileSync(path.join(root,'omniforge-bundle.js'),'utf8').replace(/<\/script/gi,'<\\/script');
html=html.replace('</body>','<script>'+bundle+'</script></body>');
fs.writeFileSync(path.join(root,'runtime.html'),html);
console.log('Created inline runtime viewer: '+Buffer.byteLength(html)+' bytes');
