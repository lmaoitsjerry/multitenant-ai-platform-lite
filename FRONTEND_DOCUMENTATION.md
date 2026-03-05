# Complete Frontend Documentation
## Multitenant AI Platform - Frontend Map

**Purpose**: This document serves as a complete blueprint for understanding and replicating the frontend architecture. It covers every page, component, button, API call, form, modal, and user interaction in the system.

---

## Architecture Overview

### Technology Stack
```
Framework:        React 19+ with React Router v7+
Build Tool:       Vite 7.2.0
Styling:          Tailwind CSS 3.4/4.1
Icons:            Heroicons
State:            React Context API
HTTP Client:      Axios with interceptors
Authentication:   JWT with refresh tokens
Multi-tenant:     X-Client-ID header injection
```

### Frontend Applications
```
tenant-dashboard/     Port 5173 - Main customer-facing SaaS application
internal-admin/       Port 5180 - Internal admin panel (no auth required)
```

---

# TENANT DASHBOARD APPLICATION

## 1. PAGES & ROUTES

```
/login                    Public     Login page with email/password
/forgot-password          Public     Password reset request
/reset-password           Public     Password reset form (with token)
/accept-invite            Public     Accept team invitation
/onboarding               Public     New tenant onboarding wizard
/                         Protected  Dashboard (redirects from /dashboard)
/quotes                   Protected  Quotes list with filters
/quotes/new               Protected  Multi-step quote generation wizard
/quotes/:id               Protected  Quote detail with PDF preview
/invoices                 Protected  Invoices list with status filters
/invoices/new             Protected  Create new invoice
/invoices/:id             Protected  Invoice detail with payment tracking
/crm/clients              Protected  Client list with search
/crm/clients/:id          Protected  Client detail with activity timeline
/crm/pipeline             Protected  Kanban-style sales pipeline
/pricing/rates            Protected  Hotel rates table with filters
/pricing/hotels           Protected  Hotels grouped by destination
/pricing/hotels/:name     Protected  Individual hotel rates detail
/analytics                Protected  Business analytics dashboard
/helpdesk                 Protected  AI-powered help chat interface
/knowledge                Protected  Knowledge base document manager
/settings                 Protected  Multi-tab settings page
/settings/team            Admin      Team member management
/settings/privacy         Protected  GDPR/POPIA privacy controls
```

---

## 2. PAGE DETAILS

### /login - Login Page
```
Purpose: User authentication entry point

Components:
├── Logo (tenant-branded or default)
├── Email input field
├── Password input field
├── "Remember me" checkbox (optional)
├── "Forgot password?" link
├── "Sign In" button
└── Background image (branded)

State:
├── email: string
├── password: string
├── loading: boolean
├── error: string | null

API Calls:
├── POST /api/v1/auth/login
│   Payload: { email, password, tenant_id? }
│   Response: { success, access_token, refresh_token, user }

On Success:
├── Store tokens in localStorage
├── Store user in localStorage
├── Set tenant_id in localStorage (from user.tenant_id)
├── Prefetch dashboard data (non-blocking)
├── Navigate to "/" or previous location

Buttons:
├── [Sign In] → Validates form, calls login API, navigates on success
└── [Forgot Password] → Navigates to /forgot-password
```

### / (Dashboard)
```
Purpose: Main landing page showing key metrics and recent activity

Components:
├── StatsCards (4 cards)
│   ├── Total Quotes (with trend)
│   ├── Revenue (with trend)
│   ├── Conversion Rate (with trend)
│   └── Active Clients (with trend)
├── RevenueChart (bar chart, 30 days)
├── QuotesTrendChart (line chart)
├── RecentQuotes (list of 5)
└── RecentActivity (timeline)

State:
├── stats: { quotes, revenue, conversion, clients }
├── recentQuotes: Quote[]
├── loading: boolean
├── error: string | null

API Calls:
├── GET /api/v1/dashboard/all (aggregated endpoint)
│   Response: { stats, recent_quotes, recent_activity, usage }
│   Cache: 5 minutes (stale-while-revalidate)

Buttons:
├── Stats cards → Click navigates to respective pages
├── Quote rows → Click navigates to /quotes/:id
└── "View All" links → Navigate to full list pages
```

### /quotes - Quotes List
```
Purpose: View and manage all quotes with filtering

Components:
├── Header with title + "New Quote" button
├── FilterBar
│   ├── Search input (searches customer name, email, quote number)
│   ├── Status dropdown (draft, sent, viewed, accepted, expired, rejected)
│   ├── Destination dropdown (from API)
│   └── Date range picker
├── QuotesTable
│   ├── Checkbox column (bulk select)
│   ├── Quote # column (sortable)
│   ├── Customer column
│   ├── Destination column
│   ├── Total column (sortable)
│   ├── Status badge column
│   ├── Created date column (sortable)
│   └── Actions column (view, send, download, delete)
├── Pagination
└── EmptyState (when no quotes)

State:
├── quotes: Quote[]
├── filters: { search, status, destination, startDate, endDate }
├── pagination: { page, limit, total }
├── selectedIds: string[]
├── loading: boolean
├── sortBy: string
├── sortOrder: 'asc' | 'desc'

API Calls:
├── GET /api/v1/quotes?status=X&destination=Y&page=N&limit=50
│   Response: { success, data: Quote[], pagination }
│   Cache: 5 minutes
├── GET /api/v1/pricing/destinations (for filter dropdown)
│   Cache: 30 minutes

Buttons:
├── [+ New Quote] → Navigate to /quotes/new
├── [Search icon] → Triggers search filter
├── [Status dropdown] → Filters by status
├── [Destination dropdown] → Filters by destination
├── [Eye icon] → Navigate to /quotes/:id
├── [Send icon] → Opens send confirmation modal
├── [Download icon] → Downloads PDF
├── [Trash icon] → Opens delete confirmation modal
├── [Pagination] → Changes page
└── [Table headers] → Sort by column
```

### /quotes/new - Generate Quote (Multi-Step Wizard)
```
Purpose: Create new quote through guided wizard

Steps/Components:
├── Step 1: Customer Details
│   ├── First Name input (required)
│   ├── Last Name input (required)
│   ├── Email input (required, validated)
│   ├── Phone input (optional)
│   ├── "Existing Customer?" toggle
│   └── Customer search (when toggle on)
├── Step 2: Trip Details
│   ├── Destination dropdown (from API)
│   ├── Check-in date picker
│   ├── Check-out date picker
│   ├── Adults count input
│   ├── Children count input
│   └── Child ages inputs (dynamic based on count)
├── Step 3: Accommodation Selection
│   ├── Hotel search/filter
│   ├── Hotel cards with "Select" buttons
│   ├── Room type selection
│   ├── Meal plan selection (BB, HB, FB, AI)
│   └── Selected accommodations summary
├── Step 4: Additional Services
│   ├── Transfers toggle + options
│   ├── Insurance toggle + options
│   ├── Activities search/add
│   └── Custom line items
├── Step 5: Review & Generate
│   ├── Full quote preview
│   ├── Validity period input
│   ├── Notes textarea
│   ├── Discount input (optional)
│   └── Generate button

State:
├── currentStep: 1-5
├── customerData: { firstName, lastName, email, phone }
├── tripData: { destination, checkIn, checkOut, adults, children, childAges }
├── accommodations: SelectedAccommodation[]
├── services: { transfers, insurance, activities, customItems }
├── quoteSettings: { validity, notes, discount }
├── loading: boolean
├── errors: Record<string, string>

API Calls:
├── GET /api/v1/pricing/destinations
├── GET /api/v1/pricing/hotels?destination=X
├── GET /api/v1/pricing/hotels/:name/rates
├── POST /api/v1/quotes/generate (final submission)
│   Payload: { customer, trip, accommodations, services, settings }
│   Response: { success, quote_id, pdf_url }
│   Timeout: 30 seconds (PDF generation)

Buttons:
├── [Back] → Go to previous step
├── [Next] → Validate current step, go to next
├── [Select Hotel] → Add hotel to accommodations
├── [Remove] → Remove accommodation/service
├── [Generate Quote] → Submit to API, navigate to /quotes/:id
└── [Save Draft] → Save without generating PDF
```

