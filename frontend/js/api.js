// =========================================================
// API CONFIGURATION
// =========================================================

const API_BASE_URL = "http://127.0.0.1:8000";


// =========================================================
// GENERIC API REQUEST
// =========================================================

async function apiRequest(
    endpoint,
    options = {}
) {
    const url = `${API_BASE_URL}${endpoint}`;

    const config = {
        ...options,
        headers: {
            "Content-Type": "application/json",
            ...(options.headers || {})
        }
    };

    try {

        const response = await fetch(
            url,
            config
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
                `Request failed with status ${response.status}`;

            throw new Error(errorMessage);
        }

        return data;

    } catch (error) {

        console.error(
            "API Request Error:",
            endpoint,
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

async function getChats() {

    return await apiRequest(
        "/api/chats",
        {
            method: "GET"
        }
    );
}


async function createChat() {

    return await apiRequest(
        "/api/chats",
        {
            method: "POST"
        }
    );
}


async function getChat(chatId) {

    return await apiRequest(
        `/api/chats/${encodeURIComponent(chatId)}`,
        {
            method: "GET"
        }
    );
}


async function deleteChat(chatId) {

    return await apiRequest(
        `/api/chats/${encodeURIComponent(chatId)}`,
        {
            method: "DELETE"
        }
    );
}


// =========================================================
// CHAT MESSAGES
// =========================================================

async function getChatMessages(chatId) {

    return await apiRequest(
        `/api/chats/${encodeURIComponent(chatId)}/messages`,
        {
            method: "GET"
        }
    );
}


async function saveChatMessage(
    chatId,
    role,
    content
) {

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

    return await apiRequest(
        `/api/chats/${encodeURIComponent(chatId)}/ask`,
        {
            method: "POST",

            body: JSON.stringify({
                question: question
            })
        }
    );
}
// =========================================================
// UPLOAD DOCUMENT
// =========================================================

async function uploadDocument(chatId, file) {

    const url =
        `${API_BASE_URL}/api/chats/${encodeURIComponent(chatId)}/upload`;

    const formData = new FormData();

    formData.append("file", file);

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
            "Document Upload Error:",
            error
        );

        throw error;
    }
}