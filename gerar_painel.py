#!/opt/radius_dashboard/venv/bin/python3
"""
Dashboard RADIUS - IFSC
Com análise avançada por usuário e equipamento
"""
import re
import os
import json
import pwd
import grp
import gzip
import glob
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import calendar

# ============================================================
# CONFIGURAÇÕES
# ============================================================
LOG_PATH = "/var/log/freeradius/radius.log*"
OUTPUT_DASHBOARD = "/var/www/html/radius/index.html"
OUTPUT_INDEX = "/var/www/html/index.html"
CHART_JS_PATH = "/var/www/html/radius/chart.min.js"

# ============================================================
# BANCO DE FABRICANTES (OUI)
# ============================================================
VENDORS_DB = {
    # Mantenha o banco de fabricantes existente aqui
    # ...
}

# ============================================================
# FUNÇÕES
# ============================================================

def get_vendor(mac):
    if not mac:
        return "Desconhecido"
    clean_mac = re.sub(r'[^a-fA-F0-9]', '', mac)[:6].upper()
    return VENDORS_DB.get(clean_mac, "Outro Fabricante")

def parse_log_file(filepath, stats, today_only=False):
    """Analisa logs com estatísticas detalhadas por usuário e equipamento"""
    
    ok_re = re.compile(r".*:\s+\((\d+)\)\s+Login OK:.*cli\s+([0-9a-fA-F:-]+)")
    fail_re = re.compile(r".*:\s+\((\d+)\)\s+Login incorrect.*cli\s+([0-9a-fA-F:-]+)")
    date_re = re.compile(r"^(\w{3}\s+\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}\s+\d{4})")
    
    error_type = "Senha incorreta"
    current_date = None
    processed_sessions = set()
    today = datetime.now().date()
    
    try:
        if filepath.endswith('.gz'):
            f = gzip.open(filepath, 'rt', encoding='utf-8', errors='ignore')
        else:
            f = open(filepath, 'r', encoding='utf-8', errors='ignore')
    except Exception as e:
        print(f"   ⚠️  Erro ao abrir {filepath}: {e}")
        return
    
    with f:
        for line in f:
            line = line.strip()
            
            # Extrai data/hora
            date_match = date_re.match(line)
            if date_match:
                try:
                    current_date = datetime.strptime(date_match.group(1), '%a %b %d %H:%M:%S %Y')
                    if stats['first_log'] is None or current_date < stats['first_log']:
                        stats['first_log'] = current_date
                    if stats['last_log'] is None or current_date > stats['last_log']:
                        stats['last_log'] = current_date
                except:
                    pass
            
            # Filtro por dia atual
            if today_only and current_date and current_date.date() != today:
                continue
            
            # Detecta erros TLS
            if "ERROR" in line or "TLS Alert" in line or "bad certificate" in line:
                if "unknown CA" in line:
                    error_type = "Erro de Certificado CA"
                elif "bad certificate" in line:
                    error_type = "Certificado inválido"
                elif "internal error" in line:
                    error_type = "Erro Interno TLS"
                else:
                    error_type = "Erro TLS"
                continue
            
            # Extrai usuário
            user_match = re.search(r'\[([^\]]+)\]', line)
            username = user_match.group(1).split('/')[0] if user_match else "Desconhecido"
            
            # Verifica sucessos
            ok_match = ok_re.match(line)
            if ok_match:
                sess_id = ok_match.group(1)
                if sess_id not in processed_sessions:
                    stats['success'] += 1
                    processed_sessions.add(sess_id)
                    
                    # Registra sucesso por usuário
                    stats['users_success'][username] += 1
                    
                    # Registra sucesso por MAC
                    mac = ok_match.group(2)
                    stats['mac_success'][mac] += 1
                    
                    # Registra por fabricante (sucessos)
                    vendor = get_vendor(mac)
                    stats['vendors_success'][vendor] = stats['vendors_success'].get(vendor, 0) + 1
                    
                error_type = "Senha incorreta"
                continue
            
            # Verifica falhas
            fail_match = fail_re.match(line)
            if fail_match:
                sess_id = fail_match.group(1)
                if sess_id not in processed_sessions:
                    stats['fail'] += 1
                    processed_sessions.add(sess_id)
                    
                    mac = fail_match.group(2)
                    vendor = get_vendor(mac)
                    
                    # Falhas por fabricante
                    stats['vendors_fail'][vendor] = stats['vendors_fail'].get(vendor, 0) + 1
                    stats['errors'][error_type] = stats['errors'].get(error_type, 0) + 1
                    
                    # Falhas por usuário
                    stats['users_fail'][username] += 1
                    
                    # Falhas por MAC (equipamento)
                    stats['mac_fail'][mac] += 1
                    
                    # Análise temporal
                    if current_date:
                        hour_key = f"{current_date.hour:02d}:00"
                        stats['hourly'][hour_key] += 1
                        day_name = calendar.day_name[current_date.weekday()]
                        stats['daily'][day_name] += 1
                        date_key = current_date.strftime('%Y-%m-%d')
                        stats['historical'][date_key] += 1
                
                error_type = "Senha incorreta"

