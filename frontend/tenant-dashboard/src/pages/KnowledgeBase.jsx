import { useState, useEffect, useCallback, useRef } from 'react';
import { API_ABSOLUTE_URL } from '../config/environment';
import { extractErrorMessage } from '../hooks/useAsyncOperation';
import {
  BookOpenIcon,
  DocumentTextIcon,
  CloudArrowUpIcon,
  TrashIcon,
  ArrowDownTrayIcon,
  MagnifyingGlassIcon,
  FolderOpenIcon,
  GlobeAltIcon,
  LockClosedIcon,
  CheckCircleIcon,
  ExclamationCircleIcon,
  ClockIcon,
  ArrowPathIcon,
  EyeIcon,
  XMarkIcon,
} from '@heroicons/react/24/outline';
import { knowledgeApi, globalKnowledgeApi } from '../services/api';

// Tab configuration
const TABS = [
  { id: 'private', label: 'My Documents', icon: LockClosedIcon },
  { id: 'global', label: 'Global Documents', icon: GlobeAltIcon },
];

// Status badge component
function StatusBadge({ status }) {
  const config = {
    indexed: { color: 'bg-green-100 text-green-700', icon: CheckCircleIcon, label: 'Indexed' },
    pending: { color: 'bg-yellow-100 text-yellow-700', icon: ClockIcon, label: 'Pending' },
    error: { color: 'bg-red-100 text-red-700', icon: ExclamationCircleIcon, label: 'Error' },
  };

  const { color, icon: Icon, label } = config[status] || config.pending;

  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${color}`}>
      <Icon className="w-3 h-3" />
      {label}
    </span>
  );
}

// Document row component
function DocumentRow({ doc, onDelete, onDownload, onView, canDelete = true, canView = false }) {
  const [deleting, setDeleting] = useState(false);

  const handleDelete = async () => {
    if (!window.confirm(`Delete "${doc.filename}"? This cannot be undone.`)) return;

    setDeleting(true);
    try {
      await onDelete(doc.document_id);
    } finally {
      setDeleting(false);
    }
  };

  const formatSize = (bytes) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleDateString('en-ZA', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
    });
  };

  return (
    <div className="flex items-center gap-4 p-4 bg-theme-surface rounded-lg border border-theme hover:border-theme-primary/30 transition-colors">
      {/* File icon */}
      <div className="p-3 bg-theme-primary/10 rounded-lg">
        <DocumentTextIcon className="w-6 h-6 text-theme-primary" />
      </div>

      {/* File info */}
      <div className="flex-1 min-w-0">
        <h4 className="font-medium text-theme truncate">{doc.filename}</h4>
        <div className="flex items-center gap-3 mt-1 text-sm text-theme-muted">
          {doc.file_size > 0 && (
            <>
              <span>{formatSize(doc.file_size)}</span>
              <span>•</span>
            </>
          )}
          <span>{formatDate(doc.uploaded_at || doc.indexed_at)}</span>
          {doc.category && doc.category !== 'general' && (
            <>
              <span>•</span>
              <span className="capitalize">{doc.category}</span>
            </>
          )}
        </div>
      </div>

      {/* Status */}
      <StatusBadge status={doc.status} />

      {/* Actions */}
      <div className="flex items-center gap-2">
        {canView && (
          <button
            onClick={() => onView(doc)}
            className="p-2 text-theme-muted hover:text-theme hover:bg-theme-border-light rounded-lg transition-colors"
            title="View content"
          >
            <EyeIcon className="w-5 h-5" />
          </button>
        )}
        <button
          onClick={() => onDownload(doc)}
          className="p-2 text-theme-muted hover:text-theme hover:bg-theme-border-light rounded-lg transition-colors"
          title="Download"
        >
          <ArrowDownTrayIcon className="w-5 h-5" />
        </button>
        {canDelete && (
          <button
            onClick={handleDelete}
            disabled={deleting}
            className="p-2 text-theme-muted hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors disabled:opacity-50"
            title="Delete"
          >
            <TrashIcon className="w-5 h-5" />
          </button>
        )}
      </div>
    </div>
  );
}

// Upload component
function UploadSection({ onUpload }) {
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);

  const handleUpload = async (files) => {
    if (!files?.length) return;

    setUploading(true);
    try {
      for (const file of files) {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('category', 'general');
        formData.append('visibility', 'private');
        formData.append('auto_index', 'true');
        await onUpload(formData);
      }
    } finally {
      setUploading(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    handleUpload(e.dataTransfer.files);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setDragOver(true);
  };

  const handleDragLeave = () => {
    setDragOver(false);
  };

  return (
    <div
      onDrop={handleDrop}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      className={`border-2 border-dashed rounded-lg p-6 text-center transition-colors ${
        dragOver
          ? 'border-theme-primary bg-theme-primary/5'
          : 'border-theme hover:border-theme-primary/50'
      }`}
    >
      {uploading ? (
        <div className="flex flex-col items-center gap-2">
          <ArrowPathIcon className="w-8 h-8 text-theme-primary animate-spin" />
          <p className="text-theme-muted">Uploading...</p>
        </div>
      ) : (
        <>
          <CloudArrowUpIcon className="w-10 h-10 text-theme-muted mx-auto mb-3" />
          <p className="text-theme font-medium">
            Drag and drop files here, or{' '}
            <label className="text-theme-primary hover:text-theme-primary-dark cursor-pointer">
              browse
              <input
                type="file"
                multiple
                accept=".pdf,.doc,.docx,.txt,.md"
                className="hidden"
                onChange={(e) => handleUpload(e.target.files)}
              />
            </label>
          </p>
          <p className="text-sm text-theme-muted mt-1">
            Supported: PDF, DOC, DOCX, TXT, MD
          </p>
        </>
      )}
    </div>
  );
}

// Document preview modal
function DocumentPreviewModal({ doc, onClose }) {
  const hasOriginal = doc.has_original_file;
  const [content, setContent] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [iframeError, setIframeError] = useState(false);

  // Get the proxy URL for the original file (avoids CORS issues)
  const originalFileUrl = hasOriginal
    ? globalKnowledgeApi.getOriginalFileUrl(doc.document_id)
    : null;

  // Fetch document details/content
  useEffect(() => {
    const fetchContent = async () => {
      setLoading(true);
      setError(null);
      try {
        if (hasOriginal) {
          // For PDFs, we'll use iframe with proxy URL - no need to fetch content
          setLoading(false);
        } else {
          // For non-PDF, fetch text content
          const data = await globalKnowledgeApi.getDocumentContent(doc.document_id);
          setContent(data.content || data.text || JSON.stringify(data, null, 2));
          setLoading(false);
        }
      } catch (err) {
        setError(err.message || 'Failed to load document content');
        setLoading(false);
      }
    };
    fetchContent();
  }, [doc.document_id, hasOriginal]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50" onClick={onClose}>
      <div
        className="bg-theme-surface rounded-lg shadow-xl w-full max-w-4xl max-h-[90vh] flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-theme">
          <div className="flex items-center gap-3 min-w-0">
            <DocumentTextIcon className="w-5 h-5 text-theme-primary flex-shrink-0" />
            <div className="min-w-0">
              <h3 className="font-medium text-theme truncate">{doc.filename}</h3>
              {doc.original_filename && doc.original_filename !== doc.filename && (
                <p className="text-xs text-theme-muted truncate">{doc.original_filename}</p>
              )}
            </div>
          </div>
          <div className="flex items-center gap-2">
            {doc.chunk_count > 0 && (
              <span className="text-xs text-theme-muted bg-theme-surface-elevated px-2 py-1 rounded">
                {doc.chunk_count} chunks
              </span>
            )}
            <button
              onClick={onClose}
              className="p-1 text-theme-muted hover:text-theme rounded-lg hover:bg-theme-border-light"
            >
              <XMarkIcon className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-auto p-4 min-h-0">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <ArrowPathIcon className="w-8 h-8 text-theme-primary animate-spin" />
              <span className="ml-3 text-theme-muted">Loading document...</span>
            </div>
          ) : error ? (
            <div className="text-center py-12">
              <ExclamationCircleIcon className="w-10 h-10 text-red-400 mx-auto mb-3" />
              <p className="text-red-600">{error}</p>
            </div>
          ) : hasOriginal ? (
            iframeError ? (
              <div className="flex flex-col items-center justify-center py-12 text-center">
                <ExclamationCircleIcon className="w-12 h-12 text-amber-500 mb-4" />
                <h4 className="text-lg font-medium text-theme mb-2">Unable to Preview Document</h4>
                <p className="text-theme-muted mb-4">
                  The document preview is not available. You can download it instead.
                </p>
                <button
                  onClick={() => globalKnowledgeApi.downloadDocument(doc.document_id, doc.filename, true)}
                  className="flex items-center gap-2 px-4 py-2 bg-theme-primary text-white rounded-lg hover:bg-theme-primary-hover transition-colors"
                >
                  <ArrowDownTrayIcon className="w-5 h-5" />
                  Download {doc.filename}
                </button>
              </div>
            ) : (
              <iframe
                src={originalFileUrl}
                className="w-full h-full min-h-[65vh] rounded border border-theme"
                title={doc.filename}
                onError={() => setIframeError(true)}
                onLoad={(e) => {
                  // Check if iframe loaded successfully by trying to access its content
                  // This won't work for cross-origin but catches some error cases
                  try {
                    const iframe = e.target;
                    // If the iframe is empty or has an error, show fallback
                    if (iframe.contentDocument?.body?.innerHTML === '') {
                      setIframeError(true);
                    }
                  } catch {
                    // Cross-origin error is expected for successful loads from proxy
                  }
                }}
              />
            )
          ) : (
            <div className="bg-theme-surface-elevated rounded-lg p-4 h-full overflow-auto">
              <pre className="whitespace-pre-wrap text-sm text-theme font-mono leading-relaxed">
                {content || doc.content_preview || 'No content available'}
              </pre>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between p-4 border-t border-theme">
          <div className="text-xs text-theme-muted">
            {doc.file_type?.toUpperCase()} • Uploaded {doc.uploaded_at ? new Date(doc.uploaded_at).toLocaleDateString() : 'recently'}
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={onClose}
              className="px-4 py-2 text-sm text-theme-muted hover:text-theme rounded-lg hover:bg-theme-border-light"
            >
              Close
            </button>
            <button
              onClick={() => globalKnowledgeApi.downloadDocument(doc.document_id, doc.original_filename || doc.filename, doc.has_original_file)}
              className="px-4 py-2 text-sm bg-theme-primary text-white rounded-lg hover:bg-theme-primary-dark flex items-center gap-1"
            >
              <ArrowDownTrayIcon className="w-4 h-4" />
              Download
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

const PAGE_SIZE = 20;

export default function KnowledgeBase() {
  const [activeTab, setActiveTab] = useState('private');
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [status, setStatus] = useState(null);
  const [previewDoc, setPreviewDoc] = useState(null);
  const [toast, setToast] = useState(null);
  const [page, setPage] = useState(1);

  const showToast = (message, type = 'error') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 4000);
  };

  const fetchIdRef = useRef(0);

  // Load documents
  const loadDocuments = useCallback(async () => {
    const currentFetchId = ++fetchIdRef.current;
    setLoading(true);
    setError(null);
    try {
      if (activeTab === 'global') {
        // Fetch from HT-ITC-Lite RAG (global KB)
        const docsResponse = await globalKnowledgeApi.listDocuments({ limit: 100 });
        if (currentFetchId !== fetchIdRef.current) return; // stale fetch, discard
        if (docsResponse.data?.success) {
          setDocuments(docsResponse.data.data || []);
        } else {
          // API returned but with error — classify for user-friendly display
          const status = docsResponse.status;
          const errorMsg = extractErrorMessage(docsResponse, 'Failed to load global documents');
          if (status === 404 || status === 502) {
            setError('global_kb_unavailable');
          } else if (status === 503 || status === 504) {
            setError('global_kb_starting');
          } else {
            setError(errorMsg);
          }
          setDocuments([]);
        }
        // No status for global KB
        setStatus(null);
      } else {
        // Fetch from local FAISS (private KB)
        const [docsResponse, statusResponse] = await Promise.all([
          knowledgeApi.listDocuments({ visibility: 'private' }),
          knowledgeApi.getStatus(),
        ]);

        if (currentFetchId !== fetchIdRef.current) return; // stale fetch, discard
        if (docsResponse.data?.success) {
          setDocuments(docsResponse.data.data || []);
        } else {
          setDocuments([]);
        }
        if (statusResponse.data?.success) {
          setStatus(statusResponse.data.data);
        }
      }
    } catch (err) {
      if (currentFetchId !== fetchIdRef.current) return; // stale fetch, discard
      console.error('Failed to load documents:', err);
      // Classify network-level errors for appropriate UX
      if (err.response?.status === 404 || err.response?.status === 502) {
        setError('global_kb_unavailable');
      } else if (err.response?.status === 503 || err.response?.status === 504) {
        setError('global_kb_starting');
      } else {
        setError(extractErrorMessage(err, 'Failed to load documents'));
      }
      setDocuments([]);
    } finally {
      if (currentFetchId === fetchIdRef.current) setLoading(false);
    }
  }, [activeTab]);

  useEffect(() => {
    loadDocuments();
    setPage(1);
  }, [loadDocuments]);

  // Poll for pending documents — refresh every 10s while any docs are pending
  useEffect(() => {
    const hasPending = documents.some(d => d.status === 'pending');
    if (!hasPending || activeTab !== 'private') return;
    const timer = setInterval(() => loadDocuments(), 10000);
    return () => clearInterval(timer);
  }, [documents, activeTab, loadDocuments]);

  // Handle upload
  const handleUpload = async (formData) => {
    try {
      await knowledgeApi.uploadDocument(formData);
      await loadDocuments();
    } catch (error) {
      console.error('Upload failed:', error);
      showToast('Upload failed. Please try again.');
    }
  };

  // Handle delete
  const handleDelete = async (documentId) => {
    try {
      await knowledgeApi.deleteDocument(documentId);
      setDocuments((prev) => prev.filter((d) => d.document_id !== documentId));
    } catch (error) {
      console.error('Delete failed:', error);
      showToast('Delete failed. Please try again.');
    }
  };

  // Handle download
  const handleDownload = (doc) => {
    if (activeTab === 'global') {
      // Use proxy URLs to avoid CORS - pass has_original_file flag
      globalKnowledgeApi.downloadDocument(
        doc.document_id,
        doc.original_filename || doc.filename,
        doc.has_original_file
      );
      return;
    }

    // Private documents: use authenticated download
    const baseUrl = API_ABSOLUTE_URL;
    const token = localStorage.getItem('access_token');
    const tenantId = localStorage.getItem('tenant_id');
    const url = `${baseUrl}/api/v1/knowledge/documents/${doc.document_id}/download`;

    fetch(url, {
      headers: {
        'Authorization': `Bearer ${token}`,
        'X-Client-ID': tenantId,
      },
    })
      .then((res) => res.blob())
      .then((blob) => {
        const downloadUrl = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = downloadUrl;
        a.download = doc.filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(downloadUrl);
      })
      .catch((err) => {
        console.error('Download failed:', err);
        showToast('Download failed. Please try again.');
      });
  };

  // Filter documents by search (hide system documents with UUID-prefixed filenames)
  const UUID_PREFIX_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i;

  const allFilteredDocuments = documents.filter((doc) => {
    // Hide system documents (UUID-prefixed filenames)
    if (doc.is_system || UUID_PREFIX_PATTERN.test(doc.filename)) return false;
    // Apply search filter
    return (
      doc.filename?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      doc.category?.toLowerCase().includes(searchQuery.toLowerCase())
    );
  });

  const totalPages = Math.max(1, Math.ceil(allFilteredDocuments.length / PAGE_SIZE));
  const filteredDocuments = allFilteredDocuments.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-theme">Knowledge Base</h1>
          <p className="text-theme-muted mt-1">
            Manage documents for AI-powered search and helpdesk
          </p>
        </div>

        {/* Status summary - show counts based on current tab/documents */}
        <div className="flex items-center gap-4 text-sm">
          <div className="text-theme-muted">
            <span className="font-medium text-theme">{documents.length}</span> {activeTab === 'global' ? 'global' : 'private'} documents
          </div>
          {activeTab === 'private' && status && (
            <>
              <div className="text-theme-muted">
                <span className="font-medium text-green-600">
                  {documents.filter(d => d.status === 'indexed').length}
                </span> indexed
              </div>
              {documents.filter(d => d.status === 'pending').length > 0 && (
                <div className="text-theme-muted">
                  <span className="font-medium text-yellow-600">
                    {documents.filter(d => d.status === 'pending').length}
                  </span> pending
                </div>
              )}
            </>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-theme">
        <div className="flex gap-4">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-3 border-b-2 transition-colors ${
                activeTab === tab.id
                  ? 'border-theme-primary text-theme-primary font-medium'
                  : 'border-transparent text-theme-muted hover:text-theme'
              }`}
            >
              <tab.icon className="w-5 h-5" />
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Main content */}
        <div className="lg:col-span-3 space-y-4">
          {/* Search */}
          <div className="relative">
            <MagnifyingGlassIcon className="w-5 h-5 absolute left-3 top-1/2 -translate-y-1/2 text-theme-muted" />
            <input
              type="text"
              placeholder="Search documents..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 bg-theme-surface border border-theme rounded-lg text-theme placeholder:text-theme-muted focus:outline-none focus:ring-2 focus:ring-theme-primary/50"
            />
          </div>

          {/* Upload section (private tab only) */}
          {activeTab === 'private' && (
            <UploadSection onUpload={handleUpload} />
          )}

          {/* Documents list */}
          {loading ? (
            <div className="space-y-3">
              {[1, 2, 3].map((i) => (
                <div key={i} className="h-20 bg-theme-surface-elevated rounded-lg animate-pulse" />
              ))}
            </div>
          ) : error ? (
            error === 'global_kb_unavailable' ? (
              <div className="text-center py-12 bg-amber-50 rounded-lg border border-amber-200">
                <GlobeAltIcon className="w-12 h-12 text-amber-400 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-amber-700">Global Knowledge Base Unavailable</h3>
                <p className="text-amber-600 mt-1 text-sm max-w-md mx-auto">
                  The HT-ITC-Lite shared knowledge base is currently being set up.
                  Your private documents are still available in the "My Documents" tab.
                </p>
                <button
                  onClick={() => setActiveTab('private')}
                  className="mt-4 px-4 py-2 bg-amber-100 text-amber-700 rounded-lg hover:bg-amber-200 transition-colors"
                >
                  View My Documents
                </button>
              </div>
            ) : error === 'global_kb_starting' ? (
              <div className="text-center py-12 bg-blue-50 rounded-lg border border-blue-200">
                <ArrowPathIcon className="w-12 h-12 text-blue-400 mx-auto mb-4 animate-spin" />
                <h3 className="text-lg font-medium text-blue-700">Service Starting Up</h3>
                <p className="text-blue-600 mt-1 text-sm max-w-md mx-auto">
                  The Global Knowledge Base service is starting up. This may take a moment.
                </p>
                <button
                  onClick={loadDocuments}
                  className="mt-4 px-4 py-2 bg-blue-100 text-blue-700 rounded-lg hover:bg-blue-200 transition-colors"
                >
                  Try Again
                </button>
              </div>
            ) : (
              <div className="text-center py-12 bg-red-50 rounded-lg border border-red-200">
                <ExclamationCircleIcon className="w-12 h-12 text-red-400 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-red-700">Failed to load documents</h3>
                <p className="text-red-600 mt-1 text-sm max-w-md mx-auto">{error}</p>
                <button
                  onClick={loadDocuments}
                  className="mt-4 px-4 py-2 bg-red-100 text-red-700 rounded-lg hover:bg-red-200 transition-colors"
                >
                  Try Again
                </button>
              </div>
            )
          ) : filteredDocuments.length > 0 ? (
            <div className="space-y-3">
              {filteredDocuments.map((doc) => (
                <DocumentRow
                  key={doc.document_id}
                  doc={doc}
                  onDelete={handleDelete}
                  onDownload={handleDownload}
                  onView={setPreviewDoc}
                  canDelete={activeTab === 'private'}
                  canView={activeTab === 'global'}
                />
              ))}
              {/* Pagination */}
              {totalPages > 1 && (
                <div className="flex items-center justify-between pt-4">
                  <span className="text-sm text-theme-muted">
                    Showing {(page - 1) * PAGE_SIZE + 1}–{Math.min(page * PAGE_SIZE, allFilteredDocuments.length)} of {allFilteredDocuments.length}
                  </span>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => setPage(p => Math.max(1, p - 1))}
                      disabled={page === 1}
                      className="px-3 py-1 text-sm border border-theme rounded-lg hover:bg-theme-surface-elevated disabled:opacity-30 disabled:cursor-not-allowed"
                    >
                      Previous
                    </button>
                    <span className="text-sm text-theme-muted tabular-nums">
                      {page} / {totalPages}
                    </span>
                    <button
                      onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                      disabled={page === totalPages}
                      className="px-3 py-1 text-sm border border-theme rounded-lg hover:bg-theme-surface-elevated disabled:opacity-30 disabled:cursor-not-allowed"
                    >
                      Next
                    </button>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="text-center py-12">
              <FolderOpenIcon className="w-12 h-12 text-theme-muted mx-auto mb-4" />
              <h3 className="text-lg font-medium text-theme">No documents found</h3>
              <p className="text-theme-muted mt-1">
                {activeTab === 'private'
                  ? 'Upload documents to build your private knowledge base'
                  : 'No global documents found. The AI helpdesk may still answer travel questions using its search index.'}
              </p>
            </div>
          )}
        </div>

        {/* Sidebar */}
        <div className="space-y-4">
          {/* Info card */}
          <div className="card">
            <div className="flex items-start gap-3">
              <div className="p-2 bg-theme-primary/10 rounded-lg">
                <BookOpenIcon className="w-5 h-5 text-theme-primary" />
              </div>
              <div>
                <h3 className="font-medium text-theme">
                  {activeTab === 'private' ? 'My Documents' : 'Global Documents'}
                </h3>
                <p className="text-sm text-theme-muted mt-1">
                  {activeTab === 'private'
                    ? 'Private documents only you can access. Used by the AI helpdesk to answer your questions.'
                    : 'Shared documents from HT-ITC-Lite. Read-only access to common resources.'}
                </p>
              </div>
            </div>
          </div>

          {/* Quick stats */}
          <div className="card">
            <h4 className="font-medium text-theme mb-3">Quick Stats</h4>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-theme-muted">Documents</span>
                <span className="font-medium text-theme">{allFilteredDocuments.length}</span>
              </div>
              {activeTab === 'private' && (
                <div className="flex justify-between">
                  <span className="text-theme-muted">Total Chunks</span>
                  <span className="font-medium text-theme">
                    {documents.reduce((sum, doc) => sum + (doc.chunk_count || 0), 0)}
                  </span>
                </div>
              )}
              {activeTab === 'private' && status?.last_updated && (
                <div className="flex justify-between">
                  <span className="text-theme-muted">Last Updated</span>
                  <span className="font-medium text-theme">
                    {new Date(status.last_updated).toLocaleDateString()}
                  </span>
                </div>
              )}
            </div>
          </div>

          {/* Supported formats */}
          <div className="card">
            <h4 className="font-medium text-theme mb-3">Supported Formats</h4>
            <div className="flex flex-wrap gap-2">
              {['PDF', 'DOCX', 'DOC', 'TXT', 'MD'].map((format) => (
                <span
                  key={format}
                  className="px-2 py-1 bg-theme-surface-elevated rounded text-xs font-medium text-theme-muted"
                >
                  .{format.toLowerCase()}
                </span>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Document Preview Modal */}
      {previewDoc && (
        <DocumentPreviewModal
          doc={previewDoc}
          onClose={() => setPreviewDoc(null)}
        />
      )}

      {/* Toast Notification */}
      {toast && (
        <div className={`fixed bottom-4 right-4 flex items-center gap-2 px-4 py-3 rounded-lg shadow-lg z-50 max-w-md ${
          toast.type === 'success' ? 'bg-green-600 text-white' :
          toast.type === 'warning' ? 'bg-yellow-500 text-white' :
          'bg-red-600 text-white'
        }`}>
          <span>{toast.message}</span>
          <button onClick={() => setToast(null)} className="ml-2 hover:opacity-80">
            <XMarkIcon className="w-4 h-4" />
          </button>
        </div>
      )}
    </div>
  );
}
