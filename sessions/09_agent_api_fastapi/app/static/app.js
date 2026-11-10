// Demo UI for the Research Brief Agent API.
// The browser's EventSource only sends GET and cannot set an Authorization header, so each run is read with
// fetch() + ReadableStream and the text/event-stream body is parsed here (event / data / id, blank line = end).
const $ = (id) => document.getElementById(id);
const state = { token: sessionStorage.getItem("token") || "", user: null, threadId: null, busy: false, mode: "signin" };

// ── HTTP ──────────────────────────────────────────────────────────────────
async function api(path, options = {}) {
  const res = await fetch(path, { ...options, headers: { Authorization: `Bearer ${state.token}`,
    "Content-Type": "application/json", ...(options.headers || {}) } });
  if (res.status === 401 && path !== "/auth/token") { signOut("Your session expired. Please sign in again."); }
  if (!res.ok) {  // every error body is application/problem+json: {title, status, detail}
    const p = await res.json().catch(() => ({ title: res.statusText, detail: "" }));
    const detail = Array.isArray(p.errors) ? p.errors.map((e) => `${e.loc.at(-1)}: ${e.msg}`).join("; ") : p.detail;
    throw new Error(`${p.title}: ${detail}`);
  }
  return res;
}

async function* sseEvents(res) {
  const reader = res.body.pipeThrough(new TextDecoderStream()).getReader();
  let buffer = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) return;
    buffer = (buffer + value).replace(/\r\n?/g, "\n");
    let cut;
    while ((cut = buffer.indexOf("\n\n")) >= 0) {
      const block = buffer.slice(0, cut); buffer = buffer.slice(cut + 2);
      const ev = { event: "message", data: "" };
      for (const line of block.split("\n")) {
        if (!line || line.startsWith(":")) continue;  // ": ping" keep-alive comments
        const i = line.indexOf(":");
        const field = i < 0 ? line : line.slice(0, i), val = i < 0 ? "" : line.slice(i + 1).replace(/^ /, "");
        if (field === "data") ev.data += (ev.data ? "\n" : "") + val; else ev[field] = val;
      }
      if (ev.data) yield { event: ev.event, data: JSON.parse(ev.data) };
    }
  }
}

// ── Rendering (text is always escaped before the small Markdown subset is applied) ──
const el = (tag, cls, text) => { const e = document.createElement(tag); if (cls) e.className = cls;
  if (text !== undefined) e.textContent = text; return e; };
const esc = (s) => s.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
function markdown(src) {
  const inline = (s) => esc(s)
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>')
    .replace(/\[(https?:\/\/[^\]\s]+)\]/g, '[<a href="$1" target="_blank" rel="noopener">source</a>]');
  let html = "", list = false;
  for (const line of src.split("\n")) {
    const item = line.match(/^\s*[-*] (.*)$/);
    if (item) { if (!list) { html += "<ul>"; list = true; } html += `<li>${inline(item[1])}</li>`; continue; }
    if (list) { html += "</ul>"; list = false; }
    const head = line.match(/^#{1,3} (.*)$/);
    if (head) html += `<h3>${inline(head[1])}</h3>`;
    else if (line.trim()) html += `<p>${inline(line)}</p>`;
  }
  return html + (list ? "</ul>" : "");
}

const conversation = $("conversation");
const scroll = () => { conversation.scrollTop = conversation.scrollHeight; };
function showConversation() { $("empty").hidden = true; conversation.hidden = false; }
function userMessage(text) { showConversation(); conversation.append(el("div", "msg-user", text)); scroll(); }

