// State Management
let state = {
    user: null,
    accessToken: null,
    refreshToken: null,
    activeTab: 'dashboard',
    keys: [],
    logs: [],
    sessionRawKeys: {}, // Maps key ID -> raw API key (for keys generated during current session)
    providersModels: {}, // Maps provider name -> array of dynamic models
    totals: {
        total_requests: 0,
        total_prompt_tokens: 0,
        total_completion_tokens: 0,
        total_tokens: 0,
        total_cost: 0,
        average_latency_ms: 0
    },
    charts: {
        latency: null,
        model: null,
        latencyCompare: null,
        errorType: null
    },
    refreshIntervalId: null,
    
    // Phase 9 Prompt Registry state
    prompts: [],
    selectedPrompt: null,
    selectedPromptVersions: [],
    selectedPromptExperiment: null,
    sandboxVariables: {},
    sandboxRating: 0,
    sandboxTraceId: null
};


// DOM Elements
const elements = {
    loadingScreen: document.getElementById('loading-screen'),
    toastContainer: document.getElementById('toast-container'),
    authContainer: document.getElementById('auth-container'),
    dashboardContainer: document.getElementById('dashboard-container'),
    loginForm: document.getElementById('login-form'),
    registerForm: document.getElementById('register-form'),
    toggleToRegister: document.getElementById('toggle-to-register'),
    toggleToLogin: document.getElementById('toggle-to-login'),
    authTitle: document.getElementById('auth-title'),
    authSubtitle: document.getElementById('auth-subtitle'),
    
    // Sidebar & Profile
    sidebarUserEmail: document.getElementById('sidebar-user-email'),
    userAvatarChar: document.getElementById('user-avatar-char'),
    logoutBtn: document.getElementById('logout-btn'),
    navItems: document.querySelectorAll('.nav-item'),
    tabPanels: document.querySelectorAll('.tab-panel'),
    pageTitle: document.getElementById('page-title'),
    pageDescription: document.getElementById('page-description'),
    refreshDashboardBtn: document.getElementById('refresh-dashboard-btn'),

    // Dashboard metrics
    statRequests: document.getElementById('stat-requests'),
    statCost: document.getElementById('stat-cost'),
    statTokens: document.getElementById('stat-tokens'),
    statTokensRatio: document.getElementById('stat-tokens-ratio'),
    statLatency: document.getElementById('stat-latency'),
    
    // Cache stats
    statCacheHitRate: document.getElementById('stat-cache-hit-rate'),
    statCacheHitsRatio: document.getElementById('stat-cache-hits-ratio'),
    statCacheTokensSaved: document.getElementById('stat-cache-tokens-saved'),
    statCacheSpendSaved: document.getElementById('stat-cache-spend-saved'),
    statCacheLatencySaved: document.getElementById('stat-cache-latency-saved'),
    
    logsTbody: document.getElementById('logs-tbody'),
    logsCountBadge: document.getElementById('logs-count-badge'),

    // Keys View
    keysTbody: document.getElementById('keys-tbody'),
    openCreateKeyModalBtn: document.getElementById('open-create-key-modal-btn'),
    createKeyModal: document.getElementById('create-key-modal'),
    createKeyForm: document.getElementById('create-key-form'),
    revealKeyModal: document.getElementById('reveal-key-modal'),
    revealKeyCode: document.getElementById('reveal-key-code'),
    copyKeyBtn: document.getElementById('copy-key-btn'),
    acknowledgeKeyBtn: document.getElementById('acknowledge-key-btn'),
    
    // Rename Key Modal
    renameKeyModal: document.getElementById('rename-key-modal'),
    renameKeyForm: document.getElementById('rename-key-form'),
    renameKeyNameInput: document.getElementById('rename-key-name-input'),
    renameKeyId: document.getElementById('rename-key-id'),
    
    // Playground View
    playgroundKeySelect: document.getElementById('playground-key-select'),
    playgroundRawKeyInput: document.getElementById('playground-raw-key-input'),
    playgroundRoutingMode: document.getElementById('playground-routing-mode'),
    playgroundDirectProviderGroup: document.getElementById('playground-direct-provider-group'),
    playgroundDirectModelGroup: document.getElementById('playground-direct-model-group'),
    playgroundProviderSelect: document.getElementById('playground-provider-select'),
    playgroundModelSelect: document.getElementById('playground-model-select'),
    playgroundPolicyGroup: document.getElementById('playground-policy-group'),
    playgroundFallbackGroup: document.getElementById('playground-fallback-group'),
    playgroundPolicySelect: document.getElementById('playground-policy-select'),
    playgroundFallbackInput: document.getElementById('playground-fallback-input'),
    playgroundTemperature: document.getElementById('playground-temperature'),
    temperatureVal: document.getElementById('temperature-val'),
    playgroundMaxTokens: document.getElementById('playground-max-tokens'),
    playgroundBypassCache: document.getElementById('playground-bypass-cache'),
    clearChatBtn: document.getElementById('clear-chat-btn'),
    chatMessagesContainer: document.getElementById('chat-messages-container'),
    chatForm: document.getElementById('chat-form'),
    chatInputTextarea: document.getElementById('chat-input-textarea'),
    chatSendBtn: document.getElementById('chat-send-btn'),

    // Log Detail Modal
    logDetailModal: document.getElementById('log-detail-modal'),
    detailReqId: document.getElementById('detail-req-id'),
    detailCacheType: document.getElementById('detail-cache-type'),
    detailCostSaved: document.getElementById('detail-cost-saved'),
    detailTimestamp: document.getElementById('detail-timestamp'),
    detailModel: document.getElementById('detail-model'),
    detailStatus: document.getElementById('detail-status'),
    detailLatency: document.getElementById('detail-latency'),
    detailCost: document.getElementById('detail-cost'),
    detailTokens: document.getElementById('detail-tokens'),
    detailIp: document.getElementById('detail-ip'),
    detailErrorContainer: document.getElementById('detail-error-container'),
    detailErrorMessage: document.getElementById('detail-error-message'),
    
    // Quota details
    planNameBadge: document.getElementById('plan-name-badge'),
    planUpgradeSelect: document.getElementById('plan-upgrade-select'),
    requestsQuotaRatio: document.getElementById('requests-quota-ratio'),
    requestsQuotaBar: document.getElementById('requests-quota-bar'),
    tokensQuotaRatio: document.getElementById('tokens-quota-ratio'),
    tokensQuotaBar: document.getElementById('tokens-quota-bar'),

    // Provider Health Status
    providerHealthTbody: document.getElementById('provider-health-tbody'),
    providerHealthUpdateTime: document.getElementById('provider-health-update-time'),

    // Observability View
    obsStatToday: document.getElementById('obs-stat-today'),
    obsStatWeek: document.getElementById('obs-stat-week'),
    obsStatMonth: document.getElementById('obs-stat-month'),
    tracesTbody: document.getElementById('traces-tbody'),
    tracesCountBadge: document.getElementById('traces-count-badge'),
    
    // Trace Detail Modal
    traceDetailModal: document.getElementById('trace-detail-modal'),
    traceDetailId: document.getElementById('trace-detail-id'),
    traceDetailLatency: document.getElementById('trace-detail-latency'),
    traceDetailTimestamp: document.getElementById('trace-detail-timestamp'),
    traceDetailStatus: document.getElementById('trace-detail-status'),
    traceTimelineFlow: document.getElementById('trace-timeline-flow'),
    traceAttemptsList: document.getElementById('trace-attempts-list'),
    traceDetailPrompt: document.getElementById('trace-detail-prompt'),
    traceDetailResponse: document.getElementById('trace-detail-response'),
    
    // Content Safety Elements
    safetyStatBlocked: document.getElementById('safety-stat-blocked'),
    safetyStatWarned: document.getElementById('safety-stat-warned'),
    safetyStatMasked: document.getElementById('safety-stat-masked'),
    safetyStatTopKey: document.getElementById('safety-stat-top-key'),
    guardrailsCountBadge: document.getElementById('guardrails-count-badge'),
    guardrailsTbody: document.getElementById('guardrails-tbody'),
    
    // Sandbox Elements
    sandboxPromptTextarea: document.getElementById('sandbox-prompt-textarea'),
    runSandboxSafetyBtn: document.getElementById('run-sandbox-safety-btn'),
    sandboxPolicyPii: document.getElementById('sandbox-policy-pii'),
    sandboxPolicyInjection: document.getElementById('sandbox-policy-injection'),
    sandboxPolicyToxicity: document.getElementById('sandbox-policy-toxicity'),
    sandboxPolicyChars: document.getElementById('sandbox-policy-chars'),
    sandboxPolicyStrict: document.getElementById('sandbox-policy-strict'),
    sandboxResultsCard: document.getElementById('sandbox-results-card'),
    sandboxAllowedBadge: document.getElementById('sandbox-allowed-badge'),
    sandboxMaskedOutput: document.getElementById('sandbox-masked-output'),
    sandboxViolationsTbody: document.getElementById('sandbox-violations-tbody')
};

// Initialize App
window.addEventListener('DOMContentLoaded', () => {
    // Setup general event listeners
    initEventListeners();
    
    // Try to auto-login using saved refresh token
    const savedRefreshToken = localStorage.getItem('gateway_refresh_token');
    if (savedRefreshToken) {
        performTokenRefresh(savedRefreshToken)
            .then(() => {
                showDashboardScreen();
                showToast('Welcome back!', 'Session restored successfully.', 'success');
            })
            .catch(() => {
                localStorage.removeItem('gateway_refresh_token');
                showAuthScreen();
            })
            .finally(() => {
                hideLoadingScreen();
            });
    } else {
        showAuthScreen();
        hideLoadingScreen();
    }
});

// Event Listeners
function initEventListeners() {
    // Auth Toggles
    elements.toggleToRegister.addEventListener('click', showRegisterForm);
    elements.toggleToLogin.addEventListener('click', showLoginForm);

    // Auth Form Submits
    elements.loginForm.addEventListener('submit', handleLogin);
    elements.registerForm.addEventListener('submit', handleRegister);
    elements.logoutBtn.addEventListener('click', handleLogout);

    // Navigation Tabs Toggle
    elements.navItems.forEach(item => {
        item.addEventListener('click', () => {
            const targetTab = item.getAttribute('data-tab');
            if (targetTab && targetTab !== 'logout') {
                switchTab(targetTab);
            }
        });
    });

    // Refresh Dashboard Button
    elements.refreshDashboardBtn.addEventListener('click', () => {
        if (state.accessToken) {
            elements.refreshDashboardBtn.classList.add('loading');
            refreshAllData().finally(() => {
                elements.refreshDashboardBtn.classList.remove('loading');
            });
        }
    });

    // Keys Modal actions
    elements.openCreateKeyModalBtn.addEventListener('click', () => showModal(elements.createKeyModal));
    
    document.querySelectorAll('.close-modal-trigger').forEach(trigger => {
        trigger.addEventListener('click', (e) => {
            e.preventDefault();
            const modal = trigger.closest('.modal-overlay');
            if (modal) {
                hideModal(modal);
            }
        });
    });

    // Close modal when clicking outside on the backdrop
    document.querySelectorAll('.modal-overlay').forEach(modal => {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                hideModal(modal);
            }
        });
    });

    elements.createKeyForm.addEventListener('submit', handleCreateKey);
    elements.renameKeyForm.addEventListener('submit', handleRenameKeySubmit);
    
    elements.copyKeyBtn.addEventListener('click', () => {
        const keyText = elements.revealKeyCode.textContent;
        navigator.clipboard.writeText(keyText).then(() => {
            showToast('Copied!', 'API key copied to clipboard.', 'success');
        });
    });

    elements.acknowledgeKeyBtn.addEventListener('click', () => {
        hideModal(elements.revealKeyModal);
        refreshAllData();
    });

    // Plan switcher action
    elements.planUpgradeSelect.addEventListener('change', () => {
        const selectedPlan = elements.planUpgradeSelect.value;
        handlePlanUpgrade(selectedPlan);
    });

    // Playground Form & Actions
    elements.playgroundTemperature.addEventListener('input', (e) => {
        elements.temperatureVal.textContent = e.target.value;
    });

    elements.playgroundKeySelect.addEventListener('change', () => {
        const keyId = elements.playgroundKeySelect.value;
        if (state.sessionRawKeys[keyId]) {
            elements.playgroundRawKeyInput.value = state.sessionRawKeys[keyId];
            elements.playgroundRawKeyInput.placeholder = "(Loaded from session)";
        } else {
            elements.playgroundRawKeyInput.value = '';
            elements.playgroundRawKeyInput.placeholder = "Paste raw gw_live_... key";
        }
    });

    elements.clearChatBtn.addEventListener('click', clearPlaygroundChat);
    elements.chatForm.addEventListener('submit', handlePlaygroundChatSubmit);

    // Textarea Auto-height and trigger submit on Enter
    elements.chatInputTextarea.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            elements.chatForm.dispatchEvent(new Event('submit'));
        }
    });

    // Playground Model Selection dynamic update
    elements.playgroundProviderSelect.addEventListener('change', updatePlaygroundModels);

    // Playground Routing Mode toggle listener
    elements.playgroundRoutingMode.addEventListener('change', () => {
        const mode = elements.playgroundRoutingMode.value;
        if (mode === 'direct') {
            elements.playgroundDirectProviderGroup.classList.remove('hidden');
            elements.playgroundDirectModelGroup.classList.remove('hidden');
            elements.playgroundPolicyGroup.classList.add('hidden');
            elements.playgroundFallbackGroup.classList.add('hidden');
        } else {
            elements.playgroundDirectProviderGroup.classList.add('hidden');
            elements.playgroundDirectModelGroup.classList.add('hidden');
            elements.playgroundPolicyGroup.classList.remove('hidden');
            elements.playgroundFallbackGroup.classList.remove('hidden');
        }
    });

    // Sandbox Safety analyze button listener
    elements.runSandboxSafetyBtn.addEventListener('click', handleSandboxSafetySubmit);
    
    // Phase 9 Prompt Registry Event Listeners
    initPromptEventListeners();
}


// UI State Switchers
function showLoadingScreen() {
    elements.loadingScreen.classList.remove('hidden');
}

function hideLoadingScreen() {
    elements.loadingScreen.classList.add('hidden');
}

function showAuthScreen() {
    elements.authContainer.classList.remove('hidden');
    elements.dashboardContainer.classList.add('hidden');
    showLoginForm();
}

function showDashboardScreen() {
    elements.authContainer.classList.add('hidden');
    elements.dashboardContainer.classList.remove('hidden');
    
    // Set user profile visuals
    elements.sidebarUserEmail.textContent = state.user.email;
    elements.userAvatarChar.textContent = state.user.email.charAt(0).toUpperCase();
    
    // Default Tab
    switchTab('dashboard');
    refreshAllData();
    fetchProvidersModels();
    
    // Start Token Refresh cycle
    startTokenRefreshTimer();
}

