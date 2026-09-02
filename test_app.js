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
// This file connects:
//
// 💬 Ask Documents
// 📄 Summarize
// 🔄 Compare Documents
// 🎯 Generate Quiz
// 📑 Flashcards
// 📁 Upload Documents
// 🎥 YouTube Multimodal
//
// =========================================================


// =========================================================
// APPLICATION STATE
// =========================================================

let currentAction = "ask";

// Active YouTube URL for the current conversation.
let currentYouTubeUrl = "";

// The player is temporarily moved into the chat stream. Keep a reference
// to its original DOM host so chat rerenders do not destroy the player node.
let youtubePanelHost = null;

let isUploading = false;

let isAsking = false;

let isRunningAction = false;


// =========================================================
// DOM HELPER
// =========================================================

function $(id) {

    return document.getElementById(id);

}


// =========================================================
// STATUS MESSAGE
// =========================================================


// =========================================================
// STATUS MESSAGE / AI PROCESSING INDICATOR
// =========================================================
// =========================================================
// STATUS MESSAGE / CHATGPT-STYLE PROCESSING
// =========================================================

function setStatus(message, isError = false) {
    const status = $("statusMessage");
    const chatContainer = $("chatContainer");
    const text = message || "";

    // The status area is intentionally kept out of the top-right corner.
    // Every upload / processing / error state belongs to the conversation.
    const oldProcessing = document.querySelectorAll(
        ".rag-processing-status, .rag-inline-status"
    );
    oldProcessing.forEach(el => el.remove());

    if (status) {
        status.textContent = "";
        status.style.display = "none";
        status.classList.remove("error", "processing");
    }

    document.body.classList.remove("rag-processing");

    if (!text || !chatContainer) {
        return;
    }

    const userMessages = chatContainer.querySelectorAll(".message.user");
    const latestUserMessage = userMessages[userMessages.length - 1];

    const lower = text.toLowerCase();
    const isProcessing = !isError && (
        /thinking|analyzing|processing|generating|reading|searching|uploading|upload|comparing|summarizing|creating/.test(lower)
    );

    const row = document.createElement("div");
    row.className = isError
        ? "rag-inline-status rag-inline-status-error"
        : isProcessing
            ? "rag-processing-status"
            : "rag-inline-status";

    if (isProcessing) {
        row.innerHTML = `
            <span class="processing-dot" aria-hidden="true"></span>
            <span class="processing-text">${escapeHtml(text)}</span>
            <span class="processing-dots" aria-hidden="true">•••</span>
        `;
        document.body.classList.add("rag-processing");
    } else {
        row.innerHTML = `
            <span class="inline-status-icon" aria-hidden="true">${isError ? "⚠" : "✓"}</span>
            <span class="inline-status-text">${escapeHtml(text)}</span>
        `;
    }

    // Put every state immediately after the latest user message when one
    // exists. Otherwise it stays at the end of the conversation stream.
    if (latestUserMessage) {
        latestUserMessage.insertAdjacentElement("afterend", row);
    } else {
        chatContainer.appendChild(row);
    }

    scrollToBottom();

    // Success/info messages are temporary, but errors stay until the next
    // state/result replaces them so the user can actually read the error.
    if (!isProcessing && !isError) {
        window.setTimeout(() => {
            row.classList.add("is-hiding");
            window.setTimeout(() => row.remove(), 220);
        }, 4200);
    }
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

    currentYouTubeUrl = "";

    const container =
        $("chatContainer");


    if (container) {

        const youtubePanel = $("youtubePanel");

        if (youtubePanelHost && youtubePanel && youtubePanel.parentNode === container) {
            youtubePanelHost.appendChild(youtubePanel);
        }

        container.innerHTML =
            "";

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

    if (
        text === undefined ||
        text === null
    ) {

        return "";

    }


    /*
     * TABLE FIX — surgical patch
     *
     * Keep the original Markdown formatter completely intact.
     * Only extract Markdown comparison tables before escapeHtml()
     * so they can be rendered as real HTML tables.
     */

    const tableHtml = [];

    let source =
        String(text)
            .replace(/\r\n/g, "\n")
            .replace(/\r/g, "\n");


    const lines =
        source.split("\n");

    const outputLines = [];

    let i = 0;


    while (
        i < lines.length
    ) {

        const header =
            lines[i];

        const separator =
            lines[i + 1];


        /*
         * Only treat a block as a table when the SECOND row is
         * definitely a Markdown separator row. This prevents
         * normal text, citations, URLs, and other features from
         * being accidentally changed.
         */

        if (
            i + 1 < lines.length &&
            header.includes("|") &&
            separator.includes("|")
        ) {

            const separatorCells =
                separator
                    .trim()
                    .replace(/^\|/, "")
                    .replace(/\|$/, "")
                    .split("|")
                    .map(
                        cell =>
                            cell.trim()
                    );


            const isTable =
                separatorCells.length >= 2 &&
                separatorCells.every(
                    cell =>
                        /^:?-{3,}:?$/.test(
                            cell
                        )
                );


            if (
                isTable
            ) {

                const splitRow =
                    row => {

                        let value =
                            String(row)
                                .trim();


                        if (
                            value.startsWith("|")
                        ) {

                            value =
                                value.slice(1);

                        }


                        if (
                            value.endsWith("|")
                        ) {

                            value =
                                value.slice(
                                    0,
                                    -1
                                );

                        }


                        return value
                            .split("|")
                            .map(
                                cell =>
                                    cell.trim()
                            );

                    };


                const headers =
                    splitRow(header);

                const rows = [];

                let j =
                    i + 2;


                while (
                    j < lines.length &&
                    lines[j].includes("|") &&
                    lines[j].trim()
                ) {

                    rows.push(
                        splitRow(
                            lines[j]
                        )
                    );

                    j++;

                }


                const cellEscape =
                    value =>
                        escapeHtml(
                            String(
                                value || ""
                            )
                        );


                const headerHtml =
                    headers
                        .map(
                            cell =>
                                `<th>${cellEscape(cell)}</th>`
                        )
                        .join("");


                const bodyHtml =
                    rows
                        .map(
                            cells => {

                                return `
                                    <tr>
                                        ${headers
                                            .map(
                                                (_, index) =>
                                                    `<td>${cellEscape(
                                                        cells[index] || ""
                                                    )}</td>`
                                            )
                                            .join("")}
                                    </tr>
                                `;

                            }
                        )
                        .join("");


                const token =
                    `__RAG_COMPARISON_TABLE_${tableHtml.length}__`;


                tableHtml.push(
                    `
                    <div class="answer-table-wrap">
                        <table class="answer-table">
                            <thead>
                                <tr>${headerHtml}</tr>
                            </thead>
                            <tbody>
                                ${bodyHtml}
                            </tbody>
                        </table>
                    </div>
                    `
                );


                outputLines.push(
                    token
                );


                i = j;

                continue;

            }

        }


        outputLines.push(
            lines[i]
        );

        i++;

    }


    /*
     * IMPORTANT:
     * From this point onward this is the ORIGINAL formatter.
     * This preserves headings, bold, inline code, bullets,
     * lists, line breaks, and all other existing behavior.
     */

    let html =
        escapeHtml(
            outputLines.join("\n")
        );


    // -----------------------------------------------------
    // H3
    // -----------------------------------------------------

    html =
        html.replace(
            /^### (.+)$/gm,
            "<h3>$1</h3>"
        );


    // -----------------------------------------------------
    // H2
    // -----------------------------------------------------

    html =
        html.replace(
            /^## (.+)$/gm,
            "<h2>$1</h2>"
        );


    // -----------------------------------------------------
    // H1
    // -----------------------------------------------------

    html =
        html.replace(
            /^# (.+)$/gm,
            "<h2>$1</h2>"
        );


    // -----------------------------------------------------
    // BOLD
    // -----------------------------------------------------

    html =
        html.replace(
            /\*\*(.*?)\*\*/g,
            "<strong>$1</strong>"
        );


    // -----------------------------------------------------
    // INLINE CODE
    // -----------------------------------------------------

    html =
        html.replace(
            /`([^`]+)`/g,
            "<code>$1</code>"
        );


    // -----------------------------------------------------
    // BULLET POINTS
    // -----------------------------------------------------

    html =
        html.replace(
            /^[•*-] (.+)$/gm,
            "<li>$1</li>"
        );


    // -----------------------------------------------------
    // GROUP LIST ITEMS
    // -----------------------------------------------------

    html =
        html.replace(
            /(<li>.*?<\/li>\s*)+/gs,
            match =>
                `<ul>${match}</ul>`
        );


    // -----------------------------------------------------
    // NEW LINES
    // -----------------------------------------------------

    html =
        html.replace(
            /\n/g,
            "<br>"
        );


    /*
     * Restore the real table AFTER all normal Markdown
     * formatting is finished.
     */

    tableHtml.forEach(
        (table, index) => {

            const token =
                `__RAG_COMPARISON_TABLE_${index}__`;


            html =
                html.replace(
                    new RegExp(
                        token,
                        "g"
                    ),
                    table
                );

        }
    );


    return html;

}


// =========================================================

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


    requestAnimationFrame(
        () => {

            main.scrollTo({

                top:
                    main.scrollHeight,

                behavior:
                    "smooth"

            });

        }
    );

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


    // -----------------------------------------------------
    // HEADER
    // -----------------------------------------------------

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


    // -----------------------------------------------------
    // CONTENT
    // -----------------------------------------------------

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
// YOUTUBE SOURCE CARD
// =========================================================

function renderYouTubeSourceCard(
    videoUrl,
    ready = true
) {

    const container = $("chatContainer");

    if (!container || !videoUrl) {
        return;
    }

    const videoId =
        extractYouTubeVideoId(videoUrl);

    if (!videoId) {
        return;
    }

    const existing =
        container.querySelector(".youtube-source-card");

    if (existing) {
        return;
    }

    const card =
        document.createElement("div");

    card.className = "youtube-source-card";

    const thumbnail =
        document.createElement("img");

    thumbnail.className = "youtube-source-thumbnail";
    thumbnail.src =
        `https://img.youtube.com/vi/${encodeURIComponent(videoId)}/hqdefault.jpg`;
    thumbnail.alt = "YouTube video thumbnail";
    thumbnail.loading = "lazy";

    const info =
        document.createElement("div");

    info.className = "youtube-source-info";

    const eyebrow =
        document.createElement("div");

    eyebrow.className = "youtube-source-eyebrow";
    eyebrow.textContent = "YouTube video";

    const title =
        document.createElement("div");

    title.className = "youtube-source-title";
    title.textContent = "Video analyzed and ready for questions";

    const meta =
        document.createElement("div");

    meta.className = "youtube-source-meta";
    meta.textContent = ready
        ? "Transcript analyzed and summary is available in this chat"
        : "Analyzing video...";

    info.appendChild(eyebrow);
    info.appendChild(title);
    info.appendChild(meta);

    const watch =
        document.createElement("a");

    watch.className = "youtube-source-watch";
    watch.href = videoUrl;
    watch.target = "_blank";
    watch.rel = "noopener noreferrer";
    watch.textContent = "Watch ↗";

    card.appendChild(thumbnail);
    card.appendChild(info);
    card.appendChild(watch);

    container.appendChild(card);
}


