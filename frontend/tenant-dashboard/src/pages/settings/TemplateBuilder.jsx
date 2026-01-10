import { useState, useEffect, useCallback, useRef } from 'react';
import {
  DndContext,
  closestCenter,
  DragOverlay,
  useDraggable,
  useDroppable,
  PointerSensor,
  useSensor,
  useSensors,
} from '@dnd-kit/core';
import {
  SortableContext,
  verticalListSortingStrategy,
  useSortable,
  arrayMove,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { useTheme } from '../../context/ThemeContext';
import { templatesApi } from '../../services/api';
import {
  Bars3Icon,
  PlusIcon,
  TrashIcon,
  EyeIcon,
  EyeSlashIcon,
  DocumentTextIcon,
  BuildingOfficeIcon,
  UserIcon,
  TableCellsIcon,
  BanknotesIcon,
  ClipboardDocumentListIcon,
  ArrowPathIcon,
  CheckCircleIcon,
  XMarkIcon,
  Cog6ToothIcon,
  PhotoIcon,
  CursorArrowRaysIcon,
  Square2StackIcon,
  PencilIcon,
} from '@heroicons/react/24/outline';

// Available section types with their configurations
const SECTION_TYPES = {
  header: {
    id: 'header',
    name: 'Company Header',
    icon: BuildingOfficeIcon,
    description: 'Logo, company name, contact info',
    configurable: ['showLogo', 'showAddress', 'showPhone', 'showEmail', 'showWebsite'],
    defaultConfig: {
      showLogo: true,
      showAddress: true,
      showPhone: true,
      showEmail: true,
      showWebsite: true,
    },
  },
  customer: {
    id: 'customer',
    name: 'Customer Details',
    icon: UserIcon,
    description: 'Customer name, email, address',
    configurable: ['showEmail', 'showPhone', 'showAddress'],
    defaultConfig: {
      showEmail: true,
      showPhone: true,
      showAddress: false,
    },
  },
  document_info: {
    id: 'document_info',
    name: 'Document Info',
    icon: DocumentTextIcon,
    description: 'Quote/Invoice number, date',
    configurable: ['showDate', 'showNumber', 'showValidity'],
    defaultConfig: {
      showDate: true,
      showNumber: true,
      showValidity: true,
    },
  },
  trip_details: {
    id: 'trip_details',
    name: 'Trip Details',
    icon: ClipboardDocumentListIcon,
    description: 'Destination, dates, travelers',
    configurable: ['showDestination', 'showDates', 'showTravelers'],
    defaultConfig: {
      showDestination: true,
      showDates: true,
      showTravelers: true,
    },
  },
  line_items: {
    id: 'line_items',
    name: 'Line Items',
    icon: TableCellsIcon,
    description: 'Itemized list with prices',
    configurable: ['showQuantity', 'showUnitPrice', 'showSubtotal'],
    defaultConfig: {
      showQuantity: true,
      showUnitPrice: true,
      showSubtotal: true,
    },
  },
  totals: {
    id: 'totals',
    name: 'Price Summary',
    icon: BanknotesIcon,
    description: 'Subtotal, tax, total',
    configurable: ['showSubtotal', 'showTax', 'showDiscount', 'showTotal'],
    defaultConfig: {
      showSubtotal: true,
      showTax: true,
      showDiscount: true,
      showTotal: true,
    },
  },
  banking: {
    id: 'banking',
    name: 'Banking Details',
    icon: BanknotesIcon,
    description: 'Payment instructions',
    configurable: ['showBankName', 'showAccountNumber', 'showBranchCode', 'showSwift'],
    defaultConfig: {
      showBankName: true,
      showAccountNumber: true,
      showBranchCode: true,
      showSwift: false,
    },
  },
  terms: {
    id: 'terms',
    name: 'Terms & Conditions',
    icon: ClipboardDocumentListIcon,
    description: 'Legal terms',
    configurable: ['collapsible'],
    defaultConfig: {
      collapsible: false,
    },
  },
  notes: {
    id: 'notes',
    name: 'Notes',
    icon: DocumentTextIcon,
    description: 'Additional notes',
    configurable: [],
    defaultConfig: {},
  },
  footer: {
    id: 'footer',
    name: 'Footer',
    icon: DocumentTextIcon,
    description: 'Page numbers, message',
    configurable: ['showPageNumbers', 'showThankYou'],
    defaultConfig: {
      showPageNumbers: true,
      showThankYou: true,
    },
  },
};

// Default templates
const DEFAULT_QUOTE_SECTIONS = [
  { id: 'header', type: 'header', visible: true, config: SECTION_TYPES.header.defaultConfig },
  { id: 'customer', type: 'customer', visible: true, config: SECTION_TYPES.customer.defaultConfig },
  { id: 'document_info', type: 'document_info', visible: true, config: SECTION_TYPES.document_info.defaultConfig },
  { id: 'trip_details', type: 'trip_details', visible: true, config: SECTION_TYPES.trip_details.defaultConfig },
  { id: 'line_items', type: 'line_items', visible: true, config: SECTION_TYPES.line_items.defaultConfig },
  { id: 'totals', type: 'totals', visible: true, config: SECTION_TYPES.totals.defaultConfig },
  { id: 'terms', type: 'terms', visible: true, config: SECTION_TYPES.terms.defaultConfig },
  { id: 'notes', type: 'notes', visible: false, config: SECTION_TYPES.notes.defaultConfig },
  { id: 'footer', type: 'footer', visible: true, config: SECTION_TYPES.footer.defaultConfig },
];

const DEFAULT_INVOICE_SECTIONS = [
  { id: 'header', type: 'header', visible: true, config: SECTION_TYPES.header.defaultConfig },
  { id: 'customer', type: 'customer', visible: true, config: SECTION_TYPES.customer.defaultConfig },
  { id: 'document_info', type: 'document_info', visible: true, config: SECTION_TYPES.document_info.defaultConfig },
  { id: 'trip_details', type: 'trip_details', visible: true, config: SECTION_TYPES.trip_details.defaultConfig },
  { id: 'line_items', type: 'line_items', visible: true, config: SECTION_TYPES.line_items.defaultConfig },
  { id: 'totals', type: 'totals', visible: true, config: SECTION_TYPES.totals.defaultConfig },
  { id: 'banking', type: 'banking', visible: true, config: SECTION_TYPES.banking.defaultConfig },
  { id: 'terms', type: 'terms', visible: true, config: SECTION_TYPES.terms.defaultConfig },
  { id: 'notes', type: 'notes', visible: false, config: SECTION_TYPES.notes.defaultConfig },
  { id: 'footer', type: 'footer', visible: true, config: SECTION_TYPES.footer.defaultConfig },
];

// Sample data for preview
const SAMPLE_DATA = {
  company: {
    name: 'Holiday Today Travel',
    email: 'quotes@holidaytoday.co.za',
    phone: '+27 21 123 4567',
    website: 'www.holidaytoday.co.za',
    address: '123 Travel Street, Cape Town 8001',
  },
  customer: {
    name: 'John Smith',
    email: 'john.smith@example.com',
    phone: '+27 82 555 1234',
  },
  document: {
    quoteNumber: 'QT-2024-001',
    invoiceNumber: 'INV-2024-001',
    date: new Date().toLocaleDateString('en-ZA'),
    validity: '14 days',
    dueDate: new Date(Date.now() + 14 * 24 * 60 * 60 * 1000).toLocaleDateString('en-ZA'),
  },
  trip: {
    destination: 'Zanzibar, Tanzania',
    checkIn: '15 Mar 2024',
    checkOut: '22 Mar 2024',
    nights: 7,
    travelers: '2 Adults',
  },
  items: [
    { description: 'Beach Resort - 7 nights', qty: 1, price: 'R 24,500' },
    { description: 'Airport Transfers', qty: 2, price: 'R 2,800' },
    { description: 'Travel Insurance', qty: 2, price: 'R 1,200' },
  ],
  totals: {
    subtotal: 'R 28,500',
    vat: 'R 4,275',
    total: 'R 32,775',
  },
  banking: {
    bank: 'First National Bank',
    account: '62XXXXXXXXX',
    branch: '250655',
    swift: 'FIRNZAJJ',
  },
};

// Draggable Palette Item
function PaletteItem({ type, sectionType, isDisabled }) {
  const { attributes, listeners, setNodeRef, isDragging } = useDraggable({
    id: `palette-${type}`,
    data: { type: 'palette', sectionType: type },
    disabled: isDisabled,
  });

  const Icon = sectionType.icon;

  return (
    <div
      ref={setNodeRef}
      {...listeners}
      {...attributes}
      className={`
        flex items-center gap-3 p-3 rounded-lg border-2 border-dashed transition-all
        ${isDragging ? 'opacity-50 border-primary-400 bg-primary-50' : ''}
        ${isDisabled
          ? 'border-gray-200 bg-gray-50 opacity-50 cursor-not-allowed'
          : 'border-gray-300 bg-white hover:border-primary-400 hover:bg-primary-50 cursor-grab active:cursor-grabbing'
        }
      `}
    >
      <Icon className={`w-5 h-5 ${isDisabled ? 'text-gray-400' : 'text-primary-600'}`} />
      <div className="flex-1 min-w-0">
        <div className={`text-sm font-medium truncate ${isDisabled ? 'text-gray-400' : 'text-gray-900'}`}>
          {sectionType.name}
        </div>
        <div className="text-xs text-gray-500 truncate">{sectionType.description}</div>
      </div>
      {isDisabled && (
        <span className="text-xs text-gray-400 bg-gray-100 px-2 py-0.5 rounded">Added</span>
      )}
    </div>
  );
}

// Canvas Section - Sortable and Selectable
function CanvasSection({ section, isSelected, onSelect, onRemove, templateType, primaryColor }) {
  const sectionType = SECTION_TYPES[section.type];
  const Icon = sectionType?.icon || DocumentTextIcon;
  const config = section.config || {};

  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: section.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : section.visible ? 1 : 0.5,
  };

  // Render section preview content
  const renderContent = () => {
    switch (section.type) {
      case 'header':
        return (
          <div className="flex justify-between items-start">
            <div>
              {config.showLogo && (
                <div className="w-16 h-6 bg-gray-200 rounded flex items-center justify-center text-[8px] text-gray-400 mb-1">
                  LOGO
                </div>
              )}
              <div className="font-semibold text-xs" style={{ color: primaryColor }}>
                {SAMPLE_DATA.company.name}
              </div>
            </div>
            <div className="text-right text-[9px] text-gray-500 space-y-0.5">
              {config.showPhone && <div>{SAMPLE_DATA.company.phone}</div>}
              {config.showEmail && <div>{SAMPLE_DATA.company.email}</div>}
              {config.showWebsite && <div>{SAMPLE_DATA.company.website}</div>}
            </div>
          </div>
        );

      case 'customer':
        return (
          <div className="text-[9px]">
            <div className="font-semibold text-gray-600 mb-0.5">Bill To:</div>
            <div className="font-medium text-gray-800">{SAMPLE_DATA.customer.name}</div>
            {config.showEmail && <div className="text-gray-500">{SAMPLE_DATA.customer.email}</div>}
            {config.showPhone && <div className="text-gray-500">{SAMPLE_DATA.customer.phone}</div>}
          </div>
        );

      case 'document_info':
        return (
          <div className="flex justify-between text-[9px]">
            <div>
              {config.showNumber && (
                <div>
                  <span className="font-semibold">{templateType === 'quote' ? 'Quote' : 'Invoice'} #:</span>{' '}
                  {templateType === 'quote' ? SAMPLE_DATA.document.quoteNumber : SAMPLE_DATA.document.invoiceNumber}
                </div>
              )}
              {config.showDate && <div><span className="font-semibold">Date:</span> {SAMPLE_DATA.document.date}</div>}
            </div>
            {config.showValidity && templateType === 'quote' && (
              <div className="text-right">
                <span className="font-semibold">Valid:</span> {SAMPLE_DATA.document.validity}
              </div>
            )}
          </div>
        );

      case 'trip_details':
        return (
          <div className="text-[9px] bg-gray-50 p-1.5 rounded">
            <div className="font-semibold mb-0.5" style={{ color: primaryColor }}>Trip Details</div>
            <div className="grid grid-cols-2 gap-0.5 text-gray-600">
              {config.showDestination && <div>{SAMPLE_DATA.trip.destination}</div>}
              {config.showTravelers && <div>{SAMPLE_DATA.trip.travelers}</div>}
              {config.showDates && <div>{SAMPLE_DATA.trip.checkIn} - {SAMPLE_DATA.trip.checkOut}</div>}
            </div>
          </div>
        );

      case 'line_items':
        return (
          <div className="text-[9px]">
            <table className="w-full">
              <thead>
                <tr style={{ borderBottom: `1px solid ${primaryColor}` }}>
                  <th className="text-left py-0.5 font-semibold">Item</th>
                  {config.showQuantity && <th className="text-center py-0.5 font-semibold w-8">Qty</th>}
                  {config.showUnitPrice && <th className="text-right py-0.5 font-semibold w-12">Price</th>}
                </tr>
              </thead>
              <tbody className="text-gray-600">
                {SAMPLE_DATA.items.slice(0, 2).map((item, i) => (
                  <tr key={i} className="border-b border-gray-100">
                    <td className="py-0.5 truncate max-w-[120px]">{item.description}</td>
                    {config.showQuantity && <td className="text-center py-0.5">{item.qty}</td>}
                    {config.showUnitPrice && <td className="text-right py-0.5">{item.price}</td>}
                  </tr>
                ))}
                <tr className="text-gray-400 italic">
                  <td colSpan={3} className="py-0.5">... more items</td>
                </tr>
              </tbody>
            </table>
          </div>
        );

      case 'totals':
        return (
          <div className="text-[9px] text-right space-y-0.5">
            {config.showSubtotal && (
              <div className="flex justify-end gap-2">
                <span className="text-gray-500">Subtotal:</span>
                <span className="w-14">{SAMPLE_DATA.totals.subtotal}</span>
              </div>
            )}
            {config.showTax && (
              <div className="flex justify-end gap-2">
                <span className="text-gray-500">VAT:</span>
                <span className="w-14">{SAMPLE_DATA.totals.vat}</span>
              </div>
            )}
            {config.showTotal && (
              <div className="flex justify-end gap-2 font-bold" style={{ color: primaryColor }}>
                <span>TOTAL:</span>
                <span className="w-14">{SAMPLE_DATA.totals.total}</span>
              </div>
            )}
          </div>
        );

      case 'banking':
        return (
          <div className="text-[9px] bg-gray-50 p-1.5 rounded">
            <div className="font-semibold mb-0.5" style={{ color: primaryColor }}>Payment Details</div>
            <div className="grid grid-cols-2 gap-0.5 text-gray-600">
              {config.showBankName && <div>Bank: {SAMPLE_DATA.banking.bank}</div>}
              {config.showAccountNumber && <div>Acc: {SAMPLE_DATA.banking.account}</div>}
              {config.showBranchCode && <div>Branch: {SAMPLE_DATA.banking.branch}</div>}
              {config.showSwift && <div>SWIFT: {SAMPLE_DATA.banking.swift}</div>}
            </div>
          </div>
        );

      case 'terms':
        return (
          <div className="text-[9px] text-gray-500">
            <div className="font-semibold text-gray-600 mb-0.5">Terms & Conditions</div>
            <div className="text-[8px] leading-tight">
              Payment due within 14 days...
            </div>
          </div>
        );

      case 'notes':
        return (
          <div className="text-[9px] text-gray-500 italic">
            <div className="font-semibold text-gray-600 mb-0.5">Notes</div>
            Thank you for choosing us...
          </div>
        );

      case 'footer':
        return (
          <div className="text-[8px] text-center text-gray-400 pt-1 border-t border-gray-200">
            {config.showThankYou && <div>Thank you for your business!</div>}
            {config.showPageNumbers && <div>Page 1 of 1</div>}
          </div>
        );

      default:
        return <div className="text-[9px] text-gray-400">{sectionType?.name}</div>;
    }
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      onClick={(e) => {
        e.stopPropagation();
        onSelect(section.id);
      }}
      className={`
        group relative rounded transition-all cursor-pointer
        ${isSelected
          ? 'ring-2 ring-primary-500 ring-offset-1'
          : 'hover:ring-2 hover:ring-gray-300 hover:ring-offset-1'
        }
        ${!section.visible ? 'opacity-50' : ''}
        ${isDragging ? 'shadow-lg z-50' : ''}
      `}
    >
      {/* Drag Handle - Top Bar */}
      <div
        {...attributes}
        {...listeners}
        className={`
          absolute -top-0 left-0 right-0 h-5 flex items-center justify-center gap-1
          bg-gradient-to-b from-gray-100 to-transparent opacity-0 group-hover:opacity-100
          transition-opacity cursor-grab active:cursor-grabbing rounded-t
          ${isSelected ? 'opacity-100' : ''}
        `}
      >
        <Bars3Icon className="w-3 h-3 text-gray-400" />
        <span className="text-[9px] text-gray-500">{sectionType?.name}</span>
      </div>

      {/* Section Content */}
      <div className={`p-2 ${isSelected ? 'bg-primary-50/30' : 'bg-white'}`}>
        {renderContent()}
      </div>

      {/* Hidden indicator */}
      {!section.visible && (
        <div className="absolute inset-0 flex items-center justify-center bg-white/80 rounded">
          <span className="text-[9px] text-gray-400 flex items-center gap-1">
            <EyeSlashIcon className="w-3 h-3" />
            Hidden
          </span>
        </div>
      )}
    </div>
  );
}

