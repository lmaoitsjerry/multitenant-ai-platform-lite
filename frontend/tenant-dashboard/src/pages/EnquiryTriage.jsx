import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  EnvelopeIcon,
  UserIcon,
  CalendarIcon,
  MapPinIcon,
  UserGroupIcon,
  ClockIcon,
  CheckIcon,
  XMarkIcon,
  ArrowPathIcon,
  SparklesIcon,
  InboxIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  DocumentTextIcon,
  PencilIcon,
  CurrencyDollarIcon,
  ForwardIcon,
  MinusIcon,
  PlusIcon,
  BuildingOfficeIcon,
} from '@heroicons/react/24/outline';
import { inboundApi, quotesApi } from '../services/api';

// Priority colors
const priorityConfig = {
  urgent: { bg: 'bg-red-100 text-red-800 border-red-200', dot: 'bg-red-500' },
  high: { bg: 'bg-orange-100 text-orange-800 border-orange-200', dot: 'bg-orange-500' },
  normal: { bg: 'bg-blue-100 text-blue-800 border-blue-200', dot: 'bg-blue-500' },
  low: { bg: 'bg-gray-100 text-gray-600 border-gray-200', dot: 'bg-gray-400' },
};

// Source labels
const sourceLabels = {
  email: 'Email',
  web: 'Web Form',
  phone: 'Phone',
  chat: 'Live Chat',
};

function formatTimeAgo(dateString) {
  if (!dateString) return 'Unknown';
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now - date;
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString();
}

