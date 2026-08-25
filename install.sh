#!/bin/bash
# install.sh - Instalação do Dashboard RADIUS
set -e

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
REPO_RAW="https://raw.githubusercontent.com/tiagojulianoferreira/radius_dashboard/main"

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     RADIUS Dashboard - Script de Instalação Automática    ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"

if [ "$EUID" -ne 0 ]; then echo -e "${RED}❌ Execute como root${NC}"; exit 1; fi

# Função para baixar arquivo com verificação
download_file() {
    local url="$1"
    local output="$2"
    local description="$3"
    
    echo -n "   📥 Baixando $description... "
    
    # Tenta baixar
    if wget -q -O "$output" "$url" 2>/dev/null; then
        # Verifica se o arquivo não está vazio
        if [ -s "$output" ]; then
            # Verifica se não é um HTML de erro
            if ! grep -q "404: Not Found" "$output" 2>/dev/null; then
                echo -e "${GREEN}OK${NC}"
                return 0
            else
                echo -e "${RED}ERRO 404${NC}"
                rm -f "$output"
                return 1
            fi
        else
            echo -e "${RED}ARQUIVO VAZIO${NC}"
            rm -f "$output"
            return 1
        fi
    else
        echo -e "${RED}FALHOU${NC}"
        return 1
    fi
}

# Verifica conexão
echo -e "${YELLOW}[1/6] Verificando conexão...${NC}"
if ! curl -s --connect-timeout 5 -o /dev/null -w "%{http_code}" https://raw.githubusercontent.com | grep -q "200\|301\|302"; then
    echo -e "${RED}❌ Sem conexão com GitHub${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Conexão ok${NC}"

# Instala dependências
echo -e "${YELLOW}[2/6] Instalando dependências...${NC}"
apt update -qq
apt install -y -qq nginx python3 python3-venv wget curl git

# Cria diretórios
echo -e "${YELLOW}[3/6] Criando diretórios...${NC}"
mkdir -p /opt/radius_dashboard/templates/css
mkdir -p /opt/radius_dashboard/templates/js
mkdir -p /opt/radius_dashboard/config
mkdir -p /var/www/html/radius
mkdir -p /var/log

# Baixa arquivos do repositório
echo -e "${YELLOW}[4/6] Baixando arquivos do repositório...${NC}"

# Lista de arquivos para baixar
FILES=(
    "gerar_painel.py:/opt/radius_dashboard/gerar_painel.py:Script Python"
    "templates/index.html:/opt/radius_dashboard/templates/index.html:Template HTML"
    "templates/css/style.css:/opt/radius_dashboard/templates/css/style.css:CSS"
    "templates/js/dashboard.js:/opt/radius_dashboard/templates/js/dashboard.js:JavaScript"
    "config/nginx-radius.conf:/opt/radius_dashboard/config/nginx-radius.conf:Config Nginx"
)

FAILED=0
for file in "${FILES[@]}"; do
    IFS=':' read -r src dest desc <<< "$file"
    if ! download_file "${REPO_RAW}/${src}" "$dest" "$desc"; then
        FAILED=$((FAILED + 1))
        echo -e "   ${YELLOW}⚠️  Falha ao baixar $desc. Criando fallback...${NC}"
    fi
done

# Se o dashboard.js não foi baixado, cria um fallback
if [ ! -s "/opt/radius_dashboard/templates/js/dashboard.js" ] || grep -q "404" "/opt/radius_dashboard/templates/js/dashboard.js" 2>/dev/null; then
    echo -e "   ${YELLOW}📝 Criando dashboard.js localmente...${NC}"
    cat > /opt/radius_dashboard/templates/js/dashboard.js << 'JS_FALLBACK'
document.addEventListener('DOMContentLoaded',function(){const colors={{ COLORS }};
[['chartVendors','doughnut',{{ VENDORS_LABELS }},{{ VENDORS_DATA }}],
 ['chartErrors','bar',{{ ERRORS_LABELS }},{{ ERRORS_DATA }}],
 ['chartHourly','bar',{{ HOUR_LABELS }},{{ HOUR_DATA }}],
 ['chartDaily','bar',{{ DAY_LABELS }},{{ DAY_DATA }}]
].forEach(function(c){const el=document.getElementById(c[0]);if(el)new Chart(el,{type:c[1],data:{labels:c[2],datasets:[{data:c[3],backgroundColor:c[0]==='chartVendors'?colors:'#1976d2',borderWidth:2,borderColor:'#fff',borderRadius:4}]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{position:'bottom',labels:{padding:15,font:{size:11}}}},scales:c[1]==='bar'?{y:{beginAtZero:true,ticks:{stepSize:1}}}:{}}})});
const h=document.getElementById('chartHistorical');if(h)new Chart(h,{type:'line',data:{labels:{{ HISTORICAL_DATES }},datasets:[{label:'Falhas por dia',data:{{ HISTORICAL_VALUES }},borderColor:'#c62828',backgroundColor:'rgba(198,40,40,0.1)',fill:true,tension:0.4,pointRadius:3}]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:true},tooltip:{callbacks:{label:function(c){return c.parsed.y+' falhas'}}}},scales:{y:{beginAtZero:true,ticks:{stepSize:1}}}}});
const u=document.getElementById('chartProblematicUsers');if(u){const d={{ PROBLEMATIC_USERS_DETAILS }};new Chart(u,{type:'bar',data:{labels:{{ PROBLEMATIC_USERS_LABELS }},datasets:[{label:'Taxa de Erro (%)',data:{{ PROBLEMATIC_USERS_DATA }},backgroundColor:['#c62828','#d32f2f','#e53935','#ef5350','#e57373'],borderRadius:4}]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false},tooltip:{callbacks:{afterLabel:function(c){const u=d[c.dataIndex];return u?u.fail+' falhas / '+u.total+' tentativas':''}}}},scales:{y:{beginAtZero:true,max:100,ticks:{callback:function(v){return v+'%'}}}}}})}
const m=document.getElementById('chartProblematicMacs');if(m){const d={{ PROBLEMATIC_MACS_DETAILS }};new Chart(m,{type:'bar',data:{labels:{{ PROBLEMATIC_MACS_LABELS }},datasets:[{label:'Taxa de Erro (%)',data:{{ PROBLEMATIC_MACS_DATA }},backgroundColor:['#0d47a1','#1565c0','#1976d2','#1e88e5','#42a5f5'],borderRadius:4}]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false},tooltip:{callbacks:{afterLabel:function(c){const d=c.dataIndex;const mac=macsData[d];return mac?mac.vendor+' | '+mac.fail+' falhas / '+mac.total+' tentativas':''}}}},scales:{y:{beginAtZero:true,max:100,ticks:{callback:function(v){return v+'%'}}}}}})}console.log('📊 Dashboard RADIUS carregado!')});
JS_FALLBACK
fi

# Dá permissão ao script Python
chmod +x /opt/radius_dashboard/gerar_painel.py

# Configura Nginx
echo -e "${YELLOW}[5/6] Configurando Nginx...${NC}"
if [ -f /opt/radius_dashboard/config/nginx-radius.conf ]; then
    cp /opt/radius_dashboard/config/nginx-radius.conf /etc/nginx/sites-available/radius
else
    cat > /etc/nginx/sites-available/radius << 'NGINX'
server {
    listen 8080 default_server;
    listen [::]:8080 default_server;
    server_name _;
    root /var/www/html;
    index index.html;
    location = / { return 301 /radius/index.html; }
    location /radius/ {
        alias /var/www/html/radius/;
        index index.html;
        try_files $uri $uri/ =404;
        location ~* \.html$ { add_header Cache-Control "no-cache, no-store, must-revalidate"; }
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|avif)$ { expires 1y; add_header Cache-Control "public, immutable"; }
    }
    location ~ /\. { deny all; }
    access_log /var/log/nginx/radius_access.log;
    error_log /var/log/nginx/radius_error.log;
}
NGINX
fi

ln -sf /etc/nginx/sites-available/radius /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx

# Configura serviço
echo -e "${YELLOW}[6/6] Configurando serviço...${NC}"
cat > /etc/systemd/system/radius-dashboard.service << 'SERVICE'
[Unit]
Description=Dashboard RADIUS
After=network.target

[Service]
Type=oneshot
ExecStart=/opt/radius_dashboard/venv/bin/python3 /opt/radius_dashboard/gerar_painel.py
User=www-data
Group=www-data
StandardOutput=append:/var/log/radius_dashboard.log
StandardError=append:/var/log/radius_dashboard.log
SERVICE

cat > /etc/systemd/system/radius-dashboard.timer << 'TIMER'
[Unit]
Description=Timer Dashboard RADIUS
[Timer]
OnBootSec=1min
OnUnitActiveSec=5min
[Install]
WantedBy=timers.target
TIMER

systemctl daemon-reload
systemctl enable radius-dashboard.timer
systemctl start radius-dashboard.timer

# Cria ambiente virtual e gera dashboard
echo -e "${YELLOW}📊 Gerando dashboard...${NC}"
cd /opt/radius_dashboard
python3 -m venv venv
/opt/radius_dashboard/venv/bin/python3 /opt/radius_dashboard/gerar_painel.py

echo -e "${GREEN}✅ Instalação concluída!${NC}"
echo -e "📊 Acesse: ${BLUE}http://$(hostname -I | cut -d' ' -f1):8080/radius/index.html${NC}"
