// =========================================================
// MULTI-MODAL RAG DOCUMENT ASSISTANT
// APP.JS
//
// IMPORTANT:
// API functions are provided by api.js
// Chat state/functions are provided by chats.js
//
// DO NOT declare:
// API_BASE_URL
// currentChatId
// createChat
// getChats
// uploadDocument
// askDocuments
// saveChatMessage
// loadChats
// getChat
// openChat
// =========================================================


// =========================================================
// APPLICATION STATE
// =========================================================

let currentAction = "ask";
let isUploading = false;
let isAsking = false;


// =========================================================
// DOM HELPER
// =========================================================

function $(id) {
    return document.getElementById(id);
}


// =========================================================
// STATUS MESSAGE
// =========================================================

function setStatus(message, isError = false) {

    const status = $("statusMessage");

    if (!status) {
        console.log(message);
        return;
    }

    status.textContent = message || "";

    status.classList.toggle(
        "error",
        Boolean(isError)
    );

    status.style.display =
        message ? "block" : "none";
}


// =========================================================
// EMPTY STATE
// =========================================================

function showEmptyState() {

    const emptyState =
        $("emptyState");

    if (emptyState) {
        emptyState.classList.remove("hidden");
    }
}


function hideEmptyState() {

    const emptyState =
        $("emptyState");

    if (emptyState) {
        emptyState.classList.add("hidden");
    }
}


// =========================================================
// CHAT CONTAINER
// =========================================================

function clearChatInterface() {

    const container =
        $("chatContainer");

    if (container) {
        container.innerHTML = "";
    }

    hideSources();
    showEmptyState();
}


// =========================================================
// ESCAPE HTML
// =========================================================

function escapeHtml(text) {

    const div =
        document.createElement("div");

    div.textContent =
        text || "";

    return div.innerHTML;
}


// =========================================================
// FORMAT ANSWER
// =========================================================

