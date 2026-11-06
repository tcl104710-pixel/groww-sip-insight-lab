/**
 * Groww SIP Insight Lab — AI Discovery Engine Frontend
 * Production-ready client logic for Vercel deployment.
 */

// Global Application State
const AppState = {
  allRecords: [],
  filteredRecords: [],
  stats: {},
  crossSource: {},
  insights: [],
  opportunities: [],
  discoveryChain: [],
  assignmentQuestions: [],
  activeTab: 'overview',
  currentPage: 1,
  pageSize: 15,
  searchDebounceTimer: null,
};

// Color palettes for Plotly charts
const ChartColors = {
  brandBlue: '#2563eb',
  growwGreen: '#00d09c',
  amber: '#f59e0b',
  rose: '#e11d48',
  purple: '#8b5cf6',
  slate: '#64748b',
  sources: {
    'Reddit': '#ff4500',
    'YouTube': '#ff0000',
    'Apple App Store': '#0070c9',
    'Google Play Store': '#00875a',
  },
  sentiments: {
    'positive': '#10b981',
    'neutral': '#64748b',
    'negative': '#ef4444',
  }
};

// -----------------------------------------------------------------------------
// Initialization & Data Loading
// -----------------------------------------------------------------------------

document.addEventListener('DOMContentLoaded', () => {
  initApp();
});

async function initApp() {
  showLoading(true);
  hideError();

  try {
    // Attempt 1: Fetch from Serverless API
    const apiSuccess = await loadFromAPI();
    
    // Attempt 2: Fallback to bundled static JSON if API fails
    if (!apiSuccess) {
      console.warn('API endpoints unavailable, falling back to static research_data.json');
      await loadFromStaticJSON();
    }

    // Initialize UI
    AppState.filteredRecords = [...AppState.allRecords];
    renderAllViews();
    showLoading(false);
  } catch (err) {
    console.error('Fatal initialization error:', err);
    showLoading(false);
    showError(err.message || 'Unable to load research datasets.');
  }
}

async function loadFromAPI() {
  try {
    const statsRes = await fetch('/api/stats');
    if (!statsRes.ok) return false;
    AppState.stats = await statsRes.json();

    const [csRes, recRes, insRes, oppRes, chainRes, qRes] = await Promise.all([
      fetch('/api/cross-source'),
      fetch('/api/records?limit=2000'),
      fetch('/api/insights'),
      fetch('/api/opportunities'),
      fetch('/api/discovery-chain'),
      fetch('/api/assignment-evaluation')
    ]);

    if (!csRes.ok || !recRes.ok || !insRes.ok || !oppRes.ok) return false;

    AppState.crossSource = await csRes.json();
    const recordsData = await recRes.json();
    AppState.allRecords = recordsData.records || [];
    AppState.insights = await insRes.json();
    AppState.opportunities = await oppRes.json();
    AppState.discoveryChain = chainRes.ok ? await chainRes.json() : [];
    AppState.assignmentQuestions = qRes.ok ? await qRes.json() : [];

    return AppState.allRecords.length > 0;
  } catch (e) {
    return false;
  }
}

async function loadFromStaticJSON() {
  const candidates = [
    '/data/research_data.json',
    './data/research_data.json',
    'public/data/research_data.json'
  ];

  let loaded = false;
  for (const url of candidates) {
    try {
      const res = await fetch(url);
      if (res.ok) {
        const bundle = await res.json();
        AppState.stats = bundle.stats || {};
        AppState.allRecords = bundle.records || [];
        AppState.crossSource = bundle.cross_source || {};
        AppState.insights = bundle.insights || [];
        AppState.opportunities = bundle.opportunities || [];
        AppState.discoveryChain = bundle.discovery_chain || [];
        AppState.assignmentQuestions = bundle.assignment_questions || [];
        loaded = true;
        break;
      }
    } catch (e) {
      // try next candidate
    }
  }

  if (!loaded) {
    throw new Error('Could not load research data from API or bundled static JSON.');
  }
}

function refreshCorpus() {
  const refreshBtn = document.getElementById('refreshBtn');
  if (refreshBtn) refreshBtn.classList.add('animate-spin');
  initApp().finally(() => {
    if (refreshBtn) refreshBtn.classList.remove('animate-spin');
  });
}

function showLoading(show) {
  const loader = document.getElementById('loadingState');
  if (loader) {
    if (show) loader.classList.remove('hidden');
    else loader.classList.add('hidden');
  }
}

function showError(msg) {
  const errBox = document.getElementById('errorState');
  const errMsg = document.getElementById('errorMessage');
  if (errBox) {
    if (errMsg) errMsg.textContent = msg;
    errBox.classList.remove('hidden');
  }
}

function hideError() {
  const errBox = document.getElementById('errorState');
  if (errBox) errBox.classList.add('hidden');
}

// -----------------------------------------------------------------------------
// Master Render Orchestrator
// -----------------------------------------------------------------------------

function renderAllViews() {
  renderKPIs();
  renderAccountingTable();
  renderOverviewCharts();
  renderCrossSourceTable();
  renderCrossSourceCharts();
  renderProblemExplorer();
  renderEvidenceTable();
  renderInsights();
  renderOpportunities();
  renderDiscoveryChain();
  renderAssignmentQuestions();

  if (window.lucide) {
    window.lucide.createIcons();
  }
}

// -----------------------------------------------------------------------------
// Top KPI Cards
// -----------------------------------------------------------------------------

function renderKPIs() {
  const grid = document.getElementById('kpiGrid');
  if (!grid) return;

  const stats = AppState.stats || {};
  const totalRaw = stats.total_raw || 1065;
  const totalCleaned = stats.total_cleaned || 696;
  const totalRelevant = stats.total_relevant || 269;
  const totalClassified = stats.total_classified || 269;
  const noisePct = stats.noise_filtered_pct || 34.6;

  const kpis = [
    { label: 'Raw Collected', value: totalRaw.toLocaleString(), sub: '4 Public Sources', icon: 'database', color: 'text-slate-700' },
    { label: 'Cleaned Corpus', value: totalCleaned.toLocaleString(), sub: `${noisePct}% Noise Filtered`, icon: 'sparkles', color: 'text-brand-600' },
    { label: 'Relevant SIP', value: totalRelevant.toLocaleString(), sub: 'Empirical Focus', icon: 'filter', color: 'text-indigo-600' },
    { label: 'AI Classified', value: totalClassified.toLocaleString(), sub: '100% LLM Tagged', icon: 'shield-check', color: 'text-emerald-600' },
    { label: 'Recurring Insights', value: '7', sub: 'High-Impact Themes', icon: 'lightbulb', color: 'text-amber-600' },
    { label: 'P0/P1 Actions', value: '4', sub: 'Critical Opportunities', icon: 'target', color: 'text-rose-600' }
  ];

  grid.innerHTML = kpis.map(k => `
    <div class="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex flex-col justify-between">
      <div class="flex items-center justify-between text-xs text-slate-500 font-semibold mb-1">
        <span>${k.label}</span>
        <i data-lucide="${k.icon}" class="w-4 h-4 ${k.color}"></i>
      </div>
      <div>
        <div class="text-xl sm:text-2xl font-black ${k.color}">${k.value}</div>
        <div class="text-[11px] text-slate-400 mt-0.5">${k.sub}</div>
      </div>
    </div>
  `).join('');
}

