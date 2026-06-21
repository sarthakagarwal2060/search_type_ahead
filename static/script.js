const searchInput = document.getElementById('searchInput');
const clearButton = document.getElementById('clearButton');
const searchButton = document.getElementById('searchButton');
const suggestionsBox = document.getElementById('suggestionsBox');
const suggestionsList = document.getElementById('suggestionsList');
const trendingList = document.getElementById('trendingList');
const debugToggle = document.getElementById('debugToggle');
const debugInfo = document.getElementById('debugInfo');
const debugContent = document.getElementById('debugContent');
const toast = document.getElementById('toast');

let currentFocus = -1;
const API_BASE = '';

// Format number (e.g., 1500000 -> 1.5M, 1500 -> 1.5k)
function formatNumber(num) {
    if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
    if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
    return num;
}

// Debounce function
function debounce(func, delay) {
    let timer = null;
    return function() {
        const context = this;
        const args = arguments;
        clearTimeout(timer);
        timer = setTimeout(() => func.apply(context, args), delay);
    }
}

const debouncedFetchSuggestions = debounce(fetchSuggestions, 300);

// Fetch Suggestions
async function fetchSuggestions(query) {
    if (!query.trim()) {
        suggestionsBox.classList.add('hidden');
        fetchTrending();
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/suggest?q=${encodeURIComponent(query)}`);
        const data = await response.json();
        
        const results = data.results || [];
        const meta = data.meta || null;
        
        renderSuggestions(results, query);
        
        if (debugToggle.checked && meta) {
            debugContent.textContent = JSON.stringify(meta, null, 2);
        }
    } catch (error) {
        console.error("Error fetching suggestions:", error);
    }
}

// Render Suggestions
function renderSuggestions(suggestions, query) {
    suggestionsList.innerHTML = '';
    currentFocus = -1;

    if (suggestions.length === 0) {
        const li = document.createElement('li');
        li.innerHTML = `<span class="suggestion-text" style="color: var(--text-secondary)">No results found</span>`;
        suggestionsList.appendChild(li);
        suggestionsBox.classList.remove('hidden');
        return;
    }

    suggestions.forEach(item => {
        const li = document.createElement('li');
        
        // Highlight matching prefix
        const lowerItem = item.query.toLowerCase();
        const lowerQuery = query.toLowerCase();
        
        let htmlText = item.query;
        if (lowerItem.startsWith(lowerQuery)) {
            const match = item.query.substring(0, query.length);
            const remainder = item.query.substring(query.length);
            htmlText = `<span class="suggestion-highlight">${match}</span>${remainder}`;
        }
        
        li.innerHTML = `
            <span class="suggestion-text">${htmlText}</span>
            <span class="suggestion-meta">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 12h-4l-3 9L9 3l-3 9H2"></path></svg>
                ${formatNumber(item.count)}
            </span>
        `;
        
        li.addEventListener('click', () => {
            searchInput.value = item.query;
            submitSearch(item.query);
        });
        
        suggestionsList.appendChild(li);
    });
    
    suggestionsBox.classList.remove('hidden');
}

// Fetch Trending
async function fetchTrending() {
    try {
        const response = await fetch(`${API_BASE}/suggest?q=`);
        const data = await response.json();
        const results = data.results || [];
        renderTrending(results);
    } catch (error) {
        console.error("Error fetching trending:", error);
    }
}

// Render Trending
function renderTrending(data) {
    trendingList.innerHTML = '';
    data.forEach(item => {
        const tag = document.createElement('div');
        tag.className = 'tag';
        tag.innerHTML = `
            <svg class="tag-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"></polyline><polyline points="17 6 23 6 23 12"></polyline></svg>
            ${item.query}
        `;
        tag.addEventListener('click', () => {
            searchInput.value = item.query;
            submitSearch(item.query);
        });
        trendingList.appendChild(tag);
    });
}

// Debug info is now handled inline in fetchSuggestions

// Submit Search
async function submitSearch(query) {
    if (!query.trim()) return;
    
    suggestionsBox.classList.add('hidden');
    
    try {
        const response = await fetch(`${API_BASE}/search`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: query })
        });
        const data = await response.json();
        
        showToast(`Search confirmed: "${query}"`);
        
        // Simulate immediate update for trending if empty
        if (searchInput.value === '') {
            setTimeout(fetchTrending, 1000);
        }
    } catch (error) {
        console.error("Search failed:", error);
    }
}

function showToast(message) {
    toast.textContent = message;
    toast.classList.remove('hidden');
    toast.classList.add('show');
    
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.classList.add('hidden'), 300);
    }, 3000);
}

// Event Listeners
searchInput.addEventListener('input', (e) => {
    const val = e.target.value;
    clearButton.classList.toggle('hidden', val.length === 0);
    debouncedFetchSuggestions(val);
});

searchInput.addEventListener('focus', () => {
    if (searchInput.value.trim().length > 0) {
        fetchSuggestions(searchInput.value);
    }
});

document.addEventListener('click', (e) => {
    if (!e.target.closest('.search-wrapper')) {
        suggestionsBox.classList.add('hidden');
    }
});

clearButton.addEventListener('click', () => {
    searchInput.value = '';
    clearButton.classList.add('hidden');
    suggestionsBox.classList.add('hidden');
    searchInput.focus();
    fetchTrending();
});

searchButton.addEventListener('click', () => {
    submitSearch(searchInput.value);
});

// Keyboard navigation
searchInput.addEventListener('keydown', (e) => {
    const items = suggestionsList.getElementsByTagName('li');
    if (!items.length) {
        if (e.key === 'Enter') {
            submitSearch(searchInput.value);
        }
        return;
    }
    
    if (e.key === 'ArrowDown') {
        currentFocus++;
        addActive(items);
        e.preventDefault();
    } else if (e.key === 'ArrowUp') {
        currentFocus--;
        addActive(items);
        e.preventDefault();
    } else if (e.key === 'Enter') {
        e.preventDefault();
        if (currentFocus > -1) {
            items[currentFocus].click();
        } else {
            submitSearch(searchInput.value);
        }
    }
});

function addActive(items) {
    if (!items) return false;
    removeActive(items);
    if (currentFocus >= items.length) currentFocus = 0;
    if (currentFocus < 0) currentFocus = (items.length - 1);
    items[currentFocus].classList.add("active");
    // Scroll into view
    items[currentFocus].scrollIntoView({ block: 'nearest' });
}

function removeActive(items) {
    for (let i = 0; i < items.length; i++) {
        items[i].classList.remove("active");
    }
}

debugToggle.addEventListener('change', (e) => {
    if (e.target.checked) {
        debugInfo.classList.remove('hidden');
    } else {
        debugInfo.classList.add('hidden');
    }
});

// Init
fetchTrending();