function showLoginForm() {
    elements.registerForm.classList.add('hidden');
    elements.loginForm.classList.remove('hidden');
    elements.authTitle.textContent = "Welcome Back";
    elements.authSubtitle.textContent = "Log in to manage your API keys and track analytics";
}

function showRegisterForm() {
    elements.loginForm.classList.add('hidden');
    elements.registerForm.classList.remove('hidden');
    elements.authTitle.textContent = "Create Account";
    elements.authSubtitle.textContent = "Sign up to start routing queries securely through the gateway";
}

function showModal(modalEl) {
    modalEl.classList.remove('hidden');
}

function hideModal(modalEl) {
    modalEl.classList.add('hidden');
}

// Navigation Tab Switcher
function switchTab(tabId) {
    state.activeTab = tabId;
    const mainContent = document.querySelector('.main-content');

    // Update active nav button
    elements.navItems.forEach(item => {
        if (item.getAttribute('data-tab') === tabId) {
            item.classList.add('active');
        } else {
            item.classList.remove('active');
        }
    });

    // Update active panel display
    elements.tabPanels.forEach(panel => {
        if (panel.id === `tab-${tabId}`) {
            panel.classList.add('active');
        } else {
            panel.classList.remove('active');
        }
    });

    // Playground needs to fill the remaining height so the chat box scrolls.
    // All other tabs let the main content scroll normally.
    if (tabId === 'playground') {
        mainContent.classList.add('playground-active');
    } else {
        mainContent.classList.remove('playground-active');
    }

    // Update Titles
    switch (tabId) {
        case 'dashboard':
            elements.pageTitle.textContent = "Analytics Dashboard";
            elements.pageDescription.textContent = "Real-time usage metrics and cost estimation stats";
            elements.refreshDashboardBtn.classList.remove('hidden');
            break;
        case 'api-keys':
            elements.pageTitle.textContent = "API Keys Management";
            elements.pageDescription.textContent = "Manage developer gateway tokens and configure expiration";
            elements.refreshDashboardBtn.classList.remove('hidden');
            break;
        case 'playground':
            elements.pageTitle.textContent = "Interactive Playground";
            elements.pageDescription.textContent = "Test your LLM Gateway configuration and prompt responses in real time";
            elements.refreshDashboardBtn.classList.add('hidden');
            break;
        case 'observability':
            elements.pageTitle.textContent = "Observability & Tracing";
            elements.pageDescription.textContent = "Track end-to-end request pipelines, retries, and error categorization";
            elements.refreshDashboardBtn.classList.remove('hidden');
            break;
        case 'guardrails':
            elements.pageTitle.textContent = "Content Safety & AI Governance";
            elements.pageDescription.textContent = "Monitor prompt injection detections, jailbreak blocks, PII redactions, and dry-run safety sandbox configurations";
            elements.refreshDashboardBtn.classList.remove('hidden');
            fetchGuardrailData().then(() => updateGuardrailsUI());
            break;
        case 'prompts':
            elements.pageTitle.textContent = "Prompt Registry & Evaluation";
            elements.pageDescription.textContent = "Create templates, manage versions, configure A/B tests, and compare analytics across versions.";
            elements.refreshDashboardBtn.classList.add('hidden');
            fetchPrompts();
            break;
        case 'benchmarks':
            elements.pageTitle.textContent = "Model Leaderboard & Benchmarks";
            elements.pageDescription.textContent = "Empirically evaluate and benchmark models across Quality, P50/P95 Latency, Cost, Throughput, and Reliability.";
            elements.refreshDashboardBtn.classList.add('hidden');
            fetchLeaderboard();
            fetchBenchmarkJobs();
            break;
    }


    lucide.createIcons();

}

// Toast System
function showToast(title, message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    
    let iconName = 'info';
    if (type === 'success') iconName = 'check-circle';
    if (type === 'error') iconName = 'alert-octagon';
    if (type === 'warning') iconName = 'alert-triangle';

    toast.innerHTML = `
        <i data-lucide="${iconName}"></i>
        <div class="toast-content">
            <h4>${title}</h4>
            <p>${message}</p>
        </div>
        <button class="toast-close"><i data-lucide="x"></i></button>
    `;
    
    elements.toastContainer.appendChild(toast);
    lucide.createIcons();

    // Trigger slide-in
    setTimeout(() => toast.classList.add('show'), 10);

    // Auto dismiss after 4 seconds
    const dismissTimeout = setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 4000);

    toast.querySelector('.toast-close').addEventListener('click', () => {
        clearTimeout(dismissTimeout);
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    });
}

// Authentication Handlers
async function handleLogin(e) {
    e.preventDefault();
    const email = document.getElementById('login-email').value;
    const password = document.getElementById('login-password').value;
    
    const submitBtn = e.target.querySelector('button[type="submit"]');
    setButtonState(submitBtn, true, "Logging in...");

    try {
        const response = await fetch('/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });

        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || 'Failed to authenticate');
        }

        const data = await response.json();
        state.accessToken = data.access_token;
        state.refreshToken = data.refresh_token;
        localStorage.setItem('gateway_refresh_token', data.refresh_token);

        // Fetch User Info
        await fetchUserProfile();
        showDashboardScreen();
        showToast('Access Granted', `Logged in as ${email}`, 'success');
    } catch (error) {
        showToast('Login Failed', error.message, 'error');
    } finally {
        setButtonState(submitBtn, false, "Log In", "arrow-right");
    }
}

async function handleRegister(e) {
    e.preventDefault();
    const email = document.getElementById('register-email').value;
    const password = document.getElementById('register-password').value;

    const submitBtn = e.target.querySelector('button[type="submit"]');
    setButtonState(submitBtn, true, "Registering...");

    try {
        const response = await fetch('/api/auth/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });

        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || 'Registration failed');
        }

        showToast('Success!', 'Registration successful. Please log in.', 'success');
        showLoginForm();
    } catch (error) {
        showToast('Registration Error', error.message, 'error');
    } finally {
        setButtonState(submitBtn, false, "Create Account", "user-plus");
    }
}

async function handleLogout() {
    const tokenToRevoke = state.refreshToken;
    
    // Clear Client state
    state.user = null;
    state.accessToken = null;
    state.refreshToken = null;
    localStorage.removeItem('gateway_refresh_token');
    
    if (state.refreshIntervalId) {
        clearInterval(state.refreshIntervalId);
        state.refreshIntervalId = null;
    }

    showAuthScreen();
    showToast('Signed Out', 'You have been safely logged out.', 'info');

    // Call backend logout asynchronously (fire-and-forget style)
    if (tokenToRevoke) {
        fetch('/api/auth/logout', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ refresh_token: tokenToRevoke })
        }).catch(err => console.error("Error revoking token on backend:", err));
    }
}

async function fetchUserProfile() {
    const response = await fetch('/api/auth/me', {
        headers: { 'Authorization': `Bearer ${state.accessToken}` }
    });
    if (!response.ok) throw new Error('Could not fetch user profile details.');
    state.user = await response.json();
}

// Auth Token Rotation
async function performTokenRefresh(savedRefreshToken) {
    const response = await fetch('/api/auth/refresh', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: savedRefreshToken })
    });

    if (!response.ok) throw new Error('Token refresh rejected.');

    const data = await response.json();
    state.accessToken = data.access_token;
    state.refreshToken = data.refresh_token;
    localStorage.setItem('gateway_refresh_token', data.refresh_token);
    
    await fetchUserProfile();
    return true;
}

function startTokenRefreshTimer() {
    if (state.refreshIntervalId) clearInterval(state.refreshIntervalId);
    
    // Refresh tokens every 10 minutes (access token validity is 15 minutes)
    state.refreshIntervalId = setInterval(() => {
        if (state.refreshToken) {
            performTokenRefresh(state.refreshToken)
                .then(() => console.log("Silent access token rotation successful"))
                .catch(() => {
                    showToast('Session Expired', 'Please log in again to continue.', 'error');
                    handleLogout();
                });
        }
    }, 10 * 60 * 1000);
}

// Data Synchronization & Loading
async function refreshAllData() {
    if (!state.accessToken) return;
    
    try {
        await Promise.all([
            fetchUsageData(),
            fetchKeysData(),
            fetchQuotaData(),
            fetchProviderHealthData(),
            fetchObservabilityData(),
            fetchCacheStats(),
            fetchGuardrailData()
        ]);
        
        updateDashboardUI();
        updateKeysUI();
        updatePlaygroundUI();
        updateQuotaUI();
        updateProviderHealthUI();
        updateObservabilityUI();
        updateCacheStatsUI();
        updateGuardrailsUI();
    } catch (error) {
        console.error("Data refresh failed", error);
        showToast('Refresh Failed', 'Unable to sync metrics with gateway database.', 'error');
    }
}

async function fetchCacheStats() {
    const response = await fetch('/api/cache/stats', {
        headers: { 'Authorization': `Bearer ${state.accessToken}` }
    });
    if (!response.ok) throw new Error('Failed to fetch cache stats.');
    state.cacheStats = await response.json();
}

function updateCacheStatsUI() {
    if (!state.cacheStats) return;
    
    const cs = state.cacheStats;
    elements.statCacheHitRate.textContent = `${(cs.hit_rate * 100).toFixed(1)}%`;
    elements.statCacheHitsRatio.textContent = `Exact: ${cs.exact_hits.toLocaleString()} | Semantic: ${cs.semantic_hits.toLocaleString()}`;
    elements.statCacheTokensSaved.textContent = cs.tokens_saved.toLocaleString();
    elements.statCacheSpendSaved.textContent = formatCost(cs.spend_saved);
    elements.statCacheLatencySaved.textContent = `${Math.round(cs.average_latency_saved_ms)} ms`;
}

async function fetchUsageData() {
    const response = await fetch('/api/usage', {
        headers: { 'Authorization': `Bearer ${state.accessToken}` }
    });
    if (!response.ok) throw new Error('Failed to get usage dashboard data.');
    const data = await response.json();
    state.logs = data.logs;
    state.totals = {
        total_requests: data.total_requests,
        total_prompt_tokens: data.total_prompt_tokens,
        total_completion_tokens: data.total_completion_tokens,
        total_tokens: data.total_tokens,
        total_cost: data.total_cost,
        average_latency_ms: data.average_latency_ms
    };
}

async function fetchKeysData() {
    const response = await fetch('/api/api-keys', {
        headers: { 'Authorization': `Bearer ${state.accessToken}` }
    });
    if (!response.ok) throw new Error('Failed to fetch API keys.');
    state.keys = await response.json();
}

async function fetchQuotaData() {
    const response = await fetch('/api/usage/quota', {
        headers: { 'Authorization': `Bearer ${state.accessToken}` }
    });
    if (!response.ok) throw new Error('Failed to fetch quota data.');
    state.quota = await response.json();
}

function updateQuotaUI() {
    if (!state.quota) return;
    
    const q = state.quota;
    
    // Update plan badge
    elements.planNameBadge.textContent = q.plan.charAt(0).toUpperCase() + q.plan.slice(1);
    elements.planUpgradeSelect.value = q.plan;
    
    // Calculate requests ratio
    const reqRatio = q.request_limit > 0 ? (q.requests_today / q.request_limit) : 0;
    const reqPercent = Math.min(Math.round(reqRatio * 100), 100);
    elements.requestsQuotaRatio.textContent = `${q.requests_today} / ${q.request_limit.toLocaleString()} requests`;
    elements.requestsQuotaBar.style.width = `${reqPercent}%`;
    elements.requestsQuotaBar.className = "progress-bar-fill " + getQuotaColorClass(reqRatio);
    
    // Calculate tokens ratio
    const tokRatio = q.token_limit > 0 ? (q.tokens_this_month / q.token_limit) : 0;
    const tokPercent = Math.min(Math.round(tokRatio * 100), 100);
    elements.tokensQuotaRatio.textContent = `${q.tokens_this_month.toLocaleString()} / ${q.token_limit.toLocaleString()} tokens`;
    elements.tokensQuotaBar.style.width = `${tokPercent}%`;
    elements.tokensQuotaBar.className = "progress-bar-fill " + getQuotaColorClass(tokRatio);
}

function getQuotaColorClass(ratio) {
    if (ratio >= 0.95) return "red";
    if (ratio >= 0.80) return "yellow";
    return "green";
}

async function fetchProviderHealthData() {
    const response = await fetch('/api/providers/health', {
        headers: { 'Authorization': `Bearer ${state.accessToken}` }
    });
    if (!response.ok) throw new Error('Failed to fetch provider health data.');
    state.providerHealth = await response.json();
}

function updateProviderHealthUI() {
    if (!state.providerHealth || !elements.providerHealthTbody) return;
    
    elements.providerHealthTbody.innerHTML = '';
    
    state.providerHealth.forEach(m => {
        const row = document.createElement('tr');
        
        let statusClass = 'badge-success';
        if (m.status === 'degraded') statusClass = 'badge-warning';
        if (m.status === 'unhealthy') statusClass = 'badge-error';
        
        row.innerHTML = `
            <td><strong style="color: var(--text-primary); font-size: 0.95rem;">${m.provider}</strong></td>
            <td><span class="badge ${statusClass}">${m.status}</span></td>
            <td>${m.avg_latency_ms} ms</td>
            <td>${m.success_rate.toFixed(2)}%</td>
            <td>${m.total_requests}</td>
            <td>${m.total_failures}</td>
            <td>${m.consecutive_failures}</td>
        `;
        elements.providerHealthTbody.appendChild(row);
    });
    
    elements.providerHealthUpdateTime.textContent = `Live: ${new Date().toLocaleTimeString()}`;
    lucide.createIcons();
}