### /quotes/:id - Quote Detail
```
Purpose: View quote details, PDF preview, and take actions

Components:
├── Header
│   ├── Quote number + status badge
│   ├── [Send Quote] button
│   ├── [Download PDF] button
│   └── [Actions dropdown] (edit, duplicate, delete, convert to invoice)
├── QuoteInfo card
│   ├── Customer name, email, phone
│   ├── Destination
│   ├── Travel dates
│   ├── Number of travelers
│   └── Created date, validity
├── PDF Preview iframe
├── Line Items table
│   ├── Description
│   ├── Quantity
│   ├── Unit price
│   └── Total
├── Totals section
│   ├── Subtotal
│   ├── Discount (if any)
│   ├── Tax
│   └── Grand Total
├── Activity Timeline
│   ├── Created event
│   ├── Sent events
│   ├── Viewed events
│   └── Status change events
└── SendQuoteModal (conditional)

State:
├── quote: Quote
├── loading: boolean
├── showSendModal: boolean
├── sending: boolean
├── pdfLoading: boolean

API Calls:
├── GET /api/v1/quotes/:id
│   Response: { success, data: Quote }
│   Cache: 10 minutes
├── POST /api/v1/quotes/:id/resend
│   Response: { success, message }
├── GET /api/v1/quotes/:id/pdf (blob)
├── DELETE /api/v1/quotes/:id

Buttons:
├── [Send Quote] → Opens SendQuoteModal
├── [Download PDF] → Triggers PDF download
├── [Edit] → Navigate to edit mode
├── [Duplicate] → Create copy, navigate to new
├── [Convert to Invoice] → Opens conversion modal
├── [Delete] → Opens delete confirmation
└── [Back to Quotes] → Navigate to /quotes
```

### /invoices - Invoices List
```
Purpose: View and manage all invoices

Components:
├── Header with title + "Create Invoice" button
├── Status tabs (All, Draft, Sent, Partially Paid, Paid, Overdue)
├── SearchBar
├── InvoicesTable
│   ├── Invoice # column
│   ├── Customer column
│   ├── Amount column
│   ├── Status badge column
│   ├── Due date column
│   ├── Paid amount column
│   └── Actions column
├── Pagination
└── CreateInvoiceModal (conditional)

State:
├── invoices: Invoice[]
├── statusFilter: string
├── search: string
├── pagination: { page, limit, total }
├── showCreateModal: boolean
├── loading: boolean

API Calls:
├── GET /api/v1/invoices?status=X&search=Y&page=N
│   Cache: 5 minutes
├── GET /api/v1/invoices/stats
│   Response: { total_invoiced, total_paid, outstanding, overdue_count }

Buttons:
├── [+ Create Invoice] → Opens CreateInvoiceModal
├── [Status tabs] → Filter by status
├── [View] → Navigate to /invoices/:id
├── [Send] → Send invoice email
├── [Download] → Download PDF
└── [Record Payment] → Opens payment modal
```

### /invoices/:id - Invoice Detail
```
Purpose: View invoice details and manage payments

Components:
├── Header
│   ├── Invoice number + status badge
│   ├── [Send Invoice] button
│   ├── [Download PDF] button
│   ├── [Record Payment] button
│   └── [Mark as Paid] button (when applicable)
├── InvoiceInfo card
│   ├── Customer details
│   ├── Invoice date
│   ├── Due date
│   └── Payment terms
├── PDF Preview
├── Line Items table
├── Totals section
├── Payment History table
│   ├── Payment date
│   ├── Amount
│   ├── Method
│   ├── Reference
│   └── Notes
├── RecordPaymentModal (conditional)
└── Activity Timeline

State:
├── invoice: Invoice
├── payments: Payment[]
├── loading: boolean
├── showPaymentModal: boolean
├── recording: boolean

API Calls:
├── GET /api/v1/invoices/:id
│   Cache: 10 minutes
├── POST /api/v1/invoices/:id/send
├── POST /api/v1/invoices/:id/payments
│   Payload: { amount, method, reference, notes, payment_date }
├── PATCH /api/v1/invoices/:id/status
│   Payload: { status: 'paid' | 'partial' | 'overdue' }
├── GET /api/v1/invoices/:id/pdf (blob)

Buttons:
├── [Send Invoice] → Sends email to customer
├── [Download PDF] → Downloads PDF file
├── [Record Payment] → Opens RecordPaymentModal
├── [Mark as Paid] → Updates status to 'paid'
└── [Delete] → Opens delete confirmation
```

### /crm/pipeline - Sales Pipeline (Kanban)
```
Purpose: Visual sales pipeline with drag-and-drop

Components:
├── Header with stats summary
├── KanbanBoard
│   ├── Column: Quoted (clients with quotes sent)
│   ├── Column: Negotiating (in discussion)
│   ├── Column: Booked (travel confirmed)
│   ├── Column: Paid (payment received)
│   ├── Column: Travelled (trip completed)
│   └── Column: Lost (did not proceed)
├── ClientCard (draggable)
│   ├── Client name
│   ├── Email
│   ├── Total value
│   ├── Last activity
│   └── Quick actions
└── AddClientModal (conditional)

State:
├── pipeline: { [stage]: Client[] }
├── draggedClient: Client | null
├── loading: boolean
├── showAddModal: boolean

API Calls:
├── GET /api/v1/crm/pipeline
│   Response: { stages: { quoted: [], negotiating: [], ... } }
│   Cache: 5 minutes
├── PATCH /api/v1/crm/clients/:id/stage
│   Payload: { stage: 'quoted' | 'negotiating' | ... }

Drag & Drop:
├── onDragStart → Set draggedClient
├── onDragOver → Allow drop
├── onDrop → Call updateStage API, move card to new column
└── Uses @dnd-kit/core library

Buttons:
├── [+ Add Client] → Opens AddClientModal
├── [Client card] → Navigate to /crm/clients/:id
└── [Quick actions] → Email, call, view quotes
```

### /crm/clients - Clients List
```
Purpose: View and manage all clients

Components:
├── Header with title + "Add Client" button
├── SearchBar
├── FilterBar (source, stage, date range)
├── ClientsTable
│   ├── Name column
│   ├── Email column
│   ├── Phone column
│   ├── Source badge column (Website, Referral, etc.)
│   ├── Stage badge column
│   ├── Quotes count column
│   ├── Total value column
│   └── Actions column
├── Pagination
└── AddClientModal (conditional)

State:
├── clients: Client[]
├── filters: { search, source, stage }
├── pagination: { page, limit, total }
├── showAddModal: boolean
├── loading: boolean

API Calls:
├── GET /api/v1/crm/clients?search=X&source=Y&page=N
│   Cache: 5 minutes
├── POST /api/v1/crm/clients
│   Payload: { name, email, phone, source }
├── DELETE /api/v1/crm/clients/:id

Buttons:
├── [+ Add Client] → Opens AddClientModal
├── [View] → Navigate to /crm/clients/:id
├── [Edit] → Opens edit modal
└── [Delete] → Opens delete confirmation
```

