import { useEffect, useMemo, useRef, useState } from "react";
import {
  BookOpen,
  CheckCircle2,
  Copy,
  Check,
  Download,
  ExternalLink,
  FileSearch,
  FileText,
  Filter,
  Layers,
  LoaderCircle,
  Search,
  Sparkles,
  Eye,
  AlignLeft,
  Info,
} from "lucide-react";
import { getCorpusChunks, getCorpusOverview } from "./api";
import type { CorpusChunkItem, CorpusDocument, CorpusOverview } from "./types";

interface CorpusInspectorViewProps {
  activeCorpus?: "labour" | "hcmut";
  onSelectCorpus?: (corpus: "labour" | "hcmut") => void;
  initialCorpus?: "labour" | "hcmut";
  initialDocCode?: string | null;
  initialChunkId?: string | null;
  onSelectDocCode?: (docCode: string) => void;
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatClausesAndPoints(text: string, title?: string) {
  let body = text;
  if (title && body.startsWith(title)) {
    body = body.slice(title.length).trim();
  }

  // Regex to split on Vietnamese legal clauses e.g. " 1. ", " 2. ", "Khoản 1. "
  const clauseRegex = /(?=(?:^|\s)(?:Khoản\s+\d+|[1-9]\d*)\.\s+[A-ZÀ-Ỹ“\"])/g;
  const segments = body.split(clauseRegex).map((s) => s.trim()).filter(Boolean);

  if (segments.length <= 1) {
    return <p className="chunk-raw-paragraph">{body || text}</p>;
  }

  return (
    <div className="chunk-clause-list">
      {segments.map((seg, idx) => {
        const leadMatch = seg.match(/^((?:Khoản\s+\d+|[1-9]\d*)\.)\s+(.*)$/s);
        if (leadMatch) {
          const [, num, rest] = leadMatch;
          return (
            <div key={idx} className="chunk-clause-row">
              <span className="clause-chip">{num}</span>
              <span className="clause-text">{rest}</span>
            </div>
          );
        }
        return (
          <p key={idx} className="chunk-clause-lead">
            {seg}
          </p>
        );
      })}
    </div>
  );
}

export function CorpusInspectorView({
  activeCorpus,
  onSelectCorpus,
  initialCorpus = "labour",
  initialDocCode,
  initialChunkId,
}: CorpusInspectorViewProps) {
  // Synchronized corpus state
  const [localCorpus, setLocalCorpus] = useState<"labour" | "hcmut">(activeCorpus || initialCorpus);
  const corpus = activeCorpus || localCorpus;

  const [overview, setOverview] = useState<CorpusOverview | null>(null);
  const [selectedDocCode, setSelectedDocCode] = useState<string | null>(initialDocCode || null);
  const [loadingOverview, setLoadingOverview] = useState(true);

  // Active page for PDF jumping
  const [activePdfPage, setActivePdfPage] = useState<number>(1);

  // Chunks state
  const [chunks, setChunks] = useState<CorpusChunkItem[]>([]);
  const [loadingChunks, setLoadingChunks] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [chapterFilter, setChapterFilter] = useState<string>("all");
  const [viewMode, setViewMode] = useState<"formatted" | "verbatim">("formatted");

  // Highlight state
  const [highlightChunkId, setHighlightChunkId] = useState<string | null>(initialChunkId || null);
  const [copiedSha, setCopiedSha] = useState(false);
  const activeChunkRef = useRef<HTMLDivElement>(null);

  // Sync corpus when prop changes
  useEffect(() => {
    if (activeCorpus) {
      setLocalCorpus(activeCorpus);
    }
  }, [activeCorpus]);

  useEffect(() => {
    if (initialDocCode) {
      setSelectedDocCode(initialDocCode);
    }
    if (initialChunkId) {
      setHighlightChunkId(initialChunkId);
    }
  }, [initialDocCode, initialChunkId]);

  const handleCorpusSwitch = (newCorpus: "labour" | "hcmut") => {
    setLocalCorpus(newCorpus);
    onSelectCorpus?.(newCorpus);
    setSearchQuery("");
    setChapterFilter("all");
    setActivePdfPage(1);
    setHighlightChunkId(null);
  };

  // Load Overview whenever corpus changes
  useEffect(() => {
    let active = true;
    setLoadingOverview(true);
    getCorpusOverview(corpus)
      .then((data) => {
        if (!active) return;
        setOverview(data);
        setLoadingOverview(false);
        // Default select first doc if not selected or invalid for this corpus
        if (data.documents.length > 0) {
          setSelectedDocCode((curr) => {
            const exists = curr && data.documents.some((d) => d.doc_code.toLowerCase() === curr.toLowerCase());
            return exists ? curr : data.documents[0].doc_code;
          });
        }
      })
      .catch((err) => {
        if (!active) return;
        console.error("Failed to load corpus overview:", err);
        setLoadingOverview(false);
      });

    return () => {
      active = false;
    };
  }, [corpus]);

  // Load chunks whenever corpus or selectedDocCode changes
  useEffect(() => {
    if (!selectedDocCode) return;
    let active = true;
    setLoadingChunks(true);

    getCorpusChunks({
      corpus,
      doc_code: selectedDocCode,
      limit: 500,
    })
      .then((res) => {
        if (!active) return;
        setChunks(res.items);
        setLoadingChunks(false);

        // If a target chunk was specified, jump PDF to its page
        if (highlightChunkId) {
          const target = res.items.find((c) => c.article_id === highlightChunkId);
          if (target?.source_pages && target.source_pages.length > 0) {
            setActivePdfPage(target.source_pages[0]);
          }
        }
      })
      .catch((err) => {
        if (!active) return;
        console.error("Failed to load chunks:", err);
        setLoadingChunks(false);
      });

    return () => {
      active = false;
    };
  }, [corpus, selectedDocCode, highlightChunkId]);

  // Auto-scroll to highlighted chunk when loaded
  useEffect(() => {
    if (highlightChunkId && !loadingChunks && activeChunkRef.current) {
      activeChunkRef.current.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  }, [highlightChunkId, loadingChunks, chunks]);

  const selectedDoc: CorpusDocument | undefined = useMemo(() => {
    if (!overview || !selectedDocCode) return undefined;
    return (
      overview.documents.find((d) => d.doc_code.toLowerCase() === selectedDocCode.toLowerCase()) ||
      overview.documents[0]
    );
  }, [overview, selectedDocCode]);

  // Filter chunks in Pane B
  const filteredChunks = useMemo(() => {
    return chunks.filter((c) => {
      if (chapterFilter !== "all" && c.chapter !== chapterFilter) {
        return false;
      }
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase().trim();
        const inId = c.article_id.toLowerCase().includes(q);
        const inTitle = c.title.toLowerCase().includes(q);
        const inText = c.text.toLowerCase().includes(q);
        return inId || inTitle || inText;
      }
      return true;
    });
  }, [chunks, chapterFilter, searchQuery]);

  const copySha256 = (sha: string) => {
    navigator.clipboard.writeText(sha);
    setCopiedSha(true);
    setTimeout(() => setCopiedSha(false), 2000);
  };

  const jumpToPage = (pageNum: number, articleId?: string) => {
    setActivePdfPage(pageNum);
    if (articleId) {
      setHighlightChunkId(articleId);
    }
  };

  return (
    <div className="corpus-inspector">
      {/* ---------------- Top Summary Bar ---------------- */}
      <header className="corpus-topbar">
        <div className="corpus-switch-group">
          <button
            type="button"
            className={`corpus-pill-btn ${corpus === "labour" ? "active" : ""}`}
            onClick={() => handleCorpusSwitch("labour")}
          >
            <BookOpen size={16} />
            <span>Pháp luật Lao động (10 văn bản)</span>
          </button>
          <button
            type="button"
            className={`corpus-pill-btn ${corpus === "hcmut" ? "active" : ""}`}
            onClick={() => handleCorpusSwitch("hcmut")}
          >
            <Layers size={16} />
            <span>Học vụ HCMUT (10 văn bản)</span>
          </button>
        </div>

        {overview && (
          <div className="corpus-stats-strip">
            <div className="corpus-stat-badge">
              <FileText size={14} />
              <span>
                <strong>{overview.total_documents}</strong> PDF nguồn
              </span>
            </div>
            <div className="corpus-stat-badge">
              <Layers size={14} />
              <span>
                <strong>{overview.total_chunks}</strong> Chunks Điều/Khoản
              </span>
            </div>
            <div className="corpus-stat-badge highlight">
              <Sparkles size={14} />
              <span>
                Phân rã: <strong>{overview.chunking_granularity}</strong>
              </span>
            </div>
            <div className="corpus-stat-badge mono">
              <span>{overview.id_template}</span>
            </div>
          </div>
        )}
      </header>

      {/* ---------------- Main Content Body ---------------- */}
      <div className="corpus-body">
        {/* Left Column: Document Selector */}
        <aside className="corpus-doc-sidebar" aria-label="Danh mục văn bản nguồn">
          <div className="doc-sidebar-header">
            <h3>Tài liệu PDF gốc</h3>
            <span className="count-pill">{overview?.documents.length ?? 0}</span>
          </div>

          {loadingOverview ? (
            <div className="corpus-loading">
              <LoaderCircle className="spinning" size={20} />
              <span>Đang nạp danh mục văn bản…</span>
            </div>
          ) : (
            <nav className="doc-list-nav">
              {overview?.documents.map((doc) => {
                const isSelected = selectedDoc?.doc_code === doc.doc_code;
                return (
                  <button
                    key={doc.doc_code}
                    type="button"
                    className={`doc-item-btn ${isSelected ? "active" : ""}`}
                    onClick={() => {
                      setSelectedDocCode(doc.doc_code);
                      setChapterFilter("all");
                      setSearchQuery("");
                      setHighlightChunkId(null);
                      setActivePdfPage(1);
                    }}
                  >
                    <div className="doc-badge-row">
                      <span className="doc-code-badge">{doc.doc_code}</span>
                      <span className="doc-chunks-chip">{doc.chunk_count} chunks</span>
                    </div>
                    <div className="doc-title-text" title={doc.doc_title}>
                      {doc.doc_title}
                    </div>
                    <div className="doc-meta-footer">
                      <span>{doc.pages} trang</span>
                      <span>·</span>
                      <span>{formatBytes(doc.bytes)}</span>
                      {doc.pdf_available && (
                        <span className="pdf-status-ok" title="File PDF đã xác minh trên máy">
                          <CheckCircle2 size={12} /> Có sẵn
                        </span>
                      )}
                    </div>
                  </button>
                );
              })}
            </nav>
          )}
        </aside>

        {/* Right Split View: Pane A (PDF) & Pane B (Chunks) */}
        <div className="corpus-split-content">
          {selectedDoc ? (
            <>
              {/* Document Subheader / Metadata Banner */}
              <div className="doc-banner">
                <div className="doc-banner-info">
                  <div className="doc-banner-badges">
                    <span className="badge-code">{selectedDoc.doc_code}</span>
                    <span className="badge-pages">{selectedDoc.pages} trang</span>
                    <span className="badge-size">{formatBytes(selectedDoc.bytes)}</span>
                    <span className="badge-chunks">{selectedDoc.chunk_count} Chunks Điều/Khoản</span>
                    {selectedDoc.document_number && (
                      <span className="badge-docnum">Số: {selectedDoc.document_number}</span>
                    )}
                    {selectedDoc.issued_date && (
                      <span className="badge-date">Ban hành: {selectedDoc.issued_date}</span>
                    )}
                  </div>
                  <h2 className="doc-banner-title">{selectedDoc.doc_title}</h2>
                  <div className="doc-banner-hash">
                    <span className="hash-label">SHA-256:</span>
                    <code className="hash-code">{selectedDoc.sha256}</code>
                    <button
                      type="button"
                      className="copy-btn"
                      onClick={() => copySha256(selectedDoc.sha256)}
                      title="Sao chép SHA-256"
                    >
                      {copiedSha ? <Check size={13} className="text-emerald-500" /> : <Copy size={13} />}
                    </button>
                  </div>
                </div>

                <div className="doc-banner-actions">
                  <a
                    href={`${selectedDoc.pdf_url}#page=${activePdfPage}`}
                    target="_blank"
                    rel="noreferrer"
                    className="button-secondary open-pdf-btn"
                  >
                    <ExternalLink size={14} /> Mở PDF tab mới
                  </a>
                  <a
                    href={selectedDoc.pdf_url}
                    download={selectedDoc.pdf_filename}
                    className="button-secondary download-pdf-btn"
                  >
                    <Download size={14} /> Tải PDF
                  </a>
                </div>
              </div>

              {/* The Two Split Panes */}
              <div className="split-panes-container">
                {/* ---------------- PANE A: Native PDF Viewer ---------------- */}
                <section className="pane-container pane-pdf" aria-label="PDF Viewer">
                  <header className="pane-header">
                    <div className="pane-title-group">
                      <div className="pane-title">
                        <FileSearch size={16} />
                        <span>PDF GỐC (BẢN CHÍNH THỨC)</span>
                      </div>
                      <div className="pdf-page-indicator">
                        <span>
                          Đang xem: Trang <strong>{activePdfPage}</strong> / {selectedDoc.pages}
                        </span>
                      </div>
                    </div>
                    <span className="file-name-pill">{selectedDoc.pdf_filename}</span>
                  </header>

                  <div className="pdf-frame-wrapper">
                    <iframe
                      key={`${selectedDoc.doc_code}_p${activePdfPage}`}
                      src={`${selectedDoc.pdf_url}#page=${activePdfPage}&toolbar=1&navpanes=1`}
                      title={`PDF - ${selectedDoc.doc_title} - Trang ${activePdfPage}`}
                      className="pdf-embedded-frame"
                    />
                  </div>
                </section>

                {/* ---------------- PANE B: Chunks List ---------------- */}
                <section className="pane-container pane-chunks" aria-label="Extracted Chunks">
                  <header className="pane-header">
                    <div className="pane-title">
                      <Layers size={16} />
                      <span>CHUNKS ĐÃ TÁCH & INDEX ({filteredChunks.length} / {chunks.length})</span>
                    </div>

                    <div className="view-mode-toggle">
                      <button
                        type="button"
                        className={`mode-btn ${viewMode === "formatted" ? "active" : ""}`}
                        onClick={() => setViewMode("formatted")}
                        title="Định dạng Khoản/Điểm dễ đọc"
                      >
                        <AlignLeft size={13} /> Định dạng
                      </button>
                      <button
                        type="button"
                        className={`mode-btn ${viewMode === "verbatim" ? "active" : ""}`}
                        onClick={() => setViewMode("verbatim")}
                        title="Nguyên văn thô"
                      >
                        <Eye size={13} /> Thô
                      </button>
                    </div>
                  </header>

                  {/* Chunks Filter Bar */}
                  <div className="chunks-filter-bar">
                    <div className="search-box">
                      <Search size={14} className="search-icon" />
                      <input
                        type="text"
                        placeholder="Lọc Điều, khoản, từ khóa..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                      />
                      {searchQuery && (
                        <button
                          type="button"
                          className="clear-search-btn"
                          onClick={() => setSearchQuery("")}
                        >
                          ×
                        </button>
                      )}
                    </div>

                    {selectedDoc.chapters && selectedDoc.chapters.length > 0 && (
                      <div className="chapter-select-wrap">
                        <Filter size={13} />
                        <select
                          value={chapterFilter}
                          onChange={(e) => setChapterFilter(e.target.value)}
                          aria-label="Lọc theo chương"
                        >
                          <option value="all">Tất cả các chương ({selectedDoc.chapters.length})</option>
                          {selectedDoc.chapters.map((ch) => (
                            <option key={ch} value={ch}>
                              {ch}
                            </option>
                          ))}
                        </select>
                      </div>
                    )}
                  </div>

                  {/* Chunks Scrollable Cards List */}
                  <div className="chunks-list-scroll">
                    {loadingChunks ? (
                      <div className="corpus-loading">
                        <LoaderCircle className="spinning" size={20} />
                        <span>Đang tải các chunk Điều/Khoản…</span>
                      </div>
                    ) : filteredChunks.length === 0 ? (
                      <div className="chunks-empty">
                        <p>Không tìm thấy chunk nào phù hợp với bộ lọc hiện tại.</p>
                      </div>
                    ) : (
                      filteredChunks.map((chunk) => {
                        const isHighlighted = highlightChunkId === chunk.article_id;
                        const pageLabel =
                          chunk.source_pages && chunk.source_pages.length > 0
                            ? chunk.source_pages.length === 1
                              ? `Trang ${chunk.source_pages[0]}`
                              : `Trang ${chunk.source_pages[0]}–${chunk.source_pages[chunk.source_pages.length - 1]}`
                            : null;

                        return (
                          <article
                            key={chunk.article_id}
                            ref={isHighlighted ? activeChunkRef : null}
                            className={`chunk-card ${isHighlighted ? "highlighted-pulse" : ""}`}
                            onClick={() => {
                              setHighlightChunkId(chunk.article_id);
                              if (chunk.source_pages && chunk.source_pages.length > 0) {
                                jumpToPage(chunk.source_pages[0], chunk.article_id);
                              }
                            }}
                          >
                            <header className="chunk-card-head">
                              <div className="chunk-badges-left">
                                <span className="chunk-id-badge">{chunk.article_id}</span>
                                {chunk.chapter && (
                                  <span className="chunk-chapter-badge" title={chunk.chapter}>
                                    {chunk.chapter}
                                  </span>
                                )}
                                {pageLabel && chunk.source_pages && (
                                  <button
                                    type="button"
                                    className="badge-page-jump"
                                    title={`Bấm để chuyển PDF đến trang ${chunk.source_pages[0]}`}
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      jumpToPage(chunk.source_pages![0], chunk.article_id);
                                    }}
                                  >
                                    <FileText size={11} /> 📄 {pageLabel}
                                  </button>
                                )}
                                {chunk.char_start != null && chunk.char_end != null && (
                                  <span
                                    className="badge-char-range"
                                    title={`Vị trí ký tự trong toàn văn: ${chunk.char_start} – ${chunk.char_end}`}
                                  >
                                    char {chunk.char_start}–{chunk.char_end}
                                  </span>
                                )}
                              </div>
                              <div className="chunk-meta-right">
                                <span>{chunk.char_count} ký tự</span>
                                <span>·</span>
                                <span>{chunk.word_count} từ</span>
                                {chunk.clause_count > 0 && (
                                  <>
                                    <span>·</span>
                                    <span className="badge-clause">{chunk.clause_count} khoản</span>
                                  </>
                                )}
                                {chunk.point_count > 0 && (
                                  <>
                                    <span>·</span>
                                    <span className="badge-point">{chunk.point_count} điểm</span>
                                  </>
                                )}
                              </div>
                            </header>

                            <h4 className="chunk-card-title">{chunk.title}</h4>

                            <div className="chunk-card-content">
                              {viewMode === "formatted"
                                ? formatClausesAndPoints(chunk.text, chunk.title)
                                : <pre className="verbatim-text">{chunk.text}</pre>}
                            </div>

                            <footer className="chunk-card-foot">
                              <span className="index-integrity-note">
                                <CheckCircle2 size={12} /> Đã index trong hybrid vector/FTS5 store
                              </span>
                              {chunk.extraction && (
                                <span className="extraction-pipeline-badge" title={chunk.extraction}>
                                  <Info size={11} /> Pipeline: pypdf layout + NFC
                                </span>
                              )}
                            </footer>
                          </article>
                        );
                      })
                    )}
                  </div>
                </section>
              </div>
            </>
          ) : (
            <div className="no-doc-selected">
              <FileSearch size={32} />
              <p>Chọn một văn bản từ danh sách bên trái để đối chiếu PDF gốc và Chunk.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
