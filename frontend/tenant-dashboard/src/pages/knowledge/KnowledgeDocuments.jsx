import { useState, useEffect, useRef } from 'react';
import { knowledgeApi } from '../../services/api';
import {
  DocumentTextIcon,
  ArrowUpTrayIcon,
  TrashIcon,
  ArrowPathIcon,
  FolderIcon,
  XMarkIcon,
  CheckCircleIcon,
  ExclamationCircleIcon,
  ClockIcon,
  LockClosedIcon,
  GlobeAltIcon,
  MagnifyingGlassIcon,
  SparklesIcon,
  DocumentArrowUpIcon,
} from '@heroicons/react/24/outline';

const statusIcons = {
  indexed: { icon: CheckCircleIcon, color: 'text-green-600', bg: 'bg-green-100' },
  pending: { icon: ClockIcon, color: 'text-yellow-600', bg: 'bg-yellow-100' },
  error: { icon: ExclamationCircleIcon, color: 'text-red-600', bg: 'bg-red-100' },
};

const CATEGORIES = [
  { id: 'hotel-info', label: 'Hotel Information' },
  { id: 'destination-guides', label: 'Destination Guides' },
  { id: 'visa-requirements', label: 'Visa Requirements' },
  { id: 'company-policies', label: 'Company Policies' },
  { id: 'faqs', label: 'FAQs' },
  { id: 'general', label: 'General' },
];

const categoryColors = {
  'hotel-info': 'bg-blue-100 text-blue-700',
  'destination-guides': 'bg-green-100 text-green-700',
  'visa-requirements': 'bg-purple-100 text-purple-700',
  'company-policies': 'bg-orange-100 text-orange-700',
  'faqs': 'bg-teal-100 text-teal-700',
  'general': 'bg-gray-100 text-gray-700',
};

// Confirmation Modal Component
function ConfirmModal({ isOpen, title, message, onConfirm, onCancel, danger }) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl max-w-md w-full mx-4 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-2">{title}</h3>
        <p className="text-gray-600 mb-6">{message}</p>
        <div className="flex gap-3">
          <button onClick={onCancel} className="btn-secondary flex-1">Cancel</button>
          <button
            onClick={onConfirm}
            className={`flex-1 px-4 py-2 rounded-lg font-medium transition-colors ${
              danger ? 'bg-red-600 text-white hover:bg-red-700' : 'bg-primary-600 text-white hover:bg-primary-700'
            }`}
          >
            Confirm
          </button>
        </div>
      </div>
    </div>
  );
}

