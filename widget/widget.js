(function () {
  "use strict";

  // ── Config from script tag ──────────────────────────────
  var script = document.currentScript;
  var botId = script.getAttribute("data-bot-id");
  var apiBase = script.getAttribute("data-api") || "https://api.yourdomain.com";

  if (!botId) {
    console.error("[Johal] Missing data-bot-id attribute.");
    return;
  }

  // ── State ───────────────────────────────────────────────
  var sessionId = "session_" + Math.random().toString(36).substr(2, 12);
  var isOpen = false;
  var isTyping = false;

  // ── Styles ──────────────────────────────────────────────
  var style = document.createElement("style");
  style.textContent = [
    "#jh-bubble{position:fixed;bottom:20px;right:20px;width:56px;height:56px;",
    "background:#5B21B6;border-radius:50%;cursor:pointer;z-index:999999;",
    "display:flex;align-items:center;justify-content:center;",
    "box-shadow:0 4px 20px rgba(91,33,182,.4);transition:transform .2s;}",
    "#jh-bubble:hover{transform:scale(1.08);}",
    "#jh-bubble svg{width:24px;height:24px;fill:white;}",
    "#jh-panel{position:fixed;bottom:88px;right:20px;width:360px;height:520px;",
    "border-radius:16px;background:#fff;z-index:999998;display:none;",
    "flex-direction:column;overflow:hidden;",
    "box-shadow:0 8px 40px rgba(0,0,0,.18);font-family:sans-serif;}",
    "#jh-panel.open{display:flex;}",
    "#jh-header{background:#5B21B6;color:#fff;padding:16px 18px;",
    "display:flex;align-items:center;gap:10px;flex-shrink:0;}",
    "#jh-header-avatar{width:36px;height:36px;border-radius:50%;",
    "background:rgba(255,255,255,.25);display:flex;align-items:center;",
    "justify-content:center;font-size:18px;}",
    "#jh-header-title{font-weight:600;font-size:15px;}",
    "#jh-header-sub{font-size:12px;opacity:.8;}",
    "#jh-messages{flex:1;overflow-y:auto;padding:14px;",
    "display:flex;flex-direction:column;gap:10px;}",
    ".jh-msg{max-width:80%;padding:10px 14px;border-radius:14px;",
    "font-size:14px;line-height:1.5;word-break:break-word;}",
    ".jh-msg.user{align-self:flex-end;background:#5B21B6;color:#fff;",
    "border-bottom-right-radius:4px;}",
    ".jh-msg.bot{align-self:flex-start;background:#F3F4F6;color:#111;",
    "border-bottom-left-radius:4px;}",
    ".jh-msg.bot.typing{opacity:.6;}",
    "#jh-predefined{display:flex;flex-wrap:wrap;gap:6px;padding:0 14px 10px;}",
    ".jh-predef-btn{background:#EDE9FE;color:#5B21B6;border:none;",
    "border-radius:20px;padding:6px 12px;font-size:12px;cursor:pointer;}",
    ".jh-predef-btn:hover{background:#DDD6FE;}",
    "#jh-input-area{display:flex;gap:8px;padding:12px 14px;",
    "border-top:1px solid #E5E7EB;flex-shrink:0;}",
    "#jh-input{flex:1;border:1px solid #D1D5DB;border-radius:22px;",
    "padding:9px 14px;font-size:14px;outline:none;resize:none;}",
    "#jh-input:focus{border-color:#5B21B6;}",
    "#jh-send{background:#5B21B6;color:#fff;border:none;border-radius:50%;",
    "width:38px;height:38px;cursor:pointer;display:flex;",
    "align-items:center;justify-content:center;flex-shrink:0;}",
    "#jh-send:hover{background:#4C1D95;}",
    "#jh-send svg{width:16px;height:16px;fill:white;}",
  ].join("");
  document.head.appendChild(style);

  // ── HTML ─────────────────────────────────────────────────
  var container = document.createElement("div");
  container.innerHTML = [
    '<div id="jh-bubble">',
    '<svg viewBox="0 0 24 24"><path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2z"/></svg>',
    "</div>",
    '<div id="jh-panel">',
    '<div id="jh-header">',
    '<div id="jh-header-avatar">🤖</div>',
    '<div><div id="jh-header-title">Chat with us</div>',
    '<div id="jh-header-sub">We reply instantly</div></div>',
    "</div>",
    '<div id="jh-messages"></div>',
    '<div id="jh-predefined"></div>',
    '<div id="jh-input-area">',
    '<input id="jh-input" placeholder="Type a message..." autocomplete="off" />',
    '<button id="jh-send"><svg viewBox="0 0 24 24"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg></button>',
    "</div>",
    "</div>",
  ].join("");
  document.body.appendChild(container);

  // ── DOM refs ─────────────────────────────────────────────
  var bubble = document.getElementById("jh-bubble");
  var panel = document.getElementById("jh-panel");
  var messages = document.getElementById("jh-messages");
  var input = document.getElementById("jh-input");
  var sendBtn = document.getElementById("jh-send");
  var predefined = document.getElementById("jh-predefined");

  // ── Toggle panel ─────────────────────────────────────────
  bubble.addEventListener("click", function () {
    isOpen = !isOpen;
    panel.classList.toggle("open", isOpen);
    if (isOpen && messages.children.length === 0) {
      addMessage("Hi! How can I help you today?", "bot");
      loadConfig();
    }
    if (isOpen) input.focus();
  });

  // ── Add message to UI ────────────────────────────────────
  function addMessage(text, role) {
    var div = document.createElement("div");
    div.className = "jh-msg " + role;
    div.textContent = text;
    messages.appendChild(div);
    messages.scrollTop = messages.scrollHeight;
    return div;
  }

  // ── Typing indicator ─────────────────────────────────────
  var typingEl = null;
  function showTyping() {
    typingEl = addMessage("...", "bot typing");
  }
  function hideTyping() {
    if (typingEl && typingEl.parentNode) {
      typingEl.parentNode.removeChild(typingEl);
      typingEl = null;
    }
  }

  // ── Send message ─────────────────────────────────────────
  function sendMessage(text) {
    text = (text || input.value || "").trim();
    if (!text || isTyping) return;
    input.value = "";
    addMessage(text, "user");
    isTyping = true;
    showTyping();

    fetch(apiBase + "/api/chat/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        bot_id: botId,
        session_id: sessionId,
        message: text,
      }),
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        hideTyping();
        isTyping = false;
        if (data.handoff) {
          addMessage("You've been connected to a human agent. Please wait...", "bot");
        } else if (data.reply) {
          addMessage(data.reply, "bot");
        }
        if (data.session_id) sessionId = data.session_id;
      })
      .catch(function () {
        hideTyping();
        isTyping = false;
        addMessage("Something went wrong. Please try again.", "bot");
      });
  }

  sendBtn.addEventListener("click", function () { sendMessage(); });
  input.addEventListener("keydown", function (e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  // ── Load bot config (header text, predefined questions) ──
  function loadConfig() {
    fetch(apiBase + "/api/bots/public/" + botId + "/config/")
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data.header_text) {
          document.getElementById("jh-header-title").textContent = data.header_text;
        }
        if (data.welcome_message) {
          if (messages.children.length === 1) {
            messages.children[0].textContent = data.welcome_message;
          }
        }
        if (data.theme_color) {
          style.textContent = style.textContent.replace(/#5B21B6/g, data.theme_color);
          style.textContent = style.textContent.replace(/#4C1D95/g, data.theme_color);
          style.textContent = style.textContent.replace(/#EDE9FE/g, data.theme_color + "22");
        }
        if (data.predefined_questions && data.predefined_questions.length) {
          predefined.innerHTML = "";
          data.predefined_questions.forEach(function (q) {
            var btn = document.createElement("button");
            btn.className = "jh-predef-btn";
            btn.textContent = q;
            btn.addEventListener("click", function () {
              predefined.style.display = "none";
              sendMessage(q);
            });
            predefined.appendChild(btn);
          });
        }
      })
      .catch(function () {});
  }
})();
