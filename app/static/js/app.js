const chatWindow = document.getElementById("chatWindow");
const messageInput = document.getElementById("messageInput");
const sendBtn = document.getElementById("sendBtn");
const clearHistoryBtn = document.getElementById("clearHistoryBtn");
const statusBar = document.getElementById("statusBar");
const streamToggle = document.getElementById("streamToggle");

const sessionStorageKey = "imageagent_session_id";
let sessionId = localStorage.getItem(sessionStorageKey);
if (!sessionId) {
  sessionId = crypto.randomUUID();
  localStorage.setItem(sessionStorageKey, sessionId);
}

function setStatus(text = "") {
  statusBar.textContent = text;
}

function scrollToBottom() {
  chatWindow.scrollTop = chatWindow.scrollHeight;
}

function formatDate(isoValue) {
  try {
    return new Date(isoValue).toLocaleTimeString();
  } catch {
    return "";
  }
}

function createMessageElement({ role, content, createdAt, isError = false, image }) {
  const wrapper = document.createElement("article");
  wrapper.className = `message ${role === "user" ? "user" : "assistant"}${isError ? " error" : ""}`;

  const meta = document.createElement("div");
  meta.className = "meta";
  meta.textContent = `${role === "user" ? "Te" : "Assistant"} • ${formatDate(createdAt)}`;
  wrapper.appendChild(meta);

  const body = document.createElement("div");
  body.className = "content";
  body.textContent = content || "";
  wrapper.appendChild(body);

  if (image && image.image_url) {
    const img = document.createElement("img");
    img.className = "preview";
    img.src = image.image_url;
    img.alt = "Generated image preview";
    wrapper.appendChild(img);

    const link = document.createElement("a");
    link.className = "image-link";
    link.href = image.image_url;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    link.textContent = "Kép megnyitása külön";
    wrapper.appendChild(link);
  }

  return wrapper;
}

function addMessage(payload) {
  const element = createMessageElement(payload);
  chatWindow.appendChild(element);
  scrollToBottom();
  return element;
}

function addLoadingMessage() {
  const loading = document.createElement("article");
  loading.className = "message assistant";
  loading.innerHTML = `
    <div class="meta">Assistant</div>
    <div class="content loading-dots">Dolgozom<span>.</span><span>.</span><span>.</span></div>
  `;
  chatWindow.appendChild(loading);
  scrollToBottom();
  return loading;
}

async function loadHistory() {
  try {
    const response = await fetch(`/api/history?session_id=${encodeURIComponent(sessionId)}`);
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || "History lekérés sikertelen.");
    }
    chatWindow.innerHTML = "";
    for (const message of data.messages || []) {
      addMessage({
        role: message.role,
        content: message.content,
        createdAt: message.created_at,
        image: message.metadata ? { image_url: message.metadata.image_url } : null,
      });
    }
  } catch (error) {
    addMessage({
      role: "assistant",
      content: `Hiba a history betöltésekor: ${error.message}`,
      createdAt: new Date().toISOString(),
      isError: true,
    });
  }
}

async function sendMessage() {
  const message = messageInput.value.trim();
  if (!message) {
    return;
  }

  messageInput.value = "";
  addMessage({ role: "user", content: message, createdAt: new Date().toISOString() });
  const loadingNode = addLoadingMessage();
  setStatus("Kérés fut...");
  sendBtn.disabled = true;

  try {
    if (streamToggle.checked) {
      await sendStreaming(message, loadingNode);
    } else {
      await sendClassic(message, loadingNode);
    }
    setStatus("");
  } catch (error) {
    loadingNode.remove();
    addMessage({
      role: "assistant",
      content: `Hiba: ${error.message}`,
      createdAt: new Date().toISOString(),
      isError: true,
    });
    setStatus("Hiba történt.");
  } finally {
    sendBtn.disabled = false;
    messageInput.focus();
  }
}

async function sendClassic(message, loadingNode) {
  const response = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, session_id: sessionId, stream: false }),
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || data.detail || "Szerverhiba.");
  }
  loadingNode.remove();
  addMessage({
    role: "assistant",
    content: data.message,
    createdAt: data.created_at,
    image: data.image,
  });
}

async function sendStreaming(message, loadingNode) {
  const response = await fetch("/api/chat/stream", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, session_id: sessionId, stream: true }),
  });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.error || data.detail || "Streaming hívás sikertelen.");
  }
  if (!response.body) {
    throw new Error("A böngésző nem támogatja a streaminget ebben a módban.");
  }

  const assistantMessage = addMessage({
    role: "assistant",
    content: "",
    createdAt: new Date().toISOString(),
  });
  loadingNode.remove();

  const contentNode = assistantMessage.querySelector(".content");
  let renderedText = "";
  let finalImage = null;

  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";
  let activeEvent = "message";

  while (true) {
    const { done, value } = await reader.read();
    if (done) {
      break;
    }
    buffer += decoder.decode(value, { stream: true });
    const blocks = buffer.split("\n\n");
    buffer = blocks.pop() || "";

    for (const rawBlock of blocks) {
      const lines = rawBlock.split("\n");
      let dataText = "";
      for (const line of lines) {
        if (line.startsWith("event:")) {
          activeEvent = line.replace("event:", "").trim();
        } else if (line.startsWith("data:")) {
          dataText += line.replace("data:", "").trim();
        }
      }

      if (!dataText) {
        continue;
      }

      const payload = JSON.parse(dataText);
      if (activeEvent === "token") {
        renderedText += payload.content || "";
        contentNode.textContent = renderedText;
      }
      if (activeEvent === "done") {
        if (payload.message) {
          renderedText = payload.message;
          contentNode.textContent = renderedText;
        }
        finalImage = payload.image || null;
      }
      if (activeEvent === "error") {
        throw new Error(payload.error || "Streaming hiba.");
      }
    }
  }

  if (finalImage && finalImage.image_url) {
    const img = document.createElement("img");
    img.className = "preview";
    img.src = finalImage.image_url;
    assistantMessage.appendChild(img);

    const link = document.createElement("a");
    link.className = "image-link";
    link.href = finalImage.image_url;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    link.textContent = "Kép megnyitása külön";
    assistantMessage.appendChild(link);
  }
}

async function clearHistory() {
  try {
    const response = await fetch(`/api/history?session_id=${encodeURIComponent(sessionId)}`, {
      method: "DELETE",
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || "History törlés sikertelen.");
    }
    chatWindow.innerHTML = "";
    setStatus("History törölve.");
  } catch (error) {
    setStatus(`Hiba: ${error.message}`);
  }
}

sendBtn.addEventListener("click", sendMessage);
messageInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    sendMessage();
  }
});
clearHistoryBtn.addEventListener("click", clearHistory);

loadHistory().then(() => {
  if (chatWindow.children.length === 0) {
    addMessage({
      role: "assistant",
      content:
        "Szia! Kérdezhetsz általános dolgokat, programozási feladatokat, vagy kérhetsz képgenerálást is.",
      createdAt: new Date().toISOString(),
    });
  }
});