function formatAnswer(text) {

    if (!text) {
        return "";
    }

    let html =
        escapeHtml(text);


    // H3
    html =
        html.replace(
            /^### (.+)$/gm,
            "<h3>$1</h3>"
        );


    // H2
    html =
        html.replace(
            /^## (.+)$/gm,
            "<h2>$1</h2>"
        );


    // H1
    html =
        html.replace(
            /^# (.+)$/gm,
            "<h2>$1</h2>"
        );


    // Bold
    html =
        html.replace(
            /\*\*(.*?)\*\*/g,
            "<strong>$1</strong>"
        );


    // Inline code
    html =
        html.replace(
            /`([^`]+)`/g,
            "<code>$1</code>"
        );


    // Bullet points
    html =
        html.replace(
            /^[•*-] (.+)$/gm,
            "<li>$1</li>"
        );


    // Group consecutive list items
    html =
        html.replace(
            /(<li>.*?<\/li>\s*)+/gs,
            match => `<ul>${match}</ul>`
        );


    // New lines
    html =
        html.replace(
            /\n/g,
            "<br>"
        );


    return html;
}


// =========================================================
// SCROLL TO BOTTOM
// =========================================================

function scrollToBottom() {

    const main =
        document.querySelector(
            ".main-content"
        );

    if (!main) {
        return;
    }

    requestAnimationFrame(() => {

        main.scrollTo({
            top: main.scrollHeight,
            behavior: "smooth"
        });

    });
}


// =========================================================
// RENDER SINGLE MESSAGE
// =========================================================

function renderMessage(
    role,
    content
) {

    const container =
        $("chatContainer");

    if (!container) {

        console.warn(
            "chatContainer not found."
        );

        return;
    }


    hideEmptyState();


    const message =
        document.createElement("div");

    message.className =
        `message ${
            role === "user"
                ? "user"
                : "assistant"
        }`;


    // -----------------------------------------------------
    // HEADER
    // -----------------------------------------------------

    const header =
        document.createElement("div");

    header.className =
        "message-header";


    const icon =
        document.createElement("div");

    icon.className =
        "message-icon";

    icon.textContent =
        role === "user"
            ? "👤"
            : "🤖";


    const name =
        document.createElement("span");

    name.textContent =
        role === "user"
            ? "You"
            : "RAG Assistant";


    header.appendChild(icon);
    header.appendChild(name);


    // -----------------------------------------------------
    // CONTENT
    // -----------------------------------------------------

    const contentElement =
        document.createElement("div");

    contentElement.className =
        "message-content";


    if (role === "assistant") {

        contentElement.classList.add(
            "answer-content"
        );

        contentElement.innerHTML =
            formatAnswer(content);

    } else {

        contentElement.textContent =
            content || "";
    }


    message.appendChild(header);

    message.appendChild(
        contentElement
    );

    container.appendChild(
        message
    );


    scrollToBottom();
}


// =========================================================
// RENDER ALL MESSAGES
// =========================================================

function renderMessages(messages) {

    const container =
        $("chatContainer");

    if (!container) {
        return;
    }


    container.innerHTML = "";


    if (
        !Array.isArray(messages) ||
        messages.length === 0
    ) {

        showEmptyState();

        return;
    }


    hideEmptyState();


    messages.forEach(
        message => {

            renderMessage(
                message.role,
                message.content
            );

        }
    );


    scrollToBottom();
}


// =========================================================
// SOURCES
// =========================================================

function hideSources() {

    const section =
        $("sourcesSection");

    const container =
        $("sourcesContainer");


    if (section) {

        section.classList.add(
            "hidden"
        );
    }


    if (container) {

        container.innerHTML = "";
    }
}


function renderSources(sources) {

    const section =
        $("sourcesSection");

    const container =
        $("sourcesContainer");


    if (
        !section ||
        !container
    ) {
        return;
    }


    container.innerHTML = "";


    if (
        !Array.isArray(sources) ||
        sources.length === 0
    ) {

        section.classList.add(
            "hidden"
        );

        return;
    }


    section.classList.remove(
        "hidden"
    );


    sources.forEach(
        source => {

            const card =
                document.createElement(
                    "div"
                );

            card.className =
                "source-card";


            const name =
                document.createElement(
                    "div"
                );

            name.className =
                "source-name";

            name.textContent =
                source.file_name ||
                source.source ||
                "Source";


            const location =
                document.createElement(
                    "div"
                );

            location.className =
                "source-location";


            const parts = [];


            if (
                source.page !== undefined &&
                source.page !== null
            ) {

                parts.push(
                    `Page ${source.page}`
                );
            }


            if (
                source.source_type
            ) {

                parts.push(
                    source.source_type
                );
            }


            location.textContent =
                parts.join(" • ");


            card.appendChild(
                name
            );


            if (parts.length) {

                card.appendChild(
                    location
                );
            }


            container.appendChild(
                card
            );

        }
    );
}


// =========================================================
// DOCUMENT LIBRARY STORAGE
// =========================================================

function getChatDocumentsKey(chatId) {

    return `rag_documents_${chatId}`;
}


function getChatDocuments(chatId) {

    if (!chatId) {
        return [];
    }


    try {

        const stored =
            localStorage.getItem(
                getChatDocumentsKey(
                    chatId
                )
            );


        if (!stored) {
            return [];
        }


        const documents =
            JSON.parse(stored);


        if (
            !Array.isArray(documents)
        ) {
            return [];
        }


        return documents;

    } catch (error) {

        console.error(
            "Could not read chat documents:",
            error
        );

        return [];
    }
}


function saveChatDocuments(
    chatId,
    documents
) {

    if (!chatId) {
        return;
    }


    try {

        localStorage.setItem(
            getChatDocumentsKey(
                chatId
            ),
            JSON.stringify(
                documents
            )
        );

    } catch (error) {

        console.error(
            "Could not save chat documents:",
            error
        );
    }
}


// =========================================================
// FILE SIZE
// =========================================================

function formatFileSize(bytes) {

    if (
        bytes === undefined ||
        bytes === null ||
        Number.isNaN(
            Number(bytes)
        )
    ) {
        return "";
    }


    const size =
        Number(bytes);


    if (
        size < 1024
    ) {
        return `${size} B`;
    }


    if (
        size < 1024 * 1024
    ) {
        return `${(
            size / 1024
        ).toFixed(1)} KB`;
    }


    if (
        size < 1024 * 1024 * 1024
    ) {
        return `${(
            size / (1024 * 1024)
        ).toFixed(1)} MB`;
    }


    return `${(
        size /
        (1024 * 1024 * 1024)
    ).toFixed(1)} GB`;
}


// =========================================================
// DOCUMENT ICON
// =========================================================

function getDocumentIcon(fileName) {

    const extension =
        (
            fileName || ""
        )
            .split(".")
            .pop()
            .toLowerCase();


    if (
        extension === "pdf"
    ) {
        return "📕";
    }


    if (
        extension === "docx" ||
        extension === "doc"
    ) {
        return "📘";
    }


    if (
        extension === "pptx" ||
        extension === "ppt"
    ) {
        return "📙";
    }


    if (
        extension === "xlsx" ||
        extension === "xls" ||
        extension === "csv"
    ) {
        return "📊";
    }


    if (
        extension === "png" ||
        extension === "jpg" ||
        extension === "jpeg"
    ) {
        return "🖼️";
    }


    if (
        extension === "txt"
    ) {
        return "📄";
    }


    return "📁";
}


// =========================================================
// DOCUMENT LIBRARY
// =========================================================

function renderDocumentLibrary() {

    const library =
        $("documentLibrary");

    const documentList =
        $("documentList");

    const countElement =
        $("documentLibraryCount");


    if (
        !library ||
        !documentList
    ) {

        console.warn(
            "Document library elements not found."
        );

        return;
    }


    // currentChatId comes from chats.js.
    // NEVER redeclare it here.

    if (
        typeof currentChatId ===
        "undefined" ||
        !currentChatId
    ) {

        library.style.display =
            "none";

        documentList.innerHTML =
            "";

        if (countElement) {

            countElement.textContent =
                "0 documents";
        }

        return;
    }


    const documents =
        getChatDocuments(
            currentChatId
        );


    documentList.innerHTML =
        "";


    if (countElement) {

        countElement.textContent =
            documents.length === 1
                ? "1 document"
                : `${documents.length} documents`;
    }


    if (
        documents.length === 0
    ) {

        library.style.display =
            "none";

        return;
    }


    library.style.display =
        "block";


    documents.forEach(
        doc => {

            const card =
                document.createElement(
                    "div"
                );

            card.className =
                "document-card";


            card.style.display =
                "flex";

            card.style.alignItems =
                "center";

            card.style.gap =
                "12px";

            card.style.padding =
                "14px";

            card.style.marginBottom =
                "10px";

            card.style.border =
                "1px solid rgba(255,255,255,0.10)";

            card.style.borderRadius =
                "12px";

            card.style.background =
                "rgba(255,255,255,0.04)";


            // -------------------------------------------------
            // ICON
            // -------------------------------------------------

            const icon =
                document.createElement(
                    "div"
                );

            icon.textContent =
                getDocumentIcon(
                    doc.file_name ||
                    "document"
                );

            icon.style.fontSize =
                "28px";


            // -------------------------------------------------
            // INFO
            // -------------------------------------------------

            const info =
                document.createElement(
                    "div"
                );

            info.style.flex =
                "1";

            info.style.minWidth =
                "0";


            const name =
                document.createElement(
                    "div"
                );

            name.textContent =
                doc.file_name ||
                "Unnamed document";

            name.style.fontWeight =
                "600";

            name.style.overflow =
                "hidden";

            name.style.textOverflow =
                "ellipsis";

            name.style.whiteSpace =
                "nowrap";


            const meta =
                document.createElement(
                    "div"
                );


            const parts = [];


            if (
                doc.file_type
            ) {

                parts.push(
                    doc.file_type
                );
            }


            if (
                doc.file_size !== undefined &&
                doc.file_size !== null
            ) {

                parts.push(
                    formatFileSize(
                        doc.file_size
                    )
                );
            }


            if (
                doc.chunks !== undefined &&
                doc.chunks !== null
            ) {

                parts.push(
                    `${doc.chunks} chunks`
                );
            }


            meta.textContent =
                parts.join(" • ");


            meta.style.fontSize =
                "12px";

            meta.style.opacity =
                "0.65";

            meta.style.marginTop =
                "4px";


            info.appendChild(
                name
            );

            info.appendChild(
                meta
            );


            // -------------------------------------------------
            // STATUS
            // -------------------------------------------------

            const status =
                document.createElement(
                    "div"
                );

            status.textContent =
                "✓ Ready";

            status.style.fontSize =
                "12px";

            status.style.whiteSpace =
                "nowrap";

            status.style.padding =
                "5px 9px";

            status.style.borderRadius =
                "8px";

            status.style.background =
                "rgba(46, 204, 113, 0.12)";

            status.style.color =
                "#2ecc71";


            card.appendChild(
                icon
            );

            card.appendChild(
                info
            );

            card.appendChild(
                status
            );


            documentList.appendChild(
                card
            );

        }
    );
}


// =========================================================
// ADD UPLOADED DOCUMENT
// =========================================================

function addUploadedDocument(
    uploadResult,
    file
) {

    if (
        typeof currentChatId ===
        "undefined" ||
        !currentChatId
    ) {

        console.warn(
            "Cannot add document without a current chat."
        );

        return;
    }


    const documents =
        getChatDocuments(
            currentChatId
        );


    const documentData = {

        file_name:
            uploadResult?.file_name ||
            file.name,

        file_type:
            (
                file.name
                    .split(".")
                    .pop() ||
                ""
            ).toUpperCase(),

        file_size:
            file.size,

        chunks:
            uploadResult?.chunks ??
            0,

        uploaded_at:
            new Date().toISOString()
    };


    const existingIndex =
        documents.findIndex(
            document =>
                document.file_name ===
                file.name
        );


    if (
        existingIndex !== -1
    ) {

        documents[
            existingIndex
        ] =
            documentData;

    } else {

        documents.push(
            documentData
        );
    }


    saveChatDocuments(
        currentChatId,
        documents
    );


    renderDocumentLibrary();
}


// =========================================================
// ENSURE CURRENT CHAT
// =========================================================

async function ensureCurrentChat() {

    if (
        typeof currentChatId !==
        "undefined" &&
        currentChatId
    ) {

        return currentChatId;
    }


    setStatus(
        "Creating a new chat..."
    );


    // createChat() comes from api.js.

    const result =
        await createChat();


    if (
        !result ||
        !result.chat_id
    ) {

        throw new Error(
            "Could not create a new chat."
        );
    }


    // currentChatId comes from chats.js.

    currentChatId =
        result.chat_id;


    // Persist current chat.

    localStorage.setItem(
        "rag_current_chat_id",
        currentChatId
    );


    console.log(
        "Created chat:",
        currentChatId
    );


    // Refresh recent chats.

    if (
        typeof loadChats ===
        "function"
    ) {

        try {

            await loadChats();

        } catch (error) {

            console.warn(
                "Could not refresh chats:",
                error
            );
        }
    }


    return currentChatId;
}


// =========================================================
// UPLOAD PANEL UI
// =========================================================

function initializeUploadUI() {

    const uploadBtn =
        $("uploadBtn");

    const uploadPanel =
        $("uploadPanel");

    const closeUploadBtn =
        $("closeUploadBtn");

    const chooseFilesBtn =
        $("chooseFilesBtn");

    const fileInput =
        $("fileInput");


    // -----------------------------------------------------
    // OPEN UPLOAD PANEL
    // -----------------------------------------------------

    if (
        uploadBtn &&
        uploadPanel
    ) {

        uploadBtn.addEventListener(
            "click",
            () => {

                uploadPanel.classList.toggle(
                    "open"
                );

            }
        );
    }


    // -----------------------------------------------------
    // CLOSE UPLOAD PANEL
    // -----------------------------------------------------

    if (
        closeUploadBtn &&
        uploadPanel
    ) {

        closeUploadBtn.addEventListener(
            "click",
            () => {

                uploadPanel.classList.remove(
                    "open"
                );

                setStatus("");

            }
        );
    }


    // -----------------------------------------------------
    // CHECK FILE INPUT
    // -----------------------------------------------------

    if (
        !chooseFilesBtn ||
        !fileInput
    ) {

        console.error(
            "Upload UI error: chooseFilesBtn or fileInput not found."
        );

        return;
    }


    // -----------------------------------------------------
    // CHOOSE FILES
    // -----------------------------------------------------
    //
    // IMPORTANT:
    // Open native file picker immediately.
    // Do not await createChat() before this.
    //

    chooseFilesBtn.addEventListener(
        "click",
        () => {

            console.log(
                "Choose Files clicked."
            );

            fileInput.click();

        }
    );


    // -----------------------------------------------------
    // FILE SELECTED
    // -----------------------------------------------------

    fileInput.addEventListener(
        "change",
        async () => {

            const files =
                Array.from(
                    fileInput.files || []
                );


            if (
                !files.length
            ) {
                return;
            }


            if (isUploading) {
                return;
            }


            isUploading =
                true;

            chooseFilesBtn.disabled =
                true;


            try {

                let uploadedCount =
                    0;


                // -------------------------------------------------
                // VALIDATE CURRENT CHAT
                // -------------------------------------------------

                if (
                    typeof currentChatId !==
                        "undefined" &&
                    currentChatId
                ) {

                    try {

                        console.log(
                            "Checking current chat:",
                            currentChatId
                        );


                        // getChat() comes from api.js.

                        if (
                            typeof getChat ===
                            "function"
                        ) {

                            await getChat(
                                currentChatId
                            );

                            console.log(
                                "Current chat is valid:",
                                currentChatId
                            );

                        }

                    } catch (error) {

                        console.warn(
                            "Current chat is invalid. Creating a new chat.",
                            error
                        );


                        currentChatId =
                            null;


                        localStorage.removeItem(
                            "rag_current_chat_id"
                        );
                    }
                }


                // -------------------------------------------------
                // CREATE CHAT IF NEEDED
                // -------------------------------------------------

                if (
                    typeof currentChatId ===
                        "undefined" ||
                    !currentChatId
                ) {

                    setStatus(
                        "Creating a new chat..."
                    );


                    const result =
                        await createChat();


                    if (
                        !result ||
                        !result.chat_id
                    ) {

                        throw new Error(
                            "Could not create a chat."
                        );
                    }


                    currentChatId =
                        result.chat_id;


                    // Persist the newly created chat.

                    localStorage.setItem(
                        "rag_current_chat_id",
                        currentChatId
                    );


                    console.log(
                        "New chat created:",
                        currentChatId
                    );


                    // Refresh chat list.

                    if (
                        typeof loadChats ===
                        "function"
                    ) {

                        try {

                            await loadChats();

                        } catch (error) {

                            console.warn(
                                "Could not refresh chats:",
                                error
                            );
                        }
                    }
                }


                // -------------------------------------------------
                // UPLOAD EACH FILE
                // -------------------------------------------------

                for (
                    const file of files
                ) {

                    setStatus(
                        `Uploading ${file.name}...`
                    );


                    console.log(
                        "Uploading:",
                        file.name,
                        "Chat:",
                        currentChatId
                    );


                    // uploadDocument() comes from api.js.

                    const result =
                        await uploadDocument(
                            currentChatId,
                            file
                        );


                    console.log(
                        "Upload response:",
                        result
                    );


                    addUploadedDocument(
                        result,
                        file
                    );


                    uploadedCount++;
                }


                // -------------------------------------------------
                // SUCCESS
                // -------------------------------------------------

                if (
                    uploadedCount === 1
                ) {

                    setStatus(
                        "Document uploaded successfully."
                    );

                } else {

                    setStatus(
                        `${uploadedCount} documents uploaded successfully.`
                    );
                }


                // -------------------------------------------------
                // REFRESH DOCUMENT LIBRARY
                // -------------------------------------------------

                renderDocumentLibrary();


                // -------------------------------------------------
                // CLOSE PANEL
                // -------------------------------------------------

                if (
                    uploadPanel
                ) {

                    uploadPanel.classList.remove(
                        "open"
                    );
                }


                // -------------------------------------------------
                // REFRESH CHATS
                // -------------------------------------------------

                if (
                    typeof loadChats ===
                    "function"
                ) {

                    try {

                        await loadChats();

                    } catch (error) {

                        console.warn(
                            "Could not refresh chats after upload:",
                            error
                        );
                    }
                }

            } catch (error) {

                console.error(
                    "Document upload failed:",
                    error
                );


                setStatus(
                    error.message ||
                    "Document upload failed.",
                    true
                );

            } finally {

                isUploading =
                    false;


                chooseFilesBtn.disabled =
                    false;


                // Allow selecting same file again.

                fileInput.value =
                    "";
            }

        }
    );
}


// =========================================================
// QUESTION INPUT
// =========================================================

function initializeQuestionInput() {

    const input =
        $("questionInput");

    const sendBtn =
        $("sendBtn");


    if (
        !input ||
        !sendBtn
    ) {

        console.error(
            "Question input elements not found."
        );

        return;
    }


    // -----------------------------------------------------
    // SEND BUTTON
    // -----------------------------------------------------

    sendBtn.addEventListener(
        "click",
        async () => {

            await sendQuestion();

        }
    );


    // -----------------------------------------------------
    // ENTER KEY
    // -----------------------------------------------------

    input.addEventListener(
        "keydown",
        async event => {

            if (
                event.key ===
                "Enter" &&
                !event.shiftKey
            ) {

                event.preventDefault();

                await sendQuestion();
            }

        }
    );


    // -----------------------------------------------------
    // AUTO RESIZE
    // -----------------------------------------------------

    input.addEventListener(
        "input",
        () => {

            input.style.height =
                "auto";


            input.style.height =
                `${Math.min(
                    input.scrollHeight,
                    180
                )}px`;
        }
    );
}


// =========================================================
// SEND QUESTION
// =========================================================

async function sendQuestion() {

    const input =
        $("questionInput");

    const sendBtn =
        $("sendBtn");


    if (!input) {
        return;
    }


    const question =
        input.value.trim();


    if (!question) {
        return;
    }


    if (isAsking) {
        return;
    }


    try {

        // -------------------------------------------------
        // ENSURE CHAT
        // -------------------------------------------------

        await ensureCurrentChat();


        isAsking =
            true;


        if (sendBtn) {

            sendBtn.disabled =
                true;
        }


        input.disabled =
            true;


        hideEmptyState();


        // -------------------------------------------------
        // SHOW USER MESSAGE
        // -------------------------------------------------

        renderMessage(
            "user",
            question
        );


        input.value =
            "";

        input.style.height =
            "auto";


        // -------------------------------------------------
        // SAVE USER MESSAGE
        // -------------------------------------------------

        try {

            await saveChatMessage(
                currentChatId,
                "user",
                question
            );

        } catch (error) {

            console.warn(
                "Could not save user message:",
                error
            );
        }


        // -------------------------------------------------
        // ASK BACKEND
        // -------------------------------------------------

        setStatus(
            "Thinking..."
        );


        const response =
            await askDocuments(
                currentChatId,
                question
            );


        console.log(
            "Ask response:",
            response
        );


        // -------------------------------------------------
        // ANSWER
        // -------------------------------------------------

        const answer =
            response?.answer ||
            response?.response ||
            response?.content ||
            "No answer returned.";


        // -------------------------------------------------
        // SOURCES
        // -------------------------------------------------

        const sources =
            response?.sources ||
            response?.citations ||
            [];


        if (
            Array.isArray(
                sources
            )
        ) {

            renderSources(
                sources
            );
        }


        // -------------------------------------------------
        // SAVE ASSISTANT MESSAGE
        // -------------------------------------------------

        try {

            await saveChatMessage(
                currentChatId,
                "assistant",
                answer
            );

        } catch (error) {

            console.warn(
                "Could not save assistant message:",
                error
            );
        }


        // -------------------------------------------------
        // SHOW ASSISTANT MESSAGE
        // -------------------------------------------------

        renderMessage(
            "assistant",
            answer
        );


        setStatus("");


        // -------------------------------------------------
        // REFRESH CHAT LIST
        // -------------------------------------------------

        if (
            typeof loadChats ===
            "function"
        ) {

            try {

                await loadChats();

            } catch (error) {

                console.warn(
                    "Could not refresh chats:",
                    error
                );
            }
        }


        return response;

    } catch (error) {

        console.error(
            "Question error:",
            error
        );


        setStatus(
            error.message ||
            "Something went wrong.",
            true
        );

    } finally {

        isAsking =
            false;


        if (sendBtn) {

            sendBtn.disabled =
                false;
        }


        input.disabled =
            false;


        input.focus();
    }
}


// =========================================================
// ACTION BUTTONS
// =========================================================

function initializeActionButtons() {

    const buttons =
        document.querySelectorAll(
            ".action-btn"
        );


    buttons.forEach(
        button => {

            button.addEventListener(
                "click",
                () => {

                    buttons.forEach(
                        item => {

                            item.classList.remove(
                                "active"
                            );

                        }
                    );


                    button.classList.add(
                        "active"
                    );


                    currentAction =
                        button.dataset.action ||
                        "ask";


                    handleActionChange(
                        currentAction
                    );

                }
            );

        }
    );
}


// =========================================================
// ACTION CHANGE
// =========================================================

function handleActionChange(
    action
) {

    switch (action) {

        case "ask":

            setStatus("");

            break;


        case "compare":

            setStatus(
                "Compare Documents will be connected next."
            );

            break;


        case "summarize":

            setStatus(
                "Summarize will be connected next."
            );

            break;


        case "quiz":

            setStatus(
                "Generate Quiz will be connected next."
            );

            break;


        case "flashcards":

            setStatus(
                "Flashcards will be connected next."
            );

            break;


        default:

            setStatus("");
    }
}


// =========================================================
// YOUTUBE
// =========================================================

function extractYouTubeVideoId(
    url
) {

    if (!url) {
        return null;
    }


    try {

        const parsed =
            new URL(url);


        // youtube.com/watch?v=...

        if (
            parsed.hostname.includes(
                "youtube.com"
            )
        ) {

            const id =
                parsed.searchParams.get(
                    "v"
                );


            if (id) {
                return id;
            }
        }


        // youtu.be/VIDEO_ID

        if (
            parsed.hostname.includes(
                "youtu.be"
            )
        ) {

            return parsed.pathname
                .replace(
                    "/",
                    ""
                )
                .split("?")[0];
        }


        // youtube.com/embed/VIDEO_ID

        if (
            parsed.pathname.startsWith(
                "/embed/"
            )
        ) {

            return parsed.pathname
                .split(
                    "/embed/"
                )[1]
                ?.split("/")[0] ||
                null;
        }

    } catch (error) {

        console.warn(
            "Invalid YouTube URL:",
            error
        );
    }


    return null;
}


function showYouTubeVideo(
    url
) {

    const panel =
        $("youtubePanel");

    const iframe =
        $("youtubePlayer");


    if (
        !panel ||
        !iframe
    ) {
        return;
    }


    const videoId =
        extractYouTubeVideoId(
            url
        );


    if (!videoId) {

        setStatus(
            "Please enter a valid YouTube URL.",
            true
        );

        return;
    }


    iframe.src =
        `https://www.youtube.com/embed/${videoId}?enablejsapi=1`;


    panel.classList.remove(
        "hidden"
    );


    panel.style.display =
        "block";


    setStatus(
        "YouTube video loaded."
    );
}


