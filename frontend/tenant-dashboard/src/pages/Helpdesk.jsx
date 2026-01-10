import { useState, useRef, useEffect, useCallback } from 'react';
import { useAuth } from '../context/AuthContext';
import { helpdeskApi } from '../services/api';
import {
  PaperAirplaneIcon,
  SparklesIcon,
  UserCircleIcon,
  DocumentTextIcon,
  ArrowPathIcon,
  LightBulbIcon,
  QuestionMarkCircleIcon,
} from '@heroicons/react/24/outline';

// Suggested questions for quick access
const SUGGESTED_QUESTIONS = [
  "How do I create a new quote?",
  "How do I add a client to the CRM?",
  "What are the different pipeline stages?",
  "How do I generate an invoice from a quote?",
  "How do I update pricing rates?",
];

function Message({ message, isUser }) {
  return (
    <div className={`flex gap-3 ${isUser ? 'flex-row-reverse' : ''}`}>
      {/* Avatar */}
      <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
        isUser ? 'bg-primary-100' : 'bg-gradient-to-br from-purple-500 to-indigo-600'
      }`}>
        {isUser ? (
          <UserCircleIcon className="w-5 h-5 text-primary-600" />
        ) : (
          <SparklesIcon className="w-4 h-4 text-white" />
        )}
      </div>

      {/* Message Content */}
      <div className={`max-w-[80%] ${isUser ? 'text-right' : ''}`}>
        <div className={`inline-block px-4 py-2 rounded-2xl ${
          isUser
            ? 'bg-primary-600 text-white rounded-tr-md'
            : 'bg-gray-100 text-gray-800 rounded-tl-md'
        }`}>
          <p className="text-sm whitespace-pre-wrap">{message.content}</p>
        </div>

        {/* Sources (for AI responses) */}
        {!isUser && message.sources && message.sources.length > 0 && (
          <div className="mt-2 space-y-1">
            <p className="text-xs text-gray-500">Sources:</p>
            {message.sources.map((source, idx) => (
              <div key={idx} className="flex items-center gap-1 text-xs text-gray-500">
                <DocumentTextIcon className="w-3 h-3" />
                <span className="truncate">{source.title || source.filename || 'Document'}</span>
                {source.score && (
                  <span className="text-gray-400">({Math.round(source.score * 100)}% match)</span>
                )}
              </div>
            ))}
          </div>
        )}

        <p className="text-xs text-gray-400 mt-1">
          {new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </p>
      </div>
    </div>
  );
}

function TypingIndicator() {
  return (
    <div className="flex gap-3">
      <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gradient-to-br from-purple-500 to-indigo-600 flex items-center justify-center">
        <SparklesIcon className="w-4 h-4 text-white" />
      </div>
      <div className="bg-gray-100 px-4 py-2 rounded-2xl rounded-tl-md">
        <div className="flex gap-1">
          <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></span>
          <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></span>
          <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></span>
        </div>
      </div>
    </div>
  );
}

export default function Helpdesk() {
  const { user } = useAuth();
  const [messages, setMessages] = useState([
    {
      id: 1,
      role: 'assistant',
      content: `Hi ${user?.name?.split(' ')[0] || 'there'}! I'm your Zorah platform assistant. I can help you with:\n\n- **Platform features** - How to use quotes, CRM, invoices, and more\n- **Best practices** - Tips for managing clients and bookings\n- **Troubleshooting** - Common issues and solutions\n\nWhat can I help you with today?`,
      timestamp: new Date().toISOString(),
    }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  // Auto-scroll to bottom when new messages arrive
  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading, scrollToBottom]);

  // Focus input on mount
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

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
      // Try centralized Zorah helpdesk API first
      const response = await helpdeskApi.ask(userMessage.content);
      let assistantContent = '';
      let sources = [];

      if (response.data?.success && response.data?.answer) {
        // Use response from centralized helpdesk
        assistantContent = response.data.answer;
        if (response.data.sources) {
          sources = response.data.sources;
        }
      } else {
        // Fallback to local help response generator
        assistantContent = generateHelpResponse(userMessage.content);
      }

      const assistantMessage = {
        id: Date.now() + 1,
        role: 'assistant',
        content: assistantContent,
        sources: sources.length > 0 ? sources : undefined,
        timestamp: new Date().toISOString(),
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Failed to get response:', error);

      // Provide fallback response on error
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
        content: `Hi ${user?.name?.split(' ')[0] || 'there'}! I'm your AI assistant. I can help you with questions about the platform, finding information in your knowledge base, and guiding you through common tasks.\n\nWhat can I help you with today?`,
        timestamp: new Date().toISOString(),
      }
    ]);
  };

  return (
    <div className="h-[calc(100vh-8rem)] flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">AI Helpdesk</h1>
          <p className="text-gray-500">Get help with platform features, best practices, and troubleshooting</p>
        </div>
        <button
          onClick={clearChat}
          className="btn-secondary flex items-center gap-2"
        >
          <ArrowPathIcon className="w-4 h-4" />
          New Chat
        </button>
      </div>

      {/* Chat Container */}
      <div className="flex-1 bg-white rounded-xl border border-gray-200 flex flex-col overflow-hidden">
        {/* Messages Area */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
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
            <div className="flex items-center gap-2 mb-2">
              <LightBulbIcon className="w-4 h-4 text-amber-500" />
              <span className="text-xs text-gray-500">Suggested questions:</span>
            </div>
            <div className="flex flex-wrap gap-2">
              {SUGGESTED_QUESTIONS.map((question, idx) => (
                <button
                  key={idx}
                  onClick={() => handleSuggestedQuestion(question)}
                  className="px-3 py-1.5 text-sm bg-gray-100 text-gray-700 rounded-full hover:bg-gray-200 transition-colors"
                >
                  {question}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Input Area */}
        <div className="border-t border-gray-200 p-4">
          <form onSubmit={handleSubmit} className="flex gap-3">
            <div className="flex-1 relative">
              <input
                ref={inputRef}
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Ask a question..."
                className="w-full px-4 py-3 pr-12 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                disabled={isLoading}
              />
              <QuestionMarkCircleIcon className="absolute right-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
            </div>
            <button
              type="submit"
              disabled={!input.trim() || isLoading}
              className="px-4 py-3 bg-primary-600 text-white rounded-xl hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <PaperAirplaneIcon className="w-5 h-5" />
            </button>
          </form>
          <p className="text-xs text-gray-400 mt-2 text-center">
            Powered by Zorah AI - Centralized platform support
          </p>
        </div>
      </div>
    </div>
  );
}

// Helper function to generate helpful responses when no knowledge base results
function generateHelpResponse(question) {
  const lowerQuestion = question.toLowerCase();

  // Quote-related
  if (lowerQuestion.includes('quote') && (lowerQuestion.includes('create') || lowerQuestion.includes('new') || lowerQuestion.includes('make'))) {
    return "To create a new quote:\n\n1. Go to **Quotes** in the sidebar\n2. Click **New Quote** button\n3. Fill in the customer details and travel requirements\n4. Add destinations and accommodations\n5. Click **Generate Quote** to create the PDF\n\nThe quote will be automatically saved and can be sent to the customer via email.";
  }

  if (lowerQuestion.includes('quote') && lowerQuestion.includes('send')) {
    return "To send a quote to a customer:\n\n1. Go to **Quotes** and find the quote\n2. Click on the quote to open details\n3. Click the **Send Quote** button\n4. Verify the recipient email and click confirm\n\nThe customer will receive an email with the quote PDF attached.";
  }

  // Client/CRM related
  if (lowerQuestion.includes('client') && (lowerQuestion.includes('add') || lowerQuestion.includes('create') || lowerQuestion.includes('new'))) {
    return "To add a new client:\n\n1. Go to **CRM** > **All Clients**\n2. Click the **Add Client** button\n3. Enter the client's name, email, and phone number\n4. Select the source (e.g., Website, Referral)\n5. Click **Save**\n\nThe client will appear in your CRM and can be associated with quotes and invoices.";
  }

  if (lowerQuestion.includes('pipeline')) {
    return "The Pipeline view shows your clients organized by their journey stage:\n\n- **Quoted**: Client has received a quote\n- **Negotiating**: Discussing terms or options\n- **Booked**: Travel has been confirmed\n- **Paid**: Payment received\n- **Travelled**: Trip completed\n- **Lost**: Didn't proceed\n\nYou can drag clients between stages to update their status.";
  }

  // Invoice related
  if (lowerQuestion.includes('invoice')) {
    return "To create an invoice:\n\n1. Go to **Invoices** in the sidebar\n2. Click **Create Invoice**\n3. You can create from an existing quote or manually\n4. Add line items, set due date, and payment terms\n5. Click **Generate Invoice**\n\nInvoices can be sent directly to customers and tracked for payment status.";
  }

  // Pricing related
  if (lowerQuestion.includes('pricing') || lowerQuestion.includes('rate')) {
    return "To manage pricing:\n\n1. Go to **Pricing Guide** in the sidebar\n2. Use **Rates** to view and update accommodation rates\n3. Use **Hotels** to browse properties and their pricing\n4. Click on any rate to edit dates, prices, or availability\n\nRates are automatically used when generating quotes.";
  }

  // Settings related
  if (lowerQuestion.includes('setting') || lowerQuestion.includes('brand') || lowerQuestion.includes('logo')) {
    return "To customize your settings:\n\n1. Go to **Settings** in the sidebar\n2. Use different tabs to configure:\n   - **Profile**: Your personal info\n   - **Company**: Business details and banking\n   - **Branding**: Logo, colors, and themes\n   - **Notifications**: Email preferences\n   - **Integrations**: Connected services\n\nAll changes are saved automatically.";
  }

  // Default response
  return "I can help you with:\n\n- **Quotes**: Creating, sending, and managing travel quotes\n- **CRM**: Adding clients and managing the sales pipeline\n- **Invoices**: Generating and tracking invoices\n- **Pricing**: Managing accommodation rates\n- **Settings**: Customizing your platform\n\nCould you provide more details about what you're trying to do?";
}
