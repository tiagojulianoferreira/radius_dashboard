#!/opt/radius_dashboard/venv/bin/python3
"""
Dashboard RADIUS - IFSC
Análise de autenticações FreeRADIUS
"""
import re, os, json, pwd, grp, gzip, glob
from datetime import datetime
from collections import defaultdict, Counter
import calendar

# ============================================================
# CONFIGURAÇÕES
# ============================================================
LOG_PATH = "/var/log/freeradius/radius.log*"
OUTPUT_DASHBOARD = "/var/www/html/radius/index.html"
OUTPUT_INDEX = "/var/www/html/index.html"
TEMPLATE_DIR = "/opt/radius_dashboard/templates"
CHART_JS_PATH = "/var/www/html/radius/chart.min.js"

# ============================================================
# BANCO DE FABRICANTES (OUI)
# ============================================================
VENDORS_DB = {
    "001C42": "Apple", "001E52": "Apple", "1CD1A1": "Apple",
    "40A108": "Apple", "7CD1C3": "Apple", "A47174": "Apple",
    "CC08E0": "Apple", "F0D1A9": "Apple",
    "0016DB": "Samsung", "185A58": "Samsung", "508569": "Samsung",
    "8455A5": "Samsung", "980D2E": "Samsung", "A0B100": "Samsung",
    "C802A6": "Samsung", "F49F5A": "Samsung",
    "001EA7": "Motorola", "0022AA": "Motorola", "1430C6": "Motorola",
    "404E32": "Motorola", "84D32A": "Motorola", "A470D2": "Motorola",
    "185936": "Xiaomi", "50EC50": "Xiaomi", "6493F2": "Xiaomi",
    "9C2EA1": "Xiaomi", "AC4A69": "Xiaomi", "CC4E24": "Xiaomi",
    "1C5A3B": "Google", "2405F5": "Google", "3C5AB2": "Google",
    "F80F41": "Google",
    "001EC0": "Huawei", "0050F2": "Huawei", "00C08E": "Huawei",
    "00C866": "Oppo", "00E05A": "Oppo", "08006C": "Oppo",
    "025FA4": "Apple", "02BB42": "Android", "067600": "Apple",
    "0ED5C4": "Android", "12CE6D": "Apple", "16A8EC": "Apple",
    "1A0E92": "Apple", "1ED9C0": "Android",
    "0013E8": "Intel", "4C796E": "Intel", "70CD60": "Intel",
    "0004F2": "HP", "001B11": "HP", "00215E": "Dell",
    "001C25": "Dell", "000C29": "VMware", "005056": "VMware",
    "0090A8": "TP-Link", "D052A8": "TP-Link",
    "001FC6": "Asus", "AC9E17": "Asus",
}

# ============================================================
# FUNÇÕES
# ============================================================

def get_vendor(mac):
    if not mac: return "Desconhecido"
    clean_mac = re.sub(r'[^a-fA-F0-9]', '', mac)[:6].upper()
    return VENDORS_DB.get(clean_mac, "Outro Fabricante")

