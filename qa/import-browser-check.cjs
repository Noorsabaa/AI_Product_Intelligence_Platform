const {chromium}=require(process.env.PLAYWRIGHT_MODULE);
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({headless:true,channel:'msedge'});
 try {
  const page=await browser.newPage({viewport:{width:1280,height:900}});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  const base='http://127.0.0.1:8001';
  const registration=await page.request.post(base+'/api/auth/register',{data:{username:'import-'+Date.now(),password:'Import-browser-check-password'}});
  assert.equal(registration.status(),201);
  await page.goto(base+'/#dashboard');
  await page.getByRole('button',{name:'Import feedback',exact:true}).first().click();
  await page.getByLabel('Choose feedback CSV').setInputFiles({name:'export.csv',mimeType:'text/csv',buffer:Buffer.from('Reviews,Date,Rating\nThe billing export is broken and our reports are missing.,8/3/2026,2.0')});
  const rejected=page.waitForResponse(r=>r.url().includes('/ingest/csv')&&r.request().method()==='POST');
  await page.getByRole('button',{name:'Import & analyze',exact:true}).click();
  assert.equal((await rejected).status(),422);
  const choice=page.getByLabel('Date interpretation');await choice.waitFor();
  assert.equal((await page.request.get(base+'/api/dashboard/overview').then(r=>r.json())).summary.total,0);
  await page.screenshot({path:'qa/import-date-choice.png',fullPage:true,animations:'disabled'});
  await choice.selectOption('mdy');
  const imported=page.waitForResponse(r=>r.url().includes('/ingest/csv')&&r.request().method()==='POST');
  await page.getByRole('button',{name:'Import & analyze',exact:true}).click();
  assert.equal((await imported).status(),200);
  await page.getByRole('heading',{name:'Import company feedback'}).waitFor({state:'hidden'});
  assert.equal((await page.request.get(base+'/api/dashboard/overview').then(r=>r.json())).summary.total,1);
  assert.deepEqual(errors,[]);
  console.log(JSON.stringify({passed:['ambiguous date choice displayed','rejected import left workspace empty','same file imported successfully after month/day choice','dialog closed after successful import'],errors}));
 } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
