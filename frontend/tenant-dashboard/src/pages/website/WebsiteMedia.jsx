import { useState, useEffect } from 'react';
import { websiteBuilderApi } from '../../services/api';
import ConfirmDialog from '../../components/ui/ConfirmDialog';
import {
  PhotoIcon,
  TrashIcon,
  ArrowUpTrayIcon,
  FolderIcon,
  XMarkIcon,
} from '@heroicons/react/24/outline';

const CATEGORIES = [
  { id: 'all', name: 'All Images' },
  { id: 'logos', name: 'Logos' },
  { id: 'heroes', name: 'Hero Images' },
  { id: 'backgrounds', name: 'Backgrounds' },
  { id: 'gallery', name: 'Gallery' },
];

function formatFileSize(bytes) {
  if (!bytes) return '';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function WebsiteMedia() {
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [images, setImages] = useState([]);
  const [category, setCategory] = useState('all');
  const [selectedImage, setSelectedImage] = useState(null);
  const [error, setError] = useState(null);
  const [deleteTarget, setDeleteTarget] = useState(null);

  useEffect(() => {
    loadImages();
  }, [category]);

  async function loadImages() {
    setLoading(true);
    try {
      const cat = category === 'all' ? null : category;
      const response = await websiteBuilderApi.listMedia(cat);
      setImages(response.data?.images || []);
    } catch (err) {
      console.error('Failed to load media:', err);
      setError('Failed to load media library');
    } finally {
      setLoading(false);
    }
  }

  async function handleUpload(e) {
    const files = e.target.files;
    if (!files?.length) return;

    setUploading(true);
    setError(null);

    try {
      for (const file of files) {
        const uploadCategory = category === 'all' ? 'gallery' : category;
        await websiteBuilderApi.uploadMedia(file, uploadCategory);
      }
      await loadImages();
    } catch (err) {
      console.error('Upload failed:', err);
      setError('Failed to upload image(s)');
    } finally {
      setUploading(false);
    }
  }

  function handleDelete(image) {
    setDeleteTarget(image);
  }

  async function confirmDelete() {
    if (!deleteTarget) return;
    try {
      await websiteBuilderApi.deleteMedia(deleteTarget.path);
      setImages(prev => prev.filter(img => img.path !== deleteTarget.path));
      if (selectedImage?.path === deleteTarget.path) {
        setSelectedImage(null);
      }
    } catch (err) {
      console.error('Delete failed:', err);
      setError('Failed to delete image');
    } finally {
      setDeleteTarget(null);
    }
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Media Library</h1>
          <p className="text-gray-500">Upload and manage images for your website</p>
        </div>
        <label className="btn-primary flex items-center gap-2 cursor-pointer">
          <ArrowUpTrayIcon className="w-5 h-5" />
          {uploading ? 'Uploading...' : 'Upload Images'}
          <input
            type="file"
            accept="image/*"
            multiple
            onChange={handleUpload}
            disabled={uploading}
            className="hidden"
          />
        </label>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
          {error}
        </div>
      )}

      {/* Categories */}
      <div className="flex gap-2 flex-wrap">
        {CATEGORIES.map(cat => (
          <button
            key={cat.id}
            onClick={() => setCategory(cat.id)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              category === cat.id
                ? 'bg-purple-600 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            {cat.name}
          </button>
        ))}
      </div>

      {/* Images Grid */}
      {loading ? (
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
          {[...Array(12)].map((_, i) => (
            <div key={i} className="aspect-square bg-gray-200 rounded-lg animate-pulse" />
          ))}
        </div>
      ) : images.length === 0 ? (
        <div className="bg-gray-50 rounded-xl border border-gray-200 p-12 text-center">
          <FolderIcon className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No Images Yet</h3>
          <p className="text-gray-500 mb-4">Upload images to use on your website</p>
          <label className="btn-secondary inline-flex items-center gap-2 cursor-pointer">
            <ArrowUpTrayIcon className="w-4 h-4" />
            Upload Your First Image
            <input
              type="file"
              accept="image/*"
              multiple
              onChange={handleUpload}
              className="hidden"
            />
          </label>
        </div>
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
          {images.map((image) => (
            <div
              key={image.path}
              onClick={() => setSelectedImage(image)}
              className="aspect-square bg-gray-100 rounded-lg overflow-hidden cursor-pointer hover:ring-2 hover:ring-purple-400 transition-all relative group"
            >
              <img
                src={image.url}
                alt={image.name}
                className="w-full h-full object-cover"
              />
              <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                <PhotoIcon className="w-8 h-8 text-white" />
              </div>
              {image.category && (
                <span className="absolute bottom-2 left-2 px-2 py-0.5 bg-black/60 text-white text-xs rounded">
                  {image.category}
                </span>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Image Detail Modal */}
      {selectedImage && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/50" onClick={() => setSelectedImage(null)} />
          <div className="relative bg-white rounded-xl max-w-2xl w-full max-h-[90vh] overflow-hidden">
            {/* Header */}
            <div className="flex items-center justify-between p-4 border-b">
              <h3 className="font-semibold text-gray-900 truncate">{selectedImage.name}</h3>
              <button
                onClick={() => setSelectedImage(null)}
                className="p-1 hover:bg-gray-100 rounded"
              >
                <XMarkIcon className="w-5 h-5" />
              </button>
            </div>

            {/* Image */}
            <div className="p-4 bg-gray-50">
              <img
                src={selectedImage.url}
                alt={selectedImage.name}
                className="max-h-96 mx-auto object-contain"
              />
            </div>

            {/* Details */}
            <div className="p-4 border-t space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-gray-500">Category:</span>
                <span className="text-gray-900">{selectedImage.category || 'Uncategorized'}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-500">Size:</span>
                <span className="text-gray-900">{formatFileSize(selectedImage.size)}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-500">URL:</span>
                <input
                  type="text"
                  value={selectedImage.url}
                  readOnly
                  className="flex-1 ml-4 text-xs bg-gray-100 px-2 py-1 rounded font-mono truncate"
                  onClick={(e) => {
                    e.target.select();
                    navigator.clipboard.writeText(selectedImage.url);
                  }}
                />
              </div>
            </div>

            {/* Actions */}
            <div className="p-4 border-t flex justify-end gap-2">
              <button
                onClick={() => handleDelete(selectedImage)}
                className="btn-secondary text-red-600 hover:bg-red-50 flex items-center gap-2"
              >
                <TrashIcon className="w-4 h-4" />
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
      <ConfirmDialog
        open={!!deleteTarget}
        title="Delete Image"
        message="Delete this image? This cannot be undone."
        confirmLabel="Delete"
        confirmVariant="danger"
        onConfirm={confirmDelete}
        onCancel={() => setDeleteTarget(null)}
      />
    </div>
  );
}
