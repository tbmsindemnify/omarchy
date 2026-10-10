import http from 'node:http';
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
const root=path.dirname(fileURLToPath(import.meta.url));
const port=Number(process.env.PORT || 5247);
const mime={'.html':'text/html','.js':'text/javascript','.mjs':'text/javascript','.json':'application/json','.png':'image/png','.css':'text/css'};
http.createServer(async(req,res)=>{
  try {
    const url=new URL(req.url,`http://127.0.0.1:${port}`);
    if(req.method==='POST' && /^\/atlas\/\d$/.test(url.pathname)) {
      if(req.headers.origin!==`http://127.0.0.1:${port}`) {res.writeHead(403).end();return;}
      const chunks=[];let size=0;
      for await(const chunk of req){size+=chunk.length;if(size>32*1024*1024)throw new Error('Atlas too large');chunks.push(chunk);}
      const data=Buffer.concat(chunks);
      if(!data.subarray(0,8).equals(Buffer.from([137,80,78,71,13,10,26,10])))throw new Error('Expected PNG');
      await fs.mkdir(path.join(root,'../assets'),{recursive:true});
      await fs.writeFile(path.join(root,`../assets/style-${url.pathname.at(-1)}.png`),data);
      res.writeHead(200).end('saved');return;
    }
    if(req.method!=='GET'){res.writeHead(405).end();return;}
    const file=path.resolve(root,'.'+decodeURIComponent(url.pathname==='/'?'/index.html':url.pathname));
    if(!file.startsWith(root+path.sep)){res.writeHead(403).end();return;}
    const data=await fs.readFile(file);
    res.writeHead(200,{'Content-Type':mime[path.extname(file)]||'application/octet-stream','Cache-Control':'no-store'}).end(data);
  } catch(error){res.writeHead(404).end(error.message);}
}).listen(port,'127.0.0.1',()=>console.log(`Voxtype depth studio: http://127.0.0.1:${port}`));
