const API = "http://localhost:8000";
let currentChatId = null;

let chatEl;
let welcomeCard;
let messageInput;
let sendBtn;
let statusPill;
let chatTitle;
let chatSubtitle;
let chunkList;
let chunksMeta;
let chatListEl;
let newChatBtn;
let ingestBtn;
let tablesBtn;

document.addEventListener("DOMContentLoaded", () => {
  chatEl = document.getElementById("chat");
  welcomeCard = document.getElementById("welcomeCard");
  messageInput = document.getElementById("messageInput");
  sendBtn = document.getElementById("sendBtn");
  statusPill = document.getElementById("statusPill");
  chatTitle = document.getElementById("chatTitle");
  chatSubtitle = document.getElementById("chatSubtitle");
  chunkList = document.getElementById("chunkList");
  chunksMeta = document.getElementById("chunksMeta");
  chatListEl = document.getElementById("chatList");
  newChatBtn = document.getElementById("newChatBtn");
  ingestBtn = document.getElementById("ingestBtn");
  tablesBtn = document.getElementById("tablesBtn");

  newChatBtn.addEventListener("click", newChat);
  sendBtn.addEventListener("click", sendMessage);
  ingestBtn.addEventListener("click", ingest);
  tablesBtn.addEventListener("click", loadTables);

  messageInput.addEventListener("input", autoResizeTextarea);
  messageInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  loadChats();
});

function setStatus(text, type = "ready") {
  statusPill.innerText = text;
  statusPill.classList.remove("loading", "error");

  if (type === "loading") {
    statusPill.classList.add("loading");
  } else if (type === "error") {
    statusPill.classList.add("error");
  }
}

function clearWelcome() {
  const existingWelcome = document.getElementById("welcomeCard");
  if (existingWelcome) {
    existingWelcome.remove();
  }
}

function addMessage(text, role) {
  clearWelcome();

  const row = document.createElement("div");
  row.className = `message-row ${role === "user" ? "user-row" : "assistant-row"}`;

  const div = document.createElement("div");
  div.className = `message ${role}`;
  if (role === "assistant") {
    div.innerHTML = marked.parse(text);
  } else {
    div.innerText = text;
  }

  row.appendChild(div);
  chatEl.appendChild(row);
  row.scrollIntoView({ behavior: "instant", block: "end" });
}

function showEmptyList(container, text) {
  container.innerHTML = `<div class="empty-state">${text}</div>`;
}

function autoResizeTextarea() {
  messageInput.style.height = "auto";
  messageInput.style.height = `${Math.min(messageInput.scrollHeight, 160)}px`;
}

function renderChunks(chunks = []) {
  if (!chunks.length) {
    chunksMeta.innerText = "No chunks returned";
    showEmptyList(chunkList, "No retrieved chunks for this response.");
    return;
  }

  chunksMeta.innerText = `${chunks.length} chunk${chunks.length === 1 ? "" : "s"} returned`;
  chunkList.innerHTML = "";

  chunks.forEach((c, i) => {
    const card = document.createElement("div");
    card.className = "chunk-card";

    const label = document.createElement("small");
    label.innerText = `Chunk ${i + 1}`;

    const content = document.createElement("div");
    content.innerText = c.content || "(empty chunk)";

    card.appendChild(label);
    card.appendChild(content);
    chunkList.appendChild(card);
  });
}

// ---------------- CHAT ----------------

async function newChat() {
  try {
    setStatus("Creating chat...", "loading");

    const res = await fetch(`${API}/chats`, {
      method: "POST"
    });

    const data = await res.json();

    currentChatId = data.chat_id;
    chatTitle.innerText = "Conversation";
    chatSubtitle.innerText = `Chat ${currentChatId}`;
    chatEl.innerHTML = `
      <div class="welcome-card" id="welcomeCard">
        <h3>New chat created</h3>
        <p>Your conversation is ready. Ask a question to begin retrieving relevant context.</p>
      </div>
    `;

    renderChunks([]);
    await loadChats();
    setStatus("Ready");
  } catch (err) {
    console.error(err);
    setStatus("Error", "error");
    alert("Failed to create a new chat.");
  }
}

async function loadChats() {
  try {
    const res = await fetch(`${API}/chats`);
    const chats = await res.json();

    chatListEl.innerHTML = "";

    if (!chats.length) {
      showEmptyList(chatListEl, "No chats yet.");
      return;
    }

    chats.forEach((c) => {
      const btn = document.createElement("button");
      btn.className = "list-btn";
      btn.innerHTML = `
        <span>Chat ${c.chat_id}</span>
        <small>${currentChatId === c.chat_id ? "Open" : "View"}</small>
      `;
      btn.addEventListener("click", () => loadChatHistory(c.chat_id));
      chatListEl.appendChild(btn);
    });
  } catch (err) {
    console.error(err);
    showEmptyList(chatListEl, "Could not load chats.");
  }
}

async function loadChatHistory(chatId) {
  try {
    setStatus("Loading chat...", "loading");
    currentChatId = chatId;

    const res = await fetch(`${API}/chats/${chatId}`);
    const data = await res.json();

    chatEl.innerHTML = "";
    chatTitle.innerText = "Conversation";
    chatSubtitle.innerText = `Chat ${chatId}`;

    if (!data.messages || !data.messages.length) {
      chatEl.innerHTML = `
        <div class="welcome-card" id="welcomeCard">
          <h3>Empty conversation</h3>
          <p>This chat has no messages yet.</p>
        </div>
      `;
    } else {
      data.messages.forEach((m) => addMessage(m.content, m.role));
    }

    renderChunks([]);
    await loadChats();
    setStatus("Ready");
  } catch (err) {
    console.error(err);
    setStatus("Error", "error");
    alert("Failed to load chat history.");
  }
}

async function sendMessage() {
  const text = messageInput.value.trim();
  if (!text) return;

  try {
    sendBtn.disabled = true;
    setStatus("Thinking...", "loading");

    addMessage(text, "user");
    messageInput.value = "";
    autoResizeTextarea();

    const res = await fetch(`${API}/chat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        chat_id: currentChatId,
        message: text,
        top_k: 5,
        temperature: 0.7
      })
    });

    const data = await res.json();

    addMessage(data.answer || "No response received.", "assistant");
    renderChunks(data.retrieved_chunks || []);
    await loadChats();
    setStatus("Ready");
  } catch (err) {
    console.error(err);
    setStatus("Error", "error");
    addMessage("Something went wrong while contacting the backend.", "assistant");
  } finally {
    sendBtn.disabled = false;
  }
}

// ---------------- ADMIN ----------------

async function ingest() {
  try {
    setStatus("Running ingest...", "loading");

    const res = await fetch(`${API}/ingest`, {
      method: "POST"
    });

    const data = await res.json();
    alert(data.status || "Ingest complete.");
    await loadDocuments();
    setStatus("Ready");
  } catch (err) {
    console.error(err);
    setStatus("Error", "error");
    alert("Failed to run ingest.");
  }
}

async function loadTables() {
  try {
    setStatus("Loading tables...", "loading");

    const res = await fetch(`${API}/tables`);
    const data = await res.json();

    chatTitle.innerText = "Database Tables";
    chatSubtitle.innerText = "Schema overview";

    chatEl.innerHTML = `
      <div class="welcome-card">
        <h3>Tables loaded</h3>
        <p>See browser console for the full schema payload.</p>
      </div>
    `;

    console.log("Tables:", data);
    renderChunks([]);
    setStatus("Ready");
  } catch (err) {
    console.error(err);
    setStatus("Error", "error");
    alert("Failed to load tables.");
  }
}