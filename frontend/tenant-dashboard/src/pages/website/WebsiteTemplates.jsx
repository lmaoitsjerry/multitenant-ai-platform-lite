import { useState, useEffect } from 'react';
import { websiteBuilderApi } from '../../services/api';
import {
  CheckCircleIcon,
  ArrowPathIcon,
} from '@heroicons/react/24/outline';

export default function WebsiteTemplates() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [templates, setTemplates] = useState([]);
  const [currentTemplate, setCurrentTemplate] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    setLoading(true);
    try {
      const [templatesRes, configRes] = await Promise.all([
        websiteBuilderApi.getTemplates(),
        websiteBuilderApi.getWebsiteConfig(),
      ]);
      setTemplates(templatesRes.data?.templates || []);
      setCurrentTemplate(configRes.data?.template || null);
    } catch (err) {
      console.error('Failed to load templates:', err);
      setError('Failed to load templates. Please check if Website Builder is running.');
    } finally {
      setLoading(false);
    }
  }

  async function selectTemplate(templateId) {
    setSaving(true);
    try {
      await websiteBuilderApi.selectTemplate(templateId);
      setCurrentTemplate(templateId);
    } catch (err) {
      console.error('Failed to select template:', err);
      setError('Failed to select template');
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <div className="p-6">
        <div className="animate-pulse space-y-6">
          <div className="h-8 w-48 bg-gray-200 rounded" />
          <div className="grid grid-cols-3 gap-6">
            {[1, 2, 3].map(i => (
              <div key={i} className="h-64 bg-gray-200 rounded-xl" />
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (error && templates.length === 0) {
    return (
      <div className="p-6">
        <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-center">
          <p className="text-red-700">{error}</p>
          <button onClick={loadData} className="btn-secondary mt-4">
            <ArrowPathIcon className="w-4 h-4 mr-2" />
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Website Templates</h1>
        <p className="text-gray-500">Choose a template that best represents your travel brand</p>
      </div>

      {/* Templates Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {templates.map((template) => {
          const isSelected = currentTemplate === template.id;
          return (
            <div
              key={template.id}
              onClick={() => !saving && selectTemplate(template.id)}
              className={`relative bg-white rounded-xl border-2 overflow-hidden cursor-pointer transition-all ${
                isSelected
                  ? 'border-purple-500 ring-2 ring-purple-200'
                  : 'border-gray-200 hover:border-purple-300 hover:shadow-lg'
              }`}
            >
              {/* Thumbnail */}
              <div className="aspect-video bg-gray-100 relative overflow-hidden">
                {template.thumbnail ? (
                  <img
                    src={template.thumbnail}
                    alt={template.name}
                    className="w-full h-full object-cover"
                  />
                ) : (
                  <div className="w-full h-full flex items-center justify-center">
                    <span className="text-gray-400">No preview</span>
                  </div>
                )}
                {isSelected && (
                  <div className="absolute top-3 right-3 bg-purple-600 text-white p-1.5 rounded-full">
                    <CheckCircleIcon className="w-5 h-5" />
                  </div>
                )}
              </div>

              {/* Info */}
              <div className="p-4">
                <h3 className="font-semibold text-gray-900 mb-1">{template.name}</h3>
                <p className="text-sm text-gray-500 line-clamp-2">{template.description}</p>

                {/* Color Preview */}
                {template.colors && (
                  <div className="flex gap-1 mt-3">
                    {Object.entries(template.colors).slice(0, 5).map(([key, color]) => (
                      <div
                        key={key}
                        className="w-6 h-6 rounded-full border border-gray-200"
                        style={{ backgroundColor: color }}
                        title={key}
                      />
                    ))}
                  </div>
                )}

                {isSelected && (
                  <span className="inline-block mt-3 px-3 py-1 bg-purple-100 text-purple-700 text-sm font-medium rounded-full">
                    Selected
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {templates.length === 0 && (
        <div className="bg-gray-50 rounded-xl border border-gray-200 p-12 text-center">
          <p className="text-gray-500">No templates available. Check Website Builder connection.</p>
        </div>
      )}
    </div>
  );
}