function parseEmailContent(message) {
  const details = { destination: null, dates: null, travelers: null, budget: null };
  if (!message) return details;

  const destinations = [
    'zanzibar', 'maldives', 'mauritius', 'seychelles', 'dubai', 'kenya',
    'tanzania', 'cape town', 'kruger', 'victoria falls', 'bali', 'thailand'
  ];

  const lowerMessage = message.toLowerCase();
  for (const dest of destinations) {
    if (lowerMessage.includes(dest)) {
      details.destination = dest.charAt(0).toUpperCase() + dest.slice(1);
      break;
    }
  }

  const datePatterns = [
    /(\d{1,2})\s*(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\s*(\d{4})?/gi,
    /(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{2,4})/g,
  ];
  for (const pattern of datePatterns) {
    const match = message.match(pattern);
    if (match) { details.dates = match[0]; break; }
  }

  const travelerPatterns = [
    /(\d+)\s*(adult|person|people|pax|guest|traveler)/i,
    /(two|three|four|five|six)\s*(adult|person|people|pax|guest)/i,
    /couple/i,
    /family\s*of\s*(\d+)/i,
  ];
  for (const pattern of travelerPatterns) {
    const match = message.match(pattern);
    if (match) {
      details.travelers = match[0].toLowerCase().includes('couple') ? '2 adults' : match[0];
      break;
    }
  }

  return details;
}

export default function EnquiryTriage() {
  const navigate = useNavigate();
  const [tickets, setTickets] = useState([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [processing, setProcessing] = useState(false);
  const [stats, setStats] = useState({ total: 0, open: 0, processed: 0 });
  const [seeding, setSeeding] = useState(false);
  const [warning, setWarning] = useState(null);
  const [notification, setNotification] = useState(null);
  const [editableDetails, setEditableDetails] = useState({
    destination: '', check_in: '', check_out: '',
    rooms: [{ adults: 2, children: 0 }],
    children_ages: [], budget: '', requested_hotel: '',
  });

  const totalAdults = editableDetails.rooms.reduce((s, r) => s + r.adults, 0);
  const totalChildren = editableDetails.rooms.reduce((s, r) => s + r.children, 0);

  const showNotification = useCallback((type, message) => {
    setNotification({ type, message });
    setTimeout(() => setNotification(null), 4000);
  }, []);

  // Load open tickets
  const loadTickets = useCallback(async () => {
    setLoading(true);
    setError(null);
    setWarning(null);
    try {
      const response = await inboundApi.listTickets({ status: 'open', limit: 50 });
      if (response.data?.success) {
        setTickets(response.data.data || []);
        setStats({
          total: response.data.stats?.total || 0,
          open: response.data.stats?.open || 0,
          processed: (response.data.stats?.in_progress || 0) +
                     (response.data.stats?.resolved || 0) +
                     (response.data.stats?.closed || 0),
        });
        setCurrentIndex(0);
        if (response.data.warning) setWarning(response.data.warning);
      } else {
        setError(response.data?.error || 'Failed to load enquiries');
      }
    } catch (err) {
      console.error('Failed to load tickets:', err);
      setTickets([]);
      setStats({ total: 0, open: 0, processed: 0 });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadTickets(); }, [loadTickets]);

  const currentTicket = tickets[currentIndex];
  const parsedDetails = currentTicket ? parseEmailContent(currentTicket.message) : {};
  const metadataDetails = currentTicket?.metadata?.parsed_details || {};

  // Sync editable details when current ticket changes
  useEffect(() => {
    if (currentTicket) {
      // Build rooms from metadata — if rooms exist use them, otherwise derive from adults/children
      const metaRooms = metadataDetails.rooms;
      const rooms = Array.isArray(metaRooms) && metaRooms.length > 0
        ? metaRooms
        : [{ adults: metadataDetails.adults ?? 2, children: metadataDetails.children ?? 0 }];

      setEditableDetails({
        destination: metadataDetails.destination || parsedDetails.destination || '',
        check_in: metadataDetails.check_in || '',
        check_out: metadataDetails.check_out || '',
        rooms,
        children_ages: Array.isArray(metadataDetails.children_ages) ? metadataDetails.children_ages : [],
        budget: metadataDetails.budget ?? '',
        requested_hotel: metadataDetails.requested_hotel || '',
      });
    }
  }, [currentIndex, currentTicket?.ticket_id]);

  // Handle accept (auto-generate draft quote, fallback to manual form)
  const handleAccept = async () => {
    if (!currentTicket || processing) return;
    setProcessing(true);
    try {
      // Mark ticket as in-progress
      await inboundApi.updateTicket(currentTicket.ticket_id, {
        status: 'in_progress',
        notes: 'Accepted for quote generation via triage',
      });

      // Auto-fix stale dates: if check_in is in the past, bump forward by 1 year
      let fixedCheckIn = editableDetails.check_in;
      let fixedCheckOut = editableDetails.check_out;
      let datesAutoCorrected = false;

      if (fixedCheckIn) {
        const today = new Date().toISOString().split('T')[0];
        if (fixedCheckIn < today) {
          const bumpYear = (dateStr) => {
            const d = new Date(dateStr);
            d.setFullYear(d.getFullYear() + 1);
            return d.toISOString().split('T')[0];
          };
          fixedCheckIn = bumpYear(fixedCheckIn);
          if (fixedCheckOut) fixedCheckOut = bumpYear(fixedCheckOut);
          datesAutoCorrected = true;
        }
      }

      if (datesAutoCorrected) {
        showNotification('warning', `Dates were in the past — auto-corrected to ${fixedCheckIn}`);
      }

      // Build prefill data for fallback
      const prefillData = {
        customerName: currentTicket.customer_name,
        customerEmail: currentTicket.customer_email,
        destination: editableDetails.destination,
        check_in: fixedCheckIn,
        check_out: fixedCheckOut,
        adults: totalAdults,
        children: totalChildren,
        rooms: editableDetails.rooms,
        budget: editableDetails.budget,
        requested_hotel: editableDetails.requested_hotel,
        notes: `From enquiry: ${currentTicket.subject}\n\n${currentTicket.message}`,
        ticketId: currentTicket.ticket_id,
      };

      // Try auto-generating a draft quote
      try {
        const budgetNum = typeof editableDetails.budget === 'number'
          ? editableDetails.budget
          : (parseInt(String(editableDetails.budget).replace(/[^\d]/g, ''), 10) || null);
        const payload = {
          inquiry: {
            name: currentTicket.customer_name || 'Guest',
            email: currentTicket.customer_email,
            destination: editableDetails.destination,
            check_in: fixedCheckIn,
            check_out: fixedCheckOut,
            adults: totalAdults,
            children: totalChildren,
            children_ages: editableDetails.children_ages,
            rooms: editableDetails.rooms,
            room_count: editableDetails.rooms.length,
            requested_hotel: editableDetails.requested_hotel || undefined,
            budget: budgetNum,
            message: `From enquiry: ${currentTicket.subject}\n\n${currentTicket.message}`,
          },
          send_email: false,
          save_as_draft: true,
          ticket_id: currentTicket.ticket_id,
          selected_hotels: editableDetails.requested_hotel ? [editableDetails.requested_hotel] : undefined,
        };
        const response = await quotesApi.generate(payload);
        const data = response.data || {};
        if (data.success && data.quote_id) {
          showNotification('success', 'Draft quote created — review and send when ready');
          navigate(`/quotes/${data.quote_id}`);
          return;
        }
        // Generation returned but failed — surface the actual reason
        const reason = data.error || data.status || 'Unknown error';
        console.warn('Quote generation returned failure:', data);
        throw new Error(reason);
      } catch (genErr) {
        console.error('Auto-generate failed, falling back to manual form:', genErr);
        const detail = genErr.response?.data?.detail || genErr.message || '';
        showNotification('warning', `Auto-generation failed${detail ? ': ' + detail : ''} — opening quote builder`);
        navigate('/quotes/new', { state: { prefill: prefillData } });
      }
    } catch (err) {
      console.error('Failed to accept ticket:', err);
      showNotification('error', 'Failed to accept enquiry. Please try again.');
    } finally {
      setProcessing(false);
    }
  };

  // Handle reject
  const handleReject = async () => {
    if (!currentTicket || processing) return;
    setProcessing(true);
    try {
      await inboundApi.updateTicket(currentTicket.ticket_id, {
        status: 'closed',
        notes: 'Rejected via triage - not a valid enquiry',
      });
      showNotification('success', 'Enquiry rejected');
      setTickets(prev => prev.filter((_, i) => i !== currentIndex));
      if (currentIndex >= tickets.length - 1 && currentIndex > 0) {
        setCurrentIndex(prev => prev - 1);
      }
      setStats(prev => ({ ...prev, open: prev.open - 1, processed: prev.processed + 1 }));
    } catch (err) {
      console.error('Failed to reject ticket:', err);
      showNotification('error', 'Failed to reject enquiry. Please try again.');
    } finally {
      setProcessing(false);
    }
  };

  // Handle skip
  const handleSkip = () => {
    if (processing || !tickets.length) return;
    if (currentIndex < tickets.length - 1) {
      setCurrentIndex(prev => prev + 1);
    } else if (tickets.length > 1) {
      setCurrentIndex(0);
    }
  };

  // Handle previous
  const handlePrevious = () => {
    if (processing || currentIndex === 0) return;
    setCurrentIndex(prev => prev - 1);
  };

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
      switch (e.key) {
        case 'a': handleAccept(); break;
        case 'r': handleReject(); break;
        case 's': handleSkip(); break;
        case 'ArrowRight': handleSkip(); break;
        case 'ArrowLeft': handlePrevious(); break;
        default: break;
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [currentTicket, processing, currentIndex]);

  // Stepper component for adults/children
  const Stepper = ({ label, icon: Icon, value, onChange, min = 0, max = 20 }) => (
    <div className="flex items-start gap-3">
      <div className="mt-0.5 text-theme-primary">
        {Icon ? <Icon className="h-4 w-4" /> : null}
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-xs text-gray-500 mb-1">{label}</p>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => onChange(Math.max(min, value - 1))}
            disabled={value <= min}
            className="p-1 rounded-md border border-gray-300 hover:bg-gray-100 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
          >
            <MinusIcon className="h-3.5 w-3.5 text-gray-600" />
          </button>
          <span className="w-8 text-center text-sm font-semibold text-gray-900 tabular-nums">{value}</span>
          <button
            type="button"
            onClick={() => onChange(Math.min(max, value + 1))}
            disabled={value >= max}
            className="p-1 rounded-md border border-gray-300 hover:bg-gray-100 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
          >
            <PlusIcon className="h-3.5 w-3.5 text-gray-600" />
          </button>
        </div>
      </div>
    </div>
  );

  // Seed handler
  const handleSeedData = async () => {
    setSeeding(true);
    try {
      const response = await inboundApi.seedSampleTickets();
      if (response.data?.success) await loadTickets();
    } catch (err) {
      console.error('Failed to seed tickets:', err);
      setError('Failed to create sample data. The database table may need to be created first.');
    } finally {
      setSeeding(false);
    }
  };

  // Loading state
  if (loading) {
    return (
      <div className="flex items-center justify-center py-32">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-4 border-theme-primary border-t-transparent mx-auto"></div>
          <p className="mt-4 text-gray-500">Loading enquiries...</p>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="flex items-center justify-center py-32">
        <div className="text-center max-w-md">
          <ExclamationTriangleIcon className="h-12 w-12 text-red-500 mx-auto" />
          <h3 className="mt-4 text-lg font-bold text-gray-900">Error Loading Enquiries</h3>
          <p className="mt-2 text-gray-500">{error}</p>
          <div className="mt-4 flex gap-3 justify-center">
            <button onClick={loadTickets} className="btn-primary inline-flex items-center text-sm">
              <ArrowPathIcon className="h-4 w-4 mr-1.5" /> Try Again
            </button>
            <button onClick={() => navigate(-1)} className="btn-secondary text-sm">Go Back</button>
          </div>
        </div>
      </div>
    );
  }

  // Empty state
  if (tickets.length === 0) {
    return (
      <div className="flex items-center justify-center py-32">
        <div className="text-center max-w-md">
          <div className="bg-green-50 rounded-full w-16 h-16 flex items-center justify-center mx-auto">
            <CheckCircleIcon className="h-8 w-8 text-green-600" />
          </div>
          <h3 className="mt-4 text-xl font-bold text-gray-900">All Caught Up!</h3>
          <p className="mt-2 text-gray-500 text-sm">
            {warning
              ? 'The enquiries table needs to be set up. Run migration 016_inbound_tickets.sql then seed sample data.'
              : 'No pending enquiries to triage. Seed sample data for testing or wait for new ones.'}
          </p>
          <div className="mt-4 flex flex-col sm:flex-row justify-center gap-2">
            <button onClick={handleSeedData} disabled={seeding} className="btn-primary inline-flex items-center justify-center text-sm">
              {seeding
                ? <><ArrowPathIcon className="h-4 w-4 mr-1.5 animate-spin" /> Creating...</>
                : <><SparklesIcon className="h-4 w-4 mr-1.5" /> Seed Sample Enquiries</>
              }
            </button>
            <button onClick={loadTickets} className="btn-secondary inline-flex items-center justify-center text-sm">
              <ArrowPathIcon className="h-4 w-4 mr-1.5" /> Refresh
            </button>
          </div>
          {warning && (
            <div className="mt-4 p-3 bg-amber-50 border border-amber-200 rounded-lg text-xs text-amber-700">{warning}</div>
          )}
        </div>
      </div>
    );
  }

  const priority = priorityConfig[currentTicket?.priority] || priorityConfig.normal;

  return (
    <div className="space-y-4">
      {/* Notification Toast */}
      {notification && (
        <div className={`fixed top-4 left-1/2 -translate-x-1/2 z-50 px-4 py-2.5 rounded-lg shadow-lg flex items-center gap-2 text-sm font-medium ${
          notification.type === 'error' ? 'bg-red-500 text-white' :
          notification.type === 'warning' ? 'bg-amber-500 text-white' :
          'bg-green-500 text-white'
        }`}>
          {notification.type === 'error'
            ? <ExclamationTriangleIcon className="h-4 w-4" />
            : <CheckCircleIcon className="h-4 w-4" />}
          {notification.message}
          <button onClick={() => setNotification(null)} className="ml-2 hover:opacity-80">
            <XMarkIcon className="h-3.5 w-3.5" />
          </button>
        </div>
      )}

      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Enquiry Triage</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            Review incoming enquiries and create quotes
          </p>
        </div>
        <div className="flex items-center gap-2">
          {/* Ticket Navigation */}
          <div className="flex items-center bg-gray-100 rounded-lg">
            <button
              onClick={handlePrevious}
              disabled={currentIndex === 0 || processing}
              className="p-2 text-gray-600 hover:text-gray-900 disabled:opacity-30 disabled:cursor-not-allowed rounded-l-lg hover:bg-gray-200 transition-colors"
            >
              <ChevronLeftIcon className="h-4 w-4" />
            </button>
            <span className="px-3 py-1.5 text-sm font-medium text-gray-700 tabular-nums">
              {currentIndex + 1} <span className="text-gray-400">/</span> {tickets.length}
            </span>
            <button
              onClick={handleSkip}
              disabled={tickets.length <= 1 || processing}
              className="p-2 text-gray-600 hover:text-gray-900 disabled:opacity-30 disabled:cursor-not-allowed rounded-r-lg hover:bg-gray-200 transition-colors"
            >
              <ChevronRightIcon className="h-4 w-4" />
            </button>
          </div>
          <button
            onClick={loadTickets}
            className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
            title="Refresh"
          >
            <ArrowPathIcon className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Keyboard shortcuts bar */}
      <div className="flex items-center gap-4 text-xs text-gray-400">
        <span><kbd className="px-1.5 py-0.5 bg-gray-100 border border-gray-200 rounded text-[10px] font-mono">A</kbd> Accept</span>
        <span><kbd className="px-1.5 py-0.5 bg-gray-100 border border-gray-200 rounded text-[10px] font-mono">R</kbd> Reject</span>
        <span><kbd className="px-1.5 py-0.5 bg-gray-100 border border-gray-200 rounded text-[10px] font-mono">S</kbd> Skip</span>
        <span><kbd className="px-1.5 py-0.5 bg-gray-100 border border-gray-200 rounded text-[10px] font-mono">&larr;</kbd><kbd className="px-1.5 py-0.5 bg-gray-100 border border-gray-200 rounded text-[10px] font-mono">&rarr;</kbd> Navigate</span>
      </div>

      {/* Stats Bar */}
      <div className="flex items-center gap-6 text-sm">
        <div className="flex items-center gap-1.5">
          <span className="inline-block w-2 h-2 rounded-full bg-amber-400"></span>
          <span className="text-gray-600"><span className="font-semibold text-gray-900">{stats.open}</span> Pending</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="inline-block w-2 h-2 rounded-full bg-green-400"></span>
          <span className="text-gray-600"><span className="font-semibold text-gray-900">{stats.processed}</span> Processed</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="inline-block w-2 h-2 rounded-full bg-gray-300"></span>
          <span className="text-gray-600"><span className="font-semibold text-gray-900">{stats.total}</span> Total</span>
        </div>
      </div>

      {/* Split View */}
      <div className="flex gap-5 items-start">
        {/* Left Panel — Email Content (65%) */}
        <div className="w-[65%] min-w-0">
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
            {/* Email Header */}
            <div className="px-6 py-4 border-b border-gray-100">
              <div className="flex items-start justify-between gap-4">
                <div className="min-w-0">
                  <h2 className="text-lg font-semibold text-gray-900 truncate">
                    {currentTicket.subject || 'No Subject'}
                  </h2>
                  <div className="flex items-center gap-3 mt-1.5 text-sm text-gray-500">
                    <span className="flex items-center gap-1">
                      <UserIcon className="h-3.5 w-3.5" />
                      {currentTicket.customer_name || 'Unknown'}
                    </span>
                    <span className="flex items-center gap-1">
                      <EnvelopeIcon className="h-3.5 w-3.5" />
                      {currentTicket.customer_email}
                    </span>
                  </div>
                </div>
                <div className="flex items-center gap-2 flex-shrink-0">
                  <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold border ${priority.bg}`}>
                    {(currentTicket.priority || 'normal').toUpperCase()}
                  </span>
                </div>
              </div>
              <div className="flex items-center gap-3 mt-2 text-xs text-gray-400">
                <span className="flex items-center gap-1">
                  <ClockIcon className="h-3 w-3" />
                  {formatTimeAgo(currentTicket.created_at)}
                </span>
                <span className="flex items-center gap-1">
                  via {sourceLabels[currentTicket.source] || currentTicket.source}
                </span>
                <span className="font-mono text-gray-300">{currentTicket.ticket_id}</span>
              </div>
            </div>

            {/* Email Body */}
            <div className="px-6 py-5 min-h-[350px] max-h-[60vh] overflow-y-auto">
              <p className="text-gray-700 whitespace-pre-wrap leading-relaxed text-[15px]">
                {currentTicket.message || 'No message content'}
              </p>
            </div>
          </div>
        </div>

        {/* Right Panel — Details & Actions (35%) */}
        <div className="w-[35%] space-y-4">
          {/* Customer Info */}
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5">
            <h3 className="text-sm font-semibold text-gray-900 mb-3 flex items-center gap-1.5">
              <UserIcon className="h-4 w-4 text-gray-400" />
              Customer
            </h3>
            <div className="space-y-2.5">
              <div>
                <p className="text-xs text-gray-500">Name</p>
                <p className="text-sm font-medium text-gray-900">{currentTicket.customer_name || 'Unknown'}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500">Email</p>
                <p className="text-sm font-medium text-gray-900 truncate">{currentTicket.customer_email}</p>
              </div>
              <div className="flex gap-4">
                <div>
                  <p className="text-xs text-gray-500">Source</p>
                  <p className="text-sm font-medium text-gray-900">{sourceLabels[currentTicket.source] || currentTicket.source}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-500">Priority</p>
                  <div className="flex items-center gap-1.5 mt-0.5">
                    <span className={`w-2 h-2 rounded-full ${priority.dot}`}></span>
                    <span className="text-sm font-medium text-gray-900 capitalize">{currentTicket.priority || 'normal'}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* AI-Detected Details (Structured Inputs) */}
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5">
            <h3 className="text-sm font-semibold text-gray-900 mb-3 flex items-center gap-1.5">
              <SparklesIcon className="h-4 w-4 text-theme-primary" />
              Travel Details
            </h3>
            <div className="space-y-3">
              {/* Destination */}
              <div className="flex items-start gap-3">
                <div className="mt-0.5 text-theme-primary"><MapPinIcon className="h-4 w-4" /></div>
                <div className="flex-1 min-w-0">
                  <p className="text-xs text-gray-500 mb-0.5">Destination</p>
                  <input
                    type="text"
                    className="w-full text-sm font-medium bg-white border border-gray-300 rounded px-2 py-1.5 focus:outline-none focus:ring-1 focus:ring-theme-primary focus:border-theme-primary"
                    value={editableDetails.destination}
                    onChange={(e) => setEditableDetails(prev => ({ ...prev, destination: e.target.value }))}
                    placeholder="e.g. Zanzibar"
                  />
                </div>
              </div>
              {/* Preferred Hotel */}
              <div className="flex items-start gap-3">
                <div className="mt-0.5 text-theme-primary"><BuildingOfficeIcon className="h-4 w-4" /></div>
                <div className="flex-1 min-w-0">
                  <p className="text-xs text-gray-500 mb-0.5">Preferred Hotel</p>
                  <input type="text"
                    className="w-full text-sm font-medium bg-white border border-gray-300 rounded px-2 py-1.5 focus:outline-none focus:ring-1 focus:ring-theme-primary focus:border-theme-primary"
                    value={editableDetails.requested_hotel}
                    onChange={(e) => setEditableDetails(prev => ({ ...prev, requested_hotel: e.target.value }))}
                    placeholder="e.g. Hilton Mauritius"
                  />
                </div>
              </div>
              {/* Check-in / Check-out */}
              <div className="flex items-start gap-3">
                <div className="mt-0.5 text-theme-primary"><CalendarIcon className="h-4 w-4" /></div>
                <div className="flex-1 min-w-0">
                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <p className="text-xs text-gray-500 mb-0.5">Check-in</p>
                      <input
                        type="date"
                        className="w-full text-sm bg-white border border-gray-300 rounded px-2 py-1.5 focus:outline-none focus:ring-1 focus:ring-theme-primary focus:border-theme-primary"
                        value={editableDetails.check_in}
                        onChange={(e) => setEditableDetails(prev => ({ ...prev, check_in: e.target.value }))}
                      />
                    </div>
                    <div>
                      <p className="text-xs text-gray-500 mb-0.5">Check-out</p>
                      <input
                        type="date"
                        className="w-full text-sm bg-white border border-gray-300 rounded px-2 py-1.5 focus:outline-none focus:ring-1 focus:ring-theme-primary focus:border-theme-primary"
                        value={editableDetails.check_out}
                        min={editableDetails.check_in || undefined}
                        onChange={(e) => setEditableDetails(prev => ({ ...prev, check_out: e.target.value }))}
                      />
                    </div>
                  </div>
                </div>
              </div>
              {/* Room Configuration */}
              <div className="space-y-3">
                <p className="text-xs text-gray-500 ml-7">Rooms & Guests</p>
                {editableDetails.rooms.map((room, idx) => (
                  <div key={idx} className="ml-7 p-3 bg-gray-50 rounded-lg border border-gray-200">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium text-gray-700">Room {idx + 1}</span>
                      {editableDetails.rooms.length > 1 && (
                        <button onClick={() => setEditableDetails(prev => {
                          const rooms = prev.rooms.filter((_, i) => i !== idx);
                          const newTotalChildren = rooms.reduce((s, r) => s + r.children, 0);
                          const ages = [...prev.children_ages];
                          while (ages.length < newTotalChildren) ages.push(8);
                          return { ...prev, rooms, children_ages: ages.slice(0, newTotalChildren) };
                        })} className="text-xs text-red-500 hover:text-red-700">Remove</button>
                      )}
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                      <Stepper label="Adults" icon={null} value={room.adults} min={1} max={6}
                        onChange={(v) => setEditableDetails(prev => {
                          const rooms = [...prev.rooms];
                          rooms[idx] = { ...rooms[idx], adults: v };
                          return { ...prev, rooms };
                        })} />
                      <Stepper label="Children" icon={null} value={room.children} min={0} max={4}
                        onChange={(v) => setEditableDetails(prev => {
                          const rooms = [...prev.rooms];
                          rooms[idx] = { ...rooms[idx], children: v };
                          const newTotalChildren = rooms.reduce((s, r) => s + r.children, 0);
                          const ages = [...prev.children_ages];
                          while (ages.length < newTotalChildren) ages.push(8);
                          return { ...prev, rooms, children_ages: ages.slice(0, newTotalChildren) };
                        })} />
                    </div>
                  </div>
                ))}
                {editableDetails.rooms.length < 4 && (
                  <button onClick={() => setEditableDetails(prev => ({
                    ...prev, rooms: [...prev.rooms, { adults: 2, children: 0 }]
                  }))} className="ml-7 w-[calc(100%-1.75rem)] py-1.5 text-xs text-theme-primary font-medium border border-dashed border-gray-300 rounded-lg hover:border-theme-primary">
                    + Add room
                  </button>
                )}
              </div>
              {totalChildren > 0 && (
                <div className="ml-7 mt-2">
                  <p className="text-xs text-gray-500 mb-1">Children Ages</p>
                  <div className="flex flex-wrap gap-2">
                    {editableDetails.children_ages.map((age, i) => (
                      <select key={i} value={age}
                        onChange={(e) => {
                          const ages = [...editableDetails.children_ages];
                          ages[i] = parseInt(e.target.value);
                          setEditableDetails(prev => ({ ...prev, children_ages: ages }));
                        }}
                        className="w-16 text-sm border border-gray-300 rounded px-1.5 py-1">
                        {Array.from({ length: 18 }, (_, a) => (
                          <option key={a} value={a}>{a}</option>
                        ))}
                      </select>
                    ))}
                  </div>
                </div>
              )}
              {/* Budget */}
              <div className="flex items-start gap-3">
                <div className="mt-0.5 text-theme-primary"><CurrencyDollarIcon className="h-4 w-4" /></div>
                <div className="flex-1 min-w-0">
                  <p className="text-xs text-gray-500 mb-0.5">Budget (ZAR)</p>
                  <input
                    type="text"
                    className="w-full text-sm font-medium bg-white border border-gray-300 rounded px-2 py-1.5 focus:outline-none focus:ring-1 focus:ring-theme-primary focus:border-theme-primary"
                    value={editableDetails.budget}
                    onChange={(e) => setEditableDetails(prev => ({ ...prev, budget: e.target.value }))}
                    placeholder="e.g. 50000"
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5 space-y-2.5">
            <button
              onClick={handleAccept}
              disabled={processing}
              className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-green-600 text-white text-sm font-medium hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors shadow-sm"
            >
              {processing ? (
                <>
                  <ArrowPathIcon className="h-4 w-4 animate-spin" />
                  Creating Draft...
                </>
              ) : (
                <>
                  <CheckIcon className="h-4 w-4" />
                  Accept & Create Quote
                </>
              )}
            </button>
            <button
              onClick={handleReject}
              disabled={processing}
              className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-red-50 text-red-700 text-sm font-medium hover:bg-red-100 border border-red-200 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <XMarkIcon className="h-4 w-4" />
              Reject Enquiry
            </button>
            <button
              onClick={handleSkip}
              disabled={processing}
              className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-gray-50 text-gray-700 text-sm font-medium hover:bg-gray-100 border border-gray-200 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <ForwardIcon className="h-4 w-4" />
              Skip for Later
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
