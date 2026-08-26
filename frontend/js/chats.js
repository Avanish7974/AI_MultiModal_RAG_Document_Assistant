// =========================================================
// CHAT STATE
// =========================================================

let currentChatId = null;
let selectedChatForMenu = null;


// =========================================================
// INTERNAL FLAGS
// =========================================================

let chatControlsInitialized = false;
let outsideMenuListenerInitialized = false;


// =========================================================
// LOCAL STORAGE KEYS
// =========================================================

const CURRENT_CHAT_STORAGE_KEY =
    "rag_current_chat_id";


// =========================================================
// SAVE CURRENT CHAT ID
// =========================================================

function saveCurrentChatId(chatId) {

    if (!chatId) {

        localStorage.removeItem(
            CURRENT_CHAT_STORAGE_KEY
        );

        return;
    }

    localStorage.setItem(
        CURRENT_CHAT_STORAGE_KEY,
        chatId
    );
}


// =========================================================
// GET SAVED CURRENT CHAT ID
// =========================================================

function getSavedCurrentChatId() {

    return localStorage.getItem(
        CURRENT_CHAT_STORAGE_KEY
    );
}


// =========================================================
// LOAD ALL CHATS
// =========================================================

async function loadChats() {

    const container =
        document.getElementById(
            "recentChats"
        );

    if (!container) {
        return;
    }

    container.innerHTML = `
        <div class="chat-loading">
            Loading chats...
        </div>
    `;

    try {

        const data =
            await getChats();

        const chats =
            Array.isArray(data)
                ? data
                : (
                    Array.isArray(data?.chats)
                        ? data.chats
                        : []
                );

        renderChats(chats);

    } catch (error) {

        console.error(
            "Could not load chats:",
            error
        );

        container.innerHTML = `
            <div class="chat-loading">
                Unable to load chats.
            </div>
        `;
    }
}


// =========================================================
// GET CHAT ID FROM BACKEND OBJECT
// =========================================================

function getChatIdFromObject(chat) {

    return (
        chat?.chat_id ||
        chat?.id ||
        chat?.uuid ||
        null
    );
}


// =========================================================
// GET CHAT TITLE FROM BACKEND OBJECT
// =========================================================

function getChatTitleFromObject(chat) {

    return (
        chat?.title ||
        chat?.name ||
        "New Chat"
    );
}


// =========================================================
// RENDER CHAT LIST
// =========================================================

function renderChats(chats) {

    const container =
        document.getElementById(
            "recentChats"
        );

    if (!container) {
        return;
    }

    container.innerHTML = "";

    if (!Array.isArray(chats) || !chats.length) {

        container.innerHTML = `
            <div class="chat-loading">
                No chats yet.
            </div>
        `;

        return;
    }


    chats.forEach(chat => {

        const chatId =
            getChatIdFromObject(chat);

        if (!chatId) {
            return;
        }


        // =====================================================
        // ROW
        // =====================================================

        const row =
            document.createElement(
                "div"
            );

        row.className =
            "chat-row";

        row.dataset.chatId =
            chatId;


        // =====================================================
        // CHAT BUTTON
        // =====================================================

        const chatButton =
            document.createElement(
                "button"
            );

        chatButton.className =
            "chat-item";

        chatButton.type =
            "button";


        if (
            currentChatId &&
            String(chatId) === String(currentChatId)
        ) {

            chatButton.classList.add(
                "active"
            );
        }


        // =====================================================
        // CHAT TITLE
        // =====================================================

        // =====================================================
// CHAT ICON
// =====================================================

const icon =
    document.createElement(
        "span"
    );

icon.className =
    "chat-item-icon";

icon.innerHTML = `
    <svg
        width="18"
        height="18"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="1.8"
        stroke-linecap="round"
        stroke-linejoin="round"
        aria-hidden="true"
    >
        <path
            d="M20 11.5a7.5 7.5 0 0 1-7.5 7.5
               7.8 7.8 0 0 1-3.4-.8L4 19.5
               l1.3-4.2A7.5 7.5 0 1 1 20 11.5Z"
        />
    </svg>
`;

// =====================================================
// CHAT TITLE
// =====================================================

const title =
    document.createElement(
        "span"
    );

title.className =
    "chat-item-title";

title.textContent =
    getChatTitleFromObject(chat);


        chatButton.appendChild(
    icon
);

chatButton.appendChild(
    title
);


        // =====================================================
        // OPEN CHAT
        // =====================================================

        chatButton.addEventListener(
            "click",
            async event => {

                event.stopPropagation();

                await selectChat(
                    chatId
                );
            }
        );


        // =====================================================
        // THREE DOT BUTTON
        // =====================================================

        const menuButton =
            document.createElement(
                "button"
            );

        menuButton.className =
            "chat-menu-btn";

        menuButton.type =
            "button";

        menuButton.textContent =
            "⋮";

        menuButton.title =
            "Chat options";


        menuButton.addEventListener(
            "click",
            event => {

                event.preventDefault();

                event.stopPropagation();

                openChatContextMenu(
                    chatId,
                    menuButton
                );
            }
        );


        // =====================================================
        // BUILD ROW
        // =====================================================

        row.appendChild(
            chatButton
        );

        row.appendChild(
            menuButton
        );

        container.appendChild(
            row
        );

    });
}