// One agent turn: a collapsible activity log, the streamed answer, and an approval card when the run pauses.
function agentTurn() {
  const turn = el("div", "msg-agent");
  const activity = el("details", "activity"), summary = el("summary"), steps = el("ol");
  activity.append(summary, steps);
  const answer = el("div", "typing");
  turn.append(activity, answer);
  conversation.append(turn);
  let tools = 0, text = "";
  const t0 = performance.now();
  const setSummary = (label) => { summary.textContent = label; };
  setSummary("Working…");
  return {
    step(kind, detail) {
      const li = el("li"); li.append(el("span", "kind", kind), detail); steps.append(li);
      if (kind === "tool_call") tools += 1;
      setSummary(`Working… ${tools} tool call${tools === 1 ? "" : "s"}`); scroll();
    },
    token(t) { text += t; answer.innerHTML = markdown(text); answer.className = "typing"; scroll(); },
    finish(status) {
      answer.className = "";
      const secs = ((performance.now() - t0) / 1000).toFixed(0);
      setSummary(`${status === "interrupted" ? "Paused for approval" : "Done"} · ${tools} tool call${tools === 1 ? "" : "s"} · ${secs} s`);
      if (!text && !tools) turn.remove();
    },
    error(message) { answer.className = ""; turn.append(el("div", "notice error", message)); },
  };
}

function approvalCard(data) {
  const action = data.action_requests[0];
  const card = el("div", "approval");
  const header = el("header"); header.append("Approve ", el("code", "", action.name), "?");
  const reason = el("input"); reason.placeholder = "Reason (sent to the agent if you reject)";
  const approve = el("button", "primary", "Approve"), reject = el("button", "secondary", "Reject");
  const decide = (body) => { card.remove(); stream(`/threads/${state.threadId}/resume`, body); };
  approve.onclick = () => decide({ decision: "approve" });
  reject.onclick = () => decide({ decision: "reject", message: reason.value || null });
  const actions = el("div", "actions"); actions.append(approve, reject, reason);
  card.append(header, el("div", "title", action.args.title || ""),
    el("pre", "", action.args.content || JSON.stringify(action.args, null, 2)), actions);
  conversation.append(card); scroll();
}

// ── One run: map each SSE event to the UI ─────────────────────────────────────
async function stream(path, body) {
  setBusy(true);
  const turn = agentTurn();
  try {
    const res = await api(path, { method: "POST", body: JSON.stringify(body) });  // 401/404/409/422 fail here
    for await (const { event, data } of sseEvents(res)) {
      if (event === "token") turn.token(data.text);
      else if (event === "tool_call") turn.step("tool_call", `${data.name}(${JSON.stringify(data.args).slice(0, 90)})`);
      else if (event === "progress") turn.step("progress", `${data.stage}: ${data.query}`);
      else if (event === "tool_result") turn.step("tool_result", `${data.name} → ${data.status}`);
      else if (event === "interrupt") { turn.finish("interrupted"); approvalCard(data); }
      else if (event === "done") turn.finish(data.status);
      else if (event === "error") turn.error(`${data.title}: ${data.detail}`);
    }
  } catch (err) { turn.error(err.message); }
  setBusy(false); loadThreads();
}

// ── Threads and session ───────────────────────────────────────────────────────
function setBusy(on) { state.busy = on; $("send").disabled = on || !$("input").value.trim(); }

async function loadThreads() {
  const threads = await (await api("/threads")).json();
  const nav = $("threads"); nav.replaceChildren();
  for (const t of threads) {
    const b = el("button", `thread${t.thread_id === state.threadId ? " active" : ""}`, t.title);
    if (t.status === "interrupted") b.append(el("span", "badge", "● needs approval"));
    b.onclick = () => openThread(t.thread_id);
    nav.append(b);
  }
}

async function openThread(id) {
  state.threadId = id; conversation.replaceChildren();
  const t = await (await api(`/threads/${id}`)).json();
  showConversation();
  for (const m of t.messages) {
    if (m.role === "user") conversation.append(el("div", "msg-user", m.content));
    else if (m.role === "assistant" && m.content) {
      const div = el("div", "msg-agent"); div.innerHTML = markdown(m.content); conversation.append(div);
    }
  }
  if (t.interrupt) approvalCard(t.interrupt);
  scroll(); loadThreads();
}

function newBrief() {
  state.threadId = null; conversation.replaceChildren(); conversation.hidden = true; $("empty").hidden = false;
  loadThreads(); $("input").focus();
}

async function send(text) {
  setBusy(true);  // before the first await: a second Enter must not start a second run
  userMessage(text);
  try {
    if (!state.threadId) state.threadId = (await (await api("/threads", { method: "POST" })).json()).thread_id;
  } catch (err) { conversation.append(el("div", "notice error", err.message)); setBusy(false); return; }
  await stream(`/threads/${state.threadId}/runs`, { message: text });
}

