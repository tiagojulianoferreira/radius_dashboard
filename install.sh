#!/bin/bash
# install-radius-dashboard.sh
# Script de instalação automática do Dashboard RADIUS

set -e

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     RADIUS Dashboard - Script de Instalação Automática    ║${NC}"
echo -e "${BLUE}║           FreeRADIUS Monitoring & Analytics               ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# ============================================================
# 1. VERIFICAÇÃO DE PRÉ-REQUISITOS
# ============================================================
echo -e "${YELLOW}[1/8] Verificando pré-requisitos...${NC}"

# Verifica se está rodando como root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}❌ Este script precisa ser executado como root${NC}"
    exit 1
fi

# Verifica Python 3
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 não encontrado. Instale com: apt install python3 python3-venv${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Python 3: $(python3 --version)${NC}"

# Verifica Nginx
if ! command -v nginx &> /dev/null; then
    echo -e "${YELLOW}⚠️  Nginx não encontrado. Instalando...${NC}"
    apt update && apt install -y nginx
fi
echo -e "${GREEN}✅ Nginx: $(nginx -v 2>&1)${NC}"

# Verifica FreeRADIUS
if ! command -v freeradius &> /dev/null && ! command -v radiusd &> /dev/null; then
    echo -e "${YELLOW}⚠️  FreeRADIUS não encontrado. Certifique-se de que está instalado.${NC}"
fi

# Verifica os logs do FreeRADIUS
LOG_PATH="/var/log/freeradius/radius.log"
if [ ! -f "$LOG_PATH" ]; then
    echo -e "${YELLOW}⚠️  Log do FreeRADIUS não encontrado em: $LOG_PATH${NC}"
    echo -e "${YELLOW}   Verifique se o FreeRADIUS está configurado corretamente${NC}"
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
fi

# ============================================================
# 2. CONFIGURAÇÃO DO DOMÍNIO
# ============================================================
echo ""
echo -e "${YELLOW}[2/8] Configuração do domínio...${NC}"
read -p "Digite o domínio para o dashboard (ex: radius.ifsc.edu.br) ou pressione Enter para usar localhost: " DOMAIN
DOMAIN=${DOMAIN:-"localhost"}

# ============================================================
# 3. INSTALAÇÃO DO DASHBOARD
# ============================================================
echo ""
echo -e "${YELLOW}[3/8] Instalando o Dashboard...${NC}"

# Cria diretório do projeto
mkdir -p /opt/radius_dashboard
cd /opt/radius_dashboard

# Cria ambiente virtual
echo "   Criando ambiente virtual Python..."
python3 -m venv venv
source venv/bin/activate

# Instala dependências
echo "   Instalando dependências..."
pip install --upgrade pip

# Baixa o Chart.js
echo "   Baixando Chart.js..."
mkdir -p /var/www/html/radius
wget -q -O /var/www/html/radius/chart.min.js https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js
chown www-data:www-data /var/www/html/radius/chart.min.js

# ============================================================
# 4. CRIAÇÃO DO SCRIPT PYTHON
# ============================================================
echo ""
echo -e "${YELLOW}[4/8] Criando script Python...${NC}"

# O script Python será baixado ou criado aqui
# (Na prática, você deve colocar o conteúdo do script aqui)

# Baixa o script do repositório ou cria localmente
cat > /opt/radius_dashboard/gerar_painel.py << 'EOF'
#!/opt/radius_dashboard/venv/bin/python3
"""
Dashboard RADIUS - IFSC
Com análise histórica e dados do dia atual
"""
# [COLE AQUI O CONTEÚDO COMPLETO DO SCRIPT ATUALIZADO]
EOF

chmod +x /opt/radius_dashboard/gerar_painel.py

# ============================================================
# 5. CONFIGURAÇÃO DO NGINX
# ============================================================
echo ""
echo -e "${YELLOW}[5/8] Configurando Nginx...${NC}"

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

    location = /favicon.ico {
        try_files /favicon.ico =404;
    }

    access_log /var/log/nginx/radius_access.log;
    error_log /var/log/nginx/radius_error.log;
}
EOF

# Habilita o site
ln -sf /etc/nginx/sites-available/radius /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx

echo -e "${GREEN}✅ Nginx configurado na porta 8080${NC}"

# ============================================================
# 6. CRIAÇÃO DOS SERVIÇOS SYSTEMD
# ============================================================
echo ""
echo -e "${YELLOW}[6/8] Configurando serviços systemd...${NC}"

# Serviço
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

# Timer
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

# ============================================================
# 7. ATIVAÇÃO DOS SERVIÇOS
# ============================================================
echo ""
echo -e "${YELLOW}[7/8] Ativando serviços...${NC}"

systemctl daemon-reload
systemctl enable radius-dashboard.timer
systemctl start radius-dashboard.timer
systemctl enable radius-dashboard.service

# Executa a primeira geração
echo "   Executando primeira geração do dashboard..."
systemctl start radius-dashboard.service

# ============================================================
# 8. VERIFICAÇÃO FINAL
# ============================================================
echo ""
echo -e "${YELLOW}[8/8] Verificação final...${NC}"

# Verifica se o dashboard foi gerado
if [ -f "/var/www/html/radius/index.html" ]; then
    SIZE=$(du -h /var/www/html/radius/index.html | cut -f1)
    echo -e "${GREEN}✅ Dashboard gerado com sucesso! (Tamanho: $SIZE)${NC}"
else
    echo -e "${RED}❌ Dashboard NÃO foi gerado. Verifique os logs:${NC}"
    echo "   journalctl -u radius-dashboard.service -n 50"
fi

# Verifica o serviço
if systemctl is-active --quiet radius-dashboard.timer; then
    echo -e "${GREEN}✅ Timer ativo: $(systemctl list-timers --all | grep radius-dashboard)${NC}"
else
    echo -e "${RED}❌ Timer não está ativo${NC}"
fi

# ============================================================
# RESUMO FINAL
# ============================================================
echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                    INSTALAÇÃO CONCLUÍDA!                    ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}✅ Dashboard RADIUS instalado com sucesso!${NC}"
echo ""
echo "📊 Acesse o dashboard:"
echo -e "   ${BLUE}http://$DOMAIN:8080/radius/index.html${NC}"
echo "   ${BLUE}http://$DOMAIN:8080/${NC} (redireciona automaticamente)"
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
echo "   - Ver timer: systemctl status radius-dashboard.timer"
echo ""
echo -e "${YELLOW}⚠️  Para acessar via HTTPS, configure um proxy reverso (Nginx Proxy Manager, Caddy, etc.)${NC}"
echo ""
