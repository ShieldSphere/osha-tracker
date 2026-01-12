from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def dashboard():
    """Serve the main dashboard page."""
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OSHA Tracker Dashboard</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
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
    <nav class="bg-blue-600 text-white p-4 shadow-lg">
        <div class="container mx-auto flex justify-between items-center">
            <h1 class="text-2xl font-bold">OSHA Tracker</h1>
            <div class="flex items-center gap-4">
                <span id="sync-status" class="text-sm"></span>
                <button onclick="openCRMModal()" class="bg-purple-600 hover:bg-purple-700 px-4 py-2 rounded flex items-center gap-2">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"></path>
                    </svg>
                    CRM
                </button>
                <button onclick="openEnrichedCompaniesModal()" class="bg-green-600 hover:bg-green-700 px-4 py-2 rounded flex items-center gap-2">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"></path>
                    </svg>
                    Enriched Companies
                </button>
                <button onclick="openChartsModal()" class="bg-blue-500 hover:bg-blue-700 px-4 py-2 rounded">
                    Charts
                </button>
                <button onclick="triggerSync()" class="bg-blue-500 hover:bg-blue-700 px-4 py-2 rounded">
                    Sync Now
                </button>
            </div>
        </div>
    </nav>

    <main class="container mx-auto p-6">
        <div class="flex flex-col lg:flex-row gap-6">
            <!-- Left Sidebar - Stats Cards -->
            <div class="lg:w-64 flex-shrink-0">
                <div class="sticky top-6 space-y-4">
                    <div class="bg-white p-5 rounded-lg shadow">
                        <h3 class="text-gray-500 text-xs uppercase tracking-wider mb-1">Data Range</h3>
                        <p id="stat-date-range" class="text-sm font-medium text-gray-700">Loading...</p>
                        <p id="stat-date-span" class="text-xs text-gray-500 mt-1"></p>
                    </div>
                    <!-- New Inspections Widget -->
                    <div class="bg-gradient-to-br from-blue-50 to-cyan-50 p-5 rounded-lg shadow border-2 border-blue-200 cursor-pointer hover:shadow-lg transition-shadow" onclick="openNewInspectionsModal()">
                        <div class="flex items-center justify-between mb-2">
                            <h3 class="text-gray-700 text-xs uppercase tracking-wider font-semibold">📋 New Inspections (7d)</h3>
                        </div>
                        <p id="new-inspections-count" class="text-2xl font-bold text-blue-600">-</p>
                        <p id="new-inspections-companies" class="text-xs text-gray-600 mt-1">Loading...</p>
                    </div>
                    <!-- New Violations Widget -->
                    <div class="bg-gradient-to-br from-orange-50 to-red-50 p-5 rounded-lg shadow border-2 border-orange-200 cursor-pointer hover:shadow-lg transition-shadow" onclick="openNewViolationsModal()">
                        <div class="flex items-center justify-between mb-2">
                            <h3 class="text-gray-700 text-xs uppercase tracking-wider font-semibold">🚨 New Penalties (45d)</h3>
                        </div>
                        <p id="new-violations-count" class="text-2xl font-bold text-orange-600">-</p>
                        <p id="new-violations-companies" class="text-xs text-gray-600 mt-1">Loading...</p>
                        <p id="new-violations-penalties" class="text-xs text-gray-600"></p>
                    </div>
                    <!-- CRM Pipeline Widget -->
                    <div class="bg-gradient-to-br from-purple-50 to-indigo-50 p-5 rounded-lg shadow border-2 border-purple-200 cursor-pointer hover:shadow-lg transition-shadow" onclick="openCRMModal()">
                        <div class="flex items-center justify-between mb-2">
                            <h3 class="text-gray-700 text-xs uppercase tracking-wider font-semibold">👥 CRM Pipeline</h3>
                        </div>
                        <p id="crm-total-prospects" class="text-2xl font-bold text-purple-600">-</p>
                        <p id="crm-pipeline-value" class="text-xs text-gray-600 mt-1">Loading...</p>
                    </div>
                    <!-- Upcoming Callbacks Widget -->
                    <div class="bg-gradient-to-br from-green-50 to-emerald-50 p-5 rounded-lg shadow border-2 border-green-200 cursor-pointer hover:shadow-lg transition-shadow" onclick="openCRMModal()">
                        <div class="flex items-center justify-between mb-2">
                            <h3 class="text-gray-700 text-xs uppercase tracking-wider font-semibold">📅 Callbacks (7d)</h3>
                        </div>
                        <p id="crm-upcoming-callbacks" class="text-2xl font-bold text-green-600">-</p>
                        <p id="crm-overdue-callbacks" class="text-xs text-red-600 mt-1"></p>
                    </div>
                    <div class="bg-white p-5 rounded-lg shadow">
                        <h3 class="text-gray-500 text-xs uppercase tracking-wider mb-1">Total Inspections</h3>
                        <p id="stat-total" class="text-2xl font-bold text-blue-600">-</p>
                    </div>
                    <div class="bg-white p-5 rounded-lg shadow">
                        <h3 class="text-gray-500 text-xs uppercase tracking-wider mb-1">Total Penalties</h3>
                        <p id="stat-penalties" class="text-2xl font-bold text-red-600">-</p>
                    </div>
                    <div class="bg-white p-5 rounded-lg shadow">
                        <h3 class="text-gray-500 text-xs uppercase tracking-wider mb-1">States Covered</h3>
                        <p id="stat-states" class="text-2xl font-bold text-green-600">-</p>
                    </div>
                    <div class="bg-white p-5 rounded-lg shadow">
                        <h3 class="text-gray-500 text-xs uppercase tracking-wider mb-1">Avg Penalty</h3>
                        <p id="stat-avg" class="text-2xl font-bold text-orange-600">-</p>
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
                <div class="flex items-center gap-4">
                    <select id="contacted-filter" onchange="loadEnrichedCompanies()" class="text-sm border border-gray-300 rounded px-3 py-1">
                        <option value="">All Companies</option>
                        <option value="not_contacted">Not Contacted</option>
                        <option value="contacted">Contacted</option>
                    </select>
                    <button onclick="closeEnrichedCompaniesModal()" class="text-gray-500 hover:text-gray-700 text-2xl">&times;</button>
                </div>
            </div>
            <div class="overflow-y-auto flex-1">
                <table class="min-w-full divide-y divide-gray-200">
                    <thead class="bg-gray-50 sticky top-0">
                        <tr>
                            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Contacted</th>
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

    <!-- Charts Modal -->
    <div id="charts-modal" class="fixed inset-0 bg-black bg-opacity-50 hidden flex items-center justify-center z-50">
        <div class="bg-white rounded-lg shadow-xl max-w-4xl w-full mx-4 max-h-[90vh] overflow-y-auto">
            <div class="p-6 border-b flex justify-between items-center">
                <h2 class="text-xl font-semibold">Inspection Statistics</h2>
                <button onclick="closeChartsModal()" class="text-gray-500 hover:text-gray-700 text-2xl">&times;</button>
            </div>
            <div class="p-6">
                <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div>
                        <h3 class="text-lg font-semibold mb-4">Inspections by State</h3>
                        <canvas id="chart-states"></canvas>
                    </div>
                    <div>
                        <h3 class="text-lg font-semibold mb-4">Inspections by Type</h3>
                        <canvas id="chart-types"></canvas>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- New Inspections Modal -->
    <div id="new-inspections-modal" class="fixed inset-0 bg-black bg-opacity-50 hidden flex items-center justify-center z-50">
        <div class="bg-white rounded-lg shadow-xl max-w-5xl w-full mx-4 max-h-[90vh] flex flex-col">
            <div class="p-6 border-b flex justify-between items-center bg-gradient-to-r from-blue-50 to-cyan-50">
                <div>
                    <h2 class="text-xl font-semibold text-gray-800">📋 New Inspections (Last 7 Days)</h2>
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
                    <h2 class="text-xl font-semibold text-gray-800">🚨 New Penalties (Last 45 Days)</h2>
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

    <!-- CRM Modal -->
    <div id="crm-modal" class="fixed inset-0 bg-black bg-opacity-50 hidden flex items-center justify-center z-50">
        <div class="bg-white rounded-lg shadow-xl max-w-6xl w-full mx-4 max-h-[90vh] flex flex-col">
            <div class="p-6 border-b flex justify-between items-center bg-gradient-to-r from-purple-50 to-indigo-50">
                <div>
                    <h2 class="text-xl font-semibold text-gray-800">👥 CRM - Sales Pipeline</h2>
                    <p id="crm-modal-subtitle" class="text-sm text-gray-600 mt-1"></p>
                </div>
                <button onclick="closeCRMModal()" class="text-gray-500 hover:text-gray-700 text-2xl">&times;</button>
            </div>
            <!-- CRM Tabs -->
            <div class="border-b px-6 flex gap-4">
                <button id="crm-tab-prospects" onclick="switchCRMTab('prospects')" class="py-3 px-4 border-b-2 border-purple-600 text-purple-600 font-medium">Prospects</button>
                <button id="crm-tab-callbacks" onclick="switchCRMTab('callbacks')" class="py-3 px-4 border-b-2 border-transparent text-gray-500 hover:text-gray-700">Callbacks</button>
            </div>
            <!-- CRM Stats Bar -->
            <div class="px-6 py-3 bg-gray-50 border-b flex gap-6 text-sm">
                <div><span class="text-gray-500">New:</span> <span id="crm-stat-new" class="font-semibold text-blue-600">0</span></div>
                <div><span class="text-gray-500">Contacted:</span> <span id="crm-stat-contacted" class="font-semibold text-yellow-600">0</span></div>
                <div><span class="text-gray-500">Qualified:</span> <span id="crm-stat-qualified" class="font-semibold text-green-600">0</span></div>
                <div><span class="text-gray-500">Won:</span> <span id="crm-stat-won" class="font-semibold text-purple-600">0</span></div>
                <div><span class="text-gray-500">Lost:</span> <span id="crm-stat-lost" class="font-semibold text-red-600">0</span></div>
                <div class="ml-auto"><span class="text-gray-500">Pipeline Value:</span> <span id="crm-stat-value" class="font-semibold text-green-600">$0</span></div>
            </div>
            <!-- CRM Filter Bar -->
            <div class="px-6 py-3 border-b flex gap-4 items-center">
                <select id="crm-filter-status" onchange="loadProspects()" class="border rounded px-3 py-1.5 text-sm">
                    <option value="">All Statuses</option>
                    <option value="new_lead">New Lead</option>
                    <option value="contacted">Contacted</option>
                    <option value="qualified">Qualified</option>
                    <option value="won">Won</option>
                    <option value="lost">Lost</option>
                </select>
                <select id="crm-filter-priority" onchange="loadProspects()" class="border rounded px-3 py-1.5 text-sm">
                    <option value="">All Priorities</option>
                    <option value="high">High</option>
                    <option value="medium">Medium</option>
                    <option value="low">Low</option>
                </select>
                <input type="text" id="crm-search" placeholder="Search company..." class="border rounded px-3 py-1.5 text-sm w-48" onkeyup="debounceCRMSearch()">
            </div>
            <!-- CRM Content -->
            <div class="flex-1 overflow-auto p-6">
                <!-- Prospects Tab -->
                <div id="crm-prospects-content">
                    <table class="w-full">
                        <thead class="bg-gray-50 sticky top-0">
                            <tr>
                                <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Company</th>
                                <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Location</th>
                                <th class="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Status</th>
                                <th class="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Priority</th>
                                <th class="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Est. Value</th>
                                <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Next Action</th>
                                <th class="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Actions</th>
                            </tr>
                        </thead>
                        <tbody id="crm-prospects-list">
                            <tr><td colspan="7" class="px-4 py-8 text-center text-gray-500">Loading...</td></tr>
                        </tbody>
                    </table>
                </div>
                <!-- Callbacks Tab -->
                <div id="crm-callbacks-content" class="hidden">
                    <table class="w-full">
                        <thead class="bg-gray-50 sticky top-0">
                            <tr>
                                <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Date/Time</th>
                                <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Company</th>
                                <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Type</th>
                                <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Notes</th>
                                <th class="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Status</th>
                                <th class="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Actions</th>
                            </tr>
                        </thead>
                        <tbody id="crm-callbacks-list">
                            <tr><td colspan="6" class="px-4 py-8 text-center text-gray-500">Loading...</td></tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>

    <!-- Prospect Detail Modal -->
    <div id="prospect-detail-modal" class="fixed inset-0 bg-black bg-opacity-50 hidden flex items-center justify-center z-[60]">
        <div class="bg-white rounded-lg shadow-xl max-w-4xl w-full mx-4 max-h-[90vh] flex flex-col">
            <div class="p-6 border-b flex justify-between items-center">
                <div>
                    <h2 id="prospect-detail-title" class="text-xl font-semibold text-gray-800">Prospect Details</h2>
                    <p id="prospect-detail-subtitle" class="text-sm text-gray-600 mt-1"></p>
                </div>
                <button onclick="closeProspectDetailModal()" class="text-gray-500 hover:text-gray-700 text-2xl">&times;</button>
            </div>
            <div class="flex-1 overflow-auto p-6" id="prospect-detail-content">
                <!-- Content loaded dynamically -->
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
        let statesChart = null;
        let typesChart = null;
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
            loadSyncStatus();
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
                                View Details →
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
                `${data.count} new citations across ${data.total_companies} companies • $${data.total_penalties.toLocaleString(undefined, {maximumFractionDigits: 0})} in penalties`;

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
                                View Details →
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
                                    ${hasMultipleInspections ? `<span class="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium bg-orange-100 text-orange-800" title="Multiple inspections for this company">×${companyNameCounts[companyName]}</span>` : ''}
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
            const dotMatch = standard.match(/^(\d{4})\.(\d+)/);
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
                            <div>
                                <p class="text-xs text-gray-500 uppercase tracking-wider">Enrichment</p>
                                <p class="mt-1 flex items-center gap-2">
                                    <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                                        inspection.enrichment_status === 'completed' ? 'bg-green-100 text-green-800' :
                                        inspection.enrichment_status === 'failed' ? 'bg-red-100 text-red-800' :
                                        inspection.enrichment_status === 'in_progress' ? 'bg-yellow-100 text-yellow-800' :
                                        'bg-gray-100 text-gray-800'
                                    }">
                                        ${inspection.enrichment_status || 'pending'}
                                    </span>
                                    ${inspection.enrichment_status !== 'completed' ? `
                                        <button onclick="enrichInspection(${inspection.id})"
                                            id="enrich-btn-${inspection.id}"
                                            class="inline-flex items-center px-2 py-1 text-xs font-medium rounded bg-blue-100 text-blue-700 hover:bg-blue-200">
                                            <svg class="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path>
                                            </svg>
                                            Enrich
                                        </button>
                                    ` : ''}
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

                // Load company data if already enriched
                if (inspection.enrichment_status === 'completed') {
                    loadCompanyData(inspection.id);
                }

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
                    const prospect = await response.json();
                    // Already a prospect - show "View in CRM" button
                    container.innerHTML = `
                        <div class="flex items-center gap-2">
                            <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${getStatusColor(prospect.status)}">
                                ${formatStatus(prospect.status)}
                            </span>
                            <button onclick="openProspectDetail(${prospect.id})"
                                class="inline-flex items-center px-3 py-1.5 text-sm font-medium rounded-md bg-purple-600 text-white hover:bg-purple-700 transition-colors">
                                <svg class="w-4 h-4 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path>
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"></path>
                                </svg>
                                View in CRM
                            </button>
                        </div>
                    `;
                }
                // If 404, keep the "Add to CRM" button as is
            } catch (e) {
                console.error('Error checking CRM status:', e);
            }
        }

        function closeModal() {
            document.getElementById('modal').classList.add('hidden');
        }

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
                const result = await fetch(`${API_BASE}/${inspectionId}/enrich`, { method: 'POST' }).then(r => r.json());

                if (result.success) {
                    // Show success and display company data
                    if (btn) {
                        btn.classList.remove('bg-blue-100', 'text-blue-700', 'hover:bg-blue-200');
                        btn.classList.add('bg-green-100', 'text-green-700');
                        btn.innerHTML = `
                            <svg class="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
                            </svg>
                            Enriched
                        `;
                    }
                    displayCompanyData(inspectionId, result);
                } else {
                    // Show error
                    if (btn) {
                        btn.classList.remove('bg-blue-100', 'text-blue-700', 'hover:bg-blue-200');
                        btn.classList.add('bg-red-100', 'text-red-700');
                        btn.disabled = false;
                        btn.innerHTML = `
                            <svg class="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                            </svg>
                            Failed - Retry
                        `;
                        btn.onclick = () => {
                            btn.classList.remove('bg-red-100', 'text-red-700');
                            btn.classList.add('bg-blue-100', 'text-blue-700', 'hover:bg-blue-200');
                            enrichInspection(inspectionId);
                        };
                    }
                    console.error('Enrichment failed:', result.error);
                }
            } catch (e) {
                console.error('Enrichment error:', e);
                if (btn) {
                    btn.disabled = false;
                    btn.innerHTML = 'Error - Retry';
                }
            }
        }

        function displayCompanyData(inspectionId, result) {
            const section = document.getElementById(`company-data-section-${inspectionId}`);
            if (!section || !result.data) return;

            const data = result.data;
            const websiteUrl = result.website_url;

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

            section.innerHTML = `
                <div class="border-t border-gray-200">
                    <!-- Header -->
                    <div class="px-6 py-4 bg-green-50 border-b border-gray-200">
                        <div class="flex items-center justify-between">
                            <h3 class="text-sm font-semibold text-gray-900 uppercase tracking-wider">
                                Company Information (Enriched)
                            </h3>
                            <div class="flex items-center gap-3">
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
                        </div>
                    </div>

                    <div class="px-6 py-4 space-y-6">
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
                    </div>
                </div>
            `;
        }

        async function loadCompanyData(inspectionId) {
            try {
                const company = await fetch(`${API_BASE}/${inspectionId}/company`).then(r => r.json());
                if (company) {
                    displayCompanyData(inspectionId, { data: company, website_url: company.website });
                }
            } catch (e) {
                console.error('Error loading company data:', e);
            }
        }

        async function loadSyncStatus() {
            try {
                const status = await fetch(`${API_BASE}/sync/status`).then(r => r.json());
                if (status.last_sync) {
                    const syncDate = new Date(status.last_sync);
                    const options = {
                        year: 'numeric', month: 'short', day: 'numeric',
                        hour: '2-digit', minute: '2-digit', timeZoneName: 'short'
                    };
                    document.getElementById('sync-status').textContent =
                        `Last sync: ${syncDate.toLocaleString(undefined, options)}`;
                } else {
                    document.getElementById('sync-status').textContent = 'Never synced';
                }
            } catch (e) {
                document.getElementById('sync-status').textContent = 'Status unknown';
            }
        }

        async function triggerSync() {
            if (!confirm('Start syncing OSHA inspection data? This may take a few minutes.')) return;

            try {
                document.getElementById('sync-status').textContent = 'Syncing...';
                const result = await fetch(`${API_BASE}/sync?days_back=30`, { method: 'POST' }).then(r => r.json());
                alert(`Sync complete!\\n\\nFetched: ${result.fetched}\\nCreated: ${result.created}\\nUpdated: ${result.updated}\\nErrors: ${result.errors}`);
                loadInspections();
                loadSyncStatus();
            } catch (e) {
                alert('Sync failed: ' + e.message);
            }
        }

        function escapeHtml(text) {
            if (!text) return '';
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        // Enriched Companies modal functions
        async function openEnrichedCompaniesModal() {
            document.getElementById('enriched-companies-modal').classList.remove('hidden');
            await loadEnrichedCompanies();
        }

        function closeEnrichedCompaniesModal() {
            document.getElementById('enriched-companies-modal').classList.add('hidden');
        }

        async function loadEnrichedCompanies() {
            const filter = document.getElementById('contacted-filter').value;
            const url = filter ? `${API_BASE}/companies/enriched?contacted_filter=${filter}` : `${API_BASE}/companies/enriched`;

            try {
                const data = await fetch(url).then(r => r.json());
                const list = document.getElementById('enriched-companies-list');
                const noData = document.getElementById('no-enriched-companies');
                const countEl = document.getElementById('enriched-count');

                countEl.textContent = `(${data.total} companies)`;

                if (data.items.length === 0) {
                    list.innerHTML = '';
                    noData.classList.remove('hidden');
                    return;
                }

                noData.classList.add('hidden');
                list.innerHTML = data.items.map(company => `
                    <tr class="hover:bg-gray-50 ${company.contacted ? 'bg-green-50' : ''}">
                        <td class="px-4 py-3">
                            <input type="checkbox"
                                ${company.contacted ? 'checked' : ''}
                                onchange="toggleContacted(${company.id}, this.checked)"
                                class="w-4 h-4 text-green-600 rounded border-gray-300 focus:ring-green-500 cursor-pointer">
                        </td>
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
                            <button onclick="viewCompanyDetail(${company.id})" class="text-blue-600 hover:text-blue-800 text-sm font-medium">
                                View Details
                            </button>
                        </td>
                    </tr>
                `).join('');
            } catch (e) {
                console.error('Error loading enriched companies:', e);
            }
        }

        async function toggleContacted(companyId, contacted) {
            try {
                await fetch(`${API_BASE}/companies/${companyId}/contacted`, {
                    method: 'PATCH',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ contacted })
                });
                // Reload the list to update styling
                await loadEnrichedCompanies();
            } catch (e) {
                console.error('Error updating contacted status:', e);
            }
        }

        async function viewCompanyDetail(companyId) {
            try {
                const company = await fetch(`${API_BASE}/companies/${companyId}`).then(r => r.json());
                const modal = document.getElementById('company-detail-modal');
                const content = document.getElementById('company-detail-content');

                // Reuse the displayCompanyData format but in a standalone modal
                const data = company;
                const websiteUrl = company.website;

                // Parse services if it's a JSON string
                let services = data.services;
                if (typeof services === 'string') {
                    try { services = JSON.parse(services); } catch(e) { services = null; }
                }

                // Parse other_locations if it's a JSON string
                let otherLocations = data.other_addresses;
                if (typeof otherLocations === 'string') {
                    try { otherLocations = JSON.parse(otherLocations); } catch(e) { otherLocations = null; }
                }

                const contacts = data.contacts || [];

                content.innerHTML = `
                    <div class="p-6 border-b flex justify-between items-center bg-green-50">
                        <div>
                            <h2 class="text-xl font-semibold">${escapeHtml(company.name)}</h2>
                            <p class="text-sm text-gray-500">${[company.city, company.state].filter(Boolean).join(', ')}</p>
                        </div>
                        <div class="flex items-center gap-4">
                            <label class="flex items-center gap-2 cursor-pointer">
                                <input type="checkbox"
                                    id="detail-contacted-checkbox"
                                    ${company.contacted ? 'checked' : ''}
                                    onchange="toggleContactedFromDetail(${company.id}, this.checked)"
                                    class="w-5 h-5 text-green-600 rounded border-gray-300 focus:ring-green-500">
                                <span class="text-sm font-medium ${company.contacted ? 'text-green-700' : 'text-gray-700'}">
                                    ${company.contacted ? 'Contacted' : 'Not Contacted'}
                                </span>
                            </label>
                            <button onclick="closeCompanyDetailModal()" class="text-gray-500 hover:text-gray-700 text-2xl">&times;</button>
                        </div>
                    </div>
                    <div id="company-detail-body" class="p-6">
                        <!-- Will be filled by displayCompanyData-style content -->
                    </div>
                `;

                // Now populate the body using similar logic to displayCompanyData
                const bodyEl = document.getElementById('company-detail-body');
                bodyEl.innerHTML = buildCompanyDetailHTML(data, websiteUrl, services, otherLocations, contacts);

                modal.classList.remove('hidden');
            } catch (e) {
                console.error('Error loading company detail:', e);
            }
        }

        function buildCompanyDetailHTML(data, websiteUrl, services, otherLocations, contacts) {
            const social = data;
            return `
                <!-- Social Links -->
                <div class="flex items-center gap-3 mb-6">
                    ${social.linkedin_url ? `<a href="${social.linkedin_url}" target="_blank" class="text-blue-700 hover:text-blue-900" title="LinkedIn"><svg class="w-6 h-6" fill="currentColor" viewBox="0 0 24 24"><path d="M19 0h-14c-2.761 0-5 2.239-5 5v14c0 2.761 2.239 5 5 5h14c2.762 0 5-2.239 5-5v-14c0-2.761-2.238-5-5-5zm-11 19h-3v-11h3v11zm-1.5-12.268c-.966 0-1.75-.79-1.75-1.764s.784-1.764 1.75-1.764 1.75.79 1.75 1.764-.783 1.764-1.75 1.764zm13.5 12.268h-3v-5.604c0-3.368-4-3.113-4 0v5.604h-3v-11h3v1.765c1.396-2.586 7-2.777 7 2.476v6.759z"/></svg></a>` : ''}
                    ${social.facebook_url ? `<a href="${social.facebook_url}" target="_blank" class="text-blue-600 hover:text-blue-800" title="Facebook"><svg class="w-6 h-6" fill="currentColor" viewBox="0 0 24 24"><path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/></svg></a>` : ''}
                    ${social.twitter_url ? `<a href="${social.twitter_url}" target="_blank" class="text-gray-800 hover:text-black" title="Twitter/X"><svg class="w-6 h-6" fill="currentColor" viewBox="0 0 24 24"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg></a>` : ''}
                    ${social.instagram_url ? `<a href="${social.instagram_url}" target="_blank" class="text-pink-600 hover:text-pink-800" title="Instagram"><svg class="w-6 h-6" fill="currentColor" viewBox="0 0 24 24"><path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zm0-2.163c-3.259 0-3.667.014-4.947.072-4.358.2-6.78 2.618-6.98 6.98-.059 1.281-.073 1.689-.073 4.948 0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98 1.281.058 1.689.072 4.948.072 3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98-1.281-.059-1.69-.073-4.949-.073zm0 5.838c-3.403 0-6.162 2.759-6.162 6.162s2.759 6.163 6.162 6.163 6.162-2.759 6.162-6.163c0-3.403-2.759-6.162-6.162-6.162zm0 10.162c-2.209 0-4-1.79-4-4 0-2.209 1.791-4 4-4s4 1.791 4 4c0 2.21-1.791 4-4 4zm6.406-11.845c-.796 0-1.441.645-1.441 1.44s.645 1.44 1.441 1.44c.795 0 1.439-.645 1.439-1.44s-.644-1.44-1.439-1.44z"/></svg></a>` : ''}
                    ${websiteUrl ? `<a href="${websiteUrl}" target="_blank" class="text-blue-600 hover:text-blue-800 text-sm flex items-center gap-1 ml-2 px-3 py-1 bg-blue-50 rounded"><svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"></path></svg>Website</a>` : ''}
                </div>

                <!-- Basic Info -->
                <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                    ${data.industry ? `<div><p class="text-xs text-gray-500 uppercase">Industry</p><p class="text-sm font-medium">${escapeHtml(data.industry)}</p></div>` : ''}
                    ${data.sub_industry ? `<div><p class="text-xs text-gray-500 uppercase">Sub-Industry</p><p class="text-sm font-medium">${escapeHtml(data.sub_industry)}</p></div>` : ''}
                    ${data.employee_range || data.employee_count ? `<div><p class="text-xs text-gray-500 uppercase">Employees</p><p class="text-sm font-medium">${escapeHtml(String(data.employee_range || data.employee_count))}</p></div>` : ''}
                    ${data.year_founded ? `<div><p class="text-xs text-gray-500 uppercase">Founded</p><p class="text-sm font-medium">${data.year_founded} (${new Date().getFullYear() - data.year_founded} years)</p></div>` : ''}
                    ${data.business_type ? `<div><p class="text-xs text-gray-500 uppercase">Business Type</p><p class="text-sm font-medium">${escapeHtml(data.business_type)}</p></div>` : ''}
                    ${data.registration_number ? `<div><p class="text-xs text-gray-500 uppercase">Registration #</p><p class="text-sm font-medium">${escapeHtml(data.registration_number)}</p></div>` : ''}
                </div>

                <!-- Contact Info -->
                ${data.phone || data.email ? `
                    <div class="border-t pt-4 mb-6">
                        <p class="text-xs text-gray-500 uppercase mb-2">Contact Information</p>
                        <div class="flex flex-wrap gap-6">
                            ${data.phone ? `<a href="tel:${data.phone}" class="text-blue-600 hover:text-blue-800 flex items-center gap-2"><svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z"></path></svg>${escapeHtml(data.phone)}</a>` : ''}
                            ${data.email ? `<a href="mailto:${data.email}" class="text-blue-600 hover:text-blue-800 flex items-center gap-2"><svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"></path></svg>${escapeHtml(data.email)}</a>` : ''}
                        </div>
                    </div>
                ` : ''}

                <!-- Address -->
                ${data.address || data.city ? `
                    <div class="border-t pt-4 mb-6">
                        <p class="text-xs text-gray-500 uppercase mb-2">Headquarters</p>
                        <p class="text-sm">${data.address ? escapeHtml(data.address) + '<br>' : ''}${[data.city, data.state, data.postal_code].filter(Boolean).map(escapeHtml).join(', ')}</p>
                    </div>
                ` : ''}

                <!-- Description -->
                ${data.description ? `
                    <div class="border-t pt-4 mb-6">
                        <p class="text-xs text-gray-500 uppercase mb-2">Description</p>
                        <p class="text-sm text-gray-700">${escapeHtml(data.description)}</p>
                    </div>
                ` : ''}

                <!-- Services -->
                ${services && services.length > 0 ? `
                    <div class="border-t pt-4 mb-6">
                        <p class="text-xs text-gray-500 uppercase mb-2">Services</p>
                        <div class="flex flex-wrap gap-1">${services.map(s => `<span class="px-2 py-0.5 rounded text-xs bg-gray-100 text-gray-800">${escapeHtml(s)}</span>`).join('')}</div>
                    </div>
                ` : ''}

                <!-- Key Personnel -->
                ${contacts && contacts.length > 0 ? `
                    <div class="border-t pt-4 mb-6">
                        <p class="text-xs text-gray-500 uppercase mb-3">Key Personnel</p>
                        <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
                            ${contacts.map(p => `
                                <div class="bg-gray-50 rounded-lg p-3 border border-gray-100">
                                    <div class="flex items-start justify-between">
                                        <div>
                                            <p class="text-sm font-semibold">${escapeHtml(p.full_name || [p.first_name, p.last_name].filter(Boolean).join(' '))}</p>
                                            ${p.title ? `<p class="text-xs text-gray-500">${escapeHtml(p.title)}</p>` : ''}
                                        </div>
                                        ${p.linkedin_url ? `<a href="${p.linkedin_url}" target="_blank" class="text-blue-700 hover:text-blue-900"><svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M19 0h-14c-2.761 0-5 2.239-5 5v14c0 2.761 2.239 5 5 5h14c2.762 0 5-2.239 5-5v-14c0-2.761-2.238-5-5-5zm-11 19h-3v-11h3v11zm-1.5-12.268c-.966 0-1.75-.79-1.75-1.764s.784-1.764 1.75-1.764 1.75.79 1.75 1.764-.783 1.764-1.75 1.764zm13.5 12.268h-3v-5.604c0-3.368-4-3.113-4 0v5.604h-3v-11h3v1.765c1.396-2.586 7-2.777 7 2.476v6.759z"/></svg></a>` : ''}
                                    </div>
                                    ${(p.email || p.phone) ? `
                                        <div class="mt-2 flex flex-wrap gap-3 text-xs">
                                            ${p.email ? `<a href="mailto:${escapeHtml(p.email)}" class="text-blue-600 hover:text-blue-800">${escapeHtml(p.email)}</a>` : ''}
                                            ${p.phone ? `<a href="tel:${escapeHtml(p.phone)}" class="text-blue-600 hover:text-blue-800">${escapeHtml(p.phone)}</a>` : ''}
                                        </div>
                                    ` : ''}
                                </div>
                            `).join('')}
                        </div>
                    </div>
                ` : ''}
            `;
        }

        async function toggleContactedFromDetail(companyId, contacted) {
            await toggleContacted(companyId, contacted);
            // Update the label text
            const label = document.querySelector('#detail-contacted-checkbox').parentElement.querySelector('span');
            if (label) {
                label.textContent = contacted ? 'Contacted' : 'Not Contacted';
                label.className = `text-sm font-medium ${contacted ? 'text-green-700' : 'text-gray-700'}`;
            }
        }

        function closeCompanyDetailModal() {
            document.getElementById('company-detail-modal').classList.add('hidden');
        }

        // Charts modal functions
        async function openChartsModal() {
            document.getElementById('charts-modal').classList.remove('hidden');
            await loadChartsData();
        }

        function closeChartsModal() {
            document.getElementById('charts-modal').classList.add('hidden');
        }

        async function loadChartsData() {
            try {
                const params = getFilterParams();
                const queryString = new URLSearchParams(params).toString();
                const stats = await fetch(`${API_BASE}/stats?${queryString}`).then(r => r.json());

                // States chart
                const statesCtx = document.getElementById('chart-states').getContext('2d');
                if (statesChart) statesChart.destroy();
                statesChart = new Chart(statesCtx, {
                    type: 'bar',
                    data: {
                        labels: Object.keys(stats.inspections_by_state),
                        datasets: [{
                            label: 'Inspections',
                            data: Object.values(stats.inspections_by_state),
                            backgroundColor: 'rgba(59, 130, 246, 0.8)',
                        }]
                    },
                    options: {
                        responsive: true,
                        plugins: { legend: { display: false } }
                    }
                });

                // Types chart
                const typesCtx = document.getElementById('chart-types').getContext('2d');
                if (typesChart) typesChart.destroy();
                const typeLabels = Object.keys(stats.inspections_by_type).map(t => getInspectionTypeWithCode(t));
                typesChart = new Chart(typesCtx, {
                    type: 'doughnut',
                    data: {
                        labels: typeLabels,
                        datasets: [{
                            data: Object.values(stats.inspections_by_type),
                            backgroundColor: [
                                'rgba(59, 130, 246, 0.8)',
                                'rgba(16, 185, 129, 0.8)',
                                'rgba(245, 158, 11, 0.8)',
                                'rgba(239, 68, 68, 0.8)',
                                'rgba(139, 92, 246, 0.8)',
                                'rgba(236, 72, 153, 0.8)',
                                'rgba(34, 197, 94, 0.8)',
                                'rgba(251, 146, 60, 0.8)',
                                'rgba(99, 102, 241, 0.8)',
                                'rgba(14, 165, 233, 0.8)',
                            ],
                        }]
                    },
                    options: { responsive: true }
                });
            } catch (e) {
                console.error('Error loading charts:', e);
            }
        }

        // Close modal on escape or outside click
        document.addEventListener('keydown', e => {
            if (e.key === 'Escape') {
                closeModal();
                closeChartsModal();
                closeCRMModal();
                closeProspectDetailModal();
            }
        });
        document.getElementById('modal').addEventListener('click', e => {
            if (e.target.id === 'modal') closeModal();
        });
        document.getElementById('charts-modal').addEventListener('click', e => {
            if (e.target.id === 'charts-modal') closeChartsModal();
        });
        document.getElementById('crm-modal').addEventListener('click', e => {
            if (e.target.id === 'crm-modal') closeCRMModal();
        });
        document.getElementById('prospect-detail-modal').addEventListener('click', e => {
            if (e.target.id === 'prospect-detail-modal') closeProspectDetailModal();
        });

        // =============================================================================
        // CRM FUNCTIONS
        // =============================================================================

        let crmSearchTimeout = null;
        let currentProspectId = null;

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

                // Update modal stats
                document.getElementById('crm-stat-new').textContent = stats.by_status?.new_lead || 0;
                document.getElementById('crm-stat-contacted').textContent = stats.by_status?.contacted || 0;
                document.getElementById('crm-stat-qualified').textContent = stats.by_status?.qualified || 0;
                document.getElementById('crm-stat-won').textContent = stats.by_status?.won || 0;
                document.getElementById('crm-stat-lost').textContent = stats.by_status?.lost || 0;
                document.getElementById('crm-stat-value').textContent = `$${(stats.total_pipeline_value || 0).toLocaleString()}`;

                document.getElementById('crm-modal-subtitle').textContent =
                    `${stats.total_prospects} prospects | ${stats.upcoming_callbacks} upcoming callbacks | Won this month: $${(stats.won_value_this_month || 0).toLocaleString()}`;
            } catch (e) {
                console.error('Error loading CRM stats:', e);
            }
        }

        async function openCRMModal() {
            document.getElementById('crm-modal').classList.remove('hidden');
            loadCRMStats();
            loadProspects();
        }

        function closeCRMModal() {
            document.getElementById('crm-modal').classList.add('hidden');
        }

        function switchCRMTab(tab) {
            // Update tab styles
            document.getElementById('crm-tab-prospects').classList.remove('border-purple-600', 'text-purple-600');
            document.getElementById('crm-tab-prospects').classList.add('border-transparent', 'text-gray-500');
            document.getElementById('crm-tab-callbacks').classList.remove('border-purple-600', 'text-purple-600');
            document.getElementById('crm-tab-callbacks').classList.add('border-transparent', 'text-gray-500');

            document.getElementById(`crm-tab-${tab}`).classList.remove('border-transparent', 'text-gray-500');
            document.getElementById(`crm-tab-${tab}`).classList.add('border-purple-600', 'text-purple-600');

            // Show/hide content
            document.getElementById('crm-prospects-content').classList.add('hidden');
            document.getElementById('crm-callbacks-content').classList.add('hidden');
            document.getElementById(`crm-${tab}-content`).classList.remove('hidden');

            if (tab === 'callbacks') {
                loadCallbacks();
            } else {
                loadProspects();
            }
        }

        function debounceCRMSearch() {
            clearTimeout(crmSearchTimeout);
            crmSearchTimeout = setTimeout(loadProspects, 300);
        }

        async function loadProspects() {
            const status = document.getElementById('crm-filter-status').value;
            const priority = document.getElementById('crm-filter-priority').value;
            const search = document.getElementById('crm-search').value;

            let url = `${CRM_API}/prospects?page_size=100`;
            if (status) url += `&status=${status}`;
            if (priority) url += `&priority=${priority}`;
            if (search) url += `&search=${encodeURIComponent(search)}`;

            try {
                const response = await fetch(url);
                const data = await response.json();

                const tbody = document.getElementById('crm-prospects-list');
                if (!data.items || data.items.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="7" class="px-4 py-8 text-center text-gray-500">No prospects found. Add prospects from inspection details.</td></tr>';
                    return;
                }

                tbody.innerHTML = data.items.map(p => `
                    <tr class="hover:bg-gray-50 cursor-pointer" onclick="openProspectDetail(${p.id})">
                        <td class="px-4 py-3">
                            <div class="font-medium text-gray-900">${p.estab_name || 'Unknown'}</div>
                            <div class="text-xs text-gray-500">${p.activity_nr || ''}</div>
                        </td>
                        <td class="px-4 py-3 text-sm text-gray-600">
                            ${p.site_city || ''}${p.site_city && p.site_state ? ', ' : ''}${p.site_state || ''}
                        </td>
                        <td class="px-4 py-3 text-center">
                            <span class="px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(p.status)}">
                                ${formatStatus(p.status)}
                            </span>
                        </td>
                        <td class="px-4 py-3 text-center">
                            ${p.priority ? `<span class="px-2 py-1 rounded text-xs ${getPriorityColor(p.priority)}">${p.priority}</span>` : '-'}
                        </td>
                        <td class="px-4 py-3 text-right text-sm">
                            ${p.estimated_value ? '$' + p.estimated_value.toLocaleString() : '-'}
                        </td>
                        <td class="px-4 py-3 text-sm">
                            <div class="text-gray-900">${p.next_action || '-'}</div>
                            ${p.next_action_date ? `<div class="text-xs text-gray-500">${new Date(p.next_action_date).toLocaleDateString()}</div>` : ''}
                        </td>
                        <td class="px-4 py-3 text-center">
                            <button onclick="event.stopPropagation(); openProspectDetail(${p.id})" class="text-blue-600 hover:text-blue-800 text-sm">View</button>
                        </td>
                    </tr>
                `).join('');
            } catch (e) {
                console.error('Error loading prospects:', e);
                document.getElementById('crm-prospects-list').innerHTML =
                    '<tr><td colspan="7" class="px-4 py-8 text-center text-red-500">Error loading prospects</td></tr>';
            }
        }

        async function loadCallbacks() {
            try {
                const response = await fetch(`${CRM_API}/callbacks?status=pending`);
                const callbacks = await response.json();

                const tbody = document.getElementById('crm-callbacks-list');
                if (!callbacks || callbacks.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="6" class="px-4 py-8 text-center text-gray-500">No pending callbacks</td></tr>';
                    return;
                }

                tbody.innerHTML = callbacks.map(c => {
                    const callbackDate = new Date(c.callback_date);
                    const isOverdue = callbackDate < new Date();
                    return `
                        <tr class="hover:bg-gray-50 ${isOverdue ? 'bg-red-50' : ''}">
                            <td class="px-4 py-3">
                                <div class="font-medium ${isOverdue ? 'text-red-600' : 'text-gray-900'}">${callbackDate.toLocaleDateString()}</div>
                                <div class="text-xs text-gray-500">${callbackDate.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</div>
                            </td>
                            <td class="px-4 py-3 text-sm text-gray-900">${c.estab_name || 'Unknown'}</td>
                            <td class="px-4 py-3 text-sm text-gray-600">${c.callback_type || '-'}</td>
                            <td class="px-4 py-3 text-sm text-gray-600">${c.notes || '-'}</td>
                            <td class="px-4 py-3 text-center">
                                <span class="px-2 py-1 rounded-full text-xs font-medium ${isOverdue ? 'bg-red-100 text-red-800' : 'bg-yellow-100 text-yellow-800'}">
                                    ${isOverdue ? 'Overdue' : 'Pending'}
                                </span>
                            </td>
                            <td class="px-4 py-3 text-center space-x-2">
                                <button onclick="completeCallback(${c.id})" class="text-green-600 hover:text-green-800 text-sm">Complete</button>
                                <button onclick="openProspectDetail(${c.prospect_id})" class="text-blue-600 hover:text-blue-800 text-sm">View</button>
                            </td>
                        </tr>
                    `;
                }).join('');
            } catch (e) {
                console.error('Error loading callbacks:', e);
            }
        }

        async function completeCallback(callbackId) {
            try {
                await fetch(`${CRM_API}/callbacks/${callbackId}`, {
                    method: 'PATCH',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ status: 'completed' })
                });
                loadCallbacks();
                loadCRMStats();
            } catch (e) {
                console.error('Error completing callback:', e);
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

        function getPriorityColor(priority) {
            const colors = {
                'high': 'bg-red-100 text-red-800',
                'medium': 'bg-yellow-100 text-yellow-800',
                'low': 'bg-gray-100 text-gray-800'
            };
            return colors[priority] || '';
        }

        async function openProspectDetail(prospectId) {
            currentProspectId = prospectId;
            document.getElementById('prospect-detail-modal').classList.remove('hidden');

            try {
                const response = await fetch(`${CRM_API}/prospects/${prospectId}`);
                const prospect = await response.json();

                document.getElementById('prospect-detail-title').textContent = prospect.estab_name || 'Prospect Details';
                document.getElementById('prospect-detail-subtitle').textContent =
                    `${prospect.site_city || ''}${prospect.site_city && prospect.site_state ? ', ' : ''}${prospect.site_state || ''} | ${prospect.activity_nr || ''}`;

                document.getElementById('prospect-detail-content').innerHTML = `
                    <div class="grid grid-cols-2 gap-6">
                        <!-- Left: Status & Info -->
                        <div class="space-y-4">
                            <div class="bg-gray-50 p-4 rounded-lg">
                                <h4 class="font-medium text-gray-700 mb-3">Status & Priority</h4>
                                <div class="grid grid-cols-2 gap-4">
                                    <div>
                                        <label class="block text-xs text-gray-500 mb-1">Status</label>
                                        <select id="prospect-status" class="w-full border rounded px-2 py-1.5 text-sm" onchange="updateProspect()">
                                            <option value="new_lead" ${prospect.status === 'new_lead' ? 'selected' : ''}>New Lead</option>
                                            <option value="contacted" ${prospect.status === 'contacted' ? 'selected' : ''}>Contacted</option>
                                            <option value="qualified" ${prospect.status === 'qualified' ? 'selected' : ''}>Qualified</option>
                                            <option value="won" ${prospect.status === 'won' ? 'selected' : ''}>Won</option>
                                            <option value="lost" ${prospect.status === 'lost' ? 'selected' : ''}>Lost</option>
                                        </select>
                                    </div>
                                    <div>
                                        <label class="block text-xs text-gray-500 mb-1">Priority</label>
                                        <select id="prospect-priority" class="w-full border rounded px-2 py-1.5 text-sm" onchange="updateProspect()">
                                            <option value="">None</option>
                                            <option value="high" ${prospect.priority === 'high' ? 'selected' : ''}>High</option>
                                            <option value="medium" ${prospect.priority === 'medium' ? 'selected' : ''}>Medium</option>
                                            <option value="low" ${prospect.priority === 'low' ? 'selected' : ''}>Low</option>
                                        </select>
                                    </div>
                                </div>
                                <div class="mt-3">
                                    <label class="block text-xs text-gray-500 mb-1">Estimated Value ($)</label>
                                    <input type="number" id="prospect-value" value="${prospect.estimated_value || ''}" class="w-full border rounded px-2 py-1.5 text-sm" onchange="updateProspect()">
                                </div>
                            </div>

                            <div class="bg-gray-50 p-4 rounded-lg">
                                <h4 class="font-medium text-gray-700 mb-3">Next Action</h4>
                                <input type="text" id="prospect-next-action" value="${prospect.next_action || ''}" placeholder="What's the next step?" class="w-full border rounded px-2 py-1.5 text-sm mb-2" onchange="updateProspect()">
                                <input type="date" id="prospect-next-date" value="${prospect.next_action_date || ''}" class="w-full border rounded px-2 py-1.5 text-sm" onchange="updateProspect()">
                            </div>

                            <div class="bg-gray-50 p-4 rounded-lg">
                                <h4 class="font-medium text-gray-700 mb-3">Notes</h4>
                                <textarea id="prospect-notes" rows="3" class="w-full border rounded px-2 py-1.5 text-sm" onchange="updateProspect()">${prospect.notes || ''}</textarea>
                            </div>

                            <div class="bg-gray-50 p-4 rounded-lg">
                                <h4 class="font-medium text-gray-700 mb-3">Schedule Callback</h4>
                                <div class="grid grid-cols-2 gap-2">
                                    <input type="datetime-local" id="new-callback-date" class="border rounded px-2 py-1.5 text-sm">
                                    <select id="new-callback-type" class="border rounded px-2 py-1.5 text-sm">
                                        <option value="call">Call</option>
                                        <option value="email">Email</option>
                                        <option value="meeting">Meeting</option>
                                    </select>
                                </div>
                                <input type="text" id="new-callback-notes" placeholder="Callback notes..." class="w-full border rounded px-2 py-1.5 text-sm mt-2">
                                <button onclick="scheduleCallback()" class="mt-2 bg-green-600 text-white px-3 py-1.5 rounded text-sm hover:bg-green-700">Schedule</button>
                            </div>
                        </div>

                        <!-- Right: Activity Log -->
                        <div>
                            <div class="bg-gray-50 p-4 rounded-lg mb-4">
                                <h4 class="font-medium text-gray-700 mb-3">Log Activity</h4>
                                <div class="grid grid-cols-2 gap-2 mb-2">
                                    <select id="new-activity-type" class="border rounded px-2 py-1.5 text-sm">
                                        <option value="call">Call</option>
                                        <option value="email">Email</option>
                                        <option value="meeting">Meeting</option>
                                        <option value="note">Note</option>
                                        <option value="task">Task</option>
                                    </select>
                                    <input type="text" id="new-activity-subject" placeholder="Subject" class="border rounded px-2 py-1.5 text-sm">
                                </div>
                                <textarea id="new-activity-description" rows="2" placeholder="Description..." class="w-full border rounded px-2 py-1.5 text-sm mb-2"></textarea>
                                <input type="text" id="new-activity-outcome" placeholder="Outcome (e.g., Left voicemail)" class="w-full border rounded px-2 py-1.5 text-sm mb-2">
                                <button onclick="logActivity()" class="bg-blue-600 text-white px-3 py-1.5 rounded text-sm hover:bg-blue-700">Log Activity</button>
                            </div>

                            <h4 class="font-medium text-gray-700 mb-3">Activity History</h4>
                            <div id="activity-list" class="space-y-2 max-h-80 overflow-auto">
                                ${prospect.activities && prospect.activities.length > 0 ? prospect.activities.map(a => `
                                    <div class="bg-white border rounded p-3">
                                        <div class="flex justify-between items-start">
                                            <span class="px-2 py-0.5 rounded text-xs ${getActivityTypeColor(a.activity_type)}">${a.activity_type}</span>
                                            <span class="text-xs text-gray-500">${new Date(a.activity_date).toLocaleString()}</span>
                                        </div>
                                        ${a.subject ? `<div class="font-medium text-sm mt-1">${a.subject}</div>` : ''}
                                        ${a.description ? `<div class="text-sm text-gray-600 mt-1">${a.description}</div>` : ''}
                                        ${a.outcome ? `<div class="text-sm text-green-600 mt-1">→ ${a.outcome}</div>` : ''}
                                    </div>
                                `).join('') : '<div class="text-gray-500 text-sm">No activities yet</div>'}
                            </div>
                        </div>
                    </div>
                `;
            } catch (e) {
                console.error('Error loading prospect:', e);
                document.getElementById('prospect-detail-content').innerHTML =
                    '<div class="text-red-500">Error loading prospect details</div>';
            }
        }

        function closeProspectDetailModal() {
            document.getElementById('prospect-detail-modal').classList.add('hidden');
            currentProspectId = null;
        }

        function getActivityTypeColor(type) {
            const colors = {
                'call': 'bg-blue-100 text-blue-800',
                'email': 'bg-green-100 text-green-800',
                'meeting': 'bg-purple-100 text-purple-800',
                'note': 'bg-gray-100 text-gray-800',
                'task': 'bg-yellow-100 text-yellow-800'
            };
            return colors[type] || 'bg-gray-100 text-gray-800';
        }

        async function updateProspect() {
            if (!currentProspectId) return;

            const data = {
                status: document.getElementById('prospect-status').value,
                priority: document.getElementById('prospect-priority').value || null,
                estimated_value: parseFloat(document.getElementById('prospect-value').value) || null,
                next_action: document.getElementById('prospect-next-action').value || null,
                next_action_date: document.getElementById('prospect-next-date').value || null,
                notes: document.getElementById('prospect-notes').value || null
            };

            try {
                await fetch(`${CRM_API}/prospects/${currentProspectId}`, {
                    method: 'PATCH',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });
                loadCRMStats();
                loadProspects();
            } catch (e) {
                console.error('Error updating prospect:', e);
            }
        }

        async function logActivity() {
            if (!currentProspectId) return;

            const data = {
                activity_type: document.getElementById('new-activity-type').value,
                subject: document.getElementById('new-activity-subject').value || null,
                description: document.getElementById('new-activity-description').value || null,
                outcome: document.getElementById('new-activity-outcome').value || null
            };

            try {
                await fetch(`${CRM_API}/prospects/${currentProspectId}/activities`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });
                // Clear form
                document.getElementById('new-activity-subject').value = '';
                document.getElementById('new-activity-description').value = '';
                document.getElementById('new-activity-outcome').value = '';
                // Reload prospect detail
                openProspectDetail(currentProspectId);
            } catch (e) {
                console.error('Error logging activity:', e);
            }
        }

        async function scheduleCallback() {
            if (!currentProspectId) return;

            const callbackDate = document.getElementById('new-callback-date').value;
            if (!callbackDate) {
                alert('Please select a date and time');
                return;
            }

            const data = {
                callback_date: callbackDate,
                callback_type: document.getElementById('new-callback-type').value,
                notes: document.getElementById('new-callback-notes').value || null
            };

            try {
                await fetch(`${CRM_API}/prospects/${currentProspectId}/callbacks`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });
                // Clear form
                document.getElementById('new-callback-date').value = '';
                document.getElementById('new-callback-notes').value = '';
                loadCRMStats();
                alert('Callback scheduled!');
            } catch (e) {
                console.error('Error scheduling callback:', e);
            }
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
                                <button onclick="openProspectDetail(${prospect.id})"
                                    class="inline-flex items-center px-3 py-1.5 text-sm font-medium rounded-md bg-purple-600 text-white hover:bg-purple-700 transition-colors">
                                    <svg class="w-4 h-4 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path>
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"></path>
                                    </svg>
                                    View in CRM
                                </button>
                            </div>
                        `;
                    }

                    openProspectDetail(prospect.id);
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
</body>
</html>
"""
