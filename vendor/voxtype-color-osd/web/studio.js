import {createScene} from './scene.js';
const $=id=>document.getElementById(id);
const definitions=await(await fetch('./styles.json')).json();
definitions.forEach((item,i)=>$('style').add(new Option(item.name,String(i))));
const canvas=$('scene'),native=$('native'),ctx=native.getContext('2d');
let scene,style=Number(new URLSearchParams(location.search).get('style')||0),phase=0;
let playing=!matchMedia('(prefers-reduced-motion: reduce)').matches,baking=false,last=performance.now();
$('style').value=String(style);
function detail(){for(const key of ['name','description','material','depth','motion'])$(key).textContent=definitions[style][key];}
function icons(){window.lucide.createIcons();}
function playLabel(){const label=playing?'Pause rotation':'Play rotation';$('play').setAttribute('aria-label',label);$('play').title=label;$('play').innerHTML=`<i data-lucide="${playing?'pause':'play'}"></i>`;icons();}
function render(){
  scene.render(style,phase);const compact=Number($('cadence').value);
  ctx.fillStyle='#000';ctx.fillRect(0,0,720,112);
  const targetWidth=300*(1-.24*compact),targetHeight=44*.9755*(1-.12*compact);
  const scale=Math.min(targetWidth/640,targetHeight/88)*2;
  const width=696*scale,height=112*scale;
  ctx.save();ctx.beginPath();
  ctx.rect(348-320*scale-4,56-44*scale-4,640*scale+8,88*scale+8);ctx.clip();
  ctx.drawImage(canvas,348-width/2,56-height/2,width,height);ctx.restore();
  ctx.fillStyle='#50bf91';ctx.fillRect(712,38,4,58);
  $('phase').value=String(phase*180/Math.PI);
  canvas.dataset.style=definitions[style].id;canvas.dataset.phase=String(phase);
}
$('style').addEventListener('change',()=>{style=Number($('style').value);detail();if(scene)render();});
$('play').addEventListener('click',()=>{playing=!playing;playLabel();});
$('reset').addEventListener('click',()=>{phase=0;$('cadence').value='0';if(scene)render();});
$('phase').addEventListener('input',()=>{playing=false;playLabel();phase=Number($('phase').value)*Math.PI/180;if(scene)render();});
$('cadence').addEventListener('input',()=>{if(scene)render();});
detail();playLabel();

async function bake(){
  baking=true;playing=false;playLabel();
  const only=new URLSearchParams(location.search).get('only');
  const indices=only===null?Array.from({length:10},(_,i)=>i):only.split(',').map(Number).filter(i=>Number.isInteger(i)&&i>=0&&i<10);
  for(const index of indices){
    const atlas=document.createElement('canvas');atlas.width=696*12;atlas.height=112*8;
    const atlasContext=atlas.getContext('2d');
    for(let frame=0;frame<96;frame++){
      style=index;phase=frame*Math.PI*2/96;render();
      atlasContext.drawImage(canvas,(frame%12)*696,Math.floor(frame/12)*112);
      $('status').textContent=`Rendering ${definitions[index].name}: ${frame+1}/96`;
      // Cooperative task yielding also works when the user's active tab changes.
      if(frame%4===0)await new Promise(resolve=>{
        const channel=new MessageChannel();
        channel.port1.onmessage=()=>{channel.port1.close();channel.port2.close();resolve();};
        channel.port2.postMessage(null);
      });
    }
    const blob=await new Promise(resolve=>atlas.toBlob(resolve,'image/png'));
    const response=await fetch(`./atlas/${index}`,{method:'POST',body:blob});
    if(!response.ok)throw new Error(`Atlas export failed: ${response.status}`);
  }
  baking=false;style=0;phase=0;$('style').value='0';detail();render();
  $('status').textContent=`Export complete: ${indices.length} styles × 96 rotation frames`;
  document.body.dataset.export='complete';
}
try{
  scene=await createScene(canvas);render();$('status').textContent='Ready · Three.js geometry, lighting, shadows and depth testing';document.body.dataset.ready='true';
  if(new URLSearchParams(location.search).has('bake'))await bake();
  function tick(now){const dt=Math.min((now-last)/1000,.05);last=now;if(!document.hidden&&!baking&&playing){phase=(phase+dt*(.75+Number($('cadence').value)*8))%(Math.PI*2);render();}requestAnimationFrame(tick);}
  requestAnimationFrame(tick);
}catch(error){$('status').textContent=error.message;$('status').classList.add('failure');document.body.dataset.error=error.message;console.error(error);}