function updateYouTubeSourceCardStatus(ready = true) {

    const card =
        document.querySelector(".youtube-source-card");

    if (!card) {
        return;
    }

    const meta =
        card.querySelector(".youtube-source-meta");

    if (meta) {
        meta.textContent = ready
            ? "Transcript analyzed and summary is available in this chat"
            : "Analyzing video...";
    }
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


    const youtubePanel = $("youtubePanel");

    if (youtubePanelHost && youtubePanel && youtubePanel.parentNode === container) {
        youtubePanelHost.appendChild(youtubePanel);
    }

    container.innerHTML =
        "";

    currentYouTubeUrl = "";


    if (
        !Array.isArray(messages) ||
        messages.length === 0
    ) {

        showEmptyState();

        return;

    }


    hideEmptyState();


    // Restore the active YouTube source from persisted chat messages.
    const youtubeMessage =
        messages.find(
            message =>
                message?.video_url &&
                extractYouTubeVideoId(message.video_url)
        );

    if (youtubeMessage) {
        currentYouTubeUrl =
            String(youtubeMessage.video_url).trim();

        renderYouTubeSourceCard(
            currentYouTubeUrl,
            true
        );

        // Restore the embedded player immediately below the YouTube
        // source card and above the conversation/summary.
        showYouTubeVideo(currentYouTubeUrl, true);
    }


    messages.forEach(
        message => {

            // Restore interactive quiz state from persisted chat data.
            // The backend stores the complete quiz payload so refresh/chat
            // switching does not destroy the interactive quiz.
            if (
                message &&
                message.mode === "quiz" &&
                message.quiz &&
                Array.isArray(message.quiz.questions)
            ) {

                modeQuizData = message.quiz;
                modeQuizSubmitted = false;

                renderQuiz(
                    modeQuizData,
                    message.sources || []
                );

                return;
            }

            // Restore interactive flashcards from persisted chat data.
            if (
                message &&
                message.mode === "flashcards" &&
                message.flashcards &&
                Array.isArray(message.flashcards.flashcards)
            ) {

                modeFlashcardData = message.flashcards;
                modeFlashcardIndex = 0;
                modeFlashcardFlipped = false;

                renderFlashcards(
                    message.sources || []
                );

                return;
            }

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

                Array.isArray(
                    documents
                )
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

        return;

    }


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


                if (
                    formattedSize
                ) {

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


    // -----------------------------------------------------
    // OPEN
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
    // CLOSE
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

    chooseFilesBtn.addEventListener(
        "click",
        () => {

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


                await ensureCurrentChat();


                if (
                    !currentChatId
                ) {

                    throw new Error(
                        "No active chat available for upload."
                    );

                }


                for (
                    const file of files
                ) {

                    setStatus(
                        `📄 Uploading ${file.name}...`
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


                    addUploadedDocument(
                        result,
                        file
                    );


                    uploadedCount++;

                }


                await refreshCurrentChatDocuments();

                // The upload request has completed and the document is now
                // visible in the Documents list. Remove the live upload
                // indicator before showing the final inline result.
                setStatus("");

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


                if (
                    uploadPanel
                ) {

                    uploadPanel.classList.remove(
                        "open"
                    );

                }


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
    // ENTER
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
// AUTOMATIC CHAT NAME
// =========================================================

function autoNameCurrentChat(
    question
) {

    try {

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
                    question
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

    } catch (error) {

        console.warn(
            "Could not auto-name chat:",
            error
        );

    }

}


// =========================================================
// SEND NORMAL DOCUMENT QUESTION
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


    if (
        isAsking ||
        isRunningAction
    ) {

        return;

    }


    try {

        await ensureCurrentChat();


        if (
            !currentChatId
        ) {

            throw new Error(
                "No active chat available."
            );

        }


        isAsking =
            true;


        if (sendBtn) {

            sendBtn.disabled =
                true;

        }


        input.disabled =
            true;


        hideEmptyState();


        const submittedQuestion =
            question;


        input.value =
            "";


        input.style.height =
            "auto";


        renderMessage(
            "user",
            submittedQuestion
        );


        autoNameCurrentChat(
            submittedQuestion
        );


        const isYouTubeQuestion =
            Boolean(
                currentYouTubeUrl &&
                extractYouTubeVideoId(currentYouTubeUrl)
            );

        setStatus(
            isYouTubeQuestion
                ? "Thinking about the analyzed video..."
                : "Thinking..."
        );


        const response = isYouTubeQuestion
            ? await askYouTubeMultimodal(
                currentChatId,
                currentYouTubeUrl,
                submittedQuestion
            )
            : await askDocuments(
                currentChatId,
                submittedQuestion
            );


        console.log(
            "Ask response:",
            response
        );


        const answer =
            response?.answer ||
            response?.response ||
            response?.content ||
            "No answer returned.";


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


        renderMessage(
            "assistant",
            answer
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
// ACTION RESULT HELPERS
// =========================================================

function getResponseAnswer(
    response,
    fallback = ""
) {

    if (
        response === undefined ||
        response === null
    ) {

        return fallback;

    }


    if (
        typeof response ===
        "string"
    ) {

        return response;

    }


    return (
        response.answer ||
        response.response ||
        response.content ||
        response.text ||
        fallback
    );

}


// =========================================================
// FORMAT QUIZ RESULT
// =========================================================

function formatQuizResult(
    response
) {

    const quiz =
        response?.quiz ||
        response?.data ||
        response;


    if (
        !quiz ||
        typeof quiz !==
        "object"
    ) {

        return getResponseAnswer(
            response,
            "Quiz generated successfully."
        );

    }


    const questions =
        Array.isArray(
            quiz.questions
        )
            ? quiz.questions
            : [];


    if (
        !questions.length
    ) {

        return getResponseAnswer(
            response,
            "Quiz generated successfully."
        );

    }


    let output =
        "## 🎯 Generated Quiz\n\n";


    questions.forEach(
        (question, index) => {

            const questionText =
                question.question ||
                question.text ||
                `Question ${index + 1}`;


            output +=
                `### ${index + 1}. ${questionText}\n\n`;


            const options =
                question.options ||
                question.choices ||
                [];


            if (
                Array.isArray(options)
            ) {

                options.forEach(
                    (option, optionIndex) => {

                        const letter =
                            String.fromCharCode(
                                65 + optionIndex
                            );


                        output +=
                            `- ${letter}. ${option}\n`;

                    }
                );

            }


            if (
                question.answer ||
                question.correct_answer
            ) {

                output +=
                    `\n**Answer:** ${
                        question.answer ||
                        question.correct_answer
                    }\n`;

            }


            if (
                question.explanation
            ) {

                output +=
                    `**Explanation:** ${question.explanation}\n`;

            }


            output +=
                "\n";

        }
    );


    return output;

}


// =========================================================
// FORMAT FLASHCARD RESULT
// =========================================================

function formatFlashcardResult(
    response
) {

    const data =
        response?.flashcards
            ? response
            : (
                response?.data ||
                response
            );


    const cards =
        Array.isArray(
            data?.flashcards
        )
            ? data.flashcards
            : [];


    if (
        !cards.length
    ) {

        return getResponseAnswer(
            response,
            "Flashcards generated successfully."
        );

    }


    let output =
        "## 📑 Flashcards\n\n";


    cards.forEach(
        (card, index) => {

            const front =
                card.front ||
                card.question ||
                "";


            const back =
                card.back ||
                card.answer ||
                "";


            output +=
                `### Card ${index + 1}\n\n`;


            output +=
                `**Question:** ${front}\n\n`;


            output +=
                `**Answer:** ${back}\n\n`;


            if (
                card.source
            ) {

                output +=
                    `📚 **Source:** ${card.source}\n\n`;

            }

        }
    );


    return output;

}


// =========================================================
// DOCUMENT ASSISTANT MODES
// SUMMARIZE / COMPARE / QUIZ / FLASHCARDS
// =========================================================

let modeQuizData = null;
let modeQuizSubmitted = false;
let modeFlashcardData = null;
let modeFlashcardIndex = 0;
let modeFlashcardFlipped = false;


// =========================================================
// MODE CONTROLS
// =========================================================

function getModeControls() {

    let section =
        document.getElementById("modeControls");

    if (section) {
        return section;
    }

    section = document.createElement("section");
    section.id = "modeControls";
    section.className = "mode-controls hidden";

    const chatContainer =
        document.getElementById("chatContainer");

    if (chatContainer && chatContainer.parentNode) {
        chatContainer.parentNode.insertBefore(
            section,
            chatContainer
        );
    }

    return section;
}


function clearModeResult() {

    const container =
        document.getElementById("chatContainer");

    if (!container) {
        return;
    }

    container
        .querySelectorAll(".mode-result")
        .forEach(element => element.remove());
}


function hideModeControls() {

    const controls =
        document.getElementById("modeControls");

    if (!controls) {
        return;
    }

    controls.classList.add("hidden");
    controls.innerHTML = "";
}


function modeButton(text, id) {
    return `
        <button
            id="${id}"
            class="primary-btn mode-action-button"
            type="button"
        >
            ${text}
        </button>
    `;
}


// =========================================================
// SUMMARIZE CONTROLS
// =========================================================

function renderSummaryControls() {

    const controls = getModeControls();

    controls.innerHTML = `
        <div class="mode-card">
            <div class="mode-card-title">📝 Summarize Source</div>
            <div class="mode-card-description">
                Create a summary from the documents or analyzed YouTube video in this chat.
            </div>

            <div class="mode-form-row">
                <label class="mode-field">
                    <span>Summary length</span>
                    <select id="summaryLength" class="mode-select">
                        <option value="Short">Short</option>
                        <option value="Medium" selected>Medium</option>
                        <option value="Detailed">Detailed</option>
                    </select>
                </label>
            </div>

            ${modeButton("✨ Generate Summary", "summarizeBtn")}
        </div>
    `;

    controls.classList.remove("hidden");

    document
        .getElementById("summarizeBtn")
        ?.addEventListener("click", runSummary);
}


// =========================================================
// COMPARE CONTROLS — EXACTLY 2 OR 3 DOCUMENTS
// =========================================================

async function renderCompareControls() {

    const controls = getModeControls();

    controls.innerHTML = `
        <div class="mode-card">
            <div class="mode-card-title">🔄 Compare Documents</div>
            <div class="mode-card-description">
                Select exactly 2 or 3 documents to compare.
            </div>

            <div class="mode-selection-hint">
                Selected: <strong id="compareSelectedCount">0</strong> / 3
            </div>

            <div id="compareFileList" class="compare-file-list">
                Loading documents...
            </div>

            ${modeButton("🔄 Compare Selected Documents", "compareBtn")}
        </div>
    `;

    controls.classList.remove("hidden");

    const list = document.getElementById("compareFileList");
    const compareBtn = document.getElementById("compareBtn");

    try {

        const documents =
            await refreshCurrentChatDocuments();

        if (!documents.length) {
            list.innerHTML = `
                <div class="mode-empty">
                    No documents uploaded in this chat.
                </div>
            `;
            compareBtn.disabled = true;
            compareBtn.classList.add("compare-locked");
            return;
        }

        // Keep Compare visually locked until at least two documents exist.
        compareBtn.classList.toggle(
            "compare-locked",
            documents.length < 2
        );

        list.innerHTML = documents
            .map((file, index) => {
                const name =
                    file.file_name ||
                    file.filename ||
                    file.name ||
                    `Document ${index + 1}`;

                return `
                    <label class="compare-file-item">
                        <input
                            type="checkbox"
                            class="compare-checkbox"
                            value="${escapeHtml(name)}"
                        >
                        <span class="compare-file-name">
                            ${escapeHtml(name)}
                        </span>
                    </label>
                `;
            })
            .join("");

        const checkboxes =
            Array.from(
                list.querySelectorAll(".compare-checkbox")
            );

        const updateCompareState = () => {
            const selected =
                checkboxes.filter(checkbox => checkbox.checked);

            const countElement =
                document.getElementById("compareSelectedCount");

            if (countElement) {
                countElement.textContent = String(selected.length);
            }

            // Hard limit: only 3 documents can be selected.
            checkboxes.forEach(checkbox => {
                checkbox.disabled =
                    !checkbox.checked && selected.length >= 3;
            });

            compareBtn.disabled =
                documents.length < 2 ||
                selected.length < 2 ||
                selected.length > 3;

            compareBtn.classList.toggle(
                "compare-locked",
                documents.length < 2
            );
        };

        checkboxes.forEach(checkbox => {
            checkbox.addEventListener("change", updateCompareState);
        });

        compareBtn.addEventListener("click", runComparison);
        updateCompareState();

    } catch (error) {

        list.innerHTML = `
            <div class="mode-error">
                Could not load documents.
            </div>
        `;

        compareBtn.disabled = true;
        compareBtn.classList.add("compare-locked");

        setStatus(
            error.message || "Could not load documents.",
            true
        );
    }
}


// =========================================================
// QUIZ CONTROLS — DEFAULT 6 QUESTIONS
// =========================================================

function renderQuizControls() {

    const controls = getModeControls();

    controls.innerHTML = `
        <div class="mode-card">
            <div class="mode-card-title">🎯 Generate Quiz</div>
            <div class="mode-card-description">
                Create an interactive MCQ quiz from your documents or analyzed YouTube video.
                Answers stay hidden until you submit.
            </div>

            <div class="mode-form-grid">
                <label class="mode-field">
                    <span>Questions</span>
                    <select id="quizQuestionCount" class="mode-select">
                        <option value="2">2</option>
                        <option value="3">3</option>
                        <option value="4">4</option>
                        <option value="5">5</option>
                        <option value="6" selected>6</option>
                        <option value="7">7</option>
                        <option value="8">8</option>
                        <option value="9">9</option>
                        <option value="10">10</option>
                    </select>
                </label>

                <label class="mode-field">
                    <span>Difficulty</span>
                    <select id="quizDifficulty" class="mode-select">
                        <option value="Easy">Easy</option>
                        <option value="Medium" selected>Medium</option>
                        <option value="Hard">Hard</option>
                    </select>
                </label>
            </div>

            ${modeButton("🎯 Generate Quiz", "generateQuizBtn")}
        </div>
    `;

    controls.classList.remove("hidden");

    document
        .getElementById("generateQuizBtn")
        ?.addEventListener("click", runQuiz);
}


// =========================================================
// FLASHCARD CONTROLS
// =========================================================

function renderFlashcardControls() {

    const controls = getModeControls();

    controls.innerHTML = `
        <div class="mode-card">
            <div class="mode-card-title">📑 Flashcards</div>
            <div class="mode-card-description">
                Generate interactive revision cards from your documents.
            </div>

            <div class="mode-form-grid">
                <label class="mode-field">
                    <span>Number of cards</span>
                    <select id="flashcardCount" class="mode-select">
                        <option value="2">2</option>
                        <option value="3">3</option>
                        <option value="4">4</option>
                        <option value="5">5</option>
                        <option value="6">6</option>
                        <option value="7">7</option>
                        <option value="8">8</option>
                        <option value="9">9</option>
                        <option value="10" selected>10</option>
                    </select>
                </label>

                <label class="mode-field">
                    <span>Difficulty</span>
                    <select id="flashcardDifficulty" class="mode-select">
                        <option value="Easy">Easy</option>
                        <option value="Medium" selected>Medium</option>
                        <option value="Hard">Hard</option>
                    </select>
                </label>
            </div>

            ${modeButton("📑 Generate Flashcards", "generateFlashcardsBtn")}
        </div>
    `;

    controls.classList.remove("hidden");

    document
        .getElementById("generateFlashcardsBtn")
        ?.addEventListener("click", runFlashcards);
}


// =========================================================
// YOUTUBE CONTEXT HELPER
// =========================================================
// A chat may contain either uploaded documents or an analyzed
// YouTube transcript.  The AI modes should work with both.

function hasYouTubeContext() {
    return Boolean(
        currentYouTubeUrl &&
        extractYouTubeVideoId(currentYouTubeUrl)
    );
}

async function getModeSourceState() {
    const documents = await refreshCurrentChatDocuments();

    let youtube = {
        analyzed: false,
        video_url: null,
        video_id: null
    };

    // Do not rely only on frontend state. The backend is the source of truth
    // when a chat is reopened or when the page was refreshed.
    if (currentChatId && typeof getYouTubeStatus === "function") {
        try {
            const response = await getYouTubeStatus(currentChatId);
            if (response?.analyzed) {
                youtube = response;
                if (response.video_url) {
                    currentYouTubeUrl = String(response.video_url).trim();
                }
            }
        } catch (error) {
            console.warn("Could not read YouTube mode status:", error);
        }
    }

    return {
        documents,
        youtube,
        hasYoutube: Boolean(youtube.analyzed && youtube.video_url),
        hasSource: Boolean(documents.length) || Boolean(youtube.analyzed && youtube.video_url)
    };
}


// =========================================================
// SUMMARY
// =========================================================

async function runSummary() {

    if (isRunningAction || isAsking || isUploading) {
        return;
    }

    isRunningAction = true;

    try {

        await ensureCurrentChat();

        const sourceState = await getModeSourceState();
        const documents = sourceState.documents;

        const length =
            document.getElementById("summaryLength")?.value ||
            "Medium";

        setStatus(
            sourceState.hasYoutube && !documents.length
                ? "📝 Reading the video transcript and generating summary..."
                : "📝 Reading the available source and generating summary..."
        );

        const response =
            await summarizeDocuments(
                currentChatId,
                length
            );

        clearModeResult();
        hideModeControls();

        renderMessage(
            "assistant",
            getResponseAnswer(
                response,
                "Summary generated successfully."
            )
        );

        renderSources(
            response?.sources ||
            response?.citations ||
            []
        );

        setStatus("");
        await refreshChatsAfterMode();

    } catch (error) {

        console.error("Summary error:", error);

        setStatus(
            error.message || "Could not summarize documents.",
            true
        );

    } finally {
        isRunningAction = false;
    }
}


// =========================================================
// COMPARISON
// =========================================================

async function runComparison() {

    if (isRunningAction || isAsking || isUploading) {
        return;
    }

    const selected =
        Array.from(
            document.querySelectorAll(
                ".compare-checkbox:checked"
            )
        )
        .map(checkbox => checkbox.value)
        .filter(Boolean);

    if (selected.length < 2) {
        setStatus(
            "Please select at least two documents.",
            true
        );
        return;
    }

    if (selected.length > 3) {
        setStatus(
            "You can compare a maximum of three documents.",
            true
        );
        return;
    }

    isRunningAction = true;

    try {

        await ensureCurrentChat();

        setStatus(
            "🔄 Comparing selected documents..."
        );

        const response =
            await compareDocuments(
                currentChatId,
                selected
            );

        clearModeResult();
        hideModeControls();

        renderMessage(
            "assistant",
            getResponseAnswer(
                response,
                "Documents compared successfully."
            )
        );

        renderSources(
            response?.sources ||
            response?.citations ||
            []
        );

        setStatus("");
        await refreshChatsAfterMode();

    } catch (error) {

        console.error("Comparison error:", error);

        setStatus(
            error.message || "Could not compare documents.",
            true
        );

    } finally {
        isRunningAction = false;
    }
}


// =========================================================
// QUIZ GENERATION
// =========================================================

async function runQuiz() {

    if (isRunningAction || isAsking || isUploading) {
        return;
    }

    isRunningAction = true;

    try {

        await ensureCurrentChat();

        const sourceState = await getModeSourceState();
        const documents = sourceState.documents;

        const count = Math.min(
            10,
            Math.max(
                2,
                Number(
                    document.getElementById("quizQuestionCount")?.value || 6
                )
            )
        );
        const difficulty =
            document.getElementById("quizDifficulty")?.value ||
            "Medium";

        setStatus(
            sourceState.hasYoutube && !documents.length
                ? `🎯 Reading the video transcript and generating ${count}-question quiz...`
                : `🎯 Reading the available source and generating ${count}-question quiz...`
        );

        const response =
            await generateDocumentQuiz(
                currentChatId,
                count,
                difficulty
            );

        modeQuizData =
            response?.quiz ||
            response?.data ||
            response;

        if (!modeQuizData || !Array.isArray(modeQuizData.questions) || !modeQuizData.questions.length) {
            throw new Error(
                "The quiz generator returned an invalid quiz format."
            );
        }

        // Enforce the requested 2–10 question range on the client.
        modeQuizData.questions =
            modeQuizData.questions.slice(0, count);

        modeQuizSubmitted = false;

        clearModeResult();
        hideModeControls();

        renderQuiz(
            modeQuizData,
            response?.sources || response?.citations || []
        );

        setStatus("");
        await refreshChatsAfterMode();

    } catch (error) {

        console.error("Quiz error:", error);

        setStatus(
            error.message || "Could not generate quiz.",
            true
        );

    } finally {
        isRunningAction = false;
    }
}


function getCorrectAnswerIndex(question) {

    if (Number.isInteger(question?.correct_answer)) {
        return question.correct_answer;
    }

    if (Number.isInteger(question?.correctAnswer)) {
        return question.correctAnswer;
    }

    if (typeof question?.correct_answer === "string") {
        const value = question.correct_answer.trim();
        const numeric = Number(value);

        if (Number.isInteger(numeric)) {
            return numeric;
        }

        if (Array.isArray(question.options)) {
            return question.options.findIndex(
                option => String(option).trim() === value
            );
        }
    }

    if (typeof question?.answer === "string" && Array.isArray(question.options)) {
        const value = question.answer.trim();
        const numeric = Number(value);

        if (Number.isInteger(numeric)) {
            return numeric;
        }

        return question.options.findIndex(
            option => String(option).trim() === value
        );
    }

    return -1;
}


// =========================================================
// RENDER INTERACTIVE QUIZ
// =========================================================

function renderQuiz(quiz, sources) {

    const container =
        document.getElementById("chatContainer");

    if (!container) {
        return;
    }

    hideEmptyState();

    const questions =
        Array.isArray(quiz?.questions)
            ? quiz.questions.slice(0, 10)
            : [];

    const result = document.createElement("div");
    result.className = "mode-result quiz-result";

    result.innerHTML = `
        <div class="mode-result-header">🧠 Interactive Quiz</div>
        <div class="mode-result-subtitle">
            ${questions.length} questions • Answers are revealed after submission
        </div>
        <div id="quizQuestions"></div>

        <div class="quiz-submit-row">
            <button id="submitQuizBtn" class="primary-btn" type="button">
                ✅ Submit Quiz
            </button>
        </div>

        <div id="quizScore" class="quiz-score hidden"></div>
    `;

    container.appendChild(result);

    const questionsContainer =
        result.querySelector("#quizQuestions");

    questions.forEach((question, index) => {

        const questionElement =
            document.createElement("div");

        questionElement.className = "quiz-question";

        const options =
            Array.isArray(question.options)
                ? question.options
                : Array.isArray(question.choices)
                    ? question.choices
                    : [];

        questionElement.innerHTML = `
            <div class="quiz-question-title">
                Question ${index + 1}
            </div>

            <div class="quiz-question-text">
                ${escapeHtml(
                    question.question ||
                    question.text ||
                    ""
                )}
            </div>

            <div class="quiz-options">
                ${options
                    .map((option, optionIndex) => `
                        <label class="quiz-option">
                            <input
                                type="radio"
                                name="quiz_${index}"
                                value="${optionIndex}"
                            >
                            <span class="quiz-option-letter">
                                ${String.fromCharCode(65 + optionIndex)}
                            </span>
                            <span class="quiz-option-text">
                                ${escapeHtml(option)}
                            </span>
                        </label>
                    `)
                    .join("")}
            </div>

            <div class="quiz-review hidden"></div>
        `;

        questionsContainer.appendChild(questionElement);
    });

    const submitButton =
        result.querySelector("#submitQuizBtn");

    submitButton.addEventListener("click", () => {

        if (modeQuizSubmitted) {
            return;
        }

        let score = 0;
        let answered = 0;

        questions.forEach((question, index) => {

            const selected =
                result.querySelector(
                    `input[name="quiz_${index}"]:checked`
                );

            const questionElement =
                result.querySelectorAll(".quiz-question")[index];

            const options =
                questionElement.querySelectorAll(
                    `input[name="quiz_${index}"]`
                );

            const correctIndex =
                getCorrectAnswerIndex(question);

            if (selected) {
                answered++;
            }

            options.forEach(option => {
                const label =
                    option.closest(".quiz-option");

                if (!label) {
                    return;
                }

                label.classList.remove("correct", "wrong");

                if (
                    Number(option.value) ===
                    correctIndex
                ) {
                    label.classList.add("correct");
                }
            });

            if (
                selected &&
                Number(selected.value) === correctIndex
            ) {
                score++;
            } else if (selected) {
                selected
                    .closest(".quiz-option")
                    ?.classList.add("wrong");
            }

            const review =
                questionElement.querySelector(".quiz-review");

            const correctText =
                Array.isArray(question.options) &&
                correctIndex >= 0
                    ? question.options[correctIndex]
                    : question.correct_answer ||
                      question.answer ||
                      "Not available";

            const yourText =
                selected && Array.isArray(question.options)
                    ? question.options[Number(selected.value)]
                    : "Not answered";

            review.innerHTML = `
                <div class="quiz-review-answer">
                    ${
                        selected &&
                        Number(selected.value) === correctIndex
                            ? "✓ Correct"
                            : "✗ Incorrect"
                    }
                </div>
                <div>Your answer: <strong>${escapeHtml(yourText)}</strong></div>
                <div>Correct answer: <strong>${escapeHtml(correctText)}</strong></div>
                ${
                    question.explanation
                        ? `<div class="quiz-explanation">💡 ${escapeHtml(question.explanation)}</div>`
                        : ""
                }
            `;

            review.classList.remove("hidden");
        });

        modeQuizSubmitted = true;

        const percentage =
            questions.length
                ? Math.round(
                    (score / questions.length) * 100
                )
                : 0;

        const scoreElement =
            result.querySelector("#quizScore");

        scoreElement.innerHTML = `
            <div class="quiz-score-main">
                ${percentage}%
            </div>
            <div class="quiz-score-detail">
                Score: ${score} / ${questions.length}
                • Answered: ${answered} / ${questions.length}
            </div>
        `;

        scoreElement.classList.remove("hidden");
        submitButton.disabled = true;
        submitButton.textContent = "✓ Quiz Submitted";

        result
            .querySelectorAll("input[type=radio]")
            .forEach(input => {
                input.disabled = true;
            });

        scrollToBottom();
    });

    if (sources.length) {
        renderSources(sources);
    }

    scrollToBottom();
}


// =========================================================
// FLASHCARDS
// =========================================================

async function runFlashcards() {

    if (isRunningAction || isAsking || isUploading) {
        return;
    }

    isRunningAction = true;

    try {

        await ensureCurrentChat();

        const sourceState = await getModeSourceState();
        const documents = sourceState.documents;

        const count = Math.min(
            10,
            Math.max(
                2,
                Number(
                    document.getElementById("flashcardCount")?.value || 10
                )
            )
        );

        const difficulty =
            document.getElementById("flashcardDifficulty")?.value ||
            "Medium";

        setStatus(
            sourceState.hasYoutube && !documents.length
                ? "📑 Creating flashcards from the video transcript..."
                : "📑 Creating interactive flashcards..."
        );

        const response =
            await generateDocumentFlashcards(
                currentChatId,
                count,
                difficulty
            );

        const flashcardPayload = response?.flashcards;
        const raw =
            Array.isArray(flashcardPayload)
                ? { flashcards: flashcardPayload }
                : flashcardPayload ||
                  response?.data ||
                  response;

        const cards =
            Array.isArray(raw?.flashcards)
                ? raw.flashcards
                : [];

        if (!cards.length) {
            throw new Error(
                "The flashcard generator returned no flashcards."
            );
        }

        modeFlashcardData = {
            ...raw,
            flashcards: cards
                .map(card => ({
                    ...card,
                    front:
                        card.front ||
                        card.question ||
                        "",
                    back:
                        card.back ||
                        card.answer ||
                        ""
                }))
        };

        modeFlashcardIndex = 0;
        modeFlashcardFlipped = false;

        clearModeResult();
        hideModeControls();

        renderFlashcards(
            response?.sources || response?.citations || []
        );

        setStatus("");
        await refreshChatsAfterMode();

    } catch (error) {

        console.error("Flashcard error:", error);

        setStatus(
            error.message || "Could not generate flashcards.",
            true
        );

    } finally {
        isRunningAction = false;
    }
}


function renderFlashcards(sources) {

    const container =
        document.getElementById("chatContainer");

    if (!container) {
        return;
    }

    hideEmptyState();

    const cards =
        modeFlashcardData?.flashcards || [];

    if (!cards.length) {
        return;
    }

    const result = document.createElement("div");
    result.className = "mode-result flashcard-result";

    result.innerHTML = `
        <div class="mode-result-header">📑 Flashcards</div>
        <div id="flashcardCounter" class="mode-result-subtitle"></div>

        <div id="flashcard" class="flashcard"></div>

        <div class="flashcard-actions">
            <button
                id="prevFlashcard"
                class="secondary-btn"
                type="button"
            >
                ← Previous
            </button>

            <button
                id="flipFlashcard"
                class="primary-btn"
                type="button"
            >
                🔄 Flip Card
            </button>

            <button
                id="nextFlashcard"
                class="secondary-btn"
                type="button"
            >
                Next →
            </button>
        </div>
    `;

    container.appendChild(result);

    result
        .querySelector("#flipFlashcard")
        .addEventListener("click", () => {
            modeFlashcardFlipped = !modeFlashcardFlipped;
            updateFlashcard(result);
        });

    result
        .querySelector("#prevFlashcard")
        .addEventListener("click", () => {
            if (modeFlashcardIndex > 0) {
                modeFlashcardIndex--;
                modeFlashcardFlipped = false;
                updateFlashcard(result);
            }
        });

    result
        .querySelector("#nextFlashcard")
        .addEventListener("click", () => {
            if (
                modeFlashcardIndex <
                cards.length - 1
            ) {
                modeFlashcardIndex++;
                modeFlashcardFlipped = false;
                updateFlashcard(result);
            }
        });

    updateFlashcard(result);

    if (sources.length) {
        renderSources(sources);
    }

    scrollToBottom();
}


function updateFlashcard(result) {

    const cards =
        modeFlashcardData?.flashcards || [];

    if (!cards.length) {
        return;
    }

    const card =
        cards[modeFlashcardIndex];

    const flashcard =
        result.querySelector("#flashcard");

    const counter =
        result.querySelector("#flashcardCounter");

    if (!card || !flashcard || !counter) {
        return;
    }

    counter.textContent =
        `Card ${modeFlashcardIndex + 1} of ${cards.length}`;

    const text =
        modeFlashcardFlipped
            ? card.back
            : card.front;

    flashcard.innerHTML = `
        <div class="flashcard-label">
            ${modeFlashcardFlipped ? "ANSWER" : "QUESTION"}
        </div>

        <div class="flashcard-text">
            ${escapeHtml(text || "")}
        </div>

        ${
            modeFlashcardFlipped && card.source
                ? `
                    <div class="flashcard-source">
                        Source: ${escapeHtml(card.source)}
                    </div>
                `
                : ""
        }
    `;

    const previous =
        result.querySelector("#prevFlashcard");

    const next =
        result.querySelector("#nextFlashcard");

    previous.disabled =
        modeFlashcardIndex === 0;

    next.disabled =
        modeFlashcardIndex === cards.length - 1;
}


// =========================================================
// REFRESH CHAT SIDEBAR
// =========================================================

async function refreshChatsAfterMode() {

    if (typeof loadChats === "function") {
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


// =========================================================
// ACTION BUTTONS
// =========================================================

function initializeActionButtons() {

    const buttons =
        document.querySelectorAll(".action-btn");

    if (!buttons.length) {
        console.warn("No action buttons found.");
        return;
    }

    // Prevent duplicate listeners if initialization is called again.
    buttons.forEach(button => {
        if (button.dataset.modeInitialized === "true") {
            return;
        }

        button.dataset.modeInitialized = "true";

        button.addEventListener("click", async () => {

            if (isRunningAction || isAsking || isUploading) {
                return;
            }

            buttons.forEach(item => {
                item.classList.remove("active");
            });

            button.classList.add("active");

            currentAction =
                button.dataset.action || "ask";

            clearModeResult();
            hideModeControls();

            if (currentAction === "ask") {
                setStatus("");
                document.getElementById("questionInput")?.focus();
                return;
            }

            if (currentAction === "summarize") {
                renderSummaryControls();
                return;
            }

            if (currentAction === "compare") {
                await renderCompareControls();
                return;
            }

            if (currentAction === "quiz") {
                renderQuizControls();
                return;
            }

            if (currentAction === "flashcards") {
                renderFlashcardControls();
                return;
            }

            // YouTube mode opens the existing YouTube workflow.
            if (currentAction === "youtube") {
                const uploadPanel = $("uploadPanel");
                const youtubeInput = $("youtubeUrl");

                if (uploadPanel) {
                    uploadPanel.classList.add("open");
                }

                if (youtubeInput) {
                    window.setTimeout(() => youtubeInput.focus(), 0);
                }

                setStatus(
                    "Paste a YouTube URL to start video analysis."
                );
            }
        });
    });
}


// =========================================================
// YOUTUBE VIDEO ID
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


        // -----------------------------------------------------
        // youtube.com/watch?v=
        // -----------------------------------------------------

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


        // -----------------------------------------------------
        // youtu.be/
        // -----------------------------------------------------

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


        // -----------------------------------------------------
        // youtube.com/embed/
        // -----------------------------------------------------

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
    url,
    silent = false
) {

    const panel = $("youtubePanel");
    const iframe = $("youtubePlayer");
    const container = $("chatContainer");

    if (!panel || !iframe || !container) {
        return;
    }

    if (!youtubePanelHost) {
        youtubePanelHost = panel.parentNode;
    }

    const videoId = extractYouTubeVideoId(url);

    if (!videoId) {
        if (!silent) {
            setStatus(
                "Please enter a valid YouTube URL.",
                true
            );
        }
        return;
    }

    // The player belongs directly to the conversation stream. This gives
    // us the clean order:
    // YouTube source card → video player → AI summary → chat.
    iframe.src =
        `https://www.youtube-nocookie.com/embed/${videoId}?enablejsapi=1&rel=0`;

    panel.classList.remove("hidden");
    panel.style.display = "block";

    const sourceCard =
        container.querySelector(".youtube-source-card");

    if (sourceCard) {
        sourceCard.insertAdjacentElement("afterend", panel);
    } else {
        container.insertBefore(panel, container.firstChild);
    }

    if (!silent) {
        setStatus("YouTube video loaded.");
    }
}


// =========================================================
// HIDE YOUTUBE VIDEO
// =========================================================

function hideYouTubeVideo() {

    // currentYouTubeUrl = "";

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

        if (youtubePanelHost && panel.parentNode !== youtubePanelHost) {
            youtubePanelHost.appendChild(panel);
        }

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


                if (isAsking || isRunningAction) {
                    return;
                }

                try {

                    await ensureCurrentChat();

                    if (!currentChatId) {
                        throw new Error(
                            "No active chat available."
                        );
                    }

                    currentAction = "youtube";
                    currentYouTubeUrl = url;

                    const uploadPanel = $("uploadPanel");
                    if (uploadPanel) {
                        uploadPanel.classList.remove("open");
                    }

                    hideEmptyState();

                    // Keep the conversation focused on the AI summary.
                    // The video itself is available from the compact source card.

                    // Analyze the video exactly once. The backend stores the
                    // resulting summary as persistent video context for this chat.
                    setStatus(
                        "Extracting transcript and generating a video summary..."
                    );

                    isAsking = true;
                    analyzeBtn.disabled = true;

                    renderYouTubeSourceCard(
                        currentYouTubeUrl,
                        false
                    );

                    // Show the real YouTube player immediately. The user can
                    // watch while transcript analysis is running.
                    showYouTubeVideo(
                        currentYouTubeUrl,
                        true
                    );

                    const response =
                        await analyzeYouTubeVideo(
                            currentChatId,
                            currentYouTubeUrl
                        );

                    const answer =
                        getResponseAnswer(
                            response,
                            "No YouTube summary returned."
                        );

                    renderMessage(
                        "assistant",
                        answer
                    );

                    updateYouTubeSourceCardStatus(true);

                    const questionInput = $("questionInput");
                    if (questionInput) {
                        questionInput.placeholder = "Ask anything about this video...";
                    }

                    if (typeof loadChats === "function") {
                        try {
                            await loadChats();
                        } catch (loadError) {
                            console.warn(
                                "Could not refresh chats after YouTube analysis:",
                                loadError
                            );
                        }
                    }

                    setStatus(
                        "YouTube summary ready. You can now ask questions."
                    );

                } catch (error) {

                    console.error(
                        "YouTube analysis failed:",
                        error
                    );

                    hideYouTubeVideo();

                    setStatus(
                        error.message ||
                        "Could not analyze YouTube video.",
                        true
                    );

                } finally {

                    isAsking = false;
                    analyzeBtn.disabled = false;

                }

            }
        );

    }

}


// =========================================================
// YOUTUBE MULTIMODAL ASK
// =========================================================
//
// This function is available for the UI/question flow.
//
// Backend:
//
// POST
// /api/chats/{chat_id}/youtube/ask
//
// =========================================================

async function askYouTubeQuestion(
    videoUrl,
    question
) {

    if (
        !videoUrl ||
        !videoUrl.trim()
    ) {

        throw new Error(
            "YouTube video URL is required."
        );

    }


    if (
        !question ||
        !question.trim()
    ) {

        throw new Error(
            "Question cannot be empty."
        );

    }


    await ensureCurrentChat();


    if (
        !currentChatId
    ) {

        throw new Error(
            "No active chat available."
        );

    }


    const response =
        await askYouTubeMultimodal(
            currentChatId,
            videoUrl.trim(),
            question.trim()
        );


    const answer =
        getResponseAnswer(
            response,
            "No YouTube answer returned."
        );


    const sources =
        response?.sources ||
        response?.citations ||
        [];


    renderMessage(
        "user",
        question.trim()
    );


    renderMessage(
        "assistant",
        answer
    );


    renderSources(
        sources
    );


    return response;

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

    let savedChatId =
        null;


    // -----------------------------------------------------
    // Prefer chats.js helper
    // -----------------------------------------------------

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
// SIDEBAR TOGGLE
// =========================================================

function initializeSidebarToggle() {
    const sidebar =
        document.getElementById("sidebar");

    const toggleButton =
        document.getElementById("sidebarToggle");

    if (!sidebar || !toggleButton) {
        return;
    }

    toggleButton.addEventListener(
        "click",
        () => {
            const isCollapsed =
                sidebar.classList.toggle(
                    "sidebar-collapsed"
                );

            toggleButton.textContent =
                isCollapsed ? "›" : "‹";

            toggleButton.title =
                isCollapsed
                    ? "Expand sidebar"
                    : "Collapse sidebar";
        }
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
    renderYouTubeSourceCard,
    updateYouTubeSourceCardStatus,

    showYouTubeVideo,

    hideYouTubeVideo,

    ensureCurrentChat,

    sendQuestion,

    askYouTubeQuestion,

    initializeUploadUI,

    initializeQuestionInput,

    initializeYouTubeUI,

    runDocumentAction,

    runSummarizeAction,

    runCompareAction,

    runQuizAction,

    runFlashcardsAction,

    restoreSavedChat

};


// =========================================================
// END APP.JS
// =========================================================
