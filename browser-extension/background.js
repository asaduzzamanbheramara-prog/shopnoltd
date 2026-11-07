// Service worker: keeps a WebSocket to the agent service and executes browser commands.
const AGENT_WS = "wss://agent.shopnoltd.dpdns.org/ws/ext";  // change to your deployed URL
let ws = null;

function connect(token) {
  if (ws) ws.close();
  ws = new WebSocket(`${AGENT_WS}?token=${encodeURIComponent(token)}`);
  ws.onmessage = async (e) => {
    const cmd = JSON.parse(e.data);
    let out;
    try { out = { id: cmd.id, ok: true, ...(await run(cmd)) }; }
    catch (err) { out = { id: cmd.id, ok: false, error: String(err) }; }
    ws.send(JSON.stringify(out));
  };
  ws.onclose = () => { ws = null; };
  // keep the service worker alive while connected
  setInterval(() => ws && ws.readyState === 1 && ws.send(JSON.stringify({ ping: 1 })), 20000);
}

async function activeTab() {
  const [t] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!t) throw new Error("no active tab");
  return t;
}

async function inPage(tabId, fn, args) {
  const [r] = await chrome.scripting.executeScript({ target: { tabId }, func: fn, args });
  return r.result;
}

async function run(cmd) {
  if (cmd.action === "open") {
    const t = await chrome.tabs.create({ url: cmd.url });
    return { tabId: t.id };
  }
  const tab = await activeTab();
  switch (cmd.action) {
    case "get_text":
      return { url: tab.url, text: (await inPage(tab.id, () => document.body.innerText.slice(0, 20000), [])) };
    case "click":
      return { clicked: await inPage(tab.id, (sel) => { const el = document.querySelector(sel); if (!el) return false; el.click(); return true; }, [cmd.selector]) };
    case "type":
      return { typed: await inPage(tab.id, (sel, txt) => { const el = document.querySelector(sel); if (!el) return false; el.focus(); el.value = txt; el.dispatchEvent(new Event("input", { bubbles: true })); return true; }, [cmd.selector, cmd.text]) };
    case "scroll":
      await inPage(tab.id, () => window.scrollBy(0, window.innerHeight * 0.8), []);
      return { scrolled: true };
    case "screenshot":
      return { image: await chrome.tabs.captureVisibleTab(null, { format: "jpeg", quality: 60 }) };
    default:
      throw new Error("unknown action");
  }
}

chrome.runtime.onMessage.addListener((m, _s, reply) => {
  if (m.type === "connect") { connect(m.token); reply({ status: "connecting" }); }
  else if (m.type === "disconnect") { ws && ws.close(); reply({ status: "disconnected" }); }
  else if (m.type === "status") reply({ status: ws && ws.readyState === 1 ? "connected" : "disconnected" });
  return true;
});
