"""CRM Dashboard page."""
from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()


@router.get("/crm", response_class=HTMLResponse)
async def crm_page():
    """Render the CRM dashboard page."""
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CRM - TSG Safety Tracker</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        .calendar-day { min-height: 80px; }
        .calendar-event { font-size: 10px; padding: 2px 4px; margin-bottom: 2px; border-radius: 2px; cursor: pointer; }
        .calendar-event:hover { opacity: 0.8; }
    </style>
</head>
<body class="bg-gray-100 min-h-screen">
    <!-- Navigation -->
    <nav class="bg-gray-900 text-white shadow-lg">
        <div class="max-w-7xl mx-auto px-4">
            <div class="flex justify-between items-center h-16">
                <div class="flex items-center space-x-8">
                    <h1 class="text-xl font-bold">TSG Safety</h1>
                    <div class="flex space-x-1">
                        <a href="/" class="px-4 py-2 rounded-md text-sm font-medium text-gray-300 hover:text-white hover:bg-gray-700">Overview</a>
                        <a href="/osha" class="px-4 py-2 rounded-md text-sm font-medium text-gray-300 hover:text-white hover:bg-gray-700">OSHA</a>
                        <a href="/epa" class="px-4 py-2 rounded-md text-sm font-medium text-gray-300 hover:text-white hover:bg-gray-700">EPA</a>
                        <a href="/crm" class="px-4 py-2 rounded-md text-sm font-medium bg-purple-600 text-white">CRM</a>
                    </div>
                </div>
            </div>
        </div>
    </nav>

    <div class="max-w-7xl mx-auto px-4 py-8">
        <!-- Header -->
        <div class="mb-6">
            <h2 class="text-2xl font-bold text-gray-800">Sales Pipeline</h2>
            <p id="crm-subtitle" class="text-gray-600 mt-1">Loading...</p>
        </div>

        <!-- Analytics & Calendar Section -->
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
            <!-- Pipeline Funnel Chart -->
            <div class="bg-white rounded-lg shadow p-4">
                <h3 class="text-sm font-semibold text-gray-700 mb-3">Pipeline Funnel</h3>
                <div style="height: 200px; position: relative;">
                    <canvas id="funnelChart"></canvas>
                </div>
            </div>

            <!-- Activity Summary -->
            <div class="bg-white rounded-lg shadow p-4">
                <h3 class="text-sm font-semibold text-gray-700 mb-3">Activity This Week</h3>
                <div id="activity-summary" class="space-y-2">
                    <div class="flex justify-between items-center">
                        <span class="text-sm text-gray-600">Calls Made</span>
                        <span id="activity-calls" class="font-semibold text-blue-600">-</span>
                    </div>
                    <div class="flex justify-between items-center">
                        <span class="text-sm text-gray-600">Emails Sent</span>
                        <span id="activity-emails" class="font-semibold text-green-600">-</span>
                    </div>
                    <div class="flex justify-between items-center">
                        <span class="text-sm text-gray-600">Meetings</span>
                        <span id="activity-meetings" class="font-semibold text-purple-600">-</span>
                    </div>
                    <div class="flex justify-between items-center border-t pt-2 mt-2">
                        <span class="text-sm text-gray-600">Total Activities</span>
                        <span id="activity-total" class="font-bold text-gray-800">-</span>
                    </div>
                </div>
                <div class="mt-4 pt-3 border-t">
                    <h4 class="text-xs font-semibold text-gray-500 uppercase mb-2">Conversion Rate</h4>
                    <div class="flex items-center gap-2">
                        <div class="flex-1 bg-gray-200 rounded-full h-3">
                            <div id="conversion-bar" class="bg-green-500 h-3 rounded-full" style="width: 0%"></div>
                        </div>
                        <span id="conversion-rate" class="text-sm font-semibold text-green-600">0%</span>
                    </div>
                    <p class="text-xs text-gray-500 mt-1">Won / (Won + Lost)</p>
                </div>
            </div>

            <!-- Mini Calendar -->
            <div class="bg-white rounded-lg shadow p-4">
                <div class="flex justify-between items-center mb-3">
                    <h3 class="text-sm font-semibold text-gray-700">Follow-up Calendar</h3>
                    <div class="flex gap-1">
                        <button onclick="changeMonth(-1)" class="p-1 hover:bg-gray-100 rounded">&lt;</button>
                        <span id="calendar-month" class="text-sm font-medium px-2">January 2026</span>
                        <button onclick="changeMonth(1)" class="p-1 hover:bg-gray-100 rounded">&gt;</button>
                    </div>
                </div>
                <div id="mini-calendar" class="text-xs">
                    <!-- Calendar will be rendered here -->
                </div>
                <div class="mt-3 pt-3 border-t">
                    <div class="flex items-center gap-4 text-xs">
                        <span class="flex items-center gap-1"><span class="w-2 h-2 rounded bg-blue-500"></span> Callback</span>
                        <span class="flex items-center gap-1"><span class="w-2 h-2 rounded bg-green-500"></span> Follow-up</span>
                        <span class="flex items-center gap-1"><span class="w-2 h-2 rounded bg-red-500"></span> Overdue</span>
                    </div>
                </div>
            </div>
        </div>

        <!-- Stats Cards -->
        <div class="grid grid-cols-2 md:grid-cols-6 gap-4 mb-6">
            <div class="bg-white rounded-lg shadow p-4">
                <p class="text-xs text-gray-500 uppercase">Total Prospects</p>
                <p id="stat-total" class="text-2xl font-bold text-purple-600">-</p>
            </div>
            <div class="bg-white rounded-lg shadow p-4">
                <p class="text-xs text-gray-500 uppercase">New Leads</p>
                <p id="stat-new" class="text-2xl font-bold text-blue-600">-</p>
            </div>
            <div class="bg-white rounded-lg shadow p-4">
                <p class="text-xs text-gray-500 uppercase">Contacted</p>
                <p id="stat-contacted" class="text-2xl font-bold text-yellow-600">-</p>
            </div>
            <div class="bg-white rounded-lg shadow p-4">
                <p class="text-xs text-gray-500 uppercase">Qualified</p>
                <p id="stat-qualified" class="text-2xl font-bold text-green-600">-</p>
            </div>
            <div class="bg-white rounded-lg shadow p-4">
                <p class="text-xs text-gray-500 uppercase">Won</p>
                <p id="stat-won" class="text-2xl font-bold text-purple-600">-</p>
            </div>
            <div class="bg-white rounded-lg shadow p-4">
                <p class="text-xs text-gray-500 uppercase">Pipeline Value</p>
                <p id="stat-value" class="text-2xl font-bold text-green-600">-</p>
            </div>
        </div>

        <!-- Tabs -->
        <div class="bg-white rounded-lg shadow">
            <div class="border-b px-6 flex gap-4">
                <button id="tab-prospects" onclick="switchTab('prospects')" class="py-4 px-4 border-b-2 border-purple-600 text-purple-600 font-medium">Prospects</button>
                <button id="tab-callbacks" onclick="switchTab('callbacks')" class="py-4 px-4 border-b-2 border-transparent text-gray-500 hover:text-gray-700">Callbacks</button>
            </div>

            <!-- Filter Bar -->
            <div class="px-6 py-4 border-b bg-gray-50 flex flex-wrap gap-4 items-center">
                <select id="filter-status" onchange="loadProspects()" class="border rounded px-3 py-2 text-sm">
                    <option value="">All Statuses</option>
                    <option value="new_lead">New Lead</option>
                    <option value="contacted">Contacted</option>
                    <option value="qualified">Qualified</option>
                    <option value="won">Won</option>
                    <option value="lost">Lost</option>
                </select>
                <select id="filter-priority" onchange="loadProspects()" class="border rounded px-3 py-2 text-sm">
                    <option value="">All Priorities</option>
                    <option value="high">High</option>
                    <option value="medium">Medium</option>
                    <option value="low">Low</option>
                </select>
                <input type="text" id="search-input" placeholder="Search company..." class="border rounded px-3 py-2 text-sm w-64" onkeyup="debounceSearch()">
            </div>

            <!-- Prospects Content -->
            <div id="prospects-content" class="p-6">
                <table class="w-full">
                    <thead class="bg-gray-50">
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
                    <tbody id="prospects-list">
                        <tr><td colspan="7" class="px-4 py-8 text-center text-gray-500">Loading...</td></tr>
                    </tbody>
                </table>
            </div>

            <!-- Callbacks Content -->
            <div id="callbacks-content" class="p-6 hidden">
                <table class="w-full">
                    <thead class="bg-gray-50">
                        <tr>
                            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Date/Time</th>
                            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Company</th>
                            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Type</th>
                            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Notes</th>
                            <th class="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Status</th>
                            <th class="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Actions</th>
                        </tr>
                    </thead>
                    <tbody id="callbacks-list">
                        <tr><td colspan="6" class="px-4 py-8 text-center text-gray-500">Loading...</td></tr>
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <!-- Prospect Detail Modal -->
    <div id="prospect-modal" class="fixed inset-0 bg-black bg-opacity-50 hidden flex items-center justify-center z-50">
        <div class="bg-white rounded-lg shadow-xl max-w-4xl w-full mx-4 max-h-[90vh] flex flex-col">
            <div class="p-6 border-b flex justify-between items-center">
                <div>
                    <h2 id="prospect-title" class="text-xl font-semibold text-gray-800">Prospect Details</h2>
                    <p id="prospect-subtitle" class="text-sm text-gray-600 mt-1"></p>
                </div>
                <button onclick="closeProspectModal()" class="text-gray-500 hover:text-gray-700 text-2xl">&times;</button>
            </div>
            <div class="flex-1 overflow-auto p-6" id="prospect-content">
                <!-- Content loaded dynamically -->
            </div>
        </div>
    </div>

    <!-- Company Info Modal -->
    <div id="company-info-modal" class="fixed inset-0 bg-black bg-opacity-50 hidden flex items-center justify-center z-[60]">
        <div class="bg-white rounded-lg shadow-xl max-w-3xl w-full mx-4 max-h-[90vh] flex flex-col">
            <div class="p-6 border-b flex justify-between items-center">
                <div>
                    <h2 class="text-xl font-semibold text-gray-800">Company Information</h2>
                    <p class="text-sm text-gray-600 mt-1">OSHA inspection details, enriched company data, and contacts</p>
                </div>
                <button onclick="closeCompanyInfoModal()" class="text-gray-500 hover:text-gray-700 text-2xl">&times;</button>
            </div>
            <div class="flex-1 overflow-auto p-6" id="company-info-content">
                <!-- Content loaded dynamically -->
            </div>
        </div>
    </div>

    <script>
        const CRM_API = '/api/crm';
        let searchTimeout = null;
        let currentProspectId = null;
        let currentMonth = new Date();
        let funnelChart = null;
        let allCallbacks = [];

        // Outcome options for activity logging
        const outcomeOptions = {
            call: [
                'Connected - Interested',
                'Connected - Not Interested',
                'Connected - Call Back Later',
                'Left Voicemail',
                'No Answer',
                'Wrong Number',
                'Busy',
                'Sent to Voicemail'
            ],
            email: [
                'Sent - Awaiting Response',
                'Replied - Interested',
                'Replied - Not Interested',
                'Replied - Request More Info',
                'Bounced',
                'No Response'
            ],
            meeting: [
                'Completed - Moving Forward',
                'Completed - Need Follow-up',
                'Completed - Not a Fit',
                'Rescheduled',
                'No Show',
                'Cancelled'
            ],
            note: [
                'General Note',
                'Research Finding',
                'Contact Update',
                'Status Update'
            ],
            task: [
                'Completed',
                'In Progress',
                'Deferred',
                'Cancelled'
            ]
        };

        // Initialize
        document.addEventListener('DOMContentLoaded', () => {
            loadStats();
            loadProspects();
            loadActivitySummary();
            loadAllCallbacks();
            renderCalendar();
        });

        async function loadStats() {
            try {
                const response = await fetch(`${CRM_API}/stats`);
                const stats = await response.json();

                document.getElementById('stat-total').textContent = stats.total_prospects || 0;
                document.getElementById('stat-new').textContent = stats.by_status?.new_lead || 0;
                document.getElementById('stat-contacted').textContent = stats.by_status?.contacted || 0;
                document.getElementById('stat-qualified').textContent = stats.by_status?.qualified || 0;
                document.getElementById('stat-won').textContent = stats.by_status?.won || 0;
                document.getElementById('stat-value').textContent = '$' + (stats.total_pipeline_value || 0).toLocaleString();

                document.getElementById('crm-subtitle').textContent =
                    `${stats.total_prospects} prospects | ${stats.upcoming_callbacks} upcoming callbacks | Won this month: $${(stats.won_value_this_month || 0).toLocaleString()}`;

                // Update funnel chart
                updateFunnelChart(stats.by_status || {});

                // Calculate conversion rate
                const won = stats.by_status?.won || 0;
                const lost = stats.by_status?.lost || 0;
                const total = won + lost;
                const conversionRate = total > 0 ? Math.round((won / total) * 100) : 0;
                document.getElementById('conversion-rate').textContent = conversionRate + '%';
                document.getElementById('conversion-bar').style.width = conversionRate + '%';
            } catch (e) {
                console.error('Error loading stats:', e);
            }
        }

        function updateFunnelChart(byStatus) {
            const ctx = document.getElementById('funnelChart').getContext('2d');

            if (funnelChart) {
                funnelChart.destroy();
            }

            funnelChart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: ['New Lead', 'Contacted', 'Qualified', 'Won', 'Lost'],
                    datasets: [{
                        data: [
                            byStatus.new_lead || 0,
                            byStatus.contacted || 0,
                            byStatus.qualified || 0,
                            byStatus.won || 0,
                            byStatus.lost || 0
                        ],
                        backgroundColor: [
                            'rgba(59, 130, 246, 0.8)',
                            'rgba(234, 179, 8, 0.8)',
                            'rgba(34, 197, 94, 0.8)',
                            'rgba(147, 51, 234, 0.8)',
                            'rgba(239, 68, 68, 0.8)'
                        ],
                        borderRadius: 4
                    }]
                },
                options: {
                    indexAxis: 'y',
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false }
                    },
                    scales: {
                        x: { beginAtZero: true, grid: { display: false } },
                        y: { grid: { display: false } }
                    }
                }
            });
        }

        async function loadActivitySummary() {
            try {
                // Get all prospects to count activities
                const response = await fetch(`${CRM_API}/prospects?page_size=1000`);
                const data = await response.json();

                let calls = 0, emails = 0, meetings = 0, total = 0;
                const oneWeekAgo = new Date();
                oneWeekAgo.setDate(oneWeekAgo.getDate() - 7);

                // This is a simplified count - in production you'd have a dedicated endpoint
                for (const prospect of data.items || []) {
                    if (prospect.activities) {
                        for (const activity of prospect.activities) {
                            const actDate = new Date(activity.activity_date);
                            if (actDate >= oneWeekAgo) {
                                total++;
                                if (activity.activity_type === 'call') calls++;
                                else if (activity.activity_type === 'email') emails++;
                                else if (activity.activity_type === 'meeting') meetings++;
                            }
                        }
                    }
                }

                document.getElementById('activity-calls').textContent = calls;
                document.getElementById('activity-emails').textContent = emails;
                document.getElementById('activity-meetings').textContent = meetings;
                document.getElementById('activity-total').textContent = total;
            } catch (e) {
                console.error('Error loading activity summary:', e);
            }
        }

        async function loadAllCallbacks() {
            try {
                const response = await fetch(`${CRM_API}/callbacks`);
                allCallbacks = await response.json();
                renderCalendar();
            } catch (e) {
                console.error('Error loading callbacks:', e);
                allCallbacks = [];
            }
        }

        function changeMonth(delta) {
            currentMonth.setMonth(currentMonth.getMonth() + delta);
            renderCalendar();
        }

        function renderCalendar() {
            const year = currentMonth.getFullYear();
            const month = currentMonth.getMonth();

            // Update month label
            const monthNames = ['January', 'February', 'March', 'April', 'May', 'June',
                'July', 'August', 'September', 'October', 'November', 'December'];
            document.getElementById('calendar-month').textContent = `${monthNames[month]} ${year}`;

            // Get first day and number of days in month
            const firstDay = new Date(year, month, 1).getDay();
            const daysInMonth = new Date(year, month + 1, 0).getDate();
            const today = new Date();
            today.setHours(0, 0, 0, 0);

            // Group callbacks by date
            const callbacksByDate = {};
            for (const cb of allCallbacks) {
                const cbDate = new Date(cb.callback_date);
                if (cbDate.getFullYear() === year && cbDate.getMonth() === month) {
                    const day = cbDate.getDate();
                    if (!callbacksByDate[day]) callbacksByDate[day] = [];
                    callbacksByDate[day].push(cb);
                }
            }

            // Build calendar HTML
            let html = '<div class="grid grid-cols-7 gap-1 text-center">';

            // Day headers
            const dayNames = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
            for (const day of dayNames) {
                html += `<div class="text-xs font-medium text-gray-500 py-1">${day}</div>`;
            }

            // Empty cells before first day
            for (let i = 0; i < firstDay; i++) {
                html += '<div class="calendar-day bg-gray-50"></div>';
            }

            // Days
            for (let day = 1; day <= daysInMonth; day++) {
                const currentDate = new Date(year, month, day);
                const isToday = currentDate.getTime() === today.getTime();
                const isPast = currentDate < today;
                const callbacks = callbacksByDate[day] || [];

                let dayClass = 'calendar-day p-1 rounded border';
                if (isToday) dayClass += ' bg-blue-50 border-blue-300';
                else dayClass += ' bg-white border-gray-200';

                html += `<div class="${dayClass}">`;
                html += `<div class="text-xs font-medium ${isToday ? 'text-blue-600' : 'text-gray-700'}">${day}</div>`;

                // Show callbacks for this day (max 2, then show +N more)
                const maxToShow = 2;
                for (let i = 0; i < Math.min(callbacks.length, maxToShow); i++) {
                    const cb = callbacks[i];
                    const isOverdue = isPast && cb.status === 'pending';
                    let eventClass = 'calendar-event truncate ';
                    if (isOverdue) eventClass += 'bg-red-200 text-red-800';
                    else if (cb.callback_type === 'call') eventClass += 'bg-blue-200 text-blue-800';
                    else eventClass += 'bg-green-200 text-green-800';

                    html += `<div class="${eventClass}" onclick="openProspectDetail(${cb.prospect_id})" title="${escapeHtml(cb.estab_name || '')}">${escapeHtml(cb.estab_name || '').substring(0, 10)}</div>`;
                }

                if (callbacks.length > maxToShow) {
                    html += `<div class="text-xs text-gray-500">+${callbacks.length - maxToShow} more</div>`;
                }

                html += '</div>';
            }

            html += '</div>';
            document.getElementById('mini-calendar').innerHTML = html;
        }

        function switchTab(tab) {
            document.getElementById('tab-prospects').classList.remove('border-purple-600', 'text-purple-600');
            document.getElementById('tab-prospects').classList.add('border-transparent', 'text-gray-500');
            document.getElementById('tab-callbacks').classList.remove('border-purple-600', 'text-purple-600');
            document.getElementById('tab-callbacks').classList.add('border-transparent', 'text-gray-500');

            document.getElementById(`tab-${tab}`).classList.remove('border-transparent', 'text-gray-500');
            document.getElementById(`tab-${tab}`).classList.add('border-purple-600', 'text-purple-600');

            document.getElementById('prospects-content').classList.add('hidden');
            document.getElementById('callbacks-content').classList.add('hidden');
            document.getElementById(`${tab}-content`).classList.remove('hidden');

            if (tab === 'callbacks') {
                loadCallbacks();
            } else {
                loadProspects();
            }
        }

        function debounceSearch() {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(loadProspects, 300);
        }

        async function loadProspects() {
            const status = document.getElementById('filter-status').value;
            const priority = document.getElementById('filter-priority').value;
            const search = document.getElementById('search-input').value;

            let url = `${CRM_API}/prospects?page_size=100`;
            if (status) url += `&status=${status}`;
            if (priority) url += `&priority=${priority}`;
            if (search) url += `&search=${encodeURIComponent(search)}`;

            try {
                const response = await fetch(url);
                const data = await response.json();

                const tbody = document.getElementById('prospects-list');
                if (!data.items || data.items.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="7" class="px-4 py-8 text-center text-gray-500">No prospects found. Add prospects from inspection details.</td></tr>';
                    return;
                }

                tbody.innerHTML = data.items.map(p => `
                    <tr class="hover:bg-gray-50 cursor-pointer border-b" onclick="openProspectDetail(${p.id})">
                        <td class="px-4 py-4">
                            <div class="font-medium text-gray-900">${escapeHtml(p.estab_name || 'Unknown')}</div>
                            <div class="text-xs text-gray-500">${escapeHtml(p.activity_nr || '')}</div>
                        </td>
                        <td class="px-4 py-4 text-sm text-gray-600">
                            ${escapeHtml(p.site_city || '')}${p.site_city && p.site_state ? ', ' : ''}${escapeHtml(p.site_state || '')}
                        </td>
                        <td class="px-4 py-4 text-center">
                            <span class="px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(p.status)}">
                                ${formatStatus(p.status)}
                            </span>
                        </td>
                        <td class="px-4 py-4 text-center">
                            ${p.priority ? `<span class="px-2 py-1 rounded text-xs ${getPriorityColor(p.priority)}">${p.priority}</span>` : '-'}
                        </td>
                        <td class="px-4 py-4 text-right text-sm">
                            ${p.estimated_value ? '$' + p.estimated_value.toLocaleString() : '-'}
                        </td>
                        <td class="px-4 py-4 text-sm">
                            <div class="text-gray-900">${escapeHtml(p.next_action || '-')}</div>
                            ${p.next_action_date ? `<div class="text-xs text-gray-500">${new Date(p.next_action_date).toLocaleDateString()}</div>` : ''}
                        </td>
                        <td class="px-4 py-4 text-center space-x-2">
                            <button onclick="event.stopPropagation(); viewCompanyInfo(${p.inspection_id})" class="text-blue-600 hover:text-blue-800 text-sm font-medium">Company</button>
                            <button onclick="event.stopPropagation(); openProspectDetail(${p.id})" class="text-purple-600 hover:text-purple-800 text-sm font-medium">Prospect</button>
                        </td>
                    </tr>
                `).join('');
            } catch (e) {
                console.error('Error loading prospects:', e);
                document.getElementById('prospects-list').innerHTML =
                    '<tr><td colspan="7" class="px-4 py-8 text-center text-red-500">Error loading prospects</td></tr>';
            }
        }

        async function loadCallbacks() {
            try {
                const response = await fetch(`${CRM_API}/callbacks?status=pending`);
                const callbacks = await response.json();

                const tbody = document.getElementById('callbacks-list');
                if (!callbacks || callbacks.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="6" class="px-4 py-8 text-center text-gray-500">No pending callbacks</td></tr>';
                    return;
                }

                tbody.innerHTML = callbacks.map(c => {
                    const callbackDate = new Date(c.callback_date);
                    const isOverdue = callbackDate < new Date();
                    return `
                        <tr class="hover:bg-gray-50 border-b ${isOverdue ? 'bg-red-50' : ''}">
                            <td class="px-4 py-4">
                                <div class="font-medium ${isOverdue ? 'text-red-600' : 'text-gray-900'}">${callbackDate.toLocaleDateString()}</div>
                                <div class="text-xs text-gray-500">${callbackDate.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</div>
                            </td>
                            <td class="px-4 py-4 text-sm text-gray-900">${escapeHtml(c.estab_name || 'Unknown')}</td>
                            <td class="px-4 py-4 text-sm text-gray-600">${escapeHtml(c.callback_type || '-')}</td>
                            <td class="px-4 py-4 text-sm text-gray-600">${escapeHtml(c.notes || '-')}</td>
                            <td class="px-4 py-4 text-center">
                                <span class="px-2 py-1 rounded-full text-xs font-medium ${isOverdue ? 'bg-red-100 text-red-800' : 'bg-yellow-100 text-yellow-800'}">
                                    ${isOverdue ? 'Overdue' : 'Pending'}
                                </span>
                            </td>
                            <td class="px-4 py-4 text-center space-x-2">
                                <button onclick="completeCallback(${c.id})" class="text-green-600 hover:text-green-800 text-sm font-medium">Complete</button>
                                <button onclick="openProspectDetail(${c.prospect_id})" class="text-purple-600 hover:text-purple-800 text-sm font-medium">View</button>
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
                loadStats();
                loadAllCallbacks();
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

        function escapeHtml(text) {
            if (!text) return '';
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        function updateOutcomeOptions() {
            const activityType = document.getElementById('new-activity-type').value;
            const outcomeSelect = document.getElementById('new-activity-outcome');
            const options = outcomeOptions[activityType] || [];

            outcomeSelect.innerHTML = '<option value="">Select outcome...</option>' +
                options.map(opt => `<option value="${opt}">${opt}</option>`).join('') +
                '<option value="other">Other (type below)</option>';
        }

        async function openProspectDetail(prospectId) {
            currentProspectId = prospectId;
            document.getElementById('prospect-modal').classList.remove('hidden');

            try {
                const response = await fetch(`${CRM_API}/prospects/${prospectId}`);
                const prospect = await response.json();

                // Store inspection_id for viewing company info
                window.currentInspectionId = prospect.inspection_id;

                document.getElementById('prospect-title').textContent = prospect.estab_name || 'Prospect Details';
                document.getElementById('prospect-subtitle').textContent =
                    `${prospect.site_city || ''}${prospect.site_city && prospect.site_state ? ', ' : ''}${prospect.site_state || ''} | ${prospect.activity_nr || ''}`;

                document.getElementById('prospect-content').innerHTML = `
                    <!-- View Company Info Button -->
                    <div class="mb-4 pb-4 border-b">
                        <button onclick="viewCompanyInfo(${prospect.inspection_id})" class="bg-purple-600 text-white px-4 py-2 rounded hover:bg-purple-700 text-sm font-medium">
                            View Company Info
                        </button>
                        <span class="ml-2 text-sm text-gray-500">View enriched company details, contacts, and OSHA inspection info</span>
                    </div>

                    <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
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
                                <input type="text" id="prospect-next-action" value="${escapeHtml(prospect.next_action || '')}" placeholder="What's the next step?" class="w-full border rounded px-2 py-1.5 text-sm mb-2" onchange="updateProspect()">
                                <input type="date" id="prospect-next-date" value="${prospect.next_action_date || ''}" class="w-full border rounded px-2 py-1.5 text-sm" onchange="updateProspect()">
                            </div>

                            <div class="bg-gray-50 p-4 rounded-lg">
                                <h4 class="font-medium text-gray-700 mb-3">Notes</h4>
                                <textarea id="prospect-notes" rows="3" class="w-full border rounded px-2 py-1.5 text-sm" onchange="updateProspect()">${escapeHtml(prospect.notes || '')}</textarea>
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
                                <button onclick="scheduleCallback()" class="mt-2 bg-green-600 text-white px-4 py-2 rounded text-sm hover:bg-green-700">Schedule Callback</button>
                            </div>
                        </div>

                        <!-- Right: Activity Log -->
                        <div>
                            <div class="bg-gray-50 p-4 rounded-lg mb-4">
                                <h4 class="font-medium text-gray-700 mb-3">Log Activity</h4>
                                <div class="grid grid-cols-2 gap-2 mb-2">
                                    <select id="new-activity-type" class="border rounded px-2 py-1.5 text-sm" onchange="updateOutcomeOptions()">
                                        <option value="call">Call</option>
                                        <option value="email">Email</option>
                                        <option value="meeting">Meeting</option>
                                        <option value="note">Note</option>
                                        <option value="task">Task</option>
                                    </select>
                                    <input type="text" id="new-activity-subject" placeholder="Subject" class="border rounded px-2 py-1.5 text-sm">
                                </div>
                                <textarea id="new-activity-description" rows="2" placeholder="Description..." class="w-full border rounded px-2 py-1.5 text-sm mb-2"></textarea>
                                <label class="block text-xs text-gray-500 mb-1">Outcome</label>
                                <select id="new-activity-outcome" class="w-full border rounded px-2 py-1.5 text-sm mb-2" onchange="toggleCustomOutcome()">
                                    <option value="">Select outcome...</option>
                                    <option value="Connected - Interested">Connected - Interested</option>
                                    <option value="Connected - Not Interested">Connected - Not Interested</option>
                                    <option value="Connected - Call Back Later">Connected - Call Back Later</option>
                                    <option value="Left Voicemail">Left Voicemail</option>
                                    <option value="No Answer">No Answer</option>
                                    <option value="Wrong Number">Wrong Number</option>
                                    <option value="Busy">Busy</option>
                                    <option value="Sent to Voicemail">Sent to Voicemail</option>
                                    <option value="other">Other (type below)</option>
                                </select>
                                <input type="text" id="new-activity-custom-outcome" placeholder="Custom outcome..." class="w-full border rounded px-2 py-1.5 text-sm mb-2 hidden">
                                <button onclick="logActivity()" class="bg-blue-600 text-white px-4 py-2 rounded text-sm hover:bg-blue-700">Log Activity</button>
                            </div>

                            <h4 class="font-medium text-gray-700 mb-3">Activity History</h4>
                            <div id="activity-list" class="space-y-2 max-h-80 overflow-auto">
                                ${prospect.activities && prospect.activities.length > 0 ? prospect.activities.map(a => `
                                    <div class="bg-white border rounded p-3">
                                        <div class="flex justify-between items-start">
                                            <span class="px-2 py-0.5 rounded text-xs ${getActivityTypeColor(a.activity_type)}">${a.activity_type}</span>
                                            <span class="text-xs text-gray-500">${new Date(a.activity_date).toLocaleString()}</span>
                                        </div>
                                        ${a.subject ? `<div class="font-medium text-sm mt-1">${escapeHtml(a.subject)}</div>` : ''}
                                        ${a.description ? `<div class="text-sm text-gray-600 mt-1">${escapeHtml(a.description)}</div>` : ''}
                                        ${a.outcome ? `<div class="text-sm text-green-600 mt-1">Outcome: ${escapeHtml(a.outcome)}</div>` : ''}
                                    </div>
                                `).join('') : '<div class="text-gray-500 text-sm">No activities yet</div>'}
                            </div>
                        </div>
                    </div>
                `;

                // Initialize outcome options for the default activity type
                updateOutcomeOptions();
            } catch (e) {
                console.error('Error loading prospect:', e);
                document.getElementById('prospect-content').innerHTML =
                    '<div class="text-red-500">Error loading prospect details</div>';
            }
        }

        function toggleCustomOutcome() {
            const outcomeSelect = document.getElementById('new-activity-outcome');
            const customInput = document.getElementById('new-activity-custom-outcome');
            if (outcomeSelect.value === 'other') {
                customInput.classList.remove('hidden');
                customInput.focus();
            } else {
                customInput.classList.add('hidden');
                customInput.value = '';
            }
        }

        function closeProspectModal() {
            document.getElementById('prospect-modal').classList.add('hidden');
            currentProspectId = null;
        }

        // Close modal on backdrop click
        document.getElementById('prospect-modal').addEventListener('click', e => {
            if (e.target.id === 'prospect-modal') closeProspectModal();
        });

        // Close on escape
        document.addEventListener('keydown', e => {
            if (e.key === 'Escape') closeProspectModal();
        });

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
                loadStats();
                loadProspects();
            } catch (e) {
                console.error('Error updating prospect:', e);
            }
        }

        async function logActivity() {
            if (!currentProspectId) return;

            const outcomeSelect = document.getElementById('new-activity-outcome');
            const customOutcome = document.getElementById('new-activity-custom-outcome');
            let outcome = outcomeSelect.value;
            if (outcome === 'other') {
                outcome = customOutcome.value;
            }

            const data = {
                activity_type: document.getElementById('new-activity-type').value,
                subject: document.getElementById('new-activity-subject').value || null,
                description: document.getElementById('new-activity-description').value || null,
                outcome: outcome || null
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
                document.getElementById('new-activity-custom-outcome').value = '';
                document.getElementById('new-activity-custom-outcome').classList.add('hidden');
                // Reload prospect detail and activity summary
                openProspectDetail(currentProspectId);
                loadActivitySummary();
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
                loadStats();
                loadAllCallbacks();
                alert('Callback scheduled!');
            } catch (e) {
                console.error('Error scheduling callback:', e);
            }
        }

        // View Company Info function
        async function viewCompanyInfo(inspectionId) {
            // Show company info modal
            document.getElementById('company-info-modal').classList.remove('hidden');
            document.getElementById('company-info-content').innerHTML = '<div class="text-center py-8 text-gray-500">Loading company information...</div>';

            try {
                // Fetch inspection details
                const inspectionResponse = await fetch(`/api/inspections/${inspectionId}`);
                const inspection = await inspectionResponse.json();

                // Fetch company details (linked to inspection) - includes contacts
                const companyResponse = await fetch(`/api/inspections/${inspectionId}/company`);
                let company = null;
                let contacts = [];
                if (companyResponse.ok) {
                    company = await companyResponse.json();
                    // Contacts are included in the company response
                    contacts = company?.contacts || [];
                }

                // Build the modal content
                let html = '<div class="space-y-6">';

                // OSHA Inspection Info
                html += `
                    <div class="bg-red-50 border border-red-200 rounded-lg p-4">
                        <h4 class="font-semibold text-red-800 mb-3">OSHA Inspection Details</h4>
                        <div class="grid grid-cols-2 gap-4 text-sm">
                            <div>
                                <span class="text-gray-600">Establishment:</span>
                                <span class="font-medium ml-2">${escapeHtml(inspection.estab_name || 'N/A')}</span>
                            </div>
                            <div>
                                <span class="text-gray-600">Activity #:</span>
                                <span class="font-medium ml-2">${escapeHtml(inspection.activity_nr || 'N/A')}</span>
                            </div>
                            <div>
                                <span class="text-gray-600">Location:</span>
                                <span class="font-medium ml-2">${escapeHtml(inspection.site_city || '')}${inspection.site_city && inspection.site_state ? ', ' : ''}${escapeHtml(inspection.site_state || '')}</span>
                            </div>
                            <div>
                                <span class="text-gray-600">Address:</span>
                                <span class="font-medium ml-2">${escapeHtml(inspection.site_address || 'N/A')}</span>
                            </div>
                            <div>
                                <span class="text-gray-600">Open Date:</span>
                                <span class="font-medium ml-2">${inspection.open_date ? new Date(inspection.open_date).toLocaleDateString() : 'N/A'}</span>
                            </div>
                            <div>
                                <span class="text-gray-600">Total Penalty:</span>
                                <span class="font-medium ml-2 text-red-600">$${(inspection.total_current_penalty || 0).toLocaleString()}</span>
                            </div>
                        </div>
                    </div>
                `;

                // Company Info (if enriched)
                if (company) {
                    html += `
                        <div class="bg-blue-50 border border-blue-200 rounded-lg p-4">
                            <h4 class="font-semibold text-blue-800 mb-3">Enriched Company Data</h4>
                            <div class="grid grid-cols-2 gap-4 text-sm">
                                <div>
                                    <span class="text-gray-600">Company Name:</span>
                                    <span class="font-medium ml-2">${escapeHtml(company.name || 'N/A')}</span>
                                </div>
                                <div>
                                    <span class="text-gray-600">Domain:</span>
                                    ${company.domain ? `<a href="https://${company.domain}" target="_blank" class="font-medium ml-2 text-blue-600 hover:underline">${escapeHtml(company.domain)}</a>` : '<span class="ml-2 text-gray-400">N/A</span>'}
                                </div>
                                <div>
                                    <span class="text-gray-600">Industry:</span>
                                    <span class="font-medium ml-2">${escapeHtml(company.industry || 'N/A')}</span>
                                </div>
                                <div>
                                    <span class="text-gray-600">Sub-Industry:</span>
                                    <span class="font-medium ml-2">${escapeHtml(company.sub_industry || 'N/A')}</span>
                                </div>
                                <div>
                                    <span class="text-gray-600">Employees:</span>
                                    <span class="font-medium ml-2">${company.employee_count ? company.employee_count.toLocaleString() : (company.employee_range || 'N/A')}</span>
                                </div>
                                <div>
                                    <span class="text-gray-600">Revenue:</span>
                                    <span class="font-medium ml-2">${company.revenue_range || (company.annual_revenue ? '$' + company.annual_revenue.toLocaleString() : 'N/A')}</span>
                                </div>
                                <div>
                                    <span class="text-gray-600">Phone:</span>
                                    ${company.phone ? `<a href="tel:${company.phone}" class="font-medium ml-2 text-blue-600">${escapeHtml(company.phone)}</a>` : '<span class="ml-2 text-gray-400">N/A</span>'}
                                </div>
                                <div>
                                    <span class="text-gray-600">LinkedIn:</span>
                                    ${company.linkedin_url ? `<a href="${company.linkedin_url}" target="_blank" class="font-medium ml-2 text-blue-600 hover:underline">View Profile</a>` : '<span class="ml-2 text-gray-400">N/A</span>'}
                                </div>
                            </div>
                        </div>
                    `;
                } else {
                    html += `
                        <div class="bg-gray-50 border border-gray-200 rounded-lg p-4">
                            <h4 class="font-semibold text-gray-700 mb-2">Company Not Enriched</h4>
                            <p class="text-sm text-gray-600">This company has not been enriched with Apollo data yet. Go to the OSHA dashboard to enrich this company.</p>
                        </div>
                    `;
                }

                // Contacts (if any)
                if (contacts && contacts.length > 0) {
                    html += `
                        <div class="bg-green-50 border border-green-200 rounded-lg p-4">
                            <h4 class="font-semibold text-green-800 mb-3">Contacts (${contacts.length})</h4>
                            <div class="space-y-3">
                    `;
                    for (const contact of contacts) {
                        html += `
                            <div class="bg-white rounded border p-3">
                                <div class="flex justify-between items-start">
                                    <div>
                                        <div class="font-medium">${escapeHtml(contact.full_name || (contact.first_name + ' ' + contact.last_name) || 'Unknown')}</div>
                                        <div class="text-sm text-gray-600">${escapeHtml(contact.title || 'N/A')}</div>
                                    </div>
                                    <span class="px-2 py-0.5 text-xs rounded ${contact.contact_type === 'safety' ? 'bg-orange-100 text-orange-800' : 'bg-purple-100 text-purple-800'}">${contact.contact_type || 'other'}</span>
                                </div>
                                <div class="mt-2 grid grid-cols-2 gap-2 text-sm">
                                    <div>
                                        <span class="text-gray-500">Email:</span>
                                        ${contact.email ? `<a href="mailto:${contact.email}" class="text-blue-600 hover:underline ml-1">${escapeHtml(contact.email)}</a>` : '<span class="text-gray-400 ml-1">N/A</span>'}
                                    </div>
                                    <div>
                                        <span class="text-gray-500">Phone:</span>
                                        ${contact.phone ? `<a href="tel:${contact.phone}" class="text-blue-600 ml-1">${escapeHtml(contact.phone)}</a>` : '<span class="text-gray-400 ml-1">N/A</span>'}
                                    </div>
                                    ${contact.linkedin_url ? `
                                        <div class="col-span-2">
                                            <a href="${contact.linkedin_url}" target="_blank" class="text-blue-600 hover:underline text-sm">View LinkedIn Profile</a>
                                        </div>
                                    ` : ''}
                                </div>
                            </div>
                        `;
                    }
                    html += '</div></div>';
                } else if (company) {
                    html += `
                        <div class="bg-gray-50 border border-gray-200 rounded-lg p-4">
                            <h4 class="font-semibold text-gray-700 mb-2">No Contacts Found</h4>
                            <p class="text-sm text-gray-600">No contacts have been saved for this company yet.</p>
                        </div>
                    `;
                }

                html += '</div>';

                document.getElementById('company-info-content').innerHTML = html;
            } catch (e) {
                console.error('Error loading company info:', e);
                document.getElementById('company-info-content').innerHTML = '<div class="text-red-500 text-center py-8">Error loading company information</div>';
            }
        }

        function closeCompanyInfoModal() {
            document.getElementById('company-info-modal').classList.add('hidden');
        }

        // Close company info modal on backdrop click
        document.getElementById('company-info-modal')?.addEventListener('click', e => {
            if (e.target.id === 'company-info-modal') closeCompanyInfoModal();
        });
    </script>

    <div id="sync-widget" class="fixed bottom-4 right-4 z-50 w-96 bg-white border border-gray-200 rounded-lg shadow-lg">
        <div class="flex items-center justify-between px-3 py-2 border-b bg-gray-50">
            <span class="text-xs font-semibold text-gray-800">Sync Status</span>
            <button id="sync-widget-toggle" class="text-xs text-blue-600 hover:text-blue-800">Hide</button>
        </div>
        <div id="sync-widget-body" class="px-3 py-2 space-y-3">
            <div>
                <div class="flex items-center gap-1 text-[10px] font-semibold text-gray-700 mb-1">
                    <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                    Automatic (Cron)
                </div>
                <div id="sync-widget-cron" class="text-[10px] text-gray-600 space-y-1">Loading...</div>
            </div>
            <div>
                <div class="flex items-center gap-1 text-[10px] font-semibold text-gray-700 mb-1">
                    <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 15l-2 5L9 9l11 4-5 2zm0 0l5 5M7.188 2.239l.777 2.897M5.136 7.965l-2.898-.777M13.95 4.05l-2.122 2.122m-5.657 5.656l-2.12 2.122"></path></svg>
                    Manual
                </div>
                <div id="sync-widget-manual" class="text-[10px] text-gray-600 space-y-1">No manual syncs yet</div>
            </div>
            <div class="pt-1 border-t border-gray-100">
                <a href="/api/inspections/cron/status?format=html" target="_blank" class="text-[10px] text-blue-600 hover:text-blue-800">View full sync history →</a>
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

            function getAddedCount(label, details) {
                if (!details) return 'n/a';
                if (label === 'Inspections') return details.new_inspections_added ?? 0;
                if (label === 'Violations') return details.new_violations_found ?? 0;
                if (label === 'EPA') return details.new ?? 0;
                return 'n/a';
            }

            function statusColor(status) {
                if (status === 'success') return 'text-green-600';
                if (status === 'failed') return 'text-red-600';
                if (status === 'running') return 'text-yellow-600';
                return 'text-gray-600';
            }

            function formatLine(label, run) {
                if (!run) return `<div>${label}: <span class="text-gray-400">n/a</span></div>`;
                const status = run.status || 'unknown';
                const end = formatTime(run.finished_at);
                const details = parseDetails(run.details);
                const added = getAddedCount(label, details);
                return `<div>${label}: <span class="${statusColor(status)}">${status}</span> | ${end} | added ${added}</div>`;
            }

            function getLatestRunId(latest) {
                const ids = Object.values(latest || {}).map(entry => entry?.id || 0);
                return ids.length ? Math.max(...ids) : 0;
            }

            function renderSyncStatus(latest) {
                cronContent.innerHTML = [
                    formatLine('Inspections', latest.inspections),
                    formatLine('Violations', latest['violations-bulk']),
                    formatLine('EPA', latest.epa),
                ].join('');
            }

            // Expose manual sync status update function
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

            async function loadSyncWidget() {
                try {
                    const response = await fetch('/api/inspections/cron/status');
                    if (response.status === 401) {
                        cronContent.textContent = 'Sync status unavailable (unauthorized).';
                        return false;
                    }
                    if (!response.ok) {
                        cronContent.textContent = 'Sync status unavailable.';
                        return false;
                    }

                    const data = await response.json();
                    const latest = data.latest || {};
                    renderSyncStatus(latest);
                    lastRunId = getLatestRunId(latest);
                    return true;
                } catch (e) {
                    cronContent.textContent = 'Sync status unavailable.';
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
                            renderSyncStatus(payload.latest);
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

            loadSavedManualStatus();
            loadSyncWidget().then((ok) => {
                if (ok) startSyncStream();
            });
        })();
    </script>

</body>
</html>
"""

