import { useState, useRef, useEffect, useCallback } from 'react';
import { useAuth } from '../../context/AuthContext';
import { helpdeskApi } from '../../services/api';
import { normalizeKbSource } from '../../utils/fieldTransformers';
import DegradedServiceBanner from '../ui/DegradedServiceBanner';
import {
  PaperAirplaneIcon,
  SparklesIcon,
  UserCircleIcon,
  DocumentTextIcon,
  ArrowPathIcon,
  LightBulbIcon,
  XMarkIcon,
  GlobeAltIcon,
} from '@heroicons/react/24/outline';

// Suggested questions for quick access
const SUGGESTED_QUESTIONS = [
  "What's the best time to visit Zanzibar?",
  "How do I create a new quote?",
  "Tell me about Mauritius hotels",
  "What are the different pipeline stages?",
];

// User-friendly labels for response methods
const METHOD_LABELS = {
  dual_kb: 'Knowledge Base',
  private_kb_synthesis: 'Your Documents',
  smart_static: 'Help Guide',
  llm_synthesis: 'AI Generated',
  llm_synthesis_web: 'AI + Web Search',
  static_fallback: 'Help Guide',
};

function Message({ message, isUser }) {
  return (
    <div className={`flex gap-2 ${isUser ? 'flex-row-reverse' : ''}`}>
      {/* Avatar */}
      <div className={`flex-shrink-0 w-7 h-7 rounded-full flex items-center justify-center ${
        isUser ? 'bg-theme-primary/20' : 'bg-gradient-to-br from-purple-500 to-indigo-600'
      }`}>
        {isUser ? (
          <UserCircleIcon className="w-4 h-4 text-theme-primary" />
        ) : (
          <SparklesIcon className="w-3 h-3 text-white" />
        )}
      </div>

      {/* Message Content */}
      <div className={`max-w-[85%] ${isUser ? 'text-right' : ''}`}>
        {/* Degraded service banner (for AI responses with circuit breaker metadata) */}
        {!isUser && message.serviceStatus?.degraded && (
          <DegradedServiceBanner status={message.serviceStatus} />
        )}
        <div className={`inline-block px-3 py-2 rounded-2xl ${
          isUser
            ? 'bg-theme-primary text-white rounded-tr-sm'
            : 'bg-theme-surface-elevated text-theme rounded-tl-sm'
        }`}>
          <p className="text-sm whitespace-pre-wrap">{message.content}</p>
        </div>

        {/* Sources (for AI responses) */}
        {!isUser && message.sources && message.sources.length > 0 && (
          <div className="mt-1.5 space-y-0.5">
            <p className="text-xs text-theme-muted">Sources:</p>
            {message.sources.slice(0, 4).map((rawSource, idx) => {
              const source = normalizeKbSource(rawSource);
              return (
                <div key={idx} className="flex items-center gap-1 text-xs text-theme-muted">
                  {rawSource.type === 'web_search' ? (
                    <GlobeAltIcon className="w-3 h-3 text-blue-400" />
                  ) : (
                    <DocumentTextIcon className="w-3 h-3" />
                  )}
                  <span className="truncate">{source.title}</span>
                </div>
              );
            })}
          </div>
        )}

        {/* Response method badge */}
        {!isUser && message.method && (
          <span className="text-xs text-theme-muted opacity-50">
            {METHOD_LABELS[message.method] || ''}
          </span>
        )}

        <p className="text-xs text-theme-muted mt-0.5">
          {new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </p>
      </div>
    </div>
  );
}

function TypingIndicator() {
  return (
    <div className="flex gap-2">
      <div className="flex-shrink-0 w-7 h-7 rounded-full bg-gradient-to-br from-purple-500 to-indigo-600 flex items-center justify-center">
        <SparklesIcon className="w-3 h-3 text-white" />
      </div>
      <div className="bg-theme-surface-elevated px-3 py-2 rounded-2xl rounded-tl-sm">
        <div className="flex gap-1">
          <span className="w-1.5 h-1.5 bg-theme-muted rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></span>
          <span className="w-1.5 h-1.5 bg-theme-muted rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></span>
          <span className="w-1.5 h-1.5 bg-theme-muted rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></span>
        </div>
      </div>
    </div>
  );
}

// Helper function to generate helpful responses when no knowledge base results
function generateHelpResponse(question) {
  const lowerQuestion = question.toLowerCase();

  if (lowerQuestion.includes('quote') && (lowerQuestion.includes('create') || lowerQuestion.includes('new'))) {
    return "To create a new quote:\n\n1. Go to **Quotes** in the sidebar\n2. Click **New Quote**\n3. Fill in customer details\n4. Click **Generate Quote**";
  }

  if (lowerQuestion.includes('client') && (lowerQuestion.includes('add') || lowerQuestion.includes('new'))) {
    return "To add a client:\n\n1. Go to **CRM** > **All Clients**\n2. Click **Add Client**\n3. Enter their details\n4. Click **Save**";
  }

  if (lowerQuestion.includes('pipeline')) {
    return "The Pipeline shows clients by stage:\n\n- **Quoted**: Has a quote\n- **Negotiating**: In discussion\n- **Booked**: Confirmed\n- **Paid**: Payment received\n\nDrag clients between stages to update.";
  }

  if (lowerQuestion.includes('invoice')) {
    return "To create an invoice:\n\n1. Go to **Invoices**\n2. Click **Create Invoice**\n3. Add line items and details\n4. Click **Generate**";
  }

  return "I can help with:\n\n- **Quotes** - Creating and sending\n- **CRM** - Managing clients\n- **Invoices** - Billing\n- **Settings** - Configuration\n\nWhat would you like to know more about?";
}

export default function HelpDeskPanel({ isOpen, onClose }) {
  const { user } = useAuth();
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  // Initialize messages when panel opens for first time
  useEffect(() => {
    if (isOpen && messages.length === 0) {
      setMessages([
        {
          id: 1,
          role: 'assistant',
          content: `Hi ${user?.name?.split(' ')[0] || 'there'}! I'm your AI assistant. How can I help you today?`,
          timestamp: new Date().toISOString(),
        }
      ]);
    }
  }, [isOpen, user, messages.length]);

  // Auto-scroll to bottom
  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading, scrollToBottom]);

  // Focus input when panel opens
  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  }, [isOpen]);

  // Handle escape key to close
  useEffect(() => {
    const handleEscape = (e) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleEscape);
    return () => window.removeEventListener('keydown', handleEscape);
  }, [isOpen, onClose]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage = {
      id: Date.now(),
      role: 'user',
      content: input.trim(),
      timestamp: new Date().toISOString(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      const response = await helpdeskApi.ask(userMessage.content);
      let assistantContent = '';
      let sources = [];

      if (response.data?.success && response.data?.answer) {
        assistantContent = response.data.answer;
        if (response.data.sources) {
          sources = response.data.sources;
        }
      } else {
        assistantContent = generateHelpResponse(userMessage.content);
      }

      const assistantMessage = {
        id: Date.now() + 1,
        role: 'assistant',
        content: assistantContent,
        sources: sources.length > 0 ? sources : undefined,
        method: response.data.method || null,
        serviceStatus: response.data._service_status || null,
        timestamp: new Date().toISOString(),
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Helpdesk error:', error);
      const errorMessage = {
        id: Date.now() + 1,
        role: 'assistant',
        content: generateHelpResponse(userMessage.content),
        timestamp: new Date().toISOString(),
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSuggestedQuestion = (question) => {
    setInput(question);
    inputRef.current?.focus();
  };

  const clearChat = () => {
    setMessages([
      {
        id: Date.now(),
        role: 'assistant',
        content: `Hi ${user?.name?.split(' ')[0] || 'there'}! I'm your AI assistant. How can I help you today?`,
        timestamp: new Date().toISOString(),
      }
    ]);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[60]">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/30 animate-backdrop"
        onClick={onClose}
      />

      {/* Panel */}
      <div className="absolute right-0 top-0 h-full w-full max-w-md bg-theme-surface shadow-2xl border-l border-theme animate-slide-panel flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-theme bg-theme-surface-elevated">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-purple-500 to-indigo-600 flex items-center justify-center">
              <SparklesIcon className="w-4 h-4 text-white" />
            </div>
            <div>
              <h2 className="font-semibold text-theme">AI Helpdesk</h2>
              <p className="text-xs text-theme-muted">Powered by Knowledge Base</p>
            </div>
          </div>
          <div className="flex items-center gap-1">
            <button
              onClick={clearChat}
              className="p-2 text-theme-muted hover:text-theme hover:bg-theme-border-light rounded-lg transition-colors"
              title="New chat"
            >
              <ArrowPathIcon className="w-4 h-4" />
            </button>
            <button
              onClick={onClose}
              className="p-2 text-theme-muted hover:text-theme hover:bg-theme-border-light rounded-lg transition-colors"
            >
              <XMarkIcon className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Messages Area */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {messages.map((message) => (
            <Message
              key={message.id}
              message={message}
              isUser={message.role === 'user'}
            />
          ))}
          {isLoading && <TypingIndicator />}
          <div ref={messagesEndRef} />
        </div>

        {/* Suggested Questions (only show when few messages) */}
        {messages.length <= 2 && (
          <div className="px-4 pb-2">
            <div className="flex items-center gap-1.5 mb-2">
              <LightBulbIcon className="w-3.5 h-3.5 text-amber-500" />
              <span className="text-xs text-theme-muted">Try asking:</span>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {SUGGESTED_QUESTIONS.map((question, idx) => (
                <button
                  key={idx}
                  onClick={() => handleSuggestedQuestion(question)}
                  className="px-2.5 py-1 text-xs bg-theme-surface-elevated text-theme-secondary rounded-full hover:bg-theme-border-light transition-colors"
                >
                  {question}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Input Area */}
        <div className="border-t border-theme p-3 bg-theme-surface">
          <form onSubmit={handleSubmit} className="flex gap-2">
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask a question..."
              className="flex-1 px-3 py-2 text-sm bg-theme-surface-elevated border border-theme-border rounded-xl focus:outline-none focus:ring-2 focus:ring-theme-primary/50 text-theme placeholder:text-theme-muted"
              disabled={isLoading}
            />
            <button
              type="submit"
              disabled={!input.trim() || isLoading}
              className="px-3 py-2 bg-theme-primary text-white rounded-xl hover:bg-theme-primary-dark disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <PaperAirplaneIcon className="w-4 h-4" />
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
