from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()


@router.get("/osha", response_class=HTMLResponse)
async def osha_dashboard():
    """Serve the OSHA inspection tracker page."""
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TSG Safety Tracker</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        .loader {
            border: 3px solid #f3f3f3;
            border-top: 3px solid #3b82f6;
            border-radius: 50%;
            width: 24px;
            height: 24px;
            animation: spin 1s linear infinite;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        .dragging {
            opacity: 0.5;
            background: #e5e7eb;
        }
        .drag-over {
            border-left: 3px solid #3b82f6;
        }
        th[draggable="true"] {
            cursor: grab;
        }
        th[draggable="true"]:active {
            cursor: grabbing;
        }
    </style>
</head>
<body class="bg-gray-100 min-h-screen">
    <nav class="bg-gray-900 text-white shadow-lg">
        <div class="max-w-7xl mx-auto px-4">
            <div class="flex justify-between items-center h-16">
                <div class="flex items-center space-x-8">
                    <h1 class="text-xl font-bold">TSG Safety</h1>
                    <div class="flex space-x-1">
                        <a href="/" class="px-4 py-2 rounded-md text-sm font-medium text-gray-300 hover:text-white hover:bg-gray-700">Overview</a>
                        <a href="/osha" class="px-4 py-2 rounded-md text-sm font-medium bg-blue-600 text-white">OSHA</a>
                        <a href="/epa" class="px-4 py-2 rounded-md text-sm font-medium text-gray-300 hover:text-white hover:bg-gray-700">EPA</a>
                        <a href="/crm" class="px-4 py-2 rounded-md text-sm font-medium text-gray-300 hover:text-white hover:bg-gray-700">CRM</a>
                    </div>
                </div>
                <div class="flex items-center gap-4">
                    <button onclick="openEnrichedCompaniesModal()" class="bg-green-600 hover:bg-green-700 px-4 py-2 rounded flex items-center gap-2 text-sm">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"></path>
                        </svg>
                        Enriched Companies
                    </button>
                    <button onclick="triggerInspectionSync()" class="bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded text-sm">
                        Sync Inspections
                    </button>
                    <button onclick="triggerViolationSync()" class="bg-purple-600 hover:bg-purple-700 px-4 py-2 rounded text-sm">
                        Sync Violations
                    </button>
                </div>
            </div>
        </div>
    </nav>

    <main class="max-w-7xl mx-auto px-4 py-8">
        <div class="mb-6">
            <h2 class="text-2xl font-bold text-gray-800">OSHA Inspections</h2>
            <p class="text-gray-600 mt-1">Track inspections, violations, and enrichment status</p>
        </div>
        <div class="flex flex-col lg:flex-row gap-6">
            <!-- Left Sidebar - Stats Cards -->
            <div class="lg:w-48 flex-shrink-0">
                <div class="sticky top-6 space-y-2">
                    <div class="bg-white p-2.5 rounded-lg shadow">
                        <h3 class="text-gray-500 text-[10px] uppercase tracking-wider mb-0.5">Data Range</h3>
                        <p id="stat-date-range" class="text-xs font-medium text-gray-700">Loading...</p>
                        <p id="stat-date-span" class="text-[10px] text-gray-500"></p>
                    </div>
                    <!-- New Inspections Widget -->
                    <div class="bg-gradient-to-br from-blue-50 to-cyan-50 p-2.5 rounded-lg shadow border border-blue-200 cursor-pointer hover:shadow-md transition-shadow" onclick="openNewInspectionsModal()">
                        <h3 class="text-gray-700 text-[10px] uppercase tracking-wider font-semibold mb-1">New Inspections (7d)</h3>
                        <p id="new-inspections-count" class="text-lg font-bold text-blue-600">-</p>
                        <p id="new-inspections-companies" class="text-[10px] text-gray-600">Loading...</p>
                    </div>
                    <!-- New Violations Widget -->
                    <div class="bg-gradient-to-br from-orange-50 to-red-50 p-2.5 rounded-lg shadow border border-orange-200 cursor-pointer hover:shadow-md transition-shadow" onclick="openNewViolationsModal()">
                        <h3 class="text-gray-700 text-[10px] uppercase tracking-wider font-semibold mb-1">New Penalties (45d)</h3>
                        <p id="new-violations-count" class="text-lg font-bold text-orange-600">-</p>
                        <p id="new-violations-companies" class="text-[10px] text-gray-600">Loading...</p>
                        <p id="new-violations-penalties" class="text-[10px] text-gray-600"></p>
                    </div>
                    <!-- CRM Pipeline Widget -->
                    <a href="/crm" class="block bg-gradient-to-br from-purple-50 to-indigo-50 p-2.5 rounded-lg shadow border border-purple-200 cursor-pointer hover:shadow-md transition-shadow">
                        <h3 class="text-gray-700 text-[10px] uppercase tracking-wider font-semibold mb-1">CRM Pipeline</h3>
                        <p id="crm-total-prospects" class="text-lg font-bold text-purple-600">-</p>
                        <p id="crm-pipeline-value" class="text-[10px] text-gray-600">Loading...</p>
                    </a>
                    <!-- Upcoming Callbacks Widget -->
                    <a href="/crm" class="block bg-gradient-to-br from-green-50 to-emerald-50 p-2.5 rounded-lg shadow border border-green-200 cursor-pointer hover:shadow-md transition-shadow">
                        <h3 class="text-gray-700 text-[10px] uppercase tracking-wider font-semibold mb-1">Callbacks (7d)</h3>
                        <p id="crm-upcoming-callbacks" class="text-lg font-bold text-green-600">-</p>
                        <p id="crm-overdue-callbacks" class="text-[10px] text-red-600"></p>
                    </a>
                    <div class="bg-white p-2.5 rounded-lg shadow">
                        <h3 class="text-gray-500 text-[10px] uppercase tracking-wider mb-0.5">Total Inspections</h3>
                        <p id="stat-total" class="text-lg font-bold text-blue-600">-</p>
                    </div>
                    <div class="bg-white p-2.5 rounded-lg shadow">
                        <h3 class="text-gray-500 text-[10px] uppercase tracking-wider mb-0.5">Total Penalties</h3>
                        <p id="stat-penalties" class="text-lg font-bold text-red-600">-</p>
                    </div>
                    <div class="bg-white p-2.5 rounded-lg shadow">
                        <h3 class="text-gray-500 text-[10px] uppercase tracking-wider mb-0.5">States Covered</h3>
                        <p id="stat-states" class="text-lg font-bold text-green-600">-</p>
                    </div>
                    <div class="bg-white p-2.5 rounded-lg shadow">
                        <h3 class="text-gray-500 text-[10px] uppercase tracking-wider mb-0.5">Avg Penalty</h3>
                        <p id="stat-avg" class="text-lg font-bold text-orange-600">-</p>
                    </div>
                </div>
            </div>

            <!-- Right Content - Filters and Table -->
            <div class="flex-1 min-w-0">
                <!-- Filters -->
                <div class="bg-white p-6 rounded-lg shadow mb-6">
                    <h2 class="text-lg font-semibold mb-4">Filters</h2>
                    <div class="grid grid-cols-1 md:grid-cols-5 gap-4">
                        <div>
                            <label class="block text-sm text-gray-600 mb-1">Search</label>
                            <input type="text" id="filter-search" placeholder="Company name..."
                                class="w-full border rounded px-3 py-2" onkeyup="debounceSearch()">
                        </div>
                        <div>
                            <label class="block text-sm text-gray-600 mb-1">Activity #</label>
                            <input type="text" id="filter-activity" placeholder="Activity number..."
                                class="w-full border rounded px-3 py-2" onkeyup="debounceSearch()">
                        </div>
                        <div>
                            <label class="block text-sm text-gray-600 mb-1">State</label>
                            <select id="filter-state" class="w-full border rounded px-3 py-2" onchange="applyFilters()">
                                <option value="">All States</option>
                            </select>
                        </div>
                        <div>
                            <label class="block text-sm text-gray-600 mb-1">Type</label>
                            <select id="filter-type" class="w-full border rounded px-3 py-2" onchange="applyFilters()">
                                <option value="">All Types</option>
                            </select>
                        </div>
                        <div>
                            <label class="block text-sm text-gray-600 mb-1">Violations</label>
                            <select id="filter-violations" class="w-full border rounded px-3 py-2" onchange="applyFilters()">
                                <option value="">All</option>
                                <option value="true">With Violations</option>
                                <option value="false">Without Violations</option>
                            </select>
                        </div>
                    </div>
                    <div class="grid grid-cols-1 md:grid-cols-5 gap-4 mt-4">
                        <div>
                            <label class="block text-sm text-gray-600 mb-1">Multiple Inspections</label>
                            <select id="filter-multiple" class="w-full border rounded px-3 py-2" onchange="applyFilters()">
                                <option value="">All Companies</option>
                                <option value="true">Multiple Inspections Only</option>
                            </select>
                        </div>
                        <div>
                            <label class="block text-sm text-gray-600 mb-1">Start Date</label>
                            <input type="date" id="filter-start" class="w-full border rounded px-3 py-2" onchange="applyFilters()">
                        </div>
                        <div>
                            <label class="block text-sm text-gray-600 mb-1">End Date</label>
                            <input type="date" id="filter-end" class="w-full border rounded px-3 py-2" onchange="applyFilters()">
                        </div>
                        <div>
                            <label class="block text-sm text-gray-600 mb-1">Min Penalty</label>
                            <input type="number" id="filter-min-penalty" placeholder="0"
                                class="w-full border rounded px-3 py-2" onchange="applyFilters()">
                        </div>
                        <div>
                            <label class="block text-sm text-gray-600 mb-1">Max Penalty</label>
                            <input type="number" id="filter-max-penalty" placeholder="No limit"
                                class="w-full border rounded px-3 py-2" onchange="applyFilters()">
                        </div>
                        <div class="flex items-end">
                            <button onclick="clearFilters()" class="bg-gray-200 hover:bg-gray-300 px-4 py-2 rounded w-full">
                                Clear Filters
                            </button>
                        </div>
                    </div>
                </div>

                <!-- Inspections Table -->
                <div class="bg-white rounded-lg shadow">
                    <div class="p-6 border-b flex justify-between items-center">
                        <h2 class="text-lg font-semibold">Inspections</h2>
                        <div id="loading" class="loader hidden"></div>
                    </div>
                    <div class="overflow-x-auto">
                        <table class="w-full" id="inspections-data-table">
                            <thead class="bg-gray-50" id="table-header">
                                <tr id="header-row"></tr>
                            </thead>
                            <tbody id="inspections-table" class="divide-y">
                                <tr><td colspan="9" class="px-4 py-8 text-center text-gray-500">Loading...</td></tr>
                            </tbody>
                        </table>
                    </div>
                    <!-- Pagination -->
                    <div class="p-4 border-t flex justify-between items-center">
                        <div id="pagination-info" class="text-sm text-gray-500"></div>
                        <div class="flex gap-2">
                            <button id="btn-prev" onclick="prevPage()" class="px-4 py-2 border rounded hover:bg-gray-100 disabled:opacity-50" disabled>
                                Previous
                            </button>
                            <button id="btn-next" onclick="nextPage()" class="px-4 py-2 border rounded hover:bg-gray-100 disabled:opacity-50" disabled>
                                Next
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </main>

    <!-- Detail Modal -->
    <div id="modal" class="fixed inset-0 bg-black bg-opacity-50 hidden flex items-center justify-center z-50">
        <div class="bg-white rounded-lg shadow-xl max-w-4xl w-full mx-4 max-h-[90vh] overflow-y-auto">
            <div id="modal-content"></div>
        </div>
    </div>

    <!-- Enriched Companies Modal -->
    <div id="enriched-companies-modal" class="fixed inset-0 bg-black bg-opacity-50 hidden flex items-center justify-center z-50">
        <div class="bg-white rounded-lg shadow-xl max-w-6xl w-full mx-4 max-h-[90vh] overflow-hidden flex flex-col">
            <div class="p-6 border-b flex justify-between items-center flex-shrink-0">
                <div class="flex items-center gap-4">
                    <h2 class="text-xl font-semibold">Enriched Companies</h2>
                    <span id="enriched-count" class="text-sm text-gray-500"></span>
                </div>
                <button onclick="closeEnrichedCompaniesModal()" class="text-gray-500 hover:text-gray-700 text-2xl">&times;</button>
            </div>
            <div class="overflow-y-auto flex-1">
                <table class="min-w-full divide-y divide-gray-200">
                    <thead class="bg-gray-50 sticky top-0">
                        <tr>
                            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Company</th>
                            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Industry</th>
                            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Location</th>
                            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Phone</th>
                            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Penalty</th>
                            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Enriched</th>
                            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
                        </tr>
                    </thead>
                    <tbody id="enriched-companies-list" class="bg-white divide-y divide-gray-200">
                        <!-- Companies loaded dynamically -->
                    </tbody>
                </table>
                <div id="no-enriched-companies" class="hidden p-8 text-center text-gray-500">
                    <svg class="w-12 h-12 mx-auto mb-4 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"></path>
                    </svg>
                    <p class="text-lg font-medium">No enriched companies yet</p>
                    <p class="text-sm mt-1">Click "Enrich" on an inspection to gather company data</p>
                </div>
            </div>
        </div>
    </div>

    <!-- Company Detail Modal -->
    <div id="company-detail-modal" class="fixed inset-0 bg-black bg-opacity-50 hidden flex items-center justify-center z-[60]">
        <div class="bg-white rounded-lg shadow-xl max-w-4xl w-full mx-4 max-h-[90vh] overflow-y-auto">
            <div id="company-detail-content"></div>
        </div>
    </div>

    <!-- Email Generation Modal -->
    <div id="email-modal" class="fixed inset-0 bg-black bg-opacity-50 hidden flex items-center justify-center z-[70]">
        <div class="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-hidden flex flex-col">
            <div class="p-4 border-b flex justify-between items-center flex-shrink-0 bg-purple-50">
                <div class="flex items-center gap-3">
                    <svg class="w-5 h-5 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"></path>
                    </svg>
                    <h2 class="text-lg font-semibold text-gray-900">Generated Email</h2>
                </div>
                <button onclick="closeEmailModal()" class="text-gray-500 hover:text-gray-700 text-2xl">&times;</button>
            </div>
            <div class="p-4 border-b bg-gray-50">
                <p class="text-xs text-gray-500 uppercase tracking-wider mb-1">Subject Line</p>
                <p id="email-subject" class="text-sm font-medium text-gray-900"></p>
            </div>
            <div class="overflow-y-auto flex-1 p-4">
                <pre id="email-body" class="whitespace-pre-wrap text-sm text-gray-800 font-sans leading-relaxed"></pre>
            </div>
            <div class="p-4 border-t flex justify-end gap-3 flex-shrink-0 bg-gray-50">
                <button onclick="closeEmailModal()" class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50">
                    Close
                </button>
                <button onclick="copyEmailToClipboard()" class="px-4 py-2 text-sm font-medium text-white bg-purple-600 rounded-md hover:bg-purple-700 flex items-center gap-2">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3"></path>
                    </svg>
                    Copy to Clipboard
                </button>
            </div>
        </div>
    </div>

    <!-- New Inspections Modal -->
    <div id="new-inspections-modal" class="fixed inset-0 bg-black bg-opacity-50 hidden flex items-center justify-center z-50">
        <div class="bg-white rounded-lg shadow-xl max-w-5xl w-full mx-4 max-h-[90vh] flex flex-col">
            <div class="p-6 border-b flex justify-between items-center bg-gradient-to-r from-blue-50 to-cyan-50">
                <div>
                    <h2 class="text-xl font-semibold text-gray-800">New Inspections (Last 7 Days)</h2>
                    <p id="new-inspections-modal-subtitle" class="text-sm text-gray-600 mt-1"></p>
                </div>
                <button onclick="closeNewInspectionsModal()" class="text-gray-500 hover:text-gray-700 text-2xl">&times;</button>
            </div>
            <div class="flex-1 overflow-auto p-6">
                <table class="w-full">
                    <thead class="bg-gray-50 sticky top-0">
                        <tr>
                            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Company</th>
                            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Location</th>
                            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Type</th>
                            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Opened</th>
                            <th class="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Action</th>
                        </tr>
                    </thead>
                    <tbody id="new-inspections-list">
                        <tr><td colspan="5" class="px-4 py-8 text-center text-gray-500">Loading...</td></tr>
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <!-- New Violations Modal -->
    <div id="new-violations-modal" class="fixed inset-0 bg-black bg-opacity-50 hidden flex items-center justify-center z-50">
        <div class="bg-white rounded-lg shadow-xl max-w-5xl w-full mx-4 max-h-[90vh] flex flex-col">
            <div class="p-6 border-b flex justify-between items-center bg-gradient-to-r from-orange-50 to-red-50">
                <div>
                    <h2 class="text-xl font-semibold text-gray-800">New Penalties (Last 45 Days)</h2>
                    <p id="new-violations-modal-subtitle" class="text-sm text-gray-600 mt-1"></p>
                </div>
                <button onclick="closeNewViolationsModal()" class="text-gray-500 hover:text-gray-700 text-2xl">&times;</button>
            </div>
            <div class="flex-1 overflow-auto p-6">
                <table class="w-full">
                    <thead class="bg-gray-50 sticky top-0">
                        <tr>
                            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Company</th>
                            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Location</th>
                            <th class="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Citations</th>
                            <th class="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Penalty</th>
                            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Issued</th>
                            <th class="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Action</th>
                        </tr>
                    </thead>
                    <tbody id="new-violations-list">
                        <tr><td colspan="6" class="px-4 py-8 text-center text-gray-500">Loading...</td></tr>
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <script>
        const API_BASE = '/api/inspections';
        const CRM_API = '/api/crm';
        let currentPage = 1;
        let currentSort = 'open_date';
        let currentSortDesc = true;
        let totalPages = 1;
        let searchTimeout = null;
        let draggedColumn = null;

        // Column definitions - order can be changed by drag and drop
        let columnOrder = ['date', 'company', 'activity', 'location', 'type', 'violations', 'initial', 'current', 'reduction'];

        const columnDefs = {
            date: { label: 'Date', sortField: 'open_date', align: 'left', sortable: true },
            company: { label: 'Company', sortField: 'estab_name', align: 'left', sortable: true },
            activity: { label: 'Activity #', sortField: 'activity_nr', align: 'left', sortable: true },
            location: { label: 'Location', sortField: null, align: 'left', sortable: false },
            type: { label: 'Type', sortField: 'insp_type', align: 'left', sortable: true },
            violations: { label: 'Violations', sortField: 'violation_count', align: 'center', sortable: true },
            initial: { label: 'Initial', sortField: null, align: 'right', sortable: false },
            current: { label: 'Current', sortField: 'total_current_penalty', align: 'right', sortable: true },
            reduction: { label: 'Reduction', sortField: null, align: 'right', sortable: false }
        };

        // Initialize
        document.addEventListener('DOMContentLoaded', () => {
            // Load saved column order from localStorage
            const savedOrder = localStorage.getItem('oshaTrackerColumnOrder');
            if (savedOrder) {
                try {
                    columnOrder = JSON.parse(savedOrder);
                } catch (e) {}
            }
            renderTableHeader();
            loadFilters();
            loadStats();
            loadInspections();
            loadCronStatus();
            loadDateRange();
            loadNewInspections();
            loadNewViolations();
        });

        async function loadDateRange() {
            try {
                const data = await fetch(`${API_BASE}/date-range`).then(r => r.json());
                const rangeEl = document.getElementById('stat-date-range');
                const spanEl = document.getElementById('stat-date-span');

                if (data.earliest_date && data.latest_date) {
                    const earliest = new Date(data.earliest_date);
                    const latest = new Date(data.latest_date);

                    const formatDate = (d) => d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
                    rangeEl.innerHTML = `${formatDate(earliest)}<br>to ${formatDate(latest)}`;

                    // Calculate span
                    const diffTime = Math.abs(latest - earliest);
                    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
                    const diffMonths = Math.round(diffDays / 30);
                    const diffYears = (diffDays / 365).toFixed(1);

                    if (diffDays < 60) {
                        spanEl.textContent = `${diffDays} days of data`;
                    } else if (diffMonths < 24) {
                        spanEl.textContent = `~${diffMonths} months of data`;
                    } else {
                        spanEl.textContent = `~${diffYears} years of data`;
                    }
                } else {
                    rangeEl.textContent = 'No data';
                    spanEl.textContent = '';
                }
            } catch (e) {
                console.error('Error loading date range:', e);
                document.getElementById('stat-date-range').textContent = 'Error';
            }
        }

        function renderTableHeader() {
            const headerRow = document.getElementById('header-row');
            headerRow.innerHTML = '';

            columnOrder.forEach((colId, index) => {
                const col = columnDefs[colId];
                const th = document.createElement('th');
                th.className = `px-4 py-3 text-${col.align} text-sm font-medium text-gray-500 hover:bg-gray-100 select-none`;
                th.draggable = true;
                th.dataset.column = colId;
                th.dataset.index = index;

                if (col.sortable) {
                    th.classList.add('cursor-pointer');
                    th.onclick = () => sortBy(col.sortField);
                }

                th.textContent = col.label;

                // Drag events
                th.addEventListener('dragstart', handleDragStart);
                th.addEventListener('dragend', handleDragEnd);
                th.addEventListener('dragover', handleDragOver);
                th.addEventListener('dragenter', handleDragEnter);
                th.addEventListener('dragleave', handleDragLeave);
                th.addEventListener('drop', handleDrop);

                headerRow.appendChild(th);
            });
        }

        function handleDragStart(e) {
            draggedColumn = e.target;
            e.target.classList.add('dragging');
            e.dataTransfer.effectAllowed = 'move';
            e.dataTransfer.setData('text/plain', e.target.dataset.index);
        }

        function handleDragEnd(e) {
            e.target.classList.remove('dragging');
            document.querySelectorAll('#header-row th').forEach(th => {
                th.classList.remove('drag-over');
            });
            draggedColumn = null;
        }

        function handleDragOver(e) {
            e.preventDefault();
            e.dataTransfer.dropEffect = 'move';
        }

        function handleDragEnter(e) {
            e.preventDefault();
            if (e.target.tagName === 'TH' && e.target !== draggedColumn) {
                e.target.classList.add('drag-over');
            }
        }

        function handleDragLeave(e) {
            e.target.classList.remove('drag-over');
        }

        function handleDrop(e) {
            e.preventDefault();
            e.target.classList.remove('drag-over');

            if (e.target.tagName !== 'TH' || e.target === draggedColumn) return;

            const fromIndex = parseInt(e.dataTransfer.getData('text/plain'));
            const toIndex = parseInt(e.target.dataset.index);

            if (fromIndex === toIndex) return;

            // Reorder columns
            const [removed] = columnOrder.splice(fromIndex, 1);
            columnOrder.splice(toIndex, 0, removed);

            // Save to localStorage
            localStorage.setItem('oshaTrackerColumnOrder', JSON.stringify(columnOrder));

            // Re-render
            renderTableHeader();
            loadInspections();
        }

        async function loadFilters() {
            try {
                const [states, types] = await Promise.all([
                    fetch(`${API_BASE}/states`).then(r => r.json()),
                    fetch(`${API_BASE}/types`).then(r => r.json())
                ]);

                const stateSelect = document.getElementById('filter-state');
                states.forEach(s => {
                    const opt = document.createElement('option');
                    opt.value = s.state;
                    opt.textContent = `${s.state} (${s.count})`;
                    stateSelect.appendChild(opt);
                });

                const typeSelect = document.getElementById('filter-type');
                types.forEach(t => {
                    const opt = document.createElement('option');
                    opt.value = t.type;
                    opt.textContent = `${getInspectionTypeWithCode(t.type)} (${t.count})`;
                    typeSelect.appendChild(opt);
                });
            } catch (e) {
                console.error('Error loading filters:', e);
            }
        }

        async function loadStats() {
            try {
                const params = getFilterParams();
                const queryString = new URLSearchParams(params).toString();
                const stats = await fetch(`${API_BASE}/stats?${queryString}`).then(r => r.json());

                document.getElementById('stat-total').textContent = stats.total_inspections.toLocaleString();
                document.getElementById('stat-penalties').textContent = '$' + stats.total_penalties.toLocaleString(undefined, {maximumFractionDigits: 0});
                document.getElementById('stat-states').textContent = stats.states_count;
                document.getElementById('stat-avg').textContent = '$' + stats.avg_penalty.toLocaleString(undefined, {maximumFractionDigits: 0});
            } catch (e) {
                console.error('Error loading stats:', e);
            }
        }

        async function loadNewViolations() {
            try {
                const params = {
                    days: 45,
                    ...getFilterParams()
                };
                const queryString = new URLSearchParams(params).toString();
                const data = await fetch(`${API_BASE}/violations/recent?${queryString}`).then(r => r.json());

                document.getElementById('new-violations-count').textContent = data.count;
                document.getElementById('new-violations-companies').textContent = `${data.total_companies} ${data.total_companies === 1 ? 'Company' : 'Companies'}`;
                document.getElementById('new-violations-penalties').textContent = `$${data.total_penalties.toLocaleString(undefined, {maximumFractionDigits: 0})} in Penalties`;

                // Store data for modal
                window.newViolationsData = data;
            } catch (e) {
                console.error('Error loading new violations:', e);
                document.getElementById('new-violations-count').textContent = '0';
                document.getElementById('new-violations-companies').textContent = 'No new violations';
            }
        }

        async function loadNewInspections() {
            try {
                const params = {
                    days: 7,
                    ...getFilterParams()
                };
                const queryString = new URLSearchParams(params).toString();
                const data = await fetch(`${API_BASE}/recent?${queryString}`).then(r => r.json());

                document.getElementById('new-inspections-count').textContent = data.count;
                document.getElementById('new-inspections-companies').textContent = `${data.unique_companies} ${data.unique_companies === 1 ? 'Company' : 'Companies'}`;

                // Store data for modal
                window.newInspectionsData = data;
            } catch (e) {
                console.error('Error loading new inspections:', e);
                document.getElementById('new-inspections-count').textContent = '0';
                document.getElementById('new-inspections-companies').textContent = 'No new inspections';
            }
        }

        function openNewInspectionsModal() {
            const modal = document.getElementById('new-inspections-modal');
            const data = window.newInspectionsData;

            if (!data || !data.items || data.items.length === 0) {
                alert('No new inspections found in the last 7 days.');
                return;
            }

            // Update subtitle
            document.getElementById('new-inspections-modal-subtitle').textContent =
                `${data.count} inspections from ${data.unique_companies} companies`;

            // Populate table
            const tbody = document.getElementById('new-inspections-list');
            tbody.innerHTML = data.items.map(item => {
                const openDate = new Date(item.open_date);
                const timeAgo = getTimeAgo(openDate);

                return `
                    <tr class="border-b hover:bg-blue-50 transition-colors">
                        <td class="px-4 py-3">
                            <div class="font-medium text-gray-900">${item.estab_name}</div>
                            <div class="text-xs text-gray-500">Inspection #${item.activity_nr}</div>
                        </td>
                        <td class="px-4 py-3 text-sm text-gray-600">
                            ${item.site_city || ''}${item.site_city && item.site_state ? ', ' : ''}${item.site_state || ''}
                        </td>
                        <td class="px-4 py-3 text-sm text-gray-600">
                            ${getInspectionTypeLabel(item.insp_type)}
                        </td>
                        <td class="px-4 py-3 text-sm text-gray-600">
                            <div>${timeAgo}</div>
                            <div class="text-xs text-gray-400">${openDate.toLocaleDateString()}</div>
                        </td>
                        <td class="px-4 py-3 text-center">
                            <button
                                onclick="showDetail(${item.inspection_id}); closeNewInspectionsModal();"
                                class="text-blue-600 hover:text-blue-800 text-sm font-medium"
                            >
                                View Details
                            </button>
                        </td>
                    </tr>
                `;
            }).join('');

            // Show modal
            modal.classList.remove('hidden');
        }

        function closeNewInspectionsModal() {
            const modal = document.getElementById('new-inspections-modal');
            modal.classList.add('hidden');
        }

        function openNewViolationsModal() {
            const modal = document.getElementById('new-violations-modal');
            const data = window.newViolationsData;

            if (!data || !data.items || data.items.length === 0) {
                alert('No new violations found in the last 45 days.');
                return;
            }

            // Update subtitle
            document.getElementById('new-violations-modal-subtitle').textContent =
                `${data.count} new citations across ${data.total_companies} companies - $${data.total_penalties.toLocaleString(undefined, {maximumFractionDigits: 0})} in penalties`;

            // Populate table
            const tbody = document.getElementById('new-violations-list');
            tbody.innerHTML = data.items.map(item => {
                const issuanceDate = new Date(item.issuance_date);
                const timeAgo = getTimeAgo(issuanceDate);

                return `
                    <tr class="border-b hover:bg-orange-50 transition-colors">
                        <td class="px-4 py-3">
                            <div class="font-medium text-gray-900">${item.estab_name}</div>
                            <div class="text-xs text-gray-500">Inspection #${item.activity_nr}</div>
                        </td>
                        <td class="px-4 py-3 text-sm text-gray-600">
                            ${item.site_city || ''}${item.site_city && item.site_state ? ', ' : ''}${item.site_state || ''}
                        </td>
                        <td class="px-4 py-3 text-center">
                            <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-orange-100 text-orange-800">
                                ${item.violation_count} citations
                            </span>
                        </td>
                        <td class="px-4 py-3 text-right font-semibold text-orange-600">
                            $${item.total_current_penalty.toLocaleString(undefined, {maximumFractionDigits: 0})}
                        </td>
                        <td class="px-4 py-3 text-sm text-gray-600">
                            <div>${timeAgo}</div>
                            <div class="text-xs text-gray-400">${issuanceDate.toLocaleDateString()}</div>
                        </td>
                        <td class="px-4 py-3 text-center">
                            <button
                                onclick="showDetail(${item.inspection_id}); closeNewViolationsModal();"
                                class="text-blue-600 hover:text-blue-800 text-sm font-medium"
                            >
                                View Details
                            </button>
                        </td>
                    </tr>
                `;
            }).join('');

            // Show modal
            modal.classList.remove('hidden');
        }

        function closeNewViolationsModal() {
            const modal = document.getElementById('new-violations-modal');
            modal.classList.add('hidden');
        }

        function getTimeAgo(date) {
            const seconds = Math.floor((new Date() - date) / 1000);

            const intervals = {
                year: 31536000,
                month: 2592000,
                week: 604800,
                day: 86400,
                hour: 3600,
                minute: 60
            };

            for (const [unit, secondsInUnit] of Object.entries(intervals)) {
                const interval = Math.floor(seconds / secondsInUnit);
                if (interval >= 1) {
                    return `${interval} ${unit}${interval !== 1 ? 's' : ''} ago`;
                }
            }

            return 'Just now';
        }

        function getFilterParams() {
            const params = {};
            const search = document.getElementById('filter-search').value;
            const activity = document.getElementById('filter-activity').value;
            const state = document.getElementById('filter-state').value;
            const type = document.getElementById('filter-type').value;
            const start = document.getElementById('filter-start').value;
            const end = document.getElementById('filter-end').value;
            const minPenalty = document.getElementById('filter-min-penalty').value;
            const maxPenalty = document.getElementById('filter-max-penalty').value;
            const violations = document.getElementById('filter-violations').value;
            const multiple = document.getElementById('filter-multiple').value;

            if (search) params.search = search;
            if (activity) params.activity_nr = activity;
            if (state) params.state = state;
            if (type) params.insp_type = type;
            if (start) params.start_date = start;
            if (end) params.end_date = end;
            if (minPenalty) params.min_penalty = minPenalty;
            if (maxPenalty) params.max_penalty = maxPenalty;
            if (violations) params.has_violations = violations;
            if (multiple) params.multiple_inspections = multiple;

            return params;
        }

        async function loadInspections() {
            const loading = document.getElementById('loading');
            loading.classList.remove('hidden');

            try {
                const params = {
                    page: currentPage,
                    page_size: 50,
                    sort_by: currentSort,
                    sort_desc: currentSortDesc,
                    ...getFilterParams()
                };

                const queryString = new URLSearchParams(params).toString();

                // Add timeout to prevent infinite hanging
                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), 30000); // 30 second timeout

                const response = await fetch(`${API_BASE}?${queryString}`, { signal: controller.signal });
                clearTimeout(timeoutId);

                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }

                const data = await response.json();

                totalPages = data.total_pages;
                renderTable(data.items);
                updatePagination(data);
                loadStats();
            } catch (e) {
                console.error('Error loading inspections:', e);
                const errorMsg = e.name === 'AbortError'
                    ? 'Request timed out after 30 seconds. Please try again or contact support.'
                    : `Error loading data: ${e.message}`;
                document.getElementById('inspections-table').innerHTML =
                    `<tr><td colspan="${columnOrder.length}" class="px-4 py-8 text-center text-red-500">${errorMsg}</td></tr>`;
            } finally {
                loading.classList.add('hidden');
            }
        }

        function formatDate(dateStr) {
            if (!dateStr) return '-';
            const parts = dateStr.split('-');
            if (parts.length !== 3) return dateStr;
            return `${parts[1]}-${parts[2]}-${parts[0]}`;
        }

        function getReductionPercent(initial, current) {
            if (!initial || initial <= 0) return '-';
            if (!current) current = 0;
            const reduction = ((initial - current) / initial) * 100;
            if (reduction <= 0) return '0%';
            return reduction.toFixed(1) + '%';
        }

        function renderTable(items) {
            const tbody = document.getElementById('inspections-table');

            if (!items.length) {
                tbody.innerHTML = `<tr><td colspan="${columnOrder.length}" class="px-4 py-8 text-center text-gray-500">No inspections found</td></tr>`;
                return;
            }

            // Count company names to detect duplicates
            const companyNameCounts = {};
            items.forEach(i => {
                const name = (i.estab_name || '').trim().toLowerCase();
                companyNameCounts[name] = (companyNameCounts[name] || 0) + 1;
            });

            tbody.innerHTML = items.map(i => {
                const initial = i.total_initial_penalty || 0;
                const current = i.total_current_penalty || 0;
                const reductionPct = getReductionPercent(initial, current);
                const hasReduction = initial > 0 && current < initial;
                const violationCount = i.violation_count || 0;

                // Check if this company appears multiple times
                const companyName = (i.estab_name || '').trim().toLowerCase();
                const hasMultipleInspections = companyNameCounts[companyName] > 1;

                // Generate cells in column order
                const cells = columnOrder.map(colId => {
                    const col = columnDefs[colId];
                    const alignClass = col.align === 'right' ? 'text-right' : col.align === 'center' ? 'text-center' : '';

                    switch(colId) {
                        case 'date':
                            return `<td class="px-4 py-3 text-sm ${alignClass}">${formatDate(i.open_date)}</td>`;
                        case 'company':
                            return `<td class="px-4 py-3 ${alignClass}">
                                <div class="flex items-center gap-2">
                                    <div class="font-medium ${hasMultipleInspections ? 'text-orange-700' : ''}">${escapeHtml(i.estab_name)}</div>
                                    ${hasMultipleInspections ? `<span class="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium bg-orange-100 text-orange-800" title="Multiple inspections for this company">x${companyNameCounts[companyName]}</span>` : ''}
                                </div>
                            </td>`;
                        case 'activity':
                            return `<td class="px-4 py-3 text-sm text-gray-600 ${alignClass}">${i.activity_nr}</td>`;
                        case 'location':
                            return `<td class="px-4 py-3 text-sm ${alignClass}">${escapeHtml(i.site_city || '')}${i.site_city && i.site_state ? ', ' : ''}${i.site_state || ''}</td>`;
                        case 'type':
                            return `<td class="px-4 py-3 text-sm ${alignClass}">${getInspectionTypeLabel(i.insp_type)}</td>`;
                        case 'violations':
                            return `<td class="px-4 py-3 text-sm ${alignClass}"><span class="inline-flex items-center justify-center min-w-[24px] px-2 py-0.5 rounded-full text-xs font-medium ${violationCount > 0 ? 'bg-red-100 text-red-800' : 'bg-gray-100 text-gray-600'}">${violationCount}</span></td>`;
                        case 'initial':
                            return `<td class="px-4 py-3 text-sm text-gray-600 ${alignClass}">${initial > 0 ? '$' + initial.toLocaleString() : '-'}</td>`;
                        case 'current':
                            return `<td class="px-4 py-3 text-sm font-medium ${current > 0 ? 'text-red-600' : ''} ${alignClass}">${current > 0 ? '$' + current.toLocaleString() : '-'}</td>`;
                        case 'reduction':
                            return `<td class="px-4 py-3 text-sm ${hasReduction ? 'text-green-600 font-medium' : 'text-gray-400'} ${alignClass}">${reductionPct}</td>`;
                        default:
                            return `<td class="px-4 py-3 text-sm ${alignClass}">-</td>`;
                    }
                }).join('');

                return `<tr class="hover:bg-gray-50 cursor-pointer ${hasMultipleInspections ? 'bg-orange-50' : ''}" onclick="showDetail(${i.id})">${cells}</tr>`;
            }).join('');
        }

        function updatePagination(data) {
            document.getElementById('pagination-info').textContent =
                `Showing ${(data.page - 1) * data.page_size + 1}-${Math.min(data.page * data.page_size, data.total)} of ${data.total}`;

            document.getElementById('btn-prev').disabled = data.page <= 1;
            document.getElementById('btn-next').disabled = data.page >= data.total_pages;
        }

        function prevPage() {
            if (currentPage > 1) {
                currentPage--;
                loadInspections();
            }
        }

        function nextPage() {
            if (currentPage < totalPages) {
                currentPage++;
                loadInspections();
            }
        }

        function sortBy(field) {
            if (currentSort === field) {
                currentSortDesc = !currentSortDesc;
            } else {
                currentSort = field;
                currentSortDesc = true;
            }
            currentPage = 1;
            loadInspections();
        }

        function debounceSearch() {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                applyFilters();
            }, 300);
        }

        function applyFilters() {
            currentPage = 1;
            loadInspections();
            loadStats();
            loadNewInspections();
            loadNewViolations();
        }

        function clearFilters() {
            document.getElementById('filter-search').value = '';
            document.getElementById('filter-activity').value = '';
            document.getElementById('filter-state').value = '';
            document.getElementById('filter-type').value = '';
            document.getElementById('filter-start').value = '';
            document.getElementById('filter-end').value = '';
            document.getElementById('filter-min-penalty').value = '';
            document.getElementById('filter-max-penalty').value = '';
            document.getElementById('filter-violations').value = '';
            document.getElementById('filter-multiple').value = '';
            currentPage = 1;
            applyFilters();
        }

        // OSHA Inspection Type codes
        const INSPECTION_TYPE_LABELS = {
            'A': 'Fatality/Catastrophe',
            'B': 'Complaint',
            'C': 'Referral',
            'D': 'Monitoring',
            'E': 'Variance',
            'F': 'Follow-up',
            'G': 'Unprog Related',
            'H': 'Planned',
            'I': 'Unprog Other',
            'J': 'Prog Related',
            'K': 'Prog Other',
            'L': 'Other-L',
            'M': 'Fat/Cat Other'
        };

        function getInspectionTypeLabel(type) {
            if (!type) return '-';
            return INSPECTION_TYPE_LABELS[type] || type;
        }

        function getInspectionTypeWithCode(type) {
            if (!type) return '-';
            const label = INSPECTION_TYPE_LABELS[type];
            return label ? `${type} - ${label}` : type;
        }

        // OSHA Inspection Scope codes
        const INSPECTION_SCOPE_LABELS = {
            'A': 'Comprehensive',
            'B': 'Partial',
            'C': 'Records Only',
            'D': 'No Inspection'
        };

        function getInspectionScopeLabel(scope) {
            if (!scope) return '-';
            return INSPECTION_SCOPE_LABELS[scope] || scope;
        }

        function getInspectionScopeWithCode(scope) {
            if (!scope) return '-';
            const label = INSPECTION_SCOPE_LABELS[scope];
            return label ? `${scope} - ${label}` : scope;
        }

        // OSHA Owner Type codes
        const OWNER_TYPE_LABELS = {
            'A': 'Private',
            'B': 'Local Government',
            'C': 'State Government',
            'D': 'Federal Government'
        };

        function getOwnerTypeLabel(ownerType) {
            if (!ownerType) return '-';
            return OWNER_TYPE_LABELS[ownerType] || ownerType;
        }

        function getOwnerTypeWithCode(ownerType) {
            if (!ownerType) return '-';
            const label = OWNER_TYPE_LABELS[ownerType];
            return label ? `${ownerType} - ${label}` : ownerType;
        }

        function getViolationTypeLabel(type) {
            const labels = { 'S': 'Serious', 'W': 'Willful', 'R': 'Repeat', 'O': 'Other' };
            return labels[type] || type || '-';
        }

        function getViolationTypeBadge(type) {
            const colors = {
                'S': 'bg-red-100 text-red-800',
                'W': 'bg-purple-100 text-purple-800',
                'R': 'bg-orange-100 text-orange-800',
                'O': 'bg-gray-100 text-gray-800'
            };
            return colors[type] || 'bg-gray-100 text-gray-800';
        }

        function getPenaltyReductionHtml(initial, current) {
            if (!initial || initial <= 0) {
                return '<p class="text-xl font-bold text-gray-400">-</p>';
            }
            if (!current) current = 0;

            const reduction = initial - current;
            const percentReduction = ((reduction / initial) * 100).toFixed(1);

            if (reduction <= 0) {
                return '<p class="text-xl font-bold text-gray-500">0%</p>';
            }

            return `
                <p class="text-xl font-bold text-green-600">${percentReduction}%</p>
                <p class="text-xs text-gray-500">-$${reduction.toLocaleString()}</p>
            `;
        }

        function getOshaInspectionUrl(activityNr, estabName, state) {
            // OSHA's inspection detail URL requires an internal ID not available in the CSV
            // So we link to a search that will find this establishment's inspections
            const name = encodeURIComponent((estabName || '').substring(0, 40));
            const st = encodeURIComponent(state || '');
            return `https://www.osha.gov/pls/imis/establishment.search?p_logger=1&establishment=${name}&State=${st}`;
        }

        function getGoogleMapsUrl(address, city, state, zip) {
            const parts = [address, city, state, zip].filter(p => p);
            const query = encodeURIComponent(parts.join(', '));
            return `https://www.google.com/maps/search/?api=1&query=${query}`;
        }

        function getOshaStandardUrl(standard) {
            if (!standard) return null;

            // Handle format with dots like "1926.1053" or "1910.134(c)(1)"
            const dotMatch = standard.match(/^(\\d{4})\\.(\\d+)/);
            if (dotMatch) {
                const part = dotMatch[1];
                // Remove leading zeros from section number
                const sectionNum = dotMatch[2].replace(/^0+/, '') || '0';
                const section = dotMatch[1] + '.' + sectionNum;
                return `https://www.osha.gov/laws-regs/regulations/standardnumber/${part}/${section}`;
            }

            // Handle format like "19100110 B06" (no dots, with suffix)
            // First, get just the numeric part (before any space)
            const numericPart = standard.split(' ')[0].replace(/[^0-9]/g, '');
            if (!numericPart || numericPart.length < 5) return null;

            // Known OSHA part prefixes
            const parts = ['1910', '1926', '1915', '1904', '1903', '1928', '1990'];
            let part = null;
            let sectionRaw = null;

            for (const p of parts) {
                if (numericPart.startsWith(p)) {
                    part = p;
                    sectionRaw = numericPart.substring(4);
                    break;
                }
            }

            if (!part || !sectionRaw) return null;

            // Remove leading zeros from section number (but keep at least one digit)
            const sectionNum = sectionRaw.replace(/^0+/, '') || '0';
            const section = part + '.' + sectionNum;

            return `https://www.osha.gov/laws-regs/regulations/standardnumber/${part}/${section}`;
        }

        async function showDetail(id) {
            try {
                // Fetch inspection details and related inspections in parallel
                const [inspection, relatedInspections] = await Promise.all([
                    fetch(`${API_BASE}/${id}`).then(r => r.json()),
                    fetch(`${API_BASE}/${id}/related`).then(r => r.json())
                ]);

                // Store for email generation
                currentInspection = inspection;

                const mapsUrl = getGoogleMapsUrl(inspection.site_address, inspection.site_city, inspection.site_state, inspection.site_zip);
                const oshaUrl = getOshaInspectionUrl(inspection.activity_nr, inspection.estab_name, inspection.site_state);

                const addressLine = [
                    inspection.site_address,
                    [inspection.site_city, inspection.site_state].filter(Boolean).join(', '),
                    inspection.site_zip
                ].filter(Boolean).join(' ');

                // Build related inspections HTML
                let relatedHtml = '';
                if (relatedInspections && relatedInspections.length > 0) {
                    relatedHtml = `
                        <div class="border-t border-gray-200">
                            <div class="px-6 py-4 bg-gray-50 border-b border-gray-200">
                                <div class="flex items-center justify-between">
                                    <h3 class="text-sm font-semibold text-gray-900 uppercase tracking-wider">
                                        Other Inspections for This Company
                                    </h3>
                                    <span class="bg-blue-100 text-blue-800 text-xs font-medium px-2.5 py-0.5 rounded-full">
                                        ${relatedInspections.length} other inspection${relatedInspections.length !== 1 ? 's' : ''}
                                    </span>
                                </div>
                            </div>
                            <div class="divide-y divide-gray-100">
                                ${relatedInspections.map(r => `
                                    <div class="px-6 py-3 hover:bg-gray-50 cursor-pointer flex items-center justify-between" onclick="showDetail(${r.id})">
                                        <div class="flex items-center gap-4">
                                            <div>
                                                <p class="text-sm font-medium text-gray-900">${formatDate(r.open_date)}</p>
                                                <p class="text-xs text-gray-500">${r.site_city || ''}${r.site_city && r.site_state ? ', ' : ''}${r.site_state || ''}</p>
                                            </div>
                                            <span class="text-xs text-gray-500 font-mono">${r.activity_nr}</span>
                                        </div>
                                        <div class="flex items-center gap-3">
                                            ${r.violation_count > 0 ? `
                                                <span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
                                                    ${r.violation_count} violation${r.violation_count !== 1 ? 's' : ''}
                                                </span>
                                            ` : ''}
                                            ${r.total_current_penalty > 0 ? `
                                                <span class="text-sm font-medium text-red-600">$${r.total_current_penalty.toLocaleString()}</span>
                                            ` : `<span class="text-sm text-gray-400">No penalty</span>`}
                                            <svg class="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path>
                                            </svg>
                                        </div>
                                    </div>
                                `).join('')}
                            </div>
                        </div>
                    `;
                }

                let violationsHtml = '';
                if (inspection.violations && inspection.violations.length > 0) {
                    violationsHtml = `
                        <div class="border-t border-gray-200">
                            <div class="px-6 py-4 bg-gray-50 border-b border-gray-200">
                                <div class="flex items-center justify-between">
                                    <h3 class="text-sm font-semibold text-gray-900 uppercase tracking-wider">
                                        Citations & Violations
                                    </h3>
                                    <span class="bg-red-100 text-red-800 text-xs font-medium px-2.5 py-0.5 rounded-full">
                                        ${inspection.violations.length} violation${inspection.violations.length !== 1 ? 's' : ''}
                                    </span>
                                </div>
                            </div>
                            <div class="overflow-x-auto">
                                <table class="w-full">
                                    <thead>
                                        <tr class="bg-gray-50 text-xs text-gray-500 uppercase tracking-wider">
                                            <th class="px-6 py-3 text-left font-medium">Citation ID</th>
                                            <th class="px-6 py-3 text-left font-medium">Type</th>
                                            <th class="px-6 py-3 text-left font-medium">OSHA Standard</th>
                                            <th class="px-6 py-3 text-right font-medium">Penalty</th>
                                            <th class="px-6 py-3 text-center font-medium">Exposed</th>
                                        </tr>
                                    </thead>
                                    <tbody class="divide-y divide-gray-100">
                                        ${inspection.violations.map(v => {
                                            const stdUrl = getOshaStandardUrl(v.standard);
                                            const stdHtml = stdUrl
                                                ? `<a href="${stdUrl}" target="_blank" class="text-blue-600 hover:text-blue-800 hover:underline font-mono">${escapeHtml(v.standard)}</a>`
                                                : `<span class="font-mono text-gray-600">${escapeHtml(v.standard || '-')}</span>`;
                                            return `
                                            <tr class="hover:bg-gray-50 transition-colors">
                                                <td class="px-6 py-3 text-sm text-gray-900 font-medium">${v.citation_id || '-'}</td>
                                                <td class="px-6 py-3">
                                                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getViolationTypeBadge(v.viol_type)}">
                                                        ${getViolationTypeLabel(v.viol_type)}
                                                    </span>
                                                </td>
                                                <td class="px-6 py-3 text-sm">${stdHtml}</td>
                                                <td class="px-6 py-3 text-sm text-right font-semibold ${v.current_penalty > 0 ? 'text-red-600' : 'text-gray-500'}">
                                                    ${v.current_penalty ? '$' + v.current_penalty.toLocaleString() : '-'}
                                                </td>
                                                <td class="px-6 py-3 text-sm text-center text-gray-600">${v.nr_exposed || '-'}</td>
                                            </tr>
                                        `}).join('')}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    `;
                } else {
                    violationsHtml = `
                        <div class="border-t border-gray-200">
                            <div class="px-6 py-4 bg-gray-50 border-b border-gray-200">
                                <h3 class="text-sm font-semibold text-gray-900 uppercase tracking-wider">
                                    Citations & Violations
                                </h3>
                            </div>
                            <div class="px-6 py-8 text-center">
                                <svg class="mx-auto h-12 w-12 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                                </svg>
                                <p class="mt-2 text-sm text-gray-500">No violations on record for this inspection</p>
                            </div>
                        </div>
                    `;
                }

                document.getElementById('modal-content').innerHTML = `
                    <!-- Header -->
                    <div class="bg-gradient-to-r from-blue-600 to-blue-700 px-6 py-5">
                        <div class="flex justify-between items-start">
                            <div class="flex-1 min-w-0">
                                <h2 class="text-xl font-bold text-white truncate">${escapeHtml(inspection.estab_name)}</h2>
                                <div class="mt-1 flex items-center gap-3 text-blue-100 text-sm">
                                    <a href="${oshaUrl}" target="_blank" class="hover:text-white flex items-center gap-1">
                                        <span class="font-mono">${inspection.activity_nr}</span>
                                        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"></path>
                                        </svg>
                                    </a>
                                    <span class="text-blue-300">|</span>
                                    <a href="${mapsUrl}" target="_blank" class="hover:text-white flex items-center gap-1">
                                        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"></path>
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"></path>
                                        </svg>
                                        <span>${escapeHtml(addressLine)}</span>
                                    </a>
                                </div>
                            </div>
                            <button onclick="closeModal()" class="text-blue-200 hover:text-white ml-4">
                                <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                                </svg>
                            </button>
                        </div>
                    </div>

                    <!-- Penalties Summary -->
                    <div class="bg-gray-50 border-b border-gray-200">
                        <div class="grid grid-cols-3 divide-x divide-gray-200">
                            <div class="px-6 py-4 text-center">
                                <p class="text-xs text-gray-500 uppercase tracking-wider font-medium">Initial Penalty</p>
                                <p class="mt-1 text-2xl font-bold text-gray-700">
                                    ${inspection.total_initial_penalty ? '$' + inspection.total_initial_penalty.toLocaleString() : '-'}
                                </p>
                            </div>
                            <div class="px-6 py-4 text-center">
                                <p class="text-xs text-gray-500 uppercase tracking-wider font-medium">Current Penalty</p>
                                <p class="mt-1 text-2xl font-bold ${inspection.total_current_penalty > 0 ? 'text-red-600' : 'text-gray-400'}">
                                    ${inspection.total_current_penalty ? '$' + inspection.total_current_penalty.toLocaleString() : '-'}
                                </p>
                            </div>
                            <div class="px-6 py-4 text-center">
                                <p class="text-xs text-gray-500 uppercase tracking-wider font-medium">Reduction</p>
                                <div class="mt-1">
                                    ${getPenaltyReductionHtml(inspection.total_initial_penalty, inspection.total_current_penalty)}
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- CRM Actions -->
                    <div class="px-6 py-3 bg-purple-50 border-b border-purple-100" id="crm-actions-${inspection.id}">
                        <div class="flex items-center justify-between">
                            <div class="flex items-center gap-2">
                                <svg class="w-5 h-5 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"></path>
                                </svg>
                                <span class="text-sm font-medium text-purple-800">CRM</span>
                            </div>
                            <div id="crm-action-buttons-${inspection.id}">
                                <button onclick="addToCRM(${inspection.id})"
                                    class="inline-flex items-center px-3 py-1.5 text-sm font-medium rounded-md bg-purple-600 text-white hover:bg-purple-700 transition-colors">
                                    <svg class="w-4 h-4 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6"></path>
                                    </svg>
                                    Add to CRM
                                </button>
                            </div>
                        </div>
                    </div>

                    <!-- Inspection Details -->
                    <div class="px-6 py-5">
                        <h3 class="text-sm font-semibold text-gray-900 uppercase tracking-wider mb-4">Inspection Details</h3>
                        <div class="grid grid-cols-2 md:grid-cols-4 gap-x-6 gap-y-4">
                            <div>
                                <p class="text-xs text-gray-500 uppercase tracking-wider">Open Date</p>
                                <p class="mt-1 text-sm font-medium text-gray-900">${formatDate(inspection.open_date)}</p>
                            </div>
                            <div>
                                <p class="text-xs text-gray-500 uppercase tracking-wider">Closing Conference</p>
                                <p class="mt-1 text-sm font-medium text-gray-900">${formatDate(inspection.close_conf_date)}</p>
                            </div>
                            <div>
                                <p class="text-xs text-gray-500 uppercase tracking-wider">Case Closed</p>
                                <p class="mt-1 text-sm font-medium text-gray-900">${formatDate(inspection.close_case_date)}</p>
                            </div>
                            <div>
                                <p class="text-xs text-gray-500 uppercase tracking-wider">Type</p>
                                <p class="mt-1 text-sm font-medium text-gray-900">${getInspectionTypeWithCode(inspection.insp_type)}</p>
                            </div>
                            <div>
                                <p class="text-xs text-gray-500 uppercase tracking-wider">Scope</p>
                                <p class="mt-1 text-sm font-medium text-gray-900">${getInspectionScopeWithCode(inspection.insp_scope)}</p>
                            </div>
                            <div>
                                <p class="text-xs text-gray-500 uppercase tracking-wider">SIC Code</p>
                                <p class="mt-1 text-sm font-medium text-gray-900">${inspection.sic_code || '-'}</p>
                            </div>
                            <div>
                                <p class="text-xs text-gray-500 uppercase tracking-wider">NAICS Code</p>
                                <p class="mt-1 text-sm font-medium text-gray-900">${inspection.naics_code || '-'}</p>
                            </div>
                            <div>
                                <p class="text-xs text-gray-500 uppercase tracking-wider">Owner Type</p>
                                <p class="mt-1 text-sm font-medium text-gray-900">${getOwnerTypeWithCode(inspection.owner_type)}</p>
                            </div>
                            <div>
                                <p class="text-xs text-gray-500 uppercase tracking-wider"># Employees</p>
                                <p class="mt-1 text-sm font-medium text-gray-900">${inspection.nr_in_estab || '-'}</p>
                            </div>
                            <div id="enrichment-status-container-${inspection.id}">
                                <p class="text-xs text-gray-500 uppercase tracking-wider">Enrichment</p>
                                <p class="mt-1 flex items-center gap-2">
                                    ${inspection.enrichment_status === 'completed' ? `
                                        <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800">
                                            completed
                                        </span>
                                        <button onclick="reEnrichInspection(${inspection.id})"
                                            id="enrich-btn-${inspection.id}"
                                            class="inline-flex items-center px-2 py-1 text-xs font-medium rounded bg-indigo-100 text-indigo-700 hover:bg-indigo-200">
                                            <svg class="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path>
                                            </svg>
                                            Re-enrich
                                        </button>
                                    ` : `
                                        <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                                            inspection.enrichment_status === 'failed' ? 'bg-red-100 text-red-800' :
                                            inspection.enrichment_status === 'in_progress' ? 'bg-yellow-100 text-yellow-800' :
                                            'bg-gray-100 text-gray-800'
                                        }">
                                            ${inspection.enrichment_status || 'pending'}
                                        </span>
                                        <button onclick="enrichInspection(${inspection.id})"
                                            id="enrich-btn-${inspection.id}"
                                            class="inline-flex items-center px-2 py-1 text-xs font-medium rounded bg-blue-100 text-blue-700 hover:bg-blue-200">
                                            <svg class="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path>
                                            </svg>
                                            Enrich
                                        </button>
                                    `}
                                </p>
                            </div>
                        </div>
                    </div>

                    <!-- Company Data Section (if enriched) -->
                    <div id="company-data-section-${inspection.id}"></div>

                    <!-- Violations Section -->
                    ${violationsHtml}

                    <!-- Related Inspections Section -->
                    ${relatedHtml}
                `;
                document.getElementById('modal').classList.remove('hidden');

                // Always try to load company data (may come from related inspection)
                loadCompanyDataOrRelated(inspection.id);

                // Check if inspection is already in CRM
                checkCRMStatus(inspection.id);
            } catch (e) {
                console.error('Error loading inspection details:', e);
            }
        }

        async function checkCRMStatus(inspectionId) {
            try {
                const response = await fetch(`/api/crm/inspection/${inspectionId}/prospect`);
                const container = document.getElementById(`crm-action-buttons-${inspectionId}`);

                if (response.ok) {
                    const data = await response.json();
                    if (data.exists) {
                        // Already a prospect - show "View in CRM" link
                        container.innerHTML = `
                            <div class="flex items-center gap-2">
                                <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${getStatusColor(data.status)}">
                                    ${formatStatus(data.status)}
                                </span>
                                <a href="/crm"
                                    class="inline-flex items-center px-3 py-1.5 text-sm font-medium rounded-md bg-purple-600 text-white hover:bg-purple-700 transition-colors">
                                    <svg class="w-4 h-4 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path>
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"></path>
                                    </svg>
                                    View in CRM
                                </a>
                            </div>
                        `;
                    }
                    // If exists is false, keep the "Add to CRM" button as is
                }
            } catch (e) {
                console.error('Error checking CRM status:', e);
            }
        }

        function closeModal() {
            document.getElementById('modal').classList.add('hidden');
        }

        // Enrichment state
        let currentEnrichmentPreview = null;
        let currentWebEnrichmentResult = null;
        let currentApolloResult = null;
        let revealedContacts = [];  // Contacts with revealed email/phone from Step 2
        let currentInspection = null;  // Store current inspection for email generation

        async function enrichInspection(inspectionId) {
            const btn = document.getElementById(`enrich-btn-${inspectionId}`);
            if (btn) {
                btn.disabled = true;
                btn.innerHTML = `
                    <svg class="w-3 h-3 mr-1 animate-spin" fill="none" viewBox="0 0 24 24">
                        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Enriching...
                `;
            }

            try {
                // Run public enrichment directly (no preview modal)
                const webResponse = await fetch(`/api/enrichment/web-enrich/${inspectionId}?quick=false`, { method: 'POST' });
                const webResult = await webResponse.json();

                if (!webResult.success || !webResult.data) {
                    const message = webResult.error || 'No public data found';
                    if (btn) {
                        btn.disabled = false;
                        btn.innerHTML = 'Enrich';
                    }
                    alert(`Enrichment not found: ${message}`);
                    return;
                }

                // Save the enrichment data
                const saveResponse = await fetch(`/api/enrichment/save-web-enrichment/${inspectionId}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        data: webResult.data || {},
                        website_url: webResult.website_url,
                        confidence: webResult.confidence || 'medium',
                        source: webResult.source || 'public'
                    })
                });

                const saveResult = await saveResponse.json();

                if (saveResult.success) {
                    // Update the enrichment status container to show completed + re-enrich button
                    updateEnrichmentStatusDisplay(inspectionId, 'completed');

                    // Load and display the company data
                    await loadCompanyDataOrRelated(inspectionId);
                } else {
                    throw new Error(saveResult.error || 'Failed to save enrichment');
                }
            } catch (e) {
                console.error('Error during enrichment:', e);
                if (btn) {
                    btn.disabled = false;
                    btn.innerHTML = 'Error - Retry';
                }
                alert('Enrichment failed: ' + e.message);
            }
        }

        // Update the enrichment status display after enrichment completes
        function updateEnrichmentStatusDisplay(inspectionId, status) {
            const container = document.getElementById(`enrichment-status-container-${inspectionId}`);
            if (!container) return;

            if (status === 'completed') {
                container.innerHTML = `
                    <p class="text-xs text-gray-500 uppercase tracking-wider">Enrichment</p>
                    <p class="mt-1 flex items-center gap-2">
                        <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800">
                            completed
                        </span>
                        <button onclick="reEnrichInspection(${inspectionId})"
                            id="enrich-btn-${inspectionId}"
                            class="inline-flex items-center px-2 py-1 text-xs font-medium rounded bg-indigo-100 text-indigo-700 hover:bg-indigo-200">
                            <svg class="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path>
                            </svg>
                            Re-enrich
                        </button>
                    </p>
                `;
            }
        }

        // Re-enrich an already enriched inspection
        async function reEnrichInspection(inspectionId) {
            if (!confirm('Re-enrich this company? This will fetch fresh data from public sources.')) return;
            await enrichInspection(inspectionId);
        }

        // Open Apollo enrichment modal for an already web-enriched company
        async function openApolloEnrichmentModal(inspectionId) {
            try {
                // Get the enrichment preview (includes existing domain/website)
                const preview = await fetch(`/api/enrichment/preview/${inspectionId}`).then(r => r.json());
                currentEnrichmentPreview = preview;
                currentWebEnrichmentResult = null;
                currentApolloResult = null;
                revealedContacts = [];

                // Mark as re-enrich since we already have web data
                preview.isReEnrich = true;

                // Show the enrichment preview modal
                showEnrichmentPreviewModal(preview);
            } catch (e) {
                console.error('Error opening Apollo enrichment:', e);
                alert('Error loading enrichment options: ' + e.message);
            }
        }

        function showEnrichmentPreviewModal(preview) {
            const qualityColors = {
                high: 'bg-green-100 text-green-800',
                medium: 'bg-yellow-100 text-yellow-800',
                low: 'bg-orange-100 text-orange-800',
                unusable: 'bg-red-100 text-red-800'
            };

            const qualityColor = qualityColors[preview.quality.level] || 'bg-gray-100 text-gray-800';

            const modal = document.createElement('div');
            modal.id = 'enrichment-preview-modal';
            modal.className = 'fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-[60]';
            modal.innerHTML = `
                <div class="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
                    <div class="p-6 border-b bg-gradient-to-r from-indigo-50 to-purple-50">
                        <div class="flex justify-between items-start">
                            <div>
                                <h2 class="text-lg font-semibold text-gray-900">Enrichment Preview</h2>
                                <p class="text-sm text-gray-500 mt-1">Review data quality before using API credits</p>
                            </div>
                            <button onclick="closeEnrichmentPreviewModal()" class="text-gray-400 hover:text-gray-600">
                                <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                                </svg>
                            </button>
                        </div>
                    </div>

                    <div class="p-6 space-y-6">
                        <!-- Data Quality Section -->
                        <div class="bg-gray-50 rounded-lg p-4">
                            <div class="flex items-center justify-between mb-3">
                                <h3 class="font-medium text-gray-900">Data Quality Assessment</h3>
                                <span class="px-3 py-1 rounded-full text-sm font-medium ${qualityColor}">
                                    ${preview.quality.level.charAt(0).toUpperCase() + preview.quality.level.slice(1)} (${preview.quality.score}/100)
                                </span>
                            </div>
                            ${preview.quality.issues.length > 0 ? `
                                <ul class="text-sm text-gray-600 space-y-1">
                                    ${preview.quality.issues.map(issue => `
                                        <li class="flex items-center gap-2">
                                            <svg class="w-4 h-4 text-yellow-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path>
                                            </svg>
                                            ${escapeHtml(issue)}
                                        </li>
                                    `).join('')}
                                </ul>
                            ` : `
                                <p class="text-sm text-green-600">No issues detected</p>
                            `}
                        </div>

                        <!-- Company Name Normalization -->
                        <div>
                            <h3 class="font-medium text-gray-900 mb-2">Company Name</h3>
                            <div class="grid grid-cols-2 gap-4">
                                <div>
                                    <p class="text-xs text-gray-500 uppercase mb-1">Original (OSHA)</p>
                                    <p class="text-sm font-mono bg-gray-100 p-2 rounded">${escapeHtml(preview.original_name)}</p>
                                </div>
                                <div>
                                    <p class="text-xs text-gray-500 uppercase mb-1">Normalized (for search)</p>
                                    <p class="text-sm font-mono bg-blue-50 p-2 rounded">${escapeHtml(preview.normalized_name)}</p>
                                </div>
                            </div>
                            ${preview.normalization_changes.length > 0 ? `
                                <p class="text-xs text-gray-500 mt-2">Changes: ${preview.normalization_changes.join(', ')}</p>
                            ` : ''}
                        </div>

                        <!-- Location -->
                        <div>
                            <h3 class="font-medium text-gray-900 mb-2">Location</h3>
                            <p class="text-sm text-gray-600">
                                ${[preview.location.address, preview.location.city, preview.location.state].filter(Boolean).join(', ') || 'No location data'}
                            </p>
                        </div>

                        <!-- Search Variants -->
                        <div>
                            <h3 class="font-medium text-gray-900 mb-2">Search Variants</h3>
                            <div class="flex flex-wrap gap-2">
                                ${preview.search_variants.map(v => `
                                    <span class="px-2 py-1 bg-gray-100 rounded text-sm">${escapeHtml(v)}</span>
                                `).join('')}
                            </div>
                        </div>

                        <!-- Existing Website (for re-enrichment) -->
                        ${preview.existingWebsite || preview.existingDomain ? `
                            <div class="bg-green-50 rounded-lg p-4 border border-green-200">
                                <div class="flex items-center gap-2 mb-2">
                                    <svg class="w-5 h-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
                                    </svg>
                                    <h3 class="font-medium text-green-900">Using Saved Website</h3>
                                </div>
                                <p class="text-sm text-green-800">
                                    ${preview.existingWebsite ? `<a href="${preview.existingWebsite}" target="_blank" class="text-blue-600 hover:underline">${escapeHtml(preview.existingWebsite)}</a>` : ''}
                                    ${!preview.existingWebsite && preview.existingDomain ? `Domain: ${escapeHtml(preview.existingDomain)}` : ''}
                                </p>
                                <p class="text-xs text-green-700 mt-1">Apollo will search using this domain for accurate results</p>
                            </div>
                        ` : ''}

                        <!-- Recommendation -->
                        <div class="bg-indigo-50 rounded-lg p-4">
                            <p class="text-sm font-medium text-indigo-900">${escapeHtml(preview.recommendation_reason)}</p>
                        </div>

                        <!-- Web Enrichment Result (if run) -->
                        <div id="web-enrichment-result" class="hidden"></div>

                        <!-- Apollo Result (if run) -->
                        <div id="apollo-result" class="hidden"></div>
                    </div>

                    <!-- Actions -->
                    <div class="p-6 border-t bg-gray-50">
                        <!-- Enrichment Options Explanation -->
                        <div class="mb-4 p-3 bg-gray-100 rounded-lg border">
                            <p class="text-sm text-gray-700 font-medium mb-2">Enrichment Options:</p>
                            <div class="text-xs text-gray-600 space-y-1">
                                <p><strong>Public Enrichment (Free):</strong> Uses public listings/registries (OpenStreetMap, OpenCorporates). Results are saved and can be edited.</p>
                                <p><strong>Apollo (Credits):</strong> Uses Apollo API for verified company & contact data. Best when you have a domain/website.</p>
                            </div>
                        </div>

                        <!-- Web Enrichment Result (if run) - moved here for visibility -->
                        <div id="web-enrichment-result-actions" class="hidden mb-4"></div>

                        <div class="flex flex-col gap-3">
                            <!-- Top row: Cancel and Web Scraping -->
                            <div class="flex justify-between items-center">
                                <button onclick="closeEnrichmentPreviewModal()"
                                    class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50">
                                    Cancel
                                </button>
                                <button onclick="runWebEnrichmentOnly(${preview.inspection_id})" id="btn-web-enrich"
                                    class="px-4 py-2 text-sm font-medium text-white bg-green-600 rounded-md hover:bg-green-700"
                                    ${preview.existingWebsite ? 'disabled title="Already has website"' : ''}>
                                    <svg class="w-4 h-4 mr-1.5 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9"></path>
                                    </svg>
                                    Public Enrich (Free)
                                </button>
                            </div>

                            <!-- Bottom row: Apollo button -->
                            <div class="flex justify-end">
                                <button onclick="runApolloEnrichmentOnly(${preview.inspection_id})" id="btn-apollo-enrich"
                                    class="px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-md hover:bg-indigo-700 ${preview.recommendation === 'do_not_enrich' && !preview.existingDomain ? 'opacity-50' : ''}"
                                    ${preview.recommendation === 'do_not_enrich' && !preview.existingDomain ? 'disabled title="Run web scraping first to find domain"' : ''}>
                                    <svg class="w-4 h-4 mr-1.5 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"></path>
                                    </svg>
                                    Apollo Search (${preview.estimated_credits} credit${preview.estimated_credits !== 1 ? 's' : ''})
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            `;

            document.body.appendChild(modal);
        }

        function closeEnrichmentPreviewModal() {
            const modal = document.getElementById('enrichment-preview-modal');
            if (modal) modal.remove();
            currentEnrichmentPreview = null;
            currentWebEnrichmentResult = null;
            currentApolloResult = null;
            revealedContacts = [];  // Clear revealed contacts when closing modal
        }

        async function runFullEnrichment(inspectionId) {
            const btn = document.getElementById('btn-full-enrich');
            const webResultContainer = document.getElementById('web-enrichment-result');
            const apolloResultContainer = document.getElementById('apollo-result');

            btn.disabled = true;

            // Check if we have an existing domain from re-enrichment
            const existingDomain = currentEnrichmentPreview?.existingDomain;
            const existingWebsite = currentEnrichmentPreview?.existingWebsite;
            let domainForApollo = null;
            let webEnrichmentComplete = false;

            if (existingDomain || existingWebsite) {
                // Use existing domain - skip web search
                webResultContainer.classList.remove('hidden');
                webResultContainer.innerHTML = `
                    <div class="bg-green-50 rounded-lg p-4">
                        <div class="flex items-center gap-2 mb-2">
                            <svg class="w-5 h-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
                            </svg>
                            <h3 class="font-medium text-green-900">Using Saved Website</h3>
                        </div>
                        <p class="text-sm text-green-700">Skipping web search - using saved domain for Apollo</p>
                    </div>
                `;

                // Extract domain from existing website or use existing domain directly
                if (existingWebsite) {
                    try {
                        domainForApollo = new URL(existingWebsite).hostname.replace('www.', '');
                    } catch (e) {
                        domainForApollo = existingDomain;
                    }
                } else {
                    domainForApollo = existingDomain;
                }
                webEnrichmentComplete = true;
            } else {
                // Step 1: Web search to find domain
                btn.innerHTML = `
                    <svg class="w-4 h-4 mr-1 animate-spin inline" fill="none" viewBox="0 0 24 24">
                        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
                    </svg>
                    Step 1: Finding website...
                `;

                // Show searching status
                webResultContainer.classList.remove('hidden');
                webResultContainer.innerHTML = `
                    <div class="bg-blue-50 rounded-lg p-4">
                        <div class="flex items-center gap-2 mb-2">
                            <svg class="w-5 h-5 text-blue-600 animate-spin" fill="none" viewBox="0 0 24 24">
                                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
                            </svg>
                            <h3 class="font-medium text-blue-900">Searching for company website...</h3>
                        </div>
                        <p class="text-sm text-blue-700">This may take 30-60 seconds (searches DuckDuckGo, LinkedIn, etc.)</p>
                    </div>
                `;

                try {
                    // Run web enrichment first - this MUST complete before Apollo
                    console.log('Starting web enrichment for inspection', inspectionId);
                    const webResponse = await fetch(`/api/enrichment/web-enrich/${inspectionId}`, { method: 'POST' });
                    const webResult = await webResponse.json();
                    console.log('Web enrichment complete:', webResult);
                    currentWebEnrichmentResult = webResult;
                    webEnrichmentComplete = true;

                    // Show web search results
                    if (webResult.website_url) {
                        webResultContainer.innerHTML = `
                            <div class="bg-green-50 rounded-lg p-4">
                                <div class="flex items-center gap-2 mb-2">
                                    <svg class="w-5 h-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
                                    </svg>
                                    <h3 class="font-medium text-green-900">Website Found</h3>
                                </div>
                                <p class="text-sm"><a href="${webResult.website_url}" target="_blank" class="text-blue-600 hover:underline">${escapeHtml(webResult.website_url)}</a></p>
                                ${webResult.confidence ? `<p class="text-xs text-green-600 mt-1">Confidence: ${webResult.confidence}</p>` : ''}
                            </div>
                        `;
                        try {
                            domainForApollo = new URL(webResult.website_url).hostname.replace('www.', '');
                            console.log('Extracted domain for Apollo:', domainForApollo);
                        } catch (e) {
                            console.warn('Could not parse website URL for domain:', e);
                        }
                    } else {
                        webResultContainer.innerHTML = `
                            <div class="bg-yellow-50 rounded-lg p-4">
                                <div class="flex items-center gap-2 mb-2">
                                    <svg class="w-5 h-5 text-yellow-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path>
                                    </svg>
                                    <h3 class="font-medium text-yellow-900">No Website Found</h3>
                                </div>
                                <p class="text-sm text-yellow-700">Will search Apollo by company name (less accurate)</p>
                                ${webResult.error ? `<p class="text-xs text-yellow-600 mt-1">${escapeHtml(webResult.error)}</p>` : ''}
                            </div>
                        `;
                    }
                } catch (e) {
                    console.error('Web enrichment error:', e);
                    webResultContainer.innerHTML = `
                        <div class="bg-red-50 rounded-lg p-4">
                            <div class="flex items-center gap-2 mb-2">
                                <svg class="w-5 h-5 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                                </svg>
                                <h3 class="font-medium text-red-900">Web Search Failed</h3>
                            </div>
                            <p class="text-sm text-red-700">${escapeHtml(e.message || 'Unknown error')}</p>
                            <p class="text-sm text-red-600 mt-1">Proceeding with Apollo name search...</p>
                        </div>
                    `;
                    webEnrichmentComplete = true; // Still proceed but without domain
                }
            }

            // Step 2: Apollo search using domain if found
            // Only proceed if web enrichment is complete
            if (!webEnrichmentComplete) {
                console.error('Web enrichment not complete, cannot proceed to Apollo');
                btn.innerHTML = 'Error - Retry';
                btn.disabled = false;
                return;
            }

            console.log('Proceeding to Apollo search with domain:', domainForApollo);
            btn.innerHTML = `
                <svg class="w-4 h-4 mr-1 animate-spin inline" fill="none" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
                </svg>
                Step 2: Searching Apollo...
            `;

            try {
                let apolloUrl = `/api/enrichment/apollo-search/${inspectionId}`;
                if (domainForApollo) {
                    apolloUrl += `?domain=${encodeURIComponent(domainForApollo)}`;
                }

                const apolloResult = await fetch(apolloUrl, { method: 'POST' }).then(r => r.json());
                currentApolloResult = apolloResult;

                // Show Apollo results
                apolloResultContainer.classList.remove('hidden');

                if (apolloResult.success && apolloResult.organization) {
                    const org = apolloResult.organization;
                    const people = apolloResult.people;
                    const allContacts = [...(people?.safety_contacts || []), ...(people?.executive_contacts || [])];

                    apolloResultContainer.innerHTML = `
                        <div class="bg-indigo-50 rounded-lg p-4">
                            <div class="flex items-center gap-2 mb-3">
                                <svg class="w-5 h-5 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
                                </svg>
                                <h3 class="font-medium text-indigo-900">Apollo Match Found</h3>
                                <span class="text-xs text-indigo-600">(${apolloResult.credits_used} credits used for search)</span>
                            </div>
                            <div class="text-sm space-y-2 mb-4">
                                <p><strong>Company:</strong> ${escapeHtml(org.name || 'Unknown')}</p>
                                ${org.domain ? `<p><strong>Domain:</strong> ${escapeHtml(org.domain)}</p>` : ''}
                                ${org.industry ? `<p><strong>Industry:</strong> ${escapeHtml(org.industry)}</p>` : ''}
                                ${org.employee_range ? `<p><strong>Employees:</strong> ${escapeHtml(org.employee_range)}</p>` : ''}
                                ${org.phone ? `<p><strong>Phone:</strong> ${escapeHtml(org.phone)}</p>` : ''}
                                ${org.city && org.state ? `<p><strong>Location:</strong> ${escapeHtml(org.city)}, ${escapeHtml(org.state)}</p>` : ''}
                            </div>
                            ${allContacts.length ? `
                                <div class="border-t border-indigo-200 pt-3 mb-4">
                                    <div class="flex justify-between items-center mb-2">
                                        <p class="font-medium text-indigo-900">Contacts Found (${allContacts.length}):</p>
                                        <label class="flex items-center gap-1 text-xs text-indigo-700 cursor-pointer">
                                            <input type="checkbox" id="select-all-contacts" onchange="toggleAllContacts(this.checked)" class="rounded">
                                            Select All
                                        </label>
                                    </div>
                                    <p class="text-xs text-gray-500 mb-2">Select contacts to reveal their info (1 credit per contact)</p>
                                    <div class="space-y-2 max-h-48 overflow-y-auto">
                                        ${allContacts.map((c, idx) => {
                                            const isSafety = (people?.safety_contacts || []).includes(c);
                                            return `
                                            <label class="flex items-center gap-2 p-2 bg-white rounded border hover:bg-gray-50 cursor-pointer">
                                                <input type="checkbox" class="contact-checkbox rounded" value="${escapeHtml(c.apollo_person_id || '')}" data-idx="${idx}">
                                                <span class="px-1.5 py-0.5 ${isSafety ? 'bg-green-100 text-green-800' : 'bg-purple-100 text-purple-800'} text-xs rounded">${isSafety ? 'Safety' : 'Exec'}</span>
                                                <div class="flex-1 min-w-0">
                                                    <div class="font-medium text-sm truncate">${escapeHtml(c.full_name || 'Unknown')}</div>
                                                    <div class="text-xs text-gray-500 truncate">${escapeHtml(c.title || 'No title')}</div>
                                                </div>
                                                ${c.email ? '<span class="text-xs text-green-600">Has email</span>' : '<span class="text-xs text-gray-400">No email yet</span>'}
                                            </label>
                                        `}).join('')}
                                    </div>
                                    <!-- Reveal options -->
                                    <div class="mt-3 p-3 bg-gray-50 rounded-lg border">
                                        <p class="text-xs font-medium text-gray-700 mb-2">What to reveal:</p>
                                        <div class="flex gap-4">
                                            <label class="flex items-center gap-2 text-sm cursor-pointer">
                                                <input type="checkbox" id="reveal-email-option" checked class="rounded" onchange="updateRevealButtonState()">
                                                <span>Email</span>
                                            </label>
                                            <label class="flex items-center gap-2 text-sm cursor-pointer">
                                                <input type="checkbox" id="reveal-phone-option" class="rounded" onchange="updateRevealButtonState()">
                                                <span>Phone</span>
                                                <span class="text-xs text-yellow-600">(requires webhook)</span>
                                            </label>
                                        </div>
                                    </div>
                                    <button id="reveal-contacts-btn" onclick="revealSelectedContacts(${inspectionId})"
                                        class="w-full mt-3 px-4 py-2 text-sm font-medium text-white bg-orange-500 rounded-md hover:bg-orange-600 disabled:opacity-50 disabled:cursor-not-allowed"
                                        disabled>
                                        Reveal for Selected (0 credits)
                                    </button>
                                </div>
                            ` : '<p class="text-sm text-gray-500 mb-4">No contacts found at this company</p>'}
                            <div id="revealed-contacts-container" class="hidden mb-4"></div>
                            <button id="confirm-save-btn" onclick="confirmAndSaveEnrichment(${inspectionId})"
                                class="w-full px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-md hover:bg-indigo-700">
                                Save Company to Database
                            </button>
                        </div>
                    `;

                    // Add event listeners for checkbox changes
                    document.querySelectorAll('.contact-checkbox').forEach(cb => {
                        cb.addEventListener('change', updateRevealButtonState);
                    });

                    btn.innerHTML = `Search Complete`;
                    btn.classList.remove('bg-indigo-600', 'hover:bg-indigo-700');
                    btn.classList.add('bg-green-600');
                } else {
                    apolloResultContainer.innerHTML = `
                        <div class="bg-red-50 rounded-lg p-4">
                            <div class="flex items-center gap-2 mb-2">
                                <svg class="w-5 h-5 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                                </svg>
                                <h3 class="font-medium text-red-900">No Apollo Match</h3>
                            </div>
                            <p class="text-sm text-red-700">${apolloResult.error || 'No organization found in Apollo'}</p>
                            <p class="text-xs text-red-500 mt-1">Credits used: ${apolloResult.credits_used}</p>
                        </div>
                    `;
                    btn.innerHTML = 'No Results - Try Again';
                    btn.disabled = false;
                }
            } catch (e) {
                console.error('Enrichment error:', e);
                btn.innerHTML = 'Error - Retry';
                btn.disabled = false;
            }
        }

        function toggleAllContacts(checked) {
            document.querySelectorAll('.contact-checkbox').forEach(cb => {
                cb.checked = checked;
            });
            updateRevealButtonState();
        }

        function updateRevealButtonState() {
            const checkboxes = document.querySelectorAll('.contact-checkbox:checked');
            const btn = document.getElementById('reveal-contacts-btn');
            const revealEmail = document.getElementById('reveal-email-option')?.checked ? true : false;
            const revealPhone = document.getElementById('reveal-phone-option')?.checked ? true : false;

            if (btn) {
                const count = checkboxes.length;
                const hasSelection = count > 0 && (revealEmail || revealPhone);

                // Build label showing what will be revealed
                let revealTypes = [];
                if (revealEmail) revealTypes.push('Email');
                if (revealPhone) revealTypes.push('Phone');
                const typeLabel = revealTypes.length > 0 ? revealTypes.join(' + ') : 'Nothing';

                btn.disabled = !hasSelection;
                btn.textContent = `Reveal ${typeLabel} for ${count} Contact${count !== 1 ? 's' : ''} (${count} credit${count !== 1 ? 's' : ''})`;
            }
        }

        async function revealSelectedContacts(inspectionId) {
            const checkboxes = document.querySelectorAll('.contact-checkbox:checked');
            const personIds = Array.from(checkboxes).map(cb => cb.value).filter(id => id);
            const revealEmail = document.getElementById('reveal-email-option')?.checked ? true : false;
            const revealPhone = document.getElementById('reveal-phone-option')?.checked ? true : false;

            if (personIds.length === 0) {
                alert('Please select at least one contact to reveal');
                return;
            }

            if (!revealEmail && !revealPhone) {
                alert('Please select at least Email or Phone to reveal');
                return;
            }

            const btn = document.getElementById('reveal-contacts-btn');
            btn.disabled = true;
            btn.innerHTML = `
                <svg class="w-4 h-4 mr-1 animate-spin inline" fill="none" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
                </svg>
                Revealing ${personIds.length} contact${personIds.length !== 1 ? 's' : ''}...
            `;

            try {
                const response = await fetch('/api/enrichment/reveal-contacts', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        person_ids: personIds,
                        reveal_email: revealEmail,
                        reveal_phone: revealPhone
                    })
                });

                const result = await response.json();

                if (result.success && result.contacts.length > 0) {
                    // Append to existing revealed contacts (don't overwrite)
                    revealedContacts = [...revealedContacts, ...result.contacts];

                    // Show ALL revealed contacts (accumulated from multiple reveals)
                    const container = document.getElementById('revealed-contacts-container');
                    container.classList.remove('hidden');
                    container.innerHTML = `
                        <div class="bg-green-50 border border-green-200 rounded-lg p-4">
                            <h4 class="font-medium text-green-900 mb-2">Revealed Contacts (${revealedContacts.length} total, ${result.credits_used} credits just used)</h4>
                            <p class="text-xs text-green-700 mb-2">These will be saved when you click "Save Company to Database"</p>
                            <div class="space-y-2 max-h-48 overflow-y-auto">
                                ${revealedContacts.map(c => `
                                    <div class="bg-white rounded border p-2 text-sm">
                                        <div class="font-medium">${escapeHtml(c.full_name || 'Unknown')}</div>
                                        <div class="text-gray-600">${escapeHtml(c.title || '')}</div>
                                        ${c.email ? `<div class="text-blue-600"><a href="mailto:${c.email}">${escapeHtml(c.email)}</a></div>` : '<div class="text-gray-400">No email</div>'}
                                        ${c.phone ? `<div class="text-blue-600"><a href="tel:${c.phone}">${escapeHtml(c.phone)}</a></div>` : ''}
                                    </div>
                                `).join('')}
                            </div>
                        </div>
                    `;

                    btn.textContent = `${revealedContacts.length} Contact${revealedContacts.length !== 1 ? 's' : ''} Revealed`;
                    btn.classList.remove('bg-orange-500', 'hover:bg-orange-600');
                    btn.classList.add('bg-green-500');

                    // Uncheck revealed contacts and re-enable button for more reveals
                    checkboxes.forEach(cb => cb.checked = false);
                    btn.disabled = false;
                    setTimeout(() => {
                        btn.classList.remove('bg-green-500');
                        btn.classList.add('bg-orange-500', 'hover:bg-orange-600');
                        updateRevealButtonState();
                    }, 1500);
                } else {
                    alert(result.error || 'Failed to reveal contacts');
                    btn.disabled = false;
                    updateRevealButtonState();
                }
            } catch (e) {
                console.error('Error revealing contacts:', e);
                alert('Error revealing contacts: ' + e.message);
                btn.disabled = false;
                updateRevealButtonState();
            }
        }

        async function confirmAndSaveEnrichment(inspectionId) {
            console.log('confirmAndSaveEnrichment called, inspectionId:', inspectionId);
            console.log('currentApolloResult:', currentApolloResult);

            if (!currentApolloResult) {
                alert('No Apollo data available. Please run the Apollo search first.');
                return;
            }

            if (!currentApolloResult.organization) {
                alert('No organization data found in Apollo results.');
                return;
            }

            // Disable button to prevent double-clicks
            const saveBtn = document.getElementById('confirm-save-btn');
            if (saveBtn) {
                saveBtn.disabled = true;
                saveBtn.textContent = 'Saving...';
            }

            try {
                // Combine all contacts from initial search
                let contacts = [
                    ...(currentApolloResult.people?.safety_contacts || []),
                    ...(currentApolloResult.people?.executive_contacts || [])
                ];

                // Merge revealed contact data (email/phone) into the original contacts
                if (revealedContacts.length > 0) {
                    const contactIds = new Set(contacts.map(c => c.apollo_person_id));

                    contacts = contacts.map(contact => {
                        // Find if this contact was revealed
                        const revealed = revealedContacts.find(r => r.apollo_person_id === contact.apollo_person_id);
                        if (revealed) {
                            // Merge revealed data (email, phone) into the contact
                            return {
                                ...contact,
                                email: revealed.email || contact.email,
                                email_status: revealed.email_status || contact.email_status,
                                phone: revealed.phone || contact.phone,
                                mobile_phone: revealed.mobile_phone || contact.mobile_phone
                            };
                        }
                        return contact;
                    });

                    // Add any revealed contacts that weren't in the original list
                    for (const revealed of revealedContacts) {
                        if (revealed.apollo_person_id && !contactIds.has(revealed.apollo_person_id)) {
                            contacts.push(revealed);
                            console.log('Added revealed contact not in original list:', revealed.full_name);
                        }
                    }
                }

                console.log('Sending to API:', { organization: currentApolloResult.organization, contacts, revealedCount: revealedContacts.length });

                const response = await fetch(`/api/enrichment/confirm/${inspectionId}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        organization: currentApolloResult.organization,
                        contacts: contacts
                    })
                });

                const result = await response.json();

                if (result.company_saved) {
                    const isReEnrich = currentEnrichmentPreview?.isReEnrich;
                    // Save organization data BEFORE closing modal (which sets currentApolloResult to null)
                    const savedOrganization = currentApolloResult?.organization;

                    alert(`${isReEnrich ? 'Updated' : 'Saved'} successfully! Company: ${result.company_data?.name}, Contacts: ${result.contacts_saved}`);
                    closeEnrichmentPreviewModal();

                    // Update the inspection detail modal to show enriched data
                    const enrichBtn = document.getElementById(`enrich-btn-${inspectionId}`);
                    if (enrichBtn) {
                        enrichBtn.classList.remove('bg-blue-100', 'text-blue-700');
                        enrichBtn.classList.add('bg-green-100', 'text-green-700');
                        enrichBtn.innerHTML = 'Enriched';
                        enrichBtn.disabled = true;
                    }

                    // Display the company data in the modal (if inspection modal is open)
                    if (savedOrganization) {
                        displayCompanyData(inspectionId, {
                            success: true,
                            data: savedOrganization,
                            confidence: 'high'
                        });
                    }

                    // Reload enriched companies list if it was a re-enrich
                    if (isReEnrich) {
                        loadEnrichedCompanies();
                    }
                } else {
                    alert(`Error saving: ${result.error}`);
                    // Re-enable button on error
                    const saveBtn = document.getElementById('confirm-save-btn');
                    if (saveBtn) {
                        saveBtn.disabled = false;
                        saveBtn.textContent = 'Confirm & Save to Database';
                    }
                }
            } catch (e) {
                console.error('Error saving enrichment:', e);
                alert('Error saving enrichment data: ' + e.message);
                // Re-enable button on error
                const saveBtn = document.getElementById('confirm-save-btn');
                if (saveBtn) {
                    saveBtn.disabled = false;
                    saveBtn.textContent = 'Confirm & Save to Database';
                }
            }
        }

        // Run public enrichment only (free) - uses public sources and saves to database
        async function runWebEnrichmentOnly(inspectionId) {
            const btn = document.getElementById('btn-web-enrich');
            const resultContainer = document.getElementById('web-enrichment-result-actions');

            btn.disabled = true;
            btn.innerHTML = `
                <svg class="w-4 h-4 mr-1 animate-spin inline" fill="none" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
                </svg>
                Searching...
            `;

            // Show searching status
            resultContainer.classList.remove('hidden');
            resultContainer.innerHTML = `
                <div class="bg-blue-50 rounded-lg p-4">
                    <div class="flex items-center gap-2 mb-2">
                        <svg class="w-5 h-5 text-blue-600 animate-spin" fill="none" viewBox="0 0 24 24">
                            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
                        </svg>
                        <h3 class="font-medium text-blue-900">Searching public sources...</h3>
                    </div>
                    <p class="text-sm text-blue-700">This may take 30-60 seconds (OpenStreetMap + OpenCorporates).</p>
                    <p class="text-xs text-blue-600 mt-1">Looking for address, phone, ownership, and business registry info...</p>
                </div>
            `;

            try {
                // Run FULL public enrichment (not quick mode)
                const response = await fetch(`/api/enrichment/web-enrich/${inspectionId}?quick=false`, { method: 'POST' });
                const webResult = await response.json();
                console.log('Web enrichment result:', webResult);
                currentWebEnrichmentResult = webResult;

                if (webResult.success || webResult.website_url) {
                    // Show the extracted data with option to edit and save
                    const data = webResult.data || {};
                    resultContainer.innerHTML = `
                        <div class="bg-green-50 rounded-lg p-4">
                            <div class="flex items-center gap-2 mb-3">
                                <svg class="w-5 h-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
                                </svg>
                                <h3 class="font-medium text-green-900">Public Enrichment Complete</h3>
                                ${webResult.confidence ? `<span class="text-xs px-2 py-0.5 bg-green-100 text-green-700 rounded">${webResult.confidence} confidence</span>` : ''}
                            </div>

                            <div class="space-y-2 text-sm mb-4">
                                ${data.legal_name || data.official_name ? `<p><strong>Legal Name:</strong> ${escapeHtml(data.legal_name || data.official_name)}</p>` : ''}
                                ${data.operating_name || data.dba_name ? `<p><strong>DBA/Operating Name:</strong> ${escapeHtml(data.operating_name || data.dba_name)}</p>` : ''}
                                ${webResult.website_url ? `<p><strong>Website:</strong> <a href="${webResult.website_url}" target="_blank" class="text-blue-600 hover:underline">${escapeHtml(webResult.website_url)}</a></p>` : ''}
                                ${data.phone || data.contact_info?.main_phone ? `<p><strong>Phone:</strong> ${escapeHtml(data.phone || data.contact_info?.main_phone)}</p>` : ''}
                                ${data.email || data.contact_info?.main_email ? `<p><strong>Email:</strong> ${escapeHtml(data.email || data.contact_info?.main_email)}</p>` : ''}
                                ${data.industry ? `<p><strong>Industry:</strong> ${escapeHtml(data.industry)}</p>` : ''}
                                ${(data.employee_count || data.employee_range) ? `<p><strong>Employees:</strong> ${escapeHtml(String(data.employee_count || data.employee_range))}</p>` : ''}
                                ${data.year_founded ? `<p><strong>Est.:</strong> ${escapeHtml(String(data.year_founded))}</p>` : ''}
                                ${data.description ? `<p class="text-gray-600 text-xs mt-2">${escapeHtml(data.description.substring(0, 200))}${data.description.length > 200 ? '...' : ''}</p>` : ''}
                            </div>

                            ${data.key_personnel && data.key_personnel.length > 0 ? `
                                <div class="border-t border-green-200 pt-3 mb-4">
                                    <p class="font-medium text-green-900 mb-2">Key Personnel Found (${data.key_personnel.length}):</p>
                                    <div class="space-y-1 text-xs max-h-32 overflow-y-auto">
                                        ${data.key_personnel.map(p => `
                                            <div class="bg-white rounded border p-1.5">
                                                <span class="font-medium">${escapeHtml(p.name || 'Unknown')}</span>
                                                ${p.title ? `<span class="text-gray-500"> - ${escapeHtml(p.title)}</span>` : ''}
                                                ${p.email ? `<span class="text-blue-600 ml-2">${escapeHtml(p.email)}</span>` : ''}
                                            </div>
                                        `).join('')}
                                    </div>
                                </div>
                            ` : ''}

                            <div class="flex gap-2">
                                <button onclick="saveWebEnrichmentData(${inspectionId})"
                                    class="flex-1 px-4 py-2 text-sm font-medium text-white bg-green-600 rounded-md hover:bg-green-700">
                                    Save to Database
                                </button>
                                <button onclick="runApolloEnrichmentOnly(${inspectionId})"
                                    class="flex-1 px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-md hover:bg-indigo-700"
                                    ${webResult.website_url ? '' : 'disabled title="No website found"'}>
                                    Continue with Apollo
                                </button>
                            </div>
                        </div>
                    `;

                    // Enable Apollo button now that we have data
                    const apolloBtn = document.getElementById('btn-apollo-enrich');
                    if (apolloBtn && webResult.website_url) {
                        apolloBtn.disabled = false;
                        apolloBtn.classList.remove('opacity-50');
                    }

                    btn.innerHTML = 'Enrichment Complete';
                    btn.classList.remove('bg-green-600', 'hover:bg-green-700');
                    btn.classList.add('bg-gray-400');
                } else {
                    resultContainer.innerHTML = `
                        <div class="bg-yellow-50 rounded-lg p-4">
                            <div class="flex items-center gap-2 mb-2">
                                <svg class="w-5 h-5 text-yellow-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path>
                                </svg>
                            <h3 class="font-medium text-yellow-900">Limited Results</h3>
                        </div>
                        <p class="text-sm text-yellow-700">${webResult.error || 'No website or company data found'}</p>
                        <p class="text-sm text-yellow-600 mt-1">Try Apollo search to find company by name</p>
                    </div>
                `;
                    btn.innerHTML = 'Try Again';
                    btn.disabled = false;
                }
            } catch (e) {
                console.error('Web enrichment error:', e);
                resultContainer.innerHTML = `
                    <div class="bg-red-50 rounded-lg p-4">
                        <div class="flex items-center gap-2 mb-2">
                            <svg class="w-5 h-5 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                            </svg>
                        <h3 class="font-medium text-red-900">Public Enrichment Failed</h3>
                    </div>
                    <p class="text-sm text-red-700">${escapeHtml(e.message || 'Unknown error')}</p>
                </div>
            `;
                btn.innerHTML = 'Retry';
                btn.disabled = false;
            }
        }

        // Save web enrichment data to database
        async function saveWebEnrichmentData(inspectionId) {
            if (!currentWebEnrichmentResult) {
                alert('No web enrichment data to save');
                return;
            }

            try {
                const response = await fetch(`/api/enrichment/save-web-enrichment/${inspectionId}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        data: currentWebEnrichmentResult.data || {},
                        website_url: currentWebEnrichmentResult.website_url,
                        confidence: currentWebEnrichmentResult.confidence || 'medium',
                        source: currentWebEnrichmentResult.source || 'public'
                    })
                });

                const result = await response.json();

                if (result.success) {
                    alert(`Saved successfully! Company: ${result.company_name || 'Unknown'}, Contacts: ${result.contacts_saved || 0}`);
                    closeEnrichmentPreviewModal();

                    // Update button in inspection list
                    const enrichBtn = document.getElementById(`enrich-btn-${inspectionId}`);
                    if (enrichBtn) {
                        enrichBtn.classList.remove('bg-blue-100', 'text-blue-700');
                        enrichBtn.classList.add('bg-green-100', 'text-green-700');
                        enrichBtn.innerHTML = 'Enriched (Public)';
                    }

                    // Display the company data in the modal (if inspection modal is open)
                    await loadCompanyData(inspectionId);
                } else {
                    alert(`Error saving: ${result.error}`);
                }
            } catch (e) {
                console.error('Error saving web enrichment:', e);
                alert('Error saving: ' + e.message);
            }
        }

        // Run Apollo enrichment only (uses credits)
        async function runApolloEnrichmentOnly(inspectionId) {
            const btn = document.getElementById('btn-apollo-enrich');
            const apolloResultContainer = document.getElementById('apollo-result');

            // Check if we have a domain from web enrichment
            let domainForApollo = null;
            if (currentWebEnrichmentResult?.website_url) {
                try {
                    domainForApollo = new URL(currentWebEnrichmentResult.website_url).hostname.replace('www.', '');
                } catch (e) {}
            } else if (currentEnrichmentPreview?.existingWebsite) {
                try {
                    domainForApollo = new URL(currentEnrichmentPreview.existingWebsite).hostname.replace('www.', '');
                } catch (e) {}
            } else if (currentEnrichmentPreview?.existingDomain) {
                domainForApollo = currentEnrichmentPreview.existingDomain;
            }

            btn.disabled = true;
            btn.innerHTML = `
                <svg class="w-4 h-4 mr-1 animate-spin inline" fill="none" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
                </svg>
                Searching Apollo...
            `;

            try {
                let apolloUrl = `/api/enrichment/apollo-search/${inspectionId}`;
                if (domainForApollo) {
                    apolloUrl += `?domain=${encodeURIComponent(domainForApollo)}`;
                }

                const apolloResult = await fetch(apolloUrl, { method: 'POST' }).then(r => r.json());
                currentApolloResult = apolloResult;

                // Show Apollo results
                apolloResultContainer.classList.remove('hidden');

                if (apolloResult.success && apolloResult.organization) {
                    const org = apolloResult.organization;
                    const people = apolloResult.people;
                    const allContacts = [...(people?.safety_contacts || []), ...(people?.executive_contacts || [])];

                    apolloResultContainer.innerHTML = `
                        <div class="bg-indigo-50 rounded-lg p-4">
                            <div class="flex items-center gap-2 mb-3">
                                <svg class="w-5 h-5 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
                                </svg>
                                <h3 class="font-medium text-indigo-900">Apollo Match Found</h3>
                                <span class="text-xs text-indigo-600">(${apolloResult.credits_used} credits used)</span>
                            </div>
                            <div class="text-sm space-y-2 mb-4">
                                <p><strong>Company:</strong> ${escapeHtml(org.name || 'Unknown')}</p>
                                ${org.domain ? `<p><strong>Domain:</strong> ${escapeHtml(org.domain)}</p>` : ''}
                                ${org.industry ? `<p><strong>Industry:</strong> ${escapeHtml(org.industry)}</p>` : ''}
                                ${org.employee_range ? `<p><strong>Employees:</strong> ${escapeHtml(org.employee_range)}</p>` : ''}
                                ${org.phone ? `<p><strong>Phone:</strong> ${escapeHtml(org.phone)}</p>` : ''}
                                ${org.city && org.state ? `<p><strong>Location:</strong> ${escapeHtml(org.city)}, ${escapeHtml(org.state)}</p>` : ''}
                            </div>
                            ${allContacts.length ? `
                                <div class="border-t border-indigo-200 pt-3 mb-4">
                                    <div class="flex justify-between items-center mb-2">
                                        <p class="font-medium text-indigo-900">Contacts Found (${allContacts.length}):</p>
                                        <label class="flex items-center gap-1 text-xs text-indigo-700 cursor-pointer">
                                            <input type="checkbox" id="select-all-contacts" onchange="toggleAllContacts(this.checked)" class="rounded">
                                            Select All
                                        </label>
                                    </div>
                                    <p class="text-xs text-gray-500 mb-2">Select contacts to reveal their info (1 credit per contact)</p>
                                    <div class="space-y-2 max-h-48 overflow-y-auto">
                                        ${allContacts.map((c, idx) => {
                                            const isSafety = (people?.safety_contacts || []).includes(c);
                                            return `
                                            <label class="flex items-center gap-2 p-2 bg-white rounded border hover:bg-gray-50 cursor-pointer">
                                                <input type="checkbox" class="contact-checkbox rounded" value="${escapeHtml(c.apollo_person_id || '')}" data-idx="${idx}">
                                                <span class="px-1.5 py-0.5 ${isSafety ? 'bg-green-100 text-green-800' : 'bg-purple-100 text-purple-800'} text-xs rounded">${isSafety ? 'Safety' : 'Exec'}</span>
                                                <div class="flex-1 min-w-0">
                                                    <div class="font-medium text-sm truncate">${escapeHtml(c.full_name || 'Unknown')}</div>
                                                    <div class="text-xs text-gray-500 truncate">${escapeHtml(c.title || 'No title')}</div>
                                                </div>
                                                ${c.email ? '<span class="text-xs text-green-600">Has email</span>' : '<span class="text-xs text-gray-400">No email yet</span>'}
                                            </label>
                                        `}).join('')}
                                    </div>
                                    <!-- Reveal options -->
                                    <div class="mt-3 p-3 bg-gray-50 rounded-lg border">
                                        <p class="text-xs font-medium text-gray-700 mb-2">What to reveal:</p>
                                        <div class="flex gap-4">
                                            <label class="flex items-center gap-2 text-sm cursor-pointer">
                                                <input type="checkbox" id="reveal-email-option" checked class="rounded" onchange="updateRevealButtonState()">
                                                <span>Email</span>
                                            </label>
                                            <label class="flex items-center gap-2 text-sm cursor-pointer">
                                                <input type="checkbox" id="reveal-phone-option" class="rounded" onchange="updateRevealButtonState()">
                                                <span>Phone</span>
                                                <span class="text-xs text-yellow-600">(requires webhook)</span>
                                            </label>
                                        </div>
                                    </div>
                                    <button id="reveal-contacts-btn" onclick="revealSelectedContacts(${inspectionId})"
                                        class="w-full mt-3 px-4 py-2 text-sm font-medium text-white bg-orange-500 rounded-md hover:bg-orange-600 disabled:opacity-50 disabled:cursor-not-allowed"
                                        disabled>
                                        Reveal for Selected (0 credits)
                                    </button>
                                </div>
                            ` : '<p class="text-sm text-gray-500 mb-4">No contacts found at this company</p>'}
                            <div id="revealed-contacts-container" class="hidden mb-4"></div>
                            <button id="confirm-save-btn" onclick="confirmAndSaveEnrichment(${inspectionId})"
                                class="w-full px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-md hover:bg-indigo-700">
                                Save Company to Database
                            </button>
                        </div>
                    `;

                    // Add event listeners for checkbox changes
                    document.querySelectorAll('.contact-checkbox').forEach(cb => {
                        cb.addEventListener('change', updateRevealButtonState);
                    });

                    btn.innerHTML = 'Search Complete';
                    btn.classList.remove('bg-indigo-600', 'hover:bg-indigo-700');
                    btn.classList.add('bg-green-600');
                } else {
                    apolloResultContainer.innerHTML = `
                        <div class="bg-red-50 rounded-lg p-4">
                            <div class="flex items-center gap-2 mb-2">
                                <svg class="w-5 h-5 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                                </svg>
                                <h3 class="font-medium text-red-900">No Apollo Match</h3>
                            </div>
                            <p class="text-sm text-red-700">${apolloResult.error || 'No organization found in Apollo'}</p>
                            <p class="text-xs text-red-500 mt-1">Credits used: ${apolloResult.credits_used}</p>
                        </div>
                    `;
                    btn.innerHTML = 'No Results - Try Again';
                    btn.disabled = false;
                }
            } catch (e) {
                console.error('Apollo search error:', e);
                apolloResultContainer.classList.remove('hidden');
                apolloResultContainer.innerHTML = `
                    <div class="bg-red-50 rounded-lg p-4">
                        <div class="flex items-center gap-2 mb-2">
                            <svg class="w-5 h-5 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                            </svg>
                            <h3 class="font-medium text-red-900">Apollo Search Failed</h3>
                        </div>
                        <p class="text-sm text-red-700">${escapeHtml(e.message || 'Unknown error')}</p>
                    </div>
                `;
                btn.innerHTML = 'Error - Retry';
                btn.disabled = false;
            }
        }

        /**
         * Normalize and extract company data from various API response formats.
         * Returns a standardized object for use in display functions.
         */
        function normalizeCompanyData(data) {
            // Handle both API response formats (enrichment result vs stored company)
            const companyName = data.official_name || data.name;
            const employees = data.employee_range || data.employee_count || data.employee_estimate;
            const phone = data.contact_info?.main_phone || data.phone;
            const email = data.contact_info?.main_email || data.email;
            const hq = data.headquarters || {};
            const city = hq.city || data.city;
            const state = hq.state || data.state;
            const address = hq.address || data.address;
            const postalCode = hq.postal_code || data.postal_code;
            const social = data.social_media || data;
            const registration = data.business_registration || data;

            // Parse services if it's a JSON string
            let services = data.services;
            if (typeof services === 'string') {
                try { services = JSON.parse(services); } catch(e) { services = null; }
            }

            // Parse other_locations if it's a JSON string
            let otherLocations = data.other_locations || data.other_addresses;
            if (typeof otherLocations === 'string') {
                try { otherLocations = JSON.parse(otherLocations); } catch(e) { otherLocations = null; }
            }

            // Get contacts (from API response or key_personnel)
            const contacts = data.contacts || data.key_personnel || [];

            return {
                companyName,
                employees,
                phone,
                email,
                city,
                state,
                address,
                postalCode,
                social,
                registration,
                services,
                otherLocations,
                contacts,
                data // Keep original data for other fields
            };
        }

        /**
         * Build the social links HTML row.
         */
        function buildSocialLinksHTML(social, websiteUrl) {
            return `
                <div class="flex items-center gap-3 flex-wrap">
                    ${social.linkedin_url ? `
                        <a href="${social.linkedin_url}" target="_blank" class="text-blue-700 hover:text-blue-900" title="LinkedIn">
                            <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 24 24"><path d="M19 0h-14c-2.761 0-5 2.239-5 5v14c0 2.761 2.239 5 5 5h14c2.762 0 5-2.239 5-5v-14c0-2.761-2.238-5-5-5zm-11 19h-3v-11h3v11zm-1.5-12.268c-.966 0-1.75-.79-1.75-1.764s.784-1.764 1.75-1.764 1.75.79 1.75 1.764-.783 1.764-1.75 1.764zm13.5 12.268h-3v-5.604c0-3.368-4-3.113-4 0v5.604h-3v-11h3v1.765c1.396-2.586 7-2.777 7 2.476v6.759z"/></svg>
                        </a>
                    ` : ''}
                    ${social.facebook_url ? `
                        <a href="${social.facebook_url}" target="_blank" class="text-blue-600 hover:text-blue-800" title="Facebook">
                            <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 24 24"><path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/></svg>
                        </a>
                    ` : ''}
                    ${social.twitter_url ? `
                        <a href="${social.twitter_url}" target="_blank" class="text-gray-800 hover:text-black" title="Twitter/X">
                            <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 24 24"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg>
                        </a>
                    ` : ''}
                    ${social.instagram_url ? `
                        <a href="${social.instagram_url}" target="_blank" class="text-pink-600 hover:text-pink-800" title="Instagram">
                            <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 24 24"><path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zm0-2.163c-3.259 0-3.667.014-4.947.072-4.358.2-6.78 2.618-6.98 6.98-.059 1.281-.073 1.689-.073 4.948 0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98 1.281.058 1.689.072 4.948.072 3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98-1.281-.059-1.69-.073-4.949-.073zm0 5.838c-3.403 0-6.162 2.759-6.162 6.162s2.759 6.163 6.162 6.163 6.162-2.759 6.162-6.163c0-3.403-2.759-6.162-6.162-6.162zm0 10.162c-2.209 0-4-1.79-4-4 0-2.209 1.791-4 4-4s4 1.791 4 4c0 2.21-1.791 4-4 4zm6.406-11.845c-.796 0-1.441.645-1.441 1.44s.645 1.44 1.441 1.44c.795 0 1.439-.645 1.439-1.44s-.644-1.44-1.439-1.44z"/></svg>
                        </a>
                    ` : ''}
                    ${social.youtube_url ? `
                        <a href="${social.youtube_url}" target="_blank" class="text-red-600 hover:text-red-800" title="YouTube">
                            <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 24 24"><path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/></svg>
                        </a>
                    ` : ''}
                    ${websiteUrl ? `
                        <a href="${websiteUrl}" target="_blank" class="text-xs text-blue-600 hover:text-blue-800 flex items-center gap-1 ml-2 px-2 py-1 bg-blue-50 rounded">
                            <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"></path>
                            </svg>
                            Website
                        </a>
                    ` : ''}
                </div>
            `;
        }

        /**
         * Build the main company content HTML (shared between both modals).
         * @param {Object} normalized - Normalized company data from normalizeCompanyData()
         * @param {Object} options - Display options
         * @param {number} options.companyId - Company ID (for related inspections)
         * @param {number} options.inspectionId - Inspection ID (for action buttons)
         * @param {boolean} options.showActions - Whether to show action buttons (Email, Apollo)
         */
        function buildCompanyContentHTML(normalized, options = {}) {
            const { companyName, employees, phone, email, city, state, address, postalCode, social, registration, services, otherLocations, contacts, data } = normalized;
            const { companyId, inspectionId, showActions = false } = options;
            const websiteUrl = data.website;

            return `
                <div class="space-y-6">
                    <!-- Social Links Row -->
                    <div class="flex items-center justify-between flex-wrap gap-2">
                        ${buildSocialLinksHTML(social, websiteUrl)}
                        ${showActions && inspectionId ? `
                            <div class="flex items-center gap-2">
                                <button onclick="openEmailModal(${inspectionId})" class="text-xs text-purple-600 hover:text-purple-800 flex items-center gap-1 px-2 py-1 bg-purple-50 rounded hover:bg-purple-100 transition-colors">
                                    <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"></path>
                                    </svg>
                                    Generate Email
                                </button>
                                <button onclick="openApolloEnrichmentModal(${inspectionId})" class="text-xs text-indigo-600 hover:text-indigo-800 flex items-center gap-1 px-2 py-1 bg-indigo-50 rounded hover:bg-indigo-100 transition-colors">
                                    <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z"></path>
                                    </svg>
                                    Enrich with Apollo
                                </button>
                            </div>
                        ` : ''}
                    </div>

                    <!-- Basic Info Grid -->
                    <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
                        ${companyName ? `
                            <div class="col-span-2">
                                <p class="text-xs text-gray-500 uppercase tracking-wider">Official Name</p>
                                <p class="mt-1 text-sm font-medium text-gray-900">${escapeHtml(companyName)}</p>
                            </div>
                        ` : ''}
                        ${data.industry ? `
                            <div>
                                <p class="text-xs text-gray-500 uppercase tracking-wider">Industry</p>
                                <p class="mt-1 text-sm font-medium text-gray-900">${escapeHtml(data.industry)}</p>
                            </div>
                        ` : ''}
                        ${data.sub_industry ? `
                            <div>
                                <p class="text-xs text-gray-500 uppercase tracking-wider">Sub-Industry</p>
                                <p class="mt-1 text-sm font-medium text-gray-900">${escapeHtml(data.sub_industry)}</p>
                            </div>
                        ` : ''}
                        ${employees ? `
                            <div>
                                <p class="text-xs text-gray-500 uppercase tracking-wider">Employees</p>
                                <p class="mt-1 text-sm font-medium text-gray-900">${escapeHtml(String(employees))}</p>
                            </div>
                        ` : ''}
                        ${data.year_founded ? `
                            <div>
                                <p class="text-xs text-gray-500 uppercase tracking-wider">Founded</p>
                                <p class="mt-1 text-sm font-medium text-gray-900">${escapeHtml(String(data.year_founded))} (${new Date().getFullYear() - data.year_founded} years)</p>
                            </div>
                        ` : ''}
                        ${registration.business_type || data.business_type ? `
                            <div>
                                <p class="text-xs text-gray-500 uppercase tracking-wider">Business Type</p>
                                <p class="mt-1 text-sm font-medium text-gray-900">${escapeHtml(registration.business_type || data.business_type)}</p>
                            </div>
                        ` : ''}
                        ${registration.registration_number || data.registration_number ? `
                            <div>
                                <p class="text-xs text-gray-500 uppercase tracking-wider">Registration #</p>
                                <p class="mt-1 text-sm font-medium text-gray-900">${escapeHtml(registration.registration_number || data.registration_number)}</p>
                            </div>
                        ` : ''}
                    </div>

                    <!-- Contact Info Section -->
                    ${phone || email ? `
                        <div class="border-t border-gray-100 pt-4">
                            <p class="text-xs text-gray-500 uppercase tracking-wider mb-2">Contact Information</p>
                            <div class="grid grid-cols-2 md:grid-cols-3 gap-4">
                                ${phone ? `
                                    <div>
                                        <p class="text-xs text-gray-400">Phone</p>
                                        <a href="tel:${escapeHtml(phone)}" class="text-sm font-medium text-blue-600 hover:text-blue-800">${escapeHtml(phone)}</a>
                                    </div>
                                ` : ''}
                                ${email ? `
                                    <div>
                                        <p class="text-xs text-gray-400">Email</p>
                                        <a href="mailto:${escapeHtml(email)}" class="text-sm font-medium text-blue-600 hover:text-blue-800">${escapeHtml(email)}</a>
                                    </div>
                                ` : ''}
                            </div>
                        </div>
                    ` : ''}

                    <!-- Address Section -->
                    ${address || city ? `
                        <div class="border-t border-gray-100 pt-4">
                            <p class="text-xs text-gray-500 uppercase tracking-wider mb-2">Headquarters</p>
                            <p class="text-sm text-gray-900">
                                ${address ? escapeHtml(address) + '<br>' : ''}
                                ${[city, state, postalCode].filter(Boolean).map(escapeHtml).join(', ')}
                            </p>
                        </div>
                    ` : ''}

                    <!-- Other Locations -->
                    ${otherLocations && otherLocations.length > 0 ? `
                        <div class="border-t border-gray-100 pt-4">
                            <p class="text-xs text-gray-500 uppercase tracking-wider mb-2">Other Locations</p>
                            <div class="space-y-2">
                                ${otherLocations.map(loc => `
                                    <div class="text-sm text-gray-700 flex items-start gap-2">
                                        <svg class="w-4 h-4 text-gray-400 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"></path>
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"></path>
                                        </svg>
                                        <span>${escapeHtml(loc.address || loc)}${loc.type ? ` <span class="text-gray-400">(${escapeHtml(loc.type)})</span>` : ''}</span>
                                    </div>
                                `).join('')}
                            </div>
                        </div>
                    ` : ''}

                    <!-- Description -->
                    ${data.description ? `
                        <div class="border-t border-gray-100 pt-4">
                            <p class="text-xs text-gray-500 uppercase tracking-wider mb-2">Description</p>
                            <p class="text-sm text-gray-700">${escapeHtml(data.description)}</p>
                        </div>
                    ` : ''}

                    <!-- Services -->
                    ${services && services.length > 0 ? `
                        <div class="border-t border-gray-100 pt-4">
                            <p class="text-xs text-gray-500 uppercase tracking-wider mb-2">Services</p>
                            <div class="flex flex-wrap gap-1">
                                ${services.map(s => `<span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-800">${escapeHtml(s)}</span>`).join('')}
                            </div>
                        </div>
                    ` : ''}

                    <!-- Key Personnel / Contacts -->
                    ${contacts && contacts.length > 0 ? `
                        <div class="border-t border-gray-100 pt-4">
                            <p class="text-xs text-gray-500 uppercase tracking-wider mb-3">Key Personnel</p>
                            <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
                                ${contacts.map(p => `
                                    <div class="bg-gray-50 rounded-lg p-3 border border-gray-100">
                                        <div class="flex items-start justify-between">
                                            <div>
                                                <p class="text-sm font-semibold text-gray-900">${escapeHtml(p.full_name || p.name || [p.first_name, p.last_name].filter(Boolean).join(' '))}</p>
                                                ${p.title ? `<p class="text-xs text-gray-500">${escapeHtml(p.title)}</p>` : ''}
                                            </div>
                                            ${p.linkedin_url ? `
                                                <a href="${p.linkedin_url}" target="_blank" class="text-blue-700 hover:text-blue-900" title="LinkedIn Profile">
                                                    <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M19 0h-14c-2.761 0-5 2.239-5 5v14c0 2.761 2.239 5 5 5h14c2.762 0 5-2.239 5-5v-14c0-2.761-2.238-5-5-5zm-11 19h-3v-11h3v11zm-1.5-12.268c-.966 0-1.75-.79-1.75-1.764s.784-1.764 1.75-1.764 1.75.79 1.75 1.764-.783 1.764-1.75 1.764zm13.5 12.268h-3v-5.604c0-3.368-4-3.113-4 0v5.604h-3v-11h3v1.765c1.396-2.586 7-2.777 7 2.476v6.759z"/></svg>
                                                </a>
                                            ` : ''}
                                        </div>
                                        ${(p.email || p.phone) ? `
                                            <div class="mt-2 flex flex-wrap gap-3 text-xs">
                                                ${p.email ? `
                                                    <a href="mailto:${escapeHtml(p.email)}" class="text-blue-600 hover:text-blue-800 flex items-center gap-1">
                                                        <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"></path>
                                                        </svg>
                                                        ${escapeHtml(p.email)}
                                                    </a>
                                                ` : ''}
                                                ${p.phone ? `
                                                    <a href="tel:${escapeHtml(p.phone)}" class="text-blue-600 hover:text-blue-800 flex items-center gap-1">
                                                        <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z"></path>
                                                        </svg>
                                                        ${escapeHtml(p.phone)}
                                                    </a>
                                                ` : ''}
                                            </div>
                                        ` : ''}
                                    </div>
                                `).join('')}
                            </div>
                        </div>
                    ` : ''}

                    <!-- Certifications -->
                    ${data.certifications && data.certifications.length > 0 ? `
                        <div class="border-t border-gray-100 pt-4">
                            <p class="text-xs text-gray-500 uppercase tracking-wider mb-2">Certifications</p>
                            <div class="flex flex-wrap gap-1">
                                ${data.certifications.map(c => `<span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800">${escapeHtml(c)}</span>`).join('')}
                            </div>
                        </div>
                    ` : ''}

                    <!-- Safety Programs -->
                    ${data.safety_programs && data.safety_programs.length > 0 ? `
                        <div class="border-t border-gray-100 pt-4">
                            <p class="text-xs text-gray-500 uppercase tracking-wider mb-2">Safety Programs</p>
                            <div class="flex flex-wrap gap-1">
                                ${data.safety_programs.map(s => `<span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800">${escapeHtml(s)}</span>`).join('')}
                            </div>
                        </div>
                    ` : ''}

                    <!-- Related Inspections (populated via JavaScript) -->
                    ${companyId ? `
                        <div id="related-inspections-section" class="border-t border-gray-100 pt-4">
                            <div class="flex items-center justify-between mb-3">
                                <p class="text-xs text-gray-500 uppercase tracking-wider">Related OSHA Inspections</p>
                                <span id="related-inspections-count" class="text-xs text-gray-400"></span>
                            </div>
                            <div id="related-inspections-loading" class="text-sm text-gray-500 flex items-center gap-2">
                                <svg class="animate-spin h-4 w-4 text-gray-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                </svg>
                                Loading inspections...
                            </div>
                            <div id="related-inspections-content" class="hidden"></div>
                            <div id="related-inspections-empty" class="hidden text-sm text-gray-500">
                                No related inspections found.
                            </div>
                        </div>
                    ` : ''}
                </div>
            `;
        }

        /**
         * Display company data in the inspection detail modal.
         * This wraps buildCompanyContentHTML with the appropriate header.
         */
        function displayCompanyData(inspectionId, result) {
            const section = document.getElementById(`company-data-section-${inspectionId}`);
            if (!section || !result.data) return;

            const data = result.data;
            const confidence = result.confidence || data.confidence || 'unknown';
            const isFromRelated = result.isFromRelated || false;
            const companyId = data.id;

            // Normalize the data
            const normalized = normalizeCompanyData(data);

            // Confidence badge colors and labels
            const confidenceBadge = {
                high: { bg: 'bg-green-100', text: 'text-green-800', label: 'High Confidence' },
                medium: { bg: 'bg-yellow-100', text: 'text-yellow-800', label: 'Medium Confidence' },
                low: { bg: 'bg-orange-100', text: 'text-orange-800', label: 'Low Confidence' },
                unknown: { bg: 'bg-gray-100', text: 'text-gray-600', label: 'Unverified' }
            }[confidence] || { bg: 'bg-gray-100', text: 'text-gray-600', label: 'Unknown' };

            section.innerHTML = `
                <div class="border-t border-gray-200">
                    <!-- Header -->
                    <div class="px-6 py-4 bg-green-50 border-b border-gray-200">
                        <div class="flex items-center justify-between flex-wrap gap-2">
                            <div class="flex items-center gap-3 flex-wrap">
                                <h3 class="text-sm font-semibold text-gray-900 uppercase tracking-wider">
                                    Company Information (Enriched)
                                </h3>
                                <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${confidenceBadge.bg} ${confidenceBadge.text}" title="Data verification confidence level">
                                    ${confidenceBadge.label}
                                </span>
                                ${isFromRelated ? `
                                    <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800" title="Data from another inspection of this company">
                                        <svg class="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1"></path>
                                        </svg>
                                        From Related Inspection
                                    </span>
                                ` : ''}
                            </div>
                        </div>
                    </div>

                    <div class="px-6 py-4">
                        ${buildCompanyContentHTML(normalized, { companyId, inspectionId, showActions: true })}
                    </div>
                </div>
            `;

            // Load related inspections if we have a company ID
            if (companyId) {
                loadRelatedInspections(companyId);
            }
        }

        async function loadCompanyData(inspectionId) {
            try {
                const company = await fetch(`${API_BASE}/${inspectionId}/company`).then(r => r.json());
                if (company) {
                    displayCompanyData(inspectionId, {
                        data: company,
                        website_url: company.website,
                        confidence: company.confidence
                    });
                }
            } catch (e) {
                console.error('Error loading company data:', e);
            }
        }

        async function loadCompanyDataOrRelated(inspectionId) {
            try {
                const response = await fetch(`${API_BASE}/${inspectionId}/company-or-related`);
                if (!response.ok) return;

                const result = await response.json();
                if (!result) return;

                const company = result.company;
                const isFromRelated = !result.is_direct;

                // Display the company data
                displayCompanyData(inspectionId, {
                    data: company,
                    website_url: company.website,
                    confidence: company.confidence,
                    isFromRelated: isFromRelated,
                    sourceInspectionId: result.source_inspection_id
                });
            } catch (e) {
                console.error('Error loading company data:', e);
            }
        }

        function formatCronTime(value) {
            if (!value) return 'n/a';
            const dt = new Date(value);
            if (Number.isNaN(dt.getTime())) return 'n/a';
            return dt.toLocaleString();
        }

        function formatCronLine(label, run) {
            if (!run) return `${label}: n/a`;
            const status = run.status || 'unknown';
            const started = formatCronTime(run.started_at);
            const finished = formatCronTime(run.finished_at);
            const error = run.error ? ' (error)' : '';
            return `${label}: ${status}${error} | start ${started} | ${finished}`;
        }

        async function loadCronStatus() {
            const container = document.getElementById('cron-status');
            if (!container) return;

            try {
                const response = await fetch(`${API_BASE}/cron/status`);
                if (response.status === 401) {
                    container.textContent = 'Cron status unavailable (unauthorized).';
                    return;
                }
                if (!response.ok) {
                    container.textContent = 'Cron status unavailable.';
                    return;
                }

                const data = await response.json();
                const latest = data.latest || {};
                const inspections = latest.inspections;
                const violations = latest['violations-bulk'];

                container.innerHTML = [
                    formatCronLine('Inspections', inspections),
                    formatCronLine('Violations', violations),
                ].map(line => `<div>${line}</div>`).join('');
            } catch (e) {
                container.textContent = 'Cron status unavailable.';
            }
        }

        async function triggerInspectionSync() {
            if (!confirm('Sync OSHA inspection records?\\n\\nThis fetches new inspections from the DOL API.')) return;

            const startTime = performance.now();
            console.log('%c[OSHA Inspection Sync] Starting...', 'color: #2563eb; font-weight: bold');
            console.log('[OSHA Inspection Sync] Parameters: days_back=90, max_requests=10');

            try {
                if (window.updateManualSyncStatus) {
                    window.updateManualSyncStatus('Inspections', 'running', 'syncing...');
                }
                console.log('[OSHA Inspection Sync] Sending POST request to API...');
                const response = await fetch(`${API_BASE}/sync?days_back=90&max_requests=10`, { method: 'POST' });
                console.log(`[OSHA Inspection Sync] Response status: ${response.status}`);

                const result = await response.json();
                const elapsed = ((performance.now() - startTime) / 1000).toFixed(1);

                console.log('%c[OSHA Inspection Sync] Complete!', 'color: #16a34a; font-weight: bold');
                console.log(`[OSHA Inspection Sync] Duration: ${elapsed}s`);
                console.log('[OSHA Inspection Sync] Results:', result);
                console.table({
                    'Fetched': result.fetched,
                    'Created': result.created,
                    'Updated': result.updated,
                    'Skipped (old)': result.skipped_old || 0,
                    'Skipped (non-SE)': result.skipped_state || 0,
                    'Errors': result.errors
                });

                let message = `Inspection Sync Complete!\\n\\n`;
                message += `Fetched: ${result.fetched}\\n`;
                message += `Created: ${result.created}\\n`;
                message += `Updated: ${result.updated}\\n`;
                message += `Skipped (old): ${result.skipped_old || 0}\\n`;
                message += `Skipped (non-SE): ${result.skipped_state || 0}\\n`;
                message += `Errors: ${result.errors}`;

                if (result.logs && result.logs.length > 0) {
                    console.log('[OSHA Inspection Sync] Server logs:', result.logs);
                }

                if (window.updateManualSyncStatus) {
                    window.updateManualSyncStatus('Inspections', 'success', `+${result.created} new`);
                }
                alert(message);
                loadInspections();
            } catch (e) {
                const elapsed = ((performance.now() - startTime) / 1000).toFixed(1);
                console.error(`%c[OSHA Inspection Sync] Failed after ${elapsed}s`, 'color: #dc2626; font-weight: bold');
                console.error('[OSHA Inspection Sync] Error:', e);
                if (window.updateManualSyncStatus) {
                    window.updateManualSyncStatus('Inspections', 'failed', e.message);
                }
                alert('Inspection sync failed: ' + e.message);
            }
        }

        async function triggerViolationSync() {
            if (!confirm('Sync violations for existing inspections?\\n\\nThis checks inspections from the past year for new citations/penalties.')) return;

            const startTime = performance.now();
            console.log('%c[OSHA Violation Sync] Starting...', 'color: #7c3aed; font-weight: bold');
            console.log('[OSHA Violation Sync] Parameters: inspection_days_back=365, max_inspections=200, max_requests=50');

            try {
                if (window.updateManualSyncStatus) {
                    window.updateManualSyncStatus('Violations', 'running', 'syncing...');
                }
                console.log('[OSHA Violation Sync] Sending POST request to API...');
                const response = await fetch(`${API_BASE}/sync/violations-recent?inspection_days_back=365&max_inspections=200&max_requests=50`, { method: 'POST' });
                console.log(`[OSHA Violation Sync] Response status: ${response.status}`);

                const result = await response.json();
                const elapsed = ((performance.now() - startTime) / 1000).toFixed(1);

                console.log('%c[OSHA Violation Sync] Complete!', 'color: #16a34a; font-weight: bold');
                console.log(`[OSHA Violation Sync] Duration: ${elapsed}s`);
                console.log('[OSHA Violation Sync] Results:', result);
                console.table({
                    'Inspections checked': result.inspections_checked,
                    'Violations fetched': result.violations_fetched,
                    'New violations': result.violations_inserted,
                    'Updated violations': result.violations_updated,
                    'Inspections with new': result.inspections_with_new_violations,
                    'Errors': result.errors
                });

                let message = `Violation Sync Complete!\\n\\n`;
                message += `Inspections checked: ${result.inspections_checked}\\n`;
                message += `Violations fetched: ${result.violations_fetched}\\n`;
                message += `New violations: ${result.violations_inserted}\\n`;
                message += `Updated violations: ${result.violations_updated}\\n`;
                message += `Inspections with new: ${result.inspections_with_new_violations}\\n`;
                message += `Errors: ${result.errors}`;

                if (result.logs && result.logs.length > 0) {
                    console.log('[OSHA Violation Sync] Server logs:', result.logs);
                }

                if (window.updateManualSyncStatus) {
                    window.updateManualSyncStatus('Violations', 'success', `+${result.violations_inserted} new`);
                }
                alert(message);
                loadInspections();
                loadNewViolations();
            } catch (e) {
                const elapsed = ((performance.now() - startTime) / 1000).toFixed(1);
                console.error(`%c[OSHA Violation Sync] Failed after ${elapsed}s`, 'color: #dc2626; font-weight: bold');
                console.error('[OSHA Violation Sync] Error:', e);
                if (window.updateManualSyncStatus) {
                    window.updateManualSyncStatus('Violations', 'failed', e.message);
                }
                alert('Violation sync failed: ' + e.message);
            }
        }

        function escapeHtml(text) {
            if (!text) return '';
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        // Enriched Companies modal functions
        let enrichedCompaniesCache = {};  // Cache for company data to avoid re-fetching

        async function openEnrichedCompaniesModal() {
            document.getElementById('enriched-companies-modal').classList.remove('hidden');
            await loadEnrichedCompanies();
        }

        function closeEnrichedCompaniesModal() {
            document.getElementById('enriched-companies-modal').classList.add('hidden');
        }

        async function loadEnrichedCompanies() {
            try {
                const data = await fetch(`${API_BASE}/companies/enriched`).then(r => r.json());
                const list = document.getElementById('enriched-companies-list');
                const noData = document.getElementById('no-enriched-companies');
                const countEl = document.getElementById('enriched-count');

                countEl.textContent = `(${data.total} companies)`;

                // Cache each company by ID for instant modal display
                enrichedCompaniesCache = {};
                data.items.forEach(company => {
                    enrichedCompaniesCache[company.id] = company;
                });

                if (data.items.length === 0) {
                    list.innerHTML = '';
                    noData.classList.remove('hidden');
                    return;
                }

                noData.classList.add('hidden');
                list.innerHTML = data.items.map(company => `
                    <tr class="hover:bg-gray-50">
                        <td class="px-4 py-3">
                            <div class="font-medium text-gray-900">${escapeHtml(company.name)}</div>
                            ${company.website ? `<a href="${company.website}" target="_blank" class="text-xs text-blue-600 hover:text-blue-800">${escapeHtml(company.website.replace('https://', '').replace('http://', '').split('/')[0])}</a>` : ''}
                        </td>
                        <td class="px-4 py-3 text-sm text-gray-600">${escapeHtml(company.industry || '-')}</td>
                        <td class="px-4 py-3 text-sm text-gray-600">${[company.city, company.state].filter(Boolean).join(', ') || '-'}</td>
                        <td class="px-4 py-3 text-sm">
                            ${company.phone ? `<a href="tel:${company.phone}" class="text-blue-600 hover:text-blue-800">${escapeHtml(company.phone)}</a>` : '-'}
                        </td>
                        <td class="px-4 py-3 text-sm font-medium ${company.total_penalty > 10000 ? 'text-red-600' : 'text-gray-900'}">
                            ${company.total_penalty ? '$' + company.total_penalty.toLocaleString() : '-'}
                        </td>
                        <td class="px-4 py-3 text-xs text-gray-500">
                            ${company.created_at ? new Date(company.created_at).toLocaleDateString() : '-'}
                        </td>
                        <td class="px-4 py-3">
                            <div class="flex items-center gap-2">
                                <button onclick="viewCompanyDetail(${company.id})" class="text-blue-600 hover:text-blue-800 text-sm font-medium">
                                    View
                                </button>
                                <button onclick="addCompanyToCRM(${company.inspection_id})"
                                    class="text-green-600 hover:text-green-800 text-sm font-medium"
                                    title="Add to CRM">
                                    + CRM
                                </button>
                            </div>
                        </td>
                    </tr>
                `).join('');
            } catch (e) {
                console.error('Error loading enriched companies:', e);
            }
        }


        async function viewCompanyDetail(companyId) {
            try {
                const modal = document.getElementById('company-detail-modal');
                const content = document.getElementById('company-detail-content');

                // Use cached data if available for instant display
                let company = enrichedCompaniesCache[companyId];
                let needsFullFetch = !company || !company.contacts;

                // If not cached, fetch from API
                if (!company) {
                    company = await fetch(`${API_BASE}/companies/${companyId}`).then(r => r.json());
                    needsFullFetch = false;  // Full fetch includes contacts
                }

                // Helper function to render the modal content
                const renderModal = (companyData) => {
                    window.currentEditCompany = companyData;
                    const normalized = normalizeCompanyData(companyData);

                    content.innerHTML = `
                        <div class="p-6 border-b flex justify-between items-center bg-green-50 flex-wrap gap-4">
                            <div>
                                <h2 class="text-xl font-semibold" id="company-name-display">${escapeHtml(companyData.name)}</h2>
                                <p class="text-sm text-gray-500">${[companyData.city, companyData.state].filter(Boolean).join(', ')}</p>
                            </div>
                            <div class="flex items-center gap-2 flex-wrap">
                                <button onclick="toggleEditMode(${companyData.id})" id="edit-company-btn"
                                    class="inline-flex items-center px-3 py-1.5 text-sm font-medium rounded-md bg-yellow-500 text-white hover:bg-yellow-600 transition-colors">
                                    <svg class="w-4 h-4 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"></path>
                                    </svg>
                                    Edit
                                </button>
                                <button onclick="reEnrichWithApollo(${companyData.inspection_id}, ${companyData.id})"
                                    class="inline-flex items-center px-3 py-1.5 text-sm font-medium rounded-md bg-indigo-600 text-white hover:bg-indigo-700 transition-colors">
                                    <svg class="w-4 h-4 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path>
                                    </svg>
                                    Apollo
                                </button>
                                <button onclick="addCompanyToCRM(${companyData.inspection_id})"
                                    id="add-to-crm-btn-${companyData.id}"
                                    class="inline-flex items-center px-3 py-1.5 text-sm font-medium rounded-md bg-green-600 text-white hover:bg-green-700 transition-colors">
                                    <svg class="w-4 h-4 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z"></path>
                                    </svg>
                                    Add to CRM
                                </button>
                                <button onclick="openEmailModal(${companyData.inspection_id})"
                                    class="inline-flex items-center px-3 py-1.5 text-sm font-medium rounded-md bg-purple-600 text-white hover:bg-purple-700 transition-colors">
                                    <svg class="w-4 h-4 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"></path>
                                    </svg>
                                    Generate Email
                                </button>
                                <button onclick="closeCompanyDetailModal()" class="text-gray-500 hover:text-gray-700 text-2xl">&times;</button>
                            </div>
                        </div>
                        <div id="company-detail-body" class="p-6">
                            ${buildCompanyContentHTML(normalized, { companyId: companyData.id, inspectionId: companyData.inspection_id, showActions: false })}
                        </div>
                        <div id="company-edit-form" class="p-6 hidden">
                            <!-- Edit form will be shown here -->
                        </div>
                    `;
                };

                // Render immediately with cached/fetched data
                renderModal(company);
                modal.classList.remove('hidden');

                // Load related inspections asynchronously
                loadRelatedInspections(companyId);

                // If we used cache without contacts, fetch full data in background and re-render
                if (needsFullFetch) {
                    fetch(`${API_BASE}/companies/${companyId}`)
                        .then(r => r.json())
                        .then(fullCompany => {
                            // Update cache with full data
                            enrichedCompaniesCache[companyId] = fullCompany;
                            // Re-render with contacts
                            renderModal(fullCompany);
                            // Re-load related inspections since DOM was replaced
                            loadRelatedInspections(companyId);
                        })
                        .catch(e => console.log('Background fetch failed:', e));
                }

                // Fetch inspection data for email generation in background
                if (company.inspection_id) {
                    fetch(`${API_BASE}/${company.inspection_id}`)
                        .then(r => r.json())
                        .then(inspection => { currentInspection = inspection; })
                        .catch(e => console.log('Could not load inspection data for email'));
                }
            } catch (e) {
                console.error('Error loading company detail:', e);
            }
        }

        async function addCompanyToCRM(inspectionId) {
            try {
                // Create a prospect from this inspection
                const response = await fetch('/api/crm/prospects', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        inspection_id: inspectionId,
                        status: 'new_lead',
                        priority: 'medium'
                    })
                });

                if (response.ok) {
                    const result = await response.json();
                    alert('Company added to CRM as a new lead!');

                    // Remove the row from the enriched companies table
                    const tableRow = document.querySelector(`tr [onclick="addCompanyToCRM(${inspectionId})"]`)?.closest('tr');
                    if (tableRow) {
                        tableRow.remove();
                        // Update the count
                        const countEl = document.getElementById('enriched-count');
                        if (countEl) {
                            const currentText = countEl.textContent;
                            const match = currentText.match(/\\((\\d+)/);
                            if (match) {
                                const newCount = parseInt(match[1]) - 1;
                                countEl.textContent = `(${newCount} companies)`;
                            }
                        }
                    }

                    // Also update button in company detail modal if open
                    const btn = document.getElementById(`add-to-crm-btn-${inspectionId}`);
                    if (btn) {
                        btn.innerHTML = 'Added to CRM';
                        btn.disabled = true;
                        btn.classList.remove('bg-green-600', 'hover:bg-green-700');
                        btn.classList.add('bg-gray-400', 'cursor-not-allowed');
                    }

                    // Close the company detail modal if open
                    closeCompanyDetailModal();
                } else {
                    const error = await response.json();
                    if (error.detail && error.detail.includes('already exists')) {
                        alert('This company is already in the CRM.');
                    } else {
                        alert('Error adding to CRM: ' + (error.detail || 'Unknown error'));
                    }
                }
            } catch (e) {
                console.error('Error adding to CRM:', e);
                alert('Error adding to CRM');
            }
        }

        function closeCompanyDetailModal() {
            document.getElementById('company-detail-modal').classList.add('hidden');
            window.currentEditCompany = null;
        }

        async function loadRelatedInspections(companyId) {
            const loadingEl = document.getElementById('related-inspections-loading');
            const contentEl = document.getElementById('related-inspections-content');
            const emptyEl = document.getElementById('related-inspections-empty');
            const countEl = document.getElementById('related-inspections-count');

            // Reset state
            loadingEl.classList.remove('hidden');
            contentEl.classList.add('hidden');
            emptyEl.classList.add('hidden');
            countEl.textContent = '';

            try {
                const response = await fetch(`${API_BASE}/companies/${companyId}/related-inspections`);
                if (!response.ok) throw new Error('Failed to load inspections');

                const data = await response.json();
                loadingEl.classList.add('hidden');

                if (data.inspections.length === 0) {
                    emptyEl.classList.remove('hidden');
                    return;
                }

                countEl.textContent = `(${data.total} inspection${data.total !== 1 ? 's' : ''})`;

                // Build the inspections table
                const tableHtml = `
                    <div class="overflow-x-auto">
                        <table class="min-w-full divide-y divide-gray-200">
                            <thead class="bg-gray-50">
                                <tr>
                                    <th class="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Activity #</th>
                                    <th class="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Location</th>
                                    <th class="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Opened</th>
                                    <th class="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Closed</th>
                                    <th class="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Penalty</th>
                                    <th class="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Violations</th>
                                    <th class="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
                                </tr>
                            </thead>
                            <tbody class="bg-white divide-y divide-gray-200">
                                ${data.inspections.map(insp => `
                                    <tr class="${insp.is_primary ? 'bg-blue-50' : 'hover:bg-gray-50'}">
                                        <td class="px-3 py-2 text-sm">
                                            <span class="font-mono text-gray-900">${escapeHtml(insp.activity_nr)}</span>
                                            ${insp.is_primary ? '<span class="ml-1 text-xs text-blue-600 font-medium">(Primary)</span>' : ''}
                                        </td>
                                        <td class="px-3 py-2 text-sm text-gray-600">
                                            ${[insp.site_city, insp.site_state].filter(Boolean).join(', ') || '-'}
                                        </td>
                                        <td class="px-3 py-2 text-sm text-gray-600">
                                            ${insp.open_date ? new Date(insp.open_date).toLocaleDateString() : '-'}
                                        </td>
                                        <td class="px-3 py-2 text-sm text-gray-600">
                                            ${insp.close_case_date ? new Date(insp.close_case_date).toLocaleDateString() : '<span class="text-yellow-600">Open</span>'}
                                        </td>
                                        <td class="px-3 py-2 text-sm font-medium ${insp.total_current_penalty > 10000 ? 'text-red-600' : 'text-gray-900'}">
                                            ${insp.total_current_penalty ? '$' + insp.total_current_penalty.toLocaleString() : '-'}
                                        </td>
                                        <td class="px-3 py-2 text-sm text-gray-600">
                                            ${insp.violation_count > 0 ? `<span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-red-100 text-red-800">${insp.violation_count}</span>` : '-'}
                                        </td>
                                        <td class="px-3 py-2 text-sm">
                                            <button onclick="viewInspectionFromCompany(${insp.id})" class="text-blue-600 hover:text-blue-800 font-medium">
                                                View
                                            </button>
                                        </td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>
                    ${data.total > 1 ? `
                        <div class="mt-3 p-3 bg-amber-50 rounded-lg border border-amber-200">
                            <p class="text-sm text-amber-800">
                                <svg class="inline-block w-4 h-4 mr-1 -mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                                </svg>
                                This company has <strong>${data.total} OSHA inspections</strong> on record. Total penalties: <strong>$${data.inspections.reduce((sum, i) => sum + (i.total_current_penalty || 0), 0).toLocaleString()}</strong>
                            </p>
                        </div>
                    ` : ''}
                `;

                contentEl.innerHTML = tableHtml;
                contentEl.classList.remove('hidden');
            } catch (e) {
                console.error('Error loading related inspections:', e);
                loadingEl.classList.add('hidden');
                emptyEl.textContent = 'Error loading inspections.';
                emptyEl.classList.remove('hidden');
            }
        }

        function viewInspectionFromCompany(inspectionId) {
            // Close the company detail modal and open the inspection detail
            closeCompanyDetailModal();
            closeEnrichedCompaniesModal();
            showDetail(inspectionId);
        }

        // Email Generation Functions
        let currentEmailContent = { subject: '', body: '' };

        function getInspectionTypeName(code) {
            const types = {
                'A': 'Accident Investigation',
                'B': 'Complaint',
                'C': 'Referral',
                'D': 'Monitoring',
                'E': 'Variance',
                'F': 'Follow-up',
                'G': 'Unprogrammed Related',
                'H': 'Planned',
                'I': 'Unprogrammed Other',
                'J': 'Programmed Related',
                'K': 'Programmed Other',
                'L': 'Fatality/Catastrophe'
            };
            return types[code] || 'an inspection';
        }

        // Normalize company names that are ALL CAPS to Title Case
        function normalizeCompanyName(name) {
            if (!name) return name;
            // Check if name is mostly uppercase (more than 80% caps)
            const upperCount = (name.match(/[A-Z]/g) || []).length;
            const letterCount = (name.match(/[a-zA-Z]/g) || []).length;
            if (letterCount > 0 && upperCount / letterCount > 0.8) {
                // Convert to title case, preserving common abbreviations
                return name.toLowerCase().replace(/\\b\\w/g, c => c.toUpperCase())
                    .replace(/\\b(Llc|Inc|Corp|Ltd|Co|Lp|Llp)\\b/gi, m => m.toUpperCase())
                    .replace(/\\b(Usa|Us)\\b/gi, m => m.toUpperCase());
            }
            return name;
        }

        async function openEmailModal(inspectionId) {
            // Get inspection and company data
            const inspection = currentInspection;
            if (!inspection) {
                alert('No inspection data available');
                return;
            }

            // Try to get company data for contact name
            let contactName = null;
            try {
                const company = await fetch(`/api/inspections/${inspectionId}/company`).then(r => r.json());
                if (company && company.contacts && company.contacts.length > 0) {
                    // Find first contact with a name
                    const contact = company.contacts.find(c => c.full_name || c.first_name);
                    if (contact) {
                        contactName = contact.first_name || contact.full_name?.split(' ')[0] || null;
                    }
                }
            } catch (e) {
                console.log('No company/contact data available');
            }

            // Format data for email
            const companyName = normalizeCompanyName(inspection.estab_name) || 'your company';
            const inspectionDate = inspection.open_date ? new Date(inspection.open_date).toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' }) : 'recently';
            const inspectionReason = getInspectionTypeName(inspection.insp_type);

            // Build greeting
            const greeting = contactName ? `Hi ${contactName},` : 'Hi!';

            // Generate email content
            const subject = 'Following Up on Your Recent OSHA Visit';
            const body = `${greeting}

I noticed that ${companyName} was visited by OSHA on ${inspectionDate} regarding ${inspectionReason}.

Dealing with OSHA can be stressful, especially when you're trying to run a business. At TSG Safety, we specialize in helping companies like yours with OSHA compliance and workplace safety - whether that's responding to citations, preparing for follow-up inspections, or building safety programs that prevent future issues.

If you'd like to chat about your situation, I'm happy to help.`;

            // Store for copying
            currentEmailContent = { subject, body };

            // Display in modal
            document.getElementById('email-subject').textContent = subject;
            document.getElementById('email-body').textContent = body;
            document.getElementById('email-modal').classList.remove('hidden');
        }

        function closeEmailModal() {
            document.getElementById('email-modal').classList.add('hidden');
        }

        async function copyEmailToClipboard() {
            const fullEmail = `Subject: ${currentEmailContent.subject}\\n\\n${currentEmailContent.body}`;
            try {
                await navigator.clipboard.writeText(fullEmail);
                // Show success feedback
                const btn = event.target.closest('button');
                const originalHtml = btn.innerHTML;
                btn.innerHTML = `
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
                    </svg>
                    Copied!
                `;
                btn.classList.remove('bg-purple-600', 'hover:bg-purple-700');
                btn.classList.add('bg-green-600');
                setTimeout(() => {
                    btn.innerHTML = originalHtml;
                    btn.classList.remove('bg-green-600');
                    btn.classList.add('bg-purple-600', 'hover:bg-purple-700');
                }, 2000);
            } catch (e) {
                alert('Failed to copy to clipboard. Please select and copy manually.');
            }
        }

        function toggleEditMode(companyId) {
            const detailBody = document.getElementById('company-detail-body');
            const editForm = document.getElementById('company-edit-form');
            const editBtn = document.getElementById('edit-company-btn');
            const company = window.currentEditCompany;

            if (!company) return;

            if (editForm.classList.contains('hidden')) {
                // Switch to edit mode
                detailBody.classList.add('hidden');
                editForm.classList.remove('hidden');
                editBtn.innerHTML = `
                    <svg class="w-4 h-4 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                    </svg>
                    Cancel
                `;
                editBtn.classList.remove('bg-yellow-500', 'hover:bg-yellow-600');
                editBtn.classList.add('bg-gray-500', 'hover:bg-gray-600');

                // Build edit form
                editForm.innerHTML = `
                    <form onsubmit="saveCompanyEdits(event, ${companyId})" class="space-y-6">
                        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                            <!-- Basic Info -->
                            <div class="space-y-4">
                                <h3 class="font-semibold text-gray-900 border-b pb-2">Basic Information</h3>
                                <div>
                                    <label class="block text-sm font-medium text-gray-700 mb-1">Company Name *</label>
                                    <input type="text" name="name" value="${escapeHtml(company.name || '')}" required
                                        class="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500">
                                </div>
                                <div>
                                    <label class="block text-sm font-medium text-gray-700 mb-1">Website</label>
                                    <input type="url" name="website" value="${escapeHtml(company.website || '')}"
                                        class="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                                        placeholder="https://example.com">
                                </div>
                                <div>
                                    <label class="block text-sm font-medium text-gray-700 mb-1">Domain</label>
                                    <input type="text" name="domain" value="${escapeHtml(company.domain || '')}"
                                        class="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                                        placeholder="example.com">
                                </div>
                                <div>
                                    <label class="block text-sm font-medium text-gray-700 mb-1">Industry</label>
                                    <input type="text" name="industry" value="${escapeHtml(company.industry || '')}"
                                        class="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500">
                                </div>
                                <div>
                                    <label class="block text-sm font-medium text-gray-700 mb-1">Sub-Industry</label>
                                    <input type="text" name="sub_industry" value="${escapeHtml(company.sub_industry || '')}"
                                        class="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500">
                                </div>
                                <div class="grid grid-cols-2 gap-4">
                                    <div>
                                        <label class="block text-sm font-medium text-gray-700 mb-1">Employee Count</label>
                                        <input type="number" name="employee_count" value="${company.employee_count || ''}"
                                            class="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500">
                                    </div>
                                    <div>
                                        <label class="block text-sm font-medium text-gray-700 mb-1">Employee Range</label>
                                        <input type="text" name="employee_range" value="${escapeHtml(company.employee_range || '')}"
                                            class="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                                            placeholder="e.g., 11-50">
                                    </div>
                                </div>
                                <div>
                                    <label class="block text-sm font-medium text-gray-700 mb-1">Year Founded</label>
                                    <input type="number" name="year_founded" value="${company.year_founded || ''}" min="1800" max="2030"
                                        class="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500">
                                </div>
                            </div>

                            <!-- Contact & Address -->
                            <div class="space-y-4">
                                <h3 class="font-semibold text-gray-900 border-b pb-2">Contact & Address</h3>
                                <div>
                                    <label class="block text-sm font-medium text-gray-700 mb-1">Phone</label>
                                    <input type="tel" name="phone" value="${escapeHtml(company.phone || '')}"
                                        class="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500">
                                </div>
                                <div>
                                    <label class="block text-sm font-medium text-gray-700 mb-1">Email</label>
                                    <input type="email" name="email" value="${escapeHtml(company.email || '')}"
                                        class="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500">
                                </div>
                                <div>
                                    <label class="block text-sm font-medium text-gray-700 mb-1">Street Address</label>
                                    <input type="text" name="address" value="${escapeHtml(company.address || '')}"
                                        class="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500">
                                </div>
                                <div class="grid grid-cols-3 gap-4">
                                    <div>
                                        <label class="block text-sm font-medium text-gray-700 mb-1">City</label>
                                        <input type="text" name="city" value="${escapeHtml(company.city || '')}"
                                            class="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500">
                                    </div>
                                    <div>
                                        <label class="block text-sm font-medium text-gray-700 mb-1">State</label>
                                        <input type="text" name="state" value="${escapeHtml(company.state || '')}" maxlength="2"
                                            class="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500">
                                    </div>
                                    <div>
                                        <label class="block text-sm font-medium text-gray-700 mb-1">ZIP</label>
                                        <input type="text" name="postal_code" value="${escapeHtml(company.postal_code || '')}"
                                            class="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500">
                                    </div>
                                </div>

                                <h3 class="font-semibold text-gray-900 border-b pb-2 mt-6">Social Media</h3>
                                <div>
                                    <label class="block text-sm font-medium text-gray-700 mb-1">LinkedIn URL</label>
                                    <input type="url" name="linkedin_url" value="${escapeHtml(company.linkedin_url || '')}"
                                        class="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500">
                                </div>
                                <div>
                                    <label class="block text-sm font-medium text-gray-700 mb-1">Facebook URL</label>
                                    <input type="url" name="facebook_url" value="${escapeHtml(company.facebook_url || '')}"
                                        class="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500">
                                </div>
                                <div>
                                    <label class="block text-sm font-medium text-gray-700 mb-1">Twitter/X URL</label>
                                    <input type="url" name="twitter_url" value="${escapeHtml(company.twitter_url || '')}"
                                        class="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500">
                                </div>
                            </div>
                        </div>

                        <!-- Description -->
                        <div>
                            <label class="block text-sm font-medium text-gray-700 mb-1">Description</label>
                            <textarea name="description" rows="3"
                                class="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500">${escapeHtml(company.description || '')}</textarea>
                        </div>

                        <!-- Submit -->
                        <div class="flex justify-end gap-3 pt-4 border-t">
                            <button type="button" onclick="toggleEditMode(${companyId})"
                                class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50">
                                Cancel
                            </button>
                            <button type="submit"
                                class="px-4 py-2 text-sm font-medium text-white bg-green-600 rounded-md hover:bg-green-700">
                                Save Changes
                            </button>
                        </div>
                    </form>
                `;
            } else {
                // Switch back to view mode
                detailBody.classList.remove('hidden');
                editForm.classList.add('hidden');
                editBtn.innerHTML = `
                    <svg class="w-4 h-4 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"></path>
                    </svg>
                    Edit
                `;
                editBtn.classList.remove('bg-gray-500', 'hover:bg-gray-600');
                editBtn.classList.add('bg-yellow-500', 'hover:bg-yellow-600');
            }
        }

        async function saveCompanyEdits(event, companyId) {
            event.preventDefault();

            const form = event.target;
            const formData = new FormData(form);
            const data = {};

            // Collect all form values
            for (const [key, value] of formData.entries()) {
                if (value !== '' && value !== null) {
                    // Convert numeric fields
                    if (key === 'employee_count' || key === 'year_founded') {
                        data[key] = parseInt(value) || null;
                    } else {
                        data[key] = value;
                    }
                }
            }

            try {
                const response = await fetch(`${API_BASE}/companies/${companyId}`, {
                    method: 'PATCH',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });

                const result = await response.json();

                if (result.success) {
                    alert('Company updated successfully!');

                    // Reload the company detail to show updated data
                    closeCompanyDetailModal();
                    await loadEnrichedCompanies();
                    viewCompanyDetail(companyId);
                } else {
                    alert('Error updating company: ' + (result.detail || 'Unknown error'));
                }
            } catch (e) {
                console.error('Error saving company edits:', e);
                alert('Error saving changes');
            }
        }

        async function reEnrichWithApollo(inspectionId, companyId) {
            // Close any open modals first
            closeCompanyDetailModal();
            closeEnrichedCompaniesModal();

            // Open the enrichment preview modal (same flow as new enrichment)
            try {
                // Fetch both the preview and existing company data
                const [preview, companyData] = await Promise.all([
                    fetch(`/api/enrichment/preview/${inspectionId}`).then(r => r.json()),
                    fetch(`/api/inspections/${inspectionId}/company`).then(r => r.json())
                ]);

                currentEnrichmentPreview = preview;
                currentWebEnrichmentResult = null;
                currentApolloResult = null;
                revealedContacts = [];  // Clear revealed contacts for re-enrichment

                // Mark that this is a re-enrichment and include existing website/domain
                preview.isReEnrich = true;
                preview.existingCompanyId = companyId;

                // Pass existing website/domain for Apollo search
                if (companyData && (companyData.website || companyData.domain)) {
                    preview.existingWebsite = companyData.website;
                    preview.existingDomain = companyData.domain;
                }

                showEnrichmentPreviewModal(preview);
            } catch (e) {
                console.error('Error loading enrichment preview:', e);
                alert('Error loading enrichment preview');
            }
        }

        // Close modal on escape or outside click
        document.addEventListener('keydown', e => {
            if (e.key === 'Escape') {
                closeModal();
            }
        });
        document.getElementById('modal').addEventListener('click', e => {
            if (e.target.id === 'modal') closeModal();
        });

        // =============================================================================
        // CRM FUNCTIONS (for sidebar widgets and Add to CRM)
        // =============================================================================

        async function loadCRMStats() {
            try {
                const response = await fetch(`${CRM_API}/stats`);
                const stats = await response.json();

                // Update sidebar widgets
                document.getElementById('crm-total-prospects').textContent = stats.total_prospects || 0;
                document.getElementById('crm-pipeline-value').textContent = `$${(stats.total_pipeline_value || 0).toLocaleString()} pipeline`;
                document.getElementById('crm-upcoming-callbacks').textContent = stats.upcoming_callbacks || 0;

                if (stats.overdue_callbacks > 0) {
                    document.getElementById('crm-overdue-callbacks').textContent = `${stats.overdue_callbacks} overdue`;
                } else {
                    document.getElementById('crm-overdue-callbacks').textContent = '';
                }
            } catch (e) {
                console.error('Error loading CRM stats:', e);
            }
        }

        function getStatusColor(status) {
            const colors = {
                'new_lead': 'bg-blue-100 text-blue-800',
                'contacted': 'bg-yellow-100 text-yellow-800',
                'qualified': 'bg-green-100 text-green-800',
                'won': 'bg-purple-100 text-purple-800',
                'lost': 'bg-red-100 text-red-800'
            };
            return colors[status] || 'bg-gray-100 text-gray-800';
        }

        function formatStatus(status) {
            const labels = {
                'new_lead': 'New Lead',
                'contacted': 'Contacted',
                'qualified': 'Qualified',
                'won': 'Won',
                'lost': 'Lost'
            };
            return labels[status] || status;
        }

        async function addToCRM(inspectionId) {
            try {
                const response = await fetch(`${CRM_API}/prospects`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ inspection_id: inspectionId })
                });

                if (response.ok) {
                    const prospect = await response.json();
                    loadCRMStats();

                    // Update the button in the inspection modal to show "View in CRM"
                    const container = document.getElementById(`crm-action-buttons-${inspectionId}`);
                    if (container) {
                        container.innerHTML = `
                            <div class="flex items-center gap-2">
                                <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${getStatusColor(prospect.status)}">
                                    ${formatStatus(prospect.status)}
                                </span>
                                <a href="/crm"
                                    class="inline-flex items-center px-3 py-1.5 text-sm font-medium rounded-md bg-purple-600 text-white hover:bg-purple-700 transition-colors">
                                    <svg class="w-4 h-4 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path>
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"></path>
                                    </svg>
                                    View in CRM
                                </a>
                            </div>
                        `;
                    }

                    // Navigate to CRM page
                    window.location.href = '/crm';
                } else {
                    const error = await response.json();
                    alert(error.detail || 'Error adding to CRM');
                }
            } catch (e) {
                console.error('Error adding to CRM:', e);
            }
        }

        // Load CRM stats on page load
        loadCRMStats();
    </script>

    <div id="sync-widget" class="fixed bottom-4 right-4 z-50 w-96 bg-white border border-gray-200 rounded-lg shadow-lg">
        <div class="flex items-center justify-between px-3 py-2 border-b bg-gray-50">
            <span class="text-xs font-semibold text-gray-800">Sync Status</span>
            <button id="sync-widget-toggle" class="text-xs text-blue-600 hover:text-blue-800">Hide</button>
        </div>
        <div id="sync-widget-body" class="px-3 py-2 space-y-3">
            <div>
                <div class="text-[10px] font-semibold text-gray-700 mb-1 flex items-center gap-1">
                    <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                    Automatic (Cron)
                </div>
                <div id="sync-widget-cron" class="text-[10px] text-gray-600 space-y-0.5 pl-4">Loading...</div>
            </div>
            <div>
                <div class="text-[10px] font-semibold text-gray-700 mb-1 flex items-center gap-1">
                    <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 15l-2 5L9 9l11 4-5 2zm0 0l5 5M7.188 2.239l.777 2.897M5.136 7.965l-2.898-.777M13.95 4.05l-2.122 2.122m-5.657 5.656l-2.12 2.122"></path></svg>
                    Manual
                </div>
                <div id="sync-widget-manual" class="text-[10px] text-gray-600 space-y-0.5 pl-4">Loading...</div>
            </div>
            <div class="pt-1 border-t">
                <a href="/api/inspections/cron/status?format=html" target="_blank" class="text-[10px] text-blue-600 hover:text-blue-800">View full sync history</a>
            </div>
        </div>
    </div>
    <script>
        (function () {
            const widget = document.getElementById('sync-widget');
            if (!widget) return;
            const body = document.getElementById('sync-widget-body');
            const toggle = document.getElementById('sync-widget-toggle');
            const cronContent = document.getElementById('sync-widget-cron');
            const manualContent = document.getElementById('sync-widget-manual');
            let cronEventSource = null;
            let lastRunId = 0;
            let reconnectTimer = null;

            function setCollapsed(collapsed) {
                body.style.display = collapsed ? 'none' : 'block';
                toggle.textContent = collapsed ? 'Show' : 'Hide';
                localStorage.setItem('syncWidgetCollapsed', collapsed ? '1' : '0');
            }

            const initial = localStorage.getItem('syncWidgetCollapsed') === '1';
            setCollapsed(initial);

            toggle.addEventListener('click', () => setCollapsed(body.style.display !== 'none'));

            function formatTime(value) {
                if (!value) return 'n/a';
                const dt = new Date(value);
                if (Number.isNaN(dt.getTime())) return 'n/a';
                return dt.toLocaleString();
            }

            function parseDetails(details) {
                if (!details) return null;
                try {
                    return JSON.parse(details);
                } catch (e) {
                    return null;
                }
            }

            function getAddedCount(jobName, details) {
                if (!details) return 'n/a';
                if (jobName === 'inspections') return details.created ?? details.new_inspections_added ?? 0;
                if (jobName === 'violations-bulk') return details.violations_inserted ?? details.new_violations_found ?? 0;
                if (jobName === 'epa') return details.new ?? 0;
                return 'n/a';
            }

            function formatLine(label, run, jobName) {
                if (!run) return `<span class="text-gray-400">${label}: No data</span>`;
                const status = run.status || 'unknown';
                const statusColor = status === 'success' ? 'text-green-600' : status === 'failed' ? 'text-red-600' : 'text-yellow-600';
                const end = formatTime(run.finished_at);
                const details = parseDetails(run.details);
                const added = getAddedCount(jobName, details);
                return `${label}: <span class="${statusColor}">${status}</span> | ${end} | +${added}`;
            }

            function getLatestRunId(runs) {
                if (!runs || !runs.length) return 0;
                return Math.max(...runs.map(r => r.id || 0));
            }

            function renderSyncStatus(data) {
                const runs = data.runs || [];
                const latest = data.latest || {};

                // Render cron section using latest
                const cronLines = [
                    formatLine('Inspections', latest.inspections, 'inspections'),
                    formatLine('Violations', latest['violations-bulk'], 'violations-bulk'),
                    formatLine('EPA', latest.epa, 'epa'),
                ];
                cronContent.innerHTML = cronLines.map(line => `<div>${line}</div>`).join('');

                // For manual section, load from localStorage (don't overwrite)
                loadSavedManualStatus();
            }

            async function loadSyncWidget() {
                try {
                    const response = await fetch('/api/inspections/cron/status');
                    if (response.status === 401) {
                        cronContent.textContent = 'Unavailable (unauthorized)';
                        manualContent.textContent = 'Unavailable (unauthorized)';
                        return false;
                    }
                    if (!response.ok) {
                        cronContent.textContent = 'Unavailable';
                        manualContent.textContent = 'Unavailable';
                        return false;
                    }

                    const data = await response.json();
                    renderSyncStatus(data);
                    lastRunId = getLatestRunId(data.runs);
                    return true;
                } catch (e) {
                    cronContent.textContent = 'Unavailable';
                    manualContent.textContent = 'Unavailable';
                    return false;
                }
            }

            function startSyncStream() {
                if (!window.EventSource || cronEventSource) return;
                const streamUrl = lastRunId
                    ? `/api/inspections/cron/stream?last_id=${encodeURIComponent(lastRunId)}`
                    : '/api/inspections/cron/stream';
                cronEventSource = new EventSource(streamUrl);

                cronEventSource.addEventListener('cron_update', (event) => {
                    try {
                        const payload = JSON.parse(event.data || '{}');
                        if (payload.latest) {
                            renderSyncStatus({ latest: payload.latest, runs: [] });
                        }
                        if (payload.run_id) {
                            lastRunId = payload.run_id;
                        }
                    } catch (e) {
                        console.error('Error parsing sync update:', e);
                    }
                });

                cronEventSource.onerror = () => {
                    if (cronEventSource) {
                        cronEventSource.close();
                        cronEventSource = null;
                    }
                    if (!reconnectTimer) {
                        reconnectTimer = setTimeout(() => {
                            reconnectTimer = null;
                            startSyncStream();
                        }, 10000);
                    }
                };
            }

            // Expose function to update manual sync status from outside
            window.updateManualSyncStatus = function(type, status, details) {
                const statusColor = status === 'success' ? 'text-green-600' : status === 'failed' ? 'text-red-600' : 'text-yellow-600';
                const time = new Date().toLocaleString();
                manualContent.innerHTML = `<div>${type}: <span class="${statusColor}">${status}</span> | ${time} | ${details}</div>`;
                // Persist to localStorage
                const saved = JSON.parse(localStorage.getItem('manualSyncStatus') || '{}');
                saved[type] = { status, details, time };
                localStorage.setItem('manualSyncStatus', JSON.stringify(saved));
            };

            // Load saved manual sync status from localStorage
            function loadSavedManualStatus() {
                const saved = JSON.parse(localStorage.getItem('manualSyncStatus') || '{}');
                const entries = Object.entries(saved);
                if (entries.length === 0) {
                    manualContent.textContent = 'No manual syncs yet';
                    return;
                }
                manualContent.innerHTML = entries.map(([type, data]) => {
                    const statusColor = data.status === 'success' ? 'text-green-600' : data.status === 'failed' ? 'text-red-600' : 'text-yellow-600';
                    return `<div>${type}: <span class="${statusColor}">${data.status}</span> | ${data.time} | ${data.details}</div>`;
                }).join('');
            }

            loadSavedManualStatus();
            loadSyncWidget().then((ok) => {
                if (ok) startSyncStream();
            });
        })();
    </script>

</body>
</html>
"""


