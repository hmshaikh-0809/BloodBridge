let typingRow = null;
const chatArea = document.getElementById("bbChatArea");
const welcome = document.getElementById("bbWelcome");

function bbShowTyping() {
    typingRow = document.createElement("div");
    typingRow.className = "bb-msg-row bot";

    const avatar = document.createElement("img");
    avatar.className = "bb-avatar";
    avatar.src = "/static/images/bot.png";

    const bubble = document.createElement("div");
    bubble.className = "bb-bubble bot bb-typing";
    bubble.innerHTML = `
        <span class="bb-dot"></span>
        <span class="bb-dot"></span>
        <span class="bb-dot"></span>
    `;

    typingRow.appendChild(avatar);
    typingRow.appendChild(bubble);

    chatArea.appendChild(typingRow);
    chatArea.scrollTop = chatArea.scrollHeight;
}

function bbHideTyping() {
    if (typingRow) {
        typingRow.remove();
        typingRow = null;
    }
}

function bbAddMessage(text, sender) {

    if (welcome) {
        welcome.remove();
    }

    const row = document.createElement("div");
    row.className = `bb-msg-row ${sender}`;

    const avatar = document.createElement("img");
    avatar.className = "bb-avatar";
    avatar.src = sender === "bot"
        ? "/static/images/bot.png"
        : "/static/images/user.png";

    const bubble = document.createElement("div");
    bubble.className = `bb-bubble ${sender}`;
    bubble.innerText = text;

    if (sender === "bot") {
        row.appendChild(avatar);
        row.appendChild(bubble);
    } else {
        row.appendChild(bubble);
        row.appendChild(avatar);
    }

    chatArea.appendChild(row);
    chatArea.scrollTop = chatArea.scrollHeight;
}

function bbSendMessage() {
    const input = document.getElementById("bbInput");
    const msg = input.value.trim();
    if (!msg) return;

    bbAddMessage(msg, "user");
    input.value = "";

    // show typing indicator
    bbShowTyping();

    fetch("/chatbot/ask_stream", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message: msg })
})
    .then(async response => {

        // remove typing dots
        bbHideTyping();

        // create empty bot message bubble
        const row = document.createElement("div");
        row.className = "bb-msg-row bot";

        const avatar = document.createElement("img");
        avatar.className = "bb-avatar";
        avatar.src = "/static/images/bot.png";

        const bubble = document.createElement("div");
        bubble.className = "bb-bubble bot";
        bubble.innerText = "";

        row.appendChild(avatar);
        row.appendChild(bubble);
        chatArea.appendChild(row);
        chatArea.scrollTop = chatArea.scrollHeight;

        // STREAM READ
        const reader = response.body.getReader();
        const decoder = new TextDecoder("utf-8");

        let fullText = "";

        while (true) {
            const { value, done } = await reader.read();
            if (done) break;

            fullText += decoder.decode(value, { stream: true });
            bubble.innerText = fullText;
            chatArea.scrollTop = chatArea.scrollHeight;
        }
    })
    .catch(err => {
        bbHideTyping();
        bbAddMessage("⚠️ BloodBot is currently unavailable.", "bot");
        console.error(err);
    });
}

/* Voice to text */
function bbStartVoice() {
    if (!('webkitSpeechRecognition' in window)) {
        alert("Voice input not supported in this browser");
        return;
    }

    const recognition = new webkitSpeechRecognition();
    recognition.lang = "en-IN";
    recognition.start();

    recognition.onresult = function(event) {
        document.getElementById("bbInput").value =
            event.results[0][0].transcript;
    };
}
