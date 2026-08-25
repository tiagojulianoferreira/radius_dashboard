#!/opt/radius_dashboard/venv/bin/python3
"""
Dashboard RADIUS - IFSC
Com análise avançada por usuário e equipamento
Versão com templates separados
"""
import re
import os
import json
import pwd
import grp
import gzip
import glob
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
    "CC08E0": "Apple", "F0D1A9": "Apple", "0003E9": "Apple",
    "000A27": "Apple", "000D93": "Apple", "001451": "Apple",
    "00187E": "Apple", "001D4F": "Apple", "002346": "Apple",
    "002509": "Apple", "002655": "Apple", "002733": "Apple",
    "002AF3": "Apple", "002E1A": "Apple", "003065": "Apple",
    "003313": "Apple", "003842": "Apple", "003E3D": "Apple",
    "00427E": "Apple", "004796": "Apple", "004B73": "Apple",
    "0050E4": "Apple", "005A83": "Apple", "0060B8": "Apple",
    "0063C5": "Apple", "00675D": "Apple", "006842": "Apple",
    "006B8E": "Apple", "006FF3": "Apple", "00735F": "Apple",
    "007C8E": "Apple", "007FE5": "Apple", "008075": "Apple",
    "008313": "Apple", "008699": "Apple", "008920": "Apple",
    "008C48": "Apple", "00909E": "Apple", "00944E": "Apple",
    "009827": "Apple", "009B3A": "Apple", "009F2D": "Apple",
    "00A302": "Apple", "00A6CA": "Apple", "00AA7F": "Apple",
    "00AE4C": "Apple", "00B21A": "Apple", "00B5D7": "Apple",
    "00B9A0": "Apple", "00BD3D": "Apple", "00C0EE": "Apple",
    "00C4E6": "Apple", "00C8A1": "Apple", "00CC4C": "Apple",
    "00D04B": "Apple", "00D41A": "Apple", "00D7D1": "Apple",
    "00DB70": "Apple", "00DF1A": "Apple", "00E2D6": "Apple",
    "00E68B": "Apple", "00EA23": "Apple", "00EDBE": "Apple",
    "00F165": "Apple", "00F4F2": "Apple", "00F88C": "Apple",
    "00FC27": "Apple", "00FFD5": "Apple",
    "0016DB": "Samsung", "185A58": "Samsung", "508569": "Samsung",
    "8455A5": "Samsung", "980D2E": "Samsung", "A0B100": "Samsung",
    "C802A6": "Samsung", "F49F5A": "Samsung", "000FF8": "Samsung",
    "002D9C": "Samsung", "003A8D": "Samsung", "004D12": "Samsung",
    "006065": "Samsung", "00686F": "Samsung", "006FC4": "Samsung",
    "0073B0": "Samsung", "00789C": "Samsung", "007F10": "Samsung",
    "00824B": "Samsung", "008739": "Samsung", "008A09": "Samsung",
    "008D84": "Samsung", "00911A": "Samsung", "0094F6": "Samsung",
    "00999F": "Samsung", "009D00": "Samsung", "00A01C": "Samsung",
    "00A3A8": "Samsung", "00A7DB": "Samsung", "00ABD3": "Samsung",
    "00AFAE": "Samsung", "00B381": "Samsung", "00B73A": "Samsung",
    "00BB12": "Samsung", "00BED0": "Samsung", "00C2A6": "Samsung",
    "00C662": "Samsung", "00CA3B": "Samsung", "00CDFE": "Samsung",
    "00D1D0": "Samsung", "00D5A5": "Samsung", "00D93C": "Samsung",
    "00DCEB": "Samsung", "00E0A4": "Samsung", "00E40A": "Samsung",
    "00E7B2": "Samsung", "00EB84": "Samsung", "00EF18": "Samsung",
    "00F2C1": "Samsung", "00F65C": "Samsung", "00FA06": "Samsung",
    "00FD9A": "Samsung", "08B2A8": "Samsung", "0C4DEA": "Samsung",
    "10F5E2": "Samsung", "14063C": "Samsung", "18DDE8": "Samsung",
    "1C1410": "Samsung", "20B3CF": "Samsung", "28F91C": "Samsung",
    "2C44FD": "Samsung", "30A070": "Samsung", "34A87F": "Samsung",
    "3868E1": "Samsung", "3C520A": "Samsung", "40D4BB": "Samsung",
    "44F459": "Samsung", "48D6D5": "Samsung", "4C0F6E": "Samsung",
    "50B7C3": "Samsung", "54E6AF": "Samsung", "58C4D5": "Samsung",
    "5CB5D2": "Samsung", "60D6B6": "Samsung", "64AD2C": "Samsung",
    "68A2C8": "Samsung", "6CB012": "Samsung", "70B5E6": "Samsung",
    "7450E3": "Samsung", "78B3D6": "Samsung", "7C2E6A": "Samsung",
    "80C10C": "Samsung", "84A945": "Samsung", "88C255": "Samsung",
    "8C8E54": "Samsung", "90B676": "Samsung", "94D4FC": "Samsung",
    "98F178": "Samsung", "9C8BAC": "Samsung", "A0369B": "Samsung",
    "A43A63": "Samsung", "A83A8D": "Samsung", "AC84C6": "Samsung",
    "B0D2F5": "Samsung", "B47B42": "Samsung", "B85F9D": "Samsung",
    "BC1481": "Samsung", "C03BD7": "Samsung", "C43D40": "Samsung",
    "C850C3": "Samsung", "CC4CF0": "Samsung", "D04B10": "Samsung",
    "D47C19": "Samsung", "D85D4C": "Samsung", "DC4D12": "Samsung",
    "E03D5A": "Samsung", "E43A6D": "Samsung", "E8761C": "Samsung",
    "EC3941": "Samsung", "F03D5E": "Samsung", "F44C76": "Samsung",
    "F89404": "Samsung", "FC125B": "Samsung",
    "001EA7": "Motorola", "0022AA": "Motorola", "1430C6": "Motorola",
    "404E32": "Motorola", "84D32A": "Motorola", "A470D2": "Motorola",
    "D850E6": "Motorola", "EC8A4C": "Motorola", "F8CF15": "Motorola",
    "185936": "Xiaomi", "50EC50": "Xiaomi", "6493F2": "Xiaomi",
    "9C2EA1": "Xiaomi", "AC4A69": "Xiaomi", "CC4E24": "Xiaomi",
    "009D6B": "Xiaomi", "00B4D8": "Xiaomi", "0CF3EE": "Xiaomi",
    "108B60": "Xiaomi", "14ABFD": "Xiaomi", "18B7DC": "Xiaomi",
    "1C8B4B": "Xiaomi", "205CE1": "Xiaomi", "247523": "Xiaomi",
    "2898A1": "Xiaomi", "2C56DC": "Xiaomi", "305ADC": "Xiaomi",
    "3451A7": "Xiaomi", "386D8A": "Xiaomi", "3C27A0": "Xiaomi",
    "40692F": "Xiaomi", "449F2D": "Xiaomi", "48B5D6": "Xiaomi",
    "4C3A3D": "Xiaomi", "50D7D6": "Xiaomi", "54FCD3": "Xiaomi",
    "58C6B1": "Xiaomi", "5C8CF6": "Xiaomi", "60CC8C": "Xiaomi",
    "64809C": "Xiaomi", "68ED43": "Xiaomi", "6C47D5": "Xiaomi",
    "708BB7": "Xiaomi", "74CE56": "Xiaomi", "78FD94": "Xiaomi",
    "7C2BBD": "Xiaomi", "80DFEE": "Xiaomi", "84F336": "Xiaomi",
    "88D4C0": "Xiaomi", "8C30E2": "Xiaomi", "90C172": "Xiaomi",
    "94B125": "Xiaomi", "98BB2E": "Xiaomi", "9C19CD": "Xiaomi",
    "A0214B": "Xiaomi", "A42B8C": "Xiaomi", "A8B948": "Xiaomi",
    "ACFDCE": "Xiaomi", "B0FC36": "Xiaomi", "B4E62D": "Xiaomi",
    "B8C9F3": "Xiaomi", "BC4C94": "Xiaomi", "C04C6E": "Xiaomi",
    "C458C1": "Xiaomi", "C85B51": "Xiaomi", "CC3E4C": "Xiaomi",
    "D0542D": "Xiaomi", "D40E2B": "Xiaomi", "D89347": "Xiaomi",
    "DC61C0": "Xiaomi", "E0D0F9": "Xiaomi", "E447C4": "Xiaomi",
    "E86FDE": "Xiaomi", "EC589C": "Xiaomi", "F0A522": "Xiaomi",
    "F4A7B6": "Xiaomi", "F8ED38": "Xiaomi", "FC527A": "Xiaomi",
    "1C5A3B": "Google", "2405F5": "Google", "3C5AB2": "Google",
    "F80F41": "Google", "00C0B7": "Google", "00E0B7": "Google",
    "0C47C9": "Google", "14D78D": "Google", "18B430": "Google",
    "1C6D6C": "Google", "20C38F": "Google", "24D879": "Google",
    "2C1973": "Google", "30C87E": "Google", "34F668": "Google",
    "3862DD": "Google", "3C88C4": "Google", "40A6D9": "Google",
    "44A842": "Google", "48A2D6": "Google", "4C5D0B": "Google",
    "50C1B4": "Google", "54BEA3": "Google", "58A0B6": "Google",
    "5CF7E6": "Google", "60E4A2": "Google", "64B9E8": "Google",
    "68F728": "Google", "6CDF7A": "Google", "70AFB4": "Google",
    "74EBCF": "Google", "78E3B5": "Google", "7C9EBD": "Google",
    "80A8F2": "Google", "84B531": "Google", "88A1CA": "Google",
    "8C9D88": "Google", "90C9D9": "Google", "94D663": "Google",
    "98D863": "Google", "9C7B98": "Google", "A0C9A4": "Google",
    "A4BAD9": "Google", "A8D2D6": "Google", "ACCF5B": "Google",
    "B0C4E3": "Google", "B4DFC1": "Google", "B8E3B4": "Google",
    "BCE6C7": "Google", "C0E6D8": "Google", "C4E9F2": "Google",
    "C8ECF8": "Google", "CCF0E5": "Google", "D0F4E6": "Google",
    "D4F8E4": "Google", "D8FCE2": "Google", "DCFFE0": "Google",
    "001EC0": "Huawei", "0050F2": "Huawei", "00C08E": "Huawei",
    "00E0F6": "Huawei", "0C96E6": "Huawei", "10D17D": "Huawei",
    "140B8C": "Huawei", "1830B4": "Huawei", "1C6B7C": "Huawei",
    "2044B4": "Huawei", "2448D6": "Huawei", "284C4E": "Huawei",
    "2C504A": "Huawei", "305442": "Huawei", "34583E": "Huawei",
    "385C3A": "Huawei", "3C6036": "Huawei", "406432": "Huawei",
    "44682E": "Huawei", "486C2A": "Huawei", "4C7026": "Huawei",
    "507422": "Huawei", "54781E": "Huawei", "587C1A": "Huawei",
    "5C8016": "Huawei", "608412": "Huawei", "64880E": "Huawei",
    "688C0A": "Huawei", "6C9006": "Huawei", "709402": "Huawei",
    "7498FE": "Huawei", "789CFA": "Huawei", "7CA0F6": "Huawei",
    "80A4F2": "Huawei", "84A8EE": "Huawei", "88ACEA": "Huawei",
    "8CB0E6": "Huawei", "90B4E2": "Huawei", "94B8DE": "Huawei",
    "98BCDA": "Huawei", "9CC0D6": "Huawei", "A0C4D2": "Huawei",
    "A4C8CE": "Huawei", "A8CCCA": "Huawei", "ACD0C6": "Huawei",
    "B0D4C2": "Huawei", "B4D8BE": "Huawei", "B8DCBA": "Huawei",
    "00C866": "Oppo", "00E05A": "Oppo", "08006C": "Oppo",
    "0C1D81": "Oppo", "103A8C": "Oppo", "143E90": "Oppo",
    "184294": "Oppo", "1C4698": "Oppo", "204A9C": "Oppo",
    "244EA0": "Oppo", "2852A4": "Oppo", "2C56A8": "Oppo",
    "305AAC": "Oppo", "345EB0": "Oppo", "3862B4": "Oppo",
    "3C66B8": "Oppo", "406ABC": "Oppo", "446EC0": "Oppo",
    "4872C4": "Oppo", "4C76C8": "Oppo", "507ACC": "Oppo",
    "547ED0": "Oppo", "5882D4": "Oppo", "5C86D8": "Oppo",
    "608ADC": "Oppo", "648EE0": "Oppo", "6892E4": "Oppo",
    "6C96E8": "Oppo", "709AEC": "Oppo", "749EF0": "Oppo",
    "78A2F4": "Oppo", "7CA6F8": "Oppo", "80AAFC": "Oppo",
    "84AEFF": "Oppo", "88B2FF": "Oppo", "8CB6FF": "Oppo",
    "90BAFF": "Oppo", "94BEFF": "Oppo", "98C2FF": "Oppo",
    "9CC6FF": "Oppo", "A0CAFF": "Oppo", "A4CEFF": "Oppo",
    "A8D2FF": "Oppo", "ACD6FF": "Oppo", "B0DAFF": "Oppo",
    "B4DEFF": "Oppo", "B8E2FF": "Oppo", "BCE6FF": "Oppo",
    "025FA4": "Apple", "02BB42": "Android", "067600": "Apple",
    "0ED5C4": "Android", "12CE6D": "Apple", "16A8EC": "Apple",
    "1A0E92": "Apple", "1ED9C0": "Android", "26EE35": "Apple",
    "2A6B27": "Android", "2CAE2B": "Android", "36C618": "Apple",
    "3A4B66": "Android", "466664": "Apple", "485F2D": "Apple",
    "4AFF92": "Android", "5246AC": "Apple", "52CFCD": "Android",
    "608110": "Android", "624D62": "Apple", "629967": "Android",
    "68C44C": "Android", "6AE6C3": "Apple", "6EDAA5": "Android",
    "7268B8": "Android", "768BE1": "Android", "783716": "Android",
    "7A258B": "Apple", "7A7DBB": "Android", "7ED471": "Android",
    "82C07E": "Apple", "866741": "Android", "8A9899": "Apple",
    "8E2D24": "Android", "8E3321": "Android", "967B51": "Apple",
    "9A2C14": "Android", "9ADEA9": "Android", "A2EE16": "Android",
    "AA7B25": "Android", "B67197": "Apple", "BA27C0": "Apple",
    "BED519": "Android", "C06B55": "Apple", "C6C46F": "Android",
    "CA8DCB": "Android", "D0CEC0": "Android", "E0E258": "Android",
    "E28C8F": "Apple", "E6737C": "Android", "EA27D3": "Apple",
    "EACC41": "Android", "EC08E5": "Android", "ECED73": "Apple",
    "EE7A97": "Android", "F63F47": "Apple", "FA1A93": "Android",
    "FA6AB0": "Android", "FEA80F": "Android",
    "0013E8": "Intel", "4C796E": "Intel", "70CD60": "Intel",
    "A0C589": "Intel", "0004F2": "HP", "001B11": "HP",
    "00215E": "Dell", "001C25": "Dell", "000C29": "VMware",
    "005056": "VMware", "0007EC": "Cisco", "001BD3": "Cisco",
    "0090A8": "TP-Link", "D052A8": "TP-Link", "000D88": "D-Link",
    "001151": "D-Link", "0024B2": "Netgear", "0040F4": "Netgear",
    "001FC6": "Asus", "AC9E17": "Asus",
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
            
            if today_only and current_date and current_date.date() != today:
                continue
            
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
            
            user_match = re.search(r'\[([^\]]+)\]', line)
            username = user_match.group(1).split('/')[0] if user_match else "Desconhecido"
            
            ok_match = ok_re.match(line)
            if ok_match:
                sess_id = ok_match.group(1)
                if sess_id not in processed_sessions:
                    stats['success'] += 1
                    processed_sessions.add(sess_id)
                    
                    stats['users_success'][username] += 1
                    mac = ok_match.group(2)
                    stats['mac_success'][mac] += 1
                    vendor = get_vendor(mac)
                    stats['vendors_success'][vendor] = stats['vendors_success'].get(vendor, 0) + 1
                    
                error_type = "Senha incorreta"
                continue
            
            fail_match = fail_re.match(line)
            if fail_match:
                sess_id = fail_match.group(1)
                if sess_id not in processed_sessions:
                    stats['fail'] += 1
                    processed_sessions.add(sess_id)
                    
                    mac = fail_match.group(2)
                    vendor = get_vendor(mac)
                    
                    stats['vendors_fail'][vendor] = stats['vendors_fail'].get(vendor, 0) + 1
                    stats['errors'][error_type] = stats['errors'].get(error_type, 0) + 1
                    stats['users_fail'][username] += 1
                    stats['mac_fail'][mac] += 1
                    
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
    
    stats['total_users_fail'] = len(stats['users_fail'])
    stats['total_macs_fail'] = len(stats['mac_fail'])
    stats['total_users_success'] = len(stats['users_success'])
    stats['total_macs_success'] = len(stats['mac_success'])
    
    stats['users_error_rate'] = {}
    all_users = set(stats['users_fail'].keys()) | set(stats['users_success'].keys())
    for user in all_users:
        total = stats['users_fail'][user] + stats['users_success'][user]
        if total > 0:
            stats['users_error_rate'][user] = (stats['users_fail'][user] / total) * 100
    
    stats['mac_error_rate'] = {}
    all_macs = set(stats['mac_fail'].keys()) | set(stats['mac_success'].keys())
    for mac in all_macs:
        total = stats['mac_fail'][mac] + stats['mac_success'][mac]
        if total > 0:
            stats['mac_error_rate'][mac] = (stats['mac_fail'][mac] / total) * 100
    
    stats['top_problematic_users'] = []
    for user, rate in sorted(stats['users_error_rate'].items(), key=lambda x: x[1], reverse=True):
        total = stats['users_fail'][user] + stats['users_success'][user]
        if total >= 5:
            stats['top_problematic_users'].append({
                'user': user,
                'fail': stats['users_fail'][user],
                'success': stats['users_success'][user],
                'total': total,
                'rate': round(rate, 1)
            })
            if len(stats['top_problematic_users']) >= 10:
                break
    
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