// Properties Panel for selected section
function PropertiesPanel({ section, onUpdate, onRemove, onClose }) {
  const sectionType = SECTION_TYPES[section?.type];

  if (!section || !sectionType) {
    return (
      <div className="p-4 text-center text-gray-500">
        <CursorArrowRaysIcon className="w-8 h-8 mx-auto mb-2 opacity-50" />
        <p className="text-sm">Click a section on the document to edit its properties</p>
      </div>
    );
  }

  const Icon = sectionType.icon;

  return (
    <div className="p-4 space-y-4">
      {/* Header */}
      <div className="flex items-center gap-3 pb-3 border-b border-gray-200">
        <div className="p-2 bg-primary-100 rounded-lg">
          <Icon className="w-5 h-5 text-primary-600" />
        </div>
        <div className="flex-1">
          <h4 className="font-semibold text-gray-900">{sectionType.name}</h4>
          <p className="text-xs text-gray-500">{sectionType.description}</p>
        </div>
        <button
          onClick={onClose}
          className="p-1 rounded hover:bg-gray-100"
        >
          <XMarkIcon className="w-4 h-4 text-gray-400" />
        </button>
      </div>

      {/* Visibility Toggle */}
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-gray-700">Visible</span>
        <button
          onClick={() => onUpdate({ visible: !section.visible })}
          className={`
            relative inline-flex h-6 w-11 items-center rounded-full transition-colors
            ${section.visible ? 'bg-primary-600' : 'bg-gray-200'}
          `}
        >
          <span
            className={`
              inline-block h-4 w-4 transform rounded-full bg-white transition-transform
              ${section.visible ? 'translate-x-6' : 'translate-x-1'}
            `}
          />
        </button>
      </div>

      {/* Configuration Options */}
      {sectionType.configurable?.length > 0 && (
        <div className="space-y-3">
          <h5 className="text-sm font-medium text-gray-700">Options</h5>
          <div className="space-y-2">
            {sectionType.configurable.map((configKey) => (
              <label key={configKey} className="flex items-center gap-3 text-sm">
                <input
                  type="checkbox"
                  checked={section.config?.[configKey] ?? true}
                  onChange={(e) => onUpdate({
                    config: { ...section.config, [configKey]: e.target.checked }
                  })}
                  className="rounded border-gray-300 text-primary-600 focus:ring-primary-500 w-4 h-4"
                />
                <span className="text-gray-700 capitalize">
                  {configKey.replace(/^show/, '').replace(/([A-Z])/g, ' $1').trim()}
                </span>
              </label>
            ))}
          </div>
        </div>
      )}

      {/* Remove Button */}
      <div className="pt-4 border-t border-gray-200">
        <button
          onClick={() => onRemove(section.id)}
          className="w-full flex items-center justify-center gap-2 px-4 py-2 text-sm text-red-600 hover:bg-red-50 rounded-lg transition-colors"
        >
          <TrashIcon className="w-4 h-4" />
          Remove Section
        </button>
      </div>
    </div>
  );
}