async function handlePlanUpgrade(planType) {
    try {
        const response = await fetch('/api/auth/upgrade', {
            method: 'PATCH',
            headers: { 
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${state.accessToken}`
            },
            body: JSON.stringify({ plan_type: planType })
        });
        
        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || 'Upgrade failed.');
        }
        
        showToast('Plan Updated', `Successfully changed your account plan to ${planType.toUpperCase()}.`, 'success');
        refreshAllData();
    } catch (error) {
        showToast('Upgrade Error', error.message, 'error');
    }
}


async function fetchProvidersModels() {
    try {
        const response = await fetch('/api/providers/models');
        if (!response.ok) throw new Error('Failed to fetch models metadata.');
        state.providersModels = await response.json();
        
        // Populate the Model Provider select dropdown dynamically
        const prevValue = elements.playgroundProviderSelect.value;
        elements.playgroundProviderSelect.innerHTML = '';
        Object.keys(state.providersModels).forEach((provider, index) => {
            const option = document.createElement('option');
            option.value = provider;
            option.textContent = provider.charAt(0).toUpperCase() + provider.slice(1);
            if (prevValue === provider || (!prevValue && index === 0)) {
                option.selected = true;
            }
            elements.playgroundProviderSelect.appendChild(option);
        });

        // Trigger models dropdown updates
        updatePlaygroundModels();
    } catch (err) {
        console.error('Error fetching providers models:', err);
        showToast('Sync Error', 'Failed to retrieve available models from gateway.', 'error');
    }
}

function updatePlaygroundModels() {
    const selectedProvider = elements.playgroundProviderSelect.value;
    const models = state.providersModels[selectedProvider] || [];
    elements.playgroundModelSelect.innerHTML = '';
    models.forEach((model, index) => {
        const option = document.createElement('option');
        option.value = model;
        option.textContent = model;
        if (index === 0) option.selected = true;
        elements.playgroundModelSelect.appendChild(option);
    });
}

// UI Rendering - Dashboard
function updateDashboardUI() {
    // 1. Stats updates
    elements.statRequests.textContent = state.totals.total_requests.toLocaleString();
    elements.statCost.textContent = formatCost(state.totals.total_cost);
    elements.statTokens.textContent = state.totals.total_tokens.toLocaleString();
    elements.statTokensRatio.textContent = `In: ${state.totals.total_prompt_tokens.toLocaleString()} | Out: ${state.totals.total_completion_tokens.toLocaleString()}`;
    elements.statLatency.textContent = `${Math.round(state.totals.average_latency_ms)} ms`;

    // Logs Counter badge
    elements.logsCountBadge.textContent = `${state.logs.length} request logs`;

    // 2. Render Request Log Table
    elements.logsTbody.innerHTML = '';
    
    if (state.logs.length === 0) {
        elements.logsTbody.innerHTML = `
            <tr>
                <td colspan="8" class="empty-state">
                    <i data-lucide="file-text"></i>
                    <p>No usage logs found. Generate an API Key and try the Playground!</p>
                </td>
            </tr>
        `;
        lucide.createIcons();
    } else {
        // Sort logs newest first
        const sortedLogs = [...state.logs].sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
        
        sortedLogs.forEach(log => {
            const row = document.createElement('tr');
            
            // Badge style for status code
            const statusClass = log.status_code >= 200 && log.status_code < 300 ? 'badge-success' : 'badge-error';
            
            const dateStr = new Date(log.created_at).toLocaleString();
            
            row.innerHTML = `
                <td><span class="badge ${statusClass}">${log.status_code}</span></td>
                <td>${dateStr}</td>
                <td><code style="color:var(--text-primary); font-size:0.85rem;">${log.model}</code></td>
                <td>${log.latency_ms} ms</td>
                <td>${log.total_tokens.toLocaleString()}</td>
                <td style="color:var(--accent-green); font-weight:500;">${formatCost(log.cost)}</td>
                <td><span style="font-size:0.85rem; color:var(--text-secondary);">${log.ip_address || 'N/A'}</span></td>
                <td>
                    <button class="detail-btn-icon" data-log-id="${log.id}">
                        <i data-lucide="eye"></i>
                    </button>
                </td>
            `;
            elements.logsTbody.appendChild(row);
        });

        // Add event listeners to detail buttons
        elements.logsTbody.querySelectorAll('.detail-btn-icon').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const logId = btn.getAttribute('data-log-id');
                const log = state.logs.find(l => l.id === logId);
                if (log) showLogDetails(log);
            });
        });

        lucide.createIcons();
    }

    // 3. Render Charts
    renderCharts();
}

function showLogDetails(log) {
    elements.detailReqId.textContent = log.request_id;
    elements.detailTimestamp.textContent = new Date(log.created_at).toLocaleString();
    elements.detailModel.textContent = `${log.provider.toUpperCase()} (${log.model})`;
    
    // Status Code Badge
    const isSuccess = log.status_code >= 200 && log.status_code < 300;
    elements.detailStatus.innerHTML = `<span class="badge ${isSuccess ? 'badge-success' : 'badge-error'}">${log.status_code}</span>`;
    
    elements.detailLatency.textContent = `${log.latency_ms} ms`;
    elements.detailCost.textContent = formatCost(log.cost);
    elements.detailTokens.textContent = `${log.total_tokens.toLocaleString()} (Prompt: ${log.prompt_tokens.toLocaleString()} | Completion: ${log.completion_tokens.toLocaleString()})`;
    elements.detailIp.textContent = log.ip_address || 'Unknown';
    elements.detailCacheType.textContent = log.cache_type ? log.cache_type.toUpperCase() : 'NONE';
    elements.detailCostSaved.textContent = formatCost(log.cost_saved || 0.0);

    // Show/hide error message panel
    if (log.error_message) {
        elements.detailErrorContainer.classList.remove('hidden');
        elements.detailErrorMessage.textContent = log.error_message;
    } else {
        elements.detailErrorContainer.classList.add('hidden');
    }

    showModal(elements.logDetailModal);
}

// Chart Rendering Logic
function renderCharts() {
    // Collect stats data (only look at last 30 requests for cleaner plots)
    const chronologicalLogs = [...state.logs]
        .sort((a, b) => new Date(a.created_at) - new Date(b.created_at))
        .slice(-30);
    
    const dates = chronologicalLogs.map((log, index) => `#${index + 1}`);
    const latencies = chronologicalLogs.map(log => log.latency_ms);
    const costs = chronologicalLogs.map(log => log.cost);

    // 1. Latency & requests line chart
    if (state.charts.latency) {
        state.charts.latency.destroy();
    }

    const ctxLatency = document.getElementById('latencyChart').getContext('2d');
    state.charts.latency = new Chart(ctxLatency, {
        type: 'line',
        data: {
            labels: dates,
            datasets: [
                {
                    label: 'Latency (ms)',
                    data: latencies,
                    borderColor: '#7c3aed',
                    backgroundColor: 'rgba(124, 58, 237, 0.08)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.3,
                    yAxisID: 'y'
                },
                {
                    label: 'Cost ($)',
                    data: costs,
                    borderColor: '#10b981',
                    backgroundColor: 'transparent',
                    borderWidth: 2,
                    borderDash: [5, 5],
                    tension: 0.3,
                    yAxisID: 'y1'
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    labels: { color: '#9aa2c0', font: { family: 'Inter', size: 11 } }
                },
                tooltip: {
                    mode: 'index',
                    intersect: false
                }
            },
            scales: {
                x: {
                    grid: { color: 'rgba(38, 43, 71, 0.3)' },
                    ticks: { color: '#646d8a' }
                },
                y: {
                    type: 'linear',
                    display: true,
                    position: 'left',
                    grid: { color: 'rgba(38, 43, 71, 0.3)' },
                    ticks: { color: '#9aa2c0', callback: value => `${value}ms` }
                },
                y1: {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    grid: { drawOnChartArea: false },
                    ticks: { color: '#9aa2c0', callback: value => formatCost(value) }
                }
            }
        }
    });

    // 2. Model Usage Doughnut Chart
    if (state.charts.model) {
        state.charts.model.destroy();
    }

    // Count occurrences of models
    const modelCounts = {};
    state.logs.forEach(log => {
        modelCounts[log.model] = (modelCounts[log.model] || 0) + 1;
    });

    const modelLabels = Object.keys(modelCounts);
    const modelData = Object.values(modelCounts);

    const ctxModel = document.getElementById('modelChart').getContext('2d');
    state.charts.model = new Chart(ctxModel, {
        type: 'doughnut',
        data: {
            labels: modelLabels,
            datasets: [{
                data: modelData,
                backgroundColor: [
                    '#7c3aed',
                    '#f59e0b',
                    '#3b82f6',
                    '#10b981',
                    '#ef4444'
                ],
                borderWidth: 1,
                borderColor: '#171b30'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: { color: '#9aa2c0', font: { family: 'Inter', size: 11 } }
                }
            },
            cutout: '65%'
        }
    });
}

// UI Rendering - API Keys List
function updateKeysUI() {
    elements.keysTbody.innerHTML = '';

    if (state.keys.length === 0) {
        elements.keysTbody.innerHTML = `
            <tr>
                <td colspan="9" class="empty-state">
                    <i data-lucide="key-round"></i>
                    <p>No active API keys found. Click 'Generate API Key' above to create one.</p>
                </td>
            </tr>
        `;
        lucide.createIcons();
    } else {
        state.keys.forEach(key => {
            const row = document.createElement('tr');
            
            const createDate = new Date(key.created_at).toLocaleDateString();
            const expiryDate = key.expires_at ? new Date(key.expires_at).toLocaleDateString() : 'Never';
            const lastUsed = key.last_used_at ? new Date(key.last_used_at).toLocaleString() : 'Never';
            const calls = key.usage ? key.usage.total_requests : 0;
            const spend = key.usage ? formatCost(key.usage.total_cost) : '$0.00';
            
            const badgeClass = key.is_active ? 'badge-success' : 'badge-error';
            const statusLabel = key.is_active ? 'Active' : 'Inactive';
            
            row.innerHTML = `
                <td style="font-weight:600; color:var(--text-primary);">${escapeHtml(key.name)}</td>
                <td><code style="font-size:0.9rem; color:var(--accent-purple-light);">${key.key_prefix}</code></td>
                <td>${createDate}</td>
                <td>${expiryDate}</td>
                <td>${lastUsed}</td>
                <td>${calls}</td>
                <td style="color:var(--accent-green); font-weight:500;">${spend}</td>
                <td><span class="badge ${badgeClass}">${statusLabel}</span></td>
                <td>
                    <div style="display: flex; gap: 0.5rem; align-items: center;">
                        <button class="btn btn-secondary btn-icon-only toggle-status-btn" data-key-id="${key.id}" title="${key.is_active ? 'Deactivate' : 'Activate'} key">
                            <i data-lucide="${key.is_active ? 'toggle-right' : 'toggle-left'}" style="${key.is_active ? 'color: var(--accent-green);' : 'color: var(--text-muted);'}"></i>
                        </button>
                        <button class="btn btn-secondary btn-icon-only rename-key-btn" data-key-id="${key.id}" title="Rename key">
                            <i data-lucide="edit-3"></i>
                        </button>
                        ${key.is_active ? `
                            <button class="btn btn-secondary btn-icon-only rotate-key-btn" data-key-id="${key.id}" title="Rotate key">
                                <i data-lucide="refresh-cw"></i>
                            </button>
                        ` : ''}
                        <button class="btn btn-danger btn-icon-only delete-key-btn" data-key-id="${key.id}" title="Delete key">
                            <i data-lucide="trash-2"></i>
                        </button>
                    </div>
                </td>
            `;
            elements.keysTbody.appendChild(row);
        });

        // Add toggle status handlers
        elements.keysTbody.querySelectorAll('.toggle-status-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const keyId = btn.getAttribute('data-key-id');
                const key = state.keys.find(k => k.id === keyId);
                if (key) {
                    handleToggleKeyStatus(key.id, key.is_active);
                }
            });
        });

        // Add rename handlers
        elements.keysTbody.querySelectorAll('.rename-key-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const keyId = btn.getAttribute('data-key-id');
                const key = state.keys.find(k => k.id === keyId);
                if (key) {
                    elements.renameKeyId.value = key.id;
                    elements.renameKeyNameInput.value = key.name;
                    showModal(elements.renameKeyModal);
                }
            });
        });

        // Add rotate handlers
        elements.keysTbody.querySelectorAll('.rotate-key-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const keyId = btn.getAttribute('data-key-id');
                const key = state.keys.find(k => k.id === keyId);
                if (key) {
                    handleRotateKey(key.id, key.name);
                }
            });
        });

        // Add delete handlers
        elements.keysTbody.querySelectorAll('.delete-key-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const keyId = btn.getAttribute('data-key-id');
                const key = state.keys.find(k => k.id === keyId);
                if (key) {
                    handleDeleteKey(key.id, key.name, key.key_prefix);
                }
            });
        });

        lucide.createIcons();
    }
}

async function handleCreateKey(e) {
    e.preventDefault();
    const name = document.getElementById('key-name-input').value;
    const expiresDaysStr = document.getElementById('key-expiry-input').value;
    const rpmStr = document.getElementById('key-rpm-input').value;
    const tokensStr = document.getElementById('key-tokens-input').value;
    
    // Read Content Safety configurations
    const guardrailPii = document.getElementById('key-guardrail-pii').value;
    const guardrailInjection = document.getElementById('key-guardrail-injection').value;
    const guardrailToxicity = document.getElementById('key-guardrail-toxicity').value;
    const guardrailCharsStr = document.getElementById('key-guardrail-chars').value;
    const guardrailStrict = document.getElementById('key-guardrail-strict').checked;
    
    const submitBtn = e.target.querySelector('button[type="submit"]');
    setButtonState(submitBtn, true, "Generating...");

    const payload = { 
        name,
        guardrail_settings: {
            pii: guardrailPii,
            prompt_injection: guardrailInjection,
            toxicity: guardrailToxicity,
            max_characters: guardrailCharsStr ? parseInt(guardrailCharsStr, 10) : 100000,
            strict_llm_verification: guardrailStrict
        }
    };
    if (expiresDaysStr) {
        payload.expires_in_days = parseInt(expiresDaysStr, 10);
    }
    if (rpmStr) {
        payload.rate_limit_rpm = parseInt(rpmStr, 10);
    }
    if (tokensStr) {
        payload.monthly_token_quota = parseInt(tokensStr, 10);
    }

    try {
        const response = await fetch('/api/api-keys', {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${state.accessToken}` 
            },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || 'Failed to create key.');
        }

        const newKey = await response.json();
        
        // Save the raw key temporarily in session memory so the playground can auto-fill it
        state.sessionRawKeys[newKey.id] = newKey.api_key;
        
        // Hide config modal and reset form
        hideModal(elements.createKeyModal);
        elements.createKeyForm.reset();

        // Show Key Reveal Modal
        elements.revealKeyCode.textContent = newKey.api_key;
        showModal(elements.revealKeyModal);
        
        showToast('Success', `API key "${name}" created.`, 'success');
    } catch (error) {
        showToast('Error', error.message, 'error');
    } finally {
        setButtonState(submitBtn, false, "Generate Key", "check");
    }
}

async function handleToggleKeyStatus(keyId, currentActive) {
    const action = currentActive ? 'deactivate' : 'activate';
    try {
        const response = await fetch(`/api/api-keys/${keyId}/${action}`, {
            method: 'PATCH',
            headers: { 'Authorization': `Bearer ${state.accessToken}` }
        });

        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || `Failed to ${action} key.`);
        }

        showToast('Success', `API key was successfully ${currentActive ? 'deactivated' : 'activated'}.`, 'success');
        refreshAllData();
    } catch (error) {
        showToast('Error', error.message, 'error');
    }
}

async function handleRenameKeySubmit(e) {
    e.preventDefault();
    const keyId = elements.renameKeyId.value;
    const name = elements.renameKeyNameInput.value;
    
    const submitBtn = e.target.querySelector('button[type="submit"]');
    setButtonState(submitBtn, true, "Renaming...");

    try {
        const response = await fetch(`/api/api-keys/${keyId}`, {
            method: 'PATCH',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${state.accessToken}`
            },
            body: JSON.stringify({ name })
        });

        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || 'Failed to rename key.');
        }

        hideModal(elements.renameKeyModal);
        elements.renameKeyForm.reset();
        showToast('Success', `API key renamed to "${name}".`, 'success');
        refreshAllData();
    } catch (error) {
        showToast('Error', error.message, 'error');
    } finally {
        setButtonState(submitBtn, false, "Rename Key", "check");
    }
}