// =========================================================
// CREATE NEW CHAT
// =========================================================

async function handleNewChat() {

    try {

        setStatus(
            "Creating new chat..."
        );


        const data =
            await createChat();


        if (!data?.chat_id && !data?.id) {

            throw new Error(
                "Server did not return a chat ID."
            );
        }


        currentChatId =
            data.chat_id ||
            data.id;


        saveCurrentChatId(
            currentChatId
        );


        // =====================================================
        // CLEAR OLD UI
        // =====================================================

        if (
            typeof clearChatInterface ===
            "function"
        ) {

            clearChatInterface();
        }


        if (
            typeof hideSources ===
            "function"
        ) {

            hideSources();
        }


        // =====================================================
        // CLEAR DOCUMENT LIBRARY
        // =====================================================

        try {

            localStorage.removeItem(
                `rag_documents_${currentChatId}`
            );

        } catch (error) {

            console.warn(
                "Could not clear document cache:",
                error
            );
        }


        if (
            typeof renderDocumentLibrary ===
            "function"
        ) {

            renderDocumentLibrary();
        }


        // =====================================================
        // REFRESH SIDEBAR
        // =====================================================

        await loadChats();

        updateActiveChatStyles();

        setStatus("");


    } catch (error) {

        console.error(
            "Could not create chat:",
            error
        );

        setStatus(
            `Could not create chat: ${error.message}`,
            true
        );
    }
}


// =========================================================
// SELECT / OPEN CHAT
// =========================================================

async function selectChat(chatId) {

    if (!chatId) {
        return;
    }


    try {

        setStatus(
            "Loading chat..."
        );


        // =====================================================
        // SET CURRENT CHAT
        // =====================================================

        currentChatId =
            chatId;

        saveCurrentChatId(
            chatId
        );


        updateActiveChatStyles();


        // =====================================================
        // LOAD CHAT
        // =====================================================

        const chat =
            await getChat(
                chatId
            );


        console.log(
            "Opened chat:",
            chat
        );


        // =====================================================
        // LOAD MESSAGES
        // =====================================================

        const messageData =
            await getChatMessages(
                chatId
            );


        const messages =
            Array.isArray(messageData)
                ? messageData
                : (
                    Array.isArray(messageData?.messages)
                        ? messageData.messages
                        : []
                );


        // =====================================================
        // LOAD FILES
        // =====================================================

        let files = [];

        try {

            const fileData =
                await getChatFiles(
                    chatId
                );

            files =
                normalizeChatFiles(
                    fileData
                );

            console.log(
                "Loaded chat files:",
                files
            );

        } catch (fileError) {

            console.warn(
                "Could not load chat files:",
                fileError
            );

            files = [];
        }


        // =====================================================
        // CLEAR CURRENT UI
        // =====================================================

        if (
            typeof clearChatInterface ===
            "function"
        ) {

            clearChatInterface();
        }


        // =====================================================
        // RENDER MESSAGES
        // =====================================================

        if (messages.length) {

            if (
                typeof renderMessages ===
                "function"
            ) {

                renderMessages(
                    messages
                );
            }

        } else {

            if (
                typeof showEmptyState ===
                "function"
            ) {

                showEmptyState();
            }
        }


        // =====================================================
        // HIDE OLD SOURCES
        // =====================================================

        if (
            typeof hideSources ===
            "function"
        ) {

            hideSources();
        }


        // =====================================================
        // RESTORE DOCUMENTS
        // =====================================================

        restoreChatDocuments(
            chatId,
            files
        );


        // =====================================================
        // REFRESH SIDEBAR
        // =====================================================

        await loadChats();

        updateActiveChatStyles();

        setStatus("");


    } catch (error) {

        console.error(
            "Could not open chat:",
            error
        );

        setStatus(
            `Could not open chat: ${error.message}`,
            true
        );
    }
}


