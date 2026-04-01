import streamlit as st
import pandas as pd
from datetime import datetime

# --- INICIALIZAÇÃO OBRIGATÓRIA ---
if 'historico_passagens' not in st.session_state:
    st.session_state.historico_passagens = []

if 'lista_voos_atual' not in st.session_state:
    st.session_state.lista_voos_atual = []

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="Hércules Operacional", layout="wide")

# --- FUNÇÕES DE CÁLCULO (MANTIDAS INTEGRALMENTE) ---
def arredondar_hercules_valor(valor):
    valor_int = int(valor)
    resto = valor_int % 100
    base = (valor_int // 100) * 100
    return float(base) if resto <= 50 else float(base + 100)

def arredondar_minutos_5(minutos_total):
    horas = int(minutos_total // 60)
    minutos = int(minutos_total % 60)
    minutos_final = 5 * round(minutos / 5)
    if minutos_final == 60:
        horas += 1
        minutos_final = 0
    return f"{horas:02d}h{minutos_final:02d}min"

def converter_tempo_pela_velocidade(tempo_str_100kt, vel_real):
    try:
        t = tempo_str_100kt.replace('min', '').replace('.', '').replace('h', ':')
        partes = t.split(':')
        minutos_base = (int(partes[0]) * 60) + int(partes[1])
        if minutos_base <= 0: return "00h00min"
        minutos_reais = minutos_base * (100 / vel_real)
        return arredondar_minutos_5(minutos_reais)
    except: return "00h00min"

# --- INTERFACE ---
aba_orc, aba_disp, aba_pass = st.tabs(["💰 ORÇAMENTO", "📍 DISPONIBILIDADE/BASES", "📋 PASSAGEM DE SERVIÇO"])

# --- ABA 💰 ORÇAMENTO (MANTIDA SEM ALTERAÇÕES) ---
with aba_orc:
    with st.sidebar:
        st.header("⚙️ Configuração")
        dist_mn = st.number_input("Distância Total (MN)", value=0.0)
        
        is_uti = st.checkbox("Voo UTI")
        if is_uti:
            has_med = st.checkbox("Equipe Médica (R$ 8.500)", value=True)
            has_ao = st.checkbox("Ambulância Origem (R$ 1.500)")
            has_ad = st.checkbox("Ambulância Destino (R$ 1.500)")
        else:
            has_med, has_ao, has_ad = False, False, False
        
        st.divider()
        n_pernas = st.number_input("Pernas Mínimas", value=0, step=1)
        n_pernoites = st.number_input("Pernoites", value=0, step=1)
        
        st.divider()
        pct_comissao = st.number_input("% Comissão", value=0.0)
        n_ajuste = st.number_input("% Ajuste Final", value=0.0)
        outras_taxas = st.number_input("Outras Taxas (R$)", value=0.0, step=100.0)

    st.subheader("📅 Cronograma de Voo")
    df_grid = st.data_editor(
        pd.DataFrame([{"Data": datetime.now().strftime('%d/%m'), "Origem": "", "Destino": "", "Tempo": "03:45h"}]), 
        num_rows="dynamic", use_container_width=True
    )

    modelos_base = [
        {"id": "jato", "nome": "CITATION 560 ULTRA", "km_padrão": 47.0, "vel": 340, "p_min": 5000.0, "p_exec": 5000.0},
        {"id": "b200", "nome": "KING AIR B200", "km_padrão": 36.0, "vel": 240, "p_min": 4500.0, "p_exec": 4000.0},
        {"id": "c90", "nome": "KING AIR C90", "km_padrão": 33.0, "vel": 220, "p_min": 4000.0, "p_exec": 4000.0}
    ]

    cols_orc = st.columns(3)
    for i, m in enumerate(modelos_base):
        with cols_orc[i]:
            km_edit = st.number_input(f"Valor KM - {m['nome']}", value=m['km_padrão'], key=f"km_{m['id']}")
            dist_km = max(dist_mn * 1.852, (1000 if "CITATION" in m['nome'] else 800)) if dist_mn > 0 else 0
            
            # Lógica Pernoite Diferenciada
            val_pern = 6000.0 if is_uti else m['p_exec']
            
            # Cálculo Final
            v_net = arredondar_hercules_valor(((km_edit * dist_km) + (n_pernas * m['p_min']) + (n_pernoites * val_pern) + outras_taxas + ((8500 if has_med else 0) + (1500 if has_ao else 0) + (1500 if has_ad else 0))) * (1 + n_ajuste/100))
            v_fin = arredondar_hercules_valor(v_net / (1 - (pct_comissao/100))) if pct_comissao > 0 else v_net
            st.metric("Valor Total", f"R$ {v_fin:,.2f}")

            # Geração de Texto WhatsApp
            cron_txt = ""
            for _, r in df_grid.iterrows():
                if r['Origem'] and r['Destino']:
                    t_c = converter_tempo_pela_velocidade(r['Tempo'], m['vel'])
                    if is_uti: cron_txt += f"{r['Origem'].upper()} > {r['Destino'].upper()} - {t_c} de voo.\n"
                    else: cron_txt += f"{r['Data']}\n{r['Origem'].upper()} > {r['Destino'].upper()} - {t_c} de voo.\n\n"

            if is_uti:
                # MODELO UTI
                amb = "Ambulância terrestre de *ORIGEM E DESTINO* inclusa." if has_ao and has_ad else ("Ambulância terrestre de *ORIGEM* inclusa no orçamento." if has_ao else ("Ambulância terrestre de *DESTINO* inclusa no orçamento." if has_ad else "Não inclusa no orçamento."))
                msg = f"*{m['nome']} - UTI AÉREA*\n\n{cron_txt}1 Médico + 1 Enfermeiro\n1 paciente + {2 if 'C90' not in m['nome'] else 1} acompanhante(s)\n{amb}\nValor: R$ {v_fin:,.2f}\n\n"
            else:
                # MODELO EXECUTIVO
                pax = "8 passageiros" if "CITATION" in m['nome'] else ("7/8 passageiros" if "B200" in m['nome'] else "6 passageiros")
                msg = f"*{m['nome']}*\n\n{cron_txt}Capacidade: {pax}\nValor: R$ {v_fin:,.2f}\n\n"
            
            msg += f"*VALOR COMISSIONADO ({pct_comissao}%)*" if pct_comissao > 0 else "*VALOR NET*"
            st.code(msg, language="markdown")

import streamlit as st
import pandas as pd
from datetime import datetime

# --- 1. CONFIGURAÇÃO E ESTILO ---

st.markdown("""
    <style>
    .titulo-base { color: #888; font-size: 0.95em; text-transform: uppercase; letter-spacing: 2px; text-align: center; margin-bottom: 20px; font-weight: bold; }
    .aero-card { background-color: #1a1a1a; padding: 12px; border-radius: 10px; margin-bottom: 10px; text-align: center; border: 1px solid #333; color: white; font-weight: bold; min-height: 80px; display: flex; flex-direction: column; justify-content: center; }
    .aero-maint { background-color: #991b1b; border: 1px solid #ef4444; box-shadow: 0px 0px 10px rgba(239, 68, 68, 0.3); }
    .motivo-txt { color: #ffcccc; font-size: 0.75em; font-weight: normal; display: block; margin-top: 5px; line-height: 1.1; }
    </style>
""", unsafe_allow_html=True)

# --- 2. INICIALIZAÇÃO DE DADOS ---
if 'frota' not in st.session_state:
    st.session_state.frota = [
        {"Prefixo": "PR-CSF", "Base": "CURITIBA", "Maint": False, "Motivo": ""},
        {"Prefixo": "PR-BEE", "Base": "CURITIBA", "Maint": False, "Motivo": ""},
        {"Prefixo": "PS-HTX", "Base": "CURITIBA", "Maint": False, "Motivo": ""},
        {"Prefixo": "PR-FGQ", "Base": "CURITIBA", "Maint": False, "Motivo": ""},
        {"Prefixo": "PS-TXH", "Base": "CURITIBA", "Maint": False, "Motivo": ""},
        {"Prefixo": "PS-TAH", "Base": "CURITIBA", "Maint": False, "Motivo": ""},
        {"Prefixo": "PS-JPP", "Base": "CURITIBA", "Maint": False, "Motivo": ""},
        {"Prefixo": "PS-ARI", "Base": "CURITIBA", "Maint": False, "Motivo": ""},
        {"Prefixo": "PT-LZH", "Base": "CURITIBA", "Maint": False, "Motivo": ""},
        {"Prefixo": "PS-HTA", "Base": "SALVADOR", "Maint": False, "Motivo": ""},
        {"Prefixo": "PR-IZQ", "Base": "BELO HORIZONTE", "Maint": False, "Motivo": ""},
        {"Prefixo": "PS-FMG", "Base": "BELO HORIZONTE", "Maint": False, "Motivo": ""},
        {"Prefixo": "PP-JVF", "Base": "BELÉM", "Maint": False, "Motivo": ""}
    ]

if 'historico_passagens' not in st.session_state:
    st.session_state.historico_passagens = []
if 'lista_voos_atual' not in st.session_state:
    st.session_state.lista_voos_atual = []

# --- 3. DEFINIÇÃO DAS ABAS ---

with aba_disp:
    st.write("### ✈️ Localização e Status da Frota")
    bases_lista = ["CURITIBA", "SALVADOR", "BELO HORIZONTE", "BELÉM"]
    cols = st.columns(4)

    for i, base in enumerate(bases_lista):
        with cols[i]:
            st.markdown(f'<p class="titulo-base">{base}</p>', unsafe_allow_html=True)
            aeros = [a for a in st.session_state.frota if a['Base'] == base]
            for a in aeros:
                tem_servico = a.get('Motivo', "") != ""
                classe = "aero-card aero-maint" if (a['Maint'] or tem_servico) else "aero-card"
                
                texto_card = f"<b>{a['Prefixo']}</b>"
                if tem_servico:
                    texto_card += f'<span class="motivo-txt">{a["Motivo"]}</span>'
                elif a['Maint']:
                    texto_card += f'<span class="motivo-txt">MANUTENÇÃO</span>'
                
                st.markdown(f'<div class="{classe}">{texto_card}</div>', unsafe_allow_html=True)

    st.divider()
    st.write("### ⚙️ Gestão de Frotas")
    with st.container():
        c1, c2, c3 = st.columns(3)
        a_sel = c1.selectbox("Aeronave", [a["Prefixo"] for a in st.session_state.frota], key="gestao_aero")
        a_atual = next(a for a in st.session_state.frota if a["Prefixo"] == a_sel)
        nova_base = c2.selectbox("Mover para Base", bases_lista, index=bases_lista.index(a_atual["Base"]))
        novo_status = c3.selectbox("Status de Disponibilidade", ["DISPONÍVEL", "MANUTENÇÃO", "CARGA"])
        
        if st.button("Confirmar Atualização de Frota", use_container_width=True):
            for aero in st.session_state.frota:
                if aero["Prefixo"] == a_sel:
                    aero["Base"] = nova_base
                    aero["Maint"] = (novo_status != "DISPONÍVEL")
                    aero["Motivo"] = "" if novo_status == "DISPONÍVEL" else novo_status
            st.rerun()

with aba_pass:

    c1, c2, c3 = st.columns(3)
    data_ps = c1.date_input("Data:", datetime.now())
    sai_ps = c2.selectbox("Saindo do Plantão:", ["RAFAEL", "GABRIEL", "MATEUS", "CAIO"])
    ent_ps = c3.selectbox("Entrando no Plantão:", ["RAFAEL", "GABRIEL", "MATEUS", "CAIO"], index=1)

    st.divider()
    st.write("### ✈️ Inserir Voo em Operação")
    with st.container(border=True):
        f1, f2 = st.columns(2)
        prefixo_v = f1.selectbox("Selecione a Aeronave:", [a["Prefixo"] for a in st.session_state.frota])
        servico_v = f2.selectbox("Serviço:", ["EXECUTIVO", "UTI", "CARGA"])

        detalhes_voo = ""
        topicos_obs = []

        if servico_v == "EXECUTIVO":
            ce1, ce2 = st.columns(2)
            cliente = ce1.text_input("Nome do Cliente:")
            trecho = ce2.text_input("Trecho:")
            obs_exec = st.text_area("Observações (Uma por linha):")
            if cliente and trecho:
                detalhes_voo = f"EXECUTIVO | {cliente.upper()} | {trecho.upper()}"
                topicos_obs = [f"• {linha.strip()}" for linha in obs_exec.split('\n') if linha.strip()]

        elif servico_v == "UTI":
            cu1, cu2 = st.columns(2)
            contratante = cu1.text_input("Contratante:")
            paciente = cu2.text_input("Nome do Paciente:")
            cu3, cu4 = st.columns(2)
            origem = cu3.text_input("Origem:")
            destino = cu4.text_input("Destino:")
            obs_uti = st.text_area("Observações da UTI (Uma por linha):")
            if paciente:
                detalhes_voo = f"UTI | {contratante.upper()} | PAC: {paciente.upper()}"
                topicos_obs = [f"PACIENTE: {paciente.upper()}", f"ORIGEM: {origem.upper()}", f"DESTINO: {destino.upper()}"] + [f"• {linha.strip()}" for linha in obs_uti.split('\n') if linha.strip()]

        elif servico_v == "CARGA":
            detalhes_voo = "OPERAÇÃO DE CARGA"
            obs_carga = st.text_area("Observações da Carga:")
            topicos_obs = [f"• {linha.strip()}" for linha in obs_carga.split('\n') if linha.strip()]

        if st.button("➕ ADICIONAR VOO À LISTA"):
            if detalhes_voo:
                st.session_state.lista_voos_atual.append({"prefixo": prefixo_v, "servico": servico_v, "resumo_card": detalhes_voo, "topicos": topicos_obs})
                st.rerun()

    if st.session_state.lista_voos_atual:
        st.write("---")
        for i, v in enumerate(st.session_state.lista_voos_atual):
            st.info(f"{i+1}. {v['prefixo']} - {v['resumo_card']}")
        if st.button("🗑️ Limpar Lista"):
            st.session_state.lista_voos_atual = []
            st.rerun()

    st.divider()
    if st.button("💾 FINALIZAR E SALVAR PASSAGEM", use_container_width=True):
        if st.session_state.lista_voos_atual:
            for v_salvo in st.session_state.lista_voos_atual:
                for aero in st.session_state.frota:
                    if aero["Prefixo"] == v_salvo["prefixo"]:
                        aero["Maint"] = True
                        aero["Motivo"] = v_salvo["resumo_card"]
            st.session_state.historico_passagens.append({"data": data_ps.strftime("%d/%m/%Y"), "de": sai_ps, "para": ent_ps, "voos": st.session_state.lista_voos_atual.copy()})
            st.session_state.lista_voos_atual = []
            st.success("Passagem Salva!")
            st.rerun()

    st.write("### 📂 Histórico de Passagens")
    for h in reversed(st.session_state.historico_passagens):
        with st.expander(f"Passagem {h['data']} - {h['de']} ➔ {h['para']}"):
            for v in h['voos']:
                st.markdown(f"**{v['prefixo']} | {v['resumo_card']}**")
                for t in v['topicos']: st.write(t)
                st.divider()
