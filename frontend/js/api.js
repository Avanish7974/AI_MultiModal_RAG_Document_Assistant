// =========================================================
// API CONFIGURATION
// =========================================================

const API_BASE_URL = "http://127.0.0.1:8000";


// =========================================================
// GENERIC API REQUEST
// =========================================================

async function apiRequest(endpoint, options = {}) {

    const url = `${API_BASE_URL}${endpoint}`;

    const config = {
        method: options.method || "GET",
        ...options,
        headers: {
            ...(options.body instanceof FormData
                ? {}
                : {
                    "Content-Type": "application/json"
                }),
            ...(options.headers || {})
        }
    };

    try {

        const response = await fetch(url, config);

        let data = null;

        try {
            data = await response.json();
        } catch {
            data = null;
        }

        if (!response.ok) {

            const errorMessage =
                data?.detail ||
                data?.message ||
                `Request failed with status ${response.status}`;

            throw new Error(errorMessage);
        }

        return data;

    } catch (error) {

        console.error(
            `[API ERROR] ${options.method || "GET"} ${endpoint}`,
            error
        );

        throw error;
    }
}


// =========================================================
// HEALTH CHECK
// =========================================================

async function checkHealth() {

    return await apiRequest(
        "/api/health",
        {
            method: "GET"
        }
    );
}


// =========================================================
// CHATS
// =========================================================


// ---------------------------------------------------------
// GET ALL CHATS
// ---------------------------------------------------------

async function getChats() {

    return await apiRequest(
        "/api/chats",
        {
            method: "GET"
        }
    );
}


// ---------------------------------------------------------
// CREATE NEW CHAT
// ---------------------------------------------------------

async function createChat() {

    return await apiRequest(
        "/api/chats",
        {
            method: "POST"
        }
    );
}


// ---------------------------------------------------------
// GET SINGLE CHAT
// ---------------------------------------------------------

async function getChat(chatId) {

    if (!chatId) {
        throw new Error("Chat ID is required.");
    }

    return await apiRequest(
        `/api/chats/${encodeURIComponent(chatId)}`,
        {
            method: "GET"
        }
    );
}


// ---------------------------------------------------------
// UPDATE / RENAME CHAT
// ---------------------------------------------------------

async function updateChatTitle(chatId, title) {

    if (!chatId) {
        throw new Error("Chat ID is required.");
    }

    if (!title || !title.trim()) {
        throw new Error("Chat title cannot be empty.");
    }

    return await apiRequest(
        `/api/chats/${encodeURIComponent(chatId)}`,
        {
            method: "PATCH",

            body: JSON.stringify({
                title: title.trim()
            })
        }
    );
}


// ---------------------------------------------------------
// DELETE CHAT
// ---------------------------------------------------------

async function deleteChat(chatId) {

    if (!chatId) {
        throw new Error("Chat ID is required.");
    }

    return await apiRequest(
        `/api/chats/${encodeURIComponent(chatId)}`,
        {
            method: "DELETE"
        }
    );
}


// =========================================================
// CHAT FILES / DOCUMENTS
// =========================================================


// ---------------------------------------------------------
// GET FILES BELONGING TO A CHAT
// ---------------------------------------------------------

async function getChatFiles(chatId) {

    if (!chatId) {
        throw new Error("Chat ID is required.");
    }

    return await apiRequest(
        `/api/chats/${encodeURIComponent(chatId)}/files`,
        {
            method: "GET"
        }
    );
}


// =========================================================
// CHAT MESSAGES
// =========================================================


// ---------------------------------------------------------
// GET CHAT MESSAGES
// ---------------------------------------------------------

async function getChatMessages(chatId) {

    if (!chatId) {
        throw new Error("Chat ID is required.");
    }

    return await apiRequest(
        `/api/chats/${encodeURIComponent(chatId)}/messages`,
        {
            method: "GET"
        }
    );
}


// ---------------------------------------------------------
// SAVE CHAT MESSAGE
// ---------------------------------------------------------

async function saveChatMessage(
    chatId,
    role,
    content
) {

    if (!chatId) {
        throw new Error("Chat ID is required.");
    }

    if (!role) {
        throw new Error("Message role is required.");
    }

    if (content === undefined || content === null) {
        throw new Error("Message content is required.");
    }

    return await apiRequest(
        `/api/chats/${encodeURIComponent(chatId)}/messages`,
        {
            method: "POST",

            body: JSON.stringify({
                role: role,
                content: content
            })
        }
    );
}


// =========================================================
// ASK DOCUMENTS
// =========================================================

async function askDocuments(
    chatId,
    question
) {

    if (!chatId) {
        throw new Error("Chat ID is required.");
    }

    if (!question || !question.trim()) {
        throw new Error("Question cannot be empty.");
    }

    return await apiRequest(
        `/api/chats/${encodeURIComponent(chatId)}/ask`,
        {
            method: "POST",

            body: JSON.stringify({
                question: question.trim()
            })
        }
    );
}


// =========================================================
// UPLOAD DOCUMENT
// =========================================================

async function uploadDocument(
    chatId,
    file
) {

    if (!chatId) {
        throw new Error("Chat ID is required.");
    }

    if (!file) {
        throw new Error("File is required.");
    }

    const url =
        `${API_BASE_URL}/api/chats/${encodeURIComponent(chatId)}/upload`;

    const formData = new FormData();

    formData.append(
        "file",
        file
    );

    try {

        const response = await fetch(
            url,
            {
                method: "POST",
                body: formData
            }
        );

        let data = null;

        try {
            data = await response.json();
        } catch {
            data = null;
        }

        if (!response.ok) {

            const errorMessage =
                data?.detail ||
                data?.message ||
                `Upload failed with status ${response.status}`;

            throw new Error(errorMessage);
        }

        return data;

    } catch (error) {

        console.error(
            "[UPLOAD ERROR]",
            error
        );

        throw error;
    }
}