// =========================================================
// NORMALIZE CHAT FILE RESPONSE
// =========================================================

function normalizeChatFiles(fileData) {

    let files = [];


    // =====================================================
    // POSSIBLE BACKEND RESPONSE FORMATS
    // =====================================================

    if (
        Array.isArray(fileData)
    ) {

        files =
            fileData;

    } else if (
        Array.isArray(fileData?.files)
    ) {

        files =
            fileData.files;

    } else if (
        Array.isArray(fileData?.documents)
    ) {

        files =
            fileData.documents;
    }


    return files.map(file => {

        const fileName =
            file?.file_name ||
            file?.filename ||
            file?.name ||
            "Unnamed document";


        const extension =
            getFileExtension(
                fileName
            );


        return {

            id:
                file?.id ||
                file?.file_id ||
                null,

            file_name:
                fileName,

            filename:
                fileName,

            name:
                fileName,

            file_type:
                file?.file_type ||
                file?.mime_type ||
                file?.type ||
                extension,

            file_size:
                file?.file_size ??
                file?.size ??
                0,

            chunks:
                file?.chunks ??
                file?.chunk_count ??
                file?.chunks_count ??
                0,

            uploaded_at:
                file?.uploaded_at ||
                file?.created_at ||
                null
        };

    });
}


// =========================================================
// GET FILE EXTENSION
// =========================================================

function getFileExtension(fileName) {

    if (!fileName) {
        return "";
    }


    const parts =
        String(fileName)
            .split(".");


    if (
        parts.length < 2
    ) {

        return "";
    }


    return parts
        .pop()
        .toUpperCase();
}


// =========================================================
// RESTORE CHAT DOCUMENTS
// =========================================================

// =========================================================
// RESTORE CHAT DOCUMENTS
// =========================================================

function restoreChatDocuments(
    chatId,
    files
) {

    if (!chatId) {
        return;
    }

    // ---------------------------------------------------------
    // Backend is the source of truth.
    // ---------------------------------------------------------

    const documents =
        Array.isArray(files)
            ? files
            : [];


    console.log(
        "Restoring documents for chat:",
        chatId,
        documents
    );


    // ---------------------------------------------------------
    // Store documents in the current chat state.
    //
    // This prevents the document list from disappearing
    // when the UI/sidebar is refreshed.
    // ---------------------------------------------------------

    try {

        localStorage.setItem(
            `rag_documents_${chatId}`,
            JSON.stringify(
                documents
            )
        );

    } catch (error) {

        console.warn(
            "Could not cache chat documents:",
            error
        );
    }


    // ---------------------------------------------------------
    // Also expose the documents globally if the existing
    // document-library code uses a global variable.
    // ---------------------------------------------------------

    if (
        typeof window !== "undefined"
    ) {

        window.currentChatDocuments =
            documents;

    }


    // ---------------------------------------------------------
    // Render document library.
    // ---------------------------------------------------------

    if (
        typeof renderDocumentLibrary ===
        "function"
    ) {

        renderDocumentLibrary();

    }
}


// =========================================================
// UPDATE ACTIVE CHAT STYLES
// =========================================================

function updateActiveChatStyles() {

    const rows =
        document.querySelectorAll(
            ".chat-row"
        );


    rows.forEach(row => {

        const button =
            row.querySelector(
                ".chat-item"
            );

        if (!button) {
            return;
        }


        const rowChatId =
            row.dataset.chatId;


        button.classList.toggle(
            "active",
            Boolean(
                currentChatId &&
                String(rowChatId) ===
                String(currentChatId)
            )
        );
    });
}


