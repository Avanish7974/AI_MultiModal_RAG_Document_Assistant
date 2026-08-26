// =========================================================
// DOCUMENT ASSISTANT MODES
// SUMMARIZE / COMPARE / QUIZ / FLASHCARDS
// =========================================================

let modeQuizData = null;
let modeFlashcardData = null;
let modeFlashcardIndex = 0;
let modeFlashcardFlipped = false;


// =========================================================
// DOM
// =========================================================

function getModeControls() {

    let section =
        document.getElementById(
            "modeControls"
        );

    if (section) {
        return section;
    }

    section =
        document.createElement(
            "section"
        );

    section.id =
        "modeControls";

    section.className =
        "mode-controls";

    const chatContainer =
        document.getElementById(
            "chatContainer"
        );

    if (chatContainer) {

        chatContainer.parentNode.insertBefore(
            section,
            chatContainer
        );
    }

    return section;
}


// =========================================================
// CLEAR MODE RESULT
// =========================================================

function clearModeResult() {

    const container =
        document.getElementById(
            "chatContainer"
        );

    if (!container) {
        return;
    }

    const generated =
        container.querySelectorAll(
            ".mode-result"
        );

    generated.forEach(
        element =>
            element.remove()
    );
}


// =========================================================
// BASIC CONTROL HTML
// =========================================================

function modeButton(
    text,
    id
) {

    return `
        <button
            id="${id}"
            class="primary-btn mode-action-button"
        >
            ${text}
        </button>
    `;
}


// =========================================================
// SUMMARIZE CONTROLS
// =========================================================

function renderSummaryControls() {

    const controls =
        getModeControls();

    controls.innerHTML = `
        <div class="mode-card">

            <div class="mode-card-title">
                📄 Summarize Documents
            </div>

            <div class="mode-card-description">
                Create one combined summary from
                all documents in this chat.
            </div>

            <div class="mode-form-row">

                <label>
                    Summary length

                    <select
                        id="summaryLength"
                        class="mode-select"
                    >
                        <option value="Short">
                            Short
                        </option>

                        <option
                            value="Medium"
                            selected
                        >
                            Medium
                        </option>

                        <option value="Detailed">
                            Detailed
                        </option>
                    </select>
                </label>

            </div>

            ${modeButton(
                "✨ Summarize All Documents",
                "summarizeBtn"
            )}

        </div>
    `;

    controls.classList.remove(
        "hidden"
    );

    document
        .getElementById(
            "summarizeBtn"
        )
        .addEventListener(
            "click",
            runSummary
        );
}


// =========================================================
// COMPARE CONTROLS
// =========================================================

