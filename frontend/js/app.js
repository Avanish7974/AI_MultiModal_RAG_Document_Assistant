// =========================================================
// MULTI-MODAL RAG DOCUMENT ASSISTANT
// APP.JS
// =========================================================
//
// IMPORTANT:
//
// API functions are provided by api.js
// Chat state/functions are provided by chats.js
//
// DO NOT declare:
//
// API_BASE_URL
// currentChatId
// createChat
// getChats
// uploadDocument
// askDocuments
// saveChatMessage
// loadChats
// getChat
// selectChat
//
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

function setStatus(
    message,
    isError = false
) {

    const status =
        $("statusMessage");


    if (!status) {

        if (message) {
            console.log(message);
        }

        return;
    }


    status.textContent =
        message || "";


    status.classList.toggle(
        "error",
        Boolean(isError)
    );


    status.style.display =
        message
            ? "block"
            : "none";
}


// =========================================================
// EMPTY STATE
// =========================================================

function showEmptyState() {

    const emptyState =
        $("emptyState");


    if (emptyState) {

        emptyState.classList.remove(
            "hidden"
        );
    }
}


function hideEmptyState() {

    const emptyState =
        $("emptyState");


    if (emptyState) {

        emptyState.classList.add(
            "hidden"
        );
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
        document.createElement(
            "div"
        );


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


    // =====================================================
    // H3
    // =====================================================

    html =
        html.replace(
            /^### (.+)$/gm,
            "<h3>$1</h3>"
        );


    // =====================================================
    // H2
    // =====================================================

    html =
        html.replace(
            /^## (.+)$/gm,
            "<h2>$1</h2>"
        );


    // =====================================================
    // H1
    // =====================================================

    html =
        html.replace(
            /^# (.+)$/gm,
            "<h2>$1</h2>"
        );


    // =====================================================
    // BOLD
    // =====================================================

    html =
        html.replace(
            /\*\*(.*?)\*\*/g,
            "<strong>$1</strong>"
        );


    // =====================================================
    // INLINE CODE
    // =====================================================

    html =
        html.replace(
            /`([^`]+)`/g,
            "<code>$1</code>"
        );


    // =====================================================
    // BULLET POINTS
    // =====================================================

    html =
        html.replace(
            /^[•*-] (.+)$/gm,
            "<li>$1</li>"
        );


    // =====================================================
    // GROUP LIST ITEMS
    // =====================================================

    html =
        html.replace(
            /(<li>.*?<\/li>\s*)+/gs,
            match =>
                `<ul>${match}</ul>`
        );


    // =====================================================
    // NEW LINES
    // =====================================================

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

            top:
                main.scrollHeight,

            behavior:
                "smooth"
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
        document.createElement(
            "div"
        );


    message.className =
        `message ${
            role === "user"
                ? "user"
                : "assistant"
        }`;


    // =====================================================
    // HEADER
    // =====================================================

    const header =
        document.createElement(
            "div"
        );


    header.className =
        "message-header";


    const icon =
        document.createElement(
            "div"
        );


    icon.className =
        "message-icon";


    icon.textContent =
        role === "user"
            ? "👤"
            : "🤖";


    const name =
        document.createElement(
            "span"
        );


    name.textContent =
        role === "user"
            ? "You"
            : "RAG Assistant";


    header.appendChild(
        icon
    );

    header.appendChild(
        name
    );


    // =====================================================
    // CONTENT
    // =====================================================

    const contentElement =
        document.createElement(
            "div"
        );


    contentElement.className =
        "message-content";


    if (
        role === "assistant"
    ) {

        contentElement.classList.add(
            "answer-content"
        );


        contentElement.innerHTML =
            formatAnswer(
                content
            );

    } else {

        contentElement.textContent =
            content || "";
    }


    message.appendChild(
        header
    );


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

function renderMessages(
    messages
) {

    const container =
        $("chatContainer");


    if (!container) {
        return;
    }


    container.innerHTML =
        "";


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

        container.innerHTML =
            "";
    }
}


// =========================================================
// RENDER SOURCES
// =========================================================

function renderSources(
    sources
) {

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


    container.innerHTML =
        "";


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
                parts.join(
                    " • "
                );


            card.appendChild(
                name
            );


            if (
                parts.length
            ) {

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

function getChatDocumentsKey(
    chatId
) {

    return `rag_documents_${chatId}`;
}


function getChatDocuments(
    chatId
) {

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
            JSON.parse(
                stored
            );


        if (
            !Array.isArray(
                documents
            )
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


// =========================================================
// SAVE CHAT DOCUMENTS
// =========================================================

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
                Array.isArray(documents)
                    ? documents
                    : []
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

function formatFileSize(
    bytes
) {

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
            size /
            (1024 * 1024)
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

function getDocumentIcon(
    fileName
) {

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
// NORMALIZE DOCUMENT OBJECT
// =========================================================

function normalizeDocumentForUI(
    doc,
    fallbackFile = null
) {

    const fileName =
        doc?.file_name ||
        doc?.filename ||
        doc?.name ||
        fallbackFile?.name ||
        "Unnamed document";


    return {

        id:
            doc?.id ||
            doc?.file_id ||
            null,

        file_name:
            fileName,

        filename:
            fileName,

        name:
            fileName,

        file_type:
            doc?.file_type ||
            doc?.mime_type ||
            doc?.type ||
            (
                fileName
                    .split(".")
                    .pop() ||
                ""
            ).toUpperCase(),

        file_size:
            doc?.file_size ??
            doc?.size ??
            fallbackFile?.size ??
            0,

        chunks:
            doc?.chunks ??
            doc?.chunk_count ??
            doc?.chunks_count ??
            0,

        uploaded_at:
            doc?.uploaded_at ||
            doc?.created_at ||
            new Date().toISOString()
    };
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


    // currentChatId belongs to chats.js.

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


            // =================================================
            // ICON
            // =================================================

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


            // =================================================
            // INFO
            // =================================================

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
                doc.file_size !==
                    undefined &&
                doc.file_size !==
                    null
            ) {

                const formattedSize =
                    formatFileSize(
                        doc.file_size
                    );


                if (formattedSize) {

                    parts.push(
                        formattedSize
                    );
                }
            }


            if (
                doc.chunks !==
                    undefined &&
                doc.chunks !==
                    null &&
                Number(doc.chunks) > 0
            ) {

                parts.push(
                    `${doc.chunks} chunks`
                );
            }


            meta.textContent =
                parts.join(
                    " • "
                );


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


            // =================================================
            // STATUS
            // =================================================

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
// RESTORE DOCUMENTS FROM BACKEND
// =========================================================

async function refreshCurrentChatDocuments() {

    if (
        typeof currentChatId ===
            "undefined" ||
        !currentChatId
    ) {

        renderDocumentLibrary();

        return [];
    }


    try {

        console.log(
            "Refreshing backend documents for chat:",
            currentChatId
        );


        const response =
            await getChatFiles(
                currentChatId
            );


        let files = [];


        if (
            Array.isArray(response)
        ) {

            files =
                response;

        } else if (
            Array.isArray(
                response?.files
            )
        ) {

            files =
                response.files;

        } else if (
            Array.isArray(
                response?.documents
            )
        ) {

            files =
                response.documents;
        }


        const documents =
            files.map(
                file =>
                    normalizeDocumentForUI(
                        file
                    )
            );


        // Backend is source of truth.

        saveChatDocuments(
            currentChatId,
            documents
        );


        renderDocumentLibrary();


        console.log(
            "Documents restored:",
            documents
        );


        return documents;


    } catch (error) {

        console.warn(
            "Could not refresh documents from backend:",
            error
        );


        // Keep cached documents if backend
        // temporarily fails.

        renderDocumentLibrary();


        return getChatDocuments(
            currentChatId
        );
    }
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


    const documentData =
        normalizeDocumentForUI(
            uploadResult,
            file
        );


    const existingIndex =
        documents.findIndex(
            document =>
                document.file_name ===
                documentData.file_name
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


    currentChatId =
        result.chat_id;


    // Use chats.js persistence function
    // when available.

    if (
        typeof saveCurrentChatId ===
        "function"
    ) {

        saveCurrentChatId(
            currentChatId
        );

    } else {

        localStorage.setItem(
            "rag_current_chat_id",
            currentChatId
        );
    }


    console.log(
        "Created chat:",
        currentChatId
    );


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


    // =====================================================
    // OPEN UPLOAD PANEL
    // =====================================================

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


    // =====================================================
    // CLOSE UPLOAD PANEL
    // =====================================================

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


    // =====================================================
    // CHECK FILE INPUT
    // =====================================================

    if (
        !chooseFilesBtn ||
        !fileInput
    ) {

        console.error(
            "Upload UI error: chooseFilesBtn or fileInput not found."
        );

        return;
    }


    // =====================================================
    // CHOOSE FILES
    // =====================================================

    chooseFilesBtn.addEventListener(
        "click",
        () => {

            fileInput.click();

        }
    );


    // =====================================================
    // FILE SELECTED
    // =====================================================

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


            if (
                isUploading
            ) {

                return;
            }


            isUploading =
                true;


            chooseFilesBtn.disabled =
                true;


            try {

                let uploadedCount =
                    0;


                // =================================================
                // ENSURE CHAT
                // =================================================

                await ensureCurrentChat();


                if (!currentChatId) {

                    throw new Error(
                        "No active chat available for upload."
                    );
                }


                // =================================================
                // UPLOAD EACH FILE
                // =================================================

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


                    const result =
                        await uploadDocument(
                            currentChatId,
                            file
                        );


                    console.log(
                        "Upload response:",
                        result
                    );


                    // =================================================
                    // SHOW IMMEDIATELY
                    // =================================================

                    addUploadedDocument(
                        result,
                        file
                    );


                    uploadedCount++;
                }


                // =================================================
                // IMPORTANT:
                //
                // NOW GET FILES DIRECTLY FROM BACKEND.
                //
                // This guarantees that the document shown in UI
                // is actually associated with this chat.
                // =================================================

                await refreshCurrentChatDocuments();


                // =================================================
                // SUCCESS
                // =================================================

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


                // =================================================
                // CLOSE PANEL
                // =================================================

                if (
                    uploadPanel
                ) {

                    uploadPanel.classList.remove(
                        "open"
                    );
                }


                // =================================================
                // REFRESH SIDEBAR
                // =================================================

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


    // =====================================================
    // SEND BUTTON
    // =====================================================

    sendBtn.addEventListener(
        "click",
        async () => {

            await sendQuestion();

        }
    );


    // =====================================================
    // ENTER KEY
    // =====================================================

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


    // =====================================================
    // AUTO RESIZE
    // =====================================================

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


    // =====================================================
    // BASIC VALIDATION
    // =====================================================

    if (!input) {
        return;
    }


    const question =
        input.value.trim();


    if (!question) {
        return;
    }


    // =====================================================
    // DUPLICATE PROTECTION
    // =====================================================

    if (isAsking) {

        console.log(
            "Question already being processed."
        );

        return;
    }


    try {

        // =================================================
        // ENSURE CHAT EXISTS
        // =================================================

        await ensureCurrentChat();


        if (!currentChatId) {

            throw new Error(
                "No active chat available."
            );
        }


        // =================================================
        // LOCK REQUEST
        // =================================================

        isAsking =
            true;


        if (sendBtn) {

            sendBtn.disabled =
                true;
        }


        input.disabled =
            true;


        // =================================================
        // HIDE EMPTY STATE
        // =================================================

        hideEmptyState();


        // =================================================
        // CAPTURE QUESTION
        // =================================================

        const submittedQuestion =
            question;


        // =================================================
        // CLEAR INPUT IMMEDIATELY
        // =================================================

        input.value =
            "";


        input.style.height =
            "auto";


        // =================================================
        // SHOW USER MESSAGE
        // =================================================

        renderMessage(
            "user",
            submittedQuestion
        );


        // =================================================
        // AUTOMATIC CHAT NAME
        // =================================================
        //
        // We use the chats.js function.
        //
        // IMPORTANT:
        // We intentionally DO NOT await it.
        //
        // The actual question should not be blocked
        // by the title update.
        //
        // Manual rename is protected inside autoNameChat().
        // =================================================

        const chatsModule =
            window.RAGChats;


        if (
            chatsModule &&
            typeof chatsModule.autoNameChat ===
                "function"
        ) {

            chatsModule
                .autoNameChat(
                    currentChatId,
                    submittedQuestion
                )
                .catch(
                    error => {

                        console.warn(
                            "Automatic chat naming failed:",
                            error
                        );
                    }
                );
        }


        // =================================================
        // ASK BACKEND
        // =================================================
        //
        // IMPORTANT:
        //
        // DO NOT call saveChatMessage() here.
        //
        // The backend /ask endpoint is already responsible
        // for saving the question and answer.
        // =================================================

        setStatus(
            "Thinking..."
        );


        const response =
            await askDocuments(
                currentChatId,
                submittedQuestion
            );


        console.log(
            "Ask response:",
            response
        );


        // =================================================
        // EXTRACT ANSWER
        // =================================================

        const answer =
            response?.answer ||
            response?.response ||
            response?.content ||
            "No answer returned.";


        // =================================================
        // EXTRACT SOURCES
        // =================================================

        const sources =
            response?.sources ||
            response?.citations ||
            [];


        // =================================================
        // RENDER SOURCES
        // =================================================

        if (
            Array.isArray(
                sources
            )
        ) {

            renderSources(
                sources
            );
        }


        // =================================================
        // SHOW ASSISTANT MESSAGE
        // =================================================

        renderMessage(
            "assistant",
            answer
        );


        // =================================================
        // REFRESH SIDEBAR
        // =================================================
        //
        // This gets the latest title from backend.
        // =================================================

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


        // =================================================
        // RESTORE ACTIVE CHAT STYLE
        // =================================================

        if (
            typeof updateActiveChatStyles ===
            "function"
        ) {

            updateActiveChatStyles();

        } else if (
            window.RAGChats &&
            typeof window.RAGChats.highlightCurrentChat ===
                "function"
        ) {

            window.RAGChats
                .highlightCurrentChat();
        }


        // =================================================
        // CLEAR STATUS
        // =================================================

        setStatus("");


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

        // =================================================
        // UNLOCK
        // =================================================

        isAsking =
            false;


        if (sendBtn) {

            sendBtn.disabled =
                false;
        }


        if (input) {

            input.disabled =
                false;

            input.focus();
        }
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


        // =====================================================
        // youtube.com/watch?v=...
        // =====================================================

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


        // =====================================================
        // youtu.be/VIDEO_ID
        // =====================================================

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


        // =====================================================
        // youtube.com/embed/VIDEO_ID
        // =====================================================

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


// =========================================================
// SHOW YOUTUBE VIDEO
// =========================================================

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


// =========================================================
// HIDE YOUTUBE VIDEO
// =========================================================

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


        console.warn(
            "Continuing application initialization..."
        );
    }
}


// =========================================================
// RESTORE SAVED CHAT
// =========================================================

async function restoreSavedChat() {

    let savedChatId = null;


    // =====================================================
    // Prefer chats.js helper
    // =====================================================

    if (
        window.RAGChats &&
        typeof window.RAGChats.getSavedCurrentChatId ===
            "function"
    ) {

        savedChatId =
            window.RAGChats
                .getSavedCurrentChatId();

    } else {

        savedChatId =
            localStorage.getItem(
                "rag_current_chat_id"
            );
    }


    if (!savedChatId) {

        console.log(
            "No saved chat to restore."
        );

        return;
    }


    console.log(
        "Saved chat found:",
        savedChatId
    );


    try {

        // =================================================
        // Use chats.js selectChat
        // =================================================

        if (
            window.RAGChats &&
            typeof window.RAGChats.selectChat ===
                "function"
        ) {

            await window.RAGChats.selectChat(
                savedChatId
            );


            console.log(
                "Previous chat restored:",
                savedChatId
            );


            return;
        }


        // Fallback for older loading order.

        if (
            typeof selectChat ===
            "function"
        ) {

            await selectChat(
                savedChatId
            );

            return;
        }


        throw new Error(
            "selectChat() is not available."
        );


    } catch (error) {

        console.warn(
            "Could not restore previous chat:",
            error
        );


        // Remove only invalid saved ID.

        localStorage.removeItem(
            "rag_current_chat_id"
        );


        if (
            window.RAGChats &&
            typeof window.RAGChats.setCurrentChatId ===
                "function"
        ) {

            window.RAGChats
                .setCurrentChatId(
                    null
                );
        }
    }
}


// =========================================================
// APP INITIALIZATION
// =========================================================

async function initializeApp() {

    console.log(
        "🚀 Initializing Multi-Modal RAG Assistant..."
    );


    // =====================================================
    // CHAT CONTROLS
    // =====================================================
    //
    // chats.js now initializes itself.
    //
    // We still call initializeChatControls if available,
    // because this makes app.js compatible with the module.
    //
    // chats.js protects against duplicate listeners.
    // =====================================================

    try {

        if (
            window.RAGChats &&
            typeof window.RAGChats.initializeChatControls ===
                "function"
        ) {

            window.RAGChats
                .initializeChatControls();
        }

    } catch (error) {

        console.error(
            "Chat controls initialization failed:",
            error
        );
    }


    // =====================================================
    // ACTION BUTTONS
    // =====================================================

    try {

        initializeActionButtons();

    } catch (error) {

        console.error(
            "Action buttons initialization failed:",
            error
        );
    }


    // =====================================================
    // UPLOAD
    // =====================================================

    try {

        initializeUploadUI();

    } catch (error) {

        console.error(
            "Upload UI initialization failed:",
            error
        );
    }


    // =====================================================
    // QUESTION INPUT
    // =====================================================

    try {

        initializeQuestionInput();

    } catch (error) {

        console.error(
            "Question input initialization failed:",
            error
        );
    }


    // =====================================================
    // YOUTUBE
    // =====================================================

    try {

        initializeYouTubeUI();

    } catch (error) {

        console.error(
            "YouTube UI initialization failed:",
            error
        );
    }


    // =====================================================
    // BACKEND HEALTH
    // =====================================================
    //
    // Do not block app startup.
    // =====================================================

    initializeApiHealth();


    // =====================================================
    // LOAD CHATS
    // =====================================================

    try {

        if (
            window.RAGChats &&
            typeof window.RAGChats.loadChats ===
                "function"
        ) {

            await window.RAGChats
                .loadChats();

        } else if (
            typeof loadChats ===
            "function"
        ) {

            await loadChats();

        } else {

            throw new Error(
                "loadChats() is not available."
            );
        }


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


    // =====================================================
    // RESTORE PREVIOUS CHAT
    // =====================================================

    await restoreSavedChat();


    // =====================================================
    // DOCUMENT LIBRARY
    // =====================================================

    try {

        // If a chat was restored, get its documents
        // directly from backend.

        if (
            typeof currentChatId !==
                "undefined" &&
            currentChatId
        ) {

            await refreshCurrentChatDocuments();

        } else {

            renderDocumentLibrary();
        }


    } catch (error) {

        console.warn(
            "Could not restore document library:",
            error
        );


        renderDocumentLibrary();
    }


    // =====================================================
    // FINAL ACTIVE CHAT STATE
    // =====================================================

    if (
        window.RAGChats &&
        typeof window.RAGChats.highlightCurrentChat ===
            "function"
    ) {

        window.RAGChats
            .highlightCurrentChat();
    }


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

    refreshCurrentChatDocuments,

    extractYouTubeVideoId,

    showYouTubeVideo,

    hideYouTubeVideo,

    ensureCurrentChat,

    sendQuestion,

    initializeUploadUI,

    initializeQuestionInput,

    initializeYouTubeUI,

    restoreSavedChat
};


// =========================================================
// END APP.JS
// =========================================================