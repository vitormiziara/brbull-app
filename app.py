import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta

# --- 1. CONFIGURAÇÃO GLOBAL ---
st.set_page_config(layout="wide", page_title="BrBull Pro Terminal", page_icon="🐂")

# Estilo CSS Customizado para parecer um Terminal Profissional
st.markdown("""
<style>
    .stMetric {
        background-color: #1E1E1E;
        padding: 15px;
        border-radius: 5px;
        border: 1px solid #333;
    }
    .stDataFrame {
        border: 1px solid #333;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. FUNÇÕES DE CÁLCULO (O CÉREBRO) ---

@st.cache_data(ttl=900) # Cache de 15 min para não travar
def pegar_dados(ticker, periodo="1y"):
    if not ticker.endswith(".SA"):
        ticker = f"{ticker}.SA"
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period=period)
        info = stock.info
        
        # Cálculos Técnicos Básicos
        df['SMA_20'] = df['Close'].rolling(window=20).mean()
        df['SMA_50'] = df['Close'].rolling(window=50).mean()
        
        # Cálculo RSI (IFR) 14 períodos
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        return df, info
    except:
        return None, None

def scanner_mercado(tickers):
    resultados = []
    # Barra de progresso visual
    progress_bar = st.progress(0)
    total = len(tickers)
    
    for i, ticker in enumerate(tickers):
        try:
            df, _ = pegar_dados(ticker, periodo="3mo")
            if df is not None and not df.empty:
                ultimo_preco = df['Close'].iloc[-1]
                ultimo_rsi = df['RSI'].iloc[-1]
                var_dia = ((df['Close'].iloc[-1] - df['Open'].iloc[-1]) / df['Open'].iloc[-1]) * 100
                
                sinal = "Neutro"
                if ultimo_rsi < 30: sinal = "🟢 COMPRA (Sobrevendido)"
                elif ultimo_rsi > 70: sinal = "🔴 VENDA (Sobrecomprado)"
                
                resultados.append({
                    "Ativo": ticker,
                    "Preço": ultimo_preco,
                    "Var %": var_dia,
                    "RSI (14)": ultimo_rsi,
                    "Sinal": sinal
                })
        except:
            pass
        progress_bar.progress((i + 1) / total)
    
    progress_bar.empty()
    return pd.DataFrame(resultados)

# --- 3. INTERFACE E NAVEGAÇÃO ---

st.sidebar.title("🐂 BrBull Pro")
menu = st.sidebar.radio("Navegação", ["Dashboard Ativo", "Radar de Oportunidades (Screener)", "Comparador"])

st.sidebar.markdown("---")
st.sidebar.info("Dados fornecidos via Yahoo Finance (15min delay)")

# --- PÁGINA 1: DASHBOARD ATIVO ---
if menu == "Dashboard Ativo":
    col1, col2 = st.columns([1, 3])
    with col1:
        ativo = st.text_input("Ticker:", value="PETR4").upper()
    
    df, info = pegar_dados(ativo)
    
    if df is not None:
        # Cabeçalho com Métricas
        p_atual = df['Close'].iloc[-1]
        p_ant = df['Close'].iloc[-2]
        var = ((p_atual - p_ant) / p_ant) * 100
        cor_var = "normal"
        
        st.title(f"{info.get('longName', ativo)}")
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Preço", f"R$ {p_atual:.2f}", f"{var:.2f}%")
        m2.metric("Máx 52 Semanas", f"R$ {info.get('fiftyTwoWeekHigh', 0):.2f}")
        m3.metric("P/L", f"{info.get('trailingPE', 'N/A')}")
        m4.metric("Dividend Yield", f"{info.get('dividendYield', 0)*100:.2f}%" if info.get('dividendYield') else "N/A")
        
        # Abas para organizar a informação
        tab1, tab2 = st.tabs(["📈 Análise Técnica", "📊 Fundamentos"])
        
        with tab1:
            # Gráfico Candlestick + Médias
            fig = go.Figure()
            fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='Preço'))
            fig.add_trace(go.Scatter(x=df.index, y=df['SMA_20'], line=dict(color='cyan', width=1), name='MMA 20'))
            fig.add_trace(go.Scatter(x=df.index, y=df['SMA_50'], line=dict(color='orange', width=1), name='MMA 50'))
            
            fig.update_layout(template="plotly_dark", height=500, margin=dict(l=0, r=0, t=30, b=0))
            st.plotly_chart(fig, use_container_width=True)
            
            # Gráfico RSI separado
            fig_rsi = go.Figure()
            fig_rsi.add_trace(go.Scatter(x=df.index, y=df['RSI'], line=dict(color='purple', width=2), name='RSI'))
            fig_rsi.add_hline(y=70, line_dash="dot", line_color="red")
            fig_rsi.add_hline(y=30, line_dash="dot", line_color="green")
            fig_rsi.update_layout(template="plotly_dark", height=200, title="IFR (RSI) - Força Relativa", margin=dict(l=0, r=0, t=30, b=0))
            st.plotly_chart(fig_rsi, use_container_width=True)

        with tab2:
            st.subheader("Dados da Empresa")
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                st.write(f"**Setor:** {info.get('sector', '-')}")
                st.write(f"**Indústria:** {info.get('industry', '-')}")
                st.write(f"**Funcionários:** {info.get('fullTimeEmployees', '-')}")
            with col_f2:
                st.write(f"**Descrição:** {info.get('longBusinessSummary', 'Sem descrição disponível.')[:500]}...")

    else:
        st.error("Ativo não encontrado.")

# --- PÁGINA 2: RADAR (SCREENER) ---
elif menu == "Radar de Oportunidades (Screener)":
    st.title("📡 Radar de Mercado (Blue Chips)")
    st.markdown("Analisa automaticamente uma cesta de ativos e busca setups de **RSI (IFR)**.")
    
    # Lista pré-definida para o demo (para não demorar muito carregando a bolsa toda)
    carteira_padrao = ["PETR4", "VALE3", "ITUB4", "BBDC4", "WEGE3", "BBAS3", "ABEV3", "JBSS3", "RENT3", "PRIO3"]
    
    if st.button("Escaniar Mercado Agora"):
        with st.spinner("Analisando indicadores técnicos..."):
            df_scan = scanner_mercado(carteira_padrao)
            
            # Formatação Condicional
            def color_rsi(val):
                if val < 30: return 'background-color: #154f18; color: white' # Verde
                if val > 70: return 'background-color: #631818; color: white' # Vermelho
                return ''

            st.dataframe(
                df_scan.style.applymap(color_rsi, subset=['RSI (14)'])
                .format({"Preço": "R$ {:.2f}", "Var %": "{:.2f}%", "RSI (14)": "{:.1f}"}),
                use_container_width=True,
                height=500
            )
    else:
        st.info("Clique no botão acima para iniciar o scan.")

# --- PÁGINA 3: COMPARADOR ---
elif menu == "Comparador":
    st.title("⚖️ Comparador de Rentabilidade")
    tickers_comp = st.text_input("Ativos (separados por vírgula)", "PETR4, VALE3, ^BVSP").upper()
    lista_comp = [t.strip() for t in tickers_comp.split(',')]
    
    if lista_comp:
        dados_comp = pd.DataFrame()
        for t in lista_comp:
            df_c, _ = pegar_dados(t)
            if df_c is not None:
                # Normalizando para base 100 para comparação justa
                dados_comp[t] = df_c['Close'] / df_c['Close'].iloc[0] * 100
        
        if not dados_comp.empty:
            fig_comp = px.line(dados_comp, x=dados_comp.index, y=dados_comp.columns, title="Performance Relativa (Base 100)")
            fig_comp.update_layout(template="plotly_dark", hovermode="x unified")
            st.plotly_chart(fig_comp, use_container_width=True)