// ── Sign in / create account ──────────────────────────────────────────────────
function setMode(mode) {
  state.mode = mode;
  $("tab-signin").classList.toggle("active", mode === "signin");
  $("tab-signup").classList.toggle("active", mode === "signup");
  $("name").hidden = mode !== "signup"; $("name").required = mode === "signup";
  $("auth-submit").textContent = mode === "signup" ? "Create account" : "Sign in";
  $("password").autocomplete = mode === "signup" ? "new-password" : "current-password";
  $("signin-error").textContent = "";
}

async function login(username, password) {
  // OAuth2 password flow: form fields, not JSON
  const res = await fetch("/auth/token", { method: "POST", body: new URLSearchParams({ username, password }) });
  const body = await res.json();
  if (!res.ok) throw new Error(body.detail);
  return body.access_token;
}

async function submitAuth(e) {
  e.preventDefault();
  const username = $("username").value.trim().toLowerCase(), password = $("password").value;
  try {
    if (state.mode === "signup") {
      const res = await fetch("/auth/signup", { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password, name: $("name").value.trim() }) });
      if (!res.ok) {
        const p = await res.json();
        throw new Error(Array.isArray(p.errors) ? p.errors.map((x) => `${x.loc.at(-1)}: ${x.msg}`).join("; ") : p.detail);
      }
    }
    await enter(await login(username, password));
  } catch (err) { $("signin-error").textContent = err.message; }
}

async function enter(token) {
  state.token = token;
  state.user = await (await api("/auth/me")).json();
  sessionStorage.setItem("token", token);
  $("signin").hidden = true; $("app").hidden = false;
  $("who").textContent = state.user.name; $("avatar").textContent = state.user.name[0].toUpperCase();
  $("greeting").textContent = `Good to see you, ${state.user.name}`;
  newBrief();
}

function signOut(message = "") {
  sessionStorage.removeItem("token"); state.token = ""; state.user = null;
  $("app").hidden = true; $("signin").hidden = false; $("signin-error").textContent = message;
  $("password").value = "";
}

$("tab-signin").onclick = () => setMode("signin");
$("tab-signup").onclick = () => setMode("signup");
$("auth-form").onsubmit = submitAuth;
$("signout").onclick = () => signOut();
$("new").onclick = newBrief;
// Vietnamese Telex (and CJK) input methods compose a word before committing it. Enter must wait for that commit,
// otherwise the message is sent without it and the input method writes the word back into the cleared box.
const input = $("input");
let composing = false, sendAfterComposition = false;
input.addEventListener("compositionstart", () => { composing = true; });
input.addEventListener("compositionend", () => {
  composing = false;
  if (sendAfterComposition) { sendAfterComposition = false; setTimeout(submitInput, 0); }
});
input.oninput = () => {
  input.style.height = "auto"; input.style.height = `${input.scrollHeight}px`; setBusy(state.busy);
};
input.onkeydown = (e) => {
  const enter = e.key === "Enter" || e.code === "Enter" || e.code === "NumpadEnter";
  if (!enter || e.shiftKey) return;
  e.preventDefault();
  if (composing || e.isComposing || e.keyCode === 229) {  // send on compositionend
    sendAfterComposition = true;
    setTimeout(() => {  // some input methods never end the composition on Enter: blur commits the word
      if (!sendAfterComposition) return;
      input.blur(); input.focus();
      setTimeout(() => { if (sendAfterComposition) { sendAfterComposition = false; composing = false; submitInput(); } }, 0);
    }, 300);
    return;
  }
  setTimeout(submitInput, 0);  // next tick: a late commit from the input method lands in the box first
};
$("composer").onsubmit = (e) => { e.preventDefault(); submitInput(); };

function submitInput() {
  if (composing) { sendAfterComposition = true; input.blur(); input.focus(); return; }  // blur commits the word
  const text = input.value.trim();
  if (!text || state.busy) return;
  input.value = ""; input.style.height = "auto"; send(text);
}
if (state.token) enter(state.token).catch(() => signOut());
