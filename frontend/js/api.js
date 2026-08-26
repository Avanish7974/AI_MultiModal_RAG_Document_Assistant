// =========================================================
// MULTI-MODAL RAG DOCUMENT ASSISTANT
// API.JS
// =========================================================


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

        const response =
            await fetch(
                url,
                config
            );


        let data = null;


        try {

            data =
                await response.json();

        } catch {

            data = null;
        }


        if (!response.ok) {

            const errorMessage =
                data?.detail ||
                data?.message ||
                `Request failed with status ${response.status}`;


            throw new Error(
                errorMessage
            );
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

        throw new Error(
            "Chat ID is required."
        );
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

async function updateChatTitle(
    chatId,
    title
) {

    if (!chatId) {

        throw new Error(
            "Chat ID is required."
        );
    }


    if (!title || !title.trim()) {

        throw new Error(
            "Chat title cannot be empty."
        );
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

async function deleteChat(
    chatId
) {

    if (!chatId) {

        throw new Error(
            "Chat ID is required."
        );
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

async function getChatFiles(
    chatId
) {

    if (!chatId) {

        throw new Error(
            "Chat ID is required."
        );
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

async function getChatMessages(
    chatId
) {

    if (!chatId) {

        throw new Error(
            "Chat ID is required."
        );
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

        throw new Error(
            "Chat ID is required."
        );
    }


    if (!role) {

        throw new Error(
            "Message role is required."
        );
    }


    if (
        content === undefined ||
        content === null
    ) {

        throw new Error(
            "Message content is required."
        );
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

        throw new Error(
            "Chat ID is required."
        );
    }


    if (!question || !question.trim()) {

        throw new Error(
            "Question cannot be empty."
        );
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
// DOCUMENT ACTIONS
// =========================================================
//
// These endpoints are used by:
//
// 📄 Summarize
// 🔄 Compare Documents
// 🎯 Generate Quiz
// 📑 Flashcards
//
// =========================================================


// =========================================================
// SUMMARIZE DOCUMENTS
// =========================================================
//
// Backend:
// POST /api/chats/{chat_id}/summarize
//
// Request:
// {
//     "length": "Short" | "Medium" | "Detailed"
// }
//
// =========================================================

async function summarizeDocuments(
    chatId,
    length = "Medium"
) {

    if (!chatId) {

        throw new Error(
            "Chat ID is required."
        );
    }


    const allowedLengths = [
        "Short",
        "Medium",
        "Detailed"
    ];


    const normalizedLength =
        allowedLengths.includes(length)
            ? length
            : "Medium";


    return await apiRequest(
        `/api/chats/${encodeURIComponent(chatId)}/summarize`,
        {
            method: "POST",

            body: JSON.stringify({
                length: normalizedLength
            })
        }
    );
}


// =========================================================
// COMPARE DOCUMENTS
// =========================================================
//
// Backend:
// POST /api/chats/{chat_id}/compare
//
// Request:
// {
//     "files": [
//         "document1.pdf",
//         "document2.pdf"
//     ]
// }
//
// =========================================================

async function compareDocuments(
    chatId,
    files
) {

    if (!chatId) {

        throw new Error(
            "Chat ID is required."
        );
    }


    if (!Array.isArray(files)) {

        throw new Error(
            "Files must be an array."
        );
    }


    const cleanedFiles =
        files
            .filter(
                file =>
                    typeof file === "string"
            )
            .map(
                file =>
                    file.trim()
            )
            .filter(
                file =>
                    file.length > 0
            );


    if (cleanedFiles.length < 2) {

        throw new Error(
            "Select at least two documents to compare."
        );
    }


    return await apiRequest(
        `/api/chats/${encodeURIComponent(chatId)}/compare`,
        {
            method: "POST",

            body: JSON.stringify({
                files: cleanedFiles
            })
        }
    );
}


// =========================================================
// GENERATE DOCUMENT QUIZ
// =========================================================
//
// Backend:
// POST /api/chats/{chat_id}/quiz
//
// Request:
// {
//     "num_questions": 5,
//     "difficulty": "Medium"
// }
//
// =========================================================

async function generateDocumentQuiz(
    chatId,
    numQuestions = 5,
    difficulty = "Medium"
) {

    if (!chatId) {

        throw new Error(
            "Chat ID is required."
        );
    }


    let questionCount =
        Number(numQuestions);


    if (
        !Number.isFinite(questionCount)
    ) {

        questionCount = 5;
    }


    questionCount =
        Math.max(
            3,
            Math.min(
                15,
                Math.floor(questionCount)
            )
        );


    const allowedDifficulties = [
        "Easy",
        "Medium",
        "Hard"
    ];


    const normalizedDifficulty =
        allowedDifficulties.includes(
            difficulty
        )
            ? difficulty
            : "Medium";


    return await apiRequest(
        `/api/chats/${encodeURIComponent(chatId)}/quiz`,
        {
            method: "POST",

            body: JSON.stringify({
                num_questions:
                    questionCount,

                difficulty:
                    normalizedDifficulty
            })
        }
    );
}


// =========================================================
// GENERATE DOCUMENT FLASHCARDS
// =========================================================
//
// Backend:
// POST /api/chats/{chat_id}/flashcards
//
// Request:
// {
//     "count": 10,
//     "difficulty": "Medium"
// }
//
// =========================================================

async function generateDocumentFlashcards(
    chatId,
    count = 10,
    difficulty = "Medium"
) {

    if (!chatId) {

        throw new Error(
            "Chat ID is required."
        );
    }


    let cardCount =
        Number(count);


    if (
        !Number.isFinite(cardCount)
    ) {

        cardCount = 10;
    }


    cardCount =
        Math.max(
            5,
            Math.min(
                20,
                Math.floor(cardCount)
            )
        );


    const allowedDifficulties = [
        "Easy",
        "Medium",
        "Hard"
    ];


    const normalizedDifficulty =
        allowedDifficulties.includes(
            difficulty
        )
            ? difficulty
            : "Medium";


    return await apiRequest(
        `/api/chats/${encodeURIComponent(chatId)}/flashcards`,
        {
            method: "POST",

            body: JSON.stringify({
                count:
                    cardCount,

                difficulty:
                    normalizedDifficulty
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

        throw new Error(
            "Chat ID is required."
        );
    }


    if (!file) {

        throw new Error(
            "File is required."
        );
    }


    const url =
        `${API_BASE_URL}/api/chats/${encodeURIComponent(chatId)}/upload`;


    const formData =
        new FormData();


    formData.append(
        "file",
        file
    );


    try {

        const response =
            await fetch(
                url,
                {
                    method: "POST",
                    body: formData
                }
            );


        let data = null;


        try {

            data =
                await response.json();

        } catch {

            data = null;
        }


        if (!response.ok) {

            const errorMessage =
                data?.detail ||
                data?.message ||
                `Upload failed with status ${response.status}`;


            throw new Error(
                errorMessage
            );
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


// =========================================================
// YOUTUBE MODE STATUS
// =========================================================
// Returns whether the current chat already has an analyzed YouTube source.

async function getYouTubeStatus(chatId) {

    if (!chatId) {
        throw new Error("Chat ID is required.");
    }

    return await apiRequest(
        `/api/chats/${encodeURIComponent(chatId)}/youtube/status`,
        {
            method: "GET"
        }
    );
}


// =========================================================
// YOUTUBE — INITIAL TRANSCRIPT ANALYSIS + SUMMARY
// =========================================================
//
// Backend:
// POST /api/chats/{chat_id}/youtube/analyze
//
// This runs once when a YouTube URL is added to a chat.
// The transcript is indexed and a text-based summary becomes the
// persistent video context used by subsequent questions.
//
// =========================================================

async function analyzeYouTubeVideo(
    chatId,
    videoUrl
) {

    if (!chatId) {

        throw new Error(
            "Chat ID is required."
        );
    }


    if (
        !videoUrl ||
        !videoUrl.trim()
    ) {

        throw new Error(
            "YouTube video URL is required."
        );
    }


    return await apiRequest(
        `/api/chats/${encodeURIComponent(chatId)}/youtube/analyze`,
        {
            method: "POST",

            body: JSON.stringify({
                video_url:
                    videoUrl.trim()
            })
        }
    );
}


// =========================================================
// YOUTUBE LEVEL 2 — MULTIMODAL ASK
// =========================================================
//
// Backend:
// POST /api/chats/{chat_id}/youtube/ask
//
// Request:
// {
//     "video_url": "...",
//     "question": "..."
// }
//
// =========================================================

async function askYouTubeMultimodal(
    chatId,
    videoUrl,
    question
) {

    // -----------------------------------------------------
    // VALIDATE CHAT
    // -----------------------------------------------------

    if (!chatId) {

        throw new Error(
            "Chat ID is required."
        );
    }


    // -----------------------------------------------------
    // VALIDATE VIDEO URL
    // -----------------------------------------------------

    if (
        !videoUrl ||
        !videoUrl.trim()
    ) {

        throw new Error(
            "YouTube video URL is required."
        );
    }


    // -----------------------------------------------------
    // VALIDATE QUESTION
    // -----------------------------------------------------

    if (
        !question ||
        !question.trim()
    ) {

        throw new Error(
            "Question cannot be empty."
        );
    }


    // -----------------------------------------------------
    // CALL BACKEND
    // -----------------------------------------------------

    return await apiRequest(
        `/api/chats/${encodeURIComponent(chatId)}/youtube/ask`,
        {
            method: "POST",

            body: JSON.stringify({
                video_url:
                    videoUrl.trim(),

                question:
                    question.trim()
            })
        }
    );
}


// =========================================================
// OPTIONAL GLOBAL API OBJECT
// =========================================================
//
// This makes the API functions available as:
//
// window.RAGAPI.summarizeDocuments(...)
// window.RAGAPI.compareDocuments(...)
// window.RAGAPI.generateDocumentQuiz(...)
// window.RAGAPI.generateDocumentFlashcards(...)
//
// Existing functions remain globally available too.
// =========================================================

window.RAGAPI = {

    apiRequest,

    checkHealth,

    getChats,
    createChat,
    getChat,
    updateChatTitle,
    deleteChat,

    getChatFiles,

    getChatMessages,
    saveChatMessage,

    askDocuments,

    summarizeDocuments,
    compareDocuments,
    generateDocumentQuiz,
    generateDocumentFlashcards,

    uploadDocument,

    analyzeYouTubeVideo,
    askYouTubeMultimodal,
    getYouTubeStatus
};


// =========================================================
// END API.JS
// =========================================================