async function handleRotateKey(keyId, keyName) {
    const confirmRotate = confirm(`Are you sure you want to rotate the API key "${keyName}"?\n\nThis will permanently disable the current key credentials, and generate a new key prefix with the same expiration date.`);
    if (!confirmRotate) return;

    try {
        const response = await fetch(`/api/api-keys/${keyId}/rotate`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${state.accessToken}` }
        });

        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || 'Failed to rotate key.');
        }

        const newKey = await response.json();
        
        // Save the raw key temporarily in session memory so the playground can auto-fill it
        state.sessionRawKeys[newKey.id] = newKey.api_key;
        
        // Show Key Reveal Modal
        elements.revealKeyCode.textContent = newKey.api_key;
        showModal(elements.revealKeyModal);
        
        showToast('Success', `API key "${keyName}" rotated successfully.`, 'success');
        refreshAllData();
    } catch (error) {
        showToast('Error', error.message, 'error');
    }
}

async function handleDeleteKey(keyId, keyName, keyPrefix) {
    const confirmDelete = confirm(`Are you sure you want to delete "${keyName}" (${keyPrefix})?\n\nThis key will be permanently deactivated and removed from active use. Historical usage records will be preserved for your dashboard stats.`);
    if (!confirmDelete) return;

    try {
        const response = await fetch(`/api/api-keys/${keyId}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${state.accessToken}` }
        });

        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || 'Failed to delete key.');
        }

        showToast('Key Deleted', `"${keyName}" was soft-deleted.`, 'warning');
        
        if (state.sessionRawKeys[keyId]) {
            delete state.sessionRawKeys[keyId];
        }

        refreshAllData();
    } catch (error) {
        showToast('Error', error.message, 'error');
    }
}

// UI Rendering - Playground Setup
function updatePlaygroundUI() {
    // Re-populate key dropdown
    const selectedVal = elements.playgroundKeySelect.value;
    elements.playgroundKeySelect.innerHTML = '<option value="" disabled selected>Select an API Key...</option>';

    const activeKeys = state.keys.filter(k => k.is_active);
    
    if (activeKeys.length === 0) {
        elements.playgroundKeySelect.innerHTML += '<option value="" disabled>No active keys available. Generate one in API Keys!</option>';
    } else {
        activeKeys.forEach(key => {
            const opt = document.createElement('option');
            opt.value = key.id;
            opt.textContent = `${key.name} (${key.key_prefix})`;
            elements.playgroundKeySelect.appendChild(opt);
        });

        // Try to maintain select key selection
        if (selectedVal && activeKeys.find(k => k.id === selectedVal)) {
            elements.playgroundKeySelect.value = selectedVal;
        }
    }
}

function clearPlaygroundChat() {
    elements.chatMessagesContainer.innerHTML = `
        <div class="chat-message assistant system">
            <div class="message-avatar"><i data-lucide="bot"></i></div>
            <div class="message-content">
                <p>Hello! Select an **API Key** on the left settings panel, write a message, and submit. The query will be securely routed through our LLM Gateway and tracked in your dashboard logs.</p>
            </div>
        </div>
    `;
    lucide.createIcons();
}

async function handlePlaygroundChatSubmit(e) {
    e.preventDefault();
    const prompt = elements.chatInputTextarea.value.trim();
    const keyId = elements.playgroundKeySelect.value;
    // Strip any non-printable or non-ASCII characters that copy-paste can introduce
    const rawKey = elements.playgroundRawKeyInput.value.replace(/[^\x20-\x7E]/g, '').trim();
    const routingMode = elements.playgroundRoutingMode.value;
    const provider = elements.playgroundProviderSelect.value;
    const model = elements.playgroundModelSelect.value;
    const routingPolicy = elements.playgroundPolicySelect.value;
    const fallbackRaw = elements.playgroundFallbackInput.value.trim();
    const fallbackChain = fallbackRaw ? fallbackRaw.split(',').map(s => s.trim().toLowerCase()).filter(Boolean) : null;
    const temperature = parseFloat(elements.playgroundTemperature.value);
    const maxTokens = parseInt(elements.playgroundMaxTokens.value, 10);

    if (!prompt) return;
    // Determine bearer token: use raw gw_live_ key if valid, otherwise fallback to session accessToken
    const authBearer = (rawKey && rawKey.startsWith('gw_live_')) ? rawKey : state.accessToken;

    if (!authBearer) {
        showToast('Authentication Error', 'Please log in or provide a valid gw_live_... API key.', 'error');
        return;
    }

    // Append User message to UI
    appendChatMessage('user', prompt);
    elements.chatInputTextarea.value = '';
    
    // Auto-focus scroll
    scrollToBottom();

    // Disable input send button
    elements.chatSendBtn.disabled = true;
    elements.chatSendBtn.innerHTML = '<div class="spinner" style="width:16px; height:16px; border-width:2px; border-top-color:transparent; border-left-color:transparent;"></div>';
    
    // Create Temporary typing bubble
    const typingBubble = appendChatMessage('assistant', 'Routing query to LLM Gateway...', true);

    // Build request payload
    const payload = {
        message: prompt,
        temperature,
        max_tokens: maxTokens,
        bypass_cache: elements.playgroundBypassCache ? elements.playgroundBypassCache.checked : false
    };
    if (routingMode === 'direct') {
        payload.provider = provider;
        payload.model = model;
    } else {
        payload.routing_policy = routingPolicy;
        if (fallbackChain && fallbackChain.length > 0) {
            payload.fallback_chain = fallbackChain;
        }
    }

    try {
        const response = await fetch('/api/gateway/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authBearer}`
            },
            body: JSON.stringify(payload)
        });

        // Delete typing bubble
        typingBubble.remove();

        if (!response.ok) {
            const err = await response.json();
            let errMsg = 'Gateway error';
            if (err && err.detail) {
                if (typeof err.detail === 'object' && err.detail.error && err.detail.error.message) {
                    errMsg = err.detail.error.message;
                } else if (typeof err.detail === 'string') {
                    errMsg = err.detail;
                } else {
                    errMsg = JSON.stringify(err.detail);
                }
            }
            throw new Error(errMsg);
        }

        const data = await response.json();
        
        // Append response text
        const meta = {
            latency: data.latency_ms,
            cost: data.cost,
            tokens: data.total_tokens,
            status: response.status,
            provider: data.provider,
            model: data.model,
            cache: data.cache
        };
        appendChatMessage('assistant', data.response_text, false, meta);
        
        // Refresh usage details in background
        refreshAllData();
    } catch (error) {
        typingBubble.remove();
        appendChatMessage('assistant', `⚠️ **Gateway Request Failed**\n\n\`\`\`\n${error.message}\n\`\`\`\nVerify your raw API key matches the selected prefix, that it is active, and your upstream GEMINI_API_KEY environment variable is configured correctly.`, false);
        showToast('Gateway Error', error.message, 'error');
    } finally {
        elements.chatSendBtn.disabled = false;
        elements.chatSendBtn.innerHTML = '<i data-lucide="send"></i>';
        lucide.createIcons();
        scrollToBottom();
    }
}