### /crm/clients/:id - Client Detail
```
Purpose: View client details, history, and related records

Components:
├── Header with client name + actions
├── ClientInfo card
│   ├── Email (with copy button)
│   ├── Phone (with call link)
│   ├── Source
│   ├── Stage
│   └── Created date
├── Stats cards
│   ├── Total Quotes
│   ├── Total Invoices
│   ├── Total Revenue
│   └── Conversion Rate
├── Tabs
│   ├── Activity tab (timeline)
│   ├── Quotes tab (related quotes list)
│   ├── Invoices tab (related invoices list)
│   └── Notes tab (internal notes)
├── AddActivityModal (conditional)
└── EditClientModal (conditional)

State:
├── client: Client
├── activities: Activity[]
├── quotes: Quote[]
├── invoices: Invoice[]
├── activeTab: 'activity' | 'quotes' | 'invoices' | 'notes'
├── loading: boolean
├── showAddActivity: boolean

API Calls:
├── GET /api/v1/crm/clients/:id
│   Cache: 10 minutes
├── GET /api/v1/crm/clients/:id/activities
├── POST /api/v1/crm/clients/:id/activities
│   Payload: { type, description, metadata }
├── PATCH /api/v1/crm/clients/:id
│   Payload: { name?, email?, phone?, stage? }

Buttons:
├── [Edit] → Opens EditClientModal
├── [Add Activity] → Opens AddActivityModal
├── [Email] → Opens email client
├── [Call] → Opens phone dialer
├── [Create Quote] → Navigate to /quotes/new with client pre-filled
├── [View Quote] → Navigate to /quotes/:id
└── [View Invoice] → Navigate to /invoices/:id
```

### /analytics - Analytics Dashboard
```
Purpose: Business intelligence and reporting

Components:
├── Period selector (7d, 30d, 90d, 12m)
├── Stats cards row
│   ├── Total Revenue (with trend)
│   ├── Quotes Generated (with trend)
│   ├── Conversion Rate (with trend)
│   └── Average Deal Size (with trend)
├── RevenueChart (bar chart by month)
├── QuotesTrendChart (line chart)
├── PipelineDonutChart (clients by stage)
├── AgingChart (invoice aging buckets)
├── TopDestinations table
├── TopConsultants table (if multi-user)
└── ConversionFunnel

State:
├── period: '7d' | '30d' | '90d' | '12m'
├── quoteAnalytics: QuoteAnalytics
├── invoiceAnalytics: InvoiceAnalytics
├── pipelineAnalytics: PipelineAnalytics
├── loading: boolean

API Calls:
├── GET /api/v1/analytics/quotes?period=30d
│   Cache: 5 minutes
├── GET /api/v1/analytics/invoices?period=30d
│   Cache: 5 minutes
├── GET /api/v1/analytics/pipeline
│   Cache: 5 minutes

Buttons:
├── [Period buttons] → Change period, refetch data
└── [Export] → Download CSV report
```

### /helpdesk - AI Helpdesk
```
Purpose: AI-powered help chat for platform questions

Components:
├── Header with title + "New Chat" button
├── ChatContainer
│   ├── WelcomeMessage (AI greeting)
│   ├── MessageList
│   │   ├── UserMessage (right-aligned, primary color)
│   │   └── AssistantMessage (left-aligned, with sources)
│   ├── TypingIndicator (while AI responds)
│   └── ScrollToBottom button
├── SuggestedQuestions (shown initially)
│   ├── "How do I create a new quote?"
│   ├── "How do I add a client to the CRM?"
│   └── ... more suggestions
├── InputArea
│   ├── Text input
│   └── Send button
└── Sources display (per message)

State:
├── messages: Message[]
├── input: string
├── isLoading: boolean

API Calls:
├── POST /api/v1/helpdesk/ask
│   Payload: { question }
│   Response: { success, answer, sources }

Buttons:
├── [Send] → Submit question to AI
├── [New Chat] → Clear messages, start fresh
└── [Suggested questions] → Fill input with question
```

### /knowledge - Knowledge Base Documents
```
Purpose: Manage documents for AI knowledge base

Components:
├── Header with "Upload Document" button
├── Tab navigation (Documents | Search)
├── Documents Tab:
│   ├── Stats cards (Total, Indexed, Pending, Chunks, Size)
│   ├── Filters (Category, Visibility)
│   ├── DocumentsTable
│   │   ├── Filename + ID
│   │   ├── Category badge
│   │   ├── Visibility badge (Public/Private)
│   │   ├── Status badge (Indexed/Pending/Error)
│   │   ├── Chunk count
│   │   ├── File size
│   │   └── Actions (Re-index, Delete)
│   └── EmptyState
├── Search Tab:
│   ├── Search input (semantic search)
│   ├── Filters (Category, Visibility, Result count)
│   ├── Suggested searches
│   └── Search results with relevance scores
├── UploadModal (conditional)
└── ConfirmModal (for delete)

State:
├── activeTab: 'documents' | 'search'
├── documents: Document[]
├── status: KBStatus
├── categoryFilter: string
├── visibilityFilter: string
├── searchQuery: string
├── searchResults: SearchResult[]
├── showUploadModal: boolean
├── loading: boolean

API Calls:
├── GET /api/v1/knowledge/documents?category=X&visibility=Y
├── GET /api/v1/knowledge/status
├── POST /api/v1/knowledge/documents (FormData)
│   Payload: { file, category, tags, visibility }
├── DELETE /api/v1/knowledge/documents/:id
├── POST /api/v1/knowledge/search
│   Payload: { query, top_k, category?, visibility? }
│   Response: { success, data: [{ content, source, score }] }

Buttons:
├── [Upload Document] → Opens UploadModal
├── [Rebuild Index] → Triggers full re-index
├── [Re-index] per doc → Re-indexes single document
├── [Delete] → Opens delete confirmation
├── [Search] → Executes semantic search
├── [Suggested search] → Fills and executes search
└── [Tab buttons] → Switch between tabs
```

### /pricing/rates - Pricing Rates
```
Purpose: View hotel rates used in quotes

Components:
├── Header with "Export Rates" button
├── Stats cards (Total Rates, Hotels, Avg Price, Price Range)
├── Filters
│   ├── Search input (hotel, room type)
│   ├── Destination dropdown
│   ├── Meal plan dropdown (BB, HB, FB, AI)
│   └── Refresh button
├── RatesTable
│   ├── Hotel name + destination
│   ├── Room type
│   ├── Meal plan badge
│   ├── Valid period
│   ├── Nights
│   ├── Per person share price
│   ├── Single price
│   └── Child price
└── Result count

State:
├── rates: Rate[]
├── stats: RateStats
├── destinations: Destination[]
├── filters: { destination, hotel_name, meal_plan }
├── search: string
├── loading: boolean

API Calls:
├── GET /api/v1/pricing/rates?destination=X&meal_plan=Y
│   Cache: 10 minutes, 30s timeout (BigQuery)
├── GET /api/v1/pricing/stats
│   Cache: 5 minutes
├── GET /api/v1/pricing/destinations
│   Cache: 30 minutes

Buttons:
├── [Export Rates] → Downloads CSV
├── [Filter dropdowns] → Apply filters
├── [Refresh] → Reload data
└── [Table headers] → Sort columns
```