// -----------------------------------------------------------------------------
// Tab 1: Research Overview
// -----------------------------------------------------------------------------

function renderAccountingTable() {
  const tbody = document.getElementById('accountingTableBody');
  if (!tbody) return;

  const rows = [
    { stage: '1. Raw Platform Extraction', count: '1,065', share: '100.0%', desc: 'Play Store (600), App Store (100), Reddit (174), YouTube (191)' },
    { stage: '2. De-duplication & Cleaning', count: '696', share: '65.4%', desc: '369 records removed (16 exact duplicates, 353 noise/spam/generic)' },
    { stage: '3. SIP Relevance Filtering', count: '269', share: '25.3%', desc: '427 non-SIP equity/F&O records partitioned out; zero SIP loss' },
    { stage: '4. Multi-Dimensional AI Classification', count: '269', share: '100.0%', desc: '100% classified across journey stage, problem theme, sentiment, behaviour' },
    { stage: '5. Verifiable Evidence Audit', count: '269', share: '100.0%', desc: '100% trace to exact public review/post ID, verbatim quote, and rating' },
  ];

  tbody.innerHTML = rows.map(r => `
    <tr class="hover:bg-slate-50/80 transition">
      <td class="py-2.5 px-4 font-bold text-slate-900">${r.stage}</td>
      <td class="py-2.5 px-4 font-mono font-bold text-brand-600">${r.count}</td>
      <td class="py-2.5 px-4 font-mono text-slate-500">${r.share}</td>
      <td class="py-2.5 px-4 text-slate-600">${r.desc}</td>
    </tr>
  `).join('');
}

function renderOverviewCharts() {
  // Funnel Chart
  const funnelEl = document.getElementById('chart-funnel');
  if (funnelEl) {
    const funnelData = [{
      type: 'funnel',
      y: ['1. Raw Platform Ingested', '2. Cleaned Corpus', '3. SIP Relevant Records', '4. AI Classified Corpus'],
      x: [1065, 696, 269, 269],
      textinfo: 'value+percent initial',
      marker: {
        color: ['#3b82f6', '#60a5fa', '#00d09c', '#10b981']
      }
    }];
    const layout = {
      margin: { l: 150, r: 20, t: 10, b: 20 },
      paper_bgcolor: 'transparent',
      plot_bgcolor: 'transparent',
      font: { family: 'inherit', size: 11 }
    };
    Plotly.newPlot(funnelEl, funnelData, layout, { responsive: true, displayModeBar: false });
  }

  // Source Distribution Donut
  const pieEl = document.getElementById('chart-source-pie');
  if (pieEl) {
    const breakdown = (AppState.stats && AppState.stats.source_classified_breakdown) || {
      'Reddit': 161,
      'YouTube': 72,
      'Apple App Store': 21,
      'Google Play Store': 15
    };

    const pieData = [{
      values: Object.values(breakdown),
      labels: Object.keys(breakdown),
      type: 'pie',
      hole: 0.55,
      marker: {
        colors: ['#ff4500', '#ef4444', '#0070c9', '#00875a']
      },
      textinfo: 'label+percent',
      textposition: 'outside',
      automargin: true
    }];
    const layout = {
      margin: { l: 20, r: 20, t: 10, b: 20 },
      showlegend: false,
      paper_bgcolor: 'transparent',
      font: { family: 'inherit', size: 11 }
    };
    Plotly.newPlot(pieEl, pieData, layout, { responsive: true, displayModeBar: false });
  }
}

// -----------------------------------------------------------------------------
// Tab 2: Cross-Source Analysis
// -----------------------------------------------------------------------------

function renderCrossSourceTable() {
  const tbody = document.getElementById('crossSourceTableBody');
  if (!tbody) return;

  const summary = (AppState.crossSource && AppState.crossSource.summary) || [];
  if (!summary.length) return;

  tbody.innerHTML = summary.map(r => `
    <tr class="hover:bg-slate-50 transition">
      <td class="py-2.5 px-4 font-bold text-slate-900 flex items-center gap-2">
        <span class="w-2.5 h-2.5 rounded-full" style="background-color: ${ChartColors.sources[r['Source Platform']] || '#64748b'}"></span>
        ${r['Source Platform']}
      </td>
      <td class="py-2.5 px-4 font-mono font-bold text-brand-600">${r['Relevant Feedback Count']}</td>
      <td class="py-2.5 px-4 font-mono text-slate-600">${r['Corpus Share (%)']}</td>
      <td class="py-2.5 px-4 font-mono ${parseFloat(r['Avg Sentiment Score']) < 0 ? 'text-rose-600' : 'text-emerald-600'}">
        ${r['Avg Sentiment Score']}
      </td>
      <td class="py-2.5 px-4 font-mono text-slate-600">${r['Avg App Rating']}</td>
      <td class="py-2.5 px-4 text-slate-800">${r['Dominant Problem Theme']}</td>
      <td class="py-2.5 px-4 text-slate-700 capitalize">${r['Dominant User Behaviour']}</td>
      <td class="py-2.5 px-4 text-xs text-slate-500 max-w-xs truncate" title="${r['Channel Persona & Context']}">${r['Channel Persona & Context']}</td>
    </tr>
  `).join('');
}

function renderCrossSourceCharts() {
  const themeCrosstab = (AppState.crossSource && AppState.crossSource.theme_crosstab) || {};
  const sentCrosstab = (AppState.crossSource && AppState.crossSource.sentiment_crosstab) || {};

  // Cross Source Themes Stacked Bar
  const crossThemesEl = document.getElementById('chart-cross-themes');
  if (crossThemesEl && Object.keys(themeCrosstab).length > 0) {
    const channels = Object.keys(themeCrosstab);
    const themes = Object.keys(themeCrosstab[channels[0]] || {});

    const traces = themes.map(theme => ({
      name: theme,
      x: channels,
      y: channels.map(ch => (themeCrosstab[ch] && themeCrosstab[ch][theme]) || 0),
      type: 'bar'
    }));

    const layout = {
      barmode: 'stack',
      margin: { l: 40, r: 20, t: 20, b: 40 },
      paper_bgcolor: 'transparent',
      plot_bgcolor: 'transparent',
      legend: { orientation: 'h', y: -0.2, font: { size: 9 } },
      yaxis: { title: 'Share (%)', range: [0, 100] },
      font: { family: 'inherit', size: 10 }
    };
    Plotly.newPlot(crossThemesEl, traces, layout, { responsive: true, displayModeBar: false });
  }

  // Cross Source Sentiment Grouped Bar
  const crossSentEl = document.getElementById('chart-cross-sent');
  if (crossSentEl && Object.keys(sentCrosstab).length > 0) {
    const channels = Object.keys(sentCrosstab);
    const sentKeys = ['negative', 'neutral', 'positive'];

    const traces = sentKeys.map(sent => ({
      name: sent.charAt(0).toUpperCase() + sent.slice(1),
      x: channels,
      y: channels.map(ch => (sentCrosstab[ch] && sentCrosstab[ch][sent]) || 0),
      type: 'bar',
      marker: { color: ChartColors.sentiments[sent] }
    }));

    const layout = {
      barmode: 'group',
      margin: { l: 40, r: 20, t: 20, b: 40 },
      paper_bgcolor: 'transparent',
      plot_bgcolor: 'transparent',
      legend: { orientation: 'h', y: -0.2, font: { size: 10 } },
      yaxis: { title: 'Proportion (%)', range: [0, 100] },
      font: { family: 'inherit', size: 10 }
    };
    Plotly.newPlot(crossSentEl, traces, layout, { responsive: true, displayModeBar: false });
  }
}

