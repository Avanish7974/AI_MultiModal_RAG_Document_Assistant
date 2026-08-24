// =========================================================
// CHAT STATE
// =========================================================

let currentChatId = null;
let selectedChatForMenu = null;


// =========================================================
// LOAD ALL CHATS
// =========================================================

async function loadChats() {

    const container =
        document.getElementById("recentChats");

    if (!container) {
        return;
    }

    container.innerHTML = `
        <div class="chat-loading">
            Loading chats...
        </div>
    `;

    try {

        const data = await getChats();

        const chats = data?.chats || [];

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
// RENDER CHAT LIST
// =========================================================

function renderChats(chats) {

    const container =
        document.getElementById("recentChats");

    if (!container) {
        return;
    }

    container.innerHTML = "";

    if (!chats.length) {

        container.innerHTML = `
            <div class="chat-loading">
                No chats yet.
            </div>
        `;

        return;
    }


    chats.forEach(chat => {

        const row =
            document.createElement("div");

        row.className = "chat-row";


        // =================================================
        // CHAT BUTTON
        // =================================================

        const chatButton =
            document.createElement("button");

        chatButton.className =
            "chat-item";


        if (
            currentChatId &&
            chat.chat_id === currentChatId
        ) {

            chatButton.classList.add(
                "active"
            );
        }


        const title =
            document.createElement("span");

        title.className =
            "chat-item-title";

        title.textContent =
            chat.title || "New Chat";


        chatButton.appendChild(title);


        chatButton.addEventListener(
            "click",
            async () => {

                await selectChat(
                    chat.chat_id
                );
            }
        );


        // =================================================
        // THREE DOT BUTTON
        // =================================================

        const menuButton =
            document.createElement("button");

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

                event.stopPropagation();

                openChatContextMenu(
                    chat.chat_id,
                    menuButton
                );
            }
        );


        // =================================================
        // BUILD ROW
        // =================================================

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

        if (!data?.chat_id) {

            throw new Error(
                "Server did not return a chat ID."
            );
        }


        currentChatId =
            data.chat_id;


        // Clear current conversation

        clearChatInterface();


        // Reload sidebar

        await loadChats();


        // Highlight new chat

        highlightCurrentChat();


        setStatus(
            ""
        );


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
// SELECT CHAT
// =========================================================

async function selectChat(chatId) {

    try {

        setStatus(
            "Loading chat..."
        );


        currentChatId =
            chatId;


        highlightCurrentChat();


        // -------------------------------------------------
        // Get chat information
        // -------------------------------------------------

        const chat =
            await getChat(chatId);


        // -------------------------------------------------
        // Get messages
        // -------------------------------------------------

        const data =
            await getChatMessages(
                chatId
            );


        const messages =
            data?.messages || [];


        // -------------------------------------------------
        // Render conversation
        // -------------------------------------------------

        clearChatInterface();


        if (messages.length) {

            renderMessages(
                messages
            );

        } else {

            showEmptyState();
        }


        // -------------------------------------------------
        // Hide sources from previous chat
        // -------------------------------------------------

        hideSources();


        setStatus(
            ""
        );


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
// HIGHLIGHT CURRENT CHAT
// =========================================================

function highlightCurrentChat() {

    const chatButtons =
        document.querySelectorAll(
            ".chat-item"
        );

    chatButtons.forEach(button => {

        button.classList.remove(
            "active"
        );
    });


    // Re-render is the safest way to ensure
    // active state remains synchronized.

    loadChats();
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
        return;
    }


    const rect =
        button.getBoundingClientRect();


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


        // If deleted chat was active

        if (
            currentChatId === chatId
        ) {

            currentChatId =
                null;

            clearChatInterface();
        }


        await loadChats();


        setStatus(
            ""
        );


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
//
// Backend currently does NOT expose a rename endpoint.
//
// Therefore we intentionally do not fake this functionality.
//
// Once we add:
// PATCH /api/chats/{chat_id}
//
// we will implement rename here.
// =========================================================

async function handleRenameChat() {

    const chatId =
        selectedChatForMenu;


    if (!chatId) {
        return;
    }


    closeChatContextMenu();


    setStatus(
        "Rename is not available from the API yet."
    );
}


// =========================================================
// INITIALIZE CHAT CONTROLS
// =========================================================

function initializeChatControls() {

    // -----------------------------------------------------
    // New Chat
    // -----------------------------------------------------

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


    // -----------------------------------------------------
    // Delete
    // -----------------------------------------------------

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


    // -----------------------------------------------------
    // Rename
    // -----------------------------------------------------

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


    // -----------------------------------------------------
    // Close menu when clicking elsewhere
    // -----------------------------------------------------

    document.addEventListener(
        "click",
        event => {

            const menu =
                document.getElementById(
                    "chatContextMenu"
                );


            if (
                menu &&
                !menu.contains(event.target)
            ) {

                closeChatContextMenu();
            }
        }
    );
}