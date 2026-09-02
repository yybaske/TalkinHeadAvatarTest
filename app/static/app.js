let currentConversationId = null;
let sending = false;
let selectedDocumentFile = null;


/* =========================================================
   DOM
========================================================= */

const conversationList =
    document.getElementById(
        "conversation-list"
    );

const messages =
    document.getElementById(
        "messages"
    );

const welcome =
    document.getElementById(
        "welcome"
    );

const messageInput =
    document.getElementById(
        "message-input"
    );

const sendButton =
    document.getElementById(
        "send-button"
    );

const newChatButton =
    document.getElementById(
        "new-chat-button"
    );

const documentManagementButton =
    document.getElementById(
        "document-management-button"
    );

const featureManagementButton =
    document.getElementById(
        "feature-management-button"
    );

const backToChatButton =
    document.getElementById(
        "back-to-chat-button"
    );

const backToChatFromFeatureButton =
    document.getElementById(
        "back-to-chat-from-feature-button"
    );

const chatView =
    document.getElementById(
        "chat-view"
    );

const documentView =
    document.getElementById(
        "document-view"
    );

const featureView =
    document.getElementById(
        "feature-view"
    );

const documentList =
    document.getElementById(
        "document-list"
    );

const documentFileInput =
    document.getElementById(
        "document-file-input"
    );

const uploadDropZone =
    document.getElementById(
        "upload-drop-zone"
    );

const selectedFile =
    document.getElementById(
        "selected-file"
    );

const uploadButton =
    document.getElementById(
        "upload-button"
    );

const uploadStatus =
    document.getElementById(
        "upload-status"
    );

const refreshDocumentsButton =
    document.getElementById(
        "refresh-documents-button"
    );

const featureList =
    document.getElementById(
        "feature-list"
    );

const featureStatus =
    document.getElementById(
        "feature-status"
    );

const conversationFeatureList =
    document.getElementById(
        "conversation-feature-list"
    );

const conversationFeatureStatus =
    document.getElementById(
        "conversation-feature-status"
    );


/* =========================================================
   Feature Definitions
========================================================= */

const CONVERSATION_FEATURE_LABELS = {
    local_rag: "社内文書",
    mcp: "MCP",
    mcp_servicenow: "ServiceNow",
    mcp_aws: "AWS",
    mcp_github: "GitHub",
    mcp_sharepoint: "SharePoint",
    external_actions: "外部更新"
};


const MCP_CONVERSATION_CHILDREN =
    new Set(
        [
            "mcp_servicenow",
            "mcp_aws",
            "mcp_github",
            "mcp_sharepoint"
        ]
    );


const FEATURE_CATEGORIES = [
    {
        key: "core",
        title: "基本機能",
        description:
            "社内AIの基本機能を設定します。"
    },
    {
        key: "integration",
        title: "外部連携",
        description:
            "外部システムとの連携基盤を設定します。"
    },
    {
        key: "mcp",
        title: "MCPサービス",
        description:
            "MCP経由で利用するサービスを個別に設定します。"
    },
    {
        key: "security",
        title: "セキュリティ",
        description:
            "外部システムへの更新など、影響の大きい機能を設定します。"
    }
];


/* =========================================================
   Initialize
========================================================= */

document.addEventListener(
    "DOMContentLoaded",
    async () => {

        resetConversationFeaturePanel();

        await loadConversations();
    }
);


/* =========================================================
   Events
========================================================= */

sendButton.addEventListener(
    "click",
    async () => {

        await sendMessage();
    }
);


messageInput.addEventListener(
    "keydown",
    async (event) => {

        if (
            event.key === "Enter"
            && !event.shiftKey
        ) {

            event.preventDefault();

            await sendMessage();
        }
    }
);


messageInput.addEventListener(
    "input",
    () => {

        autoResizeTextarea();
    }
);


newChatButton.addEventListener(
    "click",
    () => {

        showChatView();

        startNewChat();
    }
);


documentManagementButton.addEventListener(
    "click",
    async () => {

        showDocumentView();

        await loadDocuments();
    }
);


featureManagementButton.addEventListener(
    "click",
    async () => {

        showFeatureView();

        await loadFeatures();
    }
);


backToChatButton.addEventListener(
    "click",
    () => {

        showChatView();
    }
);


backToChatFromFeatureButton.addEventListener(
    "click",
    () => {

        showChatView();
    }
);


refreshDocumentsButton.addEventListener(
    "click",
    async () => {

        await loadDocuments();
    }
);


document
    .querySelectorAll(
        ".example-button"
    )
    .forEach(
        (button) => {

            button.addEventListener(
                "click",
                async () => {

                    messageInput.value =
                        button.dataset.question
                        || "";

                    await sendMessage();
                }
            );
        }
    );


uploadDropZone.addEventListener(
    "click",
    () => {

        documentFileInput.click();
    }
);


documentFileInput.addEventListener(
    "change",
    () => {

        setSelectedDocumentFile(
            documentFileInput.files[0]
        );
    }
);


uploadDropZone.addEventListener(
    "dragover",
    (event) => {

        event.preventDefault();

        uploadDropZone
            .classList
            .add(
                "dragover"
            );
    }
);


