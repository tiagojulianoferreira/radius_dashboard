#!/bin/bash
# install.sh
# Script de instalação automática do Dashboard RADIUS
# Baixa o gerar_painel.py do repositório

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
# CONFIGURAÇÕES DO REPOSITÓRIO
# ============================================================
REPO_OWNER="tiagojulianoferreira"
REPO_NAME="radius_dashboard"
REPO_BRANCH="main"
REPO_RAW="https://raw.githubusercontent.com/${REPO_OWNER}/${REPO_NAME}/${REPO_BRANCH}"

# ============================================================
# 1. VERIFICAÇÃO DE PRÉ-REQUISITOS
# ============================================================
echo -e "${YELLOW}[1/7] Verificando e instalando dependências...${NC}"

if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}❌ Este script precisa ser executado como root${NC}"
    exit 1
fi

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

# Verifica conexão com a internet via HTTPS
echo "   🌐 Verificando conexão com a internet via HTTPS..."
if ! curl -s --connect-timeout 5 --max-time 10 -o /dev/null -w "%{http_code}" https://raw.githubusercontent.com | grep -q "200\|301\|302"; then
    echo -e "${RED}❌ Sem conexão HTTPS com GitHub. Não é possível baixar os arquivos.${NC}"
    echo -e "${YELLOW}   Verifique:${NC}"
    echo -e "${YELLOW}   - Firewall liberado para porta 443${NC}"
    echo -e "${YELLOW}   - Proxy configurado (se necessário)${NC}"
    echo -e "${YELLOW}   - DNS resolvendo corretamente${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Conexão HTTPS ok${NC}"

# Atualiza os pacotes
echo "   📦 Atualizando pacotes..."
apt update -qq

# Instala dependências
echo "   📦 Instalando dependências..."
apt install -y -qq \
    nginx \
    python3 \
    python3-venv \
    python3-pip \
    wget \
    curl \
    net-tools \
    sudo \
    systemd \
    gzip \
    coreutils \
    git \
    ca-certificates

# Verifica Python
python3 --version | head -1
echo -e "${GREEN}✅ Dependências instaladas${NC}"

# ============================================================
# 2. VERIFICAÇÃO DOS LOGS
# ============================================================
echo ""
echo -e "${YELLOW}[2/7] Verificando logs do FreeRADIUS...${NC}"

LOG_PATH="/var/log/freeradius/radius.log"
if [ ! -f "$LOG_PATH" ]; then
    echo -e "${YELLOW}⚠️  Log do FreeRADIUS não encontrado em: $LOG_PATH${NC}"
    echo -e "${YELLOW}   Verificando caminhos alternativos...${NC}"
    
    ALTERNATIVE_LOGS=(
        "/var/log/radius/radius.log"
        "/var/log/freeradius/radius/radius.log"
        "/var/log/radius.log"
        "/var/log/freeradius/freeradius.log"
    )
    
    FOUND_LOG=""
    for alt in "${ALTERNATIVE_LOGS[@]}"; do
        if [ -f "$alt" ]; then
            FOUND_LOG="$alt"
            break
        fi
    done
    
    if [ -n "$FOUND_LOG" ]; then
        echo -e "${GREEN}✅ Log encontrado em: $FOUND_LOG${NC}"
        LOG_PATH="$FOUND_LOG"
    else
        echo -e "${YELLOW}⚠️  Nenhum log do FreeRADIUS encontrado.${NC}"
        echo -e "${YELLOW}   O dashboard será gerado, mas sem dados.${NC}"
        echo -e "${YELLOW}   Certifique-se de que o FreeRADIUS está configurado.${NC}"
        echo ""
        read -p "Deseja continuar mesmo assim? (s/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Ss]$ ]]; then
            exit 1
        fi
    fi
else
    echo -e "${GREEN}✅ Log do FreeRADIUS encontrado: $LOG_PATH${NC}"
    echo -e "${GREEN}   Últimas 3 linhas:${NC}"
    tail -3 "$LOG_PATH" | sed 's/^/   /'
fi

# ============================================================
# 3. CONFIGURAÇÃO DO DOMÍNIO
# ============================================================
echo ""
echo -e "${YELLOW}[3/7] Configuração do domínio...${NC}"
read -p "Digite o domínio para o dashboard (ex: radius.ifsc.edu.br) ou pressione Enter para usar localhost: " DOMAIN
DOMAIN=${DOMAIN:-"localhost"}
echo -e "${GREEN}✅ Domínio definido: $DOMAIN${NC}"

# ============================================================
# 4. INSTALAÇÃO DO DASHBOARD
# ============================================================
echo ""
echo -e "${YELLOW}[4/7] Instalando o Dashboard...${NC}"

# Cria diretórios
mkdir -p /opt/radius_dashboard
mkdir -p /var/www/html/radius
mkdir -p /var/log

cd /opt/radius_dashboard

# Cria ambiente virtual
echo "   🐍 Criando ambiente virtual Python..."
python3 -m venv venv

# ============================================================
# 5. BAIXA OS ARQUIVOS DO REPOSITÓRIO
# ============================================================
echo ""
echo -e "${YELLOW}[5/7] Baixando arquivos do repositório...${NC}"