async function renderCompareControls() {

    const controls =
        getModeControls();

    controls.innerHTML = `
        <div class="mode-card">
            <div class="mode-card-title">
                🔄 Compare Documents
            </div>

            <div class="mode-card-description">
                Select two or more documents to
                compare their contents.
            </div>

            <div
                id="compareFileList"
                class="compare-file-list"
            >
                Loading documents...
            </div>

            ${modeButton(
                "🔄 Compare Selected Documents",
                "compareBtn"
            )}
        </div>
    `;

    controls.classList.remove(
        "hidden"
    );

    const list =
        document.getElementById(
            "compareFileList"
        );

    try {

        const response =
            await getChatFiles(
                currentChatId
            );

        let files = [];

        if (
            Array.isArray(response)
        ) {

            files = response;

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

        if (!files.length) {

            list.innerHTML = `
                <div class="mode-empty">
                    No documents uploaded
                    in this chat.
                </div>
            `;

            document
                .getElementById(
                    "compareBtn"
                )
                .disabled = true;

            return;
        }

        list.innerHTML = files
            .map(
                (file, index) => {

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
                                value="${escapeHtml(
                                    name
                                )}"
                            >

                            <span>
                                ${escapeHtml(
                                    name
                                )}
                            </span>

                        </label>
                    `;
                }
            )
            .join("");

        document
            .getElementById(
                "compareBtn"
            )
            .addEventListener(
                "click",
                runComparison
            );

    } catch (error) {

        list.innerHTML = `
            <div class="mode-error">
                Could not load documents.
            </div>
        `;

        setStatus(
            error.message ||
            "Could not load documents.",
            true
        );
    }
}


// =========================================================
// QUIZ CONTROLS
// =========================================================

function renderQuizControls() {

    const controls =
        getModeControls();

    controls.innerHTML = `
        <div class="mode-card">

            <div class="mode-card-title">
                🎯 Generate Quiz
            </div>

            <div class="mode-card-description">
                Create an interactive MCQ quiz
                from your documents.
            </div>

            <div class="mode-form-grid">

                <label>
                    Questions

                    <select
                        id="quizQuestionCount"
                        class="mode-select"
                    >
                        <option value="3">
                            3
                        </option>

                        <option
                            value="5"
                            selected
                        >
                            5
                        </option>

                        <option value="10">
                            10
                        </option>

                        <option value="15">
                            15
                        </option>
                    </select>
                </label>

                <label>
                    Difficulty

                    <select
                        id="quizDifficulty"
                        class="mode-select"
                    >
                        <option value="Easy">
                            Easy
                        </option>

                        <option
                            value="Medium"
                            selected
                        >
                            Medium
                        </option>

                        <option value="Hard">
                            Hard
                        </option>
                    </select>
                </label>

            </div>

            ${modeButton(
                "🎯 Generate Quiz",
                "generateQuizBtn"
            )}

        </div>
    `;

    controls.classList.remove(
        "hidden"
    );

    document
        .getElementById(
            "generateQuizBtn"
        )
        .addEventListener(
            "click",
            runQuiz
        );
}


// =========================================================
// FLASHCARD CONTROLS
// =========================================================

function renderFlashcardControls() {

    const controls =
        getModeControls();

    controls.innerHTML = `
        <div class="mode-card">

            <div class="mode-card-title">
                📑 Flashcards
            </div>

            <div class="mode-card-description">
                Create interactive revision
                flashcards from your documents.
            </div>

            <div class="mode-form-grid">

                <label>
                    Number of cards

                    <select
                        id="flashcardCount"
                        class="mode-select"
                    >
                        <option value="5">
                            5
                        </option>

                        <option
                            value="10"
                            selected
                        >
                            10
                        </option>

                        <option value="15">
                            15
                        </option>

                        <option value="20">
                            20
                        </option>

                        <option value="30">
                            30
                        </option>
                    </select>
                </label>

                <label>
                    Difficulty

                    <select
                        id="flashcardDifficulty"
                        class="mode-select"
                    >
                        <option value="Easy">
                            Easy
                        </option>

                        <option
                            value="Medium"
                            selected
                        >
                            Medium
                        </option>

                        <option value="Hard">
                            Hard
                        </option>
                    </select>
                </label>

            </div>

            ${modeButton(
                "📑 Generate Flashcards",
                "generateFlashcardsBtn"
            )}

        </div>
    `;

    controls.classList.remove(
        "hidden"
    );

    document
        .getElementById(
            "generateFlashcardsBtn"
        )
        .addEventListener(
            "click",
            runFlashcards
        );
}


// =========================================================
// HIDE CONTROLS
// =========================================================

function hideModeControls() {

    const controls =
        document.getElementById(
            "modeControls"
        );

    if (controls) {

        controls.classList.add(
            "hidden"
        );

        controls.innerHTML =
            "";
    }
}


// =========================================================
// SUMMARY
// =========================================================

async function runSummary() {

    try {

        await ensureCurrentChat();

        setStatus(
            "📝 Reading documents and generating summary..."
        );

        const length =
            document.getElementById(
                "summaryLength"
            ).value;

        const response =
            await apiRequest(
                `/api/chats/${encodeURIComponent(
                    currentChatId
                )}/summarize`,
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body: JSON.stringify({
                        length
                    })
                }
            );

        clearModeResult();

        renderMessage(
            "assistant",
            response.answer
        );

        renderSources(
            response.sources || []
        );

        setStatus("");

        await refreshChatsAfterMode();

    } catch (error) {

        console.error(
            "Summary error:",
            error
        );

        setStatus(
            error.message ||
            "Could not summarize documents.",
            true
        );
    }
}


// =========================================================
// COMPARISON
// =========================================================

async function runComparison() {

    const selected =
        Array.from(
            document.querySelectorAll(
                ".compare-checkbox:checked"
            )
        )
        .map(
            checkbox =>
                checkbox.value
        );

    if (selected.length < 2) {

        setStatus(
            "Please select at least two documents.",
            true
        );

        return;
    }

    try {

        await ensureCurrentChat();

        setStatus(
            "🔄 Comparing selected documents..."
        );

        const response =
            await apiRequest(
                `/api/chats/${encodeURIComponent(
                    currentChatId
                )}/compare`,
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body: JSON.stringify({
                        files: selected
                    })
                }
            );

        clearModeResult();

        renderMessage(
            "assistant",
            response.answer
        );

        renderSources(
            response.sources || []
        );

        setStatus("");

        await refreshChatsAfterMode();

    } catch (error) {

        console.error(
            "Comparison error:",
            error
        );

        setStatus(
            error.message ||
            "Could not compare documents.",
            true
        );
    }
}


// =========================================================
// QUIZ
// =========================================================

async function runQuiz() {

    try {

        await ensureCurrentChat();

        const count =
            Number(
                document.getElementById(
                    "quizQuestionCount"
                ).value
            );

        const difficulty =
            document.getElementById(
                "quizDifficulty"
            ).value;

        setStatus(
            "🎯 Generating quiz..."
        );

        const response =
            await apiRequest(
                `/api/chats/${encodeURIComponent(
                    currentChatId
                )}/quiz`,
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body: JSON.stringify({
                        num_questions: count,
                        difficulty
                    })
                }
            );

        modeQuizData =
            response.quiz;

        clearModeResult();

        renderQuiz(
            modeQuizData,
            response.sources || []
        );

        setStatus("");

        await refreshChatsAfterMode();

    } catch (error) {

        console.error(
            "Quiz error:",
            error
        );

        setStatus(
            error.message ||
            "Could not generate quiz.",
            true
        );
    }
}


// =========================================================
// RENDER QUIZ
// =========================================================

function renderQuiz(
    quiz,
    sources
) {

    const container =
        document.getElementById(
            "chatContainer"
        );

    if (!container) {
        return;
    }

    hideEmptyState();

    const result =
        document.createElement(
            "div"
        );

    result.className =
        "mode-result quiz-result";

    result.innerHTML = `
        <div class="mode-result-header">
            🧠 Interactive Quiz
        </div>

        <div class="mode-result-subtitle">
            ${quiz.questions.length}
            questions
        </div>

        <div id="quizQuestions"></div>

        <button
            id="submitQuizBtn"
            class="primary-btn"
        >
            ✅ Submit Quiz
        </button>

        <div
            id="quizScore"
            class="quiz-score"
        ></div>
    `;

    container.appendChild(
        result
    );

    const questionsContainer =
        result.querySelector(
            "#quizQuestions"
        );

    quiz.questions.forEach(
        (question, index) => {

            const questionElement =
                document.createElement(
                    "div"
                );

            questionElement.className =
                "quiz-question";

            questionElement.innerHTML = `
                <div class="quiz-question-title">
                    Question ${index + 1}
                </div>

                <div class="quiz-question-text">
                    ${escapeHtml(
                        question.question
                    )}
                </div>

                <div class="quiz-options">

                    ${question.options
                        .map(
                            (
                                option,
                                optionIndex
                            ) => `
                                <label class="quiz-option">

                                    <input
                                        type="radio"
                                        name="quiz_${index}"
                                        value="${optionIndex}"
                                    >

                                    <span>
                                        ${escapeHtml(
                                            option
                                        )}
                                    </span>

                                </label>
                            `
                        )
                        .join("")}

                </div>
            `;

            questionsContainer.appendChild(
                questionElement
            );
        }
    );

    result
        .querySelector(
            "#submitQuizBtn"
        )
        .addEventListener(
            "click",
            () => {

                let score = 0;

                quiz.questions.forEach(
                    (
                        question,
                        index
                    ) => {

                        const selected =
                            result.querySelector(
                                `input[name="quiz_${index}"]:checked`
                            );

                        const options =
                            result.querySelectorAll(
                                `input[name="quiz_${index}"]`
                            );

                        options.forEach(
                            option => {

                                const label =
                                    option.closest(
                                        ".quiz-option"
                                    );

                                label.classList.remove(
                                    "correct",
                                    "wrong"
                                );

                                if (
                                    Number(
                                        option.value
                                    ) ===
                                    question.correct_answer
                                ) {

                                    label.classList.add(
                                        "correct"
                                    );
                                }
                            }
                        );

                        if (!selected) {
                            return;
                        }

                        const selectedIndex =
                            Number(
                                selected.value
                            );

                        if (
                            selectedIndex ===
                            question.correct_answer
                        ) {

                            score++;

                        } else {

                            selected
                                .closest(
                                    ".quiz-option"
                                )
                                .classList.add(
                                    "wrong"
                                );
                        }
                    }
                );

                const scoreElement =
                    result.querySelector(
                        "#quizScore"
                    );

                scoreElement.innerHTML =
                    `
                    <strong>
                        Score: ${score} / ${quiz.questions.length}
                    </strong>
                    `;

                quiz.questions.forEach(
                    question => {

                        if (
                            question.explanation
                        ) {

                            const explanation =
                                document.createElement(
                                    "div"
                                );

                            explanation.className =
                                "quiz-explanation";

                            explanation.textContent =
                                question.explanation;

                            questionsContainer
                                .appendChild(
                                    explanation
                                );
                        }
                    }
                );
            }
        );

    if (sources.length) {
        renderSources(
            sources
        );
    }

    scrollToBottom();
}


// =========================================================
// FLASHCARDS
// =========================================================

async function runFlashcards() {

    try {

        await ensureCurrentChat();

        const count =
            Number(
                document.getElementById(
                    "flashcardCount"
                ).value
            );

        const difficulty =
            document.getElementById(
                "flashcardDifficulty"
            ).value;

        setStatus(
            "📑 Creating flashcards..."
        );

        const response =
            await apiRequest(
                `/api/chats/${encodeURIComponent(
                    currentChatId
                )}/flashcards`,
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body: JSON.stringify({
                        count,
                        difficulty
                    })
                }
            );

        modeFlashcardData =
            response.flashcards;

        modeFlashcardIndex = 0;
        modeFlashcardFlipped =
            false;

        clearModeResult();

        renderFlashcards(
            response.sources || []
        );

        setStatus("");

        await refreshChatsAfterMode();

    } catch (error) {

        console.error(
            "Flashcard error:",
            error
        );

        setStatus(
            error.message ||
            "Could not generate flashcards.",
            true
        );
    }
}


// =========================================================
// RENDER FLASHCARDS
// =========================================================

function renderFlashcards(
    sources
) {

    const container =
        document.getElementById(
            "chatContainer"
        );

    if (!container) {
        return;
    }

    hideEmptyState();

    const result =
        document.createElement(
            "div"
        );

    result.className =
        "mode-result flashcard-result";

    result.innerHTML = `
        <div class="mode-result-header">
            📑 Flashcards
        </div>

        <div
            id="flashcardCounter"
            class="mode-result-subtitle"
        ></div>

        <div
            id="flashcard"
            class="flashcard"
        ></div>

        <div class="flashcard-actions">

            <button
                id="prevFlashcard"
                class="secondary-btn"
            >
                ← Previous
            </button>

            <button
                id="flipFlashcard"
                class="primary-btn"
            >
                🔄 Flip Card
            </button>

            <button
                id="nextFlashcard"
                class="secondary-btn"
            >
                Next →
            </button>

        </div>
    `;

    container.appendChild(
        result
    );

    result
        .querySelector(
            "#flipFlashcard"
        )
        .addEventListener(
            "click",
            () => {

                modeFlashcardFlipped =
                    !modeFlashcardFlipped;

                updateFlashcard(
                    result
                );
            }
        );

    result
        .querySelector(
            "#prevFlashcard"
        )
        .addEventListener(
            "click",
            () => {

                if (
                    modeFlashcardIndex > 0
                ) {

                    modeFlashcardIndex--;

                    modeFlashcardFlipped =
                        false;

                    updateFlashcard(
                        result
                    );
                }
            }
        );

    result
        .querySelector(
            "#nextFlashcard"
        )
        .addEventListener(
            "click",
            () => {

                if (
                    modeFlashcardIndex <
                    modeFlashcardData.flashcards.length - 1
                ) {

                    modeFlashcardIndex++;

                    modeFlashcardFlipped =
                        false;

                    updateFlashcard(
                        result
                    );
                }
            }
        );

    updateFlashcard(
        result
    );

    if (sources.length) {
        renderSources(
            sources
        );
    }

    scrollToBottom();
}


// =========================================================
// UPDATE FLASHCARD
// =========================================================

function updateFlashcard(
    result
) {

    const cards =
        modeFlashcardData
            ?.flashcards ||
        [];

    if (!cards.length) {
        return;
    }

    const card =
        cards[
            modeFlashcardIndex
        ];

    const flashcard =
        result.querySelector(
            "#flashcard"
        );

    const counter =
        result.querySelector(
            "#flashcardCounter"
        );

    counter.textContent =
        `Card ${
            modeFlashcardIndex + 1
        } of ${cards.length}`;

    flashcard.innerHTML = `
        <div class="flashcard-label">
            ${
                modeFlashcardFlipped
                    ? "ANSWER"
                    : "QUESTION"
            }
        </div>

        <div class="flashcard-text">
            ${escapeHtml(
                modeFlashcardFlipped
                    ? card.back
                    : card.front
            )}
        </div>

        ${
            modeFlashcardFlipped &&
            card.source
                ? `
                    <div class="flashcard-source">
                        Source: ${escapeHtml(
                            card.source
                        )}
                    </div>
                `
                : ""
        }
    `;

    const previous =
        result.querySelector(
            "#prevFlashcard"
        );

    const next =
        result.querySelector(
            "#nextFlashcard"
        );

    previous.disabled =
        modeFlashcardIndex === 0;

    next.disabled =
        modeFlashcardIndex ===
        cards.length - 1;
}


// =========================================================
// REFRESH CHAT SIDEBAR
// =========================================================

async function refreshChatsAfterMode() {

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


// =========================================================
// ACTION LISTENER
// =========================================================

function initializeDocumentModes() {

    const buttons =
        document.querySelectorAll(
            ".action-btn"
        );

    buttons.forEach(
        button => {

            button.addEventListener(
                "click",
                async () => {

                    const action =
                        button.dataset.action;

                    clearModeResult();
                    hideModeControls();

                    if (
                        action === "ask"
                    ) {

                        setStatus("");

                        return;
                    }

                    if (
                        action ===
                        "summarize"
                    ) {

                        renderSummaryControls();

                        return;
                    }

                    if (
                        action ===
                        "compare"
                    ) {

                        await renderCompareControls();

                        return;
                    }

                    if (
                        action === "quiz"
                    ) {

                        renderQuizControls();

                        return;
                    }

                    if (
                        action ===
                        "flashcards"
                    ) {

                        renderFlashcardControls();

                        return;
                    }
                }
            );
        }
    );
}


// =========================================================
// START
// =========================================================

document.addEventListener(
    "DOMContentLoaded",
    () => {

        initializeDocumentModes();

        console.log(
            "✅ Document modes initialized."
        );
    }
);