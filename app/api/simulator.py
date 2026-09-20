"""Interactive Mobile WhatsApp Web Simulator for instant testing on phone browsers."""

import tempfile
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.services.conversation import ConversationOrchestrator

router = APIRouter(tags=["Simulator"])

HTML_CONTENT = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <title>WhatsApp Print Agent</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }
    body { background: #efeae2; display: flex; flex-direction: column; height: 100vh; height: 100dvh; }
    header { background: #075e54; color: #fff; padding: 12px 16px; display: flex; align-items: center; gap: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.2); }
    .avatar { width: 40px; height: 40px; border-radius: 50%; background: #128c7e; display: flex; align-items: center; justify-content: center; font-size: 20px; }
    .header-info h1 { font-size: 16px; font-weight: 600; }
    .header-info p { font-size: 12px; color: #d4e8e1; }
    .chat-box { flex: 1; overflow-y: auto; padding: 16px; display: flex; flex-direction: column; gap: 10px; }
    .msg { max-width: 82%; padding: 8px 12px; border-radius: 8px; font-size: 14px; line-height: 1.4; word-break: break-word; white-space: pre-wrap; box-shadow: 0 1px 1px rgba(0,0,0,0.1); }
    .bot { background: #ffffff; align-self: flex-start; border-top-left-radius: 0; color: #111; }
    .user { background: #d9fdd3; align-self: flex-end; border-top-right-radius: 0; color: #111; }
    .time { font-size: 10px; color: #888; text-align: right; margin-top: 4px; }
    .chips { display: flex; gap: 6px; padding: 6px 12px; overflow-x: auto; background: #e4ded4; }
    .chip { background: #fff; border: 1px solid #ccc; border-radius: 16px; padding: 6px 12px; font-size: 13px; font-weight: 500; cursor: pointer; white-space: nowrap; color: #075e54; }
    .input-bar { display: flex; align-items: center; gap: 8px; padding: 10px; background: #f0f2f5; border-top: 1px solid #ddd; }
    .attach-btn { background: none; border: none; font-size: 22px; cursor: pointer; color: #54656f; padding: 4px; }
    input[type="text"] { flex: 1; padding: 10px 14px; border: none; border-radius: 20px; outline: none; font-size: 15px; background: #fff; }
    .send-btn { background: #128c7e; color: #fff; border: none; border-radius: 50%; width: 40px; height: 40px; display: flex; align-items: center; justify-content: center; font-size: 18px; cursor: pointer; }
    #fileInput { display: none; }
  </style>
</head>
<body>
  <header>
    <div class="avatar">🖨️</div>
    <div class="header-info">
      <h1>Print Agent Bot</h1>
      <p>Online • AI Powered Printing</p>
    </div>
  </header>

  <div class="chat-box" id="chatBox">
    <div class="msg bot">
      Hello! Welcome to WhatsApp Print Agent. 🖨️<br><br>You can send <b>Hi</b>, upload a <b>PDF document</b>, check <b>Pricing</b>, or specify print options like <i>"Print 2 copies in black and white"</i>.
      <div class="time">Just now</div>
    </div>
  </div>

  <div class="chips">
    <button class="chip" onclick="quickSend('Hi')">👋 Hi</button>
    <button class="chip" onclick="quickSend('Pricing')">💰 Pricing</button>
    <button class="chip" onclick="quickSend('Print')">🖨️ Print</button>
    <button class="chip" onclick="quickSend('PAY')">💳 Confirm Pay</button>
  </div>

  <form class="input-bar" id="chatForm" onsubmit="handleSend(event)">
    <input type="file" id="fileInput" accept=".pdf" onchange="uploadPdf(event)">
    <button type="button" class="attach-btn" onclick="document.getElementById('fileInput').click()" title="Upload PDF">📎</button>
    <input type="text" id="textInput" placeholder="Type a message or upload PDF..." autocomplete="off">
    <button type="submit" class="send-btn">➤</button>
  </form>

  <script>
    const phone = "+919876543210";
    const chatBox = document.getElementById("chatBox");

    function appendMessage(text, sender) {
      const msg = document.createElement("div");
      msg.className = "msg " + sender;
      const formatted = text.replace(/\\*(.*?)\\*/g, '<b>$1</b>').replace(/_(.*?)_/g, '<i>$1</i>');
      msg.innerHTML = formatted + `<div class="time">${new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</div>`;
      chatBox.appendChild(msg);
      chatBox.scrollTop = chatBox.scrollHeight;
    }

    async function sendPayload(formData) {
      formData.append("phone", phone);
      try {
        const res = await fetch("/api/chat", { method: "POST", body: formData });
        const data = await res.json();
        if (data.reply) {
          appendMessage(data.reply, "bot");
        }
      } catch (err) {
        appendMessage("❌ Error sending message. Please check connection.", "bot");
      }
    }

    function quickSend(txt) {
      document.getElementById("textInput").value = txt;
      document.getElementById("chatForm").requestSubmit();
    }

    function handleSend(e) {
      e.preventDefault();
      const input = document.getElementById("textInput");
      const text = input.value.trim();
      if (!text) return;
      appendMessage(text, "user");
      input.value = "";
      const fd = new FormData();
      fd.append("message", text);
      sendPayload(fd);
    }

    async function uploadPdf(e) {
      const file = e.target.files[0];
      if (!file) return;
      appendMessage("📎 Uploading: " + file.name, "user");
      const fd = new FormData();
      fd.append("file", file);
      await sendPayload(fd);
      e.target.value = "";
    }
  </script>
</body>
</html>
"""


@router.get("/", response_class=HTMLResponse)
def get_simulator():
    """Serve mobile WhatsApp web simulator interface."""
    return HTMLResponse(content=HTML_CONTENT)


@router.post("/api/chat")
async def chat_api(
    phone: Annotated[str, Form()] = "+919876543210",
    message: Annotated[str | None, Form()] = None,
    file: Annotated[UploadFile | None, File()] = None,
    db: Annotated[Session, Depends(get_db)] = None,  # type: ignore
):
    """Receive messages from web simulator and coordinate with services."""
    temp_pdf_path = None
    filename = None

    if file and file.filename:
        filename = file.filename
        content = await file.read()
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
            temp_file.write(content)
            temp_pdf_path = Path(temp_file.name)

    reply = ConversationOrchestrator.handle_message(
        db=db,
        sender_phone=phone,
        text=message,
        file_path=temp_pdf_path,
        filename=filename,
    )

    if temp_pdf_path and temp_pdf_path.exists():
        temp_pdf_path.unlink()

    return {"reply": reply}
