"""EPA Enforcement Tracker Dashboard page."""
from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()


@router.get("/epa", response_class=HTMLResponse)
async def epa_dashboard():
    """Serve the EPA enforcement tracker page."""
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>EPA Tracker - TSG Safety</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        .loader {
            border: 3px solid #f3f3f3;
            border-top: 3px solid #10b981;
            border-radius: 50%;
            width: 24px;
            height: 24px;
            animation: spin 1s linear infinite;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        .law-badge {
            font-size: 10px;
            padding: 2px 6px;
            border-radius: 4px;
            font-weight: 600;
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
                        <a href="/osha" class="px-4 py-2 rounded-md text-sm font-medium text-gray-300 hover:text-white hover:bg-gray-700">OSHA</a>
                        <a href="/epa" class="px-4 py-2 rounded-md text-sm font-medium bg-green-600 text-white">EPA</a>
                        <a href="/crm" class="px-4 py-2 rounded-md text-sm font-medium text-gray-300 hover:text-white hover:bg-gray-700">CRM</a>
                    </div>
                </div>
                <div class="flex items-center gap-4">
                    <span id="sync-status" class="text-sm text-gray-400"></span>
                    <button onclick="triggerSync()" class="bg-green-600 hover:bg-green-700 px-4 py-2 rounded text-sm">
                        Sync EPA Data
                    </button>
                </div>
            </div>
        </div>
    </nav>

    <main class="max-w-7xl mx-auto px-4 py-8">
        <div class="mb-6">
            <h2 class="text-2xl font-bold text-gray-800">EPA Enforcement</h2>
            <p class="text-gray-600 mt-1">Track enforcement cases, penalties, and compliance status</p>
        </div>
        <div class="flex flex-col lg:flex-row gap-6">
            <!-- Left Sidebar - Stats Cards -->
            <div class="lg:w-48 flex-shrink-0">
                <div class="sticky top-6 space-y-2">
                    <div class="bg-white p-2.5 rounded-lg shadow">
                        <h3 class="text-gray-500 text-[10px] uppercase tracking-wider mb-0.5">Total Cases</h3>
                        <p id="stat-total" class="text-lg font-bold text-green-600">-</p>
                    </div>
                    <div class="bg-white p-2.5 rounded-lg shadow">
                        <h3 class="text-gray-500 text-[10px] uppercase tracking-wider mb-0.5">Total Penalties</h3>
                        <p id="stat-penalties" class="text-lg font-bold text-red-600">-</p>
                    </div>
                    <div class="bg-white p-2.5 rounded-lg shadow">
                        <h3 class="text-gray-500 text-[10px] uppercase tracking-wider mb-0.5">States</h3>
                        <p id="stat-states" class="text-lg font-bold text-blue-600">-</p>
                    </div>
                    <div class="bg-white p-2.5 rounded-lg shadow">
                        <h3 class="text-gray-500 text-[10px] uppercase tracking-wider mb-0.5">Avg Penalty</h3>
                        <p id="stat-avg" class="text-lg font-bold text-orange-600">-</p>
                    </div>
                    <div class="bg-gradient-to-br from-green-50 to-emerald-50 p-2.5 rounded-lg shadow border border-green-200">
                        <h3 class="text-gray-700 text-[10px] uppercase tracking-wider font-semibold mb-1">Recent (30d)</h3>
                        <p id="stat-recent" class="text-lg font-bold text-green-600">-</p>
                    </div>

                    <!-- Laws Breakdown -->
                    <div class="bg-white p-2.5 rounded-lg shadow">
                        <h3 class="text-gray-500 text-[10px] uppercase tracking-wider mb-2">By Law</h3>
                        <div id="laws-breakdown" class="space-y-1 text-xs">
                            <!-- Populated dynamically -->
                        </div>
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
                            <input type="text" id="filter-search" placeholder="Company/Case name..."
                                class="w-full border rounded px-3 py-2" onkeyup="debounceSearch()">
                        </div>
                        <div>
                            <label class="block text-sm text-gray-600 mb-1">State</label>
                            <select id="filter-state" class="w-full border rounded px-3 py-2" onchange="applyFilters()">
                                <option value="">All States</option>
                            </select>
                        </div>
                        <div>
                            <label class="block text-sm text-gray-600 mb-1">Law</label>
                            <select id="filter-law" class="w-full border rounded px-3 py-2" onchange="applyFilters()">
                                <option value="">All Laws</option>
                                <option value="CAA">Clean Air Act (CAA)</option>
                                <option value="CWA">Clean Water Act (CWA)</option>
                                <option value="RCRA">RCRA</option>
                                <option value="SDWA">Safe Drinking Water Act</option>
                                <option value="CERCLA">Superfund (CERCLA)</option>
                                <option value="EPCRA">EPCRA</option>
                                <option value="TSCA">Toxic Substances (TSCA)</option>
                                <option value="FIFRA">FIFRA</option>
                            </select>
                        </div>
                        <div>
                            <label class="block text-sm text-gray-600 mb-1">Min Penalty</label>
                            <input type="number" id="filter-min-penalty" placeholder="0"
                                class="w-full border rounded px-3 py-2" onchange="applyFilters()">
                        </div>
                        <div class="flex items-end">
                            <button onclick="clearFilters()" class="bg-gray-200 hover:bg-gray-300 px-4 py-2 rounded w-full">
                                Clear
                            </button>
                        </div>
                    </div>
                    <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mt-4">
                        <div>
                            <label class="block text-sm text-gray-600 mb-1">Start Date</label>
                            <input type="date" id="filter-start" class="w-full border rounded px-3 py-2" onchange="applyFilters()">
                        </div>
                        <div>
                            <label class="block text-sm text-gray-600 mb-1">End Date</label>
                            <input type="date" id="filter-end" class="w-full border rounded px-3 py-2" onchange="applyFilters()">
                        </div>
                    </div>
                </div>

                <!-- Cases Table -->
                <div class="bg-white rounded-lg shadow">
                    <div class="p-6 border-b flex justify-between items-center">
                        <h2 class="text-lg font-semibold">EPA Enforcement Cases</h2>
                        <div id="loading" class="loader hidden"></div>
                    </div>
                    <div class="overflow-x-auto">
                        <table class="w-full">
                            <thead class="bg-gray-50">
                                <tr>
                                    <th class="px-4 py-3 text-left text-sm font-medium text-gray-500 cursor-pointer hover:bg-gray-100" onclick="sortBy('date_filed')">Date Filed</th>
                                    <th class="px-4 py-3 text-left text-sm font-medium text-gray-500 cursor-pointer hover:bg-gray-100" onclick="sortBy('case_name')">Case/Company</th>
                                    <th class="px-4 py-3 text-left text-sm font-medium text-gray-500">Location</th>
                                    <th class="px-4 py-3 text-center text-sm font-medium text-gray-500">Laws</th>
                                    <th class="px-4 py-3 text-right text-sm font-medium text-gray-500 cursor-pointer hover:bg-gray-100" onclick="sortBy('fed_penalty')">Penalty</th>
                                    <th class="px-4 py-3 text-center text-sm font-medium text-gray-500">Status</th>
                                    <th class="px-4 py-3 text-center text-sm font-medium text-gray-500 w-10">EPA</th>
                                </tr>
                            </thead>
                            <tbody id="cases-table" class="divide-y">
                                <tr><td colspan="7" class="px-4 py-8 text-center text-gray-500">Loading...</td></tr>
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
        <div class="bg-white rounded-lg shadow-xl max-w-3xl w-full mx-4 max-h-[90vh] overflow-y-auto">
            <div id="modal-content"></div>
        </div>
    </div>

    <script>
        const API_BASE = '/api/epa';
        let currentPage = 1;
        let currentSort = 'date_filed';
        let currentSortDesc = true;
        let totalPages = 1;
        let searchTimeout = null;
        let syncPollTimer = null;

        // Law badge colors
        const lawColors = {
            'CAA': 'bg-blue-100 text-blue-800',
            'CWA': 'bg-cyan-100 text-cyan-800',
            'RCRA': 'bg-orange-100 text-orange-800',
            'SDWA': 'bg-teal-100 text-teal-800',
            'CERCLA': 'bg-red-100 text-red-800',
            'EPCRA': 'bg-yellow-100 text-yellow-800',
            'TSCA': 'bg-purple-100 text-purple-800',
            'FIFRA': 'bg-green-100 text-green-800'
        };

        // Initialize
        document.addEventListener('DOMContentLoaded', () => {
            loadFilters();
            loadStats();
            loadCases();
        });

        async function loadFilters() {
            try {
                const states = await fetch(`${API_BASE}/states`).then(r => r.json());
                const stateSelect = document.getElementById('filter-state');
                states.forEach(s => {
                    const opt = document.createElement('option');
                    opt.value = s.state;
                    opt.textContent = `${s.state} (${s.count})`;
                    stateSelect.appendChild(opt);
                });
            } catch (e) {
                console.error('Error loading filters:', e);
            }
        }

        async function loadStats() {
            try {
                const stats = await fetch(`${API_BASE}/stats`).then(r => r.json());

                document.getElementById('stat-total').textContent = stats.total_cases.toLocaleString();
                document.getElementById('stat-penalties').textContent = '$' + stats.total_penalties.toLocaleString(undefined, {maximumFractionDigits: 0});
                document.getElementById('stat-states').textContent = stats.states_count;
                document.getElementById('stat-avg').textContent = '$' + stats.avg_penalty.toLocaleString(undefined, {maximumFractionDigits: 0});
                document.getElementById('stat-recent').textContent = stats.recent_cases;

                // Laws breakdown
                const lawsDiv = document.getElementById('laws-breakdown');
                lawsDiv.innerHTML = Object.entries(stats.by_law)
                    .filter(([law, count]) => count > 0)
                    .sort((a, b) => b[1] - a[1])
                    .map(([law, count]) => `
                        <div class="flex justify-between items-center">
                            <span class="law-badge ${lawColors[law] || 'bg-gray-100 text-gray-800'}">${law}</span>
                            <span class="font-medium">${count}</span>
                        </div>
                    `).join('');
            } catch (e) {
                console.error('Error loading stats:', e);
            }
        }

        function getFilterParams() {
            const params = {};
            const search = document.getElementById('filter-search').value;
            const state = document.getElementById('filter-state').value;
            const law = document.getElementById('filter-law').value;
            const start = document.getElementById('filter-start').value;
            const end = document.getElementById('filter-end').value;
            const minPenalty = document.getElementById('filter-min-penalty').value;

            if (search) params.search = search;
            if (state) params.state = state;
            if (law) params.law = law;
            if (start) params.start_date = start;
            if (end) params.end_date = end;
            if (minPenalty) params.min_penalty = minPenalty;

            return params;
        }

        async function loadCases() {
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
                const data = await fetch(`${API_BASE}/list?${queryString}`).then(r => r.json());

                totalPages = data.total_pages;
                renderTable(data.items);
                updatePagination(data);
            } catch (e) {
                console.error('Error loading cases:', e);
                document.getElementById('cases-table').innerHTML =
                    '<tr><td colspan="6" class="px-4 py-8 text-center text-red-500">Error loading data</td></tr>';
            } finally {
                loading.classList.add('hidden');
            }
        }

        function renderTable(items) {
            const tbody = document.getElementById('cases-table');

            if (!items.length) {
                tbody.innerHTML = '<tr><td colspan="7" class="px-4 py-8 text-center text-gray-500">No cases found. Click "Sync EPA Data" to fetch cases.</td></tr>';
                return;
            }

            tbody.innerHTML = items.map(c => `
                <tr class="hover:bg-gray-50 cursor-pointer" onclick="showDetail(${c.id})">
                    <td class="px-4 py-3 text-sm">${formatDate(c.date_filed)}</td>
                    <td class="px-4 py-3">
                        <div class="font-medium text-gray-900 truncate max-w-xs">${escapeHtml(c.case_name || c.facility_name || 'Unknown')}</div>
                        <div class="text-xs text-gray-500">${c.case_number}</div>
                    </td>
                    <td class="px-4 py-3 text-sm text-gray-600">
                        ${escapeHtml(c.facility_city || '')}${c.facility_city && c.facility_state ? ', ' : ''}${c.facility_state || ''}
                    </td>
                    <td class="px-4 py-3 text-center">
                        <div class="flex flex-wrap gap-1 justify-center">
                            ${c.laws_violated.map(law => `<span class="law-badge ${lawColors[law] || 'bg-gray-100 text-gray-800'}">${law}</span>`).join('')}
                        </div>
                    </td>
                    <td class="px-4 py-3 text-right font-medium ${c.fed_penalty > 0 ? 'text-red-600' : 'text-gray-500'}">
                        ${c.fed_penalty > 0 ? '$' + c.fed_penalty.toLocaleString(undefined, {maximumFractionDigits: 0}) : '-'}
                    </td>
                    <td class="px-4 py-3 text-center">
                        <span class="px-2 py-1 rounded text-xs ${getStatusColor(c.case_status)}">${c.case_status || 'Unknown'}</span>
                    </td>
                    <td class="px-4 py-3 text-center" onclick="event.stopPropagation()">
                        ${c.echo_url ? `
                            <a href="${c.echo_url}" target="_blank" rel="noopener noreferrer"
                               class="inline-flex items-center justify-center w-8 h-8 rounded hover:bg-green-100 text-green-600 hover:text-green-800 transition-colors"
                               title="View on EPA ECHO">
                                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"></path>
                                </svg>
                            </a>
                        ` : '-'}
                    </td>
                </tr>
            `).join('');
        }

        function getStatusColor(status) {
            if (!status) return 'bg-gray-100 text-gray-800';
            const s = status.toLowerCase();
            if (s.includes('closed') || s.includes('settled')) return 'bg-green-100 text-green-800';
            if (s.includes('open') || s.includes('pending')) return 'bg-yellow-100 text-yellow-800';
            return 'bg-gray-100 text-gray-800';
        }

        function formatDate(dateStr) {
            if (!dateStr) return '-';
            const date = new Date(dateStr);
            return date.toLocaleDateString();
        }

        function escapeHtml(text) {
            if (!text) return '';
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        function updatePagination(data) {
            document.getElementById('pagination-info').textContent =
                `Showing ${((data.page - 1) * data.page_size) + 1}-${Math.min(data.page * data.page_size, data.total)} of ${data.total} cases`;

            document.getElementById('btn-prev').disabled = data.page <= 1;
            document.getElementById('btn-next').disabled = data.page >= data.total_pages;
        }

        function prevPage() {
            if (currentPage > 1) {
                currentPage--;
                loadCases();
            }
        }

        function nextPage() {
            if (currentPage < totalPages) {
                currentPage++;
                loadCases();
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
            loadCases();
        }

        function debounceSearch() {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                currentPage = 1;
                loadCases();
            }, 300);
        }

        function applyFilters() {
            currentPage = 1;
            loadCases();
        }

        function clearFilters() {
            document.getElementById('filter-search').value = '';
            document.getElementById('filter-state').value = '';
            document.getElementById('filter-law').value = '';
            document.getElementById('filter-start').value = '';
            document.getElementById('filter-end').value = '';
            document.getElementById('filter-min-penalty').value = '';
            currentPage = 1;
            loadCases();
        }

        async function showDetail(caseId) {
            const modal = document.getElementById('modal');
            const content = document.getElementById('modal-content');

            content.innerHTML = '<div class="p-8 text-center"><div class="loader mx-auto"></div><p class="mt-4 text-gray-500">Loading...</p></div>';
            modal.classList.remove('hidden');

            try {
                const data = await fetch(`${API_BASE}/${caseId}`).then(r => r.json());

                content.innerHTML = `
                    <div class="p-6 border-b bg-gradient-to-r from-green-50 to-emerald-50">
                        <div class="flex justify-between items-start">
                            <div>
                                <h2 class="text-xl font-semibold text-gray-800">${escapeHtml(data.case_name || data.facility_name || 'Case Details')}</h2>
                                <p class="text-sm text-gray-600 mt-1">Case #${data.case_number}</p>
                            </div>
                            <button onclick="closeModal()" class="text-gray-500 hover:text-gray-700 text-2xl">&times;</button>
                        </div>
                    </div>

                    <div class="p-6">
                        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                            <div>
                                <h3 class="font-semibold text-gray-700 mb-3">Case Information</h3>
                                <div class="space-y-2 text-sm">
                                    <div class="flex justify-between">
                                        <span class="text-gray-500">Status:</span>
                                        <span class="font-medium">${data.case_status || '-'}</span>
                                    </div>
                                    <div class="flex justify-between">
                                        <span class="text-gray-500">Category:</span>
                                        <span class="font-medium">${data.case_category_desc || data.case_category || '-'}</span>
                                    </div>
                                    <div class="flex justify-between">
                                        <span class="text-gray-500">Type:</span>
                                        <span class="font-medium">${data.civil_criminal === 'CI' ? 'Civil' : data.civil_criminal === 'CR' ? 'Criminal' : '-'}</span>
                                    </div>
                                    <div class="flex justify-between">
                                        <span class="text-gray-500">Lead Agency:</span>
                                        <span class="font-medium">${data.case_lead === 'E' ? 'EPA' : data.case_lead === 'S' ? 'State' : '-'}</span>
                                    </div>
                                    <div class="flex justify-between">
                                        <span class="text-gray-500">EPA Region:</span>
                                        <span class="font-medium">${data.region || '-'}</span>
                                    </div>
                                </div>

                                <h3 class="font-semibold text-gray-700 mb-3 mt-6">Dates</h3>
                                <div class="space-y-2 text-sm">
                                    <div class="flex justify-between">
                                        <span class="text-gray-500">Filed:</span>
                                        <span class="font-medium">${formatDate(data.date_filed)}</span>
                                    </div>
                                    <div class="flex justify-between">
                                        <span class="text-gray-500">Settlement:</span>
                                        <span class="font-medium">${formatDate(data.settlement_date)}</span>
                                    </div>
                                    <div class="flex justify-between">
                                        <span class="text-gray-500">Closed:</span>
                                        <span class="font-medium">${formatDate(data.date_closed)}</span>
                                    </div>
                                </div>
                            </div>

                            <div>
                                <h3 class="font-semibold text-gray-700 mb-3">Location</h3>
                                <div class="space-y-2 text-sm">
                                    <div class="flex justify-between">
                                        <span class="text-gray-500">Facility:</span>
                                        <span class="font-medium">${escapeHtml(data.facility_name) || '-'}</span>
                                    </div>
                                    <div class="flex justify-between">
                                        <span class="text-gray-500">City:</span>
                                        <span class="font-medium">${escapeHtml(data.facility_city) || '-'}</span>
                                    </div>
                                    <div class="flex justify-between">
                                        <span class="text-gray-500">State:</span>
                                        <span class="font-medium">${data.facility_state || '-'}</span>
                                    </div>
                                </div>

                                <h3 class="font-semibold text-gray-700 mb-3 mt-6">Penalties</h3>
                                <div class="space-y-2 text-sm">
                                    <div class="flex justify-between">
                                        <span class="text-gray-500">Federal Penalty:</span>
                                        <span class="font-medium text-red-600">${data.fed_penalty > 0 ? '$' + data.fed_penalty.toLocaleString() : '-'}</span>
                                    </div>
                                    <div class="flex justify-between">
                                        <span class="text-gray-500">State/Local Penalty:</span>
                                        <span class="font-medium">${data.state_local_penalty > 0 ? '$' + data.state_local_penalty.toLocaleString() : '-'}</span>
                                    </div>
                                    <div class="flex justify-between border-t pt-2 mt-2">
                                        <span class="text-gray-700 font-medium">Total:</span>
                                        <span class="font-bold text-red-600">${data.total_penalty > 0 ? '$' + data.total_penalty.toLocaleString() : '-'}</span>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div class="mt-6">
                            <h3 class="font-semibold text-gray-700 mb-3">Environmental Laws Violated</h3>
                            <div class="flex flex-wrap gap-2">
                                ${data.laws_violated.length > 0
                                    ? data.laws_violated.map(law => `<span class="law-badge ${lawColors[law] || 'bg-gray-100 text-gray-800'}">${law} - ${getLawFullName(law)}</span>`).join('')
                                    : '<span class="text-gray-500">-</span>'}
                            </div>
                        </div>

                        ${data.echo_url ? `
                        <div class="mt-6 pt-6 border-t">
                            <a href="${data.echo_url}" target="_blank" rel="noopener noreferrer"
                               class="inline-flex items-center gap-2 bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg transition-colors">
                                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"></path>
                                </svg>
                                View Full Details on EPA ECHO
                            </a>
                            <p class="text-xs text-gray-500 mt-2">Opens the official EPA enforcement case report with complete facility and violation information.</p>
                        </div>
                        ` : ''}
                    </div>
                `;
            } catch (e) {
                console.error('Error loading case detail:', e);
                content.innerHTML = '<div class="p-8 text-center text-red-500">Error loading case details</div>';
            }
        }

        function getLawFullName(law) {
            const names = {
                'CAA': 'Clean Air Act',
                'CWA': 'Clean Water Act',
                'RCRA': 'Resource Conservation and Recovery Act',
                'SDWA': 'Safe Drinking Water Act',
                'CERCLA': 'Superfund',
                'EPCRA': 'Emergency Planning and Community Right-to-Know Act',
                'TSCA': 'Toxic Substances Control Act',
                'FIFRA': 'Federal Insecticide, Fungicide, and Rodenticide Act'
            };
            return names[law] || law;
        }

        function closeModal() {
            document.getElementById('modal').classList.add('hidden');
        }

        // Close modal on backdrop click
        document.getElementById('modal').addEventListener('click', e => {
            if (e.target.id === 'modal') closeModal();
        });

        // Close on escape
        document.addEventListener('keydown', e => {
            if (e.key === 'Escape') closeModal();
        });

        async function triggerSync() {
            const statusEl = document.getElementById('sync-status');
            statusEl.textContent = 'Syncing...';

            try {
                const response = await fetch(`${API_BASE}/sync?days_back=90`, { method: 'POST' });
                const data = await response.json();

                if (data.success) {
                    statusEl.textContent = 'EPA sync running...';
                    const runId = data.stats?.run_id || null;
                    startSyncPolling(runId);
                } else {
                    statusEl.textContent = 'Sync failed';
                }
            } catch (e) {
                console.error('Sync error:', e);
                statusEl.textContent = 'Sync error';
            }
        }

        function startSyncPolling(runId) {
            const statusEl = document.getElementById('sync-status');

            if (syncPollTimer) {
                clearInterval(syncPollTimer);
                syncPollTimer = null;
            }

            let attempts = 0;
            const maxAttempts = 40;

            syncPollTimer = setInterval(async () => {
                attempts += 1;
                try {
                    const response = await fetch(`${API_BASE}/sync/status`);
                    if (!response.ok) {
                        throw new Error('Status unavailable');
                    }
                    const payload = await response.json();
                    const latest = payload.latest;
                    if (!latest) {
                        return;
                    }

                    if (runId && latest.id !== runId) {
                        if (attempts >= maxAttempts) {
                            statusEl.textContent = 'EPA sync running (status timeout)';
                            clearInterval(syncPollTimer);
                            syncPollTimer = null;
                        }
                        return;
                    }

                    if (latest.status === 'running') {
                        statusEl.textContent = 'EPA sync running...';
                        return;
                    }

                    let added = null;
                    if (latest.details) {
                        try {
                            const details = JSON.parse(latest.details);
                            added = details?.new;
                        } catch (e) {}
                    }

                    if (latest.status === 'success') {
                        statusEl.textContent = `EPA sync completed${added !== null ? ` (added ${added})` : ''}`;
                        loadStats();
                        loadCases();
                    } else {
                        statusEl.textContent = 'EPA sync failed';
                    }

                    clearInterval(syncPollTimer);
                    syncPollTimer = null;
                    setTimeout(() => { statusEl.textContent = ''; }, 8000);
                } catch (e) {
                    if (attempts >= maxAttempts) {
                        statusEl.textContent = 'EPA sync status unknown';
                        clearInterval(syncPollTimer);
                        syncPollTimer = null;
                    }
                }
            }, 3000);
        }
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

                // Manual section
                manualContent.innerHTML = '<div class="text-gray-400">Use header buttons to trigger manual syncs</div>';
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