def parse_logs(log_pattern, today_only=False):
    stats = {
        'success': 0, 'fail': 0,
        'vendors_fail': {}, 'vendors_success': {},
        'errors': {},
        'hourly': defaultdict(int),
        'daily': defaultdict(int),
        'historical': defaultdict(int),
        'users_fail': Counter(), 'users_success': Counter(),
        'mac_fail': Counter(), 'mac_success': Counter(),
        'first_log': None, 'last_log': None
    }
    
    ok_re = re.compile(r".*:\s+\((\d+)\)\s+Login OK:.*cli\s+([0-9a-fA-F:-]+)")
    fail_re = re.compile(r".*:\s+\((\d+)\)\s+Login incorrect.*cli\s+([0-9a-fA-F:-]+)")
    date_re = re.compile(r"^(\w{3}\s+\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}\s+\d{4})")
    
    log_files = sorted(glob.glob(log_pattern), reverse=True)
    if not log_files: return stats
    
    today = datetime.now().date()
    error_type = "Senha incorreta"
    
    for log_file in log_files:
        try:
            f = gzip.open(log_file, 'rt', encoding='utf-8', errors='ignore') if log_file.endswith('.gz') else open(log_file, 'r', encoding='utf-8', errors='ignore')
            with f:
                for line in f:
                    line = line.strip()
                    date_match = date_re.match(line)
                    current_date = None
                    if date_match:
                        try:
                            current_date = datetime.strptime(date_match.group(1), '%a %b %d %H:%M:%S %Y')
                            if stats['first_log'] is None or current_date < stats['first_log']:
                                stats['first_log'] = current_date
                            if stats['last_log'] is None or current_date > stats['last_log']:
                                stats['last_log'] = current_date
                        except: pass
                    
                    if today_only and current_date and current_date.date() != today:
                        continue
                    
                    if "ERROR" in line or "TLS Alert" in line:
                        error_type = "Erro TLS" if "TLS" in line else "Erro de Certificado" if "certificate" in line else "Senha incorreta"
                        continue
                    
                    user_match = re.search(r'\[([^\]]+)\]', line)
                    username = user_match.group(1).split('/')[0] if user_match else "Desconhecido"
                    
                    ok_match = ok_re.match(line)
                    if ok_match:
                        stats['success'] += 1
                        stats['users_success'][username] += 1
                        mac = ok_match.group(2)
                        stats['mac_success'][mac] += 1
                        vendor = get_vendor(mac)
                        stats['vendors_success'][vendor] = stats['vendors_success'].get(vendor, 0) + 1
                        error_type = "Senha incorreta"
                        continue
                    
                    fail_match = fail_re.match(line)
                    if fail_match:
                        stats['fail'] += 1
                        mac = fail_match.group(2)
                        vendor = get_vendor(mac)
                        stats['vendors_fail'][vendor] = stats['vendors_fail'].get(vendor, 0) + 1
                        stats['errors'][error_type] = stats['errors'].get(error_type, 0) + 1
                        stats['users_fail'][username] += 1
                        stats['mac_fail'][mac] += 1
                        
                        if current_date:
                            stats['hourly'][f"{current_date.hour:02d}:00"] += 1
                            stats['daily'][calendar.day_name[current_date.weekday()]] += 1
                            stats['historical'][current_date.strftime('%Y-%m-%d')] += 1
                        error_type = "Senha incorreta"
        except Exception as e:
            print(f"   ⚠️  Erro em {log_file}: {e}")
    
    stats['historical'] = sorted(stats['historical'].items())
    
    all_users = set(stats['users_fail'].keys()) | set(stats['users_success'].keys())
    stats['users_error_rate'] = {}
    for user in all_users:
        total = stats['users_fail'][user] + stats['users_success'][user]
        if total > 0:
            stats['users_error_rate'][user] = (stats['users_fail'][user] / total) * 100
    
    stats['top_problematic_users'] = []
    for user, rate in sorted(stats['users_error_rate'].items(), key=lambda x: x[1], reverse=True):
        total = stats['users_fail'][user] + stats['users_success'][user]
        if total >= 5:
            stats['top_problematic_users'].append({'user': user, 'fail': stats['users_fail'][user], 'success': stats['users_success'][user], 'total': total, 'rate': round(rate, 1)})
            if len(stats['top_problematic_users']) >= 10: break
    
    all_macs = set(stats['mac_fail'].keys()) | set(stats['mac_success'].keys())
    stats['mac_error_rate'] = {}
    for mac in all_macs:
        total = stats['mac_fail'][mac] + stats['mac_success'][mac]
        if total > 0:
            stats['mac_error_rate'][mac] = (stats['mac_fail'][mac] / total) * 100
    
    stats['top_problematic_macs'] = []
    for mac, rate in sorted(stats['mac_error_rate'].items(), key=lambda x: x[1], reverse=True):
        total = stats['mac_fail'][mac] + stats['mac_success'][mac]
        if total >= 5:
            stats['top_problematic_macs'].append({'mac': mac, 'vendor': get_vendor(mac), 'fail': stats['mac_fail'][mac], 'success': stats['mac_success'][mac], 'total': total, 'rate': round(rate, 1)})
            if len(stats['top_problematic_macs']) >= 10: break
    
    stats['total_users'] = len(all_users)
    stats['total_macs'] = len(all_macs)
    return stats

def load_template(filename):
    path = os.path.join(TEMPLATE_DIR, filename)
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    return ""