uploadDropZone.addEventListener(
    "dragleave",
    () => {

        uploadDropZone
            .classList
            .remove(
                "dragover"
            );
    }
);


uploadDropZone.addEventListener(
    "drop",
    (event) => {

        event.preventDefault();

        uploadDropZone
            .classList
            .remove(
                "dragover"
            );

        setSelectedDocumentFile(
            event.dataTransfer.files[0]
        );
    }
);


uploadButton.addEventListener(
    "click",
    async () => {

        await uploadDocument();
    }
);


/* =========================================================
   Chat
========================================================= */

async function sendMessage() {

    if (sending) {
        return;
    }

    const query =
        messageInput
            .value
            .trim();

    if (!query) {
        return;
    }

    sending = true;

    sendButton.disabled =
        true;

    hideWelcome();

    addMessage(
        "user",
        query
    );

    messageInput.value =
        "";

    autoResizeTextarea();


    const loadingElement =
        addLoadingMessage();


    try {

        const body = {
            query: query
        };


        if (
            currentConversationId
        ) {

            body.conversation_id =
                currentConversationId;
        }


        const response =
            await fetch(
                "/chat",
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body:
                        JSON.stringify(
                            body
                        )
                }
            );


        const data =
            await response.json();


        loadingElement.remove();


        if (!response.ok) {

            addMessage(
                "assistant",
                data.detail
                || "エラーが発生しました。"
            );

            return;
        }


        currentConversationId =
            data.conversation_id;


        addMessage(
            "assistant",
            data.answer,
            buildMetadataText(
                data
            ),
            data.sources || []
        );


        await Promise.all(
            [
                loadConversations(),
                loadConversationFeatures()
            ]
        );


        highlightCurrentConversation();

    } catch (error) {

        if (
            loadingElement.isConnected
        ) {

            loadingElement.remove();
        }


        addMessage(
            "assistant",
            "サーバーとの通信に失敗しました。"
        );


        console.error(
            error
        );

    } finally {

        sending =
            false;

        sendButton.disabled =
            false;

        messageInput.focus();
    }
}


/* =========================================================
   Conversations
========================================================= */

async function loadConversations() {

    try {

        const response =
            await fetch(
                "/conversations"
            );


        if (!response.ok) {
            return;
        }


        const data =
            await response.json();


        conversationList.innerHTML =
            "";


        for (
            const conversation
            of data.conversations || []
        ) {

            conversationList
                .appendChild(
                    createConversationItem(
                        conversation
                    )
                );
        }


        highlightCurrentConversation();

    } catch (error) {

        console.error(
            error
        );
    }
}


function createConversationItem(
    conversation
) {

    const wrapper =
        document.createElement(
            "div"
        );

    wrapper.className =
        "conversation-item";


    const button =
        document.createElement(
            "button"
        );

    button.className =
        "conversation-button";

    button.dataset.conversationId =
        conversation.conversation_id;


    const title =
        document.createElement(
            "span"
        );

    title.className =
        "conversation-text";

    title.textContent =
        conversation.title;


    button.appendChild(
        title
    );


    button.addEventListener(
        "click",
        async () => {

            showChatView();

            await openConversation(
                conversation
                    .conversation_id
            );
        }
    );


    const deleteButton =
        document.createElement(
            "button"
        );

    deleteButton.className =
        "delete-button";

    deleteButton.textContent =
        "×";


    deleteButton.addEventListener(
        "click",
        async (event) => {

            event.stopPropagation();

            await deleteConversation(
                conversation
                    .conversation_id
            );
        }
    );


    wrapper.appendChild(
        button
    );

    wrapper.appendChild(
        deleteButton
    );


    return wrapper;
}


async function openConversation(
    conversationId
) {

    try {

        const response =
            await fetch(
                `/conversations/${
                    encodeURIComponent(
                        conversationId
                    )
                }`
            );


        const data =
            await response.json();


        if (!response.ok) {
            return;
        }


        currentConversationId =
            conversationId;


        messages.innerHTML =
            "";


        hideWelcome();


        for (
            const message
            of data.messages || []
        ) {

            let metadataText =
                "";

            let sources =
                [];


            if (
                message.metadata
                && message.role
                === "assistant"
            ) {

                metadataText =
                    buildMetadataText(
                        message.metadata
                    );

                sources =
                    message
                        .metadata
                        .sources
                    || [];
            }


            addMessage(
                message.role,
                message.content,
                metadataText,
                sources
            );
        }


        await loadConversationFeatures();


        highlightCurrentConversation();

        scrollToBottom();

    } catch (error) {

        console.error(
            error
        );
    }
}


async function deleteConversation(
    conversationId
) {

    const confirmed =
        window.confirm(
            "この会話を削除しますか？"
        );


    if (!confirmed) {
        return;
    }


    try {

        const response =
            await fetch(
                `/conversations/${
                    encodeURIComponent(
                        conversationId
                    )
                }`,
                {
                    method:
                        "DELETE"
                }
            );


        if (!response.ok) {
            return;
        }


        if (
            currentConversationId
            === conversationId
        ) {

            startNewChat();
        }


        await loadConversations();

    } catch (error) {

        console.error(
            error
        );
    }
}