// =========================================================
// HIGHLIGHT CURRENT CHAT
// =========================================================

async function highlightCurrentChat() {

    await loadChats();

    updateActiveChatStyles();
}


// =========================================================
// CONTEXT MENU
// =========================================================

function openChatContextMenu(
    chatId,
    button
) {

    selectedChatForMenu =
        chatId;


    const menu =
        document.getElementById(
            "chatContextMenu"
        );


    if (!menu) {

        console.warn(
            "chatContextMenu element not found."
        );

        return;
    }


    const rect =
        button.getBoundingClientRect();


    menu.style.position =
        "fixed";

    menu.style.left =
        `${rect.right + 8}px`;

    menu.style.top =
        `${rect.top}px`;


    menu.classList.remove(
        "hidden"
    );
}


// =========================================================
// CLOSE CONTEXT MENU
// =========================================================

function closeChatContextMenu() {

    const menu =
        document.getElementById(
            "chatContextMenu"
        );


    if (menu) {

        menu.classList.add(
            "hidden"
        );
    }


    selectedChatForMenu =
        null;
}


// =========================================================
// DELETE CHAT
// =========================================================

async function handleDeleteChat() {

    const chatId =
        selectedChatForMenu;


    if (!chatId) {
        return;
    }


    closeChatContextMenu();


    const confirmed =
        window.confirm(
            "Delete this chat permanently?"
        );


    if (!confirmed) {
        return;
    }


    try {

        setStatus(
            "Deleting chat..."
        );


        await deleteChat(
            chatId
        );


        // =====================================================
        // REMOVE LOCAL DOCUMENT CACHE
        // =====================================================

        try {

            localStorage.removeItem(
                `rag_documents_${chatId}`
            );

        } catch (error) {

            console.warn(
                "Could not remove document cache:",
                error
            );
        }


        // =====================================================
        // IF ACTIVE CHAT WAS DELETED
        // =====================================================

        if (
            String(currentChatId) ===
            String(chatId)
        ) {

            currentChatId =
                null;

            saveCurrentChatId(
                null
            );


            if (
                typeof clearChatInterface ===
                "function"
            ) {

                clearChatInterface();
            }


            if (
                typeof hideSources ===
                "function"
            ) {

                hideSources();
            }


            if (
                typeof renderDocumentLibrary ===
                "function"
            ) {

                renderDocumentLibrary();
            }
        }


        // =====================================================
        // RELOAD SIDEBAR
        // =====================================================

        await loadChats();

        updateActiveChatStyles();

        setStatus("");


    } catch (error) {

        console.error(
            "Could not delete chat:",
            error
        );

        setStatus(
            `Could not delete chat: ${error.message}`,
            true
        );
    }
}


// =========================================================
// RENAME CHAT
// =========================================================

async function handleRenameChat() {

    const chatId =
        selectedChatForMenu;


    if (!chatId) {
        return;
    }


    closeChatContextMenu();


    try {

        // =====================================================
        // GET CURRENT TITLE
        // =====================================================

        const chat =
            await getChat(
                chatId
            );


        const currentTitle =
            getChatTitleFromObject(
                chat
            );


        // =====================================================
        // ASK FOR NEW TITLE
        // =====================================================

        const newTitle =
            window.prompt(
                "Enter a new chat name:",
                currentTitle
            );


        if (
            newTitle === null
        ) {

            return;
        }


        const cleanedTitle =
            newTitle
                .trim()
                .replace(
                    /\s+/g,
                    " "
                );


        // =====================================================
        // VALIDATION
        // =====================================================

        if (!cleanedTitle) {

            setStatus(
                "Chat name cannot be empty.",
                true
            );

            return;
        }


        if (
            cleanedTitle.length > 100
        ) {

            setStatus(
                "Chat name must be 100 characters or less.",
                true
            );

            return;
        }


        // =====================================================
        // UPDATE BACKEND
        // =====================================================

        setStatus(
            "Renaming chat..."
        );


        const updatedChat =
            await updateChatTitle(
                chatId,
                cleanedTitle
            );


        console.log(
            "Chat renamed successfully:",
            updatedChat
        );


        // =====================================================
        // IMMEDIATELY UPDATE SIDEBAR
        // =====================================================

        const row =
            document.querySelector(
                `.chat-row[data-chat-id="${CSS.escape(String(chatId))}"]`
            );


        if (row) {

            const titleElement =
                row.querySelector(
                    ".chat-item-title"
                );

            if (titleElement) {

                titleElement.textContent =
                    cleanedTitle;
            }
        }


        // =====================================================
        // REFRESH FROM BACKEND
        // =====================================================

        await loadChats();

        updateActiveChatStyles();

        setStatus("");


    } catch (error) {

        console.error(
            "Could not rename chat:",
            error
        );

        setStatus(
            `Could not rename chat: ${error.message}`,
            true
        );
    }
}