def parse_all_logs(log_pattern="/var/log/freeradius/radius.log*", today_only=False):
    """Analisa todos os arquivos de log com estatísticas detalhadas"""
    
    stats = {
        'success': 0,
        'fail': 0,
        'vendors_fail': {},
        'vendors_success': {},
        'errors': {},
        'hourly': defaultdict(int),
        'daily': defaultdict(int),
        'historical': defaultdict(int),
        'users_fail': Counter(),
        'users_success': Counter(),
        'mac_fail': Counter(),
        'mac_success': Counter(),
        'first_log': None,
        'last_log': None
    }
    
    log_files = sorted(glob.glob(log_pattern), reverse=True)
    if not log_files:
        print("   ⚠️  Nenhum arquivo de log encontrado!")
        return stats
    
    print(f"   📁 Encontrados {len(log_files)} arquivos de log")
    
    for log_file in log_files:
        try:
            parse_log_file(log_file, stats, today_only)
        except Exception as e:
            print(f"   ⚠️  Erro ao processar {log_file}: {e}")
    
    stats['historical'] = sorted(stats['historical'].items())
    
    # Calcula métricas agregadas
    stats['total_users_fail'] = len(stats['users_fail'])
    stats['total_macs_fail'] = len(stats['mac_fail'])
    stats['total_users_success'] = len(stats['users_success'])
    stats['total_macs_success'] = len(stats['mac_success'])
    
    # Calcula taxa de erro por usuário
    stats['users_error_rate'] = {}
    all_users = set(stats['users_fail'].keys()) | set(stats['users_success'].keys())
    for user in all_users:
        total = stats['users_fail'][user] + stats['users_success'][user]
        if total > 0:
            stats['users_error_rate'][user] = (stats['users_fail'][user] / total) * 100
    
    # Calcula taxa de erro por MAC (equipamento)
    stats['mac_error_rate'] = {}
    all_macs = set(stats['mac_fail'].keys()) | set(stats['mac_success'].keys())
    for mac in all_macs:
        total = stats['mac_fail'][mac] + stats['mac_success'][mac]
        if total > 0:
            stats['mac_error_rate'][mac] = (stats['mac_fail'][mac] / total) * 100
    
    # Top 10 usuários problemáticos (maior taxa de erro, com pelo menos 5 tentativas)
    stats['top_problematic_users'] = []
    for user, rate in sorted(stats['users_error_rate'].items(), key=lambda x: x[1], reverse=True):
        total = stats['users_fail'][user] + stats['users_success'][user]
        if total >= 5:  # Pelo menos 5 tentativas para ser significativo
            stats['top_problematic_users'].append({
                'user': user,
                'fail': stats['users_fail'][user],
                'success': stats['users_success'][user],
                'total': total,
                'rate': round(rate, 1)
            })
            if len(stats['top_problematic_users']) >= 10:
                break
    
    # Top 10 equipamentos problemáticos
    stats['top_problematic_macs'] = []
    for mac, rate in sorted(stats['mac_error_rate'].items(), key=lambda x: x[1], reverse=True):
        total = stats['mac_fail'][mac] + stats['mac_success'][mac]
        if total >= 5:
            vendor = get_vendor(mac)
            stats['top_problematic_macs'].append({
                'mac': mac,
                'vendor': vendor,
                'fail': stats['mac_fail'][mac],
                'success': stats['mac_success'][mac],
                'total': total,
                'rate': round(rate, 1)
            })
            if len(stats['top_problematic_macs']) >= 10:
                break
    
    return stats

