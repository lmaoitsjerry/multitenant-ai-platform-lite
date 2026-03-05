import { useState, useEffect } from 'react';
import { websiteBuilderApi } from '../../services/api';
import {
  CheckIcon,
  ArrowPathIcon,
  GlobeAltIcon,
  BuildingOfficeIcon,
  PaperAirplaneIcon,
  TruckIcon,
  TicketIcon,
} from '@heroicons/react/24/outline';

const PRODUCT_TYPES = [
  { id: 'hotels', name: 'Hotels', icon: BuildingOfficeIcon },
  { id: 'flights', name: 'Flights', icon: PaperAirplaneIcon },
  { id: 'transfers', name: 'Transfers', icon: TruckIcon },
  { id: 'activities', name: 'Activities', icon: TicketIcon },
];

export default function WebsiteProducts() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState(null);
  const [productConfig, setProductConfig] = useState({ destinations: {} });
  const [markupRules, setMarkupRules] = useState({
    defaultMarkup: { percentage: 10, enabled: true },
    productTypeMarkups: [],
    supplierMarkups: [],
  });
  const [existingSettings, setExistingSettings] = useState({});

  // Destinations matching the website builder's supported set
  const destinations = [
    { code: 'zanzibar', name: 'Zanzibar' },
    { code: 'maldives', name: 'Maldives' },
    { code: 'seychelles', name: 'Seychelles' },
    { code: 'mauritius', name: 'Mauritius' },
    { code: 'cape-town', name: 'Cape Town' },
    { code: 'dubai', name: 'Dubai' },
    { code: 'kenya', name: 'Kenya' },
  ];

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    setLoading(true);
    try {
      const response = await websiteBuilderApi.getWebsiteConfig();
      if (response.data?.settings) {
        setExistingSettings(response.data.settings);
        if (response.data.settings.productConfig) {
          setProductConfig(response.data.settings.productConfig);
        }
        if (response.data.settings.markupRules) {
          setMarkupRules(response.data.settings.markupRules);
        }
      }
    } catch (err) {
      console.error('Failed to load product config:', err);
      setError('Failed to load product settings');
    } finally {
      setLoading(false);
    }
  }

  function toggleDestination(destCode) {
    setProductConfig(prev => {
      const dest = prev.destinations?.[destCode] || { enabled: false, productTypes: {} };
      const isCurrentlyEnabled = dest.enabled;

      // When enabling a destination, turn ALL product types ON by default
      const newProductTypes = isCurrentlyEnabled
        ? {} // Turning off - clear product types
        : PRODUCT_TYPES.reduce((acc, type) => {
            acc[type.id] = { enabled: true };
            return acc;
          }, {});

      return {
        ...prev,
        destinations: {
          ...prev.destinations,
          [destCode]: {
            ...dest,
            enabled: !isCurrentlyEnabled,
            productTypes: isCurrentlyEnabled ? dest.productTypes : newProductTypes,
          },
        },
      };
    });
    setSaved(false);
  }

  function toggleProductType(destCode, productType) {
    setProductConfig(prev => {
      const dest = prev.destinations?.[destCode] || { enabled: true, productTypes: {} };
      const types = dest.productTypes || {};
      return {
        ...prev,
        destinations: {
          ...prev.destinations,
          [destCode]: {
            ...dest,
            productTypes: {
              ...types,
              [productType]: { enabled: !types[productType]?.enabled },
            },
          },
        },
      };
    });
    setSaved(false);
  }

  function updateMarkup(value) {
    setMarkupRules(prev => ({
      ...prev,
      defaultMarkup: {
        ...prev.defaultMarkup,
        percentage: parseFloat(value) || 0,
      },
    }));
    setSaved(false);
  }

  async function handleSave() {
    setSaving(true);
    setError(null);
    try {
      // Merge with existing settings to avoid overwriting other keys
      const mergedSettings = { ...existingSettings, productConfig, markupRules };
      await websiteBuilderApi.updateWebsiteConfig({ settings: mergedSettings });
      setExistingSettings(mergedSettings);
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (err) {
      console.error('Failed to save:', err);
      setError('Failed to save product settings');
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <div className="p-6">
        <div className="animate-pulse space-y-6">
          <div className="h-8 w-48 bg-gray-200 rounded" />
          <div className="h-64 bg-gray-200 rounded-xl" />
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Products Configuration</h1>
          <p className="text-gray-500">Configure which destinations and products to show on your website</p>
        </div>
        <button
          onClick={handleSave}
          disabled={saving}
          className="btn-primary flex items-center gap-2"
        >
          {saving ? (
            <ArrowPathIcon className="w-4 h-4 animate-spin" />
          ) : saved ? (
            <CheckIcon className="w-4 h-4" />
          ) : null}
          {saved ? 'Saved!' : saving ? 'Saving...' : 'Save Changes'}
        </button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
          {error}
        </div>
      )}

      {/* Markup Settings */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Pricing Markup</h2>
        <p className="text-sm text-gray-500 mb-4">
          Set a default markup percentage that will be applied to all product prices on your website.
        </p>

        <div className="flex items-center gap-4">
          <label className="text-sm font-medium text-gray-700">Default Markup:</label>
          <div className="flex items-center gap-2">
            <input
              type="number"
              min="0"
              max="100"
              value={markupRules.defaultMarkup?.percentage || 0}
              onChange={(e) => updateMarkup(e.target.value)}
              className="w-24 px-3 py-2 border border-gray-200 rounded-lg text-center"
            />
            <span className="text-gray-500">%</span>
          </div>
        </div>
      </div>

      {/* Destinations */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Destinations & Product Types</h2>
        <p className="text-sm text-gray-500 mb-6">
          Enable destinations and choose which product types to display for each.
        </p>

        <div className="space-y-4">
          {destinations.map(dest => {
            const config = productConfig.destinations?.[dest.code] || { enabled: false, productTypes: {} };
            const isEnabled = config.enabled;

            return (
              <div key={dest.code} className="border border-gray-200 rounded-lg overflow-hidden">
                {/* Destination Header */}
                <div
                  onClick={() => toggleDestination(dest.code)}
                  className={`flex items-center justify-between p-4 cursor-pointer transition-colors ${
                    isEnabled ? 'bg-purple-50' : 'bg-gray-50 hover:bg-gray-100'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <div className={`p-2 rounded-lg ${isEnabled ? 'bg-purple-100' : 'bg-gray-200'}`}>
                      <GlobeAltIcon className={`w-5 h-5 ${isEnabled ? 'text-purple-600' : 'text-gray-500'}`} />
                    </div>
                    <span
                      className="font-medium"
                      style={{ color: isEnabled ? '#111827' : '#6b7280' }}
                    >
                      {dest.name}
                    </span>
                  </div>
                  <div className={`w-12 h-6 rounded-full transition-colors ${
                    isEnabled ? 'bg-purple-600' : 'bg-gray-300'
                  }`}>
                    <div className={`w-5 h-5 bg-white rounded-full shadow transform transition-transform mt-0.5 ${
                      isEnabled ? 'translate-x-6' : 'translate-x-0.5'
                    }`} />
                  </div>
                </div>

                {/* Product Types */}
                {isEnabled && (
                  <div className="p-4 border-t border-gray-200 bg-white">
                    <div className="flex flex-wrap gap-2">
                      {PRODUCT_TYPES.map(type => {
                        const typeEnabled = config.productTypes?.[type.id]?.enabled;
                        return (
                          <button
                            key={type.id}
                            onClick={() => toggleProductType(dest.code, type.id)}
                            className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                              typeEnabled
                                ? 'bg-purple-100 text-purple-700'
                                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                            }`}
                          >
                            <type.icon className="w-4 h-4" />
                            {type.name}
                          </button>
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
