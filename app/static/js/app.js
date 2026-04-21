const chatWindow = document.getElementById("chatWindow");
const messageInput = document.getElementById("messageInput");
const sendBtn = document.getElementById("sendBtn");
const clearHistoryBtn = document.getElementById("clearHistoryBtn");
const statusBar = document.getElementById("statusBar");
const streamToggle = document.getElementById("streamToggle");
const statMessages = document.getElementById("statMessages");
const statImages = document.getElementById("statImages");
const sessionBadge = document.getElementById("sessionBadge");
const promptChips = document.querySelectorAll(".prompt-chip");
const lastImageWrap = document.getElementById("lastImageWrap");

const imageModal = document.getElementById("imageModal");
const imageModalImg = document.getElementById("imageModalImg");
const imageModalLink = document.getElementById("imageModalLink");
const imageModalClose = document.getElementById("imageModalClose");

const sessionStorageKey = "frankai_session_id";
let sessionId = localStorage.getItem(sessionStorageKey);
let totalMessages = 0;
let totalImages = 0;

if (!sessionId) {
  sessionId = crypto.randomUUID();
  localStorage.setItem(sessionStorageKey, sessionId);
}
sessionBadge.textContent = sessionId;

function setStatus(text = "") {
  statusBar.textContent = text;
}

function scrollToBottom() {
  chatWindow.scrollTop = chatWindow.scrollHeight;
}

function autosizeInput() {
  messageInput.style.height = "auto";
  messageInput.style.height = `${Math.min(messageInput.scrollHeight, 220)}px`;
}

function formatDate(isoValue) {
  try {
    return new Date(isoValue).toLocaleTimeString();
  } catch {
    return "";
  }
}

function prettifyTaskType(taskType) {
  if (!taskType) {
    return "";
  }
  return String(taskType).toLowerCase();
}

function updateStats() {
  statMessages.textContent = String(totalMessages);
  statImages.textContent = String(totalImages);
}

function setLastImage(imageUrl) {
  if (!imageUrl) {
    return;
  }
  lastImageWrap.classList.remove("empty");
  lastImageWrap.innerHTML = "";
  const image = document.createElement("img");
  image.src = imageUrl;
  image.alt = "Last generated image";
  image.addEventListener("click", () => openImageModal(imageUrl));
  lastImageWrap.appendChild(image);
}

function openImageModal(url) {
  imageModalImg.src = url;
  imageModalLink.href = url;
  imageModal.hidden = false;
}

function closeImageModal() {
  imageModal.hidden = true;
  imageModalImg.src = "";
  imageModalLink.href = "#";
}

function createImageElements(image, onClickUrl) {
  const fragment = document.createDocumentFragment();
  const img = document.createElement("img");
  img.className = "preview";
  img.src = image.image_url;
  img.alt = "Generated image preview";
  img.addEventListener("click", () => openImageModal(onClickUrl || image.image_url));
  fragment.appendChild(img);

  const link = document.createElement("a");
  link.className = "image-link";
  link.href = image.image_url;
  link.target = "_blank";
  link.rel = "noopener noreferrer";
  link.textContent = "Open image in new tab";
  fragment.appendChild(link);
  return fragment;
}

function createMessageElement({
  role,
  content,
  createdAt,
  image,
  isError = false,
  taskType,
  routeReason,
}) {
  const row = document.createElement("article");
  const normalizedRole = role === "user" ? "user" : "assistant";
  row.className = `chat-row ${normalizedRole}${isError ? " error" : ""}`;

  const avatar = document.createElement("div");
  avatar.className = "avatar";
  avatar.textContent = normalizedRole === "user" ? "YOU" : "AI";
  row.appendChild(avatar);

  const card = document.createElement("div");
  card.className = "message-card";

  const head = document.createElement("div");
  head.className = "message-head";

  const sender = document.createElement("span");
  sender.className = "sender";
  sender.textContent = normalizedRole === "user" ? "You" : "FrankAI";
  head.appendChild(sender);

  const time = document.createElement("span");
  time.className = "time";
  time.textContent = formatDate(createdAt);
  head.appendChild(time);

  if (taskType && normalizedRole === "assistant") {
    const pill = document.createElement("span");
    pill.className = `route-pill ${prettifyTaskType(taskType)}`;
    pill.textContent = prettifyTaskType(taskType);
    head.appendChild(pill);
  }

  card.appendChild(head);

  const body = document.createElement("div");
  body.className = "content";
  body.textContent = content || "";
  card.appendChild(body);

  if (routeReason && normalizedRole === "assistant") {
    const reason = document.createElement("div");
    reason.className = "route-reason";
    reason.textContent = `Route: ${routeReason}`;
    card.appendChild(reason);
  }

  if (image && image.image_url) {
    card.appendChild(createImageElements(image, image.image_url));
  }

  row.appendChild(card);
  row._contentNode = body;
  row._cardNode = card;
  return row;
}

function addMessage(payload) {
  const element = createMessageElement(payload);
  chatWindow.appendChild(element);

  if (payload.role === "assistant" || payload.role === "user") {
    totalMessages += 1;
  }
  if (payload.image && payload.image.image_url) {
    totalImages += 1;
    setLastImage(payload.image.image_url);
  }
  updateStats();
  scrollToBottom();
  return element;
}

function addLoadingMessage() {
  return addMessage({
    role: "assistant",
    content: "Synthesizing response",
    createdAt: new Date().toISOString(),
    taskType: streamToggle.checked ? "stream" : "pending",
    routeReason: "",
  });
}