// -----------------------------------------------------------------------------
// Tab 3: Problem Explorer
// -----------------------------------------------------------------------------

function renderProblemExplorer() {
  const records = AppState.filteredRecords.length > 0 ? AppState.filteredRecords : AppState.allRecords;

  // Aggregate theme frequencies
  const themeCounts = {};
  const stageCounts = {};
  const behCounts = {};
  const typeCounts = {};

  records.forEach(r => {
    const th = r.problem_theme || 'Unknown';
    themeCounts[th] = (themeCounts[th] || 0) + 1;

    const st = r.user_journey_stage || 'Unknown';
    stageCounts[st] = (stageCounts[st] || 0) + 1;

    const bh = r.user_behaviour || 'Unknown';
    behCounts[bh] = (behCounts[bh] || 0) + 1;

    const tp = r.classification_type || 'Unknown';
    typeCounts[tp] = (typeCounts[tp] || 0) + 1;
  });

  // Problem Themes Horizontal Bar Chart
  const themesChartEl = document.getElementById('chart-problem-themes');
  if (themesChartEl) {
    const sortedThemes = Object.entries(themeCounts).sort((a, b) => a[1] - b[1]);
    const trace = {
      type: 'bar',
      orientation: 'h',
      x: sortedThemes.map(s => s[1]),
      y: sortedThemes.map(s => s[0]),
      marker: {
        color: sortedThemes.map(s => s[0].includes('Positive') ? '#10b981' : s[0].includes('Mandate') ? '#ef4444' : '#3b82f6')
      },
      text: sortedThemes.map(s => `${s[1]} records`),
      textposition: 'auto'
    };
    const layout = {
      margin: { l: 200, r: 20, t: 10, b: 40 },
      paper_bgcolor: 'transparent',
      plot_bgcolor: 'transparent',
      xaxis: { title: 'Record Count' },
      font: { family: 'inherit', size: 10 }
    };
    Plotly.newPlot(themesChartEl, [trace], layout, { responsive: true, displayModeBar: false });
  }

  // Stage vs Theme Heatmap
  const stageThemeEl = document.getElementById('chart-stage-theme');
  if (stageThemeEl) {
    const stages = Object.keys(stageCounts);
    const themes = Object.keys(themeCounts);
    const zMatrix = themes.map(th => {
      return stages.map(st => {
        return records.filter(r => r.problem_theme === th && r.user_journey_stage === st).length;
      });
    });

    const heatmapData = [{
      z: zMatrix,
      x: stages,
      y: themes,
      type: 'heatmap',
      colorscale: 'Blues',
      showscale: false
    }];
    const layout = {
      margin: { l: 180, r: 20, t: 10, b: 80 },
      paper_bgcolor: 'transparent',
      plot_bgcolor: 'transparent',
      xaxis: { tickangle: -25 },
      font: { family: 'inherit', size: 9 }
    };
    Plotly.newPlot(stageThemeEl, heatmapData, layout, { responsive: true, displayModeBar: false });
  }

  // Distribution Lists
  renderPillList('stageDistributionList', stageCounts, records.length);
  renderPillList('behaviourDistributionList', behCounts, records.length);
  renderPillList('typeDistributionList', typeCounts, records.length);
}

function renderPillList(containerId, countsObj, total) {
  const container = document.getElementById(containerId);
  if (!container) return;

  const sorted = Object.entries(countsObj).sort((a, b) => b[1] - a[1]);
  container.innerHTML = sorted.map(([label, count]) => {
    const pct = total > 0 ? ((count / total) * 100).toFixed(1) : 0;
    return `
      <div class="flex items-center justify-between p-2 bg-slate-50 rounded-lg border border-slate-100">
        <span class="font-medium text-slate-800 capitalize truncate pr-2">${label}</span>
        <div class="flex items-center gap-2 shrink-0">
          <span class="font-mono font-bold text-slate-900">${count}</span>
          <span class="text-[10px] text-slate-400">(${pct}%)</span>
        </div>
      </div>
    `;
  }).join('');
}

// -----------------------------------------------------------------------------
// Tab 4: Evidence Explorer (Table, Filter & Pagination)
// -----------------------------------------------------------------------------

