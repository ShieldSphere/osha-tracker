"""Main Dashboard - Overview of all TSG Safety data sources."""
from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def main_dashboard():
    """Serve the main dashboard overview page."""
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TSG Safety - Compliance Tracker</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        .card-hover { transition: all 0.2s ease; }
        .card-hover:hover { transform: translateY(-2px); box-shadow: 0 8px 25px rgba(0,0,0,0.15); }
        .gradient-osha { background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%); }
        .gradient-epa { background: linear-gradient(135deg, #10b981 0%, #059669 100%); }
        .gradient-crm { background: linear-gradient(135deg, #8b5cf6 0%, #6d28d9 100%); }
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
                        <a href="/" class="px-4 py-2 rounded-md text-sm font-medium bg-gray-700 text-white">Overview</a>
                        <a href="/osha" class="px-4 py-2 rounded-md text-sm font-medium text-gray-300 hover:text-white hover:bg-gray-700">OSHA</a>
                        <a href="/epa" class="px-4 py-2 rounded-md text-sm font-medium text-gray-300 hover:text-white hover:bg-gray-700">EPA</a>
                        <a href="/crm" class="px-4 py-2 rounded-md text-sm font-medium text-gray-300 hover:text-white hover:bg-gray-700">CRM</a>
                    </div>
                </div>
                <div class="flex items-center gap-4">
                    <span id="last-sync" class="text-sm text-gray-400"></span>
                </div>
            </div>
        </div>
    </nav>

    <main class="max-w-7xl mx-auto px-4 py-8">
        <!-- Header -->
        <div class="mb-8">
            <h2 class="text-3xl font-bold text-gray-800">Compliance Overview</h2>
            <p class="text-gray-600 mt-2">Monitor OSHA inspections, EPA enforcement cases, and sales pipeline</p>
        </div>

        <!-- Quick Stats Row -->
        <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
            <div class="bg-white rounded-lg shadow p-4">
                <p class="text-xs text-gray-500 uppercase tracking-wider">Total Records</p>
                <p id="stat-total-records" class="text-2xl font-bold text-gray-800">-</p>
                <p class="text-xs text-gray-500 mt-1">OSHA + EPA combined</p>
            </div>
            <div class="bg-white rounded-lg shadow p-4">
                <p class="text-xs text-gray-500 uppercase tracking-wider">Total Penalties</p>
                <p id="stat-total-penalties" class="text-2xl font-bold text-red-600">-</p>
                <p class="text-xs text-gray-500 mt-1">All enforcement actions</p>
            </div>
            <div class="bg-white rounded-lg shadow p-4">
                <p class="text-xs text-gray-500 uppercase tracking-wider">States Covered</p>
                <p id="stat-states-covered" class="text-2xl font-bold text-green-600">-</p>
                <p class="text-xs text-gray-500 mt-1">Geographic reach</p>
            </div>
            <div class="bg-white rounded-lg shadow p-4">
                <p class="text-xs text-gray-500 uppercase tracking-wider">CRM Pipeline</p>
                <p id="stat-pipeline-value" class="text-2xl font-bold text-purple-600">-</p>
                <p class="text-xs text-gray-500 mt-1">Potential revenue</p>
            </div>
        </div>

        <!-- Main Cards Grid -->
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
            <!-- OSHA Card -->
            <a href="/osha" class="card-hover">
                <div class="gradient-osha rounded-xl shadow-lg overflow-hidden">
                    <div class="p-6 text-white">
                        <div class="flex items-center justify-between mb-4">
                            <h3 class="text-xl font-bold">OSHA Inspections</h3>
                            <svg class="w-8 h-8 opacity-80" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"></path>
                            </svg>
                        </div>
                        <div class="space-y-3">
                            <div class="flex justify-between items-center">
                                <span class="text-blue-100">Total Inspections</span>
                                <span id="osha-total" class="text-2xl font-bold">-</span>
                            </div>
                            <div class="flex justify-between items-center">
                                <span class="text-blue-100">Total Penalties</span>
                                <span id="osha-penalties" class="text-lg font-semibold">-</span>
                            </div>
                            <div class="flex justify-between items-center">
                                <span class="text-blue-100">New (7 days)</span>
                                <span id="osha-new" class="text-lg font-semibold">-</span>
                            </div>
                        </div>
                        <div class="mt-4 pt-4 border-t border-blue-400 border-opacity-30">
                            <div class="flex items-center text-blue-100 text-sm">
                                <span>View OSHA Dashboard</span>
                                <svg class="w-4 h-4 ml-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path>
                                </svg>
                            </div>
                        </div>
                    </div>
                </div>
            </a>

            <!-- EPA Card -->
            <a href="/epa" class="card-hover">
                <div class="gradient-epa rounded-xl shadow-lg overflow-hidden">
                    <div class="p-6 text-white">
                        <div class="flex items-center justify-between mb-4">
                            <h3 class="text-xl font-bold">EPA Enforcement</h3>
                            <svg class="w-8 h-8 opacity-80" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 104 0 2 2 0 012-2h1.064M15 20.488V18a2 2 0 012-2h3.064M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                            </svg>
                        </div>
                        <div class="space-y-3">
                            <div class="flex justify-between items-center">
                                <span class="text-green-100">Total Cases</span>
                                <span id="epa-total" class="text-2xl font-bold">-</span>
                            </div>
                            <div class="flex justify-between items-center">
                                <span class="text-green-100">Total Penalties</span>
                                <span id="epa-penalties" class="text-lg font-semibold">-</span>
                            </div>
                            <div class="flex justify-between items-center">
                                <span class="text-green-100">Active Cases</span>
                                <span id="epa-active" class="text-lg font-semibold">-</span>
                            </div>
                        </div>
                        <div class="mt-4 pt-4 border-t border-green-400 border-opacity-30">
                            <div class="flex items-center text-green-100 text-sm">
                                <span>View EPA Dashboard</span>
                                <svg class="w-4 h-4 ml-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path>
                                </svg>
                            </div>
                        </div>
                    </div>
                </div>
            </a>

            <!-- CRM Card -->
            <a href="/crm" class="card-hover">
                <div class="gradient-crm rounded-xl shadow-lg overflow-hidden">
                    <div class="p-6 text-white">
                        <div class="flex items-center justify-between mb-4">
                            <h3 class="text-xl font-bold">Sales Pipeline</h3>
                            <svg class="w-8 h-8 opacity-80" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"></path>
                            </svg>
                        </div>
                        <div class="space-y-3">
                            <div class="flex justify-between items-center">
                                <span class="text-purple-100">Total Prospects</span>
                                <span id="crm-total" class="text-2xl font-bold">-</span>
                            </div>
                            <div class="flex justify-between items-center">
                                <span class="text-purple-100">Pipeline Value</span>
                                <span id="crm-value" class="text-lg font-semibold">-</span>
                            </div>
                            <div class="flex justify-between items-center">
                                <span class="text-purple-100">Upcoming Callbacks</span>
                                <span id="crm-callbacks" class="text-lg font-semibold">-</span>
                            </div>
                        </div>
                        <div class="mt-4 pt-4 border-t border-purple-400 border-opacity-30">
                            <div class="flex items-center text-purple-100 text-sm">
                                <span>View CRM Dashboard</span>
                                <svg class="w-4 h-4 ml-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path>
                                </svg>
                            </div>
                        </div>
                    </div>
                </div>
            </a>
        </div>

        <!-- Charts Section -->
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
            <!-- Penalties by Source Chart -->
            <div class="bg-white rounded-lg shadow p-6">
                <h3 class="text-lg font-semibold text-gray-800 mb-4">Penalties by Source</h3>
                <div style="height: 200px; position: relative;">
                    <canvas id="penalties-chart"></canvas>
                </div>
            </div>

            <!-- Records Timeline Chart -->
            <div class="bg-white rounded-lg shadow p-6">
                <h3 class="text-lg font-semibold text-gray-800 mb-4">Monthly Activity</h3>
                <div style="height: 200px; position: relative;">
                    <canvas id="timeline-chart"></canvas>
                </div>
            </div>
        </div>

        <!-- Recent Activity Section -->
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <!-- Recent OSHA Inspections -->
            <div class="bg-white rounded-lg shadow">
                <div class="p-4 border-b flex justify-between items-center">
                    <h3 class="font-semibold text-gray-800">Recent OSHA Inspections</h3>
                    <a href="/osha" class="text-blue-600 hover:text-blue-800 text-sm">View All</a>
                </div>
                <div id="recent-osha" class="divide-y">
                    <div class="p-4 text-center text-gray-500">Loading...</div>
                </div>
            </div>

            <!-- Recent EPA Cases -->
            <div class="bg-white rounded-lg shadow">
                <div class="p-4 border-b flex justify-between items-center">
                    <h3 class="font-semibold text-gray-800">Recent EPA Cases</h3>
                    <a href="/epa" class="text-green-600 hover:text-green-800 text-sm">View All</a>
                </div>
                <div id="recent-epa" class="divide-y">
                    <div class="p-4 text-center text-gray-500">Coming soon...</div>
                </div>
            </div>
        </div>

        <!-- CRM Quick Actions -->
        <div class="mt-6 bg-white rounded-lg shadow p-6">
            <div class="flex justify-between items-center mb-4">
                <h3 class="font-semibold text-gray-800">CRM Quick Actions</h3>
                <a href="/crm" class="text-purple-600 hover:text-purple-800 text-sm">Open CRM</a>
            </div>
            <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div class="bg-blue-50 rounded-lg p-4 text-center">
                    <p class="text-2xl font-bold text-blue-600" id="crm-new-leads">-</p>
                    <p class="text-sm text-gray-600">New Leads</p>
                </div>
                <div class="bg-yellow-50 rounded-lg p-4 text-center">
                    <p class="text-2xl font-bold text-yellow-600" id="crm-contacted">-</p>
                    <p class="text-sm text-gray-600">Contacted</p>
                </div>
                <div class="bg-green-50 rounded-lg p-4 text-center">
                    <p class="text-2xl font-bold text-green-600" id="crm-qualified">-</p>
                    <p class="text-sm text-gray-600">Qualified</p>
                </div>
                <div class="bg-purple-50 rounded-lg p-4 text-center">
                    <p class="text-2xl font-bold text-purple-600" id="crm-won">-</p>
                    <p class="text-sm text-gray-600">Won</p>
                </div>
            </div>
        </div>
    </main>

    <script>
        let penaltiesChart = null;
        let timelineChart = null;

        document.addEventListener('DOMContentLoaded', () => {
            loadOSHAStats();
            loadEPAStats();
            loadCRMStats();
            loadRecentOSHA();
            loadRecentEPA();
            initCharts();
        });

        async function loadOSHAStats() {
            try {
                const response = await fetch('/api/inspections/stats');
                oshaStats = await response.json();

                document.getElementById('osha-total').textContent = (oshaStats.total_inspections || 0).toLocaleString();
                document.getElementById('osha-penalties').textContent = '$' + (oshaStats.total_penalties || 0).toLocaleString();

                // Calculate new inspections (last 7 days)
                const recentResponse = await fetch('/api/inspections/recent?days=7');
                const recentData = await recentResponse.json();
                document.getElementById('osha-new').textContent = (recentData.count || 0).toLocaleString();

                // Update states count
                document.getElementById('stat-states-covered').textContent = oshaStats.states_count || 0;

                // Update combined stats
                updateCombinedStats();
            } catch (e) {
                console.error('Error loading OSHA stats:', e);
            }
        }

        async function loadCRMStats() {
            try {
                const response = await fetch('/api/crm/stats');
                const stats = await response.json();

                document.getElementById('crm-total').textContent = stats.total_prospects || 0;
                document.getElementById('crm-value').textContent = '$' + (stats.total_pipeline_value || 0).toLocaleString();
                document.getElementById('crm-callbacks').textContent = stats.upcoming_callbacks || 0;
                document.getElementById('stat-pipeline-value').textContent = '$' + (stats.total_pipeline_value || 0).toLocaleString();

                // Pipeline breakdown
                document.getElementById('crm-new-leads').textContent = stats.by_status?.new_lead || 0;
                document.getElementById('crm-contacted').textContent = stats.by_status?.contacted || 0;
                document.getElementById('crm-qualified').textContent = stats.by_status?.qualified || 0;
                document.getElementById('crm-won').textContent = stats.by_status?.won || 0;
            } catch (e) {
                console.error('Error loading CRM stats:', e);
            }
        }

        async function loadRecentOSHA() {
            try {
                // Use the dedicated recent inspections endpoint
                const response = await fetch('/api/inspections/recent?days=30');
                const data = await response.json();

                const container = document.getElementById('recent-osha');
                if (!data.items || data.items.length === 0) {
                    container.innerHTML = '<div class="p-4 text-center text-gray-500">No recent inspections</div>';
                    return;
                }

                container.innerHTML = data.items.slice(0, 5).map(item => `
                    <div class="p-3 hover:bg-gray-50">
                        <div class="flex justify-between items-start">
                            <div class="min-w-0 flex-1">
                                <p class="font-medium text-gray-900 truncate">${escapeHtml(item.estab_name || 'Unknown')}</p>
                                <p class="text-sm text-gray-500">${escapeHtml(item.site_city || '')}${item.site_city && item.site_state ? ', ' : ''}${escapeHtml(item.site_state || '')}</p>
                            </div>
                            <div class="text-right ml-4">
                                ${item.total_current_penalty > 0 ? `<p class="text-sm font-medium text-red-600">$${item.total_current_penalty.toLocaleString()}</p>` : ''}
                                <p class="text-xs text-gray-500">${item.open_date ? new Date(item.open_date).toLocaleDateString() : ''}</p>
                            </div>
                        </div>
                    </div>
                `).join('');
            } catch (e) {
                console.error('Error loading recent OSHA:', e);
            }
        }

        let oshaStats = null;
        let epaStats = null;

        async function loadEPAStats() {
            try {
                const response = await fetch('/api/epa/stats');
                epaStats = await response.json();

                document.getElementById('epa-total').textContent = (epaStats.total_cases || 0).toLocaleString();
                document.getElementById('epa-penalties').textContent = '$' + (epaStats.total_penalties || 0).toLocaleString(undefined, {maximumFractionDigits: 0});
                document.getElementById('epa-active').textContent = epaStats.recent_cases || 0;

                // Update combined stats
                updateCombinedStats();
            } catch (e) {
                console.error('Error loading EPA stats:', e);
                document.getElementById('epa-total').textContent = '0';
                document.getElementById('epa-penalties').textContent = '$0';
                document.getElementById('epa-active').textContent = '0';
            }
        }

        async function loadRecentEPA() {
            try {
                const response = await fetch('/api/epa/recent?days=30');
                const data = await response.json();

                const container = document.getElementById('recent-epa');
                if (!data.items || data.items.length === 0) {
                    container.innerHTML = '<div class="p-4 text-center text-gray-500">No recent EPA cases. Click "Sync EPA Data" on the EPA page.</div>';
                    return;
                }

                container.innerHTML = data.items.slice(0, 5).map(item => `
                    <div class="p-3 hover:bg-gray-50">
                        <div class="flex justify-between items-start">
                            <div class="min-w-0 flex-1">
                                <p class="font-medium text-gray-900 truncate">${escapeHtml(item.case_name || item.facility_name || 'Unknown')}</p>
                                <p class="text-sm text-gray-500">${escapeHtml(item.facility_city || '')}${item.facility_city && item.facility_state ? ', ' : ''}${item.facility_state || ''}</p>
                            </div>
                            <div class="text-right ml-4">
                                ${item.fed_penalty > 0 ? `<p class="text-sm font-medium text-red-600">$${item.fed_penalty.toLocaleString()}</p>` : ''}
                                <p class="text-xs text-gray-500">${item.date_filed ? new Date(item.date_filed).toLocaleDateString() : ''}</p>
                            </div>
                        </div>
                    </div>
                `).join('');
            } catch (e) {
                console.error('Error loading recent EPA:', e);
                document.getElementById('recent-epa').innerHTML = '<div class="p-4 text-center text-gray-500">Error loading EPA data</div>';
            }
        }

        function updateCombinedStats() {
            const oshaRecords = oshaStats?.total_inspections || 0;
            const epaRecords = epaStats?.total_cases || 0;
            const oshaPenalties = oshaStats?.total_penalties || 0;
            const epaPenalties = epaStats?.total_penalties || 0;

            document.getElementById('stat-total-records').textContent = (oshaRecords + epaRecords).toLocaleString();
            document.getElementById('stat-total-penalties').textContent = '$' + (oshaPenalties + epaPenalties).toLocaleString(undefined, {maximumFractionDigits: 0});

            // Update charts
            updatePenaltiesChart(oshaPenalties, epaPenalties);
            updateTimelineChart(oshaRecords, epaRecords);
        }

        function initCharts() {
            // Penalties by Source Chart
            const penaltiesCtx = document.getElementById('penalties-chart').getContext('2d');
            penaltiesChart = new Chart(penaltiesCtx, {
                type: 'doughnut',
                data: {
                    labels: ['OSHA', 'EPA'],
                    datasets: [{
                        data: [0, 0],
                        backgroundColor: ['#3b82f6', '#10b981'],
                        borderWidth: 0
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'bottom'
                        }
                    }
                }
            });

            // Timeline Chart
            const timelineCtx = document.getElementById('timeline-chart').getContext('2d');
            timelineChart = new Chart(timelineCtx, {
                type: 'bar',
                data: {
                    labels: ['OSHA', 'EPA'],
                    datasets: [{
                        label: 'Records',
                        data: [0, 0],
                        backgroundColor: ['#3b82f6', '#10b981']
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false }
                    },
                    scales: {
                        y: { beginAtZero: true }
                    }
                }
            });
        }

        function updatePenaltiesChart(oshaTotal, epaTotal) {
            if (penaltiesChart) {
                penaltiesChart.data.datasets[0].data = [oshaTotal, epaTotal];
                penaltiesChart.update();
            }
        }

        function updateTimelineChart(oshaRecords, epaRecords) {
            if (timelineChart) {
                timelineChart.data.datasets[0].data = [oshaRecords, epaRecords];
                timelineChart.update();
            }
        }

        function escapeHtml(text) {
            if (!text) return '';
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
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
                <a href="/api/inspections/cron/status" target="_blank" class="text-[10px] text-blue-600 hover:text-blue-800">View full sync history →</a>
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
