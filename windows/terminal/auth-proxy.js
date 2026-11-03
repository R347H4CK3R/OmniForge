const http=require('http'),crypto=require('crypto'),fs=require('fs'),path=require('path');
const proxy=require('http-proxy').createProxyServer({target:'http://127.0.0.1:8788',ws:true,changeOrigin:false});
const dir=__dirname,passFile=path.join(dir,'terminal-password.txt'),secretFile=path.join(dir,'session-secret.txt');
function secretFileValue(file){if(!fs.existsSync(file))fs.writeFileSync(file,crypto.randomBytes(32).toString('base64url'),{mode:0o600});return fs.readFileSync(file,'utf8').trim()}
const password=secretFileValue(passFile),key=secretFileValue(secretFile);
function sign(payload){return crypto.createHmac('sha256',key).update(payload).digest('base64url')}
function token(){const p=String(Date.now()+12*3600*1000);return p+'.'+sign(p)}
function isAuthorized(req){const c=(req.headers.cookie||'').match(/(?:^|;\s*)omni_terminal=([^;]+)/);if(!c)return false;const [expiry,mac]=c[1].split('.');if(!expiry||!mac||Number(expiry)<Date.now())return false;const expected=sign(expiry);return mac.length===expected.length&&crypto.timingSafeEqual(Buffer.from(mac),Buffer.from(expected))}
function send(res,status,body,headers={}){res.writeHead(status,{'Content-Type':'text/html; charset=utf-8','Cache-Control':'no-store','X-Content-Type-Options':'nosniff',...headers});res.end(body)}
const login=`<!doctype html><meta name="viewport" content="width=device-width,initial-scale=1"><title>OmniForge terminal</title><style>body{font:16px system-ui;background:#13151a;color:#fff;margin:15vh auto;max-width:320px}input,button{box-sizing:border-box;width:100%;padding:12px;margin:10px 0;border-radius:8px}button{background:#278df3;color:#fff;border:0}</style><h2>OmniForge Terminal</h2><p>Private laptop shell — authentication required</p><form action="/terminal/login" method="POST"><input type="password" name="password" placeholder="Terminal password" required autocomplete="current-password"><button>Connect</button></form>`;
let failures=0;
const server=http.createServer((req,res)=>{
  if(!req.url.startsWith('/terminal'))req.url='/terminal'+(req.url.startsWith('/')?req.url:'/'+req.url);
  if(req.url==='/terminal/login'&&req.method==='POST'){
    let body='';req.on('data',b=>{body+=b;if(body.length>4096)req.destroy()});req.on('end',()=>{
      const attempt=new URLSearchParams(body).get('password')||'';
      const ok=Buffer.byteLength(attempt)===Buffer.byteLength(password)&&crypto.timingSafeEqual(Buffer.from(attempt),Buffer.from(password));
      if(!ok){failures++;return send(res,401,login.replace('<p>Private laptop shell — authentication required</p>','<p style="color:#ff7777">Incorrect terminal password. Use the password in OmniForgeTerminal/terminal-password.txt, not the installer session token.</p>'));}
      failures=0;return send(res,303,'',{'Set-Cookie':'omni_terminal='+token()+'; HttpOnly; Secure; SameSite=Strict; Path=/terminal','Location':'/terminal'})
    });return;
  }
  if(!isAuthorized(req)){if(req.url==='/terminal/'||req.url==='/terminal')return send(res,200,login);return send(res,401,'Authentication required')}
  if(req.url==='/terminal/')req.url='/terminal';
  proxy.web(req,res,{},()=>send(res,502,'Terminal unavailable'));
});
server.on('upgrade',(req,socket,head)=>{if(!req.url.startsWith('/terminal'))req.url='/terminal'+(req.url.startsWith('/')?req.url:'/'+req.url);if(!isAuthorized(req)){socket.write('HTTP/1.1 401 Unauthorized\r\nConnection: close\r\n\r\n');socket.destroy();return}proxy.ws(req,socket,head)});
server.listen(8789,'127.0.0.1',()=>console.log('OmniForge authenticated terminal proxy on 127.0.0.1:8789'));