function startNewChat() {

    currentConversationId =
        null;


    messages.innerHTML =
        "";


    welcome.style.display =
        "block";


    messageInput.value =
        "";


    resetConversationFeaturePanel();


    highlightCurrentConversation();


    messageInput.focus();
}


/* =========================================================
   Message
========================================================= */

function addMessage(
    role,
    content,
    metadataText = "",
    sources = []
) {

    const message =
        document.createElement(
            "div"
        );

    message.className =
        `message ${role}`;


    const bubble =
        document.createElement(
            "div"
        );

    bubble.className =
        "message-bubble";


    const text =
        document.createElement(
            "div"
        );


    if (
        role === "assistant"
    ) {

        text.className =
            "markdown-content";


        text.innerHTML =
            renderMarkdown(
                removeCitationLabels(
                    content
                )
            );

    } else {

        text.textContent =
            content;
    }


    bubble.appendChild(
        text
    );


    if (
        role === "assistant"
        && sources
        && sources.length > 0
    ) {

        bubble.appendChild(
            createSourceArea(
                sources
            )
        );
    }


    if (metadataText) {

        const metadata =
            document.createElement(
                "div"
            );

        metadata.className =
            "message-meta";

        metadata.textContent =
            metadataText;


        bubble.appendChild(
            metadata
        );
    }


    message.appendChild(
        bubble
    );


    messages.appendChild(
        message
    );


    scrollToBottom();


    return message;
}


/* =========================================================
   Sources
========================================================= */

function createSourceArea(
    sources
) {

    const wrapper =
        document.createElement(
            "div"
        );

    wrapper.className =
        "source-area";


    const title =
        document.createElement(
            "div"
        );

    title.className =
        "source-area-title";

    title.textContent =
        "参照した資料";


    wrapper.appendChild(
        title
    );


    const list =
        document.createElement(
            "div"
        );

    list.className =
        "source-list";


    for (
        const source
        of getUniqueSources(
            sources
        )
    ) {

        const card =
            document.createElement(
                "div"
            );

        card.className =
            "source-card";


        const icon =
            document.createElement(
                "div"
            );

        icon.className =
            "source-icon";

        icon.textContent =
            getDocumentIcon(
                source.filename
            );


        const content =
            document.createElement(
                "div"
            );

        content.className =
            "source-card-content";


        const filename =
            document.createElement(
                "div"
            );

        filename.className =
            "source-filename";

        filename.textContent =
            source.filename
            || "不明な文書";


        content.appendChild(
            filename
        );


        const details = [];


        if (
            source.section_title
        ) {

            details.push(
                source.section_title
            );
        }


        if (
            source.page_number
            !== null
            && source.page_number
            !== undefined
        ) {

            details.push(
                `p.${source.page_number}`
            );
        }


        if (
            details.length > 0
        ) {

            const detail =
                document.createElement(
                    "div"
                );

            detail.className =
                "source-detail";

            detail.textContent =
                details.join(
                    " / "
                );


            content.appendChild(
                detail
            );
        }


        card.appendChild(
            icon
        );

        card.appendChild(
            content
        );

        list.appendChild(
            card
        );
    }


    wrapper.appendChild(
        list
    );


    return wrapper;
}


function getUniqueSources(
    sources
) {

    const result =
        [];

    const seen =
        new Set();


    for (
        const source
        of sources || []
    ) {

        const key = [
            source.filename || "",
            source.section_title || "",
            source.page_number ?? ""
        ].join(
            "|"
        );


        if (
            seen.has(
                key
            )
        ) {

            continue;
        }


        seen.add(
            key
        );

        result.push(
            source
        );
    }


    return result;
}


function getDocumentIcon(
    filename
) {

    if (!filename) {
        return "DOC";
    }


    const lower =
        filename.toLowerCase();


    if (
        lower.endsWith(
            ".pdf"
        )
    ) {
        return "PDF";
    }


    if (
        lower.endsWith(
            ".docx"
        )
    ) {
        return "DOC";
    }


    if (
        lower.endsWith(
            ".md"
        )
    ) {
        return "MD";
    }


    if (
        lower.endsWith(
            ".txt"
        )
    ) {
        return "TXT";
    }


    return "DOC";
}


function removeCitationLabels(
    text
) {

    if (!text) {
        return "";
    }


    return text
        .replace(
            /\s*\[[^\[\]\n]+\.(?:pdf|docx|txt|md)(?:\s*\/\s*[^\[\]\n]+)*\]/gi,
            ""
        )
        .replace(
            /[ \t]+\n/g,
            "\n"
        )
        .replace(
            /\n{3,}/g,
            "\n\n"
        )
        .trim();
}


/* =========================================================
   Markdown
========================================================= */

function renderMarkdown(
    markdown
) {

    if (!markdown) {
        return "";
    }


    const normalized =
        normalizeMarkdown(
            markdown
        );


    const escaped =
        escapeHtml(
            normalized
        );


    const lines =
        escaped.split(
            "\n"
        );


    const output =
        [];


    let inUnorderedList =
        false;

    let inOrderedList =
        false;


    function closeLists() {

        if (
            inUnorderedList
        ) {

            output.push(
                "</ul>"
            );

            inUnorderedList =
                false;
        }


        if (
            inOrderedList
        ) {

            output.push(
                "</ol>"
            );

            inOrderedList =
                false;
        }
    }


    for (
        const originalLine
        of lines
    ) {

        const line =
            originalLine.trim();


        if (!line) {

            closeLists();

            continue;
        }


        if (
            line.startsWith(
                "### "
            )
        ) {

            closeLists();

            output.push(
                `<h3>${
                    formatInlineMarkdown(
                        line.slice(
                            4
                        )
                    )
                }</h3>`
            );

            continue;
        }


        if (
            line.startsWith(
                "## "
            )
        ) {

            closeLists();

            output.push(
                `<h2>${
                    formatInlineMarkdown(
                        line.slice(
                            3
                        )
                    )
                }</h2>`
            );

            continue;
        }


        if (
            line.startsWith(
                "# "
            )
        ) {

            closeLists();

            output.push(
                `<h1>${
                    formatInlineMarkdown(
                        line.slice(
                            2
                        )
                    )
                }</h1>`
            );

            continue;
        }


        if (
            /^---+$/.test(
                line
            )
        ) {

            closeLists();

            output.push(
                "<hr>"
            );

            continue;
        }


        if (
            /^[-*]\s+/.test(
                line
            )
        ) {

            if (
                inOrderedList
            ) {

                output.push(
                    "</ol>"
                );

                inOrderedList =
                    false;
            }


            if (
                !inUnorderedList
            ) {

                output.push(
                    "<ul>"
                );

                inUnorderedList =
                    true;
            }


            const item =
                line.replace(
                    /^[-*]\s+/,
                    ""
                );


            output.push(
                `<li>${
                    formatInlineMarkdown(
                        item
                    )
                }</li>`
            );


            continue;
        }


        if (
            /^\d+\.\s+/.test(
                line
            )
        ) {

            if (
                inUnorderedList
            ) {

                output.push(
                    "</ul>"
                );

                inUnorderedList =
                    false;
            }


            if (
                !inOrderedList
            ) {

                output.push(
                    "<ol>"
                );

                inOrderedList =
                    true;
            }


            const item =
                line.replace(
                    /^\d+\.\s+/,
                    ""
                );


            output.push(
                `<li>${
                    formatInlineMarkdown(
                        item
                    )
                }</li>`
            );


            continue;
        }


        closeLists();


        output.push(
            `<p>${
                formatInlineMarkdown(
                    line
                )
            }</p>`
        );
    }


    closeLists();


    return output.join(
        "\n"
    );
}


function normalizeMarkdown(
    markdown
) {

    return markdown
        .replace(
            /\r\n/g,
            "\n"
        )
        .replace(
            /\r/g,
            "\n"
        )
        .replace(
            /[ \t]+-\s+(?=\*\*)/g,
            "\n\n- "
        )
        .replace(
            /([。！？!?])\s+-\s+/g,
            "$1\n\n- "
        )
        .replace(
            /[ \t]+(#{1,3}\s+)/g,
            "\n\n$1"
        )
        .replace(
            /\s+-\s+(?=\*\*[^*]+\*\*)/g,
            "\n- "
        )
        .replace(
            /\n{3,}/g,
            "\n\n"
        )
        .trim();
}


function formatInlineMarkdown(
    text
) {

    return text
        .replace(
            /\*\*(.+?)\*\*/g,
            "<strong>$1</strong>"
        )
        .replace(
            /`([^`]+)`/g,
            "<code>$1</code>"
        )
        .replace(
            /(^|[^\*])\*([^*\n]+)\*/g,
            "$1<em>$2</em>"
        );
}


function escapeHtml(
    text
) {

    return text
        .replace(
            /&/g,
            "&amp;"
        )
        .replace(
            /</g,
            "&lt;"
        )
        .replace(
            />/g,
            "&gt;"
        )
        .replace(
            /"/g,
            "&quot;"
        )
        .replace(
            /'/g,
            "&#039;"
        );
}


/* =========================================================
   Loading
========================================================= */

function addLoadingMessage() {

    const message =
        document.createElement(
            "div"
        );

    message.className =
        "message assistant";


    const bubble =
        document.createElement(
            "div"
        );

    bubble.className =
        "message-bubble";


    const loading =
        document.createElement(
            "div"
        );

    loading.className =
        "loading";


    for (
        let i = 0;
        i < 3;
        i++
    ) {

        loading.appendChild(
            document.createElement(
                "span"
            )
        );
    }


    bubble.appendChild(
        loading
    );

    message.appendChild(
        bubble
    );

    messages.appendChild(
        message
    );


    scrollToBottom();


    return message;
}


/* =========================================================
   Metadata
========================================================= */

function buildMetadataText(
    data
) {

    const parts =
        [];


    if (
        data.retrieval_used
        === true
    ) {

        parts.push(
            "文書検索あり"
        );

    } else if (
        data.retrieval_used
        === false
    ) {

        parts.push(
            "文書検索なし"
        );
    }


    if (
        data.confidence
    ) {

        parts.push(
            `信頼度: ${data.confidence}`
        );
    }


    return parts.join(
        " / "
    );
}


/* =========================================================
   UI Helper
========================================================= */

function highlightCurrentConversation() {

    document
        .querySelectorAll(
            ".conversation-button"
        )
        .forEach(
            (button) => {

                button.classList.toggle(
                    "active",
                    (
                        button.dataset.conversationId
                        === currentConversationId
                    )
                );
            }
        );
}


function hideWelcome() {

    welcome.style.display =
        "none";
}


function scrollToBottom() {

    const chatArea =
        document.getElementById(
            "chat-area"
        );


    requestAnimationFrame(
        () => {

            chatArea.scrollTop =
                chatArea.scrollHeight;
        }
    );
}


function autoResizeTextarea() {

    messageInput.style.height =
        "auto";


    messageInput.style.height =
        `${Math.min(
            messageInput.scrollHeight,
            180
        )}px`;
}


/* =========================================================
   View
========================================================= */

function showChatView() {

    chatView
        .classList
        .remove(
            "hidden"
        );


    documentView
        .classList
        .add(
            "hidden"
        );


    featureView
        .classList
        .add(
            "hidden"
        );


    documentManagementButton
        .classList
        .remove(
            "active"
        );


    featureManagementButton
        .classList
        .remove(
            "active"
        );
}


function showDocumentView() {

    chatView
        .classList
        .add(
            "hidden"
        );


    documentView
        .classList
        .remove(
            "hidden"
        );


    featureView
        .classList
        .add(
            "hidden"
        );


    documentManagementButton
        .classList
        .add(
            "active"
        );


    featureManagementButton
        .classList
        .remove(
            "active"
        );
}


function showFeatureView() {

    chatView
        .classList
        .add(
            "hidden"
        );


    documentView
        .classList
        .add(
            "hidden"
        );


    featureView
        .classList
        .remove(
            "hidden"
        );


    documentManagementButton
        .classList
        .remove(
            "active"
        );


    featureManagementButton
        .classList
        .add(
            "active"
        );
}


/* =========================================================
   Documents
========================================================= */

async function loadDocuments() {

    documentList.innerHTML =
        "読み込み中...";


    try {

        const response =
            await fetch(
                "/documents"
            );


        const data =
            await response.json();


        if (!response.ok) {

            documentList.innerHTML =
                "文書一覧の取得に失敗しました。";

            return;
        }


        renderDocuments(
            data.documents || []
        );

    } catch (error) {

        documentList.innerHTML =
            "サーバーとの通信に失敗しました。";


        console.error(
            error
        );
    }
}


function renderDocuments(
    documents
) {

    documentList.innerHTML =
        "";


    if (
        documents.length === 0
    ) {

        const empty =
            document.createElement(
                "div"
            );

        empty.className =
            "empty-documents";

        empty.textContent =
            "登録済み文書はありません。";


        documentList.appendChild(
            empty
        );

        return;
    }


    for (
        const documentItem
        of documents
    ) {

        const row =
            document.createElement(
                "div"
            );

        row.className =
            "document-row";


        const info =
            document.createElement(
                "div"
            );

        info.className =
            "document-info";


        const name =
            document.createElement(
                "div"
            );

        name.className =
            "document-name";

        name.textContent =
            documentItem.filename;


        const meta =
            document.createElement(
                "div"
            );

        meta.className =
            "document-meta";

        meta.textContent =
            `チャンク数: ${
                documentItem.chunk_count
            }`;


        info.appendChild(
            name
        );

        info.appendChild(
            meta
        );


        const deleteButton =
            document.createElement(
                "button"
            );

        deleteButton.className =
            "document-delete-button";

        deleteButton.textContent =
            "削除";


        deleteButton.addEventListener(
            "click",
            async () => {

                await deleteDocument(
                    documentItem.document_id,
                    documentItem.filename
                );
            }
        );


        row.appendChild(
            info
        );

        row.appendChild(
            deleteButton
        );


        documentList.appendChild(
            row
        );
    }
}


function setSelectedDocumentFile(
    file
) {

    uploadStatus.textContent =
        "";

    uploadStatus.className =
        "upload-status";


    if (!file) {

        selectedDocumentFile =
            null;

        selectedFile
            .classList
            .add(
                "hidden"
            );

        uploadButton.disabled =
            true;

        return;
    }


    const allowedExtensions = [
        ".pdf",
        ".docx",
        ".txt",
        ".md"
    ];


    const lowerName =
        file.name
            .toLowerCase();


    const allowed =
        allowedExtensions
            .some(
                (extension) =>
                    lowerName.endsWith(
                        extension
                    )
            );


    if (!allowed) {

        selectedDocumentFile =
            null;


        uploadButton.disabled =
            true;


        selectedFile
            .classList
            .add(
                "hidden"
            );


        uploadStatus.textContent =
            "対応していないファイル形式です。";


        uploadStatus
            .classList
            .add(
                "error"
            );


        return;
    }


    selectedDocumentFile =
        file;


    selectedFile.textContent =
        `${
            file.name
        } (${
            formatFileSize(
                file.size
            )
        })`;


    selectedFile
        .classList
        .remove(
            "hidden"
        );


    uploadButton.disabled =
        false;
}


async function uploadDocument() {

    if (
        !selectedDocumentFile
    ) {
        return;
    }


    uploadButton.disabled =
        true;


    uploadStatus.textContent =
        "文書を解析・登録しています...";


    uploadStatus.className =
        "upload-status";


    const formData =
        new FormData();


    formData.append(
        "file",
        selectedDocumentFile
    );


    try {

        const response =
            await fetch(
                "/documents",
                {
                    method:
                        "POST",

                    body:
                        formData
                }
            );


        const data =
            await response.json();


        if (!response.ok) {

            uploadStatus.textContent =
                data.detail
                || "文書登録に失敗しました。";


            uploadStatus
                .classList
                .add(
                    "error"
                );


            uploadButton.disabled =
                false;


            return;
        }


        uploadStatus.textContent =
            `登録完了: ${
                data.filename
            } / ${
                data.chunk_count
            }チャンク`;


        uploadStatus
            .classList
            .add(
                "success"
            );


        selectedDocumentFile =
            null;


        documentFileInput.value =
            "";


        selectedFile
            .classList
            .add(
                "hidden"
            );


        uploadButton.disabled =
            true;


        await loadDocuments();

    } catch (error) {

        uploadStatus.textContent =
            "サーバーとの通信に失敗しました。";


        uploadStatus
            .classList
            .add(
                "error"
            );


        uploadButton.disabled =
            false;


        console.error(
            error
        );
    }
}


async function deleteDocument(
    documentId,
    filename
) {

    const confirmed =
        window.confirm(
            `「${filename}」を削除しますか？`
        );


    if (!confirmed) {
        return;
    }


    try {

        const response =
            await fetch(
                `/documents/${
                    encodeURIComponent(
                        documentId
                    )
                }`,
                {
                    method:
                        "DELETE"
                }
            );


        const data =
            await response.json();


        if (!response.ok) {

            window.alert(
                data.detail
                || "文書削除に失敗しました。"
            );

            return;
        }


        await loadDocuments();

    } catch (error) {

        window.alert(
            "サーバーとの通信に失敗しました。"
        );


        console.error(
            error
        );
    }
}


function formatFileSize(
    bytes
) {

    if (
        bytes < 1024
    ) {

        return `${bytes} B`;
    }


    if (
        bytes
        < 1024 * 1024
    ) {

        return `${
            (
                bytes / 1024
            ).toFixed(
                1
            )
        } KB`;
    }


    return `${
        (
            bytes
            / 1024
            / 1024
        ).toFixed(
            1
        )
    } MB`;
}


/* =========================================================
   Conversation Features
========================================================= */

function resetConversationFeaturePanel() {

    conversationFeatureStatus.textContent =
        "";


    conversationFeatureStatus.className =
        "conversation-feature-status";


    conversationFeatureList.innerHTML =
        "";


    const note =
        document.createElement(
            "span"
        );


    note.className =
        "conversation-feature-empty";


    note.textContent =
        "最初のメッセージ送信後に選択できます";


    conversationFeatureList.appendChild(
        note
    );
}


async function loadConversationFeatures() {

    if (
        !currentConversationId
    ) {

        resetConversationFeaturePanel();

        return;
    }


    conversationFeatureStatus.textContent =
        "";


    conversationFeatureStatus.className =
        "conversation-feature-status";


    conversationFeatureList.innerHTML =
        (
            '<span class="conversation-feature-loading">'
            + "読み込み中..."
            + "</span>"
        );


    try {

        const response =
            await fetch(
                `/conversations/${
                    encodeURIComponent(
                        currentConversationId
                    )
                }/features`
            );


        const data =
            await response.json();


        if (!response.ok) {

            conversationFeatureList.innerHTML =
                "";


            conversationFeatureStatus.textContent =
                data.detail
                || "利用機能の取得に失敗しました。";


            conversationFeatureStatus
                .classList
                .add(
                    "error"
                );


            return;
        }


        renderConversationFeatures(
            data.features || []
        );

    } catch (error) {

        conversationFeatureList.innerHTML =
            "";


        conversationFeatureStatus.textContent =
            "利用機能の取得に失敗しました。";


        conversationFeatureStatus
            .classList
            .add(
                "error"
            );


        console.error(
            error
        );
    }
}


function renderConversationFeatures(
    features
) {

    conversationFeatureList.innerHTML =
        "";


    if (
        features.length === 0
    ) {

        const empty =
            document.createElement(
                "span"
            );


        empty.className =
            "conversation-feature-empty";


        empty.textContent =
            "利用可能な機能がありません";


        conversationFeatureList.appendChild(
            empty
        );


        return;
    }


    const featureMap =
        new Map(
            features.map(
                (feature) => [
                    feature.feature_key,
                    feature
                ]
            )
        );


    const mcpFeature =
        featureMap.get(
            "mcp"
        );


    const mcpConversationEnabled =
        (
            mcpFeature?.globally_enabled
            === true
        )
        &&
        (
            mcpFeature?.conversation_enabled
            === true
        );


    for (
        const feature
        of features
    ) {

        const disabledByGlobal =
            feature.globally_enabled
            !== true;


        const disabledByMcp =
            (
                MCP_CONVERSATION_CHILDREN
                    .has(
                        feature.feature_key
                    )
            )
            &&
            !mcpConversationEnabled;


        conversationFeatureList
            .appendChild(
                createConversationFeatureChip(
                    feature,
                    disabledByGlobal,
                    disabledByMcp
                )
            );
    }
}


function createConversationFeatureChip(
    feature,
    disabledByGlobal,
    disabledByMcp
) {

    const button =
        document.createElement(
            "button"
        );


    button.type =
        "button";


    button.className =
        "conversation-feature-chip";


    const effectiveEnabled =
        (
            feature.globally_enabled
            === true
        )
        &&
        (
            feature.conversation_enabled
            === true
        );


    if (
        effectiveEnabled
    ) {

        button
            .classList
            .add(
                "active"
            );
    }


    const disabled =
        disabledByGlobal
        || disabledByMcp;


    button.disabled =
        disabled;


    if (disabled) {

        button
            .classList
            .add(
                "disabled"
            );
    }


    const mark =
        document.createElement(
            "span"
        );


    mark.className =
        "conversation-feature-chip-mark";


    mark.textContent =
        effectiveEnabled
        ? "✓"
        : "+";


    const label =
        document.createElement(
            "span"
        );


    label.textContent =
        CONVERSATION_FEATURE_LABELS[
            feature.feature_key
        ]
        || feature.display_name
        || feature.feature_key;


    button.appendChild(
        mark
    );


    button.appendChild(
        label
    );


    if (
        disabledByGlobal
    ) {

        button.title =
            "管理者設定で無効になっています";

    } else if (
        disabledByMcp
    ) {

        button.title =
            "先にこのチャットでMCPを有効にしてください";

    } else {

        button.title =
            effectiveEnabled
            ? "クリックしてこのチャットでは無効にする"
            : "クリックしてこのチャットで有効にする";
    }


    button.addEventListener(
        "click",
        async () => {

            if (
                button.disabled
            ) {
                return;
            }


            await updateConversationFeature(
                feature.feature_key,
                !effectiveEnabled
            );
        }
    );


    return button;
}


async function updateConversationFeature(
    featureKey,
    enabled
) {

    if (
        !currentConversationId
    ) {
        return;
    }


    conversationFeatureStatus.textContent =
        "設定を更新しています...";


    conversationFeatureStatus.className =
        "conversation-feature-status";


    try {

        const response =
            await fetch(
                `/conversations/${
                    encodeURIComponent(
                        currentConversationId
                    )
                }/features/${
                    encodeURIComponent(
                        featureKey
                    )
                }`,
                {
                    method:
                        "PUT",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body:
                        JSON.stringify(
                            {
                                enabled:
                                    enabled
                            }
                        )
                }
            );


        const data =
            await response.json();


        if (!response.ok) {

            conversationFeatureStatus.textContent =
                data.detail
                || "利用機能の更新に失敗しました。";


            conversationFeatureStatus
                .classList
                .add(
                    "error"
                );


            return;
        }


        await loadConversationFeatures();


        const label =
            CONVERSATION_FEATURE_LABELS[
                featureKey
            ]
            || featureKey;


        conversationFeatureStatus.textContent =
            `${label}を${
                enabled
                ? "ON"
                : "OFF"
            }にしました。`;


        conversationFeatureStatus
            .classList
            .add(
                "success"
            );

    } catch (error) {

        conversationFeatureStatus.textContent =
            "利用機能の更新に失敗しました。";


        conversationFeatureStatus
            .classList
            .add(
                "error"
            );


        console.error(
            error
        );
    }
}


/* =========================================================
   Administrator Features
========================================================= */

async function loadFeatures(
    preserveStatus = false
) {

    if (
        !preserveStatus
    ) {

        featureStatus.textContent =
            "";

        featureStatus.className =
            "feature-status";
    }


    featureList.innerHTML =
        (
            '<div class="feature-loading">'
            + "読み込み中..."
            + "</div>"
        );


    try {

        const response =
            await fetch(
                "/features"
            );


        const data =
            await response.json();


        if (!response.ok) {

            featureList.innerHTML =
                "";


            featureStatus.textContent =
                data.detail
                || "機能設定の取得に失敗しました。";


            featureStatus
                .classList
                .add(
                    "error"
                );


            return;
        }


        renderFeatures(
            data.features || []
        );

    } catch (error) {

        featureList.innerHTML =
            "";


        featureStatus.textContent =
            "サーバーとの通信に失敗しました。";


        featureStatus
            .classList
            .add(
                "error"
            );


        console.error(
            error
        );
    }
}


function renderFeatures(
    features
) {

    featureList.innerHTML =
        "";


    if (
        features.length === 0
    ) {

        const empty =
            document.createElement(
                "div"
            );


        empty.className =
            "feature-empty";


        empty.textContent =
            "設定可能な機能がありません。";


        featureList.appendChild(
            empty
        );


        return;
    }


    const featureMap =
        new Map(
            features.map(
                (feature) => [
                    feature.feature_key,
                    feature
                ]
            )
        );


    const mcpEnabled =
        featureMap.get(
            "mcp"
        )?.enabled === true;


    for (
        const categoryDefinition
        of FEATURE_CATEGORIES
    ) {

        const categoryFeatures =
            features.filter(
                (feature) =>
                    (
                        feature.category
                        === categoryDefinition.key
                    )
            );


        if (
            categoryFeatures.length
            === 0
        ) {

            continue;
        }


        const section =
            document.createElement(
                "section"
            );


        section.className =
            "feature-section";


        const header =
            document.createElement(
                "div"
            );


        header.className =
            "feature-section-header";


        const title =
            document.createElement(
                "h2"
            );


        title.textContent =
            categoryDefinition.title;


        const description =
            document.createElement(
                "p"
            );


        description.textContent =
            categoryDefinition.description;


        header.appendChild(
            title
        );


        header.appendChild(
            description
        );


        section.appendChild(
            header
        );


        const card =
            document.createElement(
                "div"
            );


        card.className =
            "feature-card";


        for (
            const feature
            of categoryFeatures
        ) {

            const disabledByParent =
                (
                    feature.category
                    === "mcp"
                )
                &&
                !mcpEnabled;


            card.appendChild(
                createFeatureRow(
                    feature,
                    disabledByParent
                )
            );
        }


        section.appendChild(
            card
        );


        featureList.appendChild(
            section
        );
    }
}


function createFeatureRow(
    feature,
    disabledByParent
) {

    const row =
        document.createElement(
            "div"
        );


    row.className =
        "feature-row";


    if (
        disabledByParent
    ) {

        row
            .classList
            .add(
                "disabled"
            );
    }


    const info =
        document.createElement(
            "div"
        );


    info.className =
        "feature-info";


    const nameLine =
        document.createElement(
            "div"
        );


    nameLine.className =
        "feature-name-line";


    const name =
        document.createElement(
            "div"
        );


    name.className =
        "feature-name";


    name.textContent =
        feature.display_name;


    const badge =
        document.createElement(
            "span"
        );


    badge.className =
        feature.enabled
        ? "feature-state-badge on"
        : "feature-state-badge off";


    badge.textContent =
        feature.enabled
        ? "ON"
        : "OFF";


    nameLine.appendChild(
        name
    );


    nameLine.appendChild(
        badge
    );


    const description =
        document.createElement(
            "div"
        );


    description.className =
        "feature-description";


    description.textContent =
        feature.description
        || "";


    info.appendChild(
        nameLine
    );


    info.appendChild(
        description
    );


    if (
        disabledByParent
    ) {

        const note =
            document.createElement(
                "div"
            );


        note.className =
            "feature-disabled-note";


        note.textContent =
            "MCP連携をONにすると設定できます。";


        info.appendChild(
            note
        );
    }


    const switchLabel =
        document.createElement(
            "label"
        );


    switchLabel.className =
        "feature-switch";


    const input =
        document.createElement(
            "input"
        );


    input.type =
        "checkbox";


    input.checked =
        feature.enabled === true;


    input.disabled =
        disabledByParent;


    input.setAttribute(
        "aria-label",
        `${feature.display_name}を切り替える`
    );


    const slider =
        document.createElement(
            "span"
        );


    slider.className =
        "feature-switch-slider";


    input.addEventListener(
        "change",
        async () => {

            input.disabled =
                true;


            await updateFeature(
                feature.feature_key,
                input.checked
            );
        }
    );


    switchLabel.appendChild(
        input
    );


    switchLabel.appendChild(
        slider
    );


    row.appendChild(
        info
    );


    row.appendChild(
        switchLabel
    );


    return row;
}


async function updateFeature(
    featureKey,
    enabled
) {

    featureStatus.textContent =
        "設定を更新しています...";


    featureStatus.className =
        "feature-status";


    try {

        const response =
            await fetch(
                `/features/${
                    encodeURIComponent(
                        featureKey
                    )
                }`,
                {
                    method:
                        "PUT",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body:
                        JSON.stringify(
                            {
                                enabled:
                                    enabled
                            }
                        )
                }
            );


        const data =
            await response.json();


        if (!response.ok) {

            featureStatus.textContent =
                data.detail
                || "機能設定の更新に失敗しました。";


            featureStatus
                .classList
                .add(
                    "error"
                );


            await loadFeatures(
                true
            );


            return;
        }


        await loadFeatures(
            true
        );


        const feature =
            data.feature;


        featureStatus.textContent =
            `${
                feature.display_name
            }を${
                feature.enabled
                ? "ON"
                : "OFF"
            }にしました。`;


        featureStatus.className =
            "feature-status success";


        if (
            currentConversationId
        ) {

            await loadConversationFeatures();
        }

    } catch (error) {

        featureStatus.textContent =
            "サーバーとの通信に失敗しました。";


        featureStatus
            .classList
            .add(
                "error"
            );


        console.error(
            error
        );


        await loadFeatures(
            true
        );
    }
}