// Drag Overlay Preview
function DragPreview({ type, isDragging }) {
  const sectionType = SECTION_TYPES[type];
  if (!sectionType) return null;

  const Icon = sectionType.icon;

  return (
    <div className="bg-white border-2 border-primary-400 rounded-lg shadow-xl p-3 min-w-[200px]">
      <div className="flex items-center gap-2">
        <Icon className="w-5 h-5 text-primary-600" />
        <span className="font-medium text-gray-900">{sectionType.name}</span>
      </div>
    </div>
  );
}

// Main Template Builder Component
export default function TemplateBuilder({ templateType = 'quote', onClose }) {
  const { branding } = useTheme();
  const primaryColor = branding?.colors?.primary || '#7C3AED';

  // State
  const [sections, setSections] = useState(
    templateType === 'quote' ? DEFAULT_QUOTE_SECTIONS : DEFAULT_INVOICE_SECTIONS
  );
  const [selectedId, setSelectedId] = useState(null);
  const [activeId, setActiveId] = useState(null);
  const [dragType, setDragType] = useState(null);
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(true);
  const [toast, setToast] = useState(null);
  const [hasChanges, setHasChanges] = useState(false);

  const canvasRef = useRef(null);

  // DnD sensors
  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: { distance: 5 },
    })
  );

  // Droppable canvas
  const { setNodeRef: setDroppableRef, isOver } = useDroppable({
    id: 'canvas-drop-zone',
  });

  // Get sections already on canvas
  const usedSectionTypes = new Set(sections.map(s => s.type));

  // Load template
  useEffect(() => {
    loadTemplate();
  }, [templateType]);

  const loadTemplate = async () => {
    try {
      setLoading(true);
      const response = await templatesApi.get();
      if (response.data?.success) {
        const templateData = response.data.data?.[templateType];
        if (templateData?.sections) {
          const savedSections = templateData.sections;
          const defaultSections = templateType === 'quote' ? DEFAULT_QUOTE_SECTIONS : DEFAULT_INVOICE_SECTIONS;

          const mergedSections = defaultSections.map((defaultSection) => {
            const saved = savedSections.find(s => s.id === defaultSection.id);
            if (saved) {
              return {
                ...defaultSection,
                ...saved,
                config: { ...defaultSection.config, ...saved.config },
              };
            }
            return defaultSection;
          });

          setSections(mergedSections);
        }
      }
    } catch (error) {
      console.error('Failed to load template:', error);
    } finally {
      setLoading(false);
    }
  };

  // Save template
  const handleSave = async () => {
    try {
      setSaving(true);
      const response = await templatesApi.update({
        [templateType]: {
          sections,
          updated_at: new Date().toISOString(),
        },
      });

      if (response.data?.success) {
        showToast('Template saved!', 'success');
        setHasChanges(false);
      } else {
        showToast('Failed to save', 'error');
      }
    } catch (error) {
      console.error('Failed to save template:', error);
      showToast('Failed to save', 'error');
    } finally {
      setSaving(false);
    }
  };

  // Reset
  const handleReset = () => {
    setSections(templateType === 'quote' ? DEFAULT_QUOTE_SECTIONS : DEFAULT_INVOICE_SECTIONS);
    setSelectedId(null);
    setHasChanges(true);
    showToast('Reset to defaults', 'success');
  };

  // Toast helper
  const showToast = (message, type) => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 3000);
  };

  // Drag handlers
  const handleDragStart = (event) => {
    const { active } = event;
    setActiveId(active.id);

    if (active.id.startsWith('palette-')) {
      setDragType('palette');
    } else {
      setDragType('reorder');
    }
  };

  const handleDragEnd = (event) => {
    const { active, over } = event;
    setActiveId(null);
    setDragType(null);

    if (!over) return;

    // Handle palette drop onto canvas
    if (active.id.startsWith('palette-') && over.id === 'canvas-drop-zone') {
      const sectionType = active.data.current.sectionType;

      // Add section if not already present
      if (!usedSectionTypes.has(sectionType)) {
        const newSection = {
          id: sectionType,
          type: sectionType,
          visible: true,
          config: SECTION_TYPES[sectionType].defaultConfig,
        };
        setSections(prev => [...prev, newSection]);
        setSelectedId(sectionType);
        setHasChanges(true);
      }
      return;
    }

    // Handle reordering on canvas
    if (active.id !== over.id && !active.id.startsWith('palette-')) {
      setSections((items) => {
        const oldIndex = items.findIndex(item => item.id === active.id);
        const newIndex = items.findIndex(item => item.id === over.id);
        if (oldIndex !== -1 && newIndex !== -1) {
          setHasChanges(true);
          return arrayMove(items, oldIndex, newIndex);
        }
        return items;
      });
    }
  };

  // Section handlers
  const updateSection = (id, updates) => {
    setSections(prev => prev.map(s =>
      s.id === id ? { ...s, ...updates } : s
    ));
    setHasChanges(true);
  };

  const removeSection = (id) => {
    setSections(prev => prev.filter(s => s.id !== id));
    setSelectedId(null);
    setHasChanges(true);
  };

  // Get selected section
  const selectedSection = selectedId ? sections.find(s => s.id === selectedId) : null;

  // Get drag preview type
  const getDragPreviewType = () => {
    if (!activeId) return null;
    if (activeId.startsWith('palette-')) {
      return activeId.replace('palette-', '');
    }
    return sections.find(s => s.id === activeId)?.type;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-200 bg-white">
        <div>
          <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
            <PencilIcon className="w-5 h-5 text-primary-600" />
            {templateType === 'quote' ? 'Quote' : 'Invoice'} Template
          </h2>
          <p className="text-sm text-gray-500">
            Drag sections from the left onto the document, then click to edit
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={handleReset}
            className="btn-secondary text-sm flex items-center gap-2"
          >
            <ArrowPathIcon className="w-4 h-4" />
            Reset
          </button>
          <button
            onClick={handleSave}
            disabled={saving || !hasChanges}
            className="btn-primary text-sm flex items-center gap-2"
          >
            {saving ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                Saving...
              </>
            ) : (
              <>
                <CheckCircleIcon className="w-4 h-4" />
                Save
              </>
            )}
          </button>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden bg-gray-100">
        <DndContext
          sensors={sensors}
          collisionDetection={closestCenter}
          onDragStart={handleDragStart}
          onDragEnd={handleDragEnd}
        >
          {/* Left Panel - Section Palette */}
          <div className="w-64 bg-white border-r border-gray-200 overflow-y-auto flex-shrink-0">
            <div className="p-4">
              <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
                <Square2StackIcon className="w-4 h-4" />
                Available Sections
              </h3>
              <p className="text-xs text-gray-500 mb-4">
                Drag sections onto the document canvas
              </p>
              <div className="space-y-2">
                {Object.entries(SECTION_TYPES).map(([type, sectionType]) => (
                  <PaletteItem
                    key={type}
                    type={type}
                    sectionType={sectionType}
                    isDisabled={usedSectionTypes.has(type)}
                  />
                ))}
              </div>
            </div>
          </div>

          {/* Center - Document Canvas */}
          <div className="flex-1 overflow-auto p-6" onClick={() => setSelectedId(null)}>
            <div
              ref={setDroppableRef}
              className={`
                mx-auto bg-white shadow-lg rounded-sm transition-all
                ${isOver && dragType === 'palette' ? 'ring-4 ring-primary-300 ring-opacity-50' : ''}
              `}
              style={{
                width: '420px',
                minHeight: '595px', // A4-ish ratio
                padding: '24px',
              }}
            >
              {/* Document Title Bar */}
              <div
                className="text-center mb-4 pb-2 border-b-2"
                style={{ borderColor: primaryColor }}
              >
                <span className="text-lg font-bold" style={{ color: primaryColor }}>
                  {templateType === 'quote' ? 'QUOTATION' : 'TAX INVOICE'}
                </span>
              </div>

              {/* Sortable Sections */}
              <SortableContext
                items={sections.map(s => s.id)}
                strategy={verticalListSortingStrategy}
              >
                <div className="space-y-3">
                  {sections.map((section) => (
                    <CanvasSection
                      key={section.id}
                      section={section}
                      isSelected={selectedId === section.id}
                      onSelect={setSelectedId}
                      onRemove={removeSection}
                      templateType={templateType}
                      primaryColor={primaryColor}
                    />
                  ))}
                </div>
              </SortableContext>

              {/* Empty state */}
              {sections.length === 0 && (
                <div className="flex flex-col items-center justify-center h-64 text-gray-400">
                  <PlusIcon className="w-12 h-12 mb-2" />
                  <p className="text-sm">Drag sections here to build your template</p>
                </div>
              )}

              {/* Drop indicator when dragging from palette */}
              {isOver && dragType === 'palette' && (
                <div className="mt-4 p-4 border-2 border-dashed border-primary-300 rounded-lg bg-primary-50 text-center">
                  <span className="text-sm text-primary-600">Drop here to add section</span>
                </div>
              )}
            </div>
          </div>

          {/* Right Panel - Properties */}
          <div className="w-72 bg-white border-l border-gray-200 overflow-y-auto flex-shrink-0">
            <div className="sticky top-0 bg-white border-b border-gray-200 px-4 py-3">
              <h3 className="text-sm font-semibold text-gray-700 flex items-center gap-2">
                <Cog6ToothIcon className="w-4 h-4" />
                Properties
              </h3>
            </div>
            <PropertiesPanel
              section={selectedSection}
              onUpdate={(updates) => selectedId && updateSection(selectedId, updates)}
              onRemove={removeSection}
              onClose={() => setSelectedId(null)}
            />
          </div>

          {/* Drag Overlay */}
          <DragOverlay>
            {activeId && <DragPreview type={getDragPreviewType()} />}
          </DragOverlay>
        </DndContext>
      </div>

      {/* Toast */}
      {toast && (
        <div
          className={`fixed bottom-4 right-4 flex items-center gap-2 px-4 py-3 rounded-lg shadow-lg z-50 ${
            toast.type === 'success' ? 'bg-green-600 text-white' : 'bg-red-600 text-white'
          }`}
        >
          {toast.type === 'success' ? (
            <CheckCircleIcon className="w-5 h-5" />
          ) : (
            <XMarkIcon className="w-5 h-5" />
          )}
          {toast.message}
        </div>
      )}
    </div>
  );
}