// =========================================================
// AUTOMATIC CHAT TITLE
// =========================================================
//
// First question:
//
// "what is cloud computing?"
//
// becomes:
//
// "What is cloud computing"
//
// IMPORTANT:
// Manual rename is NEVER overwritten.
// =========================================================

async function autoNameChat(
    chatId,
    question
) {

    if (
        !chatId ||
        !question
    ) {

        return;
    }


    try {

        const cleanQuestion =
            question
                .trim()
                .replace(
                    /\s+/g,
                    " "
                );


        if (!cleanQuestion) {
            return;
        }


        // =====================================================
        // GET CURRENT CHAT
        // =====================================================

        const chat =
            await getChat(
                chatId
            );


        const currentTitle =
            chat?.title ||
            chat?.name ||
            "";


        // =====================================================
        // DON'T OVERWRITE MANUAL NAME
        // =====================================================

        if (
            currentTitle &&
            currentTitle.trim() &&
            currentTitle.trim().toLowerCase() !==
                "new chat"
        ) {

            return;
        }


        // =====================================================
        // CREATE TITLE
        // =====================================================

        let title =
            cleanQuestion;


        // Remove ending punctuation

        title =
            title.replace(
                /[.!?]+$/,
                ""
            );


        // Capitalize first character

        title =
            title.charAt(0).toUpperCase() +
            title.slice(1);


        // Limit title length

        if (
            title.length > 60
        ) {

            title =
                title
                    .substring(
                        0,
                        57
                    )
                    .trim() +
                "...";
        }


        // =====================================================
        // UPDATE BACKEND
        // =====================================================

        await updateChatTitle(
            chatId,
            title
        );


        // =====================================================
        // REFRESH SIDEBAR
        // =====================================================

        await loadChats();

        updateActiveChatStyles();


        console.log(
            "Automatically renamed chat:",
            title
        );


    } catch (error) {

        // Automatic naming must NEVER
        // break the question flow.

        console.warn(
            "Could not automatically name chat:",
            error
        );
    }
}


// =========================================================
// INITIALIZE CHAT CONTROLS
// =========================================================

function initializeChatControls() {

    // Prevent duplicate event listeners

    if (
        chatControlsInitialized
    ) {

        return;
    }


    chatControlsInitialized =
        true;


    // =====================================================
    // NEW CHAT
    // =====================================================

    const newChatButton =
        document.getElementById(
            "newChatBtn"
        );


    if (newChatButton) {

        newChatButton.addEventListener(
            "click",
            handleNewChat
        );
    }


    // =====================================================
    // DELETE
    // =====================================================

    const deleteButton =
        document.getElementById(
            "deleteChatBtn"
        );


    if (deleteButton) {

        deleteButton.addEventListener(
            "click",
            handleDeleteChat
        );
    }


    // =====================================================
    // RENAME
    // =====================================================

    const renameButton =
        document.getElementById(
            "renameChatBtn"
        );


    if (renameButton) {

        renameButton.addEventListener(
            "click",
            handleRenameChat
        );
    }


    // =====================================================
    // CLOSE CONTEXT MENU
    // =====================================================

    if (
        !outsideMenuListenerInitialized
    ) {

        outsideMenuListenerInitialized =
            true;


        document.addEventListener(
            "click",
            event => {

                const menu =
                    document.getElementById(
                        "chatContextMenu"
                    );


                if (!menu) {
                    return;
                }


                if (
                    !menu.contains(
                        event.target
                    )
                ) {

                    closeChatContextMenu();
                }
            }
        );
    }
}