function hideYouTubeVideo() {

    const panel =
        $("youtubePanel");

    const iframe =
        $("youtubePlayer");


    if (iframe) {

        iframe.src =
            "";
    }


    if (panel) {

        panel.classList.add(
            "hidden"
        );

        panel.style.display =
            "none";
    }
}


// =========================================================
// YOUTUBE UI
// =========================================================

function initializeYouTubeUI() {

    const closeBtn =
        $("closeYoutubeBtn");

    const input =
        $("youtubeUrl");

    const analyzeBtn =
        $("analyzeYoutubeBtn");


    if (closeBtn) {

        closeBtn.addEventListener(
            "click",
            () => {

                hideYouTubeVideo();

            }
        );
    }


    if (
        analyzeBtn &&
        input
    ) {

        analyzeBtn.addEventListener(
            "click",
            async () => {

                const url =
                    input.value.trim();


                if (!url) {

                    setStatus(
                        "Please enter a YouTube URL.",
                        true
                    );

                    return;
                }


                const videoId =
                    extractYouTubeVideoId(
                        url
                    );


                if (!videoId) {

                    setStatus(
                        "Please enter a valid YouTube URL.",
                        true
                    );

                    return;
                }


                showYouTubeVideo(
                    url
                );


                // There is currently no YouTube
                // transcript-analysis API route
                // connected to this frontend.

                setStatus(
                    "YouTube video loaded. Transcript analysis endpoint is not connected yet."
                );
            }
        );
    }
}


