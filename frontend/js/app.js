/**
 * Main Dashboard Application
 * Handles WebSocket connection, data updates, and UI interactions
 */

class TrafficDashboard {
    constructor() {
        this.ws = null;
        this.chart = null;
        this.chartData = {
            labels: [],
            datasets: []
        };
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;

        this.init();
    }

    /**
     * Initialize dashboard
     */
    init() {
        this.setupClock();
        this.setupEventListeners();
        this.connectWebSocket();
        this.loadInitialData();
    }

    /**
     * Setup clock
     */
    setupClock() {
        const updateClock = () => {
            const now = new Date();
            const timeString = now.toLocaleTimeString('en-US', { hour12: false });
            document.getElementById('clock').textContent = timeString;
        };

        updateClock();
        setInterval(updateClock, 1000);
    }

    /**
     * Setup event listeners
     */
    setupEventListeners() {
        // Mode toggle
        document.getElementById('mode-toggle').addEventListener('click', () => {
            this.toggleMode();
        });

        // Emergency button
        document.getElementById('emergency-btn').addEventListener('click', () => {
            this.openEmergencyModal();
        });

        // Emergency modal close
        document.getElementById('modal-close').addEventListener('click', () => {
            this.closeEmergencyModal();
        });

        // Emergency lane buttons
        document.querySelectorAll('.lane-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const lane = e.target.getAttribute('data-lane');
                this.triggerEmergency(lane);
            });
        });

        // Close modal on background click
        document.getElementById('emergency-modal').addEventListener('click', (e) => {
            if (e.target.id === 'emergency-modal') {
                this.closeEmergencyModal();
            }
        });
    }

    /**
     * Setup Chart.js chart (DISABLED - no chart in new layout)
     */
    setupChart() {
        // Chart removed from new layout
        return;

        const ctx = document.getElementById('traffic-chart').getContext('2d');

        this.chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [
                    {
                        label: 'North',
                        data: [],
                        borderColor: '#06b6d4',
                        backgroundColor: 'rgba(6, 182, 212, 0.1)',
                        tension: 0.4,
                        borderWidth: 2
                    },
                    {
                        label: 'South',
                        data: [],
                        borderColor: '#10b981',
                        backgroundColor: 'rgba(16, 185, 129, 0.1)',
                        tension: 0.4,
                        borderWidth: 2
                    },
                    {
                        label: 'East',
                        data: [],
                        borderColor: '#f59e0b',
                        backgroundColor: 'rgba(245, 158, 11, 0.1)',
                        tension: 0.4,
                        borderWidth: 2
                    },
                    {
                        label: 'West',
                        data: [],
                        borderColor: '#8b5cf6',
                        backgroundColor: 'rgba(139, 92, 246, 0.1)',
                        tension: 0.4,
                        borderWidth: 2
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: true,
                        position: 'top',
                        labels: {
                            color: '#9ca3af',
                            font: {
                                family: 'JetBrains Mono',
                                size: 11
                            }
                        }
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false,
                        backgroundColor: 'rgba(17, 24, 39, 0.95)',
                        titleColor: '#f9fafb',
                        bodyColor: '#9ca3af',
                        borderColor: 'rgba(255, 255, 255, 0.1)',
                        borderWidth: 1
                    }
                },
                scales: {
                    x: {
                        display: true,
                        grid: {
                            color: 'rgba(255, 255, 255, 0.05)'
                        },
                        ticks: {
                            color: '#6b7280',
                            font: {
                                family: 'JetBrains Mono',
                                size: 10
                            },
                            maxTicksLimit: 10
                        }
                    },
                    y: {
                        display: true,
                        beginAtZero: true,
                        grid: {
                            color: 'rgba(255, 255, 255, 0.05)'
                        },
                        ticks: {
                            color: '#6b7280',
                            font: {
                                family: 'JetBrains Mono',
                                size: 10
                            }
                        },
                        title: {
                            display: true,
                            text: 'Density Score',
                            color: '#9ca3af',
                            font: {
                                family: 'Plus Jakarta Sans',
                                size: 11
                            }
                        }
                    }
                },
                interaction: {
                    mode: 'nearest',
                    axis: 'x',
                    intersect: false
                }
            }
        });
    }

    /**
     * Connect to WebSocket
     */
    connectWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/live`;

        console.log('Connecting to WebSocket:', wsUrl);

        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
            console.log('WebSocket connected');
            this.reconnectAttempts = 0;
            this.updateConnectionStatus(true);
        };

        this.ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                this.handleUpdate(data);
            } catch (error) {
                console.error('Error parsing WebSocket message:', error);
            }
        };

        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            this.updateConnectionStatus(false);
        };

        this.ws.onclose = () => {
            console.log('WebSocket disconnected');
            this.updateConnectionStatus(false);

            // Attempt to reconnect
            if (this.reconnectAttempts < this.maxReconnectAttempts) {
                this.reconnectAttempts++;
                console.log(`Reconnecting... Attempt ${this.reconnectAttempts}`);
                setTimeout(() => this.connectWebSocket(), 3000);
            }
        };
    }

    /**
     * Update connection status indicator
     */
    updateConnectionStatus(connected) {
        const statusDot = document.getElementById('status-dot');
        const statusText = document.getElementById('connection-text');

        if (connected) {
            statusDot.classList.remove('disconnected');
            statusText.textContent = 'Connected';
        } else {
            statusDot.classList.add('disconnected');
            statusText.textContent = 'Disconnected';
        }
    }

    /**
     * Handle WebSocket update
     */
    handleUpdate(data) {
        console.log('WebSocket update received:', data);

        // Update lane panels
        ['N', 'S', 'E', 'W'].forEach(lane => {
            if (data.lanes[lane]) {
                this.updateLanePanel(lane, data.lanes[lane]);
            }
        });

        // Update intersection animation
        intersectionAnimator.updateSignals(data.lanes);
        intersectionAnimator.updateVehicles(data.lanes);

        // Update emergency status
        this.updateEmergencyStatus(data.emergency_active, data.emergency_lane);

        // Update mode display
        this.updateModeDisplay(data.mode);
    }

    /**
     * Update lane panel
     */
    updateLanePanel(lane, laneData) {
        console.log(`Updating lane ${lane}:`, laneData);

        // Update vehicle count
        const vehiclesEl = document.getElementById(`vehicles-${lane}`);
        if (vehiclesEl) {
            this.animateNumber(vehiclesEl, laneData.vehicles || 0);
        } else {
            console.warn(`Element vehicles-${lane} not found`);
        }

        // Update queue
        const queueEl = document.getElementById(`queue-${lane}`);
        if (queueEl) {
            this.animateNumber(queueEl, laneData.queue || 0);
        }

        // Update density value
        const densityValEl = document.getElementById(`density-val-${lane}`);
        if (densityValEl) {
            densityValEl.textContent = Math.round(laneData.density || 0);
        }

        // Update signal indicator
        const signalEl = document.getElementById(`signal-${lane}`);
        if (signalEl) {
            signalEl.className = `signal-indicator ${laneData.phase}`;
        }

        // Update countdown timer
        const countdownEl = document.getElementById(`countdown-${lane}`);
        if (countdownEl) {
            const remaining = laneData.remaining || 0;
            const phase = laneData.phase || 'red';

            countdownEl.textContent = `${phase === 'green' ? '🟢' : phase === 'yellow' ? '🟡' : '🔴'} ${remaining}s`;

            // Add urgent class if low time
            if (remaining < 5 && phase === 'green') {
                countdownEl.classList.add('urgent');
            } else {
                countdownEl.classList.remove('urgent');
            }
        }
    }

    /**
     * Animate number change
     */
    animateNumber(element, targetValue) {
        const currentValue = parseInt(element.textContent) || 0;

        if (currentValue === targetValue) return;

        const duration = 500;
        const steps = 20;
        const stepValue = (targetValue - currentValue) / steps;
        let currentStep = 0;

        const interval = setInterval(() => {
            currentStep++;
            const newValue = Math.round(currentValue + (stepValue * currentStep));

            element.textContent = newValue;

            if (currentStep >= steps) {
                element.textContent = targetValue;
                clearInterval(interval);
            }
        }, duration / steps);
    }

    /**
     * Update emergency status
     */
    updateEmergencyStatus(active, lane) {
        const statusEl = document.getElementById('emergency-status');
        const laneEl = document.getElementById('emergency-lane');

        if (active && lane) {
            statusEl.textContent = 'ACTIVE';
            statusEl.style.color = '#ef4444';
            laneEl.textContent = `Lane ${lane}`;

            // Highlight emergency lane panel
            ['N', 'S', 'E', 'W'].forEach(l => {
                const panel = document.getElementById(`lane-${l}`);
                if (l === lane) {
                    panel.classList.add('emergency');
                } else {
                    panel.classList.remove('emergency');
                }
            });
        } else {
            statusEl.textContent = 'NONE';
            statusEl.style.color = '#10b981';
            laneEl.textContent = '';

            // Remove emergency highlighting
            ['N', 'S', 'E', 'W'].forEach(l => {
                const panel = document.getElementById(`lane-${l}`);
                panel.classList.remove('emergency');
            });
        }
    }

    /**
     * Update mode display
     */
    updateModeDisplay(mode) {
        const modeText = document.getElementById('mode-text');
        modeText.textContent = mode === 'ai_optimized' ? 'AI Mode' : 'Fixed Timer';
    }

    /**
     * Update chart with new data
     */
    updateChart(data) {
        const time = new Date().toLocaleTimeString('en-US', {
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            hour12: false
        });

        // Add new data point
        this.chart.data.labels.push(time);
        this.chart.data.datasets[0].data.push(data.lanes.N?.density || 0);
        this.chart.data.datasets[1].data.push(data.lanes.S?.density || 0);
        this.chart.data.datasets[2].data.push(data.lanes.E?.density || 0);
        this.chart.data.datasets[3].data.push(data.lanes.W?.density || 0);

        // Keep only last 30 data points
        const maxPoints = 30;
        if (this.chart.data.labels.length > maxPoints) {
            this.chart.data.labels.shift();
            this.chart.data.datasets.forEach(dataset => dataset.data.shift());
        }

        this.chart.update('none');
    }

    /**
     * Load initial data from API
     */
    async loadInitialData() {
        try {
            // Load statistics
            const statsResponse = await fetch('/api/stats');
            const stats = await statsResponse.json();

            // Update metrics (only if elements exist)
            const avgWaitEl = document.getElementById('avg-wait');
            const totalVehiclesEl = document.getElementById('total-vehicles');
            const improvementEl = document.getElementById('improvement');

            if (avgWaitEl) avgWaitEl.textContent = `${Math.round(stats.avg_wait_time)}s`;
            if (totalVehiclesEl) totalVehiclesEl.textContent = stats.total_vehicles.toLocaleString();
            if (improvementEl) improvementEl.textContent = `+${Math.round(stats.improvement_percentage)}%`;

            console.log('Initial data loaded:', stats);
        } catch (error) {
            console.error('Error loading initial data:', error);
        }
    }

    /**
     * Toggle mode between AI and fixed timer
     */
    async toggleMode() {
        try {
            const response = await fetch('/api/mode/toggle', { method: 'POST' });
            const result = await response.json();

            if (result.success) {
                this.updateModeDisplay(result.mode);
            }
        } catch (error) {
            console.error('Error toggling mode:', error);
        }
    }

    /**
     * Open emergency modal
     */
    openEmergencyModal() {
        document.getElementById('emergency-modal').classList.add('active');
    }

    /**
     * Close emergency modal
     */
    closeEmergencyModal() {
        document.getElementById('emergency-modal').classList.remove('active');
    }

    /**
     * Trigger emergency override
     */
    async triggerEmergency(lane) {
        try {
            const response = await fetch('/api/emergency/override', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ lane })
            });

            const result = await response.json();

            if (result.success) {
                console.log(`Emergency activated for lane ${lane}`);
                this.closeEmergencyModal();
            } else {
                alert(result.message);
            }
        } catch (error) {
            console.error('Error triggering emergency:', error);
            alert('Failed to trigger emergency override');
        }
    }
}

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    const dashboard = new TrafficDashboard();
});