def load_template(filename):
    """Carrega um template do diretório de templates"""
    template_path = os.path.join(TEMPLATE_DIR, filename)
    if os.path.exists(template_path):
        with open(template_path, 'r', encoding='utf-8') as f:
            return f.read()
    return ""

def generate_html(stats, stats_today, chart_js_code):
    """Gera HTML usando templates separados"""
    
    # Carrega os templates
    html_template = load_template('index.html')
    css_template = load_template('css/style.css')
    js_template = load_template('js/dashboard.js')
    
    # Se os templates não existirem, usa os embutidos
    if not html_template:
        html_template = get_default_html()
    if not css_template:
        css_template = get_default_css()
    if not js_template:
        js_template = get_default_js()
    
    # Prepara os dados para substituição
    data = prepare_data(stats, stats_today)
    
    # Substitui placeholders
    html = html_template
    for key, value in data.items():
        html = html.replace(f'{{{{ {key} }}}}', value)
    
    # Insere Chart.js e CSS
    html = html.replace('{{ CHART_JS }}', chart_js_code)
    html = html.replace('{{ CSS_STYLES }}', css_template)
    html = html.replace('{{ JS_SCRIPTS }}', js_template)
    
    return html

def prepare_data(stats, stats_today):
    """Prepara todos os dados para substituição nos templates"""
    
    # Dados básicos
    total_today = stats_today['success'] + stats_today['fail']
    fail_percentage_today = (stats_today['fail'] / total_today * 100) if total_today > 0 else 0
    
    total = stats['success'] + stats['fail']
    global_error_rate = (stats['fail'] / total * 100) if total > 0 else 0
    
    # Calcula taxa ajustada
    adjusted_fail = stats['fail']
    adjusted_success = stats['success']
    sorted_users = sorted(stats['users_fail'].items(), key=lambda x: x[1], reverse=True)
    remove_count = max(1, int(len(sorted_users) * 0.05))
    for user, count in sorted_users[:remove_count]:
        adjusted_fail -= count
        adjusted_success -= stats['users_success'].get(user, 0)
    adjusted_attempts = adjusted_fail + adjusted_success
    adjusted_error_rate = (adjusted_fail / adjusted_attempts * 100) if adjusted_attempts > 0 else 0
    
    # Período
    period_text = "Dados disponíveis"
    if stats['first_log'] and stats['last_log']:
        days = (stats['last_log'] - stats['first_log']).days
        period_text = f"📅 {stats['first_log'].strftime('%d/%m/%Y %H:%M')} até {stats['last_log'].strftime('%d/%m/%Y %H:%M')} ({days} dias)"
    
    # Prepara dados JSON
    data = {
        'PERIOD_TEXT': period_text,
        'TIMESTAMP': datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
        
        # Dados do dia atual
        'TODAY_SUCCESS': f"{stats_today['success']:,}",
        'TODAY_FAIL': f"{stats_today['fail']:,}",
        'TODAY_RATE': f"{fail_percentage_today:.1f}",
        'TODAY_TOTAL': f"{total