### /pricing/hotels - Hotels List
```
Purpose: Browse hotels grouped by destination

Components:
├── Header with hotel/destination counts
├── Destination filter cards (clickable)
├── Search input
├── Hotels list (grouped by destination)
│   ├── Destination header with count
│   ├── HotelCard (expandable)
│   │   ├── Hotel name (links to detail)
│   │   ├── Star rating
│   │   ├── Expand/collapse button
│   │   └── Expanded: rates table preview
│   └── "View all rates" link

State:
├── hotels: Hotel[]
├── destinations: Destination[]
├── destinationFilter: string
├── search: string
├── expandedHotel: string | null
├── hotelRates: { [name]: Rate[] }
├── loading: boolean

API Calls:
├── GET /api/v1/pricing/hotels?destination=X
│   Cache: 10 minutes
├── GET /api/v1/pricing/destinations
├── GET /api/v1/pricing/hotels/:name/rates (on expand)

Buttons:
├── [Destination cards] → Filter by destination
├── [Hotel name] → Navigate to hotel detail
├── [Expand/Collapse] → Show/hide rates preview
└── [View all rates] → Navigate to hotel detail
```

### /settings - Settings Page
```
Purpose: Manage account and company settings

Components:
├── Tab navigation
│   ├── Company (company info)
│   ├── Branding (colors, logo, theme)
│   ├── Email (email templates, SMTP)
│   ├── Banking (payment details)
│   ├── Team (team members - admin only)
│   ├── Templates (quote/invoice layout)
│   └── Privacy (GDPR/POPIA controls)
├── Company Tab:
│   ├── Company name input
│   ├── Email input
│   ├── Phone input
│   ├── Address textarea
│   ├── VAT number input
│   └── Save button
├── Branding Tab:
│   ├── Logo upload (with crop modal)
│   ├── Primary color picker
│   ├── Secondary color picker
│   ├── Font family selector
│   ├── Theme presets grid
│   ├── Dark mode toggle
│   └── Preview panel
├── Templates Tab:
│   ├── Quote/Invoice tab toggle
│   ├── TemplateBuilder component
│   │   ├── Section palette (draggable)
│   │   ├── Document canvas (sortable)
│   │   └── Properties panel
│   ├── Save/Reset buttons
│   └── Live preview
└── Other tabs (see separate sections)

State:
├── activeTab: string
├── settings: TenantSettings
├── branding: BrandingSettings
├── loading: boolean
├── saving: boolean
├── hasChanges: boolean

API Calls:
├── GET /api/v1/settings
├── PUT /api/v1/settings (company/email/banking)
├── GET /api/v1/branding
├── PUT /api/v1/branding
├── POST /api/v1/branding/upload/logo (FormData)
├── GET /api/v1/branding/presets
├── POST /api/v1/branding/apply-preset/:name
├── GET /api/v1/templates
├── PUT /api/v1/templates

Buttons:
├── [Tab buttons] → Switch settings tab
├── [Upload Logo] → Opens file picker
├── [Apply Preset] → Applies theme preset
├── [Reset] → Reset to defaults
├── [Save Changes] → Save current tab settings
└── [Toggle dark mode] → Switch theme mode
```

### /settings/team - Team Settings (Admin Only)
```
Purpose: Manage team members and invitations

Components:
├── Header with "Invite Member" button
├── UsersTable
│   ├── User avatar + name + email
│   ├── Role badge (Admin/Consultant)
│   ├── Status (Active/Inactive)
│   ├── Last login date
│   └── Actions (Edit, Deactivate)
├── Pending Invitations section
│   ├── Invitation card
│   │   ├── Name + email
│   │   ├── Role badge
│   │   ├── Expiry date
│   │   └── Resend/Cancel buttons
├── InviteModal (conditional)
│   ├── Name input
│   ├── Email input
│   ├── Role dropdown (Consultant/Admin)
│   └── Send button
├── EditUserModal (conditional)
├── ConfirmModal (for deactivate/cancel)
└── Toast notifications

State:
├── users: User[]
├── invitations: Invitation[]
├── showInviteModal: boolean
├── showEditModal: boolean
├── selectedUser: User | null
├── inviteForm: { email, name, role }
├── editForm: { name, role }
├── loading: boolean
├── submitting: boolean

API Calls:
├── GET /api/v1/users
├── GET /api/v1/users/invitations
├── POST /api/v1/users/invite
│   Payload: { email, name, role }
├── PATCH /api/v1/users/:id
│   Payload: { name?, role? }
├── DELETE /api/v1/users/:id (deactivate)
├── POST /api/v1/users/invitations/:id/resend
├── DELETE /api/v1/users/invitations/:id (cancel)

Buttons:
├── [Invite Member] → Opens InviteModal
├── [Edit user] → Opens EditUserModal
├── [Deactivate] → Opens confirm, calls deactivate
├── [Resend invitation] → Resends invite email
├── [Cancel invitation] → Opens confirm, cancels invite
└── [Send Invitation] → Submits invite form
```

### /settings/privacy - Privacy Settings (GDPR/POPIA)
```
Purpose: Manage privacy consents and data rights

Components:
├── Info banner (privacy rights explanation)
├── Communication Preferences section
│   ├── ConsentToggle cards
│   │   ├── Marketing Emails toggle
│   │   ├── Marketing SMS toggle
│   │   ├── Marketing Calls toggle
│   │   ├── Analytics toggle
│   │   └── Third-Party Sharing toggle
├── Quick Actions section
│   ├── [Download My Data] button
│   └── [Delete My Account] button
├── Submit Data Request form
│   ├── Request type radio buttons
│   │   ├── Access My Data
│   │   ├── Export My Data
│   │   ├── Correct My Data
│   │   ├── Delete My Data
│   │   └── Object to Processing
│   ├── Details textarea (optional)
│   └── Submit button
├── Request History section
│   ├── Request cards with status badges
│   │   ├── Request type
│   │   ├── Created date
│   │   ├── Due date
│   │   └── Status (Pending/Verified/In Progress/Completed/Rejected)
└── Status message toast

State:
├── consents: { [type]: { granted: boolean } }
├── dsarRequests: DSARRequest[]
├── loading: boolean
├── saving: boolean
├── submitting: boolean
├── message: { type: 'success' | 'error', text: string } | null

API Calls:
├── GET /privacy/consent
├── POST /privacy/consent
│   Payload: { consent_type, granted, source }
├── POST /privacy/dsar
│   Payload: { request_type, email, name, details }
├── GET /privacy/dsar
├── POST /privacy/export
│   Payload: { email, include_quotes, include_invoices, format }

Buttons:
├── [Consent toggles] → Toggle individual consent, save immediately
├── [Download My Data] → Requests data export
├── [Delete My Account] → Submits erasure DSAR
└── [Submit Request] → Submits DSAR form
```

---

## 3. COMPONENTS

### Layout Components