async function loadHistory() {
  try {
    const response = await fetch(`/api/history?session_id=${encodeURIComponent(sessionId)}`);
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || "Failed to load chat history.");
    }

    chatWindow.innerHTML = "";
    totalMessages = 0;
    totalImages = 0;
    let latestImage = null;

    for (const item of data.messages || []) {
      const imageUrl = item.metadata ? item.metadata.image_url : null;
      addMessage({
        role: item.role,
        content: item.content,
        createdAt: item.created_at,
        image: imageUrl ? { image_url: imageUrl } : null,
      });
      if (imageUrl) {
        latestImage = imageUrl;
      }
    }

    if (latestImage) {
      setLastImage(latestImage);
    }
  } catch (error) {
    addMessage({
      role: "assistant",
      content: `History load failed: ${error.message}`,
      createdAt: new Date().toISOString(),
      isError: true,
    });
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
    throw new Error(data.error || data.detail || "Server error.");
  }

  loadingNode.remove();
  if (totalMessages > 0) {
    totalMessages -= 1;
  }

  addMessage({
    role: "assistant",
    content: data.message,
    createdAt: data.created_at,
    image: data.image,
    taskType: data.task_type,
    routeReason: data.route_reason,
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
    throw new Error(data.error || data.detail || "Streaming request failed.");
  }
  if (!response.body) {
    throw new Error("Browser does not expose streaming body.");
  }

  const assistantNode = addMessage({
    role: "assistant",
    content: "",
    createdAt: new Date().toISOString(),
  });

  loadingNode.remove();
  if (totalMessages > 0) {
    totalMessages -= 1;
  }

  let renderedText = "";
  let finalImage = null;
  let finalTaskType = "";
  let finalRouteReason = "";
  const contentNode = assistantNode._contentNode;
  const head = assistantNode.querySelector(".message-head");

  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) {
      break;
    }

    buffer += decoder.decode(value, { stream: true });
    const chunks = buffer.split("\n\n");
    buffer = chunks.pop() || "";

    for (const block of chunks) {
      const lines = block.split("\n");
      let eventType = "message";
      const dataLines = [];

      for (const line of lines) {
        if (line.startsWith("event:")) {
          eventType = line.slice(6).trim();
        } else if (line.startsWith("data:")) {
          dataLines.push(line.slice(5).trim());
        }
      }

      if (!dataLines.length) {
        continue;
      }

      let payload;
      try {
        payload = JSON.parse(dataLines.join(""));
      } catch {
        continue;
      }

      if (eventType === "meta") {
        finalTaskType = payload.task_type || "";
        finalRouteReason = payload.route_reason || "";
        if (finalTaskType && head && !assistantNode.querySelector(".route-pill")) {
          const pill = document.createElement("span");
          pill.className = `route-pill ${prettifyTaskType(finalTaskType)}`;
          pill.textContent = prettifyTaskType(finalTaskType);
          head.appendChild(pill);
        }
      }

      if (eventType === "token") {
        renderedText += payload.content || "";
        contentNode.textContent = renderedText;
      }

      if (eventType === "done") {
        if (payload.message) {
          renderedText = payload.message;
          contentNode.textContent = renderedText;
        }
        finalImage = payload.image || null;
      }

      if (eventType === "error") {
        throw new Error(payload.error || "Streaming failed.");
      }
    }
  }

  if (finalRouteReason) {
    const reason = document.createElement("div");
    reason.className = "route-reason";
    reason.textContent = `Route: ${finalRouteReason}`;
    assistantNode._cardNode.appendChild(reason);
  }

  if (finalImage && finalImage.image_url) {
    assistantNode._cardNode.appendChild(createImageElements(finalImage, finalImage.image_url));
    totalImages += 1;
    setLastImage(finalImage.image_url);
    updateStats();
  }
}

async function sendMessage() {
  const message = messageInput.value.trim();
  if (!message) {
    return;
  }

  messageInput.value = "";
  autosizeInput();

  addMessage({
    role: "user",
    content: message,
    createdAt: new Date().toISOString(),
  });
  const loadingNode = addLoadingMessage();

  setStatus("Processing...");
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
    if (totalMessages > 0) {
      totalMessages -= 1;
    }
    updateStats();
    addMessage({
      role: "assistant",
      content: `Error: ${error.message}`,
      createdAt: new Date().toISOString(),
      isError: true,
    });
    setStatus("Request failed.");
  } finally {
    sendBtn.disabled = false;
    messageInput.focus();
  }
}

async function clearHistory() {
  try {
    const response = await fetch(`/api/history?session_id=${encodeURIComponent(sessionId)}`, {
      method: "DELETE",
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || "Failed to clear history.");
    }

    chatWindow.innerHTML = "";
    totalMessages = 0;
    totalImages = 0;
    updateStats();
    lastImageWrap.classList.add("empty");
    lastImageWrap.innerHTML = "<p>No generated image yet.</p>";
    setStatus("History cleared.");
  } catch (error) {
    setStatus(`Error: ${error.message}`);
  }
}

sendBtn.addEventListener("click", sendMessage);
clearHistoryBtn.addEventListener("click", clearHistory);

messageInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    sendMessage();
  }
});

messageInput.addEventListener("input", autosizeInput);

for (const chip of promptChips) {
  chip.addEventListener("click", () => {
    messageInput.value = chip.dataset.prompt || "";
    autosizeInput();
    messageInput.focus();
    setStatus("Prompt injected. Press Send Message.");
  });
}

imageModalClose.addEventListener("click", closeImageModal);
imageModal.addEventListener("click", (event) => {
  if (event.target === imageModal) {
    closeImageModal();
  }
});
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && !imageModal.hidden) {
    closeImageModal();
  }
});

loadHistory().then(() => {
  if (chatWindow.children.length === 0) {
    addMessage({
      role: "assistant",
      content:
        "Welcome to FrankAI.art. Ask for chat, coding help, or image generation in one place.",
      createdAt: new Date().toISOString(),
    });
  }
});

autosizeInput();
