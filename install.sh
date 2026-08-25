cat > /tmp/install-radius-dashboard.sh << 'EOF'
#!/bin/bash
# install-radius-dashboard.sh
# Script de instalação automática do Dashboard RADIUS

set -e

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     RADIUS Dashboard - Script de Instalação Automática    ║${NC}"
echo -e "${BLUE}║           FreeRADIUS Monitoring & Analytics               ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# ============================================================
# 1. VERIFICAÇÃO DE PRÉ-REQUISITOS
# ============================================================
echo -e "${YELLOW}[1/6] Verificando pré-requisitos...${NC}"

if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}❌ Este script precisa ser executado como root${NC}"
    exit 1
fi

if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 não encontrado.${NC}"
    echo -e "${YELLOW}   Instale com: apt install python3 python3-venv python3-pip -y${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Python 3: $(python3 --version)${NC}"

if ! command -v nginx &> /dev/null; then
    echo -e "${YELLOW}⚠️  Nginx não encontrado. Instalando...${NC}"
    apt update && apt install -y nginx
fi
echo -e "${GREEN}✅ Nginx: $(nginx -v 2>&1 | cut -d'/' -f2)${NC}"

if ! command -v wget &> /dev/null; then
    echo -e "${YELLOW}⚠️  wget não encontrado. Instalando...${NC}"
    apt install -y wget
fi

LOG_PATH="/var/log/freeradius/radius.log"
if [ ! -f "$LOG_PATH" ]; then
    echo -e "${YELLOW}⚠️  Log do FreeRADIUS não encontrado em: $LOG_PATH${NC}"
    echo -e "${YELLOW}   Verifique se o FreeRADIUS está instalado e configurado${NC}"
    echo -e "${YELLOW}   Caminhos comuns de log:${NC}"
    echo -e "${YELLOW}   - /var/log/freeradius/radius.log${NC}"
    echo -e "${YELLOW}   - /var/log/radius/radius.log${NC}"
    echo ""
    read -p "Deseja continuar mesmo assim? (s/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Ss]$ ]]; then
        exit 1
    fi
else
    echo -e "${GREEN}✅ Log do FreeRADIUS encontrado: $LOG_PATH${NC}"
    echo -e "${GREEN}   Últimas 3 linhas:${NC}"
    tail -3 "$LOG_PATH" | sed 's/^/   /'
fi

# ============================================================
# 2. CONFIGURAÇÃO DO DOMÍNIO
# ============================================================
echo ""
echo -e "${YELLOW}[2/6] Configuração do domínio...${NC}"
read -p "Digite o domínio para o dashboard (ex: radius.ifsc.edu.br) ou pressione Enter para usar localhost: " DOMAIN
DOMAIN=${DOMAIN:-"localhost"}
echo -e "${GREEN}✅ Domínio definido: $DOMAIN${NC}"

# ============================================================
# 3. INSTALAÇÃO DO DASHBOARD
# ============================================================
echo ""
echo -e "${YELLOW}[3/6] Instalando o Dashboard...${NC}"

mkdir -p /opt/radius_dashboard
cd /opt/radius_dashboard

echo "   Criando ambiente virtual Python..."
python3 -m venv venv

mkdir -p /var/www/html/radius

echo "   Baixando Chart.js..."
wget -q -O /var/www/html/radius/chart.min.js https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js
chown www-data:www-data /var/www/html/radius/chart.min.js 2>/dev/null || true
echo -e "${GREEN}✅ Chart.js baixado${NC}"

# ============================================================
# 4. CRIAÇÃO DO SCRIPT PYTHON
# ============================================================
echo ""
echo -e "${YELLOW}[4/6] Criando script Python...${NC}"

