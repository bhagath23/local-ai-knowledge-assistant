
import { useState, useRef, useEffect } from "react";
import {
  BrainCircuit,
  Plus,
  MessageSquare,
  FileText,
  Upload,
  Send,
  Trash2,
  LoaderCircle,
  Sparkles,
  Bot,
  User,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  MessageCircle,
  Paperclip,
  X,
  Search,
  Database,
  ArrowLeft,
  BookOpen,
  AlertTriangle
} from "lucide-react";
import "./App.css";

const API_URL = "http://127.0.0.1:8000";

const getDisplayName = (filename) =>
  filename?.split(/[\\/]/).pop() || filename;

const getErrorMessage = (data, fallback) => {
  if (typeof data?.detail === "string") return data.detail;
  if (data?.detail?.message) return data.detail.message;
  return data?.message || fallback;
};

async function readResponse(response, fallback) {
  const data = await response.json();
  if (!response.ok) {
    throw new Error(getErrorMessage(data, fallback));
  }
  return data;
}

function App() {
  const [messages, setMessages] = useState([]);
  const [question, setQuestion] = useState("");

  const [documents, setDocuments] = useState([]);
  const [conversations, setConversations] = useState([]);

  const [selectedDocument, setSelectedDocument] = useState(null);
  const [activeConversation, setActiveConversation] = useState(null);
  const [attachedDocuments, setAttachedDocuments] = useState([]);

  const [expandedDocuments, setExpandedDocuments] = useState({});
  const [activeView, setActiveView] = useState("assistant");
  const [documentSearch, setDocumentSearch] = useState("");

  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [creatingConversation, setCreatingConversation] = useState(false);
  const [managingDocuments, setManagingDocuments] = useState(false);
  const [deletingDocument, setDeletingDocument] = useState(null);

  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const fileInputRef = useRef(null);
  const messagesEndRef = useRef(null);

  // ---------------- LOAD DATA ----------------

  const loadDocuments = async () => {
    const response = await fetch(`${API_URL}/documents`);
    const data = await readResponse(response, "Could not load documents.");

    setDocuments(
      (data.documents || []).map((doc) => ({
        name: doc.filename,
        pages: doc.pages ?? 0,
        chunks: doc.chunks ?? 0
      }))
    );
  };

  const loadConversations = async () => {
    const response = await fetch(`${API_URL}/conversations`);
    const data = await readResponse(
      response,
      "Could not load conversations."
    );
    setConversations(data.conversations || []);
  };

  useEffect(() => {
    const initialize = async () => {
      try {
        await Promise.all([loadDocuments(), loadConversations()]);
      } catch (err) {
        setError(err.message);
      }
    };

    initialize();
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({
      behavior: "smooth"
    });
  }, [messages, loading]);

  // ---------------- ATTACHED DOCUMENTS ----------------

  const loadAttachedDocuments = async (conversationId) => {
    const response = await fetch(
      `${API_URL}/conversations/${conversationId}/documents`
    );

    const data = await readResponse(
      response,
      "Could not load attached documents."
    );

    const names = Array.isArray(data)
      ? data
      : data.documents || data.document_names || [];

    setAttachedDocuments(names);
    return names;
  };

  // ---------------- UPLOAD PDF ----------------

  const handleUpload = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;

    if (!file.name.toLowerCase().endsWith(".pdf")) {
      setError("Please upload a PDF file.");
      event.target.value = "";
      return;
    }

    setUploading(true);
    setError("");
    setSuccess("");

    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await fetch(`${API_URL}/upload`, {
        method: "POST",
        body: formData
      });

      const data = await readResponse(response, "Upload failed.");

      if (data.duplicate) {
        setError(`${getDisplayName(data.filename)} is already indexed.`);
      } else {
        await loadDocuments();

        setSelectedDocument(data.filename);
        setActiveConversation(null);
        setAttachedDocuments([]);
        setMessages([]);
        setQuestion([]);
        setActiveView("assistant");

        setSuccess("PDF uploaded and indexed successfully.");
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
      event.target.value = "";
    }
  };

  // ---------------- CREATE CONVERSATION ----------------

  const createNewConversation = async (documentName) => {
    if (!documentName || creatingConversation) return;

    setCreatingConversation(true);
    setError("");
    setSuccess("");

    try {
      const response = await fetch(`${API_URL}/conversations`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          document_names: [documentName],
          title: "New Conversation"
        })
      });

      const data = await readResponse(
        response,
        "Could not create conversation."
      );

      setActiveConversation(data);
      setSelectedDocument(documentName);
      setAttachedDocuments([documentName]);
      setMessages([]);
      setQuestion("");
      setActiveView("assistant");

      setExpandedDocuments((previous) => ({
        ...previous,
        [documentName]: true
      }));

      await loadConversations();
      setSuccess("New conversation created.");
    } catch (err) {
      setError(err.message);
    } finally {
      setCreatingConversation(false);
    }
  };

  // ---------------- OPEN CONVERSATION ----------------

  const openConversation = async (conversation) => {
    if (loading) return;

    setError("");
    setSuccess("");
    setQuestion("");
    setMessages([]);
    setAttachedDocuments([]);
    setActiveConversation(conversation);
    setActiveView("assistant");

    try {
      const [documentsResponse, messagesResponse] = await Promise.all([
        fetch(`${API_URL}/conversations/${conversation.id}/documents`),
        fetch(`${API_URL}/conversations/${conversation.id}/messages`)
      ]);

      const documentsData = await readResponse(
        documentsResponse,
        "Could not load conversation documents."
      );

      const messagesData = await readResponse(
        messagesResponse,
        "Could not load conversation."
      );

      const names = Array.isArray(documentsData)
        ? documentsData
        : documentsData.documents || documentsData.document_names || [];

      setAttachedDocuments(names);
      setSelectedDocument(names[0] || conversation.document_name || null);

      setMessages(
        (messagesData.messages || []).map((message) => ({
          role: message.role,
          content: message.content,
          sources: message.sources || []
        }))
      );

      setExpandedDocuments((previous) => {
        const updated = { ...previous };
        names.forEach((name) => {
          updated[name] = true;
        });
        return updated;
      });
    } catch (err) {
      setError(err.message);
    }
  };

  // ---------------- ATTACH DOCUMENT ----------------

  const attachDocument = async (documentName) => {
    if (!activeConversation || !documentName || managingDocuments) return;

    if (attachedDocuments.includes(documentName)) {
      setError("This PDF is already attached.");
      return;
    }

    setManagingDocuments(true);
    setError("");
    setSuccess("");

    try {
      const response = await fetch(
        `${API_URL}/conversations/${activeConversation.id}/documents`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify({
            document_name: documentName
          })
        }
      );

      await readResponse(response, "Could not attach PDF.");

      await loadAttachedDocuments(activeConversation.id);
      await loadConversations();

      setSuccess(`${getDisplayName(documentName)} attached successfully.`);
    } catch (err) {
      setError(err.message);
    } finally {
      setManagingDocuments(false);
    }
  };

  // ---------------- DETACH DOCUMENT ----------------

  const detachDocument = async (documentName) => {
    if (!activeConversation || managingDocuments) return;

    if (attachedDocuments.length <= 1) {
      setError(
        "A conversation must have at least one attached PDF. Delete the conversation if you no longer need it."
      );
      return;
    }

    const confirmed = window.confirm(
      `Remove "${getDisplayName(documentName)}" from this conversation?\n\nThe original PDF will remain in your knowledge base.`
    );

    if (!confirmed) return;

    setManagingDocuments(true);
    setError("");
    setSuccess("");

    try {
      const response = await fetch(
        `${API_URL}/conversations/${activeConversation.id}/documents/${encodeURIComponent(documentName)}`,
        { method: "DELETE" }
      );

      await readResponse(response, "Could not remove PDF.");

      const names = await loadAttachedDocuments(activeConversation.id);

      if (selectedDocument === documentName) {
        setSelectedDocument(names[0] || null);
      }

      await loadConversations();
      setSuccess(`${getDisplayName(documentName)} removed from conversation.`);
    } catch (err) {
      setError(err.message);
    } finally {
      setManagingDocuments(false);
    }
  };

  // ---------------- DELETE CONVERSATION ----------------

  const handleDeleteConversation = async (event, conversation) => {
    event.stopPropagation();

    const confirmed = window.confirm(
      `Delete this conversation?\n\n${conversation.title}\n\nIts messages and PDF associations will be deleted. Original PDFs will remain available.`
    );

    if (!confirmed) return;

    try {
      const response = await fetch(
        `${API_URL}/conversations/${conversation.id}`,
        { method: "DELETE" }
      );

      await readResponse(response, "Could not delete conversation.");

      if (activeConversation?.id === conversation.id) {
        setActiveConversation(null);
        setAttachedDocuments([]);
        setMessages([]);
        setQuestion("");
        setSelectedDocument(null);
      }

      await loadConversations();
      setSuccess("Conversation deleted.");
      setError("");
    } catch (err) {
      setError(err.message);
    }
  };

  // ---------------- SELECT DOCUMENT ----------------

  const handleSelectDocument = (documentName) => {
    setSelectedDocument(documentName);
    setActiveConversation(null);
    setAttachedDocuments([]);
    setMessages([]);
    setQuestion("");
    setError("");
    setSuccess("");
    setActiveView("assistant");

    setExpandedDocuments((previous) => ({
      ...previous,
      [documentName]: !previous[documentName]
    }));
  };

  // ---------------- ASK AI ----------------

  const handleAsk = async (event) => {
    event.preventDefault();

    const userQuestion = question.trim();

    if (!userQuestion || loading) return;

    if (!activeConversation && !selectedDocument) {
      setError("Please select a document before asking a question.");
      return;
    }

    setError("");
    setSuccess("");
    setQuestion("");

    // Display the user's question immediately.
    const temporaryId = `pending-${Date.now()}`;

    setMessages((previous) => [
      ...previous,
      {
        id: temporaryId,
        role: "user",
        content: userQuestion,
        sources: [],
        pending: true
      }
    ]);

    setLoading(true);

    try {
      let conversation = activeConversation;

      if (!conversation) {
        const title =
          userQuestion.length > 48
            ? `${userQuestion.substring(0, 45)}...`
            : userQuestion;

        const createResponse = await fetch(`${API_URL}/conversations`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify({
            document_names: [selectedDocument],
            title
          })
        });

        conversation = await readResponse(
          createResponse,
          "Could not create conversation."
        );

        setActiveConversation(conversation);
        setAttachedDocuments([selectedDocument]);
        await loadConversations();
      }

      const response = await fetch(`${API_URL}/ask`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          question: userQuestion,
          top_k: 5,
          conversation_id: conversation.id
        })
      });

      const data = await readResponse(
        response,
        "Failed to generate answer."
      );

      setMessages((previous) => [
        ...previous.map((message) =>
          message.id === temporaryId
            ? { ...message, pending: false }
            : message
        ),
        {
          role: "assistant",
          content: data.answer,
          sources: data.sources || []
        }
      ]);

      await loadConversations();
    } catch (err) {
      setMessages((previous) =>
        previous.map((message) =>
          message.id === temporaryId
            ? { ...message, pending: false, failed: true }
            : message
        )
      );

      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // ---------------- NEW CHAT ----------------

  const newChat = () => {
    setMessages([]);
    setQuestion("");
    setActiveConversation(null);
    setAttachedDocuments([]);
    setError("");
    setSuccess("");
    setActiveView("assistant");

    if (!selectedDocument && documents.length > 0) {
      setSelectedDocument(documents[0].name);
    }
  };

  // ---------------- CONVERSATION GROUPING ----------------

  const getDocumentConversations = (documentName) =>
    conversations.filter((conversation) => {
      const names = conversation.document_names || [
        conversation.document_name
      ];
      return names.includes(documentName);
    });

  // ---------------- PERMANENT PDF DELETION ----------------

  const handleDeleteDocument = async (documentName) => {
    if (deletingDocument) return;

    const confirmed = window.confirm(
      `Permanently delete "${getDisplayName(documentName)}"?\n\nThis will remove its indexed chunks and document associations from conversations. This action cannot be undone.`
    );

    if (!confirmed) return;

    setDeletingDocument(documentName);
    setError("");
    setSuccess("");

    try {
      const response = await fetch(
        `${API_URL}/documents?filename=${encodeURIComponent(documentName)}`,
        { method: "DELETE" }
      );

      await readResponse(response, "Could not delete this PDF.");

      if (selectedDocument === documentName) {
        setSelectedDocument(null);
        setActiveConversation(null);
        setAttachedDocuments([]);
        setMessages([]);
        setQuestion("");
      }

      await Promise.all([loadDocuments(), loadConversations()]);

      setSuccess(`${getDisplayName(documentName)} permanently deleted.`);
    } catch (err) {
      setError(err.message);
    } finally {
      setDeletingDocument(null);
    }
  };

  // ---------------- FILTER DOCUMENTS ----------------

  const filteredDocuments = documents.filter((doc) =>
    getDisplayName(doc.name)
      .toLowerCase()
      .includes(documentSearch.toLowerCase())
  );

  // ---------------- THINKING INDICATOR ----------------

  const ThinkingIndicator = () => (
    <div className="loading-message">
      <LoaderCircle className="spin" size={19} />
      <span>Llama 3.2 is thinking...</span>
    </div>
  );

  // ---------------- RENDER ----------------

  return (
    <div className="app-container">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-icon">
            <BrainCircuit size={25} />
          </div>
          <div>
            <h2>Knowledge AI</h2>
            <span>Local Intelligence</span>
          </div>
        </div>

        <button className="new-chat-btn" onClick={newChat}>
          <Plus size={18} />
          New conversation
        </button>

        <div className="sidebar-section">
          <p className="section-label">WORKSPACE</p>

          <button
            className={`nav-item ${activeView === "assistant" ? "active" : ""}`}
            onClick={() => setActiveView("assistant")}
          >
            <MessageSquare size={17} />
            AI Assistant
          </button>

          <button
            className={`nav-item ${activeView === "knowledge" ? "active" : ""}`}
            onClick={() => setActiveView("knowledge")}
          >
            <Database size={17} />
            Knowledge Base
          </button>
        </div>

        <div className="documents-section">
          <div className="document-heading">
            <p className="section-label">YOUR DOCUMENTS</p>
            <button
              className="icon-button"
              onClick={() => fileInputRef.current?.click()}
              title="Upload PDF"
            >
              <Plus size={17} />
            </button>
          </div>

          {documents.length === 0 ? (
            <p className="empty-documents">No documents uploaded yet.</p>
          ) : (
            documents.map((doc) => {
              const docConversations = getDocumentConversations(doc.name);
              const isExpanded = !!expandedDocuments[doc.name];

              return (
                <div className="document-group" key={doc.name}>
                  <div
                    className={`document-item ${
                      selectedDocument === doc.name ? "selected" : ""
                    }`}
                  >
                    <button
                      className="document-select"
                      onClick={() => handleSelectDocument(doc.name)}
                      title={doc.name}
                    >
                      <FileText size={17} />
                      <div className="document-info">
                        <span>{getDisplayName(doc.name)}</span>
                        <small>
                          {doc.pages} pages · {doc.chunks} chunks
                        </small>
                      </div>
                    </button>

                    <button
                      className="document-expand"
                      onClick={() =>
                        setExpandedDocuments((previous) => ({
                          ...previous,
                          [doc.name]: !previous[doc.name]
                        }))
                      }
                      title="Show conversations"
                    >
                      {isExpanded ? (
                        <ChevronDown size={15} />
                      ) : (
                        <ChevronRight size={15} />
                      )}
                    </button>
                  </div>

                  {isExpanded && (
                    <div className="conversation-list">
                      <button
                        className="start-document-chat"
                        onClick={() => createNewConversation(doc.name)}
                        disabled={creatingConversation}
                      >
                        <Plus size={14} />
                        New chat
                      </button>

                      {docConversations.length === 0 ? (
                        <p className="empty-conversations">
                          No conversations yet.
                        </p>
                      ) : (
                        docConversations.map((conversation) => (
                          <div
                            key={conversation.id}
                            className={`conversation-item ${
                              activeConversation?.id === conversation.id
                                ? "active"
                                : ""
                            }`}
                          >
                            <button
                              className="conversation-select"
                              onClick={() => openConversation(conversation)}
                              title={conversation.title}
                            >
                              <MessageCircle size={14} />
                              <span>{conversation.title}</span>
                            </button>

                            <button
                              className="delete-conversation"
                              onClick={(event) =>
                                handleDeleteConversation(event, conversation)
                              }
                              title="Delete conversation"
                              aria-label="Delete conversation"
                            >
                              <Trash2 size={15} />
                            </button>
                          </div>
                        ))
                      )}
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>

        <div className="sidebar-footer">
          <div className="local-status">
            <span className="status-dot"></span>
            Running locally
          </div>
          <span>Ollama · ChromaDB · RAG</span>
        </div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <div>
            <span className="topbar-title">
              {activeView === "knowledge"
                ? "Knowledge Base"
                : activeConversation?.title || "AI Assistant"}
            </span>

            <span className="topbar-subtitle">
              {activeView === "knowledge"
                ? `${documents.length} indexed PDF(s)`
                : activeConversation
                  ? `${attachedDocuments.length} PDF(s) attached`
                  : selectedDocument
                    ? `Document: ${getDisplayName(selectedDocument)}`
                    : "Your private knowledge workspace"}
            </span>
          </div>

          <div className="model-badge">
            <span className="status-dot"></span>
            Llama 3.2 · 3B
          </div>
        </header>

        {error && (
          <div className="error-message">
            <AlertTriangle size={15} />
            {error}
            <button onClick={() => setError("")} aria-label="Dismiss error">
              <X size={15} />
            </button>
          </div>
        )}

        {success && (
          <div className="success-message">
            <CheckCircle2 size={14} />
            {success}
            <button onClick={() => setSuccess("")} aria-label="Dismiss message">
              <X size={15} />
            </button>
          </div>
        )}

        {activeView === "knowledge" ? (
          <section className="knowledge-page">
            <div className="knowledge-header">
              <div>
                <h1>Your Knowledge Base</h1>
                <p>
                  Manage your uploaded PDFs and their indexed content.
                </p>
              </div>

              <button
                className="new-chat-btn"
                onClick={() => fileInputRef.current?.click()}
                disabled={uploading}
              >
                <Upload size={17} />
                Upload PDF
              </button>
            </div>

            <div className="knowledge-search">
              <Search size={18} />
              <input
                type="text"
                placeholder="Search your PDFs..."
                value={documentSearch}
                onChange={(event) => setDocumentSearch(event.target.value)}
              />
            </div>

            <div className="knowledge-summary">
              <div className="knowledge-stat">
                <FileText size={20} />
                <div>
                  <strong>{documents.length}</strong>
                  <span>Documents</span>
                </div>
              </div>

              <div className="knowledge-stat">
                <BookOpen size={20} />
                <div>
                  <strong>
                    {documents.reduce((sum, doc) => sum + doc.pages, 0)}
                  </strong>
                  <span>Total pages</span>
                </div>
              </div>

              <div className="knowledge-stat">
                <Database size={20} />
                <div>
                  <strong>
                    {documents.reduce((sum, doc) => sum + doc.chunks, 0)}
                  </strong>
                  <span>Indexed chunks</span>
                </div>
              </div>
            </div>

            <div className="knowledge-list">
              <div className="knowledge-list-heading">
                <h2>Indexed documents</h2>
                <span>{filteredDocuments.length} results</span>
              </div>

              {filteredDocuments.length === 0 ? (
                <div className="knowledge-empty">
                  <FileText size={35} />
                  <h3>
                    {documents.length === 0
                      ? "Your knowledge base is empty"
                      : "No matching PDFs"}
                  </h3>
                  <p>
                    {documents.length === 0
                      ? "Upload a PDF to start building your local knowledge base."
                      : "Try a different search term."}
                  </p>
                  {documents.length === 0 && (
                    <button
                      className="new-chat-btn"
                      onClick={() => fileInputRef.current?.click()}
                    >
                      <Upload size={16} />
                      Upload your first PDF
                    </button>
                  )}
                </div>
              ) : (
                filteredDocuments.map((doc) => (
                  <div className="knowledge-document" key={doc.name}>
                    <div className="knowledge-document-icon">
                      <FileText size={23} />
                    </div>

                    <div className="knowledge-document-info">
                      <strong title={doc.name}>
                        {getDisplayName(doc.name)}
                      </strong>
                      <span>{doc.pages} pages · {doc.chunks} chunks</span>
                      <small title={doc.name}>{doc.name}</small>
                    </div>

                    <div className="knowledge-document-actions">
                      <button
                        onClick={() => {
                          handleSelectDocument(doc.name);
                          setActiveView("assistant");
                        }}
                        title="Ask questions about this PDF"
                      >
                        <MessageSquare size={16} />
                        Ask
                      </button>

                      <button
                        className="knowledge-delete"
                        onClick={() => handleDeleteDocument(doc.name)}
                        disabled={deletingDocument === doc.name}
                        title="Permanently delete PDF"
                      >
                        {deletingDocument === doc.name ? (
                          <LoaderCircle className="spin" size={16} />
                        ) : (
                          <Trash2 size={16} />
                        )}
                        Delete
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>
          </section>
        ) : (
          <>
            {activeConversation && (
              <div className="attached-documents-panel">
                <div className="attached-documents-heading">
                  <span>
                    <Paperclip size={14} />
                    Conversation documents ({attachedDocuments.length})
                  </span>

                  <select
                    defaultValue=""
                    disabled={managingDocuments || documents.length === 0}
                    onChange={(event) => {
                      const value = event.target.value;
                      if (value) attachDocument(value);
                      event.target.value = "";
                    }}
                  >
                    <option value="">+ Attach another PDF</option>
                    {documents
                      .filter((doc) => !attachedDocuments.includes(doc.name))
                      .map((doc) => (
                        <option key={doc.name} value={doc.name}>
                          {getDisplayName(doc.name)}
                        </option>
                      ))}
                  </select>
                </div>

                <div className="attached-document-list">
                  {attachedDocuments.map((name) => (
                    <div className="attached-document-chip" key={name}>
                      <FileText size={14} />
                      <span title={name}>{getDisplayName(name)}</span>
                      <button
                        onClick={() => detachDocument(name)}
                        disabled={managingDocuments}
                        title="Remove from conversation"
                      >
                        <X size={14} />
                      </button>
                    </div>
                  ))}

                  {attachedDocuments.length === 0 && (
                    <span className="empty-conversations">
                      No documents attached.
                    </span>
                  )}
                </div>

                {managingDocuments && (
                  <span className="document-management-status">
                    Updating conversation documents...
                  </span>
                )}
              </div>
            )}

            <section className="chat-area">
              {messages.length === 0 ? (
                <div className="welcome-screen">
                  <div className="welcome-icon">
                    <Sparkles size={29} />
                  </div>

                  <h1>What would you like to know?</h1>

                  <p>
                    {activeConversation
                      ? "Ask questions across all PDFs attached to this conversation."
                      : selectedDocument
                        ? `Ask questions about ${getDisplayName(selectedDocument)}.`
                        : "Select a document from the sidebar to start a conversation."}
                    {" "}Your AI assistant runs completely locally.
                  </p>

                  <div className="suggestion-grid">
                    <button
                      onClick={() => setQuestion("Summarize this document.")}
                      disabled={!selectedDocument && !activeConversation}
                    >
                      <FileText size={19} />
                      <span>
                        <strong>Summarize document</strong>
                        <small>Get key points and insights</small>
                      </span>
                    </button>

                    <button
                      onClick={() =>
                        setQuestion("Explain the main concepts in these documents.")
                      }
                      disabled={!selectedDocument && !activeConversation}
                    >
                      <BrainCircuit size={19} />
                      <span>
                        <strong>Explain concepts</strong>
                        <small>Understand complex topics</small>
                      </span>
                    </button>

                    <button
                      onClick={() =>
                        setQuestion("What are the important topics in these documents?")
                      }
                      disabled={!selectedDocument && !activeConversation}
                    >
                      <MessageSquare size={19} />
                      <span>
                        <strong>Find important topics</strong>
                        <small>Discover relevant information</small>
                      </span>
                    </button>

                    <button onClick={() => fileInputRef.current?.click()}>
                      <Upload size={19} />
                      <span>
                        <strong>Upload a document</strong>
                        <small>Add a new PDF to your library</small>
                      </span>
                    </button>
                  </div>
                </div>
              ) : (
                <div className="messages-container">
                  {messages.map((message, index) => (
                    <div
                      className={`message-row ${message.role}`}
                      key={message.id || index}
                    >
                      <div className="message-avatar">
                        {message.role === "user" ? (
                          <User size={18} />
                        ) : (
                          <Bot size={19} />
                        )}
                      </div>

                      <div className="message-content">
                        <span className="message-author">
                          {message.role === "user" ? "You" : "Knowledge AI"}
                        </span>

                        <div className="message-text">
                          {message.content}
                        </div>

                        {message.pending && (
                          <span className="document-management-status">
                            Your question has been sent...
                          </span>
                        )}

                        {message.failed && (
                          <span className="document-management-status">
                            The request failed. Please try asking again.
                          </span>
                        )}

                        {message.sources?.length > 0 && (
                          <div className="sources-container">
                            <span className="sources-title">
                              <FileText size={15} />
                              Sources
                            </span>

                            {message.sources.map((source, sourceIndex) => (
                              <div className="source-item" key={sourceIndex}>
                                <FileText size={15} />
                                <span>{getDisplayName(source.source)}</span>
                                <small>Page {source.page_number}</small>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  ))}

                  <div ref={messagesEndRef} />
                  {loading && <ThinkingIndicator />}
                </div>
              )}
            </section>

            <div className="input-section">
              <form className="chat-input-box" onSubmit={handleAsk}>
                <textarea
                  placeholder={
                    activeConversation
                      ? "Ask anything about your attached PDFs..."
                      : selectedDocument
                        ? "Ask anything about this document..."
                        : "Select a document to start asking questions..."
                  }
                  value={question}
                  onChange={(event) => setQuestion(event.target.value)}
                  disabled={
                    (!selectedDocument && !activeConversation) || loading
                  }
                  onKeyDown={(event) => {
                    if (event.key === "Enter" && !event.shiftKey) {
                      event.preventDefault();
                      handleAsk(event);
                    }
                  }}
                  rows={2}
                />

                <div className="input-bottom">
                  <span>Shift + Enter for a new line</span>
                  <button
                    type="submit"
                    className="send-button"
                    disabled={
                      !question.trim() ||
                      (!selectedDocument && !activeConversation) ||
                      loading
                    }
                  >
                    <Send size={17} />
                  </button>
                </div>
              </form>

              <p className="privacy-note">
                <CheckCircle2 size={13} />
                Your documents and conversations are processed locally.
              </p>
            </div>
          </>
        )}
      </main>

      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf,application/pdf"
        hidden
        onChange={handleUpload}
      />

      {(uploading || creatingConversation) && (
        <div className="upload-overlay">
          <LoaderCircle className="spin" size={24} />
          {uploading
            ? "Processing and indexing your PDF..."
            : "Creating conversation..."}
        </div>
      )}
    </div>
  );
}

export default App;