```
Layout.jsx
├── Purpose: Main app shell with sidebar and content area
├── Props: { children }
├── Contains: Sidebar, Header, main content area
├── State: Uses AppContext for sidebar state
└── Behavior: Responsive sidebar collapse on mobile

Sidebar.jsx
├── Purpose: Main navigation sidebar
├── Props: none (uses context)
├── State from AppContext:
│   ├── sidebarPinned: boolean
│   ├── sidebarHovered: boolean
│   └── sidebarExpanded: computed
├── Navigation sections:
│   ├── Main: Dashboard, Quotes, Invoices
│   ├── CRM: Clients, Pipeline
│   ├── Pricing: Rates, Hotels
│   ├── AI: Helpdesk, Knowledge
│   └── Footer: Settings, User menu
├── Buttons:
│   ├── [Nav links] → Navigate to page
│   ├── [Pin toggle] → Toggle sidebarPinned
│   ├── [User menu] → Dropdown with profile, settings, logout
│   └── [Collapse toggle] → Collapse sidebar on mobile
└── Hover behavior: Expand when hovered (if not pinned)

Header.jsx
├── Purpose: Top header bar
├── Props: none (uses contexts)
├── Contains:
│   ├── Company name (from clientInfo)
│   ├── Dark mode toggle
│   ├── Notifications bell
│   └── User dropdown menu
├── State from ThemeContext: darkMode
├── State from AppContext: clientInfo
└── Buttons:
    ├── [Dark mode toggle] → Toggle theme
    ├── [Notifications] → Show notifications dropdown
    └── [User avatar] → Show user menu dropdown
```

### Auth Components

```
ProtectedRoute.jsx
├── Purpose: Route wrapper requiring authentication
├── Props: { children, requireAdmin?: boolean }
├── Uses: useAuth() hook
├── Behavior:
│   ├── If loading → Show loading spinner
│   ├── If !authenticated → Redirect to /login
│   ├── If requireAdmin && !isAdmin → Redirect to /
│   └── Otherwise → Render children
└── Exports: ProtectedRoute, AdminRoute

AdminRoute.jsx
├── Purpose: Route wrapper requiring admin role
├── Implementation: <ProtectedRoute requireAdmin>{children}</ProtectedRoute>
```

### UI Components

```
Toggle.jsx
├── Purpose: Reusable toggle switch
├── Props:
│   ├── checked: boolean
│   ├── onChange: (checked: boolean) => void
│   ├── disabled?: boolean
│   ├── size?: 'sm' | 'md' | 'lg'
│   ├── label?: string
│   └── labelPosition?: 'left' | 'right'
├── Features:
│   ├── Keyboard accessible (Enter, Space)
│   ├── Screen reader friendly
│   └── Smooth color transitions
└── Uses CSS variables for theming

ToggleCard.jsx
├── Purpose: Toggle with card styling
├── Props:
│   ├── icon: HeroIcon component
│   ├── title: string
│   ├── description: string
│   ├── checked: boolean
│   ├── onChange: function
│   └── disabled?: boolean
└── Used in: Privacy settings, notification preferences

Skeleton.jsx
├── Purpose: Loading placeholder animations
├── Variants:
│   ├── SkeletonCard - Card with header and lines
│   ├── SkeletonTable - Table rows placeholder
│   ├── SkeletonChart - Chart area placeholder
│   └── SkeletonText - Text lines placeholder
└── Used during: Data loading states

LogoCropModal.jsx
├── Purpose: Crop uploaded logo images
├── Props:
│   ├── isOpen: boolean
│   ├── imageUrl: string
│   ├── onSave: (croppedBlob) => void
│   └── onClose: () => void
├── Features:
│   ├── Drag to reposition
│   ├── Zoom slider
│   ├── Aspect ratio lock
│   └── Preview of cropped result
└── Used in: Branding settings
```

### Modal Components (Inline in Pages)

```
ConfirmModal
├── Purpose: Generic confirmation dialog
├── Props: { isOpen, title, message, confirmText, cancelText, onConfirm, onCancel, danger }
├── Used for: Delete confirmations, deactivations, destructive actions
└── Appears in: Multiple pages

SendQuoteModal
├── Purpose: Confirm sending quote to customer
├── Contains: Recipient email preview, custom message option
└── API: POST /api/v1/quotes/:id/resend

RecordPaymentModal
├── Purpose: Record payment against invoice
├── Fields: Amount, Method, Reference, Date, Notes
└── API: POST /api/v1/invoices/:id/payments

AddClientModal
├── Purpose: Create new CRM client
├── Fields: Name, Email, Phone, Source
└── API: POST /api/v1/crm/clients

UploadDocumentModal
├── Purpose: Upload document to knowledge base
├── Fields: File picker, Category, Tags, Visibility
└── API: POST /api/v1/knowledge/documents

InviteUserModal
├── Purpose: Invite new team member
├── Fields: Name, Email, Role
└── API: POST /api/v1/users/invite
```

---

## 4. STATE MANAGEMENT

### Context Providers

```
AuthContext
├── File: context/AuthContext.jsx
├── Provider: AuthProvider
├── Hook: useAuth()
├── State:
│   ├── user: User | null
│   ├── loading: boolean (auth initialization)
│   ├── error: string | null
│   ├── isAuthenticated: boolean (derived)
│   ├── isAdmin: boolean (derived)
│   └── isConsultant: boolean (derived)
├── Methods:
│   ├── login(email, password, tenantId?) → Promise
│   ├── logout() → void
│   ├── updateUser(userData) → void
│   ├── getAccessToken() → string | null
│   ├── tryRefreshToken() → Promise<boolean>
│   └── clearError() → void
├── Effects:
│   ├── Initialize auth from localStorage on mount
│   ├── Verify token with /auth/me endpoint
│   ├── Listen for 'auth:session-expired' event
│   └── Prefetch dashboard data on login
└── Token Storage:
    ├── access_token → localStorage
    ├── refresh_token → localStorage
    ├── user → localStorage (JSON)
    └── tenant_id → localStorage

AppContext
├── File: context/AppContext.jsx
├── Provider: AppProvider
├── Hook: useApp()
├── State:
│   ├── clientInfo: ClientInfo | null
│   ├── loading: boolean
│   ├── error: string | null
│   ├── sidebarOpen: boolean
│   ├── sidebarPinned: boolean (persisted)
│   ├── sidebarHovered: boolean
│   └── sidebarExpanded: boolean (computed)
├── Methods:
│   ├── setSidebarOpen(open) → void
│   ├── toggleSidebarPinned() → void
│   ├── setSidebarHovered(hovered) → void
│   ├── refreshClientInfo() → Promise
│   └── updateClientInfo(updates) → void
├── Effects:
│   ├── Load clientInfo when authenticated
│   ├── Cache clientInfo in localStorage (30 min)
│   └── Retry on failure (3 attempts)
└── Cache: localStorage 'client_info_cache'

ThemeContext
├── File: context/ThemeContext.jsx
├── Provider: ThemeProvider
├── Hook: useTheme()
├── State:
│   ├── branding: BrandingSettings
│   ├── darkMode: boolean (persisted)
│   ├── loading: boolean
│   └── error: string | null
├── Methods:
│   ├── updateBranding(updates) → void
│   ├── toggleDarkMode() → void
│   ├── applyPreset(presetName) → Promise
│   └── refreshBranding() → Promise
├── CSS Variables Applied:
│   ├── --color-primary
│   ├── --color-secondary
│   ├── --color-background
│   ├── --color-surface
│   ├── --color-text
│   ├── --font-family
│   └── ... more theme vars
└── Storage: localStorage 'darkMode'
```

### Local State Patterns

```
Page-Level State:
├── Data arrays (quotes, invoices, clients)
├── Filter objects ({ search, status, date })
├── Pagination ({ page, limit, total })
├── Modal visibility booleans
├── Loading states
├── Selected items for bulk actions
└── Form data objects

Component-Level State:
├── Input values
├── Dropdown open/closed
├── Hover/focus states
├── Validation errors
└── Local UI toggles
```