cat > /opt/radius_dashboard/gerar_painel.py << 'PYTHON_SCRIPT'
#!/opt/radius_dashboard/venv/bin/python3
"""
Dashboard RADIUS - IFSC
Com análise histórica e dados do dia atual
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
            
            ok_match = ok_re.match(line)
            if ok_match:
                sess_id = ok_match.group(1)
                if sess_id not in processed_sessions:
                    stats['success'] += 1
                    processed_sessions.add(sess_id)
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
                    
                    stats['vendors'][vendor] = stats['vendors'].get(vendor, 0) + 1
                    stats['errors'][error_type] = stats['errors'].get(error_type, 0) + 1
                    
                    if current_date:
                        hour_key = f"{current_date.hour:02d}:00"
                        stats['hourly'][hour_key] += 1
                        day_name = calendar.day_name[current_date.weekday()]
                        stats['daily'][day_name] += 1
                        date_key = current_date.strftime('%Y-%m-%d')
                        stats['historical'][date_key] += 1
                    
                    user_match = re.search(r'\[([^\]]+)\]', line)
                    if user_match:
                        username = user_match.group(1).split('/')[0]
                        stats['users_fail'][username] += 1
                
                error_type = "Senha incorreta"

def parse_all_logs(log_pattern="/var/log/freeradius/radius.log*", today_only=False):
    stats = {
        'success': 0,
        'fail': 0,
        'vendors': {},
        'errors': {},
        'hourly': defaultdict(int),
        'daily': defaultdict(int),
        'historical': defaultdict(int),
        'users_fail': Counter(),
        'first_log': None,
        'last_log': None
    }
    
    log_files = sorted(glob.glob(log_pattern), reverse=True)
    if not log_files:
        print("   ⚠️  Nenhum arquivo de log encontrado!")
        return stats
    
    for log_file in log_files:
        try:
            parse_log_file(log_file, stats, today_only)
        except Exception as e:
            print(f"   ⚠️  Erro ao processar {log_file}: {e}")
    
    stats['historical'] = sorted(stats['historical'].items())
    return stats

def load_chartjs():
    if os.path.exists(CHART_JS_PATH):
        with open(CHART_JS_PATH, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    return "// Chart.js não encontrado"

def generate_html(stats, stats_today, chart_js_code):
    total_today = stats_today['success'] + stats_today['fail']
    fail_percentage_today = (stats_today['fail'] / total_today * 100) if total_today > 0 else 0
    
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
        
        .footer {{ text-align: center; margin-top: 25px; color: #666; font-size: 13px; }}
        
        @media (max-width: 768px) {{
            .grid {{ grid-template-columns: 1fr; }}
            .grid-2 {{ grid-template-columns: 1fr; }}
            .header {{ flex-direction: column; text-align: center; }}
            .today-stats {{ flex-direction: column; }}
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
                <div class="number warning">{fail_percentage_today:.1f}%</div>
                <div class="label">⚠️ Hoje - Taxa de falhas</div>
            </div>
            <div class="stat-item">
                <div class="number">{total_today:,}</div>
                <div class="label">📊 Hoje - Total de tentativas</div>
            </div>
        </div>
        
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
            <div class="card card-warning">
                <h3>⚠️ Taxa de falhas</h3>
                <div class="value">{fail_percentage:.1f}%</div>
                <div class="label">{stats['fail']:,} falhas em {total:,} tentativas</div>
            </div>
        </div>
        
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
                    <p><strong>Falhas:</strong> {stats['fail']:,} ({fail_percentage:.1f}%)</p>
                    <p><strong>Fabricantes distintos:</strong> {len(stats['vendors'])}</p>
                    <p><strong>Tipos de erro:</strong> {len(stats['errors'])}</p>
                    <p><strong>Usuários com falhas:</strong> {len(stats['users_fail'])}</p>
                </div>
            </div>
        </div>
        
        <div class="footer">
            <p>FreeRADIUS Dashboard - Gerado automaticamente via análise de logs históricos</p>
        </div>
    </div>
    
    <script>
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

# ============================================================
# FUNÇÃO PRINCIPAL
# ============================================================

def main():
    print("📊 Gerando Dashboard RADIUS...")
    print("📁 Lendo todos os logs...")
    
    stats = parse_all_logs(LOG_PATH, today_only=False)
    stats_today = parse_all_logs(LOG_PATH, today_only=True)
    
    print(f"\n📊 Histórico: ✅ {stats['success']:,} | ❌ {stats['fail']:,}")
    print(f"📊 Hoje: ✅ {stats_today['success']:,} | ❌ {stats_today['fail']:,}")
    
    chart_js = load_chartjs()
    dashboard_html = generate_html(stats, stats_today, chart_js)
    redirect_html = generate_redirect_html()
    
    os.makedirs("/var/www/html/radius", exist_ok=True)
    
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
PYTHON_SCRIPT

chmod +x /opt/radius_dashboard/gerar_painel.py
echo -e "${GREEN}✅ Script Python criado${NC}"

# ============================================================
# 5. CONFIGURAÇÃO DO NGINX
# ============================================================
echo ""
echo -e "${YELLOW}[5/6] Configurando Nginx...${NC}"

cat > /etc/nginx/sites-available/radius << EOF
server {
    listen 8080;
    server_name $DOMAIN;

    root /var/www/html;
    index index.html;

    location = / {
        return 301 /radius/index.html;
    }

    location /radius/ {
        alias /var/www/html/radius/;
        index index.html;
        try_files \$uri \$uri/ =404;
        
        location ~* \.html\$ {
            add_header Cache-Control "no-cache, no-store, must-revalidate";
            add_header Pragma "no-cache";
            add_header Expires "0";
        }
        
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|avif)\$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }

    location ~ ^/(_astro|static|companies)/ {
        return 404;
    }

    location ~ /\. {
        deny all;
    }

    access_log /var/log/nginx/radius_access.log;
    error_log /var/log/nginx/radius_error.log;
}
EOF

ln -sf /etc/nginx/sites-available/radius /etc/nginx/sites-enabled/ 2>/dev/null || true

if nginx -t 2>/dev/null; then
    systemctl reload nginx
    echo -e "${GREEN}✅ Nginx configurado na porta 8080${NC}"
else
    echo -e "${RED}❌ Erro na configuração do Nginx${NC}"
fi

# ============================================================
# 6. CRIAÇÃO DOS SERVIÇOS SYSTEMD
# ============================================================
echo ""
echo -e "${YELLOW}[6/6] Configurando serviços systemd...${NC}"

cat > /etc/systemd/system/radius-dashboard.service << EOF
[Unit]
Description=Servico de Geracao do Dashboard FreeRADIUS IFSC
After=network.target

[Service]
Type=oneshot
ExecStart=/opt/radius_dashboard/venv/bin/python3 /opt/radius_dashboard/gerar_painel.py
User=www-data
Group=www-data
StandardOutput=append:/var/log/radius_dashboard.log
StandardError=append:/var/log/radius_dashboard.log

[Install]
WantedBy=multi-user.target
EOF

cat > /etc/systemd/system/radius-dashboard.timer << EOF
[Unit]
Description=Timer para gerar dashboard FreeRADIUS a cada 5 minutos
Requires=radius-dashboard.service

[Timer]
OnBootSec=1min
OnUnitActiveSec=5min
RandomizedDelaySec=30s

[Install]
WantedBy=timers.target
EOF

systemctl daemon-reload
systemctl enable radius-dashboard.timer 2>/dev/null || true
systemctl start radius-dashboard.timer 2>/dev/null || true

# ============================================================
# VERIFICAÇÃO FINAL
# ============================================================
echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                    INSTALAÇÃO CONCLUÍDA!                    ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

echo "📊 Gerando dashboard pela primeira vez..."
if /opt/radius_dashboard/venv/bin/python3 /opt/radius_dashboard/gerar_painel.py 2>/dev/null; then
    echo -e "${GREEN}✅ Dashboard gerado com sucesso!${NC}"
else
    echo -e "${RED}❌ Falha ao gerar o dashboard.${NC}"
fi

echo ""
echo "📊 Acesse o dashboard:"
echo -e "   ${BLUE}http://$DOMAIN:8080/radius/index.html${NC}"
echo -e "   ${BLUE}http://$DOMAIN:8080/${NC} (redireciona automaticamente)"
echo ""
echo "📁 Arquivos importantes:"
echo "   - Script: /opt/radius_dashboard/gerar_painel.py"
echo "   - HTML: /var/www/html/radius/index.html"
echo "   - Logs: /var/log/radius_dashboard.log"
echo ""
echo "🔄 Atualização automática:"
echo "   - Timer: radius-dashboard.timer (a cada 5 minutos)"
echo "   - Verifique: systemctl list-timers --all | grep radius"
echo ""
echo "🛠️  Comandos úteis:"
echo "   - Forçar atualização: systemctl start radius-dashboard.service"
echo "   - Ver logs: journalctl -u radius-dashboard.service -n 50 -f"
echo "   - Ver timer: systemctl status radius-dashboard.timer"
echo ""
EOF

# 2. Dá permissão de execução
chmod +x /tmp/install-radius-dashboard.sh

# 3. Agora, para executar com um único comando curl, você precisa hospedar
# esse script em um servidor HTTP. Como alternativa, use:
