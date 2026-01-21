import { useState, useEffect } from 'react';
import {
  DocumentTextIcon,
  PlusIcon,
  PencilIcon,
  TrashIcon,
  ArrowPathIcon,
  MagnifyingGlassIcon,
} from '@heroicons/react/24/outline';
import { knowledgeApi } from '../services/api';

export default function KnowledgeManager() {
  const [documents, setDocuments] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [showAddModal, setShowAddModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [editingDoc, setEditingDoc] = useState(null);
  const [formData, setFormData] = useState({
    title: '',
    content: '',
    category: 'general',
    visibility: 'public',
  });
  const [actionLoading, setActionLoading] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const [docsRes, statsRes] = await Promise.all([
        knowledgeApi.listDocuments(),
        knowledgeApi.getStats(),
      ]);
      setDocuments(docsRes.data?.data || []);
      setStats(statsRes.data?.data || null);
    } catch (error) {
      console.error('Failed to load knowledge data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async () => {
    if (!formData.title.trim() || !formData.content.trim()) {
      alert('Title and content are required');
      return;
    }
    try {
      setActionLoading(true);
      await knowledgeApi.createDocument(formData);
      setShowAddModal(false);
      setFormData({ title: '', content: '', category: 'general', visibility: 'public' });
      loadData();
    } catch (error) {
      console.error('Failed to create document:', error);
      alert('Failed to create document');
    } finally {
      setActionLoading(false);
    }
  };

  const handleUpdate = async () => {
    if (!editingDoc) return;
    try {
      setActionLoading(true);
      await knowledgeApi.updateDocument(editingDoc.id, formData);
      setShowEditModal(false);
      setEditingDoc(null);
      setFormData({ title: '', content: '', category: 'general', visibility: 'public' });
      loadData();
    } catch (error) {
      console.error('Failed to update document:', error);
      alert('Failed to update document');
    } finally {
      setActionLoading(false);
    }
  };

  const handleDelete = async (docId) => {
    if (!confirm('Are you sure you want to delete this document?')) return;
    try {
      await knowledgeApi.deleteDocument(docId);
      loadData();
    } catch (error) {
      console.error('Failed to delete document:', error);
      alert('Failed to delete document');
    }
  };

  const handleRebuildIndex = async () => {
    if (!confirm('Rebuild the FAISS index? This may take a while.')) return;
    try {
      setActionLoading(true);
      await knowledgeApi.rebuildIndex();
      alert('Index rebuilt successfully');
      loadData();
    } catch (error) {
      console.error('Failed to rebuild index:', error);
      alert('Failed to rebuild index');
    } finally {
      setActionLoading(false);
    }
  };

  const openEditModal = async (doc) => {
    try {
      const res = await knowledgeApi.getDocument(doc.id);
      const fullDoc = res.data?.data || doc;
      setEditingDoc(fullDoc);
      setFormData({
        title: fullDoc.title,
        content: fullDoc.content || '',
        category: fullDoc.category,
        visibility: fullDoc.visibility,
      });
      setShowEditModal(true);
    } catch (error) {
      console.error('Failed to load document:', error);
      alert('Failed to load document');
    }
  };

  const filteredDocs = documents.filter(doc => {
    const matchesSearch = !search ||
      doc.title?.toLowerCase().includes(search.toLowerCase());
    const matchesCategory = !categoryFilter || doc.category === categoryFilter;
    return matchesSearch && matchesCategory;
  });

  const categories = [...new Set(documents.map(d => d.category))];

  const formatBytes = (bytes) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Knowledge Base</h1>
          <p className="text-gray-500 mt-1">Manage RAG documents and FAISS index</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleRebuildIndex}
            disabled={actionLoading}
            className="btn-secondary flex items-center gap-2"
          >
            <ArrowPathIcon className="w-5 h-5" />
            Rebuild Index
          </button>
          <button
            onClick={() => setShowAddModal(true)}
            className="btn-primary flex items-center gap-2"
          >
            <PlusIcon className="w-5 h-5" />
            Add Document
          </button>
        </div>
      </div>

      {/* FAISS Helpdesk Index Stats */}
      {stats?.faiss_index && (
        <div className="card bg-gradient-to-r from-purple-50 to-indigo-50 border-purple-200">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-lg font-semibold text-purple-900">FAISS Helpdesk Index</h3>
              <p className="text-sm text-purple-600">Pre-built vector index for helpdesk queries</p>
            </div>
            <div className={`px-3 py-1 rounded-full text-sm font-medium ${
              stats.faiss_index.initialized
                ? 'bg-green-100 text-green-700'
                : 'bg-yellow-100 text-yellow-700'
            }`}>
              {stats.faiss_index.initialized ? 'Active' : 'Initializing'}
            </div>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            <div>
              <p className="text-sm text-purple-600">Vectors</p>
              <p className="text-2xl font-bold text-purple-900">
                {stats.faiss_index.vector_count?.toLocaleString() || 0}
              </p>
            </div>
            <div>
              <p className="text-sm text-purple-600">Documents</p>
              <p className="text-2xl font-bold text-purple-900">
                {stats.faiss_index.document_count?.toLocaleString() || 0}
              </p>
            </div>
            <div>
              <p className="text-sm text-purple-600">Source</p>
              <p className="text-lg font-medium text-purple-900">
                {stats.faiss_index.bucket || 'N/A'}
              </p>
            </div>
          </div>
          {stats.faiss_index.error && (
            <p className="mt-2 text-sm text-red-600">Error: {stats.faiss_index.error}</p>
          )}
        </div>
      )}

      {/* Manageable Documents Stats */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="card">
            <p className="text-sm text-gray-500">Managed Documents</p>
            <p className="text-2xl font-bold text-gray-900">{stats.total_documents}</p>
          </div>
          <div className="card">
            <p className="text-sm text-gray-500">Global / Tenant</p>
            <p className="text-2xl font-bold text-gray-900">
              {stats.global_documents} / {stats.tenant_documents}
            </p>
          </div>
          <div className="card">
            <p className="text-sm text-gray-500">Total Chunks</p>
            <p className="text-2xl font-bold text-gray-900">{stats.total_chunks}</p>
          </div>
          <div className="card">
            <p className="text-sm text-gray-500">Storage Size</p>
            <p className="text-2xl font-bold text-gray-900">{formatBytes(stats.index_size_bytes)}</p>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="card">
        <div className="flex flex-col md:flex-row gap-4">
          <div className="flex-1 relative">
            <MagnifyingGlassIcon className="w-5 h-5 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              placeholder="Search documents..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="input pl-10"
            />
          </div>
          <select
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
            className="input w-full md:w-48"
          >
            <option value="">All Categories</option>
            {categories.map(cat => (
              <option key={cat} value={cat}>{cat}</option>
            ))}
          </select>
          <button onClick={loadData} className="btn-secondary">
            <ArrowPathIcon className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* Documents List */}
      <div className="card">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">
          Documents ({filteredDocs.length})
        </h3>

        {loading ? (
          <div className="space-y-3">
            {[1, 2, 3].map(i => (
              <div key={i} className="h-16 bg-gray-100 rounded animate-pulse" />
            ))}
          </div>
        ) : filteredDocs.length === 0 ? (
          <p className="text-gray-500 text-center py-8">No documents found</p>
        ) : (
          <div className="space-y-3">
            {filteredDocs.map(doc => (
              <div
                key={doc.id}
                className="flex items-center justify-between p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
              >
                <div className="flex items-center gap-4">
                  <div className="p-2 bg-blue-100 rounded-lg">
                    <DocumentTextIcon className="w-5 h-5 text-blue-600" />
                  </div>
                  <div>
                    <p className="font-medium text-gray-900">{doc.title}</p>
                    <div className="flex items-center gap-2 text-sm text-gray-500">
                      <span className="badge badge-info">{doc.category}</span>
                      <span>{doc.visibility}</span>
                      {doc.tenant_id && <span className="text-xs">Tenant: {doc.tenant_id}</span>}
                      <span className={doc.indexed ? 'text-green-600' : 'text-yellow-600'}>
                        {doc.indexed ? 'Indexed' : 'Pending'}
                      </span>
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => openEditModal(doc)}
                    className="p-2 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                  >
                    <PencilIcon className="w-5 h-5" />
                  </button>
                  <button
                    onClick={() => handleDelete(doc.id)}
                    className="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                  >
                    <TrashIcon className="w-5 h-5" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Add Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl p-6 w-full max-w-2xl max-h-[90vh] overflow-y-auto">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Add Document</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Title</label>
                <input
                  type="text"
                  value={formData.title}
                  onChange={(e) => setFormData({...formData, title: e.target.value})}
                  className="input"
                  placeholder="Document title"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Category</label>
                  <select
                    value={formData.category}
                    onChange={(e) => setFormData({...formData, category: e.target.value})}
                    className="input"
                  >
                    <option value="general">General</option>
                    <option value="destinations">Destinations</option>
                    <option value="policies">Policies</option>
                    <option value="faq">FAQ</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Visibility</label>
                  <select
                    value={formData.visibility}
                    onChange={(e) => setFormData({...formData, visibility: e.target.value})}
                    className="input"
                  >
                    <option value="public">Public (All Tenants)</option>
                    <option value="private">Private</option>
                  </select>
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Content</label>
                <textarea
                  value={formData.content}
                  onChange={(e) => setFormData({...formData, content: e.target.value})}
                  className="input h-64 resize-none font-mono text-sm"
                  placeholder="Document content..."
                />
              </div>
            </div>
            <div className="flex justify-end gap-3 mt-6">
              <button onClick={() => setShowAddModal(false)} className="btn-secondary">
                Cancel
              </button>
              <button
                onClick={handleCreate}
                disabled={actionLoading}
                className="btn-primary"
              >
                {actionLoading ? 'Creating...' : 'Create Document'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Edit Modal */}
      {showEditModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl p-6 w-full max-w-2xl max-h-[90vh] overflow-y-auto">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Edit Document</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Title</label>
                <input
                  type="text"
                  value={formData.title}
                  onChange={(e) => setFormData({...formData, title: e.target.value})}
                  className="input"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Category</label>
                  <select
                    value={formData.category}
                    onChange={(e) => setFormData({...formData, category: e.target.value})}
                    className="input"
                  >
                    <option value="general">General</option>
                    <option value="destinations">Destinations</option>
                    <option value="policies">Policies</option>
                    <option value="faq">FAQ</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Visibility</label>
                  <select
                    value={formData.visibility}
                    onChange={(e) => setFormData({...formData, visibility: e.target.value})}
                    className="input"
                  >
                    <option value="public">Public (All Tenants)</option>
                    <option value="private">Private</option>
                  </select>
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Content</label>
                <textarea
                  value={formData.content}
                  onChange={(e) => setFormData({...formData, content: e.target.value})}
                  className="input h-64 resize-none font-mono text-sm"
                />
              </div>
            </div>
            <div className="flex justify-end gap-3 mt-6">
              <button onClick={() => setShowEditModal(false)} className="btn-secondary">
                Cancel
              </button>
              <button
                onClick={handleUpdate}
                disabled={actionLoading}
                className="btn-primary"
              >
                {actionLoading ? 'Saving...' : 'Save Changes'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