---

## 5. API INTEGRATION

### API Client Configuration

```javascript
// File: services/api.js

// Axios instance
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  timeout: 10000, // 10 seconds default
});

// Request interceptor
api.interceptors.request.use((config) => {
  // Add X-Client-ID header (except for login)
  if (!config.url.includes('/auth/login')) {
    const clientId = getTenantId();
    if (clientId && clientId !== 'example') {
      config.headers['X-Client-ID'] = clientId;
    }
  }

  // Add Authorization header
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers['Authorization'] = `Bearer ${token}`;
  }

  // Set Content-Type (skip for FormData)
  if (!(config.data instanceof FormData)) {
    config.headers['Content-Type'] = 'application/json';
  }

  return config;
});

// Response interceptor (token refresh)
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    // On 401, attempt token refresh
    // Queue failed requests during refresh
    // Dispatch 'auth:session-expired' if refresh fails
  }
);
```

### Caching System

```javascript
// Cache configuration
CACHE_TTL = 600000;        // 10 minutes (rates)
STATS_CACHE_TTL = 300000;  // 5 minutes (stats)
DETAIL_CACHE_TTL = 600000; // 10 minutes (details)
LIST_CACHE_TTL = 300000;   // 5 minutes (lists)
STATIC_CACHE_TTL = 1800000; // 30 minutes (hotels, destinations)

// Cache functions
getCached(key) → data | null
setCached(key, data, ttl)
getStaleCached(key) → { data, isStale } | null
fetchWithSWR(key, fetcher, ttl) → Promise (stale-while-revalidate)
clearCache(pattern?) → void
prefetch(key, fetcher, ttl) → Promise
warmCache() → Promise (on app start)
prefetchForRoute(route) → void (on navigation)

// Cache persistence
- Saved to sessionStorage every 10 seconds
- Restored on app load (if not expired)
```

### API Modules

```javascript
// Authentication
authApi = {
  login(email, password, tenantId?)
  logout()
  refresh(refreshToken)
  me()
  requestPasswordReset(email)
  changePassword(newPassword)
  updateProfile(data)
  acceptInvite(token, password, name?)
}

// Quotes
quotesApi = {
  list(params?, options?)     // GET /api/v1/quotes
  get(id)                     // GET /api/v1/quotes/:id
  generate(data)              // POST /api/v1/quotes/generate
  resend(id)                  // POST /api/v1/quotes/:id/resend
  update(id, data)            // PATCH /api/v1/quotes/:id
  delete(id)                  // DELETE /api/v1/quotes/:id
  download(id)                // GET /api/v1/quotes/:id/pdf (blob)
  prefetch(id)                // Prefetch detail for hover
}

// Invoices
invoicesApi = {
  list(params?)               // GET /api/v1/invoices
  get(id)                     // GET /api/v1/invoices/:id
  createFromQuote(data)       // POST /api/v1/invoices/convert-quote
  createManual(data)          // POST /api/v1/invoices/create
  update(id, data)            // PATCH /api/v1/invoices/:id
  delete(id)                  // DELETE /api/v1/invoices/:id
  send(id)                    // POST /api/v1/invoices/:id/send
  download(id)                // GET /api/v1/invoices/:id/pdf (blob)
  updateStatus(id, status)    // PATCH /api/v1/invoices/:id/status
  recordPayment(id, data)     // POST /api/v1/invoices/:id/payments
  getStats()                  // GET /api/v1/invoices/stats
  prefetch(id)
  clearListCache()            // Clear after mutations
}

// CRM
crmApi = {
  listClients(params?, forceRefresh?)
  getClient(id)
  createClient(data)
  updateClient(id, data)
  deleteClient(id)
  getPipeline()
  updateStage(clientId, stage)
  getActivities(clientId)
  addActivity(clientId, data)
  getStats()
  prefetch(id)
}

// Pricing
pricingApi = {
  listRates(params?)          // 30s timeout for BigQuery
  getRate(id)
  listHotels(params?)         // 30s timeout
  getHotel(hotelName)
  getHotelRates(hotelName)
  listDestinations()          // 30s timeout
  getStats()                  // 30s timeout
}

// Knowledge Base
knowledgeApi = {
  listDocuments(params?)
  getDocument(id)
  uploadDocument(formData)    // FormData with file
  deleteDocument(id)
  updateVisibility(id, visibility)
  search(query, params?)
  getStatus()
}

// Dashboard
dashboardApi = {
  getAll()                    // Aggregated endpoint, 30s timeout, SWR
  getStats(period?)
  getRecentActivity(limit?)
}

// Analytics
analyticsApi = {
  getQuoteAnalytics(period?)
  getInvoiceAnalytics(period?)
  getPipelineAnalytics()
  getCallAnalytics(period?)
}

// Branding
brandingApi = {
  get()
  update(data)
  getPresets()
  applyPreset(presetName)
  uploadLogo(formData)
  uploadBackground(formData)
  reset()
  getFonts()
  preview(data)
  getCSSVariables()
}

// Settings
tenantSettingsApi = {
  get()
  update(data)
  updateCompany(data)
  updateEmail(data)
  updateBanking(data)
}

// Templates
templatesApi = {
  get()
  update(data)
  getQuote()
  getInvoice()
  reset()
  getLayouts()
}

// Users (Admin)
usersApi = {
  list()
  get(userId)
  update(userId, data)
  deactivate(userId)
  invite(email, name, role)
  listInvitations()
  cancelInvitation(invitationId)
  resendInvitation(invitationId)
}

// Helpdesk
helpdeskApi = {
  ask(question)               // POST /api/v1/helpdesk/ask
  getTopics()
  search(query)
}

// Privacy
privacyApi = {
  getConsents()
  updateConsent(consent)
  updateConsentsBulk(consents)
  submitDSAR(request)
  getDSARs()
  getDSARStatus(requestId)
  requestExport(request)
  requestErasure(email)
}

// Leaderboard
leaderboardApi = {
  getRankings(period?, metric?, limit?)
  getMyPerformance(period?)
  getSummary(period?)
  getConsultantPerformance(consultantId, period?)
}

// Notifications
notificationsApi = {
  list(params?)
  getUnreadCount()
  markRead(notificationId)
  markAllRead()
  getPreferences()
  updatePreferences(preferences)
}

// Client Info
clientApi = {
  getInfo()                   // GET /api/v1/client/info
  updateInfoCache(updates)
  clearInfoCache()
}
```

---

## 6. FORMS

### Login Form
```
Fields:
├── email: string (required, email format)
└── password: string (required, min 8 chars)

Validation: On submit
Submit: authApi.login()
Success: Navigate to /
Error: Display error message
```

### Quote Generation Form (Multi-Step)
```
Step 1 - Customer:
├── firstName: string (required)
├── lastName: string (required)
├── email: string (required, email format)
└── phone: string (optional)

Step 2 - Trip:
├── destination: string (required, from dropdown)
├── checkIn: Date (required)
├── checkOut: Date (required, after checkIn)
├── adults: number (required, min 1)
├── children: number (optional, 0+)
└── childAges: number[] (required if children > 0)

Step 3 - Accommodations:
├── selectedHotels: HotelSelection[]
│   ├── hotelName: string
│   ├── roomType: string
│   ├── mealPlan: 'BB' | 'HB' | 'FB' | 'AI'
│   └── rateId: string

Step 4 - Services:
├── transfers: boolean + TransferOptions
├── insurance: boolean + InsuranceOptions
└── customItems: CustomItem[]

Step 5 - Settings:
├── validity: number (days)
├── notes: string (optional)
└── discount: number (optional, percentage)

Validation: Per-step, blocks next if invalid
Submit: quotesApi.generate()
Success: Navigate to /quotes/:newId
```

