cat > /opt/radius_dashboard/templates/js/dashboard.js << 'JS'
// Gráficos do Dashboard RADIUS

document.addEventListener('DOMContentLoaded', function() {
    // Cores para os gráficos
    const colors = {{ COLORS }};

    // 1. Gráfico de fabricantes
    const ctxVendors = document.getElementById('chartVendors');
    if (ctxVendors) {
        new Chart(ctxVendors, {
            type: 'doughnut',
            data: {
                labels: {{ VENDORS_LABELS }},
                datasets: [{
                    data: {{ VENDORS_DATA }},
                    backgroundColor: colors,
                    borderWidth: 2,
                    borderColor: '#fff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'bottom', labels: { padding: 15, font: { size: 11 } } }
                }
            }
        });
    }

    // 2. Gráfico de erros
    const ctxErrors = document.getElementById('chartErrors');
    if (ctxErrors) {
        new Chart(ctxErrors, {
            type: 'bar',
            data: {
                labels: {{ ERRORS_LABELS }},
                datasets: [{
                    label: 'Quantidade',
                    data: {{ ERRORS_DATA }},
                    backgroundColor: '#1976d2',
                    borderRadius: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: { y: { beginAtZero: true, ticks: { stepSize: 1 } } }
            }
        });
    }

    // 3. Gráfico de falhas por hora
    const ctxHourly = document.getElementById('chartHourly');
    if (ctxHourly) {
        new Chart(ctxHourly, {
            type: 'bar',
            data: {
                labels: {{ HOUR_LABELS }},
                datasets: [{
                    label: 'Falhas',
                    data: {{ HOUR_DATA }},
                    backgroundColor: '#e65100',
                    borderRadius: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: { y: { beginAtZero: true, ticks: { stepSize: 1 } } }
            }
        });
    }

    // 4. Gráfico de falhas por dia da semana
    const ctxDaily = document.getElementById('chartDaily');
    if (ctxDaily) {
        new Chart(ctxDaily, {
            type: 'bar',
            data: {
                labels: {{ DAY_LABELS }},
                datasets: [{
                    label: 'Falhas',
                    data: {{ DAY_DATA }},
                    backgroundColor: '#0d47a1',
                    borderRadius: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: { y: { beginAtZero: true, ticks: { stepSize: 1 } } }
            }
        });
    }

    // 5. Série histórica
    const ctxHistorical = document.getElementById('chartHistorical');
    if (ctxHistorical) {
        new Chart(ctxHistorical, {
            type: 'line',
            data: {
                labels: {{ HISTORICAL_DATES }},
                datasets: [{
                    label: 'Falhas por dia',
                    data: {{ HISTORICAL_VALUES }},
                    borderColor: '#c62828',
                    backgroundColor: 'rgba(198, 40, 40, 0.1)',
                    fill: true,
                    tension: 0.4,
                    pointRadius: 3
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: true },
                    tooltip: { callbacks: { label: function(context) { return context.parsed.y + ' falhas'; } } }
                },
                scales: { y: { beginAtZero: true, ticks: { stepSize: 1 } } }
            }
        });
    }

    // 6. Top usuários problemáticos
    const ctxProblematicUsers = document.getElementById('chartProblematicUsers');
    if (ctxProblematicUsers) {
        const usersData = {{ PROBLEMATIC_USERS_DETAILS }};
        new Chart(ctxProblematicUsers, {
            type: 'bar',
            data: {
                labels: {{ PROBLEMATIC_USERS_LABELS }},
                datasets: [{
                    label: 'Taxa de Erro (%)',
                    data: {{ PROBLEMATIC_USERS_DATA }},
                    backgroundColor: ['#c62828', '#d32f2f', '#e53935', '#ef5350', '#e57373'],
                    borderRadius: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            afterLabel: function(context) {
                                const user = usersData[context.dataIndex];
                                return user ? user.fail + ' falhas / ' + user.total + ' tentativas' : '';
                            }
                        }
                    }
                },
                scales: {
                    y: { beginAtZero: true, max: 100, ticks: { callback: function(value) { return value + '%'; } } }
                }
            }
        });
    }

    // 7. Top equipamentos problemáticos
    const ctxProblematicMacs = document.getElementById('chartProblematicMacs');
    if (ctxProblematicMacs) {
        const macsData = {{ PROBLEMATIC_MACS_DETAILS }};
        new Chart(ctxProblematicMacs, {
            type: 'bar',
            data: {
                labels: {{ PROBLEMATIC_MACS_LABELS }},
                datasets: [{
                    label: 'Taxa de Erro (%)',
                    data: {{ PROBLEMATIC_MACS_DATA }},
                    backgroundColor: ['#0d47a1', '#1565c0', '#1976d2', '#1e88e5', '#42a5f5'],
                    borderRadius: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            afterLabel: function(context) {
                                const mac = macsData[context.dataIndex];
                                return mac ? mac.vendor + ' | ' + mac.fail + ' falhas / ' + mac.total + ' tentativas' : '';
                            }
                        }
                    }
                },
                scales: {
                    y: { beginAtZero: true, max: 100, ticks: { callback: function(value) { return value + '%'; } } }
                }
            }
        });
    }
});

console.log('📊 Dashboard RADIUS carregado com sucesso!');
console.log('📅 Atualizado em: {{ TIMESTAMP }}');
JS