# Baixa o script Python
echo "   📥 Baixando gerar_painel.py..."
if wget -q -O /opt/radius_dashboard/gerar_painel.py "${REPO_RAW}/gerar_painel.py"; then
    echo -e "${GREEN}✅ gerar_painel.py baixado${NC}"
else
    echo -e "${RED}❌ Falha ao baixar gerar_painel.py${NC}"
    echo -e "${YELLOW}   Verifique se o arquivo existe no repositório:${NC}"
    echo -e "${YELLOW}   ${REPO_RAW}/gerar_painel.py${NC}"
    exit 1
fi

chmod +x /opt/radius_dashboard/gerar_painel.py

# Baixa o Chart.js
echo "   📥 Baixando Chart.js..."
if wget -q -O /var/www/html/radius/chart.min.js https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js; then
    echo -e "${GREEN}✅ Chart.js baixado${NC}"
else
    echo -e "${YELLOW}⚠️  Falha ao baixar Chart.js. Tentando com curl...${NC}"
    curl -s -o /var/www/html/radius/chart.min.js https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js
fi
chown www-data:www-data /var/www/html/radius/chart.min.js 2>/dev/null || true

echo -e "${GREEN}✅ Arquivos baixados${NC}"

# ============================================================
# 6. CONFIGURAÇÃO DO NGINX
# ============================================================
echo ""
echo -e "${YELLOW}[6/7] Configurando Nginx...${NC}"

# Para o Nginx se estiver rodando
systemctl stop nginx 2>/dev/null || true

# Remove configurações antigas
rm -f /etc/nginx/sites-enabled/default
rm -f /etc/nginx/sites-available/default

# Cria a configuração
cat > /etc/nginx/sites-available/radius << 'NGINX_CONFIG'
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
            add_header Pragma "no-cache";
            add_header Expires "0";
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
NGINX_CONFIG

# Habilita o site
ln -sf /etc/nginx/sites-available/radius /etc/nginx/sites-enabled/

# Inicia o Nginx
systemctl start nginx

# Testa a configuração
if nginx -t 2>/dev/null; then
    systemctl reload nginx
    echo -e "${GREEN}✅ Nginx configurado na porta 8080${NC}"
else
    echo -e "${RED}❌ Erro na configuração do Nginx${NC}"
    echo -e "${YELLOW}   Verifique: nginx -t${NC}"
fi

# ============================================================
# 7. CRIAÇÃO DOS SERVIÇOS SYSTEMD
# ============================================================
echo ""
echo -e "${YELLOW}[7/7] Configurando serviços systemd...${NC}"

# Atualiza o script com o caminho correto do log
sed -i "s|LOG_PATH = \"/var/log/freeradius/radius.log*\"|LOG_PATH = \"${LOG_PATH}*\"|g" /opt/radius_dashboard/gerar_painel.py

# Serviço
cat > /etc/systemd/system/radius-dashboard.service << 'SERVICE'
[Unit]
Description=Servico de Geracao do Dashboard FreeRADIUS IFSC
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
Description=Timer para gerar dashboard FreeRADIUS a cada 5 minutos
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
systemctl enable radius-dashboard.service 2>/dev/null || true

echo -e "${GREEN}✅ Serviços systemd configurados${NC}"

# ============================================================
# VERIFICAÇÃO FINAL
# ============================================================
echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                    INSTALAÇÃO CONCLUÍDA!                    ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Gera o dashboard pela primeira vez
echo "📊 Gerando dashboard pela primeira vez..."
if /opt/radius_dashboard/venv/bin/python3 /opt/radius_dashboard/gerar_painel.py 2>/dev/null; then
    echo -e "${GREEN}✅ Dashboard gerado com sucesso!${NC}"
else
    echo -e "${RED}❌ Falha ao gerar o dashboard.${NC}"
    echo -e "${YELLOW}   Verifique o log: cat /var/log/radius_dashboard.log${NC}"
    echo -e "${YELLOW}   Execute manualmente: /opt/radius_dashboard/venv/bin/python3 /opt/radius_dashboard/gerar_painel.py${NC}"
fi

# Verifica o arquivo HTML
if [ -f "/var/www/html/radius/index.html" ]; then
    SIZE=$(du -h /var/www/html/radius/index.html | cut -f1)
    echo -e "${GREEN}✅ Dashboard HTML: $SIZE${NC}"
else
    echo -e "${RED}❌ Dashboard HTML não encontrado${NC}"
fi

# Resumo
echo ""
echo "📊 Acesse o dashboard:"
echo -e "   ${BLUE}http://$DOMAIN:8080/radius/index.html${NC}"
echo -e "   ${BLUE}http://$DOMAIN:8080/${NC} (redireciona automaticamente)"
echo ""

echo "📁 Arquivos importantes:"
echo "   - Script: /opt/radius_dashboard/gerar_painel.py"
echo "   - HTML: /var/www/html/radius/index.html"
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
echo "   - Ver logs do dashboard: cat /var/log/radius_dashboard.log"
echo "   - Ver timer: systemctl status radius-dashboard.timer"
echo "   - Ver Nginx: systemctl status nginx"
echo ""

echo -e "${GREEN}✅ Instalação concluída!${NC}"
echo -e "${YELLOW}⚠️  Para acessar via HTTPS, configure um proxy reverso (Nginx Proxy Manager, Caddy, etc.)${NC}"