// =========================================================
// API HEALTH
// =========================================================

async function initializeApiHealth() {

    try {

        if (
            typeof checkHealth !==
            "function"
        ) {

            console.warn(
                "checkHealth() not available."
            );

            return;
        }


        const result =
            await checkHealth();


        console.log(
            "API Health:",
            result
        );


        if (
            result?.status ===
            "healthy"
        ) {

            console.log(
                "✅ FastAPI connection OK"
            );

        } else {

            console.warn(
                "Unexpected health response:",
                result
            );
        }

    } catch (error) {

        console.error(
            "FastAPI health check failed:",
            error
        );


        // Do not throw here.
        // Chat loading should continue even if
        // the health endpoint fails.

        console.warn(
            "Continuing application initialization..."
        );
    }
}


// =========================================================
// APP INITIALIZATION
// =========================================================

async function initializeApp() {

    console.log(
        "🚀 Initializing Multi-Modal RAG Assistant..."
    );


    // -----------------------------------------------------
    // CHAT CONTROLS
    // -----------------------------------------------------
    //
    // Provided by chats.js.
    //

    if (
        typeof initializeChatControls ===
        "function"
    ) {

        try {

            initializeChatControls();

        } catch (error) {

            console.error(
                "Chat controls initialization failed:",
                error
            );
        }
    }


    // -----------------------------------------------------
    // ACTION BUTTONS
    // -----------------------------------------------------

    try {

        initializeActionButtons();

    } catch (error) {

        console.error(
            "Action buttons initialization failed:",
            error
        );
    }


    // -----------------------------------------------------
    // UPLOAD
    // -----------------------------------------------------

    try {

        initializeUploadUI();

    } catch (error) {

        console.error(
            "Upload UI initialization failed:",
            error
        );
    }


    // -----------------------------------------------------
    // QUESTION INPUT
    // -----------------------------------------------------

    try {

        initializeQuestionInput();

    } catch (error) {

        console.error(
            "Question input initialization failed:",
            error
        );
    }


    // -----------------------------------------------------
    // YOUTUBE
    // -----------------------------------------------------

    try {

        initializeYouTubeUI();

    } catch (error) {

        console.error(
            "YouTube UI initialization failed:",
            error
        );
    }


    // -----------------------------------------------------
    // BACKEND HEALTH
    // -----------------------------------------------------
    //
    // IMPORTANT:
    // Do NOT await this.
    //
    // A slow health endpoint must not block
    // Recent Chats from loading.
    //

    initializeApiHealth();


    // -----------------------------------------------------
    // LOAD CHATS
    // -----------------------------------------------------

    if (
        typeof loadChats ===
        "function"
    ) {

        try {

            console.log(
                "Loading chats..."
            );


            await loadChats();


            console.log(
                "Chats loaded successfully."
            );

        } catch (error) {

            console.error(
                "Could not load chats:",
                error
            );

            setStatus(
                "Could not load recent chats.",
                true
            );
        }

    } else {

        console.error(
            "loadChats() is not available. Check chats.js."
        );
    }


    // -----------------------------------------------------
    // RESTORE PREVIOUS CHAT
    // -----------------------------------------------------

    const savedChatId =
        localStorage.getItem(
            "rag_current_chat_id"
        );


    if (savedChatId) {

        console.log(
            "Saved chat found:",
            savedChatId
        );


        try {

            if (
                typeof openChat !==
                "function"
            ) {

                throw new Error(
                    "openChat() is not available."
                );
            }


            // currentChatId comes from chats.js.

            currentChatId =
                savedChatId;


            await openChat(
                savedChatId
            );


            // Keep persistence in sync.

            if (
                typeof currentChatId !==
                    "undefined" &&
                currentChatId
            ) {

                localStorage.setItem(
                    "rag_current_chat_id",
                    currentChatId
                );
            }


            console.log(
                "Restored previous chat:",
                savedChatId
            );

        } catch (error) {

            console.warn(
                "Could not restore previous chat:",
                error
            );


            // Remove only the invalid saved ID.

            localStorage.removeItem(
                "rag_current_chat_id"
            );


            if (
                typeof currentChatId !==
                "undefined"
            ) {

                currentChatId =
                    null;
            }
        }
    }


    // -----------------------------------------------------
    // DOCUMENT LIBRARY
    // -----------------------------------------------------

    renderDocumentLibrary();


    console.log(
        "✅ Multi-Modal RAG Assistant initialized."
    );
}


// =========================================================
// DOM READY
// =========================================================

if (
    document.readyState ===
    "loading"
) {

    document.addEventListener(
        "DOMContentLoaded",
        initializeApp,
        {
            once: true
        }
    );

} else {

    initializeApp();
}


// =========================================================
// GLOBAL EXPORTS
// =========================================================

window.RAGApp = {

    setStatus,

    renderMessages,

    renderMessage,

    renderSources,

    hideSources,

    renderDocumentLibrary,

    addUploadedDocument,

    extractYouTubeVideoId,

    showYouTubeVideo,

    hideYouTubeVideo,

    ensureCurrentChat,

    sendQuestion,

    initializeUploadUI,

    initializeQuestionInput,

    initializeYouTubeUI

};


// =========================================================
// END APP.JS
// =========================================================