// Chat DOM Injectors
function appendChatMessage(sender, text, isTyping = false, metadata = null) {
    const msg = document.createElement('div');
    msg.className = `chat-message ${sender} ${isTyping ? 'typing' : ''}`;
    
    const avatarIcon = sender === 'user' ? 'user' : 'bot';
    
    // Parse rich markdown (headings, tables, lists, code blocks, bold, etc.)
    let formattedHtml = '';
    if (typeof marked !== 'undefined' && marked.parse) {
        try {
            marked.setOptions({ breaks: true, gfm: true });
            formattedHtml = marked.parse(text);
        } catch (e) {
            console.warn('Marked.js error, falling back to built-in parser:', e);
        }
    }
    
    // Built-in standalone fallback markdown parser (guarantees tables and headings render)
    if (!formattedHtml) {
        const lines = text.split('\n');
        let inTable = false;
        let out = [];

        for (let i = 0; i < lines.length; i++) {
            const line = lines[i].trim();
            
            // Markdown table row
            if (line.startsWith('|') && line.endsWith('|')) {
                const cells = line.split('|').slice(1, -1).map(c => c.trim());
                // Separator row (e.g. |---|---|)
                if (cells.every(c => /^:?-+:?$/.test(c))) {
                    continue;
                }
                if (!inTable) {
                    inTable = true;
                    out.push('<table><thead><tr>' + cells.map(c => `<th>${escapeHtml(c)}</th>`).join('') + '</tr></thead><tbody>');
                } else {
                    out.push('<tr>' + cells.map(c => `<td>${escapeHtml(c)}</td>`).join('') + '</tr>');
                }
                continue;
            } else if (inTable) {
                inTable = false;
                out.push('</tbody></table>');
            }

            // Headings
            if (line.startsWith('### ')) {
                out.push(`<h3>${escapeHtml(line.slice(4))}</h3>`);
            } else if (line.startsWith('## ')) {
                out.push(`<h2>${escapeHtml(line.slice(3))}</h2>`);
            } else if (line.startsWith('# ')) {
                out.push(`<h1>${escapeHtml(line.slice(2))}</h1>`);
            } else if (line.startsWith('> ')) {
                out.push(`<blockquote>${escapeHtml(line.slice(2))}</blockquote>`);
            } else if (line.startsWith('- ') || line.startsWith('* ')) {
                out.push(`<li>${escapeHtml(line.slice(2))}</li>`);
            } else if (line) {
                out.push(`<p>${escapeHtml(line)}</p>`);
            }
        }
        if (inTable) out.push('</tbody></table>');

        formattedHtml = out.join('\n')
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/`([^`]+)`/g, '<code>$1</code>');
    }

    msg.innerHTML = `
        <div class="message-avatar"><i data-lucide="${avatarIcon}"></i></div>
        <div class="message-content markdown-body">
            ${formattedHtml}
            ${metadata ? `
                <div class="msg-metadata">
                    ${metadata.provider ? `<span><i data-lucide="cpu" style="width:12px;height:12px;"></i> ${metadata.provider} (${metadata.model})</span>` : ''}
                    <span><i data-lucide="clock" style="width:12px;height:12px;"></i> ${metadata.latency}ms</span>
                    <span><i data-lucide="coins" style="width:12px;height:12px;"></i> ${formatCost(metadata.cost)}</span>
                    <span><i data-lucide="hash" style="width:12px;height:12px;"></i> ${metadata.tokens} tokens</span>
                    ${metadata.cache && metadata.cache.hit ? `
                        <span class="cache-hit-badge">
                            <i data-lucide="database" style="width:12px;height:12px;"></i> 
                            Cache Hit: ${metadata.cache.type === 'exact' ? 'Exact' : `Semantic (${(metadata.cache.similarity * 100).toFixed(0)}% sim)`}
                        </span>
                    ` : ''}
                </div>
            ` : ''}
        </div>
    `;

    elements.chatMessagesContainer.appendChild(msg);
    lucide.createIcons();
    return msg;
}

function scrollToBottom() {
    elements.chatMessagesContainer.scrollTop = elements.chatMessagesContainer.scrollHeight;
}

// Helpers
function setButtonState(buttonEl, isLoading, text, iconName = null) {
    if (isLoading) {
        buttonEl.disabled = true;
        buttonEl.innerHTML = `<div class="spinner" style="width:16px; height:16px; border-width:2px; border-top-color:transparent;"></div> <span>${text}</span>`;
    } else {
        buttonEl.disabled = false;
        let iconHtml = '';
        if (iconName) {
            iconHtml = `<i data-lucide="${iconName}"></i>`;
        }
        buttonEl.innerHTML = `<span>${text}</span> ${iconHtml}`;
        lucide.createIcons();
    }
}

function escapeHtml(string) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return String(string).replace(/[&<>"']/g, function(m) { return map[m]; });
}

function formatCost(value) {
    if (value === 0) return '$0.00';
    if (value < 0.01) return `$${value.toFixed(6)}`;
    return `$${value.toFixed(4)}`;
}

// ==========================================
// OBSERVABILITY & TRACING CORE FUNCTIONS
// ==========================================

async function fetchObservabilityData() {
    if (!state.accessToken) return;
    try {
        const headers = { 'Authorization': `Bearer ${state.accessToken}` };
        const [tracesRes, providersRes, errorsRes, throughputRes] = await Promise.all([
            fetch('/api/observability/traces', { headers }),
            fetch('/api/observability/metrics/providers', { headers }),
            fetch('/api/observability/metrics/errors', { headers }),
            fetch('/api/observability/metrics/throughput', { headers })
        ]);
        
        if (!tracesRes.ok || !providersRes.ok || !errorsRes.ok || !throughputRes.ok) {
            throw new Error("Failed to fetch observability datasets");
        }
        
        state.observability = {
            traces: await tracesRes.json(),
            providers: await providersRes.json(),
            errors: await errorsRes.json(),
            throughput: await throughputRes.json()
        };
    } catch (error) {
        console.error("Observability sync failed:", error);
        state.observability = state.observability || {
            traces: [],
            providers: [],
            errors: {},
            throughput: { today: 0, week: 0, month: 0 }
        };
    }
}

function updateObservabilityUI() {
    if (!state.observability) return;
    const obs = state.observability;

    // 1. Throughput Stats Cards
    if (elements.obsStatToday) elements.obsStatToday.textContent = obs.throughput.today.toLocaleString();
    if (elements.obsStatWeek) elements.obsStatWeek.textContent = obs.throughput.week.toLocaleString();
    if (elements.obsStatMonth) elements.obsStatMonth.textContent = obs.throughput.month.toLocaleString();

    // 2. Trace Explorer table
    if (elements.tracesTbody) {
        elements.tracesTbody.innerHTML = '';
        if (elements.tracesCountBadge) {
            elements.tracesCountBadge.textContent = `${obs.traces.length} traces`;
        }
        
        if (obs.traces.length === 0) {
            elements.tracesTbody.innerHTML = `
                <tr>
                    <td colspan="8" class="empty-state">
                        <i data-lucide="eye"></i>
                        <p>No trace records available yet. Make a request via the Playground to generate traces.</p>
                    </td>
                </tr>
            `;
            lucide.createIcons();
        } else {
            obs.traces.forEach(t => {
                const row = document.createElement('tr');
                
                // Badge for status code
                const statusClass = t.status_code >= 200 && t.status_code < 300 ? 'badge-success' : 'badge-error';
                const dateStr = new Date(t.created_at).toLocaleString();
                
                // Truncate previews to 50 chars for the main table row if too long
                const truncateStr = (str, len = 50) => {
                    if (!str) return 'N/A';
                    if (str.length > len) return str.slice(0, len) + '...';
                    return str;
                };
                
                row.innerHTML = `
                    <td><code style="font-weight:600; color:var(--accent-purple-light);">${escapeHtml(t.trace_id)}</code></td>
                    <td><span class="badge ${statusClass}">${t.status_code}</span></td>
                    <td>${dateStr}</td>
                    <td>${t.total_latency_ms} ms</td>
                    <td><span class="badge badge-secondary" style="background:rgba(255,255,255,0.06); color:var(--text-primary); font-weight:500;">${t.attempts_count}</span></td>
                    <td><span style="font-size:0.85rem; color:var(--text-secondary); font-family:monospace;">${escapeHtml(truncateStr(t.prompt))}</span></td>
                    <td><span style="font-size:0.85rem; color:var(--text-secondary); font-family:monospace;">${escapeHtml(truncateStr(t.response))}</span></td>
                    <td>
                        <button class="detail-btn-icon trace-detail-btn" data-trace-id="${t.trace_id}">
                            <i data-lucide="eye"></i>
                        </button>
                    </td>
                `;
                elements.tracesTbody.appendChild(row);
            });

            // Register click listener for trace buttons
            elements.tracesTbody.querySelectorAll('.trace-detail-btn').forEach(btn => {
                btn.addEventListener('click', () => {
                    const traceId = btn.getAttribute('data-trace-id');
                    fetchAndShowTraceDetail(traceId);
                });
            });
            
            lucide.createIcons();
        }
    }

    // 3. Render charts
    renderObservabilityCharts();
}

async function fetchAndShowTraceDetail(traceId) {
    if (!state.accessToken) return;
    try {
        const response = await fetch(`/api/observability/traces/${traceId}`, {
            headers: { 'Authorization': `Bearer ${state.accessToken}` }
        });
        
        if (!response.ok) {
            throw new Error("Failed to fetch detailed trace");
        }
        
        const trace = await response.json();
        
        // Populate trace details modal fields
        elements.traceDetailId.textContent = trace.trace_id;
        elements.traceDetailLatency.textContent = `${trace.total_latency_ms} ms`;
        elements.traceDetailTimestamp.textContent = new Date(trace.created_at).toLocaleString();
        
        // Status Code Badge
        const isSuccess = trace.status_code >= 200 && trace.status_code < 300;
        elements.traceDetailStatus.innerHTML = `<span class="badge ${isSuccess ? 'badge-success' : 'badge-error'}">${trace.status_code}</span>`;
        
        // Prompts & Response payloads
        elements.traceDetailPrompt.textContent = trace.prompt || 'N/A';
        elements.traceDetailResponse.textContent = trace.response || 'N/A';
        
        // Build Timeline flow
        elements.traceTimelineFlow.innerHTML = '';
        if (trace.timeline && trace.timeline.length > 0) {
            trace.timeline.forEach(step => {
                const stepDiv = document.createElement('div');
                
                // Determine status decoration
                let stepClass = 'timeline-step info';
                if (step.stage === 'received') stepClass = 'timeline-step info';
                else if (step.stage === 'limits_passed') stepClass = 'timeline-step success';
                else if (step.stage === 'routing_decision') stepClass = 'timeline-step warning';
                else if (step.stage.startsWith('provider_call')) stepClass = 'timeline-step info';
                else if (step.stage === 'response_returned') stepClass = 'timeline-step success';
                
                // If overall trace has error and this is the last step or response_returned was skipped/failed
                if (!isSuccess && step.stage === 'response_returned') {
                    stepClass = 'timeline-step failed';
                }
                
                const stepTime = new Date(step.timestamp).toLocaleTimeString();
                
                stepDiv.className = stepClass;
                stepDiv.innerHTML = `
                    <div class="timeline-step-title">${escapeHtml(step.stage.toUpperCase())}</div>
                    <div class="timeline-step-meta">
                        <span>Offset: +${step.duration_ms} ms</span>
                        <span>${stepTime}</span>
                    </div>
                `;
                elements.traceTimelineFlow.appendChild(stepDiv);
            });
        } else {
            elements.traceTimelineFlow.innerHTML = '<p style="color:var(--text-muted); font-size:0.9rem;">No timeline logs.</p>';
        }
        
        // Build attempts list
        elements.traceAttemptsList.innerHTML = '';
        if (trace.attempts && trace.attempts.length > 0) {
            trace.attempts.forEach(att => {
                const attDiv = document.createElement('div');
                const isAttSuccess = att.status === 'success';
                attDiv.className = `attempt-card ${isAttSuccess ? 'success' : 'failed'}`;
                
                attDiv.innerHTML = `
                    <div class="attempt-header">
                        <span style="font-weight:600; color:var(--text-primary);">Attempt #${att.attempt}: ${escapeHtml(att.provider.toUpperCase())}</span>
                        <span class="badge ${isAttSuccess ? 'badge-success' : 'badge-error'}">${escapeHtml(att.status.toUpperCase())}</span>
                    </div>
                    <div class="attempt-meta" style="margin-top:2px;">
                        <span>Model: <code>${escapeHtml(att.model)}</code></span>
                        <span>Latency: ${att.latency_ms}ms</span>
                    </div>
                    <div class="attempt-meta" style="margin-top:2px;">
                        <span style="color:var(--accent-green);">Cost: ${formatCost(att.cost)}</span>
                    </div>
                    ${att.error ? `<div class="attempt-error">${escapeHtml(att.error)}</div>` : ''}
                `;
                elements.traceAttemptsList.appendChild(attDiv);
            });
        } else {
            elements.traceAttemptsList.innerHTML = '<p style="color:var(--text-muted); font-size:0.9rem;">No execution attempts logged (e.g. rate limit blocking before execution).</p>';
        }
        
        showModal(elements.traceDetailModal);
        lucide.createIcons();
    } catch (error) {
        console.error("Failed to load trace details:", error);
        showToast('Load Failed', 'Unable to retrieve trace timeline and retry records.', 'error');
    }
}

function renderObservabilityCharts() {
    const obs = state.observability;
    if (!obs) return;

    // 1. Providers Compare bar chart
    if (state.charts.latencyCompare) {
        state.charts.latencyCompare.destroy();
    }
    
    const providerNames = obs.providers.map(p => p.provider.toUpperCase());
    const latencies = obs.providers.map(p => p.avg_latency_ms);
    const successRates = obs.providers.map(p => p.success_rate);
    
    const ctxLatencyCompare = document.getElementById('latencyCompareChart').getContext('2d');
    state.charts.latencyCompare = new Chart(ctxLatencyCompare, {
        type: 'bar',
        data: {
            labels: providerNames,
            datasets: [
                {
                    label: 'EWMA Latency (ms)',
                    data: latencies,
                    backgroundColor: 'rgba(124, 58, 237, 0.65)',
                    borderColor: '#7c3aed',
                    borderWidth: 1.5,
                    yAxisID: 'y'
                },
                {
                    label: 'Success Rate (%)',
                    data: successRates,
                    backgroundColor: 'rgba(16, 185, 129, 0.65)',
                    borderColor: '#10b981',
                    borderWidth: 1.5,
                    yAxisID: 'y1'
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    labels: { color: '#9aa2c0', font: { family: 'Inter', size: 11 } }
                }
            },
            scales: {
                x: {
                    grid: { color: 'rgba(38, 43, 71, 0.2)' },
                    ticks: { color: '#9aa2c0' }
                },
                y: {
                    type: 'linear',
                    display: true,
                    position: 'left',
                    title: {
                        display: true,
                        text: 'Latency (ms)',
                        color: '#9aa2c0'
                    },
                    grid: { color: 'rgba(38, 43, 71, 0.2)' },
                    ticks: { color: '#9aa2c0' }
                },
                y1: {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    title: {
                        display: true,
                        text: 'Success Rate (%)',
                        color: '#9aa2c0'
                    },
                    grid: { drawOnChartArea: false },
                    ticks: { color: '#9aa2c0', min: 0, max: 100 }
                }
            }
        }
    });

    // 2. Error Categories Doughnut Chart
    if (state.charts.errorType) {
        state.charts.errorType.destroy();
    }
    
    const errorLabels = [];
    const errorData = [];
    
    Object.entries(obs.errors).forEach(([errName, count]) => {
        if (count > 0) {
            const formattedLabel = errName.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
            errorLabels.push(formattedLabel);
            errorData.push(count);
        }
    });
    
    const ctxErrorType = document.getElementById('errorTypeChart').getContext('2d');
    
    if (errorLabels.length === 0) {
        errorLabels.push("No Errors");
        errorData.push(1);
        
        state.charts.errorType = new Chart(ctxErrorType, {
            type: 'doughnut',
            data: {
                labels: errorLabels,
                datasets: [{
                    data: errorData,
                    backgroundColor: ['#10b981'],
                    borderWidth: 1,
                    borderColor: '#171b30'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: { color: '#9aa2c0', font: { family: 'Inter', size: 11 } }
                    },
                    tooltip: {
                        callbacks: {
                            label: (item) => "System Healthy (0 errors logged)"
                        }
                    }
                },
                cutout: '65%'
            }
        });
    } else {
        state.charts.errorType = new Chart(ctxErrorType, {
            type: 'doughnut',
            data: {
                labels: errorLabels,
                datasets: [{
                    data: errorData,
                    backgroundColor: [
                        '#ef4444',
                        '#f59e0b',
                        '#7c3aed',
                        '#3b82f6',
                        '#ec4899',
                        '#14b8a6'
                    ],
                    borderWidth: 1,
                    borderColor: '#171b30'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: { color: '#9aa2c0', font: { family: 'Inter', size: 11 } }
                    }
                },
                cutout: '65%'
            }
        });
    }
}

// Content Safety & Guardrails Data Fetching
async function fetchGuardrailData() {
    if (!state.accessToken) return;
    try {
        const response = await fetch('/api/guardrails/stats', {
            headers: { 'Authorization': `Bearer ${state.accessToken}` }
        });
        if (response.ok) {
            state.guardrailStats = await response.json();
        }
        
        const resEvents = await fetch('/api/guardrails/events', {
            headers: { 'Authorization': `Bearer ${state.accessToken}` }
        });
        if (resEvents.ok) {
            state.guardrailEvents = await resEvents.json();
        }
    } catch (err) {
        console.error("Error loading safety data:", err);
    }
}

// Update Guardrails UI and render safety charts
function updateGuardrailsUI() {
    if (!state.guardrailStats) return;
    
    const gs = state.guardrailStats;
    elements.safetyStatBlocked.textContent = gs.total_blocked.toLocaleString();
    elements.safetyStatWarned.textContent = gs.total_warned.toLocaleString();
    elements.safetyStatMasked.textContent = gs.total_masked.toLocaleString();
    elements.safetyStatTopKey.textContent = gs.most_triggered_key || 'None';
    
    // Render Security Audit logs table
    if (elements.guardrailsTbody) {
        elements.guardrailsTbody.innerHTML = '';
        if (!state.guardrailEvents || state.guardrailEvents.length === 0) {
            elements.guardrailsTbody.innerHTML = `
                <tr>
                    <td colspan="8" class="empty-state">
                        <i data-lucide="shield-check"></i>
                        <p>No safety logs or security violations registered yet.</p>
                    </td>
                </tr>
            `;
        } else {
            state.guardrailEvents.forEach(evt => {
                const row = document.createElement('tr');
                const timeStr = new Date(evt.created_at).toLocaleString();
                
                // Color badges for actions and severities
                let actionBadge = 'badge-info';
                if (evt.action_taken === 'block') actionBadge = 'badge-error';
                else if (evt.action_taken === 'warn') actionBadge = 'badge-warning';
                else if (evt.action_taken === 'mask') actionBadge = 'badge-success';

                let sevClass = 'badge-info';
                if (evt.severity === 'critical') sevClass = 'badge-error';
                else if (evt.severity === 'high') sevClass = 'badge-warning';
                else if (evt.severity === 'medium') sevClass = 'badge-primary';
                
                row.innerHTML = `
                    <td>${timeStr}</td>
                    <td><span style="font-size:0.85rem; font-weight:500;">${evt.api_key_name}</span></td>
                    <td><code>${evt.event_type}</code></td>
                    <td><span style="font-size:0.85rem; color:var(--text-secondary);">${evt.detector}</span></td>
                    <td><span class="badge ${actionBadge}">${evt.action_taken.toUpperCase()}</span></td>
                    <td><span class="badge ${sevClass}">${evt.severity.toUpperCase()}</span></td>
                    <td>${Math.round(evt.confidence * 100)}%</td>
                    <td><span style="font-size:0.85rem; color:var(--text-secondary); max-width:200px; display:inline-block; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="${evt.matched_detail}">${evt.matched_detail}</span></td>
                `;
                elements.guardrailsTbody.appendChild(row);
            });
        }
        elements.guardrailsCountBadge.textContent = `${state.guardrailEvents ? state.guardrailEvents.length : 0} events`;
        lucide.createIcons();
    }
    
    // Render Guardrails Trend Line Chart
    const ctxTrend = document.getElementById('guardrailsTrendChart').getContext('2d');
    const trendLabels = gs.trend_7days.map(d => d.date);
    const trendValues = gs.trend_7days.map(d => d.count);
    
    if (state.charts.guardrailsTrend) {
        state.charts.guardrailsTrend.destroy();
    }
    
    state.charts.guardrailsTrend = new Chart(ctxTrend, {
        type: 'line',
        data: {
            labels: trendLabels,
            datasets: [{
                label: 'Security Violations / Alerts',
                data: trendValues,
                borderColor: '#ef4444',
                backgroundColor: 'rgba(239, 68, 68, 0.1)',
                borderWidth: 2,
                fill: true,
                tension: 0.3
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                x: { grid: { color: 'rgba(255, 255, 255, 0.05)' }, ticks: { color: '#9aa2c0' } },
                y: { grid: { color: 'rgba(255, 255, 255, 0.05)' }, ticks: { color: '#9aa2c0', stepSize: 1 } }
            }
        }
    });

    // Render Categories Doughnut Chart
    const ctxCategories = document.getElementById('guardrailsCategoriesChart').getContext('2d');
    const catLabels = gs.top_violations.map(v => v.event_type);
    const catData = gs.top_violations.map(v => v.count);
    
    if (state.charts.guardrailsCategories) {
        state.charts.guardrailsCategories.destroy();
    }
    
    state.charts.guardrailsCategories = new Chart(ctxCategories, {
        type: 'doughnut',
        data: {
            labels: catLabels.length > 0 ? catLabels : ['No Violations'],
            datasets: [{
                data: catData.length > 0 ? catData : [1],
                backgroundColor: catData.length > 0 ? ['#ef4444', '#f59e0b', '#3b82f6', '#ec4899', '#7c3aed'] : ['#1e293b'],
                borderWidth: 1,
                borderColor: '#171b30'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: { color: '#9aa2c0', font: { family: 'Inter', size: 10 } }
                }
            },
            cutout: '60%'
        }
    });
}

// Sandbox Test Form Handler
async function handleSandboxSafetySubmit() {
    const prompt = elements.sandboxPromptTextarea.value.trim();
    if (!prompt) {
        showToast('Sandbox Error', 'Please type a test prompt first.', 'error');
        return;
    }
    
    const piiAction = elements.sandboxPolicyPii.value;
    const injectionAction = elements.sandboxPolicyInjection.value;
    const toxicityAction = elements.sandboxPolicyToxicity.value;
    const charsLimit = parseInt(elements.sandboxPolicyChars.value, 10) || 100000;
    const strictLlm = elements.sandboxPolicyStrict.checked;
    
    setButtonState(elements.runSandboxSafetyBtn, true, "Analyzing...");
    
    try {
        const response = await fetch('/api/guardrails/test', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${state.accessToken}`
            },
            body: JSON.stringify({
                prompt: prompt,
                policies: {
                    pii: piiAction,
                    prompt_injection: injectionAction,
                    toxicity: toxicityAction,
                    max_characters: charsLimit,
                    strict_llm_verification: strictLlm
                }
            })
        });
        
        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || 'Sandbox evaluation failed.');
        }
        
        const result = await response.json();
        
        // Render Output
        elements.sandboxResultsCard.classList.remove('hidden');
        elements.sandboxMaskedOutput.textContent = result.masked_prompt;
        
        // Set Allowed/Blocked Badge
        if (result.allowed) {
            elements.sandboxAllowedBadge.textContent = "Allowed";
            elements.sandboxAllowedBadge.style.background = "rgba(16, 185, 129, 0.15)";
            elements.sandboxAllowedBadge.style.color = "#10b981";
            elements.sandboxAllowedBadge.style.borderColor = "rgba(16, 185, 129, 0.3)";
        } else {
            elements.sandboxAllowedBadge.textContent = "Blocked";
            elements.sandboxAllowedBadge.style.background = "rgba(239, 68, 68, 0.15)";
            elements.sandboxAllowedBadge.style.color = "#ef4444";
            elements.sandboxAllowedBadge.style.borderColor = "rgba(239, 68, 68, 0.3)";
        }
        
        // Render violations table
        elements.sandboxViolationsTbody.innerHTML = '';
        if (result.violations.length === 0) {
            elements.sandboxViolationsTbody.innerHTML = `
                <tr>
                    <td colspan="7" class="empty-state">No policy violations detected.</td>
                </tr>
            `;
        } else {
            result.violations.forEach(v => {
                const row = document.createElement('tr');
                
                let actionClass = 'badge-info';
                if (v.action_taken === 'block') actionClass = 'badge-error';
                else if (v.action_taken === 'warn') actionClass = 'badge-warning';
                else if (v.action_taken === 'mask') actionClass = 'badge-success';

                let sevClass = 'badge-info';
                if (v.severity === 'critical') sevClass = 'badge-error';
                else if (v.severity === 'high') sevClass = 'badge-warning';
                else if (v.severity === 'medium') sevClass = 'badge-primary';

                row.innerHTML = `
                    <td><code>${v.event_type}</code></td>
                    <td><span style="font-size:0.8rem; color:var(--text-secondary);">${v.detector}</span></td>
                    <td><code>${v.matched_text}</code></td>
                    <td>${v.matched_detail}</td>
                    <td>${Math.round(v.confidence * 100)}%</td>
                    <td><span class="badge ${sevClass}">${v.severity.toUpperCase()}</span></td>
                    <td><span class="badge ${actionClass}">${v.action_taken.toUpperCase()}</span></td>
                `;
                elements.sandboxViolationsTbody.appendChild(row);
            });
        }
        lucide.createIcons();
        elements.sandboxResultsCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        showToast('Analysis Complete', 'Prompt safety validation check executed successfully.', 'success');
        
    } catch (err) {
        showToast('Sandbox Error', err.message, 'error');
    } finally {
        setButtonState(elements.runSandboxSafetyBtn, false, "Analyze Prompt Safety", "shield-check");
    }
}


// ==========================================
// Phase 9 Prompt Registry Functions
// ==========================================

function initPromptEventListeners() {
    // Open Register modal
    const openBtn = document.getElementById('open-create-prompt-btn');
    if (openBtn) {
        openBtn.addEventListener('click', () => {
            showModal(document.getElementById('create-prompt-modal'));
        });
    }

    // Handle Create Prompt Template Submit
    const createForm = document.getElementById('create-prompt-form');
    if (createForm) {
        createForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const name = document.getElementById('prompt-name-input').value.trim();
            const description = document.getElementById('prompt-desc-input').value.trim();
            const tagsInput = document.getElementById('prompt-tags-input').value.trim();
            const tags = tagsInput ? tagsInput.split(',').map(t => t.trim()).filter(Boolean) : [];

            try {
                const res = await fetch('/api/prompts', {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${state.accessToken}`,
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ name, description, tags })
                });

                if (!res.ok) {
                    const err = await res.json();
                    throw new Error(err.detail || 'Failed to register template');
                }

                showToast('Success', 'Prompt template successfully registered.', 'success');
                hideModal(document.getElementById('create-prompt-modal'));
                createForm.reset();
                await fetchPrompts();
            } catch (err) {
                showToast('Registration Error', err.message, 'error');
            }
        });
    }

    // Filter list search input
    const searchInput = document.getElementById('prompt-search-input');
    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
            const query = e.target.value.toLowerCase().trim();
            renderPromptsList(query);
        });
    }

    // Inner prompt sub-tabs
    const innerTabBtns = document.querySelectorAll('.prompt-inner-tab-btn');
    innerTabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const targetSubTab = btn.getAttribute('data-prompt-tab');
            
            // Toggle active buttons
            innerTabBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            // Toggle active content divs
            document.querySelectorAll('.prompt-inner-tab-content').forEach(div => {
                div.classList.remove('active');
            });
            const contentDiv = document.getElementById(`prompt-inner-tab-${targetSubTab}`);
            if (contentDiv) {
                contentDiv.classList.add('active');
            }

            // Perform specific load updates
            if (targetSubTab === 'eval' && state.selectedPrompt) {
                fetchPromptEvalMetrics(state.selectedPrompt.id);
            }
        });
    });

    // Create prompt version form
    const createVersionForm = document.getElementById('create-prompt-version-form');
    if (createVersionForm) {
        createVersionForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            // Fallback to first loaded template if selectedPrompt is not set
            if (!state.selectedPrompt && state.prompts && state.prompts.length > 0) {
                state.selectedPrompt = state.prompts[0];
            }
            
            if (!state.selectedPrompt) {
                showToast('Version Error', 'Please select a prompt template from the left list first.', 'error');
                return;
            }

            const version = document.getElementById('pv-version-input').value.trim();
            const description = document.getElementById('pv-desc-input').value.trim();
            const system_prompt = document.getElementById('pv-system-input').value.trim();
            const user_prompt = document.getElementById('pv-user-input').value.trim();
            const is_active = document.getElementById('pv-active-input').checked;

            if (!version || !user_prompt) {
                showToast('Version Error', 'Version Code and User Prompt Template are required.', 'error');
                return;
            }

            const submitBtn = createVersionForm.querySelector('button[type="submit"]');
            setButtonState(submitBtn, true, "Creating Version...");

            try {
                const res = await fetch(`/api/prompts/${state.selectedPrompt.id}/versions`, {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${state.accessToken}`,
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ version, description, system_prompt, user_prompt, is_active })
                });

                if (!res.ok) {
                    const err = await res.json();
                    throw new Error(err.detail || 'Failed to create prompt version');
                }

                showToast('Success', `Version ${version} registered successfully.`, 'success');
                createVersionForm.reset();
                await fetchPromptDetail(state.selectedPrompt.id);
            } catch (err) {
                showToast('Version Error', err.message, 'error');
            } finally {
                setButtonState(submitBtn, false, "Create Version", "plus");
            }
        });
    }

    // A/B split weights save
    const experimentForm = document.getElementById('prompt-experiment-form');
    if (experimentForm) {
        experimentForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            if (!state.selectedPrompt) return;

            const name = document.getElementById('exp-name-input').value.trim();
            const is_active = document.getElementById('exp-active-input').checked;

            const variants = [];
            const rows = document.querySelectorAll('.variant-weight-item');
            rows.forEach(row => {
                const vSelect = row.querySelector('.variant-ver-select');
                const wInput = row.querySelector('.variant-weight-range');
                if (vSelect && wInput && vSelect.value) {
                    variants.push({
                        version_id: vSelect.value,
                        weight: parseFloat(wInput.value) / 100.0
                    });
                }
            });

            try {
                const res = await fetch(`/api/prompts/${state.selectedPrompt.id}/experiment`, {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${state.accessToken}`,
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ name, is_active, variants })
                });

                if (!res.ok) {
                    const err = await res.json();
                    throw new Error(err.detail || 'Failed to save experiment settings');
                }

                showToast('Success', 'A/B Experiment configured and deployed.', 'success');
                await fetchPromptDetail(state.selectedPrompt.id);
            } catch (err) {
                showToast('Experiment Error', err.message, 'error');
            }
        });
    }

    // Sandbox rating stars selector interaction
    const starBtns = document.querySelectorAll('#sandbox-feedback-stars .star-btn');
    starBtns.forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            const rating = parseInt(btn.getAttribute('data-rating'));
            state.sandboxRating = rating;
            
            starBtns.forEach(b => {
                const r = parseInt(b.getAttribute('data-rating'));
                if (r <= rating) {
                    b.classList.add('active');
                } else {
                    b.classList.remove('active');
                }
            });
        });
    });

    // Sandbox submit rating feedback button
    const submitFeedbackBtn = document.getElementById('submit-sandbox-feedback-btn');
    if (submitFeedbackBtn) {
        submitFeedbackBtn.addEventListener('click', async (e) => {
            e.preventDefault();
            if (!state.sandboxTraceId) {
                showToast('Error', 'Execute a request first to rate its quality.', 'error');
                return;
            }
            if (!state.sandboxRating) {
                showToast('Error', 'Please click stars to select a rating first.', 'error');
                return;
            }

            try {
                const res = await fetch(`/api/observability/traces/${state.sandboxTraceId}/feedback`, {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${state.accessToken}`,
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        rating: state.sandboxRating,
                        justification: `Manual evaluation score via playground dashboard.`
                    })
                });

                if (!res.ok) {
                    const err = await res.json();
                    throw new Error(err.detail || 'Failed to submit rating feedback.');
                }

                showToast('Evaluation Submitted', `Manual judge score logged to request trace registry successfully.`, 'success');
                document.getElementById('sandbox-feedback-section').style.display = 'none';
            } catch (err) {
                showToast('Feedback Error', err.message, 'error');
            }
        });
    }

    // Run Sandbox request click handler
    const runSandboxBtn = document.getElementById('run-sandbox-prompt-btn');
    if (runSandboxBtn) {
        runSandboxBtn.addEventListener('click', handleSandboxPromptExecute);
    }
}

async function fetchPrompts() {
    try {
        const res = await fetch('/api/prompts', {
            headers: { 'Authorization': `Bearer ${state.accessToken}` }
        });
        if (!res.ok) throw new Error('Failed to retrieve prompt templates list');
        state.prompts = await res.json();
        renderPromptsList();

        const panel = document.getElementById('prompt-details-panel');
        const emptyState = document.getElementById('prompt-details-empty');

        // Only load details if user explicitly selected a prompt
        if (state.selectedPrompt) {
            fetchPromptDetail(state.selectedPrompt.id);
        } else {
            if (panel) panel.classList.add('hidden');
            if (emptyState) emptyState.classList.remove('hidden');
            updatePromptSandboxPlaygroundUI();
        }
    } catch (err) {
        showToast('Error Loading Templates', err.message, 'error');
    }
}

function renderPromptsList(searchQuery = '') {
    const container = document.getElementById('prompts-cards-stack');
    if (!container) return;

    container.innerHTML = '';
    
    let filtered = state.prompts;
    if (searchQuery) {
        filtered = state.prompts.filter(p => 
            p.name.toLowerCase().includes(searchQuery) ||
            p.description.toLowerCase().includes(searchQuery) ||
            p.tags.some(t => t.toLowerCase().includes(searchQuery))
        );
    }

    if (filtered.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <i data-lucide="folder-open"></i>
                <p>No matching prompt templates found.</p>
            </div>
        `;
        lucide.createIcons();
        return;
    }

    filtered.forEach(p => {
        const card = document.createElement('div');
        const isActive = state.selectedPrompt && state.selectedPrompt.id === p.id;
        card.className = `prompt-registry-card ${isActive ? 'active' : ''}`;
        
        const cardBg = isActive ? 'rgba(124, 58, 237, 0.2)' : 'rgba(30, 41, 59, 0.5)';
        const cardBorder = isActive ? '#7c3aed' : 'rgba(255, 255, 255, 0.08)';
        card.setAttribute('style', `background: ${cardBg} !important; border: 1px solid ${cardBorder} !important; border-radius: 8px; padding: 0.85rem 1rem; cursor: pointer; display: flex; flex-direction: column; gap: 0.35rem; color: #f8fafc; transition: all 0.2s ease;`);

        let tagsHtml = p.tags.map(t => `<span class="prompt-tag-pill" style="font-size: 0.72rem; background: rgba(124, 58, 237, 0.15); color: #a78bfa; padding: 2px 8px; border-radius: 12px; border: 1px solid rgba(124, 58, 237, 0.3); font-weight: 500; display: inline-block;">${t}</span>`).join('');
        
        card.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: start;">
                <h4 style="font-weight: 600; font-size: 0.95rem; color: #f8fafc; margin: 0;">${p.name}</h4>
                <i data-lucide="chevron-right" style="width: 16px; height: 16px; color: var(--text-muted);"></i>
            </div>
            <p style="font-size: 0.8rem; color: #94a3b8; margin: 0;">${p.description || 'No description provided.'}</p>
            <div class="prompt-tags-list" style="margin-top: 0.35rem; display: flex; flex-wrap: wrap; gap: 0.35rem;">
                ${tagsHtml}
            </div>
        `;

        card.addEventListener('click', () => {
            document.querySelectorAll('.prompt-registry-card').forEach(c => {
                c.classList.remove('active');
                c.style.background = 'rgba(30, 41, 59, 0.5)';
                c.style.borderColor = 'rgba(255, 255, 255, 0.08)';
            });
            card.classList.add('active');
            card.style.background = 'rgba(124, 58, 237, 0.2)';
            card.style.borderColor = '#7c3aed';
            fetchPromptDetail(p.id);
        });

        container.appendChild(card);
    });

    lucide.createIcons();
}

async function fetchPromptDetail(promptId) {
    try {
        const prompt = state.prompts.find(p => p.id === promptId);
        if (!prompt) return;
        state.selectedPrompt = prompt;

        const vRes = await fetch(`/api/prompts/${promptId}/versions`, {
            headers: { 'Authorization': `Bearer ${state.accessToken}` }
        });
        if (!vRes.ok) throw new Error('Failed to fetch versions history');
        state.selectedPromptVersions = await vRes.json();

        const expRes = await fetch(`/api/prompts/${promptId}/experiment`, {
            headers: { 'Authorization': `Bearer ${state.accessToken}` }
        });
        if (expRes.ok) {
            state.selectedPromptExperiment = await expRes.json();
        } else {
            state.selectedPromptExperiment = null;
        }

        await fetchPromptEvalMetrics(promptId);
        renderPromptDetailUI();

    } catch (err) {
        showToast('Error Loading Details', err.message, 'error');
    }
}

function renderPromptDetailUI() {
    const panel = document.getElementById('prompt-details-panel');
    const emptyState = document.getElementById('prompt-details-empty');
    if (!panel) return;
    
    panel.classList.remove('hidden');
    if (emptyState) emptyState.classList.add('hidden');

    const prompt = state.selectedPrompt;
    document.getElementById('prompt-detail-name').textContent = prompt.name;
    document.getElementById('prompt-detail-desc').textContent = prompt.description || 'No description provided.';
    
    // Tags
    const tagsDiv = document.getElementById('prompt-detail-tags');
    tagsDiv.innerHTML = prompt.tags.map(t => `<span class="prompt-tag-pill">${t}</span>`).join('');

    // Active version badge
    const activeVersion = state.selectedPromptVersions.find(v => v.is_active);
    const activeBadge = document.getElementById('prompt-active-version-badge');
    if (activeVersion) {
        activeBadge.textContent = `Active: ${activeVersion.version}`;
        activeBadge.style.display = 'inline-block';
    } else {
        activeBadge.textContent = `Active: None`;
        activeBadge.style.display = 'inline-block';
    }

    // Experiment badge
    const expBadge = document.getElementById('prompt-experiment-badge');
    if (state.selectedPromptExperiment && state.selectedPromptExperiment.is_active) {
        expBadge.style.display = 'flex';
    } else {
        expBadge.style.display = 'none';
    }

    // Update inner panels
    updatePromptVersionsUI();
    updatePromptExperimentUI();
    updatePromptSandboxPlaygroundUI();
    
    lucide.createIcons();
}

function updatePromptVersionsUI() {
    const tbody = document.getElementById('prompt-versions-tbody');
    if (!tbody) return;

    tbody.innerHTML = '';
    if (state.selectedPromptVersions.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="7" class="empty-state">No version history found. Please add a version.</td>
            </tr>
        `;
        return;
    }

    state.selectedPromptVersions.forEach(v => {
        const row = document.createElement('tr');
        const createdStr = new Date(v.created_at).toLocaleString();
        
        row.innerHTML = `
            <td><strong>${v.version}</strong></td>
            <td><span style="font-size:0.85rem; color:var(--text-secondary);">${v.description || 'N/A'}</span></td>
            <td><code style="display:block; max-width: 140px; text-overflow:ellipsis; overflow:hidden; white-space:nowrap;" title="${escapeHtml(v.system_prompt || '')}">${escapeHtml(v.system_prompt || 'None')}</code></td>
            <td><code style="display:block; max-width: 250px; text-overflow:ellipsis; overflow:hidden; white-space:nowrap;" title="${escapeHtml(v.user_prompt)}">${escapeHtml(v.user_prompt)}</code></td>
            <td><span style="font-size:0.8rem; color:var(--text-muted);">${createdStr}</span></td>
            <td>
                ${v.is_active ? 
                    `<span class="badge badge-success">Active Default</span>` : 
                    `<span class="badge badge-secondary" style="opacity: 0.6;">Inactive</span>`
                }
            </td>
            <td>
                ${v.is_active ? 
                    `<button class="btn btn-secondary btn-icon-only" disabled><i data-lucide="check"></i></button>` : 
                    `<button class="btn btn-primary btn-icon-only activate-ver-btn" data-ver-id="${v.id}" title="Make Active Default"><i data-lucide="check-circle"></i></button>`
                }
            </td>
        `;

        const actBtn = row.querySelector('.activate-ver-btn');
        if (actBtn) {
            actBtn.addEventListener('click', async () => {
                try {
                    const res = await fetch(`/api/prompts/${state.selectedPrompt.id}/versions/${v.id}/activate`, {
                        method: 'PATCH',
                        headers: { 'Authorization': `Bearer ${state.accessToken}` }
                    });
                    if (!res.ok) throw new Error('Failed to activate version.');
                    showToast('Success', `Version ${v.version} is now the default version.`, 'success');
                    await fetchPromptDetail(state.selectedPrompt.id);
                } catch (err) {
                    showToast('Activation Error', err.message, 'error');
                }
            });
        }

        tbody.appendChild(row);
    });

    lucide.createIcons();
}

function updatePromptExperimentUI() {
    const list = document.getElementById('variants-weights-list');
    if (!list) return;

    list.innerHTML = '';

    // If less than 2 versions exist, we cannot run experiment split
    if (state.selectedPromptVersions.length < 2) {
        list.innerHTML = `<p style="font-size:0.85rem; color:var(--text-muted); text-align:center; padding: 1.5rem 0;">You must have at least 2 template versions created to configure an A/B split experiment.</p>`;
        document.getElementById('save-experiment-btn').disabled = true;
        return;
    }
    document.getElementById('save-experiment-btn').disabled = false;

    // Fill details name from current experiment if exists
    if (state.selectedPromptExperiment) {
        document.getElementById('exp-name-input').value = state.selectedPromptExperiment.name;
        document.getElementById('exp-active-input').checked = state.selectedPromptExperiment.is_active;
    } else {
        document.getElementById('exp-name-input').value = `${state.selectedPrompt.name} A/B Test`;
        document.getElementById('exp-active-input').checked = true;
    }

    // Build two default variants weight sliders, populate values from experiment if exists
    const variantsCount = 2; 
    let activeVariants = [];
    if (state.selectedPromptExperiment && state.selectedPromptExperiment.variants) {
        activeVariants = state.selectedPromptExperiment.variants;
    }

    for (let i = 0; i < variantsCount; i++) {
        const item = document.createElement('div');
        item.className = 'variant-weight-item';

        const defaultWeight = i === 0 ? 50 : 50;
        const currentVariant = activeVariants[i] || {};
        const chosenVersionId = currentVariant.version_id || '';
        const weightVal = currentVariant.weight !== undefined ? Math.round(currentVariant.weight * 100) : defaultWeight;

        let optionsHtml = state.selectedPromptVersions.map(v => 
            `<option value="${v.id}" ${chosenVersionId === v.id || (!chosenVersionId && i === 0 && v.is_active) ? 'selected' : ''}>${v.version}</option>`
        ).join('');

        item.innerHTML = `
            <div>
                <select class="variant-ver-select" style="width:100%;">
                    ${optionsHtml}
                </select>
            </div>
            <div>
                <input type="range" class="variant-weight-range" min="0" max="100" value="${weightVal}">
            </div>
            <div>
                <span class="weight-display-val">${weightVal}%</span>
            </div>
        `;

        const rangeInput = item.querySelector('.variant-weight-range');
        const displaySpan = item.querySelector('.weight-display-val');

        rangeInput.addEventListener('input', () => {
            displaySpan.textContent = `${rangeInput.value}%`;
            recalculateWeightsTotal();
        });

        list.appendChild(item);
    }

    recalculateWeightsTotal();
}

function recalculateWeightsTotal() {
    const ranges = document.querySelectorAll('.variant-weight-range');
    const totalSpan = document.getElementById('experiment-weights-total');
    if (!totalSpan) return;

    let sum = 0;
    ranges.forEach(r => sum += parseInt(r.value));

    totalSpan.textContent = `Total allocated: ${sum}%`;
    if (sum === 100) {
        totalSpan.style.color = 'var(--accent-green)';
        document.getElementById('save-experiment-btn').disabled = false;
    } else {
        totalSpan.style.color = 'var(--accent-red)';
        document.getElementById('save-experiment-btn').disabled = true;
    }
}