def load_chartjs():
    if os.path.exists(CHART_JS_PATH):
        with open(CHART_JS_PATH, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    return "// Chart.js não encontrado"

def generate_html(stats, stats_today):
    html_template = load_template('index.html') or "<html><body>Template não encontrado</body></html>"
    css_template = load_template('css/style.css') or "/* CSS não encontrado */"
    js_template = load_template('js/dashboard.js') or "// JS não encontrado"
    chart_js = load_chartjs()
    
    total = stats['success'] + stats['fail']
    total_today = stats_today['success'] + stats_today['fail']
    global_rate = (stats['fail'] / total * 100) if total > 0 else 0
    today_rate = (stats_today['fail'] / total_today * 100) if total_today > 0 else 0
    
    adjusted_fail = stats['fail']; adjusted_success = stats['success']
    sorted_users = sorted(stats['users_fail'].items(), key=lambda x: x[1], reverse=True)
    remove_count = max(1, int(len(sorted_users) * 0.05))
    for user, count in sorted_users[:remove_count]:
        adjusted_fail -= count
        adjusted_success -= stats['users_success'].get(user, 0)
    adjusted_total = adjusted_fail + adjusted_success
    adjusted_rate = (adjusted_fail / adjusted_total * 100) if adjusted_total > 0 else 0
    
    period = "Dados disponíveis"
    if stats['first_log'] and stats['last_log']:
        days = (stats['last_log'] - stats['first_log']).days
        period = f"📅 {stats['first_log'].strftime('%d/%m/%Y %H:%M')} até {stats['last_log'].strftime('%d/%m/%Y %H:%M')} ({days} dias)"
    
    data = {
        'PERIOD_TEXT': period, 'TIMESTAMP': datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
        'TODAY_SUCCESS': f"{stats_today['success']:,}", 'TODAY_FAIL': f"{stats_today['fail']:,}",
        'TODAY_RATE': f"{today_rate:.1f}", 'TODAY_TOTAL': f"{total_today:,}",
        'TOTAL_SUCCESS': f"{stats['success']:,}", 'TOTAL_FAIL': f"{stats['fail']:,}",
        'TOTAL_ATTEMPTS': f"{total:,}", 'GLOBAL_RATE': f"{global_rate:.1f}",
        'ADJUSTED_RATE': f"{adjusted_rate:.1f}", 'RATE_IMPACT': f"{global_rate - adjusted_rate:.1f}",
        'TOTAL_USERS': f"{stats['total_users']}", 'TOTAL_MACS': f"{stats['total_macs']}",
        'VENDORS_LABELS': json.dumps(list(stats['vendors_fail'].keys())),
        'VENDORS_DATA': json.dumps(list(stats['vendors_fail'].values())),
        'ERRORS_LABELS': json.dumps(list(stats['errors'].keys())),
        'ERRORS_DATA': json.dumps(list(stats['errors'].values())),
        'HOUR_LABELS': json.dumps(list(stats['hourly'].keys())),
        'HOUR_DATA': json.dumps(list(stats['hourly'].values())),
        'DAY_LABELS': json.dumps(list(stats['daily'].keys())),
        'DAY_DATA': json.dumps(list(stats['daily'].values())),
        'HISTORICAL_DATES': json.dumps([d[0] for d in stats['historical'][-60:]]),
        'HISTORICAL_VALUES': json.dumps([d[1] for d in stats['historical'][-60:]]),
        'PROBLEMATIC_USERS_LABELS': json.dumps([u['user'] for u in stats['top_problematic_users']]),
        'PROBLEMATIC_USERS_DATA': json.dumps([u['rate'] for u in stats['top_problematic_users']]),
        'PROBLEMATIC_USERS_DETAILS': json.dumps(stats['top_problematic_users']),
        'PROBLEMATIC_MACS_LABELS': json.dumps([m['mac'][:8] + '...' for m in stats['top_problematic_macs']]),
        'PROBLEMATIC_MACS_DATA': json.dumps([m['rate'] for m in stats['top_problematic_macs']]),
        'PROBLEMATIC_MACS_DETAILS': json.dumps(stats['top_problematic_macs']),
        'COLORS': json.dumps(['#dc3545', '#ffc107', '#0d6efd', '#6c757d', '#20c997', '#fd7e14', '#6f42c1', '#e83e8c']),
        'CHART_JS': chart_js, 'CSS_STYLES': css_template, 'JS_SCRIPTS': js_template
    }
    
    html = html_template
    for key, value in data.items():
        html = html.replace(f'{{{{ {key} }}}}', value)
    return html

def generate_redirect_html():
    return """<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta http-equiv="refresh" content="0; url=/radius/index.html"><title>Redirecionando...</title>
<style>body{font-family:sans-serif;display:flex;justify-content:center;align-items:center;height:100vh;background:#f0f2f5;margin:0}
.container{text-align:center;padding:40px;background:white;border-radius:10px;box-shadow:0 2px 4px rgba(0,0,0,0.1)}
.spinner{border:4px solid #f3f3f3;border-top:4px solid #1a237e;border-radius:50%;width:40px;height:40px;animation:spin 1s linear infinite;margin:20px auto}
@keyframes spin{0%{transform:rotate(0)}100%{transform:rotate(360deg)}}h2{color:#1a237e}a{color:#1976d2}
</style></head>
<body><div class="container"><h2>📊 Dashboard RADIUS</h2><div class="spinner"></div>
<p>Redirecionando... <a href="/radius/index.html">clique aqui</a></p></div></body></html>"""

def main():
    print("📊 Gerando Dashboard RADIUS...")
    stats = parse_logs(LOG_PATH, today_only=False)
    stats_today = parse_logs(LOG_PATH, today_only=True)
    print(f"✅ Histórico: {stats['success']:,} | ❌ {stats['fail']:,}")
    print(f"✅ Hoje: {stats_today['success']:,} | ❌ {stats_today['fail']:,}")
    print(f"👤 Usuários: {stats['total_users']} | 📱 Equipamentos: {stats['total_macs']}")
    
    html = generate_html(stats, stats_today)
    redirect = generate_redirect_html()
    
    os.makedirs(os.path.dirname(OUTPUT_DASHBOARD), exist_ok=True)
    with open(OUTPUT_DASHBOARD, 'w', encoding='utf-8') as f:
        f.write(html)
    with open(OUTPUT_INDEX, 'w', encoding='utf-8') as f:
        f.write(redirect)
    
    try:
        uid = pwd.getpwnam("www-data").pw_uid
        gid = grp.getgrnam("www-data").gr_gid
        os.chown(OUTPUT_DASHBOARD, uid, gid)
        os.chmod(OUTPUT_DASHBOARD, 0o644)
        os.chown(OUTPUT_INDEX, uid, gid)
        os.chmod(OUTPUT_INDEX, 0o644)
    except: pass
    print("✅ Dashboard gerado com sucesso!")

if __name__ == "__main__":
    main()