// Upload Modal Component
function UploadModal({ isOpen, onClose, onUpload }) {
  const [file, setFile] = useState(null);
  const [category, setCategory] = useState('general');
  const [tags, setTags] = useState('');
  const [visibility, setVisibility] = useState('public');
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef(null);

  const handleFileSelect = (e) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      setFile(selectedFile);
    }
  };

  const handleSubmit = async () => {
    if (!file) return;
    
    setUploading(true);
    try {
      await onUpload(file, category, tags, visibility);
      onClose();
      setFile(null);
      setCategory('general');
      setTags('');
      setVisibility('public');
    } catch (error) {
      console.error('Upload failed:', error);
    } finally {
      setUploading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl w-full max-w-lg mx-4 overflow-hidden shadow-xl">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900">Upload Document</h3>
          <button onClick={onClose} className="p-1 hover:bg-gray-100 rounded-lg">
            <XMarkIcon className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        {/* Content */}
        <div className="px-6 py-4 space-y-4">
          {/* File Selection */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Select File
            </label>
            {file ? (
              <div className="flex items-center gap-3 p-3 bg-purple-50 rounded-lg border border-purple-200">
                <DocumentTextIcon className="w-8 h-8 text-purple-600" />
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-gray-900 truncate">{file.name}</p>
                  <p className="text-sm text-gray-500">
                    {(file.size / 1024).toFixed(1)} KB
                  </p>
                </div>
                <button
                  onClick={() => setFile(null)}
                  className="p-1 hover:bg-purple-100 rounded"
                >
                  <XMarkIcon className="w-5 h-5 text-purple-600" />
                </button>
              </div>
            ) : (
              <button
                onClick={() => fileInputRef.current?.click()}
                className="w-full p-6 border-2 border-dashed border-gray-300 rounded-lg hover:border-purple-400 hover:bg-purple-50 transition-colors"
              >
                <ArrowUpTrayIcon className="w-8 h-8 text-gray-400 mx-auto mb-2" />
                <p className="text-sm text-gray-600">Click to select a file</p>
                <p className="text-xs text-gray-400 mt-1">PDF, DOCX, TXT, Markdown</p>
              </button>
            )}
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.docx,.txt,.md"
              onChange={handleFileSelect}
              className="hidden"
            />
          </div>

          {/* Category */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Category
            </label>
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              className="input"
            >
              {CATEGORIES.map((cat) => (
                <option key={cat.id} value={cat.id}>{cat.label}</option>
              ))}
            </select>
          </div>

          {/* Tags */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Tags (optional)
            </label>
            <input
              type="text"
              value={tags}
              onChange={(e) => setTags(e.target.value)}
              placeholder="e.g., zanzibar, beach, honeymoon"
              className="input"
            />
            <p className="text-xs text-gray-500 mt-1">Comma-separated tags for better search</p>
          </div>

          {/* Visibility */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Visibility
            </label>
            <div className="grid grid-cols-2 gap-3">
              <button
                type="button"
                onClick={() => setVisibility('public')}
                className={`flex items-center gap-3 p-3 rounded-lg border-2 transition-colors ${
                  visibility === 'public'
                    ? 'border-purple-500 bg-purple-50'
                    : 'border-gray-200 hover:border-gray-300'
                }`}
              >
                <GlobeAltIcon className={`w-5 h-5 ${visibility === 'public' ? 'text-purple-600' : 'text-gray-400'}`} />
                <div className="text-left">
                  <p className={`font-medium ${visibility === 'public' ? 'text-purple-900' : 'text-gray-700'}`}>
                    Public
                  </p>
                  <p className="text-xs text-gray-500">Available to customers</p>
                </div>
              </button>
              <button
                type="button"
                onClick={() => setVisibility('private')}
                className={`flex items-center gap-3 p-3 rounded-lg border-2 transition-colors ${
                  visibility === 'private'
                    ? 'border-purple-500 bg-purple-50'
                    : 'border-gray-200 hover:border-gray-300'
                }`}
              >
                <LockClosedIcon className={`w-5 h-5 ${visibility === 'private' ? 'text-purple-600' : 'text-gray-400'}`} />
                <div className="text-left">
                  <p className={`font-medium ${visibility === 'private' ? 'text-purple-900' : 'text-gray-700'}`}>
                    Private
                  </p>
                  <p className="text-xs text-gray-500">Staff only (Helpdesk)</p>
                </div>
              </button>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-gray-200 bg-gray-50">
          <button onClick={onClose} className="btn-secondary">
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={!file || uploading}
            className="btn-primary flex items-center gap-2"
          >
            {uploading ? (
              <>
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                Uploading...
              </>
            ) : (
              <>
                <ArrowUpTrayIcon className="w-4 h-4" />
                Upload
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

// Toast notification component
function Toast({ message, type, onClose }) {
  useEffect(() => {
    const timer = setTimeout(onClose, 3000);
    return () => clearTimeout(timer);
  }, [onClose]);

  return (
    <div className={`fixed bottom-4 right-4 flex items-center gap-3 px-4 py-3 rounded-lg shadow-lg z-50 ${
      type === 'success' ? 'bg-green-600 text-white' : 'bg-red-600 text-white'
    }`}>
      {type === 'success' ? (
        <CheckCircleIcon className="w-5 h-5" />
      ) : (
        <ExclamationCircleIcon className="w-5 h-5" />
      )}
      <span>{message}</span>
      <button onClick={onClose} className="p-1 hover:bg-white/20 rounded">
        <XMarkIcon className="w-4 h-4" />
      </button>
    </div>
  );
}

export default function KnowledgeDocuments() {
  // Tab state
  const [activeTab, setActiveTab] = useState('documents');

  // Documents state
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [status, setStatus] = useState(null);
  const [categoryFilter, setCategoryFilter] = useState('');
  const [visibilityFilter, setVisibilityFilter] = useState('');
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [toast, setToast] = useState(null);
  const [confirmModal, setConfirmModal] = useState({ isOpen: false, title: '', message: '', onConfirm: null, danger: false });

  // Search state
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [searchLoading, setSearchLoading] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);
  const [suggestions, setSuggestions] = useState([]);
  const [loadingSuggestions, setLoadingSuggestions] = useState(false);
  const [searchFilters, setSearchFilters] = useState({
    category: '',
    visibility: '',
    topK: 10,
  });

  useEffect(() => {
    loadData();
  }, [categoryFilter, visibilityFilter]);

  useEffect(() => {
    if (activeTab === 'search' && suggestions.length === 0) {
      loadSuggestions();
    }
  }, [activeTab]);

  const loadData = async () => {
    try {
      setLoading(true);
      const [docsRes, statusRes] = await Promise.all([
        knowledgeApi.listDocuments({ 
          category: categoryFilter || undefined,
          visibility: visibilityFilter || undefined,
        }),
        knowledgeApi.getStatus(),
      ]);
      setDocuments(docsRes.data?.data || []);
      setStatus(statusRes.data?.data);
    } catch (error) {
      console.error('Failed to load knowledge base:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleUpload = async (file, category, tags, visibility) => {
    try {
      await knowledgeApi.uploadDocument(file, category, tags, visibility);
      await loadData();
      setToast({ message: 'Document uploaded and indexed successfully!', type: 'success' });
    } catch (error) {
      setToast({ message: 'Failed to upload document', type: 'error' });
      throw error;
    }
  };

  const handleDelete = (documentId) => {
    setConfirmModal({
      isOpen: true,
      title: 'Delete Document',
      message: 'Are you sure you want to delete this document? This cannot be undone.',
      danger: true,
      onConfirm: async () => {
        setConfirmModal({ ...confirmModal, isOpen: false });
        try {
          await knowledgeApi.deleteDocument(documentId);
          await loadData();
          setToast({ message: 'Document deleted', type: 'success' });
        } catch (error) {
          setToast({ message: 'Failed to delete document', type: 'error' });
        }
      }
    });
  };

  const handleReindex = async (documentId) => {
    try {
      await knowledgeApi.reindexDocument(documentId);
      await loadData();
      setToast({ message: 'Document re-indexed successfully!', type: 'success' });
    } catch (error) {
      setToast({ message: 'Failed to re-index document', type: 'error' });
    }
  };

  const handleRebuildIndex = () => {
    setConfirmModal({
      isOpen: true,
      title: 'Rebuild Index',
      message: 'This will rebuild the entire knowledge base index. This may take a few minutes. Continue?',
      danger: false,
      onConfirm: async () => {
        setConfirmModal({ ...confirmModal, isOpen: false });
        try {
          await knowledgeApi.rebuildIndex();
          await loadData();
          setToast({ message: 'Index rebuilt successfully!', type: 'success' });
        } catch (error) {
          setToast({ message: 'Failed to rebuild index', type: 'error' });
        }
      }
    });
  };

  const formatFileSize = (bytes) => {
    if (!bytes) return '-';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  // Search functions
  const loadSuggestions = async () => {
    try {
      setLoadingSuggestions(true);
      const response = await knowledgeApi.listDocuments({ limit: 20 });
      const docs = response.data?.data || [];

      if (docs.length === 0) {
        setSuggestions([]);
        return;
      }

      const suggestionSet = new Set();
      docs.forEach((doc) => {
        if (doc.filename && doc.filename.length > 10 && doc.filename.length < 60) {
          suggestionSet.add(`What is ${doc.filename}?`);
        }
        if (doc.category) {
          const categoryQuestions = {
            'hotel-info': `Tell me about the hotels`,
            'destination-guides': `What should I know about visiting this destination?`,
            'visa-requirements': `What are the visa requirements?`,
            'company-policies': `What are the booking policies?`,
            'faqs': `Frequently asked questions`,
          };
          if (categoryQuestions[doc.category]) {
            suggestionSet.add(categoryQuestions[doc.category]);
          }
        }
      });
      setSuggestions(Array.from(suggestionSet).slice(0, 6));
    } catch (error) {
      console.error('Failed to load suggestions:', error);
      setSuggestions([]);
    } finally {
      setLoadingSuggestions(false);
    }
  };

  const handleSearch = async (e) => {
    e?.preventDefault();
    if (!searchQuery.trim()) return;

    setSearchLoading(true);
    setHasSearched(true);
    try {
      const response = await knowledgeApi.search(searchQuery, {
        top_k: searchFilters.topK,
        category: searchFilters.category || undefined,
        visibility: searchFilters.visibility || undefined,
      });
      setSearchResults(response.data?.data || []);
    } catch (error) {
      console.error('Search failed:', error);
      setSearchResults([]);
    } finally {
      setSearchLoading(false);
    }
  };

  const clearSearch = () => {
    setSearchQuery('');
    setSearchResults([]);
    setHasSearched(false);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Knowledge Base</h1>
          <p className="text-gray-500 mt-1">
            Manage documents that power your AI agents
          </p>
        </div>
        {activeTab === 'documents' && (
          <div className="flex items-center gap-3">
            <button onClick={handleRebuildIndex} className="btn-secondary flex items-center gap-2">
              <ArrowPathIcon className="w-5 h-5" />
              Rebuild Index
            </button>
            <button
              onClick={() => setShowUploadModal(true)}
              className="btn-primary flex items-center gap-2"
            >
              <ArrowUpTrayIcon className="w-5 h-5" />
              Upload Document
            </button>
          </div>
        )}
      </div>

      {/* Tab Navigation */}
      <div className="border-b border-gray-200">
        <nav className="flex gap-4">
          <button
            onClick={() => setActiveTab('documents')}
            className={`pb-3 px-1 border-b-2 font-medium text-sm transition-colors ${
              activeTab === 'documents'
                ? 'border-purple-600 text-purple-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            <span className="flex items-center gap-2">
              <DocumentTextIcon className="w-5 h-5" />
              Documents
            </span>
          </button>
          <button
            onClick={() => setActiveTab('search')}
            className={`pb-3 px-1 border-b-2 font-medium text-sm transition-colors ${
              activeTab === 'search'
                ? 'border-purple-600 text-purple-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            <span className="flex items-center gap-2">
              <MagnifyingGlassIcon className="w-5 h-5" />
              Search
            </span>
          </button>
        </nav>
      </div>

      {/* Documents Tab Content */}
      {activeTab === 'documents' && (
        <>
          {/* Status Cards */}
          {status && (
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
              <div className="card p-4">
                <p className="text-sm text-gray-500">Total Documents</p>
                <p className="text-2xl font-bold text-gray-900">{status.total_documents}</p>
              </div>
              <div className="card p-4">
                <p className="text-sm text-gray-500">Indexed</p>
                <p className="text-2xl font-bold text-green-600">{status.indexed_documents}</p>
              </div>
              <div className="card p-4">
                <p className="text-sm text-gray-500">Pending</p>
                <p className="text-2xl font-bold text-yellow-600">{status.pending_documents}</p>
              </div>
              <div className="card p-4">
                <p className="text-sm text-gray-500">Total Chunks</p>
                <p className="text-2xl font-bold text-gray-900">{status.total_chunks}</p>
              </div>
              <div className="card p-4">
                <p className="text-sm text-gray-500">Index Size</p>
                <p className="text-2xl font-bold text-gray-900">{formatFileSize(status.index_size_bytes)}</p>
              </div>
            </div>
          )}

      {/* Filters */}
      <div className="card">
        <div className="flex gap-4">
          <select
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
            className="input w-48"
          >
            <option value="">All Categories</option>
            {CATEGORIES.map((cat) => (
              <option key={cat.id} value={cat.id}>{cat.label}</option>
            ))}
          </select>
          <select
            value={visibilityFilter}
            onChange={(e) => setVisibilityFilter(e.target.value)}
            className="input w-40"
          >
            <option value="">All Visibility</option>
            <option value="public">Public</option>
            <option value="private">Private</option>
          </select>
          <button onClick={loadData} className="btn-secondary flex items-center gap-2">
            <ArrowPathIcon className="w-5 h-5" />
            Refresh
          </button>
        </div>
      </div>

      {/* Documents List */}
      <div className="card p-0 overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <div className="w-8 h-8 border-4 border-purple-600 border-t-transparent rounded-full animate-spin"></div>
          </div>
        ) : documents.length === 0 ? (
          <div className="text-center py-12">
            <FolderIcon className="w-12 h-12 text-gray-300 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900">No documents yet</h3>
            <p className="text-gray-500 mt-1">Upload documents to build your knowledge base</p>
            <button
              onClick={() => setShowUploadModal(true)}
              className="btn-primary inline-flex items-center gap-2 mt-4"
            >
              <ArrowUpTrayIcon className="w-5 h-5" />
              Upload Document
            </button>
          </div>
        ) : (
          <table className="w-full">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Document</th>
                <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Category</th>
                <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Visibility</th>
                <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Chunks</th>
                <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Size</th>
                <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {documents.map((doc) => {
                const StatusIcon = statusIcons[doc.status]?.icon || ClockIcon;
                const statusColor = statusIcons[doc.status]?.color || 'text-gray-600';
                const statusBg = statusIcons[doc.status]?.bg || 'bg-gray-100';
                const isPrivate = doc.visibility === 'private';
                
                return (
                  <tr key={doc.document_id} className="hover:bg-gray-50">
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center">
                          <DocumentTextIcon className="w-5 h-5 text-purple-600" />
                        </div>
                        <div>
                          <p className="font-medium text-gray-900">{doc.filename}</p>
                          <p className="text-xs text-gray-500">{doc.document_id}</p>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${categoryColors[doc.category] || categoryColors.general}`}>
                        {doc.category}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <div className={`inline-flex items-center gap-1.5 px-2 py-1 rounded-full ${
                        isPrivate ? 'bg-orange-100' : 'bg-blue-100'
                      }`}>
                        {isPrivate ? (
                          <LockClosedIcon className="w-3.5 h-3.5 text-orange-600" />
                        ) : (
                          <GlobeAltIcon className="w-3.5 h-3.5 text-blue-600" />
                        )}
                        <span className={`text-xs font-medium ${isPrivate ? 'text-orange-700' : 'text-blue-700'}`}>
                          {isPrivate ? 'Private' : 'Public'}
                        </span>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className={`inline-flex items-center gap-1.5 px-2 py-1 rounded-full ${statusBg}`}>
                        <StatusIcon className={`w-4 h-4 ${statusColor}`} />
                        <span className={`text-xs font-medium ${statusColor}`}>{doc.status}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-gray-600">{doc.chunk_count}</td>
                    <td className="px-6 py-4 text-gray-600">{formatFileSize(doc.file_size)}</td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => handleReindex(doc.document_id)}
                          className="p-2 text-gray-500 hover:text-purple-600 hover:bg-purple-50 rounded-lg"
                          title="Re-index"
                        >
                          <ArrowPathIcon className="w-5 h-5" />
                        </button>
                        <button
                          onClick={() => handleDelete(doc.document_id)}
                          className="p-2 text-gray-500 hover:text-red-600 hover:bg-red-50 rounded-lg"
                          title="Delete"
                        >
                          <TrashIcon className="w-5 h-5" />
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

          {/* Supported formats */}
          <p className="text-sm text-gray-500 text-center">
            Supported formats: PDF, DOCX, TXT, Markdown
          </p>
        </>
      )}

      {/* Search Tab Content */}
      {activeTab === 'search' && (
        <>
          {/* Search Box */}
          <div className="card">
            <form onSubmit={handleSearch} className="space-y-4">
              <div className="relative">
                <MagnifyingGlassIcon className="w-6 h-6 absolute left-4 top-1/2 -translate-y-1/2 text-gray-400" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && handleSearch(e)}
                  placeholder="Ask a question or search for information..."
                  className="w-full pl-14 pr-4 py-4 text-lg border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                />
              </div>

              {/* Filters */}
              <div className="flex flex-wrap gap-4 items-center">
                <select
                  value={searchFilters.category}
                  onChange={(e) => setSearchFilters(f => ({ ...f, category: e.target.value }))}
                  className="input w-44"
                >
                  <option value="">All Categories</option>
                  <option value="hotel-info">Hotel Info</option>
                  <option value="destination-guides">Destination Guides</option>
                  <option value="visa-requirements">Visa Requirements</option>
                  <option value="company-policies">Company Policies</option>
                  <option value="faqs">FAQs</option>
                  <option value="general">General</option>
                </select>

                <select
                  value={searchFilters.visibility}
                  onChange={(e) => setSearchFilters(f => ({ ...f, visibility: e.target.value }))}
                  className="input w-36"
                >
                  <option value="">All Docs</option>
                  <option value="public">Public</option>
                  <option value="private">Private</option>
                </select>

                <select
                  value={searchFilters.topK}
                  onChange={(e) => setSearchFilters(f => ({ ...f, topK: parseInt(e.target.value) }))}
                  className="input w-32"
                >
                  <option value="5">5 results</option>
                  <option value="10">10 results</option>
                  <option value="20">20 results</option>
                </select>

                <button
                  type="submit"
                  disabled={!searchQuery.trim() || searchLoading}
                  className="btn-primary flex items-center gap-2"
                >
                  {searchLoading ? (
                    <>
                      <ArrowPathIcon className="w-5 h-5 animate-spin" />
                      Searching...
                    </>
                  ) : (
                    <>
                      <MagnifyingGlassIcon className="w-5 h-5" />
                      Search
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>

          {/* Suggested Queries (when no search yet) */}
          {!hasSearched && (
            <div className="card">
              <h3 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
                <SparklesIcon className="w-5 h-5 text-purple-600" />
                Suggested Searches
              </h3>
              {loadingSuggestions ? (
                <div className="flex items-center justify-center py-8">
                  <div className="w-6 h-6 border-2 border-purple-600 border-t-transparent rounded-full animate-spin"></div>
                </div>
              ) : suggestions.length === 0 ? (
                <div className="text-center py-8">
                  <DocumentArrowUpIcon className="w-12 h-12 text-gray-300 mx-auto mb-3" />
                  <p className="text-gray-500 mb-3">No documents in your knowledge base yet</p>
                  <button
                    onClick={() => setActiveTab('documents')}
                    className="text-purple-600 hover:text-purple-700 font-medium"
                  >
                    Upload documents to get search suggestions
                  </button>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {suggestions.map((suggestion, idx) => (
                    <button
                      key={idx}
                      onClick={() => {
                        setSearchQuery(suggestion);
                        setTimeout(() => handleSearch(), 100);
                      }}
                      className="text-left px-4 py-3 bg-gray-50 rounded-lg hover:bg-purple-50 hover:text-purple-700 transition-colors"
                    >
                      {suggestion}
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Search Results */}
          {hasSearched && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="font-semibold text-gray-900">
                  {searchLoading ? 'Searching...' : `${searchResults.length} result${searchResults.length !== 1 ? 's' : ''} found`}
                </h3>
                {searchResults.length > 0 && (
                  <button onClick={clearSearch} className="text-sm text-purple-600 hover:text-purple-700">
                    Clear search
                  </button>
                )}
              </div>

              {searchLoading ? (
                <div className="flex items-center justify-center py-12">
                  <div className="w-8 h-8 border-4 border-purple-600 border-t-transparent rounded-full animate-spin"></div>
                </div>
              ) : searchResults.length === 0 ? (
                <div className="card text-center py-12">
                  <FolderIcon className="w-12 h-12 text-gray-300 mx-auto mb-4" />
                  <h3 className="text-lg font-medium text-gray-900">No results found</h3>
                  <p className="text-gray-500 mt-1">Try different keywords or broaden your search</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {searchResults.map((result, idx) => (
                    <div key={idx} className="card hover:shadow-md transition-shadow">
                      <div className="flex items-start justify-between mb-3">
                        <div className="flex items-center gap-3">
                          <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center">
                            <DocumentTextIcon className="w-5 h-5 text-purple-600" />
                          </div>
                          <div>
                            <p className="font-medium text-gray-900">{result.source || 'Unknown Source'}</p>
                            <div className="flex items-center gap-2 mt-1">
                              {result.category && (
                                <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded">
                                  {result.category}
                                </span>
                              )}
                              {result.visibility === 'private' ? (
                                <span className="text-xs bg-orange-100 text-orange-600 px-2 py-0.5 rounded flex items-center gap-1">
                                  <LockClosedIcon className="w-3 h-3" />
                                  Private
                                </span>
                              ) : (
                                <span className="text-xs bg-blue-100 text-blue-600 px-2 py-0.5 rounded flex items-center gap-1">
                                  <GlobeAltIcon className="w-3 h-3" />
                                  Public
                                </span>
                              )}
                            </div>
                          </div>
                        </div>
                        <div className="text-right">
                          <span className="text-sm font-medium text-purple-600">
                            {Math.round(result.score * 100)}% match
                          </span>
                        </div>
                      </div>
                      <p className="text-gray-700 whitespace-pre-wrap leading-relaxed">
                        {result.content}
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </>
      )}

      {/* Upload Modal */}
      <UploadModal
        isOpen={showUploadModal}
        onClose={() => setShowUploadModal(false)}
        onUpload={handleUpload}
      />

      {/* Confirmation Modal */}
      <ConfirmModal
        isOpen={confirmModal.isOpen}
        title={confirmModal.title}
        message={confirmModal.message}
        danger={confirmModal.danger}
        onConfirm={confirmModal.onConfirm}
        onCancel={() => setConfirmModal({ ...confirmModal, isOpen: false })}
      />

      {/* Toast Notification */}
      {toast && (
        <Toast
          message={toast.message}
          type={toast.type}
          onClose={() => setToast(null)}
        />
      )}
    </div>
  );
}
