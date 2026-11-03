const https=require('https'),fs=require('fs'),path=require('path');
const {io}=require(path.join(process.env.APPDATA,'npm/node_modules/wetty/node_modules/socket.io-client'));
const origin='https://gaminglaptop-1.tail54e01b.ts.net';
const password=fs.readFileSync(path.join(__dirname,'terminal-password.txt'),'utf8').trim();
const body='password='+encodeURIComponent(password);
const req=https.request(origin+'/terminal/login',{method:'POST',headers:{Origin:origin,'Content-Type':'application/x-www-form-urlencoded','Content-Length':Buffer.byteLength(body)}},res=>{
 const cookie=res.headers['set-cookie']?.[0]?.split(';')[0];res.resume();
 if(res.statusCode!==303||!cookie){console.error('HTTPS login failed',res.statusCode);process.exit(1)}
 const socket=io(origin,{path:'/terminal/socket.io',transports:['websocket'],extraHeaders:{Cookie:cookie,Origin:origin},reconnection:false,timeout:10000});
 let buffer='';
 socket.on('login',()=>socket.emit('input',"Write-Output ('OMNIFORGE_' + (111 + 222))\r",false));
 const output=d=>{buffer=(buffer+String(d)).slice(-64000);if(buffer.includes('OMNIFORGE_333')){console.log('PASS: private HTTPS login, WebSocket PTY and actual PowerShell command result');socket.disconnect();process.exit(0)}};
 socket.on('data',output);socket.on('output',output);
 socket.on('connect_error',e=>{console.error(e.message);process.exit(2)});
 setTimeout(()=>{console.error('Command result timeout');socket.disconnect();process.exit(3)},15000);
});req.on('error',e=>{console.error(e.message);process.exit(4)});req.end(body);