### Add Client Form
```
Fields:
├── name: string (required)
├── email: string (required, email format)
├── phone: string (optional)
└── source: 'website' | 'referral' | 'social' | 'other' (required)

Validation: On submit
Submit: crmApi.createClient()
Success: Close modal, refresh list
```

### Record Payment Form
```
Fields:
├── amount: number (required, > 0, <= outstanding)
├── method: 'bank_transfer' | 'card' | 'cash' | 'check'
├── reference: string (optional)
├── payment_date: Date (required, <= today)
└── notes: string (optional)

Validation: On submit
Submit: invoicesApi.recordPayment()
Success: Close modal, refresh invoice
```

### Invite User Form
```
Fields:
├── name: string (required)
├── email: string (required, email format)
└── role: 'consultant' | 'admin' (required)

Validation: On submit
Submit: usersApi.invite()
Success: Close modal, refresh invitations list
```

### Company Settings Form
```
Fields:
├── company_name: string (required)
├── email: string (required, email format)
├── phone: string (optional)
├── address: string (optional)
├── vat_number: string (optional)

Submit: tenantSettingsApi.updateCompany()
```

### Branding Settings Form
```
Fields:
├── primary_color: string (hex color)
├── secondary_color: string (hex color)
├── font_family: string (from list)
├── logo: File (image)
└── background: File (image)

Submit: brandingApi.update() + uploadLogo() if file changed
```

### Banking Settings Form
```
Fields:
├── bank_name: string
├── account_name: string
├── account_number: string
├── branch_code: string
├── swift_code: string (optional)

Submit: tenantSettingsApi.updateBanking()
```

### DSAR Request Form
```
Fields:
├── request_type: 'access' | 'portability' | 'rectification' | 'erasure' | 'objection'
└── details: string (optional)

Submit: privacyApi.submitDSAR()
```

---

## 7. NAVIGATION

### Main Navigation Structure
```
Sidebar Navigation:
├── MAIN
│   ├── Dashboard (/) → HomeIcon
│   ├── Quotes (/quotes) → DocumentTextIcon
│   └── Invoices (/invoices) → ReceiptRefundIcon
├── CRM
│   ├── Clients (/crm/clients) → UsersIcon
│   └── Pipeline (/crm/pipeline) → ViewColumnsIcon
├── PRICING
│   ├── Rates (/pricing/rates) → CurrencyDollarIcon
│   └── Hotels (/pricing/hotels) → BuildingOfficeIcon
├── AI
│   ├── Helpdesk (/helpdesk) → SparklesIcon
│   └── Knowledge (/knowledge) → BookOpenIcon
└── FOOTER
    ├── Settings (/settings) → Cog6ToothIcon
    └── User Menu (dropdown)
        ├── Profile
        ├── Settings
        └── Logout
```

### Breadcrumb Patterns
```
Quote Detail: Quotes > QT-2024-001
Client Detail: CRM > Clients > John Smith
Hotel Detail: Pricing > Hotels > Safari Lodge
Invoice Detail: Invoices > INV-2024-001
Settings Tab: Settings > Team
```

### Conditional Navigation
```
Admin-only routes:
├── /settings/team → Only visible if isAdmin
└── User management actions → Hidden for non-admins

Auth-based redirects:
├── Unauthenticated → Always redirect to /login
├── Authenticated + /login → Redirect to /
└── requireAdmin + !isAdmin → Redirect to /

Return navigation:
├── After login → Return to original destination (state.from)
├── After action → Return to list page
└── Close modal → Stay on current page
```

---

## 8. MODALS & DIALOGS

### Confirmation Modals
```
ConfirmModal (generic)
├── Trigger: Delete, deactivate, destructive actions
├── Props: title, message, confirmText, cancelText, danger, onConfirm, onCancel
├── Danger mode: Red confirm button
└── Buttons: [Cancel] [Confirm]

Delete Quote Confirmation
├── Title: "Delete Quote"
├── Message: "Are you sure you want to delete QT-2024-001? This cannot be undone."
├── Danger: true
└── On Confirm: quotesApi.delete() → Navigate to /quotes

Deactivate User Confirmation
├── Title: "Deactivate User"
├── Message: "Are you sure you want to deactivate {name}? They will no longer be able to access the platform."
├── Danger: true
└── On Confirm: usersApi.deactivate() → Refresh list

Cancel Invitation Confirmation
├── Title: "Cancel Invitation"
├── Message: "Cancel invitation for {email}?"
├── Danger: true
└── On Confirm: usersApi.cancelInvitation() → Refresh list
```

### Action Modals
```
SendQuoteModal
├── Trigger: [Send Quote] button on quote detail
├── Content: Recipient email display, optional message
├── Buttons: [Cancel] [Send]
└── On Confirm: quotesApi.resend() → Show success toast

RecordPaymentModal
├── Trigger: [Record Payment] button on invoice detail
├── Content: Payment form (amount, method, reference, date, notes)
├── Buttons: [Cancel] [Record Payment]
└── On Confirm: invoicesApi.recordPayment() → Refresh invoice

AddClientModal
├── Trigger: [+ Add Client] button on clients list
├── Content: Client form (name, email, phone, source)
├── Buttons: [Cancel] [Add Client]
└── On Confirm: crmApi.createClient() → Refresh list

UploadDocumentModal
├── Trigger: [Upload Document] button on knowledge page
├── Content: File picker, category dropdown, tags input, visibility toggle
├── Buttons: [Cancel] [Upload]
└── On Confirm: knowledgeApi.uploadDocument() → Refresh list

InviteUserModal
├── Trigger: [Invite Member] button on team settings
├── Content: Invite form (name, email, role)
├── Buttons: [Cancel] [Send Invitation]
└── On Confirm: usersApi.invite() → Refresh invitations

EditUserModal
├── Trigger: [Edit] button on user row
├── Content: Edit form (name, role - email readonly)
├── Buttons: [Cancel] [Save Changes]
└── On Confirm: usersApi.update() → Refresh users

LogoCropModal
├── Trigger: Logo upload in branding settings
├── Content: Image cropper with zoom, preview
├── Buttons: [Cancel] [Save]
└── On Confirm: Return cropped blob to parent

CreateInvoiceModal
├── Trigger: [+ Create Invoice] button
├── Options: From existing quote OR manual
├── Content: Quote selector OR manual line items form
├── Buttons: [Cancel] [Create Invoice]
└── On Confirm: invoicesApi.createFromQuote() or createManual()
```

### Dropdown Menus
```
User Menu (Header)
├── Trigger: Click user avatar
├── Items:
│   ├── Profile → /settings (profile tab)
│   ├── Settings → /settings
│   └── Logout → authApi.logout() → /login

Actions Dropdown (Quote/Invoice detail)
├── Trigger: "..." button
├── Items:
│   ├── Edit → Enable edit mode
│   ├── Duplicate → Create copy
│   ├── Convert to Invoice (quote only)
│   └── Delete → Open confirmation

Notifications Dropdown (Header)
├── Trigger: Bell icon
├── Content: List of recent notifications
├── Actions:
│   ├── Mark as read → notificationsApi.markRead()
│   └── Mark all read → notificationsApi.markAllRead()
```