// =========================================================
// STEP 6 — SIDEBAR CONTROLS
// ChatGPT-style desktop collapse + mobile drawer.
// =========================================================

let sidebarControlsInitialized = false;

function initializeSidebarControls() {

    if (sidebarControlsInitialized) {
        return;
    }

    sidebarControlsInitialized = true;

    const sidebar =
        document.getElementById("sidebar");

    const toggle =
        document.getElementById("sidebarToggle");

    if (!sidebar || !toggle) {
        console.warn("Sidebar controls: required elements not found.");
        return;
    }

    const mobileBreakpoint = 760;

    function isMobile() {
        return window.innerWidth <= mobileBreakpoint;
    }

    function updateToggleIcon() {

        if (isMobile()) {

            toggle.textContent =
                sidebar.classList.contains("is-mobile-open")
                    ? "‹"
                    : "›";

            toggle.title =
                sidebar.classList.contains("is-mobile-open")
                    ? "Close sidebar"
                    : "Open sidebar";

            return;
        }

        toggle.textContent =
            sidebar.classList.contains("is-collapsed")
                ? "›"
                : "‹";

        toggle.title =
            sidebar.classList.contains("is-collapsed")
                ? "Expand sidebar"
                : "Collapse sidebar";
    }

    function closeMobileSidebar() {

        if (!isMobile()) {
            return;
        }

        sidebar.classList.remove("is-mobile-open");

        document.body.classList.remove(
            "sidebar-mobile-open"
        );

        updateToggleIcon();
    }

    toggle.addEventListener("click", event => {

        event.preventDefault();
        event.stopPropagation();

        if (isMobile()) {

            const isOpen =
                sidebar.classList.toggle(
                    "is-mobile-open"
                );

            document.body.classList.toggle(
                "sidebar-mobile-open",
                isOpen
            );

        } else {

            sidebar.classList.toggle(
                "is-collapsed"
            );
        }

        updateToggleIcon();
    });

    // Clicking outside closes mobile sidebar.
    document.addEventListener("click", event => {

        if (!isMobile()) {
            return;
        }

        if (
            !document.body.classList.contains(
                "sidebar-mobile-open"
            )
        ) {
            return;
        }

        if (sidebar.contains(event.target)) {
            return;
        }

        closeMobileSidebar();
    });

    // Escape closes mobile sidebar.
    document.addEventListener("keydown", event => {

        if (
            event.key === "Escape" &&
            isMobile()
        ) {
            closeMobileSidebar();
        }
    });

    // Reset mobile state when switching back to desktop.
    window.addEventListener("resize", () => {

        if (!isMobile()) {

            sidebar.classList.remove(
                "is-mobile-open"
            );

            document.body.classList.remove(
                "sidebar-mobile-open"
            );
        }

        updateToggleIcon();
    });

    updateToggleIcon();
}


// =========================================================
// INITIALIZE WHEN DOM IS READY
// =========================================================

function initializeChatsModule() {

    initializeSidebarControls();

    initializeChatControls();

    loadChats();
}


// =========================================================
// EXPORT CHAT FUNCTIONS
// =========================================================

window.RAGChats = {

    // State

    getCurrentChatId: () =>
        currentChatId,

    setCurrentChatId: chatId => {

        currentChatId =
            chatId;

        saveCurrentChatId(
            chatId
        );

        updateActiveChatStyles();
    },


    // Loading

    loadChats,

    renderChats,

    selectChat,

    highlightCurrentChat,


    // Creation

    handleNewChat,


    // Context menu

    openChatContextMenu,

    closeChatContextMenu,


    // Chat actions

    handleDeleteChat,

    handleRenameChat,

    autoNameChat,


    // Documents

    normalizeChatFiles,

    restoreChatDocuments,


    // State persistence

    getSavedCurrentChatId,

    saveCurrentChatId,


    // Initialization

    initializeChatControls,

    initializeChatsModule
};


// =========================================================
// AUTO INITIALIZE
// =========================================================

if (
    document.readyState ===
    "loading"
) {

    document.addEventListener(
        "DOMContentLoaded",
        initializeChatsModule
    );

} else {

    initializeChatsModule();
}


// =========================================================
// END CHATS.JS
// =========================================================