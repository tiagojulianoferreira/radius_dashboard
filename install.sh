
## 2. install.sh (Script de Instalação)

```bash
#!/bin/bash
# install.sh - Script de instalação do Dashboard RADIUS
# Uso: curl -sSL https://raw.githubusercontent.com/tiagojulianoferreira/radius_dashboard/main/install.sh | sudo bash

set -e

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configurações do repositório
REPO_OWNER="tiagojulianoferreira"
REPO_NAME="radius_dashboard"
REPO_BRANCH="main"
REPO_RAW="https://raw.githubusercontent.com/${REPO_OWNER}/${REPO_NAME}/${REPO_BRANCH}"

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     RADIUS Dashboard - Script de Instalação Automática    ║${NC}"
echo -e "${BLUE}║           FreeRADIUS Monitoring & Analytics               ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Verifica se é root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}❌ Este script precisa ser executado como root${NC}"
    echo "   Execute: sudo bash install.sh"
    exit 1
fi

# ============================================================
# 1. VERIFICAÇÃO DE CONEXÃO
# ============================================================
echo -e "${YELLOW}[1/7] Verificando conexão com a internet...${NC}"

if ! curl -s --connect-timeout 5 -o /dev/null -w "%{http_code}" https://raw.githubusercontent.com | grep -q "200\|301\|302"; then
    echo -e "${RED}❌ Sem conexão com GitHub. Verifique sua rede.${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Conexão ok${NC}"

# ============================================================
# 2. INSTALAÇÃO DE DEPENDÊNCIAS
# ============================================================
echo ""
echo -e "${YELLOW}[2/7] Instalando dependências...${NC}"

# Detecta o sistema operacional
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
    VER=$VERSION_ID
else
    echo -e "${RED}❌ Sistema operacional não suportado${NC}"
    exit 1
fi
echo -e "   📦 Sistema: ${GREEN}$OS $VER${NC}"

# Atualiza pacotes
apt update -qq 2>/dev/null || true

# Instala dependências
apt install -y -qq \
    nginx \
    python3 \
    python3-venv \
    python3-pip \
    wget \
    curl \
    net-tools \
    systemd \
    gzip \
    coreutils \
    ca-certificates

# Verifica comandos essenciais
for cmd in nginx python3 curl wget; do
    if ! command -v $cmd &> /dev/null; then
        echo -e "${RED}❌ Comando '$cmd' não encontrado${NC}"
        exit 1
    fi
done

echo -e "${GREEN}✅ Dependências instaladas${NC}"

# ============================================================
# 3. VERIFICAÇÃO DOS LOGS
# ============================================================
echo ""
echo -e "${YELLOW}[3/7] Verificando logs do FreeRADIUS...${NC}"

LOG_PATH="/var/log/freeradius/radius.log"
if [ ! -f "$LOG_PATH" ]; then
    echo -e "${YELLOW}⚠️  Log não encontrado em: $LOG_PATH${NC}"
    
    # Procura em locais alternativos
    ALT_LOGS=(
        "/var/log/radius/radius.log"
        "/var/log/freeradius/radius/radius.log"
        "/var/log/radius.log"
        "/var/log/freeradius/freeradius.log"
    )
    
    for alt in "${ALT_LOGS[@]}"; do
        if [ -f "$alt" ]; then
            LOG_PATH="$alt"
            echo -e "${GREEN}✅ Log encontrado em: $LOG_PATH${NC}"
            break
        fi
    done
    
    if [ ! -f "$LOG_PATH" ]; then
        echo -e "${YELLOW}⚠️  Nenhum log do FreeRADIUS encontrado${NC}"
        echo -e "${YELLOW}   O dashboard será gerado sem dados históricos${NC}"
        echo -e "${YELLOW}   Certifique-se que o FreeRADIUS está configurado${NC}"
        echo ""
        read -p "Continuar mesmo assim? (s/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Ss]$ ]]; then
            exit 1
        fi
    fi
else
    echo -e "${GREEN}✅ Log do FreeRADIUS encontrado: $LOG_PATH${NC}"
    echo -e "${GREEN}   Últimas 3 linhas:${NC}"
    tail -3 "$LOG_PATH" 2>/dev/null | sed 's/^/   /' || true
fi

# ============================================================
# 4. CRIAÇÃO DE DIRETÓRIOS
# ============================================================
echo ""
echo -e "${YELLOW}[4/7] Criando diretórios...${NC}"

mkdir -p /opt/radius_dashboard/templates/css
mkdir -p /opt/radius_dashboard/templates/js
mkdir -p /opt/radius_dashboard/config
mkdir -p /var/www/html/radius
mkdir -p /var/log

echo -e "${GREEN}✅ Diretórios criados${NC}"

# ============================================================
# 5. DOWNLOAD DOS ARQUIVOS
# ============================================================
echo ""
echo -e "${YELLOW}[5/7] Baixando arquivos do repositório...${NC}"

# Função para baixar arquivo
download_file() {
    local url="$1"
    local output="$2"
    local desc="$3"
    
    echo -n "   📥 Baixando $desc... "
    if wget -q -O "$output" "$url" 2>/dev/null; then
        if [ -s "$output" ]; then
            echo -e "${GREEN}OK${NC}"
            return 0
        fi
    fi
    echo -e "${RED}FALHOU${NC}"
    return 1
}

# Lista de arquivos
FILES=(
    "gerar_painel.py:/opt/radius_dashboard/gerar_painel.py:Script Python"
    "templates/index.html:/opt/radius_dashboard/templates/index.html:Template HTML"
    "templates/css/style.css:/opt/radius_dashboard/templates/css/style.css:CSS"
    "templates/js/dashboard.js:/opt/radius_dashboard/templates/js/dashboard.js:JavaScript"
    "config/nginx-radius.conf:/opt/radius_dashboard/config/nginx-radius.conf:Config Nginx"
)

for file in "${FILES[@]}"; do
    IFS=':' read -r src dest desc <<< "$file"
    if ! download_file "${REPO_RAW}/${src}" "$dest" "$desc"; then
        echo -e "   ${YELLOW}⚠️  Falha ao baixar $desc${NC}"
    fi
done

# Baixa Chart.js
echo -n "   📥 Baixando Chart.js... "
if wget -q -O /var/www/html/radius/chart.min.js https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js 2>/dev/null; then
    echo -e "${GREEN}OK${NC}"
else
    echo -e "${YELLOW}FALHOU (será baixado na primeira execução)${NC}"
fi

chmod +x /opt/radius_dashboard/gerar_painel.py
echo -e "${GREEN}✅ Arquivos baixados${NC}"

# ============================================================
# 6. CONFIGURAÇÃO DO NGINX
# ============================================================
echo ""
echo -e "${YELLOW}[6/7] Configurando Nginx...${NC}"

# Para o Nginx
systemctl stop nginx 2>/dev/null || true

# Remove configurações antigas
rm -f /etc/nginx/sites-enabled/default
rm -f /etc/nginx/sites-available/default

# Usa a configuração do repositório ou cria padrão
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

    location = / {
        return 301 /radius/index.html;
    }

    location /radius/ {
        alias /var/www/html/radius/;
        index index.html;
        try_files $uri $uri/ =404;
        
        location ~* \.html$ {
            add_header Cache-Control "no-cache, no-store, must-revalidate";
        }
        
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|avif)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }

    location ~ /\. {
        deny all;
    }

    access_log /var/log/nginx/radius_access.log;
    error_log /var/log/nginx/radius_error.log;
}
NGINX
fi

# Habilita o site
ln -sf /etc/nginx/sites-available/radius /etc/nginx/sites-enabled/

# Inicia o Nginx
systemctl start nginx 2>/dev/null || true

# Testa e recarrega
if nginx -t 2>/dev/null; then
    systemctl reload nginx 2>/dev/null || true
    echo -e "${GREEN}✅ Nginx configurado na porta 8080${NC}"
else
    echo -e "${YELLOW}⚠️  Erro na configuração do Nginx${NC}"
fi

# ============================================================
# 7. CONFIGURAÇÃO DOS SERVIÇOS SYSTEMD
# ============================================================
echo ""
echo -e "${YELLOW}[7/7] Configurando serviços systemd...${NC}"

# Cria ambiente virtual
cd /opt/radius_dashboard
python3 -m venv venv 2>/dev/null || true

# Serviço
cat > /etc/systemd/system/radius-dashboard.service << 'SERVICE'
[Unit]
Description=Dashboard RADIUS - FreeRADIUS Monitoring
After=network.target nginx.service

[Service]
Type=oneshot
ExecStart=/opt/radius_dashboard/venv/bin/python3 /opt/radius_dashboard/gerar_painel.py
User=www-data
Group=www-data
StandardOutput=append:/var/log/radius_dashboard.log
StandardError=append:/var/log/radius_dashboard.log
Environment="PYTHONUNBUFFERED=1"

[Install]
WantedBy=multi-user.target
SERVICE

# Timer
cat > /etc/systemd/system/radius-dashboard.timer << 'TIMER'
[Unit]
Description=Timer para atualizar Dashboard RADIUS a cada 5 minutos
Requires=radius-dashboard.service

[Timer]
OnBootSec=1min
OnUnitActiveSec=5min
RandomizedDelaySec=30s

[Install]
WantedBy=timers.target
TIMER

# Recarrega e ativa
systemctl daemon-reload
systemctl enable radius-dashboard.timer 2>/dev/null || true
systemctl start radius-dashboard.timer 2>/dev/null || true

echo -e "${GREEN}✅ Serviços systemd configurados${NC}"

# ============================================================
# GERAÇÃO DO DASHBOARD
# ============================================================
echo ""
echo -e "${YELLOW}📊 Gerando dashboard pela primeira vez...${NC}"

# Executa a primeira geração
if /opt/radius_dashboard/venv/bin/python3 /opt/radius_dashboard/gerar_painel.py 2>/dev/null; then
    echo -e "${GREEN}✅ Dashboard gerado com sucesso!${NC}"
else
    echo -e "${YELLOW}⚠️  Falha na primeira geração. Verifique os logs.${NC}"
    echo -e "${YELLOW}   Executando com debug...${NC}"
    /opt/radius_dashboard/venv/bin/python3 /opt/radius_dashboard/gerar_painel.py
fi

# ============================================================
# RESUMO FINAL
# ============================================================
echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                    INSTALAÇÃO CONCLUÍDA!                    ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Verifica o arquivo HTML
if [ -f "/var/www/html/radius/index.html" ]; then
    SIZE=$(du -h /var/www/html/radius/index.html | cut -f1)
    echo -e "${GREEN}✅ Dashboard HTML: $SIZE${NC}"
else
    echo -e "${RED}❌ Dashboard HTML não encontrado${NC}"
fi

# Mostra informações de acesso
IP=$(hostname -I | cut -d' ' -f1 2>/dev/null || echo "localhost")
echo ""
echo "📊 Acesse o dashboard:"
echo -e "   ${BLUE}http://$IP:8080/radius/index.html${NC}"
echo -e "   ${BLUE}http://$IP:8080/${NC} (redireciona automaticamente)"
echo ""

echo "📁 Arquivos importantes:"
echo "   - Script: /opt/radius_dashboard/gerar_painel.py"
echo "   - HTML: /var/www/html/radius/index.html"
echo "   - Templates: /opt/radius_dashboard/templates/"
echo "   - Logs: /var/log/radius_dashboard.log"
echo "   - Nginx: /etc/nginx/sites-available/radius"
echo ""

echo "🔄 Atualização automática:"
echo "   - Timer: radius-dashboard.timer (a cada 5 minutos)"
echo "   - Verifique: systemctl list-timers --all | grep radius"
echo ""

echo "🛠️  Comandos úteis:"
echo "   - Forçar atualização: systemctl start radius-dashboard.service"
echo "   - Ver logs: journalctl -u radius-dashboard.service -n 50 -f"
echo "   - Ver timer: systemctl status radius-dashboard.timer"
echo "   - Ver Nginx: systemctl status nginx"
echo ""

echo -e "${GREEN}✅ Instalação concluída!${NC}"
echo -e "${YELLOW}⚠️  Para acessar via HTTPS, configure um proxy reverso${NC}"