---

## 9. USER ROLES & PERMISSIONS

### Roles
```
admin
├── Full access to all features
├── Can manage team members
├── Can invite new users
├── Can deactivate users
├── Can view all settings
└── Can access /settings/team

consultant
├── Standard user access
├── Can create/edit quotes
├── Can create/edit invoices
├── Can manage CRM clients
├── Can view analytics
├── Cannot manage team
└── Cannot access /settings/team
```

### Permission Checks
```javascript
// In AuthContext
isAdmin = user?.role === 'admin'
isConsultant = user?.role === 'consultant'

// Route protection
<ProtectedRoute>            // Requires authentication
<AdminRoute>                // Requires admin role

// UI conditional rendering
{isAdmin && <NavLink to="/settings/team">Team</NavLink>}
{isAdmin && <EditButton onClick={...} />}

// API-level enforcement
// Backend validates role on protected endpoints
```

### Feature Access Matrix
```
Feature                    | Admin | Consultant
---------------------------|-------|------------
View Dashboard             |   ✓   |     ✓
Create Quotes              |   ✓   |     ✓
Edit Own Quotes            |   ✓   |     ✓
Delete Quotes              |   ✓   |     ✓
Create Invoices            |   ✓   |     ✓
Record Payments            |   ✓   |     ✓
View CRM                   |   ✓   |     ✓
Manage Clients             |   ✓   |     ✓
View Analytics             |   ✓   |     ✓
View Pricing               |   ✓   |     ✓
Use Helpdesk               |   ✓   |     ✓
Manage Knowledge Base      |   ✓   |     ✓
Company Settings           |   ✓   |     ✓
Branding Settings          |   ✓   |     ✓
Template Settings          |   ✓   |     ✓
Team Management            |   ✓   |     ✗
Invite Users               |   ✓   |     ✗
Deactivate Users           |   ✓   |     ✗
Privacy Settings           |   ✓   |     ✓
```

---

# INTERNAL ADMIN APPLICATION

## Overview
```
Purpose: Platform administration (no authentication)
Port: 5180
Framework: Same stack (React + Vite + Tailwind)
```

## Routes
```
/                   Dashboard - Platform stats overview
/tenants            Tenants list - All tenant organizations
/tenants/:id        Tenant detail - Individual tenant management
/usage              Usage stats - API usage across tenants
/knowledge          Knowledge manager - Central knowledge base
```

## Pages

### / - Admin Dashboard
```
Components:
├── Stats cards (Total Tenants, Active Users, API Calls, Storage)
├── Recent activity timeline
└── Quick actions

No API authentication required (internal network only)
```

### /tenants - Tenants List
```
Components:
├── Search bar
├── Tenants table
│   ├── Tenant ID
│   ├── Company name
│   ├── Users count
│   ├── Created date
│   ├── Status
│   └── Actions
└── Pagination
```

### /tenants/:id - Tenant Detail
```
Components:
├── Tenant info card
├── Users list
├── Usage stats
├── Settings (can override)
└── Danger zone (deactivate tenant)
```

### /usage - Usage Stats
```
Components:
├── Period selector
├── API calls chart
├── Top endpoints table
├── Per-tenant breakdown
└── Export button
```

### /knowledge - Knowledge Manager
```
Components:
├── Central knowledge base management
├── Document upload
├── Category management
└── Index controls
```

---

## Appendix: File Structure

```
frontend/
├── tenant-dashboard/
│   ├── src/
│   │   ├── main.jsx                    # App entry point
│   │   ├── App.jsx                     # Router setup
│   │   ├── index.css                   # Global styles + Tailwind
│   │   ├── components/
│   │   │   ├── layout/
│   │   │   │   ├── Layout.jsx
│   │   │   │   ├── Sidebar.jsx
│   │   │   │   └── Header.jsx
│   │   │   ├── ui/
│   │   │   │   ├── Toggle.jsx
│   │   │   │   ├── Skeleton.jsx
│   │   │   │   └── LogoCropModal.jsx
│   │   │   └── ProtectedRoute.jsx
│   │   ├── context/
│   │   │   ├── AuthContext.jsx
│   │   │   ├── AppContext.jsx
│   │   │   └── ThemeContext.jsx
│   │   ├── services/
│   │   │   └── api.js                  # All API modules + caching
│   │   └── pages/
│   │       ├── Dashboard.jsx
│   │       ├── Login.jsx
│   │       ├── Helpdesk.jsx
│   │       ├── Analytics.jsx
│   │       ├── Settings.jsx
│   │       ├── quotes/
│   │       │   ├── QuotesList.jsx
│   │       │   ├── GenerateQuote.jsx
│   │       │   └── QuoteDetail.jsx
│   │       ├── invoices/
│   │       │   ├── InvoicesList.jsx
│   │       │   └── InvoiceDetail.jsx
│   │       ├── crm/
│   │       │   ├── Pipeline.jsx
│   │       │   ├── ClientsList.jsx
│   │       │   └── ClientDetail.jsx
│   │       ├── pricing/
│   │       │   ├── PricingRates.jsx
│   │       │   └── PricingHotels.jsx
│   │       ├── knowledge/
│   │       │   └── KnowledgeDocuments.jsx
│   │       └── settings/
│   │           ├── TeamSettings.jsx
│   │           ├── PrivacySettings.jsx
│   │           └── TemplateBuilder.jsx
│   ├── package.json
│   └── vite.config.js
│
└── internal-admin/
    ├── src/
    │   ├── main.jsx
    │   ├── App.jsx                     # Routes + Layout inline
    │   └── pages/
    │       ├── Dashboard.jsx
    │       ├── TenantsList.jsx
    │       ├── TenantDetail.jsx
    │       ├── UsageStats.jsx
    │       └── KnowledgeManager.jsx
    ├── package.json
    └── vite.config.js
```

---

## Key Patterns for Replication

### 1. Multi-Tenant Header Injection
```javascript
// Always include X-Client-ID header (except login)
api.interceptors.request.use((config) => {
  if (!isLoginRequest) {
    config.headers['X-Client-ID'] = getTenantId();
  }
});
```

### 2. Token Refresh with Queue
```javascript
// Queue failed requests during refresh
let failedQueue = [];
// Process queue after successful refresh
const processQueue = (error, token) => {...};
```

### 3. Stale-While-Revalidate Caching
```javascript
// Return stale data immediately, refresh in background
const fetchWithSWR = async (key, fetcher, ttl) => {
  const stale = getStaleCached(key);
  if (stale) {
    fetcher().then(res => setCached(key, res.data, ttl));
    return { data: stale.data };
  }
  // Fresh fetch if no cache
};
```

### 4. Protected Route Pattern
```jsx
<ProtectedRoute requireAdmin={false}>
  <Component />
</ProtectedRoute>
```

### 5. Lazy Loading Routes
```javascript
const Dashboard = lazy(() => import('./pages/Dashboard'));
// With Suspense + Skeleton fallback
```

### 6. Context Provider Stack
```jsx
<AuthProvider>
  <AppProvider>
    <ThemeProvider>
      <App />
    </ThemeProvider>
  </AppProvider>
</AuthProvider>
```

### 7. Theme CSS Variables
```javascript
// Apply dynamically from branding settings
document.documentElement.style.setProperty('--color-primary', branding.primary);
```

---

*Document generated for frontend replication purposes. Covers all pages, components, buttons, forms, modals, API calls, state management, and user permissions.*
