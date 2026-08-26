#!/opt/radius_dashboard/venv/bin/python3
"""
Dashboard RADIUS - IFSC
Com análise histórica, desduplicação e lista de usuários com MAC e erros
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
# CONFIGURAÇÕES DE DESDUPLICAÇÃO
# ============================================================
DEDUP_WINDOW_MINUTES = 5
MAX_CONSECUTIVE_ERRORS = 3

# ============================================================
# BANCO DE FABRICANTES (OUI) - MANTIDO IGUAL
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
    "00A0B0": "Vivo", "00C8A0": "Vivo", "08D8B0": "Vivo",
    "0C94A0": "Vivo", "1098A0": "Vivo", "149CA0": "Vivo",
    "18A0A0": "Vivo", "1CA4A0": "Vivo", "20A8A0": "Vivo",
    "24ACA0": "Vivo", "28B0A0": "Vivo", "2CB4A0": "Vivo",
    "30B8A0": "Vivo", "34BCA0": "Vivo", "38C0A0": "Vivo",
    "3CC4A0": "Vivo", "40C8A0": "Vivo", "44CCA0": "Vivo",
    "48D0A0": "Vivo", "4CD4A0": "Vivo", "50D8A0": "Vivo",
    "54DCA0": "Vivo", "58E0A0": "Vivo", "5CE4A0": "Vivo",
    "60E8A0": "Vivo", "64ECA0": "Vivo", "68F0A0": "Vivo",
    "6CF4A0": "Vivo", "70F8A0": "Vivo", "74FCA0": "Vivo",
    "00E0C8": "Realme", "0C8C24": "Realme", "1099A8": "Realme",
    "14658C": "Realme", "186C8C": "Realme", "1C6C8C": "Realme",
    "206C8C": "Realme", "246C8C": "Realme", "286C8C": "Realme",
    "2C6C8C": "Realme", "306C8C": "Realme", "346C8C": "Realme",
    "386C8C": "Realme", "3C6C8C": "Realme", "406C8C": "Realme",
    "446C8C": "Realme", "486C8C": "Realme", "4C6C8C": "Realme",
    "506C8C": "Realme", "546C8C": "Realme", "586C8C": "Realme",
    "5C6C8C": "Realme", "606C8C": "Realme", "646C8C": "Realme",
    "686C8C": "Realme", "6C6C8C": "Realme", "706C8C": "Realme",
    "746C8C": "Realme", "786C8C": "Realme", "7C6C8C": "Realme",
    "0014B1": "OnePlus", "001A5A": "OnePlus", "00256B": "OnePlus",
    "002A7D": "OnePlus", "002E7D": "OnePlus", "00327D": "OnePlus",
    "00367D": "OnePlus", "003A7D": "OnePlus", "003E7D": "OnePlus",
    "00427D": "OnePlus", "00467D": "OnePlus", "004A7D": "OnePlus",
    "0012F3": "Sony", "001DBA": "Sony", "0021F5": "Sony",
    "002647": "Sony", "002AAA": "Sony", "002D9C": "Sony",
    "0030D6": "Sony", "00342E": "Sony", "003765": "Sony",
    "003A98": "Sony", "003DB7": "Sony", "00409B": "Sony",
    "0043A3": "Sony", "0046F5": "Sony", "004A1A": "Sony",
    "0013D8": "Nokia", "001859": "Nokia", "001CBA": "Nokia",
    "002061": "Nokia", "0023EB": "Nokia", "00271A": "Nokia",
    "002A5C": "Nokia", "002DA9": "Nokia", "0030F4": "Nokia",
    "003452": "Nokia", "00379A": "Nokia", "003AE6": "Nokia",
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

def format_mac(mac):
    """Formata MAC address no formato XX:XX:XX:XX:XX:XX"""
    if not mac:
        return "N/A"
    clean = re.sub(r'[^a-fA-F0-9]', '', mac).upper()
    if len(clean) >= 12:
        return ':'.join(clean[i:i+2] for i in range(0, 12, 2))
    return mac

def extract_mac_from_line(line):
    """Extrai MAC address de uma linha de log"""
    patterns = [
        r'cli\s+([0-9a-fA-F]{2}[-:]?[0-9a-fA-F]{2}[-:]?[0-9a-fA-F]{2}[-:]?[0-9a-fA-F]{2}[-:]?[0-9a-fA-F]{2}[-:]?[0-9a-fA-F]{2})',
        r'Calling-Station-Id\s*=\s*["\']([0-9a-fA-F\-:]+)["\']',
        r'([0-9a-fA-F]{2}[-:]?[0-9a-fA-F]{2}[-:]?[0-9a-fA-F]{2}[-:]?[0-9a-fA-F]{2}[-:]?[0-9a-fA-F]{2}[-:]?[0-9a-fA-F]{2})'
    ]
    for pattern in patterns:
        match = re.search(pattern, line, re.IGNORECASE)
        if match:
            mac = match.group(1)
            return re.sub(r'[:\s-]', '', mac).upper()
    return None

def detect_error_type(line):
    """Detecta o tipo de erro em uma linha de log"""
    if "unknown CA" in line:
        return "Erro de Certificado CA"
    elif "bad certificate" in line:
        return "Certificado inválido"
    elif "internal error" in line:
        return "Erro Interno TLS"
    elif "TLS" in line:
        return "Erro TLS"
    elif "mschap" in line:
        return "Erro MS-CHAP"
    elif "Invalid user" in line:
        return "Usuário inválido"
    elif "protocol version" in line:
        return "Erro TLS (versão)"
    else:
        return "Senha incorreta"

class EventDeduplicator:
    def __init__(self, window_minutes=DEDUP_WINDOW_MINUTES):
        self.window_minutes = window_minutes
        self.last_event_by_user = {}
        self.user_error_count = Counter()
        
    def is_duplicate(self, username, timestamp, session_id):
        if not timestamp or not username or username == "Desconhecido":
            return False
        
        last_time = self.last_event_by_user.get(username)
        if last_time:
            diff = (timestamp - last_time).total_seconds() / 60
            if diff < self.window_minutes:
                self.user_error_count[username] += 1
                if self.user_error_count[username] > MAX_CONSECUTIVE_ERRORS:
                    return True
            else:
                self.user_error_count[username] = 0
        
        self.last_event_by_user[username] = timestamp
        return False

def parse_log_file(filepath, stats, today_only=False, dedup=True):
    print(f"   📄 Processando: {os.path.basename(filepath)}")
    
    ok_re = re.compile(r".*:\s+\((\d+)\)\s+Login OK:.*cli\s+([0-9a-fA-F:-]+)")
    fail_re = re.compile(r".*:\s+\((\d+)\)\s+Login incorrect.*cli\s+([0-9a-fA-F:-]+)")
    date_re = re.compile(r"^(\w{3}\s+\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}\s+\d{4})")
    
    current_date = None
    processed_sessions = set()
    today = datetime.now().date()
    
    deduplicator = EventDeduplicator() if dedup else None
    users_today_data = {}  # username -> {mac, errors: set()}
    
    if filepath.endswith('.gz'):
        f = gzip.open(filepath, 'rt', encoding='utf-8', errors='ignore')
    else:
        f = open(filepath, 'r', encoding='utf-8', errors='ignore')
    
    with f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            
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
            
            ok_match = ok_re.match(line)
            if ok_match:
                sess_id = ok_match.group(1)
                if sess_id not in processed_sessions:
                    stats['success'] += 1
                    processed_sessions.add(sess_id)
                continue
            
            fail_match = fail_re.match(line)
            if fail_match:
                sess_id = fail_match.group(1)
                if sess_id not in processed_sessions:
                    user_match = re.search(r'\[([^\]]+)\]', line)
                    username = user_match.group(1).split('/')[0] if user_match else "Desconhecido"
                    
                    # Extrai MAC
                    mac = extract_mac_from_line(line)
                    if not mac:
                        mac = "N/A"
                    
                    # Detecta tipo de erro
                    error_type = detect_error_type(line)
                    
                    is_duplicate = False
                    if dedup and deduplicator and current_date:
                        is_duplicate = deduplicator.is_duplicate(username, current_date, sess_id)
                    
                    if not is_duplicate:
                        stats['fail'] += 1
                        stats['fail_dedup'] += 1
                        stats['users_fail'][username] += 1
                        
                        if current_date and current_date.date() == today:
                            if username not in users_today_data:
                                users_today_data[username] = {'mac': mac, 'errors': set()}
                            users_today_data[username]['errors'].add(error_type)
                        
                        mac_fail = fail_match.group(2)
                        vendor = get_vendor(mac_fail)
                        
                        stats['vendors'][vendor] = stats['vendors'].get(vendor, 0) + 1
                        stats['errors'][error_type] = stats['errors'].get(error_type, 0) + 1
                        
                        if current_date:
                            hour_key = f"{current_date.hour:02d}:00"
                            stats['hourly'][hour_key] += 1
                            day_name = calendar.day_name[current_date.weekday()]
                            stats['daily'][day_name] += 1
                            date_key = current_date.strftime('%Y-%m-%d')
                            stats['historical'][date_key] += 1
                    else:
                        stats['fail'] += 1
                    
                    processed_sessions.add(sess_id)
    
    return users_today_data

def parse_all_logs(log_pattern="/var/log/freeradius/radius.log*", today_only=False, dedup=True):
    stats = {
        'success': 0,
        'fail': 0,
        'fail_dedup': 0,
        'vendors': {},
        'errors': {},
        'hourly': defaultdict(int),
        'daily': defaultdict(int),
        'historical': defaultdict(int),
        'users_fail': Counter(),
        'users_today_data': {},  # username -> {mac, errors}
        'first_log': None,
        'last_log': None,
        'unique_users_affected': 0,
        'unique_users_affected_today': 0,
        'impact_percentage': 0,
        'impact_percentage_today': 0,
        'total_users': 0,
        'total_users_today': 0
    }
    
    log_files = sorted(glob.glob(log_pattern), reverse=True)
    
    if not log_files:
        print("   ⚠️  Nenhum arquivo de log encontrado!")
        return stats
    
    print(f"   📁 Encontrados {len(log_files)} arquivos de log")
    
    users_today_data = {}
    
    for log_file in log_files:
        try:
            users_data = parse_log_file(log_file, stats, today_only, dedup)
            # Atualiza dados de usuários do dia
            for username, data in users_data.items():
                if username not in users_today_data:
                    users_today_data[username] = {'mac': data['mac'], 'errors': set()}
                users_today_data[username]['errors'].update(data['errors'])
        except Exception as e:
            print(f"   ⚠️  Erro ao processar {log_file}: {e}")
    
    stats['historical'] = sorted(stats['historical'].items())
    stats['users_today_data'] = users_today_data
    
    total_unique_users = len(stats['users_fail']) + 1
    stats['unique_users_affected'] = len(stats['users_fail'])
    stats['impact_percentage'] = (stats['unique_users_affected'] / total_unique_users * 100) if total_unique_users > 0 else 0
    stats['total_users'] = total_unique_users
    
    stats['unique_users_affected_today'] = len(users_today_data)
    stats['total_users_today'] = stats['unique_users_affected_today'] + 1
    stats['impact_percentage_today'] = (stats['unique_users_affected_today'] / stats['total_users_today'] * 100) if stats['total_users_today'] > 0 else 0
    
    return stats

def load_chartjs():
    if os.path.exists(CHART_JS_PATH):
        with open(CHART_JS_PATH, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    return "// Chart.js não encontrado"

def generate_html(stats, stats_today, chart_js_code):
    total_today = stats_today['success'] + stats_today['fail']
    fail_percentage_today = (stats_today['fail'] / total_today * 100) if total_today > 0 else 0
    
    fail_dedup_today = stats_today.get('fail_dedup', stats_today['fail'])
    fail_percentage_dedup_today = (fail_dedup_today / (stats_today['success'] + fail_dedup_today) * 100) if (stats_today['success'] + fail_dedup_today) > 0 else 0
    
    unique_users_affected_today = stats_today.get('unique_users_affected_today', 0)
    impact_percentage_today = stats_today.get('impact_percentage_today', 0)
    total_users_today = stats_today.get('total_users_today', 1)
    users_today_data = stats_today.get('users_today_data', {})
    
    # Prepara lista de usuários com MAC e erros para exibição
    users_list_html = ""
    if users_today_data:
        # Ordena por usuário
        sorted_users = sorted(users_today_data.items())
        users_items = ""
        for username, data in sorted_users[:30]:
            mac_formatted = format_mac(data.get('mac', 'N/A'))
            errors = data.get('errors', set())
            errors_str = ' | '.join(sorted(errors)) if errors else 'Sem erro específico'
            users_items += f'''
            <div class="user-item">
                <span class="user-name">{username}</span>
                <span class="user-mac">{mac_formatted}</span>
                <span class="user-errors">{errors_str}</span>
            </div>'''
        if len(sorted_users) > 30:
            users_items += f'<div class="user-item" style="color:#999;font-style:italic;border-bottom:none;justify-content:center;grid-column:1/-1;">... e mais {len(sorted_users)-30} usuários</div>'
        users_list_html = f'''
        <div class="user-list-container">
            <div class="user-list-title">📋 Usuários impactados hoje ({len(sorted_users)})</div>
            <div class="user-list">
                <div class="user-item user-header">
                    <span class="user-name">👤 Usuário</span>
                    <span class="user-mac">📱 MAC Address</span>
                    <span class="user-errors">🔒 Tipo de Erro</span>
                </div>
                {users_items}
            </div>
        </div>
        '''
    
    vendors_labels = json.dumps(list(stats['vendors'].keys()))
    vendors_data = json.dumps(list(stats['vendors'].values()))
    errors_labels = json.dumps(list(stats['errors'].keys()))
    errors_data = json.dumps(list(stats['errors'].values()))
    
    hour_labels = json.dumps(list(stats['hourly'].keys()))
    hour_data = json.dumps(list(stats['hourly'].values()))
    
    day_labels = json.dumps(list(stats['daily'].keys()))
    day_data = json.dumps(list(stats['daily'].values()))
    
    historical_dates = json.dumps([d[0] for d in stats['historical'][-60:]])
    historical_values = json.dumps([d[1] for d in stats['historical'][-60:]])
    
    top_users = stats['users_fail'].most_common(15)
    users_labels = json.dumps([u[0] for u in top_users])
    users_data = json.dumps([u[1] for u in top_users])
    
    period_text = "Dados disponíveis"
    if stats['first_log'] and stats['last_log']:
        days = (stats['last_log'] - stats['first_log']).days
        period_text = f"📅 {stats['first_log'].strftime('%d/%m/%Y %H:%M')} até {stats['last_log'].strftime('%d/%m/%Y %H:%M')} ({days} dias)"
    
    total = stats['success'] + stats['fail']
    fail_percentage = (stats['fail'] / total * 100) if total > 0 else 0
    
    fail_dedup = stats.get('fail_dedup', stats['fail'])
    total_dedup = stats['success'] + fail_dedup
    fail_percentage_dedup = (fail_dedup / total_dedup * 100) if total_dedup > 0 else 0
    
    unique_users_affected = stats.get('unique_users_affected', len(stats['users_fail']))
    impact_percentage = stats.get('impact_percentage', 0)
    total_users = stats.get('total_users', len(stats['users_fail']) + 1)
    
    colors = json.dumps([
        '#dc3545', '#ffc107', '#0d6efd', '#6c757d', 
        '#20c997', '#fd7e14', '#6f42c1', '#e83e8c',
        '#198754', '#fd7e14', '#0dcaf0', '#d63384'
    ])
    
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
        
        .grid {{ display: grid; grid-template-columns: 1fr 1fr 1fr 1fr; gap: 20px; margin-bottom: 25px; }}
        .grid-2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 25px; }}
        .grid-full {{ display: grid; grid-template-columns: 1fr; gap: 20px; margin-bottom: 25px; }}
        
        .card {{
            background: white;
            border-radius: 10px;
            padding: 25px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            position: relative;
        }}
        .card h3 {{ font-size: 14px; font-weight: 500; color: #666; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 10px; }}
        .card .value {{ font-size: 48px; font-weight: 700; }}
        .card .label {{ font-size: 14px; color: #666; margin-top: 5px; }}
        .card .sub {{ font-size: 13px; color: #999; margin-top: 3px; }}
        .card .bruto {{ color: #ccc; text-decoration: line-through; font-size: 16px; }}
        .card-success .value {{ color: #2e7d32; }}
        .card-danger .value {{ color: #c62828; }}
        .card-warning .value {{ color: #e65100; }}
        .card-info .value {{ color: #0d47a1; }}
        .card-dedup {{ background: linear-gradient(135deg, #ffffff, #f3e5f5); border-left: 4px solid #6a1b9a; }}
        .card-dedup .value {{ color: #6a1b9a; }}
        .card-impact {{ background: linear-gradient(135deg, #ffffff, #ffebee); border-left: 4px solid #c62828; }}
        .card-impact .value {{ color: #c62828; font-size: 56px; }}
        
        .card-impact-today {{ 
            background: linear-gradient(135deg, #ffffff, #fff3e0); 
            border-left: 4px solid #e65100; 
        }}
        .card-impact-today .value {{ color: #e65100; font-size: 48px; }}
        
        /* LISTA DE USUÁRIOS COM MAC E ERROS */
        .user-list-container {{
            margin-top: 15px;
            border-top: 1px solid #f0e0d0;
            padding-top: 12px;
        }}
        .user-list-title {{
            font-size: 12px;
            font-weight: 600;
            color: #e65100;
            margin-bottom: 8px;
        }}
        .user-list {{
            max-height: 300px;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 2px;
            padding-right: 5px;
        }}
        .user-item {{
            display: grid;
            grid-template-columns: 1fr 1.2fr 1.8fr;
            gap: 10px;
            align-items: center;
            font-size: 13px;
            padding: 4px 10px;
            border-radius: 4px;
            background: #fff8f0;
            border-bottom: 1px solid #f5ede5;
        }}
        .user-item:last-child {{
            border-bottom: none;
        }}
        .user-item.user-header {{
            background: #f5ede5;
            font-weight: 600;
            color: #666;
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 0.3px;
            border-bottom: 2px solid #e0d0c0;
            position: sticky;
            top: 0;
            z-index: 1;
        }}
        .user-name {{
            font-family: monospace;
            color: #333;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }}
        .user-mac {{
            font-family: monospace;
            color: #888;
            font-size: 12px;
            white-space: nowrap;
        }}
        .user-errors {{
            font-size: 12px;
            color: #555;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }}
        .user-errors .error-tag {{
            display: inline-block;
            background: #e8e0d8;
            padding: 1px 8px;
            border-radius: 10px;
            font-size: 10px;
            margin: 1px 2px;
            color: #555;
        }}
        .user-header .user-mac {{
            color: #666;
        }}
        .user-header .user-errors {{
            color: #666;
        }}
        .user-list::-webkit-scrollbar {{
            width: 5px;
        }}
        .user-list::-webkit-scrollbar-track {{
            background: #f5ede5;
            border-radius: 5px;
        }}
        .user-list::-webkit-scrollbar-thumb {{
            background: #d4c5b5;
            border-radius: 5px;
        }}
        
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
        .today-stats .stat-item .sub {{ font-size: 10px; opacity: 0.6; }}
        .today-stats .stat-item .number.success {{ color: #4caf50; }}
        .today-stats .stat-item .number.danger {{ color: #f44336; }}
        .today-stats .stat-item .number.warning {{ color: #ff9800; }}
        .today-stats .stat-item .number.impact {{ color: #ffab91; }}
        
        .footer {{ text-align: center; margin-top: 25px; color: #666; font-size: 13px; }}
        
        @media (max-width: 768px) {{
            .grid {{ grid-template-columns: 1fr 1fr; }}
            .grid-2 {{ grid-template-columns: 1fr; }}
            .header {{ flex-direction: column; text-align: center; }}
            .today-stats {{ flex-direction: column; }}
            .user-item {{
                grid-template-columns: 1fr;
                gap: 2px;
                padding: 6px 10px;
            }}
            .user-mac {{
                font-size: 11px;
            }}
            .user-errors {{
                font-size: 11px;
            }}
            .user-header {{
                display: none;
            }}
        }}
        @media (max-width: 480px) {{
            .grid {{ grid-template-columns: 1fr; }}
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
                <div class="label">❌ Hoje - Falhas (bruto)</div>
                <div class="sub">↳ {stats_today.get('fail_dedup', stats_today['fail']):,} incidentes reais</div>
            </div>
            <div class="stat-item">
                <div class="number impact">{unique_users_affected_today}</div>
                <div class="label">👤 Usuários impactados hoje</div>
                <div class="sub">{impact_percentage_today:.1f}% dos usuários ativos</div>
            </div>
            <div class="stat-item">
                <div class="number warning">{fail_percentage_today:.1f}%</div>
                <div class="label">⚠️ Taxa bruta</div>
                <div class="sub">↳ {fail_percentage_dedup_today:.1f}% real</div>
            </div>
        </div>
        
        <!-- Cards de estatísticas -->
        <div class="grid">
            <div class="card card-success">
                <h3>✅ Autenticações OK</h3>
                <div class="value">{stats['success']:,}</div>
                <div class="label">Logins bem-sucedidos</div>
            </div>
            <div class="card card-danger">
                <h3>❌ Falhas brutas</h3>
                <div class="value">{stats['fail']:,}</div>
                <div class="label">Total de falhas registradas</div>
                <div class="sub"><span class="bruto">↳ {stats.get('fail_dedup', stats['fail']):,} incidentes reais</span></div>
            </div>
            <div class="card card-impact">
                <h3>👤 Usuários impactados</h3>
                <div class="value">{unique_users_affected:,}</div>
                <div class="label">{impact_percentage:.1f}% dos usuários ativos</div>
                <div class="sub">Total de {total_users} usuários únicos</div>
            </div>
            <div class="card card-dedup">
                <h3>📉 Taxa real de falhas</h3>
                <div class="value">{fail_percentage_dedup:.1f}%</div>
                <div class="label">Incidentes reais desduplicados</div>
                <div class="sub"><span class="bruto">↳ {fail_percentage:.1f}% bruta</span></div>
            </div>
        </div>
        
        <!-- Card de Usuários Impactados Hoje com Lista, MAC e Erros -->
        <div class="grid" style="margin-bottom: 25px;">
            <div class="card card-impact-today" style="grid-column: 1 / -1;">
                <h3>👤 Usuários impactados hoje</h3>
                <div class="value">{unique_users_affected_today}</div>
                <div class="label">{impact_percentage_today:.1f}% dos usuários ativos hoje</div>
                <div class="sub">Total de {total_users_today} usuários únicos hoje</div>
                {users_list_html}
            </div>
        </div>
        
        <!-- Gráficos principais -->
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
        
        <!-- Análise temporal -->
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
        
        <!-- Série histórica -->
        <div class="grid-full">
            <div class="card card-chart">
                <h3>📈 Evolução Diária de Falhas (Últimos 60 dias)</h3>
                <div class="chart-container-tall">
                    <canvas id="chartHistorical"></canvas>
                </div>
            </div>
        </div>
        
        <!-- Top usuários com falhas -->
        <div class="grid-2">
            <div class="card card-chart">
                <h3>👤 Top 15 Usuários com Mais Falhas</h3>
                <div class="chart-container">
                    <canvas id="chartUsers"></canvas>
                </div>
            </div>
            <div class="card">
                <h3>📊 Resumo</h3>
                <div style="margin-top: 15px; line-height: 1.8;">
                    <p><strong>Total de tentativas:</strong> {total:,}</p>
                    <p><strong>Sucessos:</strong> {stats['success']:,} ({stats['success']/total*100:.1f}%)</p>
                    <p><strong>Falhas brutas:</strong> {stats['fail']:,} ({fail_percentage:.1f}%)</p>
                    <p><strong>Falhas reais:</strong> {stats.get('fail_dedup', stats['fail']):,} ({fail_percentage_dedup:.1f}%)</p>
                    <p><strong>👤 Usuários impactados (histórico):</strong> {unique_users_affected} de {total_users}</p>
                    <p><strong>👤 Usuários impactados (hoje):</strong> {unique_users_affected_today}</p>
                    <p><strong>📱 Fabricantes:</strong> {len(stats['vendors'])}</p>
                    <p><strong>🔒 Tipos de erro:</strong> {len(stats['errors'])}</p>
                    <p><strong>📅 Período:</strong> { (stats['last_log'] - stats['first_log']).days if stats['first_log'] and stats['last_log'] else 0 } dias</p>
                </div>
            </div>
        </div>
        
        <div class="footer">
            <p>FreeRADIUS Dashboard - Com desduplicação de eventos repetidos</p>
            <p style="font-size: 11px; color: #999; margin-top: 5px;">🔄 Janela de desduplicação: {DEDUP_WINDOW_MINUTES} minutos | Máx. erros consecutivos: {MAX_CONSECUTIVE_ERRORS}</p>
        </div>
    </div>
    
    <script>
        // Gráfico de fabricantes
        const ctxVendors = document.getElementById('chartVendors').getContext('2d');
        new Chart(ctxVendors, {{
            type: 'doughnut',
            data: {{
                labels: {vendors_labels},
                datasets: [{{
                    data: {vendors_data},
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
        
        // Gráfico de erros
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
        
        // Gráfico de falhas por hora
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
        
        // Gráfico de falhas por dia da semana
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
        
        // Série histórica
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
        
        // Top usuários
        const ctxUsers = document.getElementById('chartUsers').getContext('2d');
        new Chart(ctxUsers, {{
            type: 'bar',
            data: {{
                labels: {users_labels},
                datasets: [{{
                    label: 'Falhas',
                    data: {users_data},
                    backgroundColor: '#6f42c1',
                    borderRadius: 4
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{ legend: {{ display: false }} }},
                scales: {{
                    y: {{ beginAtZero: true, ticks: {{ stepSize: 1 }} }},
                    x: {{ ticks: {{ font: {{ size: 9 }} }} }}
                }}
            }}
        }});
    </script>
</body>
</html>"""

