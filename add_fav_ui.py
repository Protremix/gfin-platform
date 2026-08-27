#!/usr/bin/env python3
"""Add favorites UI to investigator workbench"""

with open("/gfin/investigator_workbench.html", "r") as f:
    content = f.read()

# 1. Add CSS for favorite star
old_css = ".case-card .pattern-tag { font-size: 10px; padding: 2px 8px; border-radius: 10px; background: #f3f4f6; color: #374151; font-weight: 500; }"
new_css = old_css + """
.case-card .pattern-tag { font-size: 10px; padding: 2px 8px; border-radius: 10px; background: #f3f4f6; color: #374151; font-weight: 500; }
.case-card .fav-btn { position: absolute; top: 16px; right: 16px; background: none; border: none; cursor: pointer; font-size: 20px; color: #d1d5db; transition: all 0.2s; padding: 4px; z-index: 5; }
.case-card .fav-btn:hover { color: #fbbf24; transform: scale(1.2); }
.case-card .fav-btn.active { color: #fbbf24; }
.case-card { position: relative; }
.fav-filter { display: inline-flex; align-items: center; gap: 6px; padding: 6px 14px; border-radius: 20px; background: var(--card); border: 1px solid var(--border); cursor: pointer; font-size: 13px; font-weight: 500; color: var(--text-muted); transition: all 0.2s; }
.fav-filter:hover { border-color: #fbbf24; color: #f59e0b; }
.fav-filter.active { background: #fef3c7; border-color: #fbbf24; color: #92400e; }
.fav-filter i { font-size: 14px; }"""
content = content.replace(old_css, new_css)

# 2. Add favorites filter button before the case grid
old_cases_view = '<div id="view-cases" class="view">'
# Find the cases view section
cases_start = content.index(old_cases_view)
# Find the caseGrid div
grid_marker = 'id="caseGrid"'
grid_idx = content.index(grid_marker, cases_start)
# Find the line before caseGrid
line_start = content.rfind('\n', cases_start, grid_idx)
# Insert filter bar before the grid
filter_html = '''
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">
          <h2 class="page-title">Active Cases</h2>
          <button class="fav-filter" id="favFilterBtn" onclick="toggleFavoritesFilter()">
            <i class="fa-solid fa-star"></i> My Favorites
          </button>
        </div>
'''
content = content[:line_start+1] + filter_html + content[line_start+1:]

# 3. Add JS for favorites functionality
# Find the loadCases function and add favorite star to case cards
old_case_card = '''return `<div class="case-card" onclick="openCase('${c.case_id}')">
        <div class="case-header">
          <span class="case-id">${c.case_id}</span>
          <span class="status-badge ${statusClass}">${c.status || 'NEW'}</span>
        </div>'''

new_case_card = '''return `<div class="case-card" onclick="openCase('${c.case_id}')">
        <button class="fav-btn" onclick="event.stopPropagation();toggleFavorite('${c.case_id}', this)" data-case="${c.case_id}">
          <i class="fa-${c.is_favorite ? 'solid' : 'regular'} fa-star ${c.is_favorite ? 'active' : ''}"></i>
        </button>
        <div class="case-header">
          <span class="case-id">${c.case_id}</span>
          <span class="status-badge ${statusClass}">${c.status || 'NEW'}</span>
        </div>'''

content = content.replace(old_case_card, new_case_card)

# 4. Add favorites JS functions before the CASE DETAIL section
case_detail_marker = "// === CASE DETAIL ==="
fav_js = '''// === FAVORITES ===
let showFavoritesOnly = false;
let favoritedCases = new Set();

async function loadFavorites() {
  try {
    const data = await apiGet('/api/cases/favorites');
    favoritedCases = new Set((data.favorites || []).map(f => f.case_id));
  } catch(e) { console.error('Favorites load error:', e); }
}

async function toggleFavorite(caseId, btnEl) {
  try {
    const isFav = favoritedCases.has(caseId);
    if (isFav) {
      await apiDelete('/api/cases/' + caseId + '/favorite');
      favoritedCases.delete(caseId);
    } else {
      await apiPost('/api/cases/' + caseId + '/favorite');
      favoritedCases.add(caseId);
    }
    // Update the button
    if (btnEl) {
      const icon = btnEl.querySelector('i');
      if (favoritedCases.has(caseId)) {
        icon.className = 'fa-solid fa-star active';
        btnEl.classList.add('active');
      } else {
        icon.className = 'fa-regular fa-star';
        btnEl.classList.remove('active');
      }
    }
    // Reload cases if filter is active
    if (showFavoritesOnly) loadCasesFiltered();
  } catch(e) { console.error('Toggle favorite error:', e); }
}

function toggleFavoritesFilter() {
  showFavoritesOnly = !showFavoritesOnly;
  const btn = document.getElementById('favFilterBtn');
  if (showFavoritesOnly) {
    btn.classList.add('active');
    loadCasesFiltered();
  } else {
    btn.classList.remove('active');
    loadCases();
  }
}

async function loadCasesFiltered() {
  await loadFavorites();
  try {
    const data = await apiGet('/api/inv/board');
    const grid = document.getElementById('caseGrid');
    const favCases = (data.cases || []).filter(c => favoritedCases.has(c.case_id));
    if (favCases.length === 0) {
      grid.innerHTML = '<div class="empty-state"><i class="fa-solid fa-star" style="color:#fbbf24;"></i><h3>No favorites yet</h3><p>Click the star icon on any case to add it to your favorites</p></div>';
      return;
    }
    renderCases(favCases, grid);
  } catch(e) {
    document.getElementById('caseGrid').innerHTML = '<div class="empty-state"><i class="fa-solid fa-triangle-exclamation"></i><h3>Error loading favorites</h3></div>';
  }
}

// Also mark favorites when loading regular cases
const _originalLoadCases = loadCases;
loadCases = async function() {
  await loadFavorites();
  await _originalLoadCases();
  // Update star states
  document.querySelectorAll('.fav-btn').forEach(btn => {
    const caseId = btn.dataset.case;
    if (favoritedCases.has(caseId)) {
      btn.querySelector('i').className = 'fa-solid fa-star active';
      btn.classList.add('active');
    }
  });
};

'''

content = content.replace(case_detail_marker, fav_js + case_detail_marker)

# 5. Add apiDelete helper if it doesn't exist
if 'async function apiDelete' not in content:
    # Find apiPost and add apiDelete after it
    api_post_end = content.find('async function apiPost')
    if api_post_end > -1:
        # Find the end of apiPost function
        brace_count = 0
        i = content.index('{', api_post_end)
        while i < len(content):
            if content[i] == '{': brace_count += 1
            elif content[i] == '}': brace_count -= 1
            if brace_count == 0:
                break
            i += 1
        insert_point = content.index('\n', i) + 1
        api_delete_func = '''
async function apiDelete(url) {
  const token = localStorage.getItem('gfin_token');
  const res = await fetch(url, { method: 'DELETE', headers: { 'Authorization': 'Bearer ' + token } });
  if (!res.ok) throw new Error('API error: ' + res.status);
  return res.json();
}

'''
        content = content[:insert_point] + api_delete_func + content[insert_point:]

with open("/gfin/investigator_workbench.html", "w") as f:
    f.write(content)
print("Favorites UI added to dashboard")
