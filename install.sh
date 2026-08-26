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
    ca-certificates \
    2>/dev/null || true

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

mkdir -p /opt/radius_dashboard
mkdir -p /var/www/html/radius
mkdir -p /var/log

echo -e "${GREEN}✅ Diretórios criados${NC}"

# ============================================================
# 5. DOWNLOAD DO SCRIPT PRINCIPAL
# ============================================================
echo ""
echo -e "${YELLOW}[5/7] Baixando script principal do repositório...${NC}"

# Baixa o gerar_painel.py da raiz do repositório
echo -n "   📥 Baixando gerar_painel.py... "
if wget -q -O /opt/radius_dashboard/gerar_painel.py "${REPO_RAW}/gerar_painel.py" 2>/dev/null; then
    if [ -s /opt/radius_dashboard/gerar_painel.py ]; then
        echo -e "${GREEN}OK${NC}"
        chmod +x /opt/radius_dashboard/gerar_painel.py
    else
        echo -e "${RED}FALHOU - Arquivo vazio${NC}"
        exit 1
    fi
else
    echo -e "${RED}FALHOU${NC}"
    echo -e "${YELLOW}   Tentando via curl...${NC}"
    if curl -s -o /opt/radius_dashboard/gerar_painel.py "${REPO_RAW}/gerar_painel.py"; then
        if [ -s /opt/radius_dashboard/gerar_painel.py ]; then
            echo -e "${GREEN}OK${NC}"
            chmod +x /opt/radius_dashboard/gerar_painel.py
        else
            echo -e "${RED}FALHOU - Arquivo vazio${NC}"
            exit 1
        fi
    else
        echo -e "${RED}FALHOU${NC}"
        exit 1
    fi
fi

# Baixa Chart.js
echo -n "   📥 Baixando Chart.js... "
if wget -q -O /var/www/html/radius/chart.min.js https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js 2>/dev/null; then
    echo -e "${GREEN}OK${NC}"
else
    echo -e "${YELLOW}FALHOU (será baixado na primeira execução)${NC}"
fi

# Cria um arquivo de configuração com o caminho do log
cat > /opt/radius_dashboard/config.json << 'CONFIG'
{
    "log_path": "/var/log/freeradius/radius.log",
    "output_dir": "/var/www/html/radius",
    "cache_file": "/opt/radius_dashboard/log_cache.pickle"
}
CONFIG

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

# Configuração do Nginx
cat > /etc/nginx/sites-available/radius << 'NGINX'
server {
    listen 8080 default_server;
    listen [::]:8080 default_server;
    server_name _;

    root /var/www/html;
    index index.html;

    # Redireciona a raiz para o dashboard
    location = / {
        return 301 /radius/index.html;
    }

    # Dashboard
    location /radius/ {
        alias /var/www/html/radius/;
        index index.html;
        try_files $uri $uri/ =404;

        # Previne cache do HTML
        location ~* \.html$ {
            add_header Cache-Control "no-cache, no-store, must-revalidate";
            add_header Pragma "no-cache";
            add_header Expires "0";
        }

        # Cache para assets estáticos
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|avif)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }

    # Protege arquivos sensíveis
    location ~ /\. {
        deny all;
    }

    access_log /var/log/nginx/radius_access.log;
    error_log /var/log/nginx/radius_error.log;
}
NGINX

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
    echo -e "${YELLOW}   Verifique: nginx -t${NC}"
fi

# ============================================================
# 7. CONFIGURAÇÃO DOS SERVIÇOS SYSTEMD
# ============================================================
echo ""
echo -e "${YELLOW}[7/7] Configurando serviços systemd...${NC}"

# Cria ambiente virtual
cd /opt/radius_dashboard
if [ ! -d "venv" ]; then
    echo -n "   Criando ambiente virtual... "
    python3 -m venv venv 2>/dev/null || true
    echo -e "${GREEN}OK${NC}"
fi

# Atualiza pip e instala dependências
if [ -d "venv" ]; then
    echo -n "   Instalando dependências Python... "
    ./venv/bin/pip install --quiet --upgrade pip 2>/dev/null || true
    echo -e "${GREEN}OK${NC}"
fi

# Serviço systemd
cat > /etc/systemd/system/radius-dashboard.service << 'SERVICE'
[Unit]
Description=Dashboard RADIUS - FreeRADIUS Monitoring
After=network.target nginx.service
Wants=network.target

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

# Timer systemd (executa a cada 5 minutos)
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
    /opt/radius_dashboard/venv/bin/python3 /opt/radius_dashboard/gerar_painel.py || true
fi

# ============================================================
# AJUSTE DE PERMISSÕES
# ============================================================
echo ""
echo -e "${YELLOW}🔒 Ajustando permissões...${NC}"

chown -R www-data:www-data /var/www/html/radius 2>/dev/null || true
chown -R www-data:www-data /opt/radius_dashboard 2>/dev/null || true
chmod 755 /opt/radius_dashboard 2>/dev/null || true
chmod 644 /var/www/html/radius/*.html 2>/dev/null || true
chmod 644 /var/www/html/radius/*.json 2>/dev/null || true

echo -e "${GREEN}✅ Permissões ajustadas${NC}"

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
IP=$(hostname -I | awk '{print $1}' 2>/dev/null || echo "localhost")
echo ""
echo "📊 Acesse o dashboard:"
echo -e "   ${BLUE}http://$IP:8080/radius/index.html${NC}"
echo -e "   ${BLUE}http://$IP:8080/${NC} (redireciona automaticamente)"
echo ""

echo "📁 Arquivos importantes:"
echo "   - Script: /opt/radius_dashboard/gerar_painel.py"
echo "   - HTML: /var/www/html/radius/index.html"
echo "   - Dados: /var/www/html/radius/data.json"
echo "   - Log: /var/log/radius_dashboard.log"
echo "   - Cache: /opt/radius_dashboard/log_cache.pickle"
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
echo "   - Executar manual: /opt/radius_dashboard/venv/bin/python3 /opt/radius_dashboard/gerar_painel.py"
echo ""

echo -e "${GREEN}✅ Instalação concluída!${NC}"
echo -e "${YELLOW}⚠️  Para acessar via HTTPS, configure um proxy reverso${NC}"