def generate_redirect_html():
    return """<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta http-equiv="refresh" content="0; url=/radius/index.html">
    <title>Redirecionando...</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            background: #f0f2f5;
            margin: 0;
        }
        .container {
            text-align: center;
            padding: 40px;
            background: white;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .spinner {
            border: 4px solid #f3f3f3;
            border-top: 4px solid #1a237e;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 20px auto;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        h2 { color: #1a237e; }
        a { color: #1976d2; text-decoration: none; }
        a:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <div class="container">
        <h2>📊 Dashboard RADIUS</h2>
        <div class="spinner"></div>
        <p>Redirecionando para o dashboard...</p>
        <p><small>Se não for redirecionado automaticamente, <a href="/radius/index.html">clique aqui</a></small></p>
    </div>
</body>
</html>"""

def main():
    print("📊 Gerando Dashboard RADIUS com desduplicação...")
    print("🔄 Janela de desduplicação: {} minutos".format(DEDUP_WINDOW_MINUTES))
    print("📁 Lendo TODOS os arquivos de log...")
    
    stats = parse_all_logs(LOG_PATH, today_only=False, dedup=True)
    
    print("\n📁 Lendo dados do dia atual...")
    stats_today = parse_all_logs(LOG_PATH, today_only=True, dedup=True)
    
    print("\n📊 Estatísticas Históricas:")
    print(f"   ✅ Sucessos: {stats['success']:,}")
    print(f"   ❌ Falhas brutas: {stats['fail']:,}")
    print(f"   🔄 Falhas desduplicadas: {stats.get('fail_dedup', stats['fail']):,}")
    print(f"   👤 Usuários impactados: {stats['unique_users_affected']} de {stats['total_users']} ({stats['impact_percentage']:.1f}%)")
    print(f"   📱 Fabricantes: {len(stats['vendors'])}")
    print(f"   🔒 Tipos de erro: {len(stats['errors'])}")
    
    if stats['first_log'] and stats['last_log']:
        days = (stats['last_log'] - stats['first_log']).days
        print(f"   📅 Período: {stats['first_log'].strftime('%d/%m/%Y')} até {stats['last_log'].strftime('%d/%m/%Y')} ({days} dias)")
    
    total = stats['success'] + stats['fail']
    if total > 0:
        print(f"   📊 Taxa de falhas bruta: {stats['fail']/total*100:.2f}%")
        total_dedup = stats['success'] + stats.get('fail_dedup', stats['fail'])
        if total_dedup > 0:
            print(f"   📊 Taxa real de falhas: {stats.get('fail_dedup', stats['fail'])/total_dedup*100:.2f}%")
    
    print("\n📊 Estatísticas do Dia Atual:")
    print(f"   ✅ Sucessos hoje: {stats_today['success']:,}")
    print(f"   ❌ Falhas brutas hoje: {stats_today['fail']:,}")
    print(f"   🔄 Falhas desduplicadas hoje: {stats_today.get('fail_dedup', stats_today['fail']):,}")
    print(f"   👤 Usuários impactados hoje: {stats_today.get('unique_users_affected_today', 0)}")
    
    users_data = stats_today.get('users_today_data', {})
    if users_data:
        print(f"   📋 Lista de usuários impactados hoje ({len(users_data)}):")
        for username, data in sorted(users_data.items())[:10]:
            errors = ' | '.join(sorted(data.get('errors', set())))
            print(f"      - {username} ({format_mac(data.get('mac', 'N/A'))}) -> {errors}")
        if len(users_data) > 10:
            print(f"      ... e mais {len(users_data)-10} usuários")
    
    total_today = stats_today['success'] + stats_today['fail']
    if total_today > 0:
        print(f"   📊 Taxa de falhas bruta hoje: {stats_today['fail']/total_today*100:.2f}%")
        total_dedup_today = stats_today['success'] + stats_today.get('fail_dedup', stats_today['fail'])
        if total_dedup_today > 0:
            print(f"   📊 Taxa real de falhas hoje: {stats_today.get('fail_dedup', stats_today['fail'])/total_dedup_today*100:.2f}%")
    
    print(f"\n📦 Carregando Chart.js...")
    chart_js = load_chartjs()
    
    print(f"📝 Gerando dashboard...")
    dashboard_html = generate_html(stats, stats_today, chart_js)
    redirect_html = generate_redirect_html()
    
    os.makedirs("/var/www/html/radius", exist_ok=True)
    
    print(f"💾 Salvando em: {OUTPUT_DASHBOARD}")
    with open(OUTPUT_DASHBOARD, 'w', encoding='utf-8') as f:
        f.write(dashboard_html)
    
    print(f"💾 Salvando redirecionador em: {OUTPUT_INDEX}")
    with open(OUTPUT_INDEX, 'w', encoding='utf-8') as f:
        f.write(redirect_html)
    
    try:
        uid = pwd.getpwnam("www-data").pw_uid
        gid = grp.getgrnam("www-data").gr_gid
        os.chown(OUTPUT_DASHBOARD, uid, gid)
        os.chmod(OUTPUT_DASHBOARD, 0o644)
        os.chown(OUTPUT_INDEX, uid, gid)
        os.chmod(OUTPUT_INDEX, 0o644)
        print("🔒 Permissões ajustadas (www-data)")
    except Exception as e:
        print(f"⚠️  Erro ao ajustar permissões: {e}")
    
    print("\n✅ Dashboard gerado com sucesso!")
    print(f"📊 Acesse via Nginx Proxy Manager: https://seu-dominio/radius/")

if __name__ == "__main__":
    main()