async function fetchPromptEvalMetrics(promptId) {
    try {
        const res = await fetch(`/api/prompts/${promptId}/eval`, {
            headers: { 'Authorization': `Bearer ${state.accessToken}` }
        });
        if (!res.ok) throw new Error('Failed to retrieve metrics analytics');
        const data = await res.json();
        
        const tbody = document.getElementById('prompt-eval-tbody');
        if (!tbody) return;

        tbody.innerHTML = '';
        if (data.versions.length === 0) {
            tbody.innerHTML = `<tr><td colspan="13" class="empty-state">No evaluations registered. Try invoking this template in playground.</td></tr>`;
            return;
        }

        data.versions.forEach(v => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td><strong>${v.version_str}</strong></td>
                <td>${v.total_calls}</td>
                <td><span class="badge ${v.success_rate >= 90 ? 'badge-success' : 'badge-warning'}">${v.success_rate}%</span></td>
                <td>${v.cache_hit_rate}%</td>
                <td><span class="badge ${v.guardrail_block_rate > 0 ? 'badge-error' : 'badge-success'}">${v.guardrail_block_rate}%</span></td>
                <td>${v.avg_latency_ms} ms</td>
                <td>$${v.avg_cost.toFixed(6)}</td>
                <td>${v.avg_helpfulness > 0 ? v.avg_helpfulness.toFixed(1) : 'N/A'}</td>
                <td>${v.avg_accuracy > 0 ? v.avg_accuracy.toFixed(1) : 'N/A'}</td>
                <td>${v.avg_safety > 0 ? v.avg_safety.toFixed(1) : 'N/A'}</td>
                <td>${v.avg_tone > 0 ? v.avg_tone.toFixed(1) : 'N/A'}</td>
                <td>${v.avg_completeness > 0 ? v.avg_completeness.toFixed(1) : 'N/A'}</td>
                <td>
                    <span style="font-weight:700; color:var(--accent-purple-light);">
                        ${v.avg_overall_score > 0 ? `${v.avg_overall_score.toFixed(1)} / 5.0` : 'N/A'}
                    </span>
                </td>
            `;
            tbody.appendChild(row);
        });

    } catch (err) {
        console.error('Error fetching prompt evaluation data:', err);
    }
}

function updatePromptSandboxPlaygroundUI() {
    // Populate keys override list
    const keySelect = document.getElementById('sandbox-key-select');
    if (keySelect) {
        keySelect.innerHTML = '';
        
        if (!state.keys || state.keys.length === 0) {
            keySelect.innerHTML = `<option value="">Create an API Key first</option>`;
        } else {
            const activeKeys = state.keys.filter(k => k.is_active);
            if (activeKeys.length === 0) {
                keySelect.innerHTML = `<option value="">No active API key available</option>`;
            } else {
                keySelect.innerHTML = '<option value="">Default Session Key</option>';
                activeKeys.forEach(k => {
                    keySelect.innerHTML += `<option value="${k.id}">${k.name} (${k.key_prefix}...)</option>`;
                });
            }
        }
    }

    // Populate versions select
    const verSelect = document.getElementById('sandbox-version-select');
    if (verSelect) {
        verSelect.innerHTML = '';
        
        if (!state.selectedPromptVersions || state.selectedPromptVersions.length === 0) {
            verSelect.innerHTML = `<option value="">No versions available</option>`;
            const runBtn = document.getElementById('run-sandbox-prompt-btn');
            if (runBtn) runBtn.disabled = true;
            return;
        }
        const runBtn = document.getElementById('run-sandbox-prompt-btn');
        if (runBtn) runBtn.disabled = false;

        // Fills versions select list
        state.selectedPromptVersions.forEach(v => {
            verSelect.innerHTML += `<option value="${v.version}" ${v.is_active ? 'selected' : ''}>${v.version} ${v.is_active ? '(Active Default)' : ''}</option>`;
        });

        verSelect.onchange = () => {
            setupVariablesInputs();
        };
    }

    // Populate provider/model selects based on dynamic options
    const provSelect = document.getElementById('sandbox-provider-select');
    const modelSelect = document.getElementById('sandbox-model-select');
    
    if (provSelect) {
        provSelect.innerHTML = '<option value="">Default Routing</option>';
        if (state.providersModels) {
            Object.keys(state.providersModels).forEach(p => {
                provSelect.innerHTML += `<option value="${p}">${p.toUpperCase()}</option>`;
            });
        }
    }

    if (modelSelect) {
        modelSelect.innerHTML = '<option value="">Default Model</option>';
    }

    if (provSelect && modelSelect) {
        provSelect.onchange = () => {
            modelSelect.innerHTML = '<option value="">Default Model</option>';
            const chosen = provSelect.value;
            if (chosen && state.providersModels && state.providersModels[chosen]) {
                state.providersModels[chosen].forEach(m => {
                    modelSelect.innerHTML += `<option value="${m}">${m}</option>`;
                });
            }
        };
    }

    setupVariablesInputs();
}

function setupVariablesInputs() {
    const verSelect = document.getElementById('sandbox-version-select');
    const chosenVer = verSelect.value;
    const versionObj = state.selectedPromptVersions.find(v => v.version === chosenVer);

    const inputsDiv = document.getElementById('sandbox-variables-inputs');
    inputsDiv.innerHTML = '';
    state.sandboxVariables = {};
    state.sandboxTraceId = null;
    document.getElementById('sandbox-response-card').classList.add('hidden');
    document.getElementById('sandbox-feedback-section').style.display = 'block';
    
    // Clear stars rating
    document.querySelectorAll('#sandbox-feedback-stars .star-btn').forEach(b => b.classList.remove('active'));
    state.sandboxRating = 0;

    if (!versionObj) {
        inputsDiv.innerHTML = `<p style="font-size:0.8rem; color:var(--text-muted);">No version selected.</p>`;
        return;
    }

    // Extract placeholders using double curly braces: {{var_name}}
    const combined = (versionObj.system_prompt || '') + '\n' + versionObj.user_prompt;
    const regex = /\{\{([a-zA-Z0-9_]+)\}\}/g;
    const matches = new Set();
    let m;
    while ((m = regex.exec(combined)) !== null) {
        matches.add(m[1]);
    }

    const uniqueVars = Array.from(matches);

    if (uniqueVars.length === 0) {
        inputsDiv.innerHTML = `<p style="font-size:0.8rem; color:var(--text-muted);">No variable placeholders (e.g. {{var}}) found in this version prompt.</p>`;
        renderLivePreview(versionObj, {});
        return;
    }

    // Generate input forms
    uniqueVars.forEach(vName => {
        state.sandboxVariables[vName] = '';

        const group = document.createElement('div');
        group.className = 'form-group';
        group.innerHTML = group.innerHTML = `
            <label style="font-size:0.8rem; color: #cbd5e1; margin-bottom: 0.2rem;">${vName}</label>
            <input type="text" class="sandbox-var-input-field" data-var-name="${vName}" placeholder="Enter value for {{${vName}}}" style="width: 100%; padding: 0.85rem 1.1rem; font-size: 0.95rem; background: #090d16 !important; color: #f8fafc !important; border: 1px solid rgba(255,255,255,0.12) !important; border-radius: 8px !important;">
        `;

        const input = group.querySelector('.sandbox-var-input-field');
        input.addEventListener('input', (e) => {
            state.sandboxVariables[vName] = e.target.value;
            renderLivePreview(versionObj, state.sandboxVariables);
            runLiveVariablesValidation(versionObj);
        });

        inputsDiv.appendChild(group);
    });

    renderLivePreview(versionObj, {});
    runLiveVariablesValidation(versionObj);
}

function renderLivePreview(versionObj, variables) {
    const previewUser = document.getElementById('sandbox-rendered-user');
    const previewSystem = document.getElementById('sandbox-rendered-system');

    let sysText = versionObj.system_prompt || '';
    let userText = versionObj.user_prompt || '';

    // Interpolate variables client-side
    Object.keys(variables).forEach(k => {
        const val = variables[k] || `{{${k}}}`;
        const search = `{{${k}}}`;
        
        // Replace all occurrences
        sysText = sysText.split(search).join(val);
        userText = userText.split(search).join(val);
    });

    previewUser.textContent = userText;
    previewSystem.textContent = sysText || "No system instructions template.";
}

async function runLiveVariablesValidation(versionObj) {
    const alertDiv = document.getElementById('sandbox-validation-summary');
    const listUl = document.getElementById('sandbox-validation-list');
    const titleH5 = document.getElementById('sandbox-validation-title');

    try {
        const res = await fetch(`/api/prompts/${state.selectedPrompt.id}/preview`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${state.accessToken}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                system_prompt: versionObj.system_prompt,
                user_prompt: versionObj.user_prompt,
                variables: state.sandboxVariables
            })
        });

        if (!res.ok) return; // Silent discard
        const outcome = await res.json();

        listUl.innerHTML = '';
        if (outcome.valid) {
            alertDiv.className = "validation-summary-card valid";
            titleH5.textContent = "Variables Verified (Ready)";
            alertDiv.style.display = 'block';
        } else {
            alertDiv.className = "validation-summary-card";
            titleH5.textContent = "Variable Validation Warnings";
            
            // Build warnings lists
            Object.keys(outcome.errors).forEach(errCategory => {
                outcome.errors[errCategory].forEach(msg => {
                    const li = document.createElement('li');
                    li.textContent = `${errCategory.toUpperCase()}: ${msg}`;
                    listUl.appendChild(li);
                });
            });
            alertDiv.style.display = 'block';
        }

    } catch (err) {
        console.error(err);
    }
}

async function handleSandboxPromptExecute() {
    const btn = document.getElementById('run-sandbox-prompt-btn');
    const verSelect = document.getElementById('sandbox-version-select');
    const chosenVer = verSelect.value;
    const keyId = document.getElementById('sandbox-key-select').value;
    const sessionKey = state.sessionRawKeys[keyId];
    const rawKey = (sessionKey && sessionKey.startsWith('gw_live_')) ? sessionKey : state.accessToken;
    const providerOverride = document.getElementById('sandbox-provider-select').value;
    const modelOverride = document.getElementById('sandbox-model-select').value;

    if (!state.selectedPrompt || !chosenVer) return;

    setButtonState(btn, true, "Executing Sandbox Request...", "play");

    try {
        // Execute request to the proxy gateway endpoint using credentials and prompt template name payload
        const payload = {
            prompt_template_name: state.selectedPrompt.name,
            prompt_template_version: chosenVer,
            variables: state.sandboxVariables
        };

        if (providerOverride) payload.provider = providerOverride;
        if (modelOverride) payload.model = modelOverride;

        // Perform call via headers token validation check
        const res = await fetch('/api/gateway/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${rawKey}`
            },
            body: JSON.stringify(payload)
        });

        if (!res.ok) {
            let errText = 'Gateway execution failed';
            try {
                const err = await res.json();
                errText = err.detail && typeof err.detail === 'object' ? err.detail.error.message : (err.detail || errText);
            } catch (e) {
                errText = await res.text();
            }
            throw new Error(errText);
        }

        const data = await res.json();

        // Render response card
        document.getElementById('sandbox-response-card').classList.remove('hidden');
        document.getElementById('sandbox-response-output').textContent = data.response_text;
        
        document.getElementById('sandbox-meta-badge').textContent = `${data.provider.toUpperCase()} | ${data.model}`;
        document.getElementById('sandbox-meta-latency').textContent = `${data.latency_ms} ms`;
        document.getElementById('sandbox-meta-tokens').textContent = `${data.total_tokens || 0} (${data.prompt_tokens || 0} in / ${data.completion_tokens || 0} out)`;
        document.getElementById('sandbox-meta-cost').textContent = `$${data.cost.toFixed(5)}`;
        
        const traceId = data.request_id || 'N/A';
        document.getElementById('sandbox-meta-trace-id').textContent = traceId;
        state.sandboxTraceId = traceId;

        // Reset feedback section
        document.getElementById('sandbox-feedback-section').style.display = 'block';
        document.querySelectorAll('#sandbox-feedback-stars .star-btn').forEach(b => b.classList.remove('active'));
        state.sandboxRating = 0;

        showToast('Execution Success', 'Prompt template routed and model completed successfully.', 'success');

    } catch (err) {
        showToast('Gateway Execution Error', err.message, 'error');
    } finally {
        setButtonState(btn, false, "Execute Prompt Request", "play");
    }
}

function escapeHtml(str) {
    if (!str) return '';
    return str
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

// --- Phase 10 Model Evaluation & Benchmarking Platform ---

async function apiRequest(url, method = 'GET', body = null) {
    const headers = {};
    if (body) {
        headers['Content-Type'] = 'application/json';
    }
    if (state.accessToken) {
        headers['Authorization'] = `Bearer ${state.accessToken}`;
    }
    const options = { method, headers };
    if (body) {
        options.body = JSON.stringify(body);
    }
    const res = await fetch(url, options);
    if (!res.ok) {
        let errText = 'Request failed';
        try {
            const err = await res.json();
            errText = err.detail && typeof err.detail === 'object' ? err.detail.error.message : (err.detail || errText);
        } catch (e) {
            errText = await res.text();
        }
        throw new Error(errText);
    }
    return await res.json();
}

async function fetchLeaderboard(sortBy = 'quality') {
    const tbody = document.getElementById('leaderboard-tbody');
    if (!tbody) return;

    try {
        const res = await apiRequest(`/api/benchmarks/leaderboard?sort_by=${sortBy}`);
        if (!res) return;

        if (res.length === 0) {
            tbody.innerHTML = `<tr><td colspan="9" style="text-align: center; color: var(--text-secondary); padding: 2rem;">No benchmark runs recorded yet. Launch a benchmark to generate rankings.</td></tr>`;
            return;
        }

        tbody.innerHTML = res.map((item, idx) => {
            const rankBadge = idx === 0 ? '🥇' : idx === 1 ? '🥈' : idx === 2 ? '🥉' : `#${idx + 1}`;
            const qualityDisplay = item.mean_quality_score > 0 ? `⭐ ${item.mean_quality_score.toFixed(2)} / 5.0` : 'N/A';
            const costDisplay = `$${item.mean_cost.toFixed(6)}`;
            
            return `
                <tr>
                    <td style="font-weight: 700; font-size: 1rem;">${rankBadge}</td>
                    <td>
                        <strong style="color: #f8fafc;">${escapeHtml(item.model)}</strong>
                        <span style="font-size: 0.75rem; color: var(--text-secondary); display: block;">${escapeHtml(item.provider.toUpperCase())}</span>
                    </td>
                    <td><span class="plan-info-pill" style="background: rgba(245, 158, 11, 0.15); color: #fbbf24; font-size: 0.85rem;">${qualityDisplay}</span></td>
                    <td style="font-weight: 600; color: #60a5fa;">${item.p50_latency_ms} ms</td>
                    <td style="color: #a78bfa;">${item.p95_latency_ms} ms</td>
                    <td style="color: var(--text-secondary); font-size: 0.85rem;">±${item.std_dev_latency_ms} ms</td>
                    <td style="font-family: monospace;">${costDisplay}</td>
                    <td style="font-family: monospace; color: var(--accent-green);">${item.mean_generation_tps} t/s</td>
                    <td>
                        <span class="status-badge ${item.success_rate >= 90 ? 'active' : 'expired'}">
                            ${item.success_rate}%
                        </span>
                    </td>
                </tr>
            `;
        }).join('');

    } catch (err) {
        showToast('Error Loading Leaderboard', err.message, 'error');
    }
}

async function fetchBenchmarkJobs() {
    const container = document.getElementById('benchmark-jobs-container');
    if (!container) return;

    try {
        const jobs = await apiRequest('/api/benchmarks/jobs');
        if (!jobs) return;

        if (jobs.length === 0) {
            container.innerHTML = `<div style="text-align: center; color: var(--text-secondary); padding: 2rem;">No benchmark jobs recorded yet. Click "Launch Benchmark Run" above.</div>`;
            return;
        }

        container.innerHTML = jobs.map(j => {
            const dt = new Date(j.created_at).toLocaleString();
            const modelsCount = j.target_models ? j.target_models.length : 4;
            const totalRuns = modelsCount * j.trials_count;

            return `
                <div class="quota-banner-card" style="margin-bottom: 0; padding: 1rem;">
                    <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 0.5rem;">
                        <div>
                            <h4 style="margin: 0; color: #f8fafc; font-size: 1rem;">${escapeHtml(j.name)}</h4>
                            <span style="font-size: 0.8rem; color: var(--text-secondary);">Executed ${dt} | ${j.trials_count} trials × ${modelsCount} models (${totalRuns} total runs)</span>
                        </div>
                        <div style="display: flex; align-items: center; gap: 0.75rem;">
                            <span class="status-badge ${j.status === 'completed' ? 'active' : j.status === 'partial_failure' ? 'revoked' : 'expired'}">
                                ${j.status.toUpperCase()}
                            </span>
                        </div>
                    </div>
                    <pre style="background: #090d16; padding: 0.5rem 0.75rem; border-radius: 4px; font-family: monospace; font-size: 0.8rem; color: #9aa2c0; margin-top: 0.75rem; white-space: pre-wrap; max-height: 60px; overflow: hidden;">Prompt: ${escapeHtml(j.prompt)}</pre>
                </div>
            `;
        }).join('');

    } catch (err) {
        showToast('Error Loading Benchmark Jobs', err.message, 'error');
    }
}

// Global Event Listeners for Phase 10
document.addEventListener('DOMContentLoaded', () => {
    const openBmModalBtn = document.getElementById('open-benchmark-modal-btn');
    const createBmModal = document.getElementById('create-benchmark-modal');
    const createBmForm = document.getElementById('create-benchmark-form');
    const sortSelect = document.getElementById('leaderboard-sort-select');

    if (openBmModalBtn && createBmModal) {
        openBmModalBtn.addEventListener('click', () => {
            createBmModal.classList.remove('hidden');
        });
    }

    if (sortSelect) {
        sortSelect.addEventListener('change', () => {
            fetchLeaderboard(sortSelect.value);
        });
    }

    if (createBmForm) {
        createBmForm.addEventListener('submit', async (e) => {
            e.preventDefault();

            const name = document.getElementById('bm-name-input').value.trim();
            const prompt = document.getElementById('bm-prompt-input').value.trim();
            const trialsCount = parseInt(document.getElementById('bm-trials-input').value) || 3;
            const timeoutSeconds = parseInt(document.getElementById('bm-timeout-input').value) || 15;
            const bypassCache = document.getElementById('bm-bypass-cache').checked;
            const runGuardrails = document.getElementById('bm-run-guardrails').checked;

            const selectedModels = [];
            document.querySelectorAll('input[name="bm-models"]:checked').forEach(cb => {
                const [p, m] = cb.value.split('::');
                selectedModels.push({ provider: p, model: m });
            });

            if (selectedModels.length === 0) {
                showToast('Validation Error', 'Please select at least one target model for the benchmark.', 'warning');
                return;
            }

            const btn = createBmForm.querySelector('button[type="submit"]');
            setButtonState(btn, true, 'Executing Benchmark...', 'loader');

            try {
                const res = await apiRequest('/api/benchmarks/jobs', 'POST', {
                    name,
                    prompt,
                    target_models: selectedModels,
                    trials_count: trialsCount,
                    bypass_cache: bypassCache,
                    run_guardrails: runGuardrails,
                    timeout_seconds: timeoutSeconds
                });

                if (res) {
                    showToast('Benchmark Complete', `Job '${name}' completed successfully across ${selectedModels.length} models!`, 'success');
                    createBmModal.classList.add('hidden');
                    createBmForm.reset();
                    fetchLeaderboard(sortSelect ? sortSelect.value : 'quality');
                    fetchBenchmarkJobs();
                }
            } catch (err) {
                showToast('Benchmark Failed', err.message, 'error');
            } finally {
                setButtonState(btn, false, 'Execute Benchmark', 'play');
            }
        });
    }
});

