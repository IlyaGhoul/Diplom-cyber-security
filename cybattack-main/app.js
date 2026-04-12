(() => {
    const apiBase = typeof window.CYBER_VIS_API_BASE !== 'undefined'
        ? window.CYBER_VIS_API_BASE
        : `${location.protocol}//${location.host}`;
    const wsUrl = typeof window.CYBER_VIS_WS_URL !== 'undefined'
        ? window.CYBER_VIS_WS_URL
        : (location.protocol === 'https:' ? `wss://${location.host}/ws/monitor` : `ws://${location.host}/ws/monitor`);

    console.log('🚀 Страница загружена');
    console.log('API_BASE:', apiBase);
    console.log('WS_URL:', wsUrl);

    let ws = null;
    let totalChart = null;
    let reconnectTimer = null;
    let chartRefreshTimer = null;
    let statsRefreshTimer = null;
    let attemptsRefreshTimer = null;
    let blockedRefreshTimer = null;

    let liveAttempts = [];
    let recentAttempts = [];
    let blockedIps = [];

    const maxLiveAttempts = 20;
    const maxRecentAttempts = 20;

    const byId = (id) => document.getElementById(id);

    const setText = (id, value) => {
        const element = byId(id);
        if (element) {
            element.textContent = value;
        }
    };

    const setConnectionStatus = (connected) => {
        const statusElement = byId('wsStatus');
        if (!statusElement) return;
        if (connected) {
            statusElement.textContent = '🟢 Подключено';
            statusElement.className = 'connection-status connected pulse';
        } else {
            statusElement.textContent = '🔴 Не подключено';
            statusElement.className = 'connection-status disconnected';
        }
    };

    const showError = (message) => {
        const errorContainer = byId('errorContainer');
        if (!errorContainer) return;
        errorContainer.innerHTML = `
            <div class="error-message">
                <strong>⚠️ Ошибка:</strong> ${message}
                <br>
                <button class="retry-button" onclick="retryConnection()">Повторить подключение</button>
            </div>
        `;
    };

    const clearError = () => {
        const errorContainer = byId('errorContainer');
        if (errorContainer) {
            errorContainer.innerHTML = '';
        }
    };

    const updateLastUpdateTime = () => {
        const lastUpdate = byId('lastUpdate');
        if (lastUpdate) {
            lastUpdate.textContent = `Последнее обновление: ${new Date().toLocaleTimeString()}`;
        }
    };

    const updateStats = (stats) => {
        if (!stats) return;
        setText('totalAttempts', stats.total_attempts ?? stats.total ?? 0);
        setText('successfulAttempts', stats.successful ?? stats.login_attempts?.successful ?? 0);
        setText('failedAttempts', stats.failed ?? stats.login_attempts?.failed ?? 0);
        setText('uniqueUsers', stats.unique_users ?? 0);
        setText('uniqueIPs', stats.unique_ips ?? 0);
        setText('lastHourAttempts', stats.last_hour ?? stats.last_24h?.total ?? 0);
        setText('last10MinAttempts', stats.last_10_min ?? 0);
    };

    const createAttemptElement = (attempt) => {
        const attemptElement = document.createElement('div');
        attemptElement.className = `attempt-item ${attempt.success ? 'success' : 'failed'}`;

        const timestampValue = attempt.timestamp || attempt.attempt_time || attempt.created_at || new Date().toISOString();
        const time = new Date(timestampValue);
        const timeStr = time.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        const dateStr = time.toLocaleDateString();

        attemptElement.innerHTML = `
            <div class="attempt-header">
                <div class="attempt-username">${attempt.username || 'Неизвестно'}</div>
                <div class="attempt-time">${dateStr} ${timeStr}</div>
            </div>
            <div class="attempt-info">
                <div>
                    <span class="attempt-badge ${attempt.success ? 'badge-success' : 'badge-failed'}">
                        ${attempt.success ? '✅ Успешно' : '❌ Неудачно'}
                    </span>
                    <span style="margin-left: 10px;">${attempt.reason || ''}</span>
                </div>
                <div>
                    <span>${attempt.client_type || ''}</span>
                    <span style="margin-left:12px;color:#888;">IP: ${attempt.ip_address || (attempt.client_info && attempt.client_info.ip_address) || '---'}</span>
                    <span style="margin-left:12px;color:#999;">🌍 ${attempt.country || 'Неизвестно'}</span>
                </div>
            </div>
        `;

        return attemptElement;
    };

    const renderAttemptsList = (attempts, listId, countId) => {
        const container = byId(listId);
        if (!container) return;
        container.innerHTML = '';
        const items = Array.isArray(attempts) ? attempts : [];
        if (items.length === 0) {
            container.innerHTML = '<div class="empty-state">Нет данных</div>';
        } else {
            items.forEach((attempt) => {
                container.appendChild(createAttemptElement(attempt));
            });
        }
        if (countId) {
            setText(countId, items.length);
        }
    };

    const renderBlockedIps = (ips) => {
        const container = byId('blockedIpsList');
        if (!container) return;
        container.innerHTML = '';
        const items = Array.isArray(ips) ? ips : [];
        if (items.length === 0) {
            container.innerHTML = '<div class="empty-state">Нет заблокированных IP</div>';
        } else {
            items.forEach((item) => {
                const element = document.createElement('div');
                element.className = 'attempt-item failed';
                element.innerHTML = `
                    <div class="attempt-header">
                        <div class="attempt-username">${item.ip_address || '---'}</div>
                        <div class="attempt-time">${item.blocked_until ? new Date(item.blocked_until).toLocaleString() : ''}</div>
                    </div>
                    <div class="attempt-info">
                        <div>${item.reason || ''}</div>
                    </div>
                `;
                container.appendChild(element);
            });
        }
        setText('blockedIpsCount', items.length);
    };

    const fetchJson = async (path) => {
        const response = await fetch(`${apiBase}${path}`);
        if (!response.ok) {
            throw new Error(`HTTP ошибка: ${response.status}`);
        }
        return response.json();
    };

    const loadStats = async () => {
        try {
            console.log('🔄 Обновление данных статистики...');
            const data = await fetchJson('/api/stats');
            if (data.success) {
                updateStats(data.data);
                updateLastUpdateTime();
            }
        } catch (error) {
            console.error('❌ Ошибка загрузки статистики:', error);
        }
    };

    const loadRecentAttempts = async () => {
        try {
            const data = await fetchJson('/api/attempts?limit=20');
            if (data.success) {
                recentAttempts = data.data || [];
                renderAttemptsList(recentAttempts, 'recentAttemptsList', 'recentAttemptsCount');
            }
        } catch (error) {
            console.error('❌ Ошибка загрузки попыток:', error);
        }
    };

    const loadBlockedIps = async () => {
        try {
            const data = await fetchJson('/api/blocked-ips');
            if (data.success) {
                blockedIps = data.data || [];
                renderBlockedIps(blockedIps);
            }
        } catch (error) {
            console.error('❌ Ошибка загрузки заблокированных IP:', error);
        }
    };

    const initChart = () => {
        const canvas = byId('totalChart');
        if (!canvas || !window.Chart) return;
        totalChart = new Chart(canvas, {
            type: 'doughnut',
            data: {
                labels: ['Успешные', 'Неудачные'],
                datasets: [{
                    data: [0, 0],
                    backgroundColor: ['#4ade80', '#f87171'],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        labels: { color: '#ffffff' }
                    }
                }
            }
        });
    };

    const updateChartValues = (chartData) => {
        const total = chartData?.total || {};
        const successful = total.successful ?? 0;
        const failed = total.failed ?? 0;
        const totalCount = total.total ?? (successful + failed);
        setText('chartSuccessful', successful);
        setText('chartFailed', failed);
        setText('chartTotal', totalCount);
        if (totalChart) {
            totalChart.data.datasets[0].data = [successful, failed];
            totalChart.update();
        }
    };

    const loadChartData = async () => {
        try {
            console.log('📈 Обновляю данные графика...');
            const data = await fetchJson('/api/chart_data');
            if (data.success) {
                updateChartValues(data.data);
            }
        } catch (error) {
            console.error('❌ Ошибка загрузки данных графика:', error);
        }
    };

    const handleWebSocketMessage = (message) => {
        if (!message || !message.type) return;
        console.log('📨 WebSocket сообщение:', message.type);
        if (message.type === 'init') {
            updateStats(message.data?.stats);
            updateChartValues(message.data?.chart_data);
            recentAttempts = message.data?.recent_attempts || [];
            renderAttemptsList(recentAttempts, 'recentAttemptsList', 'recentAttemptsCount');
            updateLastUpdateTime();
            return;
        }
        if (message.type === 'login_attempt' && message.data) {
            liveAttempts.unshift(message.data);
            if (liveAttempts.length > maxLiveAttempts) {
                liveAttempts = liveAttempts.slice(0, maxLiveAttempts);
            }
            recentAttempts.unshift(message.data);
            if (recentAttempts.length > maxRecentAttempts) {
                recentAttempts = recentAttempts.slice(0, maxRecentAttempts);
            }
            renderAttemptsList(liveAttempts, 'liveAttemptsList', 'liveAttemptsCount');
            renderAttemptsList(recentAttempts, 'recentAttemptsList', 'recentAttemptsCount');
            loadStats();
            loadChartData();
            return;
        }
        if (message.type === 'ip_blocked') {
            loadBlockedIps();
            return;
        }
        if (message.type === 'stats_update') {
            updateStats(message.data);
            updateLastUpdateTime();
        }
    };

    const connectWebSocket = () => {
        if (ws) {
            ws.close();
        }
        ws = new WebSocket(wsUrl);
        ws.onopen = () => {
            setConnectionStatus(true);
            clearError();
            console.log('✅ Подключено к WebSocket');
        };
        ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                handleWebSocketMessage(data);
            } catch (error) {
                console.error('❌ Ошибка парсинга WebSocket:', error);
            }
        };
        ws.onerror = (error) => {
            console.error('❌ WebSocket ошибка:', error);
            setConnectionStatus(false);
        };
        ws.onclose = () => {
            setConnectionStatus(false);
            if (reconnectTimer) {
                clearTimeout(reconnectTimer);
            }
            reconnectTimer = setTimeout(connectWebSocket, 5000);
        };
    };

    const loadInitialData = () => {
        loadStats();
        loadRecentAttempts();
        loadBlockedIps();
        loadChartData();
    };

    window.retryConnection = () => {
        clearError();
        connectWebSocket();
        loadInitialData();
    };

    window.addEventListener('load', () => {
        initChart();
        loadInitialData();
        connectWebSocket();
        statsRefreshTimer = setInterval(loadStats, 10000);
        attemptsRefreshTimer = setInterval(loadRecentAttempts, 15000);
        blockedRefreshTimer = setInterval(loadBlockedIps, 30000);
        chartRefreshTimer = setInterval(loadChartData, 15000);
    });
})();