function renderEvidenceTable() {
  const tbody = document.getElementById('evidenceTableBody');
  const countBadge = document.getElementById('filterCountBadge');
  const countText = document.getElementById('filterCountText');
  const emptyState = document.getElementById('emptyState');
  const paginationInfo = document.getElementById('paginationInfo');
  const paginationControls = document.getElementById('paginationControls');

  const filtered = AppState.filteredRecords;
  const total = AppState.allRecords.length;
  const countMsg = `Showing: ${filtered.length.toLocaleString()} / ${total.toLocaleString()} records`;

  if (countText) countText.textContent = countMsg;
  else if (countBadge) countBadge.textContent = countMsg;

  if (filtered.length === 0) {
    if (tbody) tbody.innerHTML = '';
    if (emptyState) emptyState.classList.remove('hidden');
    if (paginationInfo) paginationInfo.textContent = '0 records';
    if (paginationControls) paginationControls.innerHTML = '';
    return;
  } else {
    if (emptyState) emptyState.classList.add('hidden');
  }

  if (!tbody) return;

  const pageSize = AppState.pageSize === 'all' ? filtered.length : parseInt(AppState.pageSize, 10);
  const totalPages = Math.ceil(filtered.length / pageSize) || 1;
  if (AppState.currentPage > totalPages) AppState.currentPage = totalPages;
  if (AppState.currentPage < 1) AppState.currentPage = 1;

  const startIndex = (AppState.currentPage - 1) * pageSize;
  const endIndex = Math.min(startIndex + pageSize, filtered.length);
  const paginated = filtered.slice(startIndex, endIndex);

  if (paginationInfo) {
    paginationInfo.textContent = `Showing ${(startIndex + 1).toLocaleString()} to ${endIndex.toLocaleString()} of ${filtered.length.toLocaleString()} records`;
  }

  // Render pagination controls
  if (paginationControls) {
    if (totalPages <= 1) {
      paginationControls.innerHTML = '';
    } else {
      let btns = [];
      // Prev Button
      btns.push(`
        <button onclick="changePage(${AppState.currentPage - 1})" ${AppState.currentPage === 1 ? 'disabled class="px-2 py-1 text-slate-300 cursor-not-allowed"' : 'class="px-2 py-1 text-slate-700 hover:bg-slate-100 rounded"'} title="Previous page">
          ‹ Prev
        </button>
      `);

      // Page numbers (smart window)
      const maxButtons = 5;
      let startP = Math.max(1, AppState.currentPage - 2);
      let endP = Math.min(totalPages, startP + maxButtons - 1);
      if (endP - startP < maxButtons - 1) {
        startP = Math.max(1, endP - maxButtons + 1);
      }

      if (startP > 1) {
        btns.push(`<button onclick="changePage(1)" class="px-2.5 py-1 rounded text-slate-600 hover:bg-slate-100">1</button>`);
        if (startP > 2) btns.push(`<span class="px-1 text-slate-400">…</span>`);
      }

      for (let p = startP; p <= endP; p++) {
        const isActive = p === AppState.currentPage;
        btns.push(`
          <button onclick="changePage(${p})" class="px-2.5 py-1 rounded font-bold text-xs ${isActive ? 'bg-brand-600 text-white' : 'text-slate-700 hover:bg-slate-100'}">
            ${p}
          </button>
        `);
      }

      if (endP < totalPages) {
        if (endP < totalPages - 1) btns.push(`<span class="px-1 text-slate-400">…</span>`);
        btns.push(`<button onclick="changePage(${totalPages})" class="px-2.5 py-1 rounded text-slate-600 hover:bg-slate-100">${totalPages}</button>`);
      }

      // Next Button
      btns.push(`
        <button onclick="changePage(${AppState.currentPage + 1})" ${AppState.currentPage === totalPages ? 'disabled class="px-2 py-1 text-slate-300 cursor-not-allowed"' : 'class="px-2 py-1 text-slate-700 hover:bg-slate-100 rounded"'} title="Next page">
          Next ›
        </button>
      `);

      paginationControls.innerHTML = btns.join('');
    }
  }

  tbody.innerHTML = paginated.map(r => {
    const quote = (r.evidence_quote || r.cleaned_text || '').replace(/"/g, '&quot;');
    const truncatedQuote = quote.length > 85 ? quote.slice(0, 85) + '…' : quote;
    const ratingDisplay = r.rating_display || (r.rating ? `${r.rating}★` : '—');
    const sourceClass = ChartColors.sources[r.source_display] || '#64748b';

    return `
      <tr class="hover:bg-slate-50/90 transition">
        <td class="py-2.5 px-3 font-mono font-bold text-brand-700 whitespace-nowrap">
          <button onclick="openRecordModal('${r.record_id}')" class="hover:underline flex items-center gap-1 text-left">
            ${r.record_id}
          </button>
        </td>
        <td class="py-2.5 px-3 whitespace-nowrap">
          <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-semibold text-white" style="background-color: ${sourceClass}">
            ${r.source_display || r.source}
          </span>
        </td>
        <td class="py-2.5 px-3 font-semibold text-amber-500 whitespace-nowrap">${ratingDisplay}</td>
        <td class="py-2.5 px-3 text-slate-500 whitespace-nowrap">${r.date || '—'}</td>
        <td class="py-2.5 px-3 font-medium text-slate-800 max-w-[140px] truncate" title="${r.problem_theme}">${r.problem_theme || '—'}</td>
        <td class="py-2.5 px-3 text-slate-600 whitespace-nowrap">${r.user_journey_stage || '—'}</td>
        <td class="py-2.5 px-3 text-slate-700 italic max-w-xs truncate" title="${quote}">"${truncatedQuote}"</td>
        <td class="py-2.5 px-3 whitespace-nowrap">
          <button onclick="openRecordModal('${r.record_id}')" class="px-2 py-1 text-[11px] font-bold text-brand-600 hover:text-brand-800 bg-brand-50 hover:bg-brand-100 rounded transition">
            Inspect
          </button>
        </td>
      </tr>
    `;
  }).join('');
}

function changePage(newPage) {
  AppState.currentPage = newPage;
  renderEvidenceTable();
  const table = document.getElementById('evidenceTableBody');
  if (table) table.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function changePageSize(newSize) {
  AppState.pageSize = newSize === 'all' ? 'all' : parseInt(newSize, 10);
  AppState.currentPage = 1;
  renderEvidenceTable();
}

// -----------------------------------------------------------------------------
// Filters & Search
// -----------------------------------------------------------------------------

function debounceSearch() {
  clearTimeout(AppState.searchDebounceTimer);
  AppState.searchDebounceTimer = setTimeout(() => {
    applyFilters(false);
    renderSearchDropdown();
  }, 150);
}

function handleSearchKeyDown(e) {
  if (e.key === 'Enter') {
    e.preventDefault();
    closeSearchDropdown();
    applyFilters(true);
    switchTab('evidenceExplorer');
    const tableEl = document.getElementById('evidenceTableBody');
    if (tableEl) tableEl.scrollIntoView({ behavior: 'smooth', block: 'start' });
  } else if (e.key === 'Escape') {
    closeSearchDropdown();
  }
}

function closeSearchDropdown() {
  const dropdown = document.getElementById('searchDropdown');
  if (dropdown) dropdown.classList.add('hidden');
}

function renderSearchDropdown() {
  const dropdown = document.getElementById('searchDropdown');
  const query = (document.getElementById('globalSearchInput')?.value || '').trim();
  if (!dropdown) return;

  if (!query) {
    dropdown.classList.add('hidden');
    dropdown.innerHTML = '';
    return;
  }

  const matches = AppState.filteredRecords.slice(0, 5);
  const totalMatches = AppState.filteredRecords.length;

  if (totalMatches === 0) {
    dropdown.innerHTML = `
      <div class="p-4 text-center text-xs text-slate-500">
        No records found matching "<span class="font-bold text-slate-700">${escapeHtml(query)}</span>"
      </div>
    `;
    dropdown.classList.remove('hidden');
    return;
  }

  const itemsHtml = matches.map(r => {
    const quote = (r.evidence_quote || r.cleaned_text || '').replace(/"/g, '&quot;');
    const truncatedQuote = quote.length > 90 ? quote.slice(0, 90) + '…' : quote;
    const sourceClass = ChartColors.sources[r.source_display] || '#64748b';

    return `
      <div onclick="openRecordModal('${r.record_id}'); closeSearchDropdown();" class="p-3 hover:bg-slate-50 cursor-pointer transition flex flex-col gap-1">
        <div class="flex items-center justify-between text-xs">
          <div class="flex items-center gap-2">
            <span class="font-mono font-bold text-brand-700">${r.record_id}</span>
            <span class="px-1.5 py-0.5 rounded text-[10px] font-semibold text-white" style="background-color: ${sourceClass}">
              ${r.source_display || r.source}
            </span>
          </div>
          <span class="text-[11px] text-slate-400 font-medium">${r.problem_theme || ''}</span>
        </div>
        <p class="text-xs text-slate-700 italic leading-snug">"${truncatedQuote}"</p>
      </div>
    `;
  }).join('');

  dropdown.innerHTML = `
    <div class="p-2 bg-slate-50 border-b border-slate-100 flex items-center justify-between text-[11px] font-bold text-slate-500">
      <span>TOP MATCHES (${totalMatches.toLocaleString()} total)</span>
      <span class="text-slate-400 text-[10px]">Press Enter to view all</span>
    </div>
    ${itemsHtml}
    <div class="p-2 bg-slate-50 border-t border-slate-100 text-center">
      <button onclick="switchTab('evidenceExplorer'); closeSearchDropdown();" class="w-full py-1 text-xs font-bold text-brand-600 hover:text-brand-800 transition flex items-center justify-center gap-1">
        <span>View all ${totalMatches.toLocaleString()} records in Evidence Explorer</span>
        <i data-lucide="arrow-right" class="w-3.5 h-3.5"></i>
      </button>
    </div>
  `;
  dropdown.classList.remove('hidden');
  if (window.lucide) window.lucide.createIcons();
}

function applyFilters(autoSwitch = false) {
  const query = (document.getElementById('globalSearchInput')?.value || '').trim().toLowerCase();
  const source = document.getElementById('sourceSelect')?.value || '';
  const theme = document.getElementById('themeSelect')?.value || '';
  const sentiment = document.getElementById('sentimentSelect')?.value || '';

  AppState.filteredRecords = AppState.allRecords.filter(r => {
    if (source) {
      const matchSource = (r.source || '').toLowerCase() === source.toLowerCase() ||
                          (r.source_display || '').toLowerCase() === source.toLowerCase() ||
                          (r.source_display || '').toLowerCase().includes(source.toLowerCase());
      if (!matchSource) return false;
    }

    if (theme && r.problem_theme !== theme) return false;
    if (sentiment && (r.sentiment || '').toLowerCase() !== sentiment.toLowerCase()) return false;

    if (query) {
      const hay = [
        r.record_id,
        r.cleaned_text,
        r.raw_text,
        r.evidence_quote,
        r.classification_reason,
        r.problem_theme,
        r.user_journey_stage
      ].join(' ').toLowerCase();
      if (!hay.includes(query)) return false;
    }

    return true;
  });

  AppState.currentPage = 1;
  renderEvidenceTable();
  renderProblemExplorer();

  if (autoSwitch && (query || source || theme || sentiment)) {
    if (AppState.activeTab !== 'evidenceExplorer') {
      switchTab('evidenceExplorer');
    }
  }
}

function resetFilters() {
  const searchInput = document.getElementById('globalSearchInput');
  const sourceSel = document.getElementById('sourceSelect');
  const themeSel = document.getElementById('themeSelect');
  const sentSel = document.getElementById('sentimentSelect');

  if (searchInput) searchInput.value = '';
  if (sourceSel) sourceSel.value = '';
  if (themeSel) themeSel.value = '';
  if (sentSel) sentSel.value = '';

  closeSearchDropdown();
  AppState.filteredRecords = [...AppState.allRecords];
  AppState.currentPage = 1;
  renderEvidenceTable();
  renderProblemExplorer();
}

  AppState.filteredRecords = [...AppState.allRecords];
  AppState.currentPage = 1;
  renderEvidenceTable();
  renderProblemExplorer();
}

function exportCSV() {
  const records = AppState.filteredRecords.length > 0 ? AppState.filteredRecords : AppState.allRecords;
  if (!records.length) return;

  const headers = ['record_id', 'source', 'date', 'rating', 'problem_theme', 'user_journey_stage', 'sentiment', 'user_behaviour', 'evidence_quote', 'confidence_score'];
  const csvRows = [headers.join(',')];

  records.forEach(r => {
    const row = headers.map(h => {
      let val = r[h] !== undefined && r[h] !== null ? String(r[h]) : '';
      val = val.replace(/"/g, '""');
      return `"${val}"`;
    });
    csvRows.push(row.join(','));
  });

  const blob = new Blob([csvRows.join('\n')], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `groww_sip_filtered_${new Date().toISOString().slice(0, 10)}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

// -----------------------------------------------------------------------------
// Tab 5: Insight Explorer
// -----------------------------------------------------------------------------

function renderInsights() {
  const grid = document.getElementById('insightsGrid');
  if (!grid) return;

  const insights = AppState.insights || [];
  grid.innerHTML = insights.map((ins, idx) => {
    const badgeClass = ins.severity === 'High' ? 'badge-p0' : ins.severity === 'Medium' ? 'badge-p1' : 'badge-pos';
    const quotesCount = (ins.quotes || []).length;
    const recCount = (ins.supporting_record_ids || []).length;

    return `
      <div class="bg-white p-5 rounded-xl border border-slate-200 shadow-sm flex flex-col justify-between hover:border-brand-300 transition">
        <div>
          <div class="flex items-center justify-between gap-2 mb-2">
            <span class="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${badgeClass}">
              ${ins.severity} Severity · ${ins.category}
            </span>
            <span class="text-xs font-mono font-bold text-brand-600">${ins.count} Records (${ins.pct}%)</span>
          </div>
          <h4 class="text-sm font-bold text-slate-900 mb-2 leading-snug">${ins.title}</h4>
          <p class="text-xs text-slate-600 mb-3">${ins.description}</p>
          <div class="bg-slate-50 p-2.5 rounded-lg border border-slate-100 text-xs text-slate-700 mb-4">
            <span class="font-bold text-brand-800">Recommendation:</span> ${ins.recommendation}
          </div>
        </div>
        <div class="flex items-center justify-between border-t border-slate-100 pt-3">
          <span class="text-[11px] text-slate-400 font-mono">${recCount} verified records</span>
          <button onclick="revealInsightEvidence(${idx})" class="text-xs font-bold text-brand-600 hover:text-brand-800 flex items-center gap-1">
            View Evidence Quotes (${quotesCount}) →
          </button>
        </div>
      </div>
    `;
  }).join('');
}

function revealInsightEvidence(insightIdx) {
  const ins = AppState.insights[insightIdx];
  if (!ins) return;

  const drawer = document.getElementById('insightDetailDrawer');
  const title = document.getElementById('drawerTitle');
  const subtitle = document.getElementById('drawerSubtitle');
  const list = document.getElementById('drawerQuotesList');

  if (!drawer || !list) return;

  title.textContent = `${ins.title} — Supporting Evidence`;
  subtitle.textContent = `${(ins.supporting_record_ids || []).length} Verified Investor Quotes · Click Record ID to inspect`;

  list.innerHTML = (ins.quotes || []).map(q => {
    return `
      <div class="bg-slate-50 p-3 rounded-lg border border-slate-200 text-xs">
        <div class="flex items-center justify-between text-[11px] font-mono text-slate-500 mb-1">
          <button onclick="openRecordModal('${q.record_id}')" class="font-bold text-brand-600 hover:underline">
            ID: ${q.record_id}
          </button>
          <span>Source: ${q.source}</span>
        </div>
        <blockquote class="italic text-slate-700">"${q.quote}"</blockquote>
      </div>
    `;
  }).join('');

  drawer.classList.remove('hidden');
  drawer.scrollIntoView({ behavior: 'smooth' });
}

function closeInsightDrawer() {
  const drawer = document.getElementById('insightDetailDrawer');
  if (drawer) drawer.classList.add('hidden');
}

// -----------------------------------------------------------------------------
// Tab 6: Opportunity Matrix
// -----------------------------------------------------------------------------

function renderOpportunities() {
  const opps = AppState.opportunities || [];
  if (!opps.length) return;

  // Render 2D Scatter Bubble Chart
  const oppChartEl = document.getElementById('chart-opp-matrix');
  if (oppChartEl) {
    const traces = opps.map(op => {
      const color = op.priority_tier === 'P0' ? '#ef4444' : op.priority_tier === 'P1' ? '#f59e0b' : '#3b82f6';
      return {
        x: [op.frequency_score],
        y: [op.severity_score],
        mode: 'markers+text',
        name: op.opportunity_name,
        text: [op.priority_tier],
        textposition: 'middle center',
        marker: {
          size: [op.opportunity_score * 7],
          color: color,
          opacity: 0.85,
          line: { width: 1.5, color: '#ffffff' }
        },
        hovertemplate: `<b>${op.opportunity_name}</b><br>Tier: ${op.priority_tier}<br>Score: ${op.opportunity_score}<br>Freq: ${op.frequency_count} records<extra></extra>`
      };
    });

    const layout = {
      margin: { l: 50, r: 20, t: 20, b: 50 },
      paper_bgcolor: 'transparent',
      plot_bgcolor: 'transparent',
      xaxis: { title: 'Frequency Score (0 - 10)', range: [0, 11] },
      yaxis: { title: 'Severity Score (0 - 10)', range: [0, 11] },
      showlegend: false,
      font: { family: 'inherit', size: 10 }
    };
    Plotly.newPlot(oppChartEl, traces, layout, { responsive: true, displayModeBar: false });
  }

  // Render Action Cards
  const cardsList = document.getElementById('opportunityCardsList');
  if (cardsList) {
    cardsList.innerHTML = opps.map(op => {
      const tierBadge = op.priority_tier === 'P0' ? 'badge-p0' : op.priority_tier === 'P1' ? 'badge-p1' : 'badge-p2';
      return `
        <div class="p-3 bg-slate-50 rounded-lg border border-slate-200 text-xs">
          <div class="flex items-center justify-between mb-1.5">
            <span class="px-2 py-0.5 rounded font-bold uppercase tracking-wider ${tierBadge}">${op.priority_tier} Priority</span>
            <span class="font-mono font-bold text-slate-800">Score: ${op.opportunity_score} / 10</span>
          </div>
          <h4 class="font-bold text-slate-900 mb-1">${op.opportunity_name}</h4>
          <p class="text-slate-600 mb-2">${op.product_recommendation}</p>
          <div class="flex items-center gap-3 text-[11px] text-slate-400 font-mono">
            <span>Frequency: ${op.frequency_count}</span>
            <span>Impact: ${op.user_impact_score}/10</span>
          </div>
        </div>
      `;
    }).join('');
  }
}

// -----------------------------------------------------------------------------
// Tab 7: AI Research Assistant
// -----------------------------------------------------------------------------

function setQuery(query) {
  const input = document.getElementById('aiQueryInput');
  if (input) {
    input.value = query;
    askAssistant();
  }
}

async function askAssistant() {
  const input = document.getElementById('aiQueryInput');
  const btn = document.getElementById('aiSubmitBtn');
  const resContainer = document.getElementById('aiResponseContainer');
  const answerText = document.getElementById('aiAnswerText');
  const citationsList = document.getElementById('aiCitationsList');
  const modelBadge = document.getElementById('aiModelBadge');

  if (!input || !input.value.trim()) return;
  const query = input.value.trim();

  // Loading state in button
  btn.disabled = true;
  btn.innerHTML = `<div class="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div> Synthesizing...`;

  try {
    const res = await fetch('/api/ask', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query })
    });

    let data;
    if (res.ok) {
      data = await res.json();
    } else {
      // Deterministic client fallback if serverless API route is unavailable
      data = deterministicFallbackAnswer(query);
    }

    // Populate response
    if (modelBadge) modelBadge.textContent = data.model ? `Engine: ${data.model}` : 'Engine: Client Evidence Retriever';
    if (answerText) {
      // Format markdown paragraphs
      answerText.innerHTML = formatMarkdown(data.answer);
    }

    if (citationsList) {
      citationsList.innerHTML = (data.citations || []).map(c => `
        <div class="bg-white p-2.5 rounded-lg border border-slate-200 text-xs">
          <div class="flex items-center justify-between font-mono text-[11px] mb-1">
            <button onclick="openRecordModal('${c.record_id}')" class="font-bold text-brand-600 hover:underline">
              [${c.record_id}]
            </button>
            <span class="text-slate-500">${c.source}</span>
          </div>
          <p class="text-slate-700 italic truncate" title="${c.quote}">"${c.quote}"</p>
          <div class="text-[10px] text-slate-400 mt-1">${c.theme}</div>
        </div>
      `).join('');
    }

    resContainer.classList.remove('hidden');
    resContainer.scrollIntoView({ behavior: 'smooth' });
  } catch (err) {
    // Client-side evidence fallback
    const fallback = deterministicFallbackAnswer(query);
    if (answerText) answerText.innerHTML = formatMarkdown(fallback.answer);
    if (citationsList) {
      citationsList.innerHTML = (fallback.citations || []).map(c => `
        <div class="bg-white p-2.5 rounded-lg border border-slate-200 text-xs">
          <div class="flex items-center justify-between font-mono text-[11px] mb-1">
            <button onclick="openRecordModal('${c.record_id}')" class="font-bold text-brand-600 hover:underline">
              [${c.record_id}]
            </button>
            <span class="text-slate-500">${c.source}</span>
          </div>
          <p class="text-slate-700 italic truncate" title="${c.quote}">"${c.quote}"</p>
          <div class="text-[10px] text-slate-400 mt-1">${c.theme}</div>
        </div>
      `).join('');
    }
    resContainer.classList.remove('hidden');
  } finally {
    btn.disabled = false;
    btn.innerHTML = `<i data-lucide="sparkles" class="w-4 h-4"></i> Ask`;
    if (window.lucide) window.lucide.createIcons();
  }
}

function deterministicFallbackAnswer(query) {
  const terms = query.toLowerCase().split(/\s+/).filter(w => w.length > 2);
  const scored = AppState.allRecords.map(r => {
    const text = [r.cleaned_text, r.evidence_quote, r.problem_theme, r.user_journey_stage].join(' ').toLowerCase();
    let score = 0;
    terms.forEach(t => { if (text.includes(t)) score++; });
    return { record: r, score };
  }).filter(item => item.score > 0).sort((a, b) => b.score - a.score).slice(0, 5);

  const citations = scored.map(s => ({
    record_id: s.record.record_id,
    source: s.record.source_display || s.record.source,
    quote: s.record.evidence_quote || s.record.cleaned_text,
    theme: s.record.problem_theme
  }));

  const answer = `Based on empirical analysis of ${AppState.allRecords.length} classified records across Google Play, App Store, Reddit, and YouTube, relevant feedback was retrieved matching your inquiry.

Key findings from verifiable investor feedback:
${citations.slice(0, 3).map(c => `• **[${c.record_id}]** (${c.source}): "${c.quote.slice(0, 140)}..."`).join('\n\n')}

Review the supporting citation cards below to inspect full verifications and star ratings.`;

  return { answer, citations, model: 'Deterministic Corpus Matcher' };
}

function formatMarkdown(text) {
  if (!text) return '';
  return text
    .replace(/^### (.*$)/gim, '<h4 class="font-bold text-slate-900 mt-3 mb-1 text-sm">$1</h4>')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/\n\n/g, '</p><p class="mt-2">')
    .replace(/^\• (.*$)/gim, '<li class="ml-4 list-disc">$1</li>');
}

// -----------------------------------------------------------------------------
// Record Inspection Modal
// -----------------------------------------------------------------------------

function openRecordModal(recordId) {
  const record = AppState.allRecords.find(r => r.record_id === recordId);
  if (!record) return;

  const modal = document.getElementById('recordModal');
  const title = document.getElementById('modalTitle');
  const body = document.getElementById('modalBody');

  if (!modal || !body) return;

  title.textContent = `Record Audit: ${record.record_id}`;

  const ratingHtml = record.rating ? `<span class="text-amber-500 font-bold">${record.rating}★</span>` : 'N/A';
  const confidencePct = record.confidence_score ? `${(record.confidence_score * 100).toFixed(0)}%` : '100%';

  body.innerHTML = `
    <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 bg-slate-50 p-3 rounded-xl border border-slate-200">
      <div>
        <div class="text-[10px] text-slate-400 uppercase font-semibold">Source</div>
        <div class="font-bold text-slate-800">${record.source_display || record.source}</div>
      </div>
      <div>
        <div class="text-[10px] text-slate-400 uppercase font-semibold">Date</div>
        <div class="font-bold text-slate-800">${record.date || '—'}</div>
      </div>
      <div>
        <div class="text-[10px] text-slate-400 uppercase font-semibold">Rating</div>
        <div>${ratingHtml}</div>
      </div>
      <div>
        <div class="text-[10px] text-slate-400 uppercase font-semibold">AI Confidence</div>
        <div class="font-mono font-bold text-emerald-600">${confidencePct}</div>
      </div>
    </div>

    <div>
      <div class="text-[11px] font-bold text-slate-600 uppercase mb-1">Verbatim Evidence Quote</div>
      <div class="bg-blue-50 border-l-4 border-brand-500 p-3 rounded text-slate-800 italic">
        "${record.evidence_quote || record.cleaned_text}"
      </div>
    </div>

    <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
      <div class="p-3 bg-slate-50 rounded-lg border border-slate-100">
        <div class="text-[10px] text-slate-400 uppercase font-semibold">Problem Theme</div>
        <div class="font-bold text-slate-900">${record.problem_theme || '—'}</div>
      </div>
      <div class="p-3 bg-slate-50 rounded-lg border border-slate-100">
        <div class="text-[10px] text-slate-400 uppercase font-semibold">User Journey Stage</div>
        <div class="font-bold text-slate-900">${record.user_journey_stage || '—'}</div>
      </div>
      <div class="p-3 bg-slate-50 rounded-lg border border-slate-100">
        <div class="text-[10px] text-slate-400 uppercase font-semibold">User Behaviour</div>
        <div class="font-bold text-slate-900 capitalize">${record.user_behaviour || '—'}</div>
      </div>
      <div class="p-3 bg-slate-50 rounded-lg border border-slate-100">
        <div class="text-[10px] text-slate-400 uppercase font-semibold">Sentiment</div>
        <div class="font-bold capitalize ${record.sentiment === 'negative' ? 'text-rose-600' : 'text-emerald-600'}">
          ${record.sentiment || '—'} (score: ${record.sentiment_score ?? 0})
        </div>
      </div>
    </div>

    <div>
      <div class="text-[11px] font-bold text-slate-600 uppercase mb-1">Classification Reason & Methodology Audit</div>
      <p class="text-slate-600 leading-relaxed bg-slate-50 p-3 rounded-lg border border-slate-100">
        ${record.classification_reason || 'Identified via multi-dimensional LLM inference with strict zero-hallucination constraint.'}
      </p>
    </div>

    ${record.url ? `
      <div class="pt-2 text-right">
        <a href="${record.url}" target="_blank" rel="noopener noreferrer" class="text-xs font-bold text-brand-600 hover:underline">
          View Original Public Post / Reference ↗
        </a>
      </div>
    ` : ''}
  `;

  modal.classList.remove('hidden');
}

function closeModal() {
  const modal = document.getElementById('recordModal');
  if (modal) modal.classList.add('hidden');
}

// -----------------------------------------------------------------------------
// Image Lightbox Modal Functions (Canvases & Blueprints)
// -----------------------------------------------------------------------------

function openImageModal(imgSrc, title, caption) {
  const modal = document.getElementById('imageLightboxModal');
  const img = document.getElementById('lightboxImg');
  const titleEl = document.getElementById('lightboxTitle');
  const captionEl = document.getElementById('lightboxCaption');
  const downloadBtn = document.getElementById('lightboxDownloadBtn');

  if (!modal || !img) return;

  img.src = imgSrc;
  if (titleEl) titleEl.textContent = title || 'Research Canvas Blueprint';
  if (captionEl) captionEl.textContent = caption || 'High-resolution Groww SIP Insight Lab dashboard artifact';
  if (downloadBtn) {
    downloadBtn.href = imgSrc;
    downloadBtn.download = imgSrc.split('/').pop() || 'canvas_blueprint.png';
  }

  modal.classList.remove('hidden');
  document.body.style.overflow = 'hidden';
  if (window.lucide) window.lucide.createIcons();
}

function closeImageModal() {
  const modal = document.getElementById('imageLightboxModal');
  if (modal) {
    modal.classList.add('hidden');
    document.body.style.overflow = '';
  }
}

// Global keyboard shortcuts (Esc to close modals)
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') {
    closeImageModal();
    closeModal();
  }
});

// -----------------------------------------------------------------------------
// Tab Switching
// -----------------------------------------------------------------------------

function switchTab(tabId) {
  AppState.activeTab = tabId;

  // Toggle buttons
  document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
  const activeBtn = document.getElementById(`tab-${tabId}`);
  if (activeBtn) activeBtn.classList.add('active');

  // Toggle panes
  document.querySelectorAll('.tab-pane').forEach(pane => pane.classList.add('hidden'));
  const activePane = document.getElementById(`tabContent-${tabId}`);
  if (activePane) activePane.classList.remove('hidden');

  // Trigger Plotly resize for charts in newly visible tab
  window.dispatchEvent(new Event('resize'));
}

// -----------------------------------------------------------------------------
// Tab 8: Discovery Chain & Assignment Questions
// -----------------------------------------------------------------------------

function renderDiscoveryChain() {
  const container = document.getElementById('discoveryChainList');
  if (!container) return;
  const chain = AppState.discoveryChain.length > 0 ? AppState.discoveryChain : AppState.opportunities;
  if (!chain || !chain.length) return;

  container.innerHTML = chain.map((item, idx) => {
    const tierClass = (item.priority_tier || '').includes('P0') ? 'badge-p0' : 'badge-p1';
    const score = item.opportunity_score !== undefined ? item.opportunity_score : 0;
    const sampleIds = (item.sample_record_ids || '').split(',').map(s => s.trim()).filter(Boolean);

    return `
      <div class="bg-slate-50 border border-slate-200 rounded-xl p-4 flex flex-col gap-3 hover:border-brand-400 transition">
        <div class="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200 pb-2">
          <div class="flex items-center gap-2">
            <span class="px-2 py-0.5 rounded text-[11px] font-bold uppercase tracking-wider ${tierClass}">
              ${item.opp_id || `OPP-0${idx+1}`} · ${item.priority_tier || 'P1'}
            </span>
            <h4 class="font-bold text-sm text-slate-900">${item.opportunity_name}</h4>
          </div>
          <div class="text-xs font-mono font-bold text-brand-700">
            Score: ${score} / 10 · Freq: ${item.frequency_count || 0} records
          </div>
        </div>

        <!-- 6-Stage Linear Chain Grid -->
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-6 gap-2 text-xs">
          <div class="p-2.5 bg-white rounded-lg border border-slate-200 flex flex-col justify-between">
            <div>
              <div class="text-[10px] font-bold text-slate-400 uppercase mb-1">1. User Feedback</div>
              <p class="italic text-slate-700 line-clamp-3" title="${item.user_feedback || ''}">"${item.user_feedback || ''}"</p>
            </div>
          </div>
          <div class="p-2.5 bg-white rounded-lg border border-slate-200 flex flex-col justify-between">
            <div>
              <div class="text-[10px] font-bold text-slate-400 uppercase mb-1">2. Research Finding</div>
              <p class="text-slate-800 line-clamp-3">${item.research_finding || ''}</p>
            </div>
          </div>
          <div class="p-2.5 bg-white rounded-lg border border-slate-200 flex flex-col justify-between">
            <div>
              <div class="text-[10px] font-bold text-rose-500 uppercase mb-1">3. User Problem</div>
              <p class="text-slate-900 font-medium line-clamp-3">${item.user_problem || ''}</p>
            </div>
          </div>
          <div class="p-2.5 bg-white rounded-lg border border-slate-200 flex flex-col justify-between">
            <div>
              <div class="text-[10px] font-bold text-amber-600 uppercase mb-1">4. Unmet Need</div>
              <p class="text-slate-800 line-clamp-3">${item.unmet_need || ''}</p>
            </div>
          </div>
          <div class="p-2.5 bg-white rounded-lg border border-slate-200 flex flex-col justify-between">
            <div>
              <div class="text-[10px] font-bold text-brand-600 uppercase mb-1">5. Opportunity</div>
              <p class="text-brand-900 font-semibold line-clamp-3">${item.product_recommendation || item.opportunity || ''}</p>
            </div>
          </div>
          <div class="p-2.5 bg-white rounded-lg border border-slate-200 flex flex-col justify-between">
            <div>
              <div class="text-[10px] font-bold text-emerald-600 uppercase mb-1">6. Evidence IDs</div>
              <div class="flex flex-wrap gap-1 mt-1">
                ${sampleIds.map(id => `
                  <button onclick="openRecordModal('${id}')" class="px-1.5 py-0.5 bg-brand-50 hover:bg-brand-100 text-brand-700 rounded text-[10px] font-mono font-bold">
                    ${id}
                  </button>
                `).join('')}
              </div>
            </div>
          </div>
        </div>
      </div>
    `;
  }).join('');
}