def load_chartjs():
    if os.path.exists(CHART_JS_PATH):
        with open(CHART_JS_PATH, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    return "// Chart.js não encontrado"

def generate_html(stats, stats_today, chart_js_code):
    """Gera HTML com métricas avançadas"""
    
    # Dados para gráficos existentes
    vendors_fail_labels = json.dumps(list(stats['vendors_fail'].keys()))
    vendors_fail_data = json.dumps(list(stats['vendors_fail'].values()))
    errors_labels = json.dumps(list(stats['errors'].keys()))
    errors_data = json.dumps(list(stats['errors'].values()))
    
    hour_labels = json.dumps(list(stats['hourly'].keys()))
    hour_data = json.dumps(list(stats['hourly'].values()))
    
    day_labels = json.dumps(list(stats['daily'].keys()))
    day_data = json.dumps(list(stats['daily'].values()))
    
    historical_dates = json.dumps([d[0] for d in stats['historical'][-60:]])
    historical_values = json.dumps([d[1] for d in stats['historical'][-60:]])
    
    # NOVOS GRÁFICOS: Top usuários e equipamentos problemáticos
    problematic_users_labels = json.dumps([u['user'] for u in stats['top_problematic_users']])
    problematic_users_data = json.dumps([u['rate'] for u in stats['top_problematic_users']])
    
    problematic_macs_labels = json.dumps([m['mac'][:8] + '...' for m in stats['top_problematic_macs']])
    problematic_macs_vendors = json.dumps([m['vendor'] for m in stats['top_problematic_macs']])
    problematic_macs_data = json.dumps([m['rate'] for m in stats['top_problematic_macs']])
    
    # Cálculo da taxa global de erro (excluindo outliers)
    # Remove top 5% dos usuários com maior taxa de erro
    total_fail = stats['fail']
    total_success = stats['success']
    total_attempts = total_fail + total_success
    global_error_rate = (total_fail / total_attempts * 100) if total_attempts > 0 else 0
    
    # Taxa de erro ajustada (excluindo top 5% dos usuários problemáticos)
    adjusted_fail = total_fail
    adjusted_success = total_success
    
    # Remove top 5% dos usuários com mais falhas
    sorted_users = sorted(stats['users_fail'].items(), key=lambda x: x[1], reverse=True)
    remove_count = max(1, int(len(sorted_users) * 0.05))
    for user, count in sorted_users[:remove_count]:
        adjusted_fail -= count
        adjusted_success -= stats['users_success'].get(user, 0)
    
    adjusted_attempts = adjusted_fail + adjusted_success
    adjusted_error_rate = (adjusted_fail / adjusted_attempts * 100) if adjusted_attempts > 0 else 0
    
    # Novos gráficos: Evolução de erros por dia (destacando outliers)
    # Vamos calcular média e desvio padrão para identificar dias atípicos
    historical_values_list = [v for _, v in stats['historical']]
    avg_fail = sum(historical_values_list) / len(historical_values_list) if historical_values_list else 0
    std_fail = (sum((x - avg_fail) ** 2 for x in historical_values_list) / len(historical_values_list)) ** 0.5 if historical_values_list else 0
    
    period_text = "Dados disponíveis"
    if stats['first_log'] and stats['last_log']:
        days = (stats['last_log'] - stats['first_log']).days
        period_text = f"📅 {stats['first_log'].strftime('%d/%m/%Y %H:%M')} até {stats['last_log'].strftime('%d/%m/%Y %H:%M')} ({days} dias)"
    
    colors = json.dumps([
        '#dc3545', '#ffc107', '#0d6efd', '#6c757d', 
        '#20c997', '#fd7e14', '#6f42c1', '#e83e8c',
        '#198754', '#fd7e14', '#0dcaf0', '#d63384'
    ])
    
    # Retorna HTML com novos gráficos
    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard RADIUS - IFSC</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f0f2f5;
            color: #333;
            padding: 20px;
        }}
        .container {{ max-width: 1400px; margin: 0 auto; }}
        .header {{
            background: white;
            padding: 20px 30px;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 25px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 10px;
        }}
        .header h1 {{ font-size: 24px; font-weight: 600; color: #1a237e; }}
        .header h1 span {{ color: #c62828; }}
        .header .timestamp {{ color: #666; font-size: 14px; }}
        .header .period {{ color: #666; font-size: 13px; background: #e8eaf6; padding: 5px 15px; border-radius: 20px; }}
        
        .grid {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 20px; margin-bottom: 25px; }}
        .grid-2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 25px; }}
        .grid-full {{ display: grid; grid-template-columns: 1fr; gap: 20px; margin-bottom: 25px; }}
        
        .card {{
            background: white;
            border-radius: 10px;
            padding: 25px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .card h3 {{ font-size: 14px; font-weight: 500; color: #666; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 10px; }}
        .card .value {{ font-size: 48px; font-weight: 700; }}
        .card .label {{ font-size: 14px; color: #666; margin-top: 5px; }}
        .card-success .value {{ color: #2e7d32; }}
        .card-danger .value {{ color: #c62828; }}
        .card-warning .value {{ color: #e65100; }}
        .card-info .value {{ color: #0d47a1; }}
        .card-chart {{ padding: 20px; }}
        .card-chart h3 {{ margin-bottom: 15px; }}
        .chart-container {{ position: relative; height: 280px; }}
        .chart-container-tall {{ position: relative; height: 350px; }}
        
        .today-stats {{
            background: linear-gradient(135deg, #1a237e 0%, #0d47a1 100%);
            color: white;
            padding: 15px 25px;
            border-radius: 10px;
            margin-bottom: 25px;
            display: flex;
            justify-content: space-around;
            align-items: center;
            flex-wrap: wrap;
            gap: 15px;
        }}
        .today-stats .stat-item {{ text-align: center; }}
        .today-stats .stat-item .number {{ font-size: 32px; font-weight: 700; }}
        .today-stats .stat-item .label {{ font-size: 12px; opacity: 0.8; text-transform: uppercase; letter-spacing: 0.5px; }}
        .today-stats .stat-item .number.success {{ color: #4caf50; }}
        .today-stats .stat-item .number.danger {{ color: #f44336; }}
        .today-stats .stat-item .number.warning {{ color: #ff9800; }}
        
        .rate-card {{
            background: white;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 25px;
        }}
        .rate-card .rate-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr 1fr;
            gap: 20px;
            text-align: center;
        }}
        .rate-card .rate-item {{
            padding: 15px;
            border-radius: 8px;
        }}
        .rate-card .rate-item .number {{
            font-size: 32px;
            font-weight: 700;
        }}
        .rate-card .rate-item .label {{
            font-size: 12px;
            color: #666;
            margin-top: 5px;
        }}
        .rate-item.global {{
            background: #e3f2fd;
        }}
        .rate-item.adjusted {{
            background: #e8f5e9;
        }}
        .rate-item.impact {{
            background: #fff3e0;
        }}
        
        .footer {{ text-align: center; margin-top: 25px; color: #666; font-size: 13px; }}
        
        @media (max-width: 768px) {{
            .grid {{ grid-template-columns: 1fr; }}
            .grid-2 {{ grid-template-columns: 1fr; }}
            .header {{ flex-direction: column; text-align: center; }}
            .today-stats {{ flex-direction: column; }}
            .rate-card .rate-grid {{ grid-template-columns: 1fr; }}
        }}
    </style>
    <script>
    {chart_js_code}
    </script>
</head>
<body>
    <div class="container">
        <div class="header">
            <div>
                <h1>📊 Dashboard <span>RADIUS</span></h1>
                <div class="period">{period_text}</div>
            </div>
            <div class="timestamp">Atualizado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</div>
        </div>
        
        <!-- Dados do dia atual -->
        <div class="today-stats">
            <div class="stat-item">
                <div class="number success">{stats_today['success']:,}</div>
                <div class="label">✅ Hoje - Sucessos</div>
            </div>
            <div class="stat-item">
                <div class="number danger">{stats_today['fail']:,}</div>
                <div class="label">❌ Hoje - Falhas</div>
            </div>
            <div class="stat-item">
                <div class="number warning">{stats_today['fail']/(stats_today['success']+stats_today['fail'])*100:.1f if (stats_today['success']+stats_today['fail'])>0 else 0}%</div>
                <div class="label">⚠️ Hoje - Taxa de falhas</div>
            </div>
            <div class="stat-item">
                <div class="number">{stats_today['success']+stats_today['fail']:,}</div>
                <div class="label">📊 Hoje - Total de tentativas</div>
            </div>
        </div>
        
        <!-- Cards de estatísticas históricas -->
        <div class="grid">
            <div class="card card-success">
                <h3>✅ Autenticações bem-sucedidas</h3>
                <div class="value">{stats['success']:,}</div>
                <div class="label">Logins OK (histórico)</div>
            </div>
            <div class="card card-danger">
                <h3>❌ Autenticações rejeitadas</h3>
                <div class="value">{stats['fail']:,}</div>
                <div class="label">Logins incorretos (histórico)</div>
            </div>
            <div class="card card-info">
                <h3>👤 Usuários únicos</h3>
                <div class="value">{stats['total_users_fail'] + stats['total_users_success']}</div>
                <div class="label">Usuários com atividade</div>
            </div>
        </div>
        
        <!-- NOVO: Taxa de Erro - Global vs Ajustada -->
        <div class="rate-card">
            <h3 style="margin-bottom: 15px; color: #1a237e;">📊 Análise de Taxa de Erro</h3>
            <div class="rate-grid">
                <div class="rate-item global">
                    <div class="number" style="color: #c62828;">{global_error_rate:.1f}%</div>
                    <div class="label">Taxa Global de Erro</div>
                    <div style="font-size: 11px; color: #666; margin-top: 5px;">{total_fail:,} falhas / {total_attempts:,} tentativas</div>
                </div>
                <div class="rate-item adjusted">
                    <div class="number" style="color: #2e7d32;">{adjusted_error_rate:.1f}%</div>
                    <div class="label">✅ Taxa Ajustada (sem outliers)</div>
                    <div style="font-size: 11px; color: #666; margin-top: 5px;">Excluídos top 5% usuários com mais falhas</div>
                </div>
                <div class="rate-item impact">
                    <div class="number" style="color: #e65100;">{global_error_rate - adjusted_error_rate:.1f}%</div>
                    <div class="label">Impacto dos Outliers</div>
                    <div style="font-size: 11px; color: #666; margin-top: 5px;">Redução na taxa ao remover usuários problemáticos</div>
                </div>
            </div>
        </div>
        
        <!-- NOVOS GRÁFICOS: Usuários e Equipamentos Problemáticos -->
        <div class="grid-2">
            <div class="card card-chart">
                <h3>👤 Top Usuários Problemáticos (Taxa de Erro)</h3>
                <div class="chart-container">
                    <canvas id="chartProblematicUsers"></canvas>
                </div>
                <div style="font-size: 11px; color: #666; margin-top: 10px; text-align: center;">
                    Apenas usuários com ≥ 5 tentativas
                </div>
            </div>
            <div class="card card-chart">
                <h3>📱 Top Equipamentos Problemáticos (Taxa de Erro)</h3>
                <div class="chart-container">
                    <canvas id="chartProblematicMacs"></canvas>
                </div>
                <div style="font-size: 11px; color: #666; margin-top: 10px; text-align: center;">
                    Apenas equipamentos com ≥ 5 tentativas | MACs anonimizados
                </div>
            </div>
        </div>
        
        <!-- Gráficos existentes mantidos -->
        <div class="grid-2">
            <div class="card card-chart">
                <h3>📱 Falhas por Fabricante</h3>
                <div class="chart-container">
                    <canvas id="chartVendors"></canvas>
                </div>
            </div>
            <div class="card card-chart">
                <h3>🔒 Falhas por Tipo de Erro</h3>
                <div class="chart-container">
                    <canvas id="chartErrors"></canvas>
                </div>
            </div>
        </div>
        
        <div class="grid-2">
            <div class="card card-chart">
                <h3>🕐 Falhas por Hora do Dia</h3>
                <div class="chart-container">
                    <canvas id="chartHourly"></canvas>
                </div>
            </div>
            <div class="card card-chart">
                <h3>📅 Falhas por Dia da Semana</h3>
                <div class="chart-container">
                    <canvas id="chartDaily"></canvas>
                </div>
            </div>
        </div>
        
        <div class="grid-full">
            <div class="card card-chart">
                <h3>📈 Evolução Diária de Falhas (Últimos 60 dias)</h3>
                <div class="chart-container-tall">
                    <canvas id="chartHistorical"></canvas>
                </div>
            </div>
        </div>
        
        <div class="footer">
            <p>FreeRADIUS Dashboard - Gerado automaticamente via análise de logs históricos</p>
            <p style="font-size: 11px; color: #999; margin-top: 5px;">
                Taxa ajustada exclui top 5% usuários com maior taxa de falha para métrica mais representativa
            </p>
        </div>
    </div>
    
    <script>
        // GRÁFICOS EXISTENTES (mantidos)
        const ctxVendors = document.getElementById('chartVendors').getContext('2d');
        new Chart(ctxVendors, {{
            type: 'doughnut',
            data: {{
                labels: {vendors_fail_labels},
                datasets: [{{
                    data: {vendors_fail_data},
                    backgroundColor: {colors},
                    borderWidth: 2,
                    borderColor: '#fff'
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{ position: 'bottom', labels: {{ padding: 15, font: {{ size: 11 }} }} }}
                }}
            }}
        }});
        
        const ctxErrors = document.getElementById('chartErrors').getContext('2d');
        new Chart(ctxErrors, {{
            type: 'bar',
            data: {{
                labels: {errors_labels},
                datasets: [{{
                    label: 'Quantidade',
                    data: {errors_data},
                    backgroundColor: '#1976d2',
                    borderRadius: 4
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{ legend: {{ display: false }} }},
                scales: {{ y: {{ beginAtZero: true, ticks: {{ stepSize: 1 }} }} }}
            }}
        }});
        
        const ctxHourly = document.getElementById('chartHourly').getContext('2d');
        new Chart(ctxHourly, {{
            type: 'bar',
            data: {{
                labels: {hour_labels},
                datasets: [{{
                    label: 'Falhas',
                    data: {hour_data},
                    backgroundColor: '#e65100',
                    borderRadius: 4
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{ legend: {{ display: false }} }},
                scales: {{ y: {{ beginAtZero: true, ticks: {{ stepSize: 1 }} }} }}
            }}
        }});
        
        const ctxDaily = document.getElementById('chartDaily').getContext('2d');
        new Chart(ctxDaily, {{
            type: 'bar',
            data: {{
                labels: {day_labels},
                datasets: [{{
                    label: 'Falhas',
                    data: {day_data},
                    backgroundColor: '#0d47a1',
                    borderRadius: 4
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{ legend: {{ display: false }} }},
                scales: {{ y: {{ beginAtZero: true, ticks: {{ stepSize: 1 }} }} }}
            }}
        }});
        
        const ctxHistorical = document.getElementById('chartHistorical').getContext('2d');
        new Chart(ctxHistorical, {{
            type: 'line',
            data: {{
                labels: {historical_dates},
                datasets: [{{
                    label: 'Falhas por dia',
                    data: {historical_values},
                    borderColor: '#c62828',
                    backgroundColor: 'rgba(198, 40, 40, 0.1)',
                    fill: true,
                    tension: 0.4,
                    pointRadius: 3
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{ display: true }},
                    tooltip: {{ callbacks: {{ label: function(context) {{ return context.parsed.y + ' falhas'; }} }} }}
                }},
                scales: {{
                    y: {{ beginAtZero: true, ticks: {{ stepSize: 1 }} }}
                }}
            }}
        }});
        
        // NOVOS GRÁFICOS: Usuários problemáticos
        const ctxProblematicUsers = document.getElementById('chartProblematicUsers').getContext('2d');
        new Chart(ctxProblematicUsers, {{
            type: 'bar',
            data: {{
                labels: {problematic_users_labels},
                datasets: [{{
                    label: 'Taxa de Erro (%)',
                    data: {problematic_users_data},
                    backgroundColor: ['#c62828', '#d32f2f', '#e53935', '#ef5350', '#e57373',
                                     '#c62828', '#d32f2f', '#e53935', '#ef5350', '#e57373'],
                    borderRadius: 4
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{ display: false }},
                    tooltip: {{
                        callbacks: {{
                            afterLabel: function(context) {{
                                const index = context.dataIndex;
                                const users = {json.dumps(stats['top_problematic_users'])};
                                const user = users[index];
                                return user ? user.fail + ' falhas / ' + user.total + ' tentativas' : '';
                            }}
                        }}
                    }}
                }},
                scales: {{
                    y: {{
                        beginAtZero: true,
                        max: 100,
                        ticks: {{ callback: function(value) {{ return value + '%'; }} }}
                    }}
                }}
            }}
        }});
        
        // NOVOS GRÁFICOS: Equipamentos problemáticos
        const ctxProblematicMacs = document.getElementById('chartProblematicMacs').getContext('2d');
        new Chart(ctxProblematicMacs, {{
            type: 'bar',
            data: {{
                labels: {problematic_macs_labels},
                datasets: [{{
                    label: 'Taxa de Erro (%)',
                    data: {problematic_macs_data},
                    backgroundColor: ['#0d47a1', '#1565c0', '#1976d2', '#1e88e5', '#42a5f5',
                                     '#0d47a1', '#1565c0', '#1976d2', '#1e88e5', '#42a5f5'],
                    borderRadius: 4
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{ display: false }},
                    tooltip: {{
                        callbacks: {{
                            afterLabel: function(context) {{
                                const index = context.dataIndex;
                                const macs = {json.dumps(stats['top_problematic_macs'])};
                                const mac = macs[index];
                                return mac ? mac.vendor + ' | ' + mac.fail + ' falhas / ' + mac.total + ' tentativas' : '';
                            }}
                        }}
                    }}
                }},
                scales: {{
                    y: {{
                        beginAtZero: true,
                        max: 100,
                        ticks: {{ callback: function(value) {{ return value + '%'; }} }}
                    }}
                }}
            }}
        }});
    </script>
</body>
</html>"""

def main():
    print("📊 Gerando Dashboard RADIUS com análise avançada...")
    print("📁 Lendo todos os logs...")
    
    stats = parse_all_logs(LOG_PATH, today_only=False)
    stats_today = parse_all_logs(LOG_PATH, today_only=True)
    
    print(f"\n📊 Histórico: ✅ {stats['success']:,} | ❌ {stats['fail']:,}")
    print(f"📊 Hoje: ✅ {stats_today['success']:,} | ❌ {stats_today['fail']:,}")
    print(f"👤 Usuários ativos: {stats['total_users_success'] + stats['total_users_fail']}")
    print(f"📱 Equipamentos ativos: {stats['total_macs_success'] + stats['total_macs_fail']}")
    print(f"🔝 Usuários problemáticos: {len(stats['top_problematic_users'])}")
    
    chart_js = load_chartjs()
    dashboard_html = generate_html(stats, stats_today, chart_js)
    redirect_html = generate_redirect_html()
    
    os.makedirs(os.path.dirname(OUTPUT_DASHBOARD), exist_ok=True)
    
    with open(OUTPUT_DASHBOARD, 'w', encoding='utf-8') as f:
        f.write(dashboard_html)
    
    with open(OUTPUT_INDEX, 'w', encoding='utf-8') as f:
        f.write(redirect_html)
    
    try:
        uid = pwd.getpwnam("www-data").pw_uid
        gid = grp.getgrnam("www-data").gr_gid
        os.chown(OUTPUT_DASHBOARD, uid, gid)
        os.chmod(OUTPUT_DASHBOARD, 0o644)
        os.chown(OUTPUT_INDEX, uid, gid)
        os.chmod(OUTPUT_INDEX, 0o644)
    except Exception as e:
        print(f"⚠️  Erro ao ajustar permissões: {e}")
    
    print("\n✅ Dashboard gerado com sucesso!")

if __name__ == "__main__":
    main()
