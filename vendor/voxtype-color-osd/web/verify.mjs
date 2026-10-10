import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
const {chromium}=await import(process.env.PLAYWRIGHT_MODULE||'playwright');
const root=path.dirname(fileURLToPath(import.meta.url));
const out=process.env.EVIDENCE_DIR||path.join(root,'../evidence');
await fs.mkdir(out,{recursive:true});
const definitions=JSON.parse(await fs.readFile(path.join(root,'styles.json'),'utf8'));
const browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_PATH||'/usr/bin/chromium',
  args:['--use-angle=swiftshader','--enable-unsafe-swiftshader']});
const errors=[];
const evidence=[];
try {
  for(const [width,height] of [[1280,800],[390,844]]) {
    const page=await browser.newPage({viewport:{width,height},deviceScaleFactor:1});
    page.on('pageerror',error=>errors.push(error.message));
    await page.goto(process.env.PREVIEW_URL||'http://127.0.0.1:5247/');
    await page.waitForSelector('body[data-ready=true]');
    await page.getByRole('button',{name:'Pause rotation',exact:true}).click();
    await page.getByRole('button',{name:'Reset view',exact:true}).click();
    assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
    for(let i=0;i<definitions.length;i++) {
      await page.getByLabel('Visual treatment',{exact:true}).selectOption(String(i));
      assert.equal(await page.locator('#name').innerText(),definitions[i].name);
      assert.equal(await page.locator('#description').innerText(),definitions[i].description);
      const stats=await page.evaluate(()=>{
        const data=document.querySelector('#native').getContext('2d').getImageData(0,0,696,112).data;
        let lit=0,dark=0,bright=0,sum=0,sum2=0;
        for(let i=0;i<data.length;i+=4){const v=Math.max(data[i],data[i+1],data[i+2]);
          if(v>25){lit++;sum+=v;sum2+=v*v;if(v<95)dark++;if(v>190)bright++;}}
        return {lit,dark,bright,contrast:Math.sqrt(sum2/lit-(sum/lit)**2)};
      });
      assert(stats.lit>1500,`Blank ${definitions[i].id}`);
      assert(stats.contrast>25,`Flat value range ${definitions[i].id}`);
      if(width===1280)await page.locator('#native').screenshot({path:path.join(out,`${i}-${definitions[i].id}.png`)});
      evidence.push({width,style:definitions[i].id,...stats});
    }
    await page.getByLabel('Visual treatment',{exact:true}).selectOption('0');
    const still=await page.locator('#scene').getAttribute('data-phase');
    await page.getByRole('button',{name:'Play rotation',exact:true}).click();
    await page.waitForTimeout(600);
    assert.notEqual(await page.locator('#scene').getAttribute('data-phase'),still,'Rotation frozen');
    await page.getByRole('slider',{name:'Speech cadence',exact:true}).focus();
    await page.keyboard.press('End');
    await page.waitForTimeout(250);
    await page.getByRole('button',{name:'Pause rotation',exact:true}).click();
    await page.getByRole('button',{name:'Reset view',exact:true}).click();
    await page.screenshot({path:path.join(out,`studio-${width}.png`),fullPage:true});
    await page.close();
  }
  const page=await browser.newPage({reducedMotion:'reduce'});
  await page.goto(process.env.PREVIEW_URL||'http://127.0.0.1:5247/');
  await page.waitForSelector('body[data-ready=true]');
  assert(await page.getByRole('button',{name:'Play rotation',exact:true}).isVisible());
  assert.equal(errors.length,0,errors.join('\n'));
  await fs.writeFile(path.join(out,'browser-checks.json'),JSON.stringify(evidence,null,2));
  console.log(`PASS: ${evidence.length} style/viewport checks; motion, cadence controls, reduced motion; no page errors.`);
} finally {await browser.close();}