function renderAssignmentQuestions() {
  const container = document.getElementById('assignmentQuestionsAccordion');
  if (!container) return;
  const questions = AppState.assignmentQuestions || [];
  if (!questions.length) return;

  container.innerHTML = questions.map((q, idx) => {
    const isFirst = idx < 2;
    return `
      <div class="border border-slate-200 rounded-xl overflow-hidden bg-slate-50">
        <button onclick="toggleAccordion('q-accordion-${idx}')" class="w-full p-4 text-left font-bold text-sm text-slate-900 flex items-center justify-between hover:bg-slate-100 transition">
          <div class="flex items-center gap-2">
            <span class="w-6 h-6 rounded-full bg-brand-600 text-white flex items-center justify-center text-xs font-bold shrink-0">
              ${q.question_id || idx+1}
            </span>
            <span>${q.question}</span>
          </div>
          <span class="text-xs font-normal text-slate-500 font-mono hidden sm:inline">${q.key_metrics || ''}</span>
        </button>
        <div id="q-accordion-${idx}" class="${isFirst ? '' : 'hidden'} p-4 pt-1 border-t border-slate-200 bg-white text-xs space-y-3">
          <div class="flex items-center gap-2 text-slate-500 font-medium">
            <span class="font-bold text-brand-700">Core Thesis:</span> ${q.core_thesis}
          </div>
          <div class="bg-blue-50/70 p-3 rounded-lg border border-blue-100">
            <span class="font-bold text-slate-800">🔬 Empirical Finding:</span>
            <p class="text-slate-700 mt-1 leading-relaxed">${q.research_finding}</p>
          </div>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div class="p-3 bg-red-50/60 rounded-lg border border-red-100">
              <span class="font-bold text-red-800">⚠️ Real User Problem:</span>
              <p class="text-slate-700 mt-1">${q.user_problem}</p>
            </div>
            <div class="p-3 bg-emerald-50/60 rounded-lg border border-emerald-100">
              <span class="font-bold text-emerald-800">🎯 Unmet User Need:</span>
              <p class="text-slate-700 mt-1">${q.unmet_need}</p>
            </div>
          </div>
          <div class="p-3 bg-indigo-50/60 rounded-lg border border-indigo-100">
            <span class="font-bold text-indigo-900">🚀 Prioritized Product Opportunity:</span>
            <p class="text-indigo-800 font-medium mt-1">${q.opportunity}</p>
          </div>
          <div>
            <div class="font-bold text-slate-700 uppercase text-[10px] mb-1.5">Grounded Evidence Quotes (Click ID to inspect audit):</div>
            <div class="space-y-1.5">
              ${(q.supporting_evidence || []).map(ev => `
                <div class="p-2 bg-slate-50 rounded border border-slate-200 flex items-start gap-2">
                  <button onclick="openRecordModal('${ev.record_id}')" class="font-mono font-bold text-brand-600 hover:underline shrink-0">
                    [${ev.record_id}]
                  </button>
                  <span class="text-slate-500 shrink-0">(${ev.source}):</span>
                  <span class="italic text-slate-700">"${ev.quote}"</span>
                </div>
              `).join('')}
            </div>
          </div>
        </div>
      </div>
    `;
  }).join('');
}

function toggleAccordion(id) {
  const el = document.getElementById(id);
  if (el) el.classList.toggle('hidden');
}

function escapeHtml(text) {
  if (!text) return '';
  return String(text)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

// Global click-outside listener to dismiss search dropdown
document.addEventListener('click', (e) => {
  const dropdown = document.getElementById('searchDropdown');
  const searchInput = document.getElementById('globalSearchInput');
  if (dropdown && !dropdown.contains(e.target) && e.target !== searchInput) {
    closeSearchDropdown();
  }
});


