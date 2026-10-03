// Build the frontend, then run: PLAYWRIGHT_MODULE=/path/to/playwright node tests/conversation-ui.cjs
// Uses installed Chrome, an isolated production server and mocked API responses.
const assert = require('node:assert/strict');
const { spawn } = require('node:child_process');
const { once } = require('node:events');
const net = require('node:net');
const path = require('node:path');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');

const done = { type: 'done', reply: 'Xin chào test', used_agents: ['lead', 'catalog'], trace: [{ agent: 'catalog', event: 'recommend', detail: 'test evidence' }], run_id: 'run-test', decision: null };
const frame = event => `data: ${JSON.stringify(event)}\n\n`;

async function main() {
  const listener = net.createServer();
  listener.listen(0, '127.0.0.1');
  await once(listener, 'listening');
  const port = listener.address().port;
  await new Promise(resolve => listener.close(resolve));
  const server = spawn(process.execPath, [require.resolve('../node_modules/next/dist/bin/next'), 'start', '--hostname', '127.0.0.1', '--port', String(port)], { cwd: path.resolve(__dirname, '..'), windowsHide: true, stdio: ['ignore', 'pipe', 'pipe'] });
  let logs = '';
  for (const stream of [server.stdout, server.stderr]) stream.on('data', chunk => { logs = (logs + chunk).slice(-10000); });
  const base = `http://127.0.0.1:${port}`;
  let browser;
  let passed = 0;
  try {
    let ready = false;
    for (let attempt = 0; attempt < 100; attempt++) {
      if (server.exitCode !== null) throw new Error(logs);
      try { if ((await fetch(base)).ok) { ready = true; break; } } catch {}
      await new Promise(resolve => setTimeout(resolve, 100));
    }
    assert.ok(ready, 'frontend startup timed out');
    browser = await chromium.launch({ channel: 'chrome', headless: true });
    async function scenario(name, run, history) {
      const context = await browser.newContext();
      await context.addInitScript(({ history }) => {
        localStorage.setItem('salepilot_external_id', 'web-fixed');
        localStorage.setItem('salepilot_owner_token', 'test-owner');
        if (history) localStorage.setItem('salepilot_msgs', JSON.stringify(history));
      }, { history });
      const page = await context.newPage();
      const errors = [];
      page.on('pageerror', error => errors.push(error.message));
      try {
        await run(page);
        assert.deepEqual(errors, [], `${name}: browser exceptions`);
        console.log(`PASS ${name}`);
        passed++;
      } finally { await context.close(); }
    }
    async function send(page) {
      await page.goto(base + '/chat');
      await page.locator('.status').filter({ hasText: 'web-fixed' }).waitFor();
      await page.getByRole('textbox', { name: '' }).fill('Tư vấn tủ lạnh');
      await page.getByRole('button', { name: 'Gửi', exact: true }).click();
    }
    await scenario('stream tokens, evidence and saved history', async page => {
      await page.route('**/chat/stream', route => route.fulfill({ contentType: 'text/event-stream', body: frame({type:'token',content:'Xin '}) + frame({type:'token',content:'chào test'}) + frame(done) }));
      await send(page);
      await page.locator('.chat-log .bubble').filter({hasText:'Xin chào test'}).waitFor();
      await page.locator('.trace-item').filter({hasText:'test evidence'}).waitFor();
      await page.waitForFunction(() => (JSON.parse(localStorage.getItem('salepilot_msgs') || '[]')).some(m => m.meta?.run_id === 'run-test'));
      await page.reload();
      await page.locator('.chat-log .bubble').filter({hasText:'Xin chào test'}).waitFor();
      await page.locator('.trace-item').filter({hasText:'test evidence'}).waitFor();
    });
    await scenario('batch fallback before stream data', async page => {
      let batches = 0;
      await page.route('**/chat/stream', route => route.fulfill({status:503,body:'unavailable'}));
      await page.route('http://localhost:8000/chat', route => { batches++; return route.fulfill({json:done}); });
      await send(page);
      await page.locator('.chat-log .bubble').filter({hasText:'Xin chào test'}).waitFor();
      assert.equal(batches,1);
    });
    await scenario('partial stream failure keeps text without replay', async page => {
      let batches = 0;
      await page.route('**/chat/stream', route => route.fulfill({contentType:'text/event-stream',body:frame({type:'token',content:'Một phần câu trả lời'})+frame({type:'error',detail:'provider down'})}));
      await page.route('http://localhost:8000/chat', route => { batches++; return route.fulfill({json:done}); });
      await send(page);
      await page.locator('.chat-log .bubble').filter({hasText:'Mất kết nối giữa chừng'}).waitFor();
      assert.equal(batches,0);
      assert.match(await page.locator('.chat-log .bubble').last().innerText(),/Một phần câu trả lời/);
    });
    await scenario('done-only response and new session', async page => {
      await page.route('**/chat/stream', route => route.fulfill({contentType:'text/event-stream',body:frame(done)}));
      await send(page);
      await page.locator('.chat-log .bubble').filter({hasText:'Xin chào test'}).waitFor();
      await page.getByRole('button',{name:'Phiên mới',exact:true}).click();
      await page.waitForFunction(() => localStorage.getItem('salepilot_external_id') !== 'web-fixed');
      assert.equal(await page.locator('.chat-log .msg').count(),1);
      assert.equal(await page.locator('.trace-item').count(),0);
    });
    await scenario('select evidence from earlier saved turn', async page => {
      await page.goto(base+'/chat');
      await page.locator('.trace-item').filter({hasText:'second trace'}).waitFor();
      await page.locator('.chat-log .bubble').filter({hasText:'first reply'}).click();
      await page.locator('.trace-item').filter({hasText:'first trace'}).waitFor();
    }, [{id:'first',role:'assistant',content:'first reply',meta:{trace:[{agent:'catalog',event:'first',detail:'first trace'}]}},{id:'second',role:'assistant',content:'second reply',meta:{trace:[{agent:'knowledge',event:'second',detail:'second trace'}]}}]);
    async function dashboard(page, options = {}) {
      let status = 'open';
      const actions = [];
      page.on('dialog', dialog => dialog.accept('test-owner'));
      await page.route('**/api/admin?*', route => {
        const endpoint = new URL(route.request().url()).searchParams.get('path');
        options.onRequest?.(endpoint);
        if(options.unauthorized) return route.fulfill({status:401,body:'denied'});
        if(endpoint.endsWith('/takeover') || endpoint.endsWith('/resolve')) {
          assert.equal(route.request().method(),'POST');
          assert.deepEqual(route.request().postDataJSON(),{channel:'web',external_id:'web-customer'});
          status=endpoint.endsWith('/takeover')?'escalated':'open'; actions.push(status);
          return route.fulfill({json:{ok:true,conversation_id:1,status}});
        }
        if(endpoint==='/jobs' && options.failJobs) return route.fulfill({status:500,body:'jobs unavailable'});
        const payload={'/leads':[{id:1,name:'Test customer'}],'/leads/conversations':[{id:1,channel:'web',external_id:'web-customer',customer_name:'Test customer',status}],'/memory':[],'/jobs':[],'/runs/latest':{run:null}}[endpoint];
        assert.notEqual(payload,undefined,endpoint);
        return route.fulfill({json:payload});
      });
      await page.goto(base+'/dashboard');
      if (!options.keepAuto) await page.getByRole('checkbox').uncheck();
      return actions;
    }
    await scenario('dashboard partial failure preserves successful panels',async page=>{
      await dashboard(page,{failJobs:true});
      await page.locator('.error-note').filter({hasText:'jobs unavailable'}).waitFor();
      await page.getByRole('heading',{name:'Leads (1)',exact:true}).waitFor();
      await page.getByRole('button',{name:'Làm mới',exact:true}).click();
      await page.getByRole('button',{name:'Người tiếp nhận',exact:true}).waitFor();
    });
    await scenario('dashboard takeover and resolve refresh state',async page=>{
      const actions=await dashboard(page);
      await page.getByRole('button',{name:'Người tiếp nhận',exact:true}).click();
      await page.getByRole('button',{name:'Giao lại bot',exact:true}).click();
      await page.getByRole('button',{name:'Người tiếp nhận',exact:true}).waitFor();
      assert.deepEqual(actions,['escalated','open']);
    });
    await scenario('dashboard auto refresh can be disabled',async page=>{
      let leadRequests=0;
      await dashboard(page,{keepAuto:true,onRequest:endpoint=>{if(endpoint==='/leads')leadRequests++;}});
      await page.getByRole('heading',{name:'Leads (1)',exact:true}).waitFor();
      const initial=leadRequests;
      await page.waitForResponse(response=>new URL(response.url()).searchParams.get('path')==='/leads' && leadRequests>initial,{timeout:12000});
      await page.getByRole('checkbox').uncheck();
      const stopped=leadRequests;
      await page.waitForTimeout(7500);
      assert.equal(leadRequests,stopped);
    });
    await scenario('dashboard unauthorized error removes owner token',async page=>{
      await dashboard(page,{unauthorized:true});
      await page.locator('.error-note').filter({hasText:'Owner token không hợp lệ'}).waitFor();
      assert.equal(await page.evaluate(()=>localStorage.getItem('salepilot_owner_token')),null);
    });
    console.log(`PASS ${passed} browser scenarios`);
  } finally {
    if(browser) await browser.close();
    if(server.exitCode===null) { server.kill(); await once(server,'exit'); }
  }
}
main().catch(error=>{console.error(error);process.exitCode=1;});
