# RADIUS Dashboard - FreeRADIUS Monitoring

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![Nginx](https://img.shields.io/badge/Nginx-1.18+-green.svg)](https://nginx.org)

Dashboard para monitoramento de autenticações FreeRADIUS com análise histórica, desduplicação de eventos, identificação de fabricantes e métricas de impacto em usuários.

## 📊 Funcionalidades

### 📈 Métricas Gerais
- Total de autenticações bem-sucedidas e rejeitadas
- Taxa de falhas bruta e **real (desduplicada)**
- Período dos dados analisados
- **Usuários únicos impactados** (histórico e hoje)

### 👤 Análise de Impacto em Usuários
- **Usuários afetados por falhas** (únicos)
- Percentual de impacto sobre usuários ativos
- Lista detalhada com:
  - Nome do usuário
  - MAC Address do dispositivo
  - Tipos de erro (separados por pipe)
- Usuários com múltiplas falhas (3+)
- Usuários com problemas persistentes (10+)

### 🔄 Desduplicação Inteligente
- Consolida eventos repetidos do mesmo usuário
- Janela de tempo configurável (5 minutos)
- Eliminação de ruído de logs
- Redução típica de 30-40% nas falhas

### 📱 Análise por Fabricante
- Identificação do fabricante do dispositivo via MAC Address (OUI)
- Suporte para MACs randomizados (iOS/Android)
- Gráfico de pizza com distribuição de falhas

### 🔒 Análise de Erros
- Classificação por tipo de erro:
  - Senha incorreta
  - Erro de Certificado CA
  - Erro TLS
  - Erro TLS (versão)
  - Erro MS-CHAP
  - Usuário inválido

### 📅 Análise Temporal
- Falhas por hora do dia
- Falhas por dia da semana
- Série histórica (últimos 60 dias)
- Comparativo: dados brutos vs desduplicados

### 👤 Análise por Usuário
- Top 15 usuários com mais falhas
- Identificação de padrões de comportamento

### 📊 Dados do Dia Atual
- Visualização separada das estatísticas do dia
- Usuários impactados no dia
- Comparação rápida com histórico

## 🛠️ Stack Tecnológica

### Backend
- **Python 3.8+** - Processamento de logs
- **FreeRADIUS** - Fonte dos dados
- **Systemd** - Agendamento e serviços
- **Pickle** - Cache de logs processados

### Frontend
- **HTML5 + CSS3** - Interface responsiva
- **Chart.js** - Visualização de dados
- **JavaScript** - Gráficos interativos

### Infraestrutura
- **Nginx** - Servidor web (porta 8080)
- **Nginx Proxy Manager** - Proxy reverso (opcional)
- **Logrotate** - Rotação de logs

## 📋 Pré-requisitos

- **Ubuntu/Debian** (ou derivados)
- **FreeRADIUS** instalado e configurado
- **Python 3.8+** com venv
- **Nginx** instalado
- **Acesso root** para instalação
- **Porta 8080** disponível

## 🚀 Instalação

### Instalação Automática (Recomendado)

```bash
# Baixe e execute o script de instalação
curl -sSL https://raw.githubusercontent.com/tiagojulianoferreira/radius_dashboard/main/install.sh | sudo bash
