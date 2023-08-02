import random
import requests
import time
import pytz
from dateutil import parser
import sqlite3
import pandas as pd
from itertools import product
import streamlit as st



valor_inicial = 0.10


# Aqui está configurado o layout da página.
st.set_page_config(layout="wide")

# Esta função éresponsávelpor destacar as cores do 0;
def destacar_ocorrencia_zero(val):
    if val == 0:
        return 'background-color: yellow'
    else:
        return ''

# Defina a função para exibir o DataFrame com o estilo aplicado
def exibir_dataframe_com_estilo(df, slot):
    styled_df = df.style.applymap(destacar_ocorrencia_zero, subset='occurrence')
    slot.dataframe(styled_df)

def format_one_decimal(value):
    return f"{value:.1f}"

pd.options.display.float_format = "{:,.0f}".format

# Aqui estão as colunas com os espaços vazios reservadoas parao dataframe.
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.header("DataFrame future_df:")
    empty_slot1 = st.empty()

with col2:
    st.header("DataFrame Cores_branco:")
    empty_slot2 = st.empty()

with col3:
    st.header("DataFrame Cores_vermelho:")
    empty_slot3 = st.empty()

with col4:
    st.header("DataFrame Cores_preto:")
    empty_slot4 = st.empty()



col5, col6, col7, col8 = st.columns(4)
empty_slot16 = col5.empty()
empty_slot5 = col6.empty()
empty_slot6 = col7.empty()
empty_slot7 = col8.empty()

col10, col11, col12, col13 = st.columns(4)
empty_slot8 = col10.empty()
empty_slot9 = col11.empty()
empty_slot10 = col12.empty()
empty_slot11 = col13.empty()

col14, col15, col16, col17 = st.columns(4)
empty_slot12 = col17.empty()
empty_slot13 = col14.empty()
empty_slot14 = col15.empty()
empty_slot15 = col16.empty()


message_slot = st.empty()





def fetch_recent_data():
    try:
        response = requests.get("https://blaze.com/api/roulette_games/recent", timeout=10)
        response.raise_for_status()  # Check if the request was successful
        data = response.json()
        sorted_data = sorted(data, key=lambda x: x['created_at'], reverse=True)
        return sorted_data
    except requests.exceptions.RequestException as e:
        st.error("Error in the request: " + str(e))
        st.experimental_rerun()  # Reiniciar a aplicação

# Função para converter o horário UTC para o horário de Brasília
def convert_to_brasilia_time(created_at):
    fuso_horario_utc = pytz.timezone('UTC')
    fuso_horario_brasilia = pytz.timezone('America/Sao_Paulo')
    horario_utc = parser.isoparse(created_at)
    horario_utc = horario_utc.replace(tzinfo=fuso_horario_utc)
    horario_brasilia = horario_utc.astimezone(fuso_horario_brasilia)
    return horario_brasilia.strftime("%Y-%m-%d %H:%M:%S")

# Função para criar a tabela se ela ainda não existir no banco de dados
def create_table_if_not_exists():
    connection = sqlite3.connect("dados.db")
    cursor = connection.cursor()

    # Define a estrutura da tabela
    create_table_query = """
    CREATE TABLE IF NOT EXISTS dados (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        color1 TEXT,
        color2 TEXT,
        color3 TEXT,
        color4 TEXT,
        color5 TEXT,
        numero1 INTEGER,
        numero2 INTEGER,
        numero3 INTEGER,
        numero4 INTEGER,
        numero5 INTEGER,
        server_seed TEXT,
        created_at TEXT
    );
    """
    cursor.execute(create_table_query)
    connection.commit()
    connection.close()

# Função para verificar se a server_seed já existe no banco de dados
def is_server_seed_exists(server_seed):
    connection = sqlite3.connect("dados.db")
    cursor = connection.cursor()
    cursor.execute("SELECT COUNT(*) FROM dados WHERE server_seed=?", (server_seed,))
    count = cursor.fetchone()[0]
    connection.close()
    return count > 0

# Função para salvar os dados no banco de dados e analisar/predizer sequências
def save_data_and_analyze(dados_api):
    novo_server_seed = dados_api[0]["server_seed"]
    if is_server_seed_exists(novo_server_seed):
        return

    color1, color2, color3, color4, color5, color6 = [d["color"] for d in dados_api[:6]]
    numero1, numero2, numero3, numero4, numero5, numero6 = [d["roll"] for d in dados_api[:6]]
    horario_brasilia = convert_to_brasilia_time(dados_api[0]["created_at"])

    connection = sqlite3.connect("dados.db")
    cursor = connection.cursor()

    # Insert the data into the table
    insert_data_query = """
    INSERT INTO dados (color1, color2, color3, color4, color5, numero1, numero2, numero3, numero4, numero5, server_seed, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    cursor.execute(insert_data_query, (color1, color2, color3, color4,color5, numero1, numero2, numero3, numero4,numero5, novo_server_seed, horario_brasilia))

    connection.commit()
    connection.close()

    # Analyze and predict sequences after obtaining new data
    analyze_and_predict_sequences(color1,color2,color3, numero1, novo_server_seed,horario_brasilia)

resultados_resumo = pd.DataFrame()  # Inicialize resultados_resumo como um DataFrame vazio

total_ganhou = 0
total_perdeu = 0
maior_sequencia_ganhou = 0
maior_sequencia_perdeu = 0
# Variáveis para controlar a sequência atual de "Perdeu" e "Ganhou"
sequencia_atual_perdeu = 0
sequencia_atual_ganhou = 0

# Função para contar a sequência consecutiva de "Perdeu" ou "Ganhou"
def contar_sequencia_consecutiva(resultados, resultado_alvo):
    sequencia_atual = 0
    maior_sequencia = 0

    for resultado in resultados:
        if resultado == resultado_alvo:
            sequencia_atual += 1
            maior_sequencia = max(maior_sequencia, sequencia_atual)
        else:
            sequencia_atual = 0

    return maior_sequencia

# Função para analisar e predizer sequências
def analyze_and_predict_sequences(color1, color2,color3, numero1, novo_server_seed, horario_brasilia):
    global resultados_resumo, total_ganhou, total_perdeu, maior_sequencia_ganhou, maior_sequencia_perdeu, sequencia_atual_ganhou, sequencia_atual_perdeu

    connection = sqlite3.connect("dados.db")
    df = pd.read_sql_query("SELECT numero1, numero2, numero3, numero4, numero5 FROM dados", connection)
    connection.close()

    # Get the most recent sequence
    latest_sequence = df.iloc[-1].values.tolist()

    latest_sequence_str = ",".join(map(str, map(int, latest_sequence)))  # Convert to integers before joining

    # Format the numbers in the DataFrame with one decimal place for columns 'numero1' to 'numero5'
    df.iloc[:, 0:-1] = df.iloc[:, 0:-1].applymap(lambda x: round(x, 1))


    occurrence_counts = df[df[df.columns].eq(latest_sequence).all(1)].shape[0]

    all_possible_numbers = list(range(15))
    all_possible_numbers_int = list(map(int, all_possible_numbers))
    latest_sequence_int = list(map(int, latest_sequence))

    sequences = list(product(all_possible_numbers_int, [latest_sequence_int[0]], [latest_sequence_int[1]], [latest_sequence_int[2]], [latest_sequence_int[3]]))
    latest_sequence_str = ",".join(map(str, latest_sequence_int))

    future_df = pd.DataFrame(sequences, columns=['numero0', 'numero1', 'numero2', 'numero3','numero4'])

    # Format the numbers in the future_df DataFrame with one decimal place for columns 'numero1' to 'numero5'
    future_df.iloc[:, 1:-1] = future_df.iloc[:, 1:-1].applymap(lambda x: round(x, 1))

    future_df['numero5'] = int(round(latest_sequence[4]))

    future_occurrence_counts = []
    for seq in sequences:
        occurrence_count = df[df[df.columns].eq(seq).all(1)].shape[0]
        future_occurrence_counts.append(occurrence_count)

    future_df['occurrence'] = future_occurrence_counts

    red_occurrences = future_df[future_df['numero0'].isin(range(1, 8))]['occurrence'].value_counts().get(0, 0)
    black_occurrences = future_df[future_df['numero0'].isin(range(8, 16))]['occurrence'].value_counts().get(0, 0)



        # VVV - P
    if color1 == 1 and color2 == 1 and color3 == 1:
        dica2 = 1
    # PPP - V
    elif color1 == 2 and color2 == 2 and color3 == 2:
        dica2 = 2
    # VVP - V
    elif color1 == 1 and color2 == 1 and color3 == 2:
        dica2 = 2
    elif color1 == 2 and color2 == 2 and color3 == 1:
        dica2 = 1
    elif color1 == 1 and color2 == 2 and color3 == 2:
        dica2 = 1
    elif color1 == 2 and color2 == 1 and color3 == 1:
        dica2 = 2
    elif color1 == 1 and color2 == 2 and color3 == 1:
        dica2 = 2
    elif color1 == 2 and color2 == 1 and color3 == 2:
        dica2 = 1
    elif color2 == 0:
        dica2 = 2
    elif color1 == 0:
        dica2 = 1
    elif color3 == 0:
        dica2 = 2
    else:
        dica2 = None


    if black_occurrences > red_occurrences:
        dica = 2
    elif black_occurrences < red_occurrences:
        dica = 1
    else:
        dica = 1


    if maior_sequencia_perdeu <= 4:
        dica_geral= dica2
    
    elif maior_sequencia_perdeu ==5:
        dica_geral= dica

    elif maior_sequencia_perdeu >5:
        dica_geral= dica2        
    


    total_red_occurrences = future_df[future_df['numero0'].isin(range(1, 7))]['occurrence'].sum()
    total_black_occurrences = future_df[future_df['numero0'].isin(range(8, 15))]['occurrence'].sum()

    percentage_red_occurrences = (red_occurrences / 14) * 100 if total_red_occurrences > 0 else 0
    percentage_black_occurrences = (black_occurrences / 14) * 100 if total_black_occurrences > 0 else 0



    Cores_branco = future_df.loc[future_df['numero0'] == 0]
    Cores_vermelho = future_df.loc[(future_df['numero0'] >= 1) & (future_df['numero0'] <= 7)]
    Cores_preto = future_df.loc[future_df['numero0'] >= 8]


    if 'ultimos_resultados_dica' not in globals():
        globals()['ultimos_resultados_dica'] = []
    ultimos_resultados_dica = globals()['ultimos_resultados_dica']
    ultimos_resultados_dica.append(dica_geral)

    resultado = None
    if len(ultimos_resultados_dica) >= 2:
        if ultimos_resultados_dica[-2] == color1:
            resultado = "Ganhou"
            sequencia_atual_ganhou += 1
            sequencia_atual_perdeu = 0  # Reiniciar a sequência de "Perdeu"
        else:
            resultado = "Perdeu"
            sequencia_atual_perdeu += 1
            sequencia_atual_ganhou = 0
            
            
    resumo = pd.DataFrame()
    resumo['Dica'] = [dica_geral]
    resumo['Cor'] = [color1]
    resumo['Numero'] = [numero1]
    resumo['Resultado'] = [resultado]
    resumo['%Vermelho'] = [percentage_red_occurrences]
    resumo['%Preto'] = [percentage_black_occurrences]
    resumo['Val_Apostado'] = [None]  # Adicione seus valores desejados aqui
    resumo['Horário'] = [horario_brasilia]  # Adicione seus valores desejados aqui
    resumo['Server_Seed'] = [novo_server_seed]  # Adicione seus valores desejados aqui
    resumo['Vazio3'] = [None]  # Adicione seus valores desejados aqui
    resumo['occurrence'] = [None]  # Adicione a coluna 'occurrence' ao DataFrame resumo

    # Armazena o DataFrame 'resumo' na lista de resultados
    resultados_resumo = pd.concat([resultados_resumo, resumo], ignore_index=True)

    # Contar as ocorrências de "Ganhou" e "Perdeu" na coluna "Resultado"
    counts = resultados_resumo['Resultado'].value_counts()
    total_ganhou = counts.get("Ganhou", 0)
    total_perdeu = counts.get("Perdeu", 0)


    counts = resultados_resumo['Resultado'].value_counts()
    total_ganhou = counts.get("Ganhou", 0)
    total_perdeu = counts.get("Perdeu", 0)

    # Calcular a maior sequência de "Ganhou" e "Perdeu" consecutiva
    maior_sequencia_ganhou = max(maior_sequencia_ganhou, contar_sequencia_consecutiva(resultados_resumo['Resultado'], "Ganhou"))
    maior_sequencia_perdeu = max(maior_sequencia_perdeu, contar_sequencia_consecutiva(resultados_resumo['Resultado'], "Perdeu"))

    # Ordenar novamente o DataFrame resultados_resumo pela coluna "horario" e redefinir o índice
    resultados_resumo = resultados_resumo.sort_values(by=['Horário'], ascending=False)
    resultados_resumo.reset_index(drop=True, inplace=True)


    empty_slot5.metric("Dica:", dica)
    empty_slot6.metric("Dica2:", dica2)
    empty_slot7.metric("Derrotas em sequência", sequencia_atual_perdeu)
    empty_slot8.metric("maior_sequencia_ganhou:", maior_sequencia_ganhou)
    empty_slot9.metric("maior_sequencia_perdeu:", maior_sequencia_perdeu)
    empty_slot10.metric("Número sorteado", numero1)
    empty_slot11.metric("Dica", dica_geral)
    empty_slot12.metric("Ganhou", total_ganhou)
    empty_slot13.metric(" Perdeu", total_perdeu)
    empty_slot14.metric("Porcentagem de 0 em Cores_vermelho:", f"{percentage_red_occurrences:.2f}%")
    empty_slot15.metric("Porcentagem de 0 em Cores_preto:", f"{percentage_black_occurrences:.2f}%")
    empty_slot16.metric("Vitórias em sequência", sequencia_atual_ganhou)    


    #Dataframes
    exibir_dataframe_com_estilo(future_df, empty_slot1)
    exibir_dataframe_com_estilo(Cores_branco, empty_slot2)
    exibir_dataframe_com_estilo(Cores_vermelho, empty_slot3)
    exibir_dataframe_com_estilo(Cores_preto, empty_slot4)     
    exibir_dataframe_com_estilo(resultados_resumo, message_slot)


    return future_df, resultado, resumo


REQUEST_DELAY_SECONDS = 28  # Defina um valor adequado com base no limite de taxa da API

# Variável para contar o número total de requisições feitas
total_request_count = 0

# Variável para controlar a obtenção do primeiro dado
first_data_obtained = False

# Função para verificar a semente do servidor e buscar os dados recentes
def check_server_seed():
    global total_request_count, first_data_obtained
    create_table_if_not_exists()

    previous_server_seeds = []
    recent_data_count = 0  # Para contar quantos dados recentes foram obtidos

    while True:
        try:
            data = fetch_recent_data()

            if data:
                # Incrementa o contador de requisições
                total_request_count += 1

                current_server_seed = data[0]["server_seed"]

                if current_server_seed not in previous_server_seeds:
                    if not first_data_obtained:
                        # Ignora o primeiro dado obtido
                        first_data_obtained = True
                    else:
                        save_data_and_analyze(data)
                        previous_server_seeds.append(current_server_seed)
                        recent_data_count += 1

                if recent_data_count == 2:
                    recent_data_count = 0
                    # Após obter dois dados recentes, espera 28 segundos antes de fazer a próxima requisição
                    time.sleep(REQUEST_DELAY_SECONDS)
                else:
                    # Aguarde 1 segundo antes de fazer a próxima solicitação
                    time.sleep(1)
            else:
                # Se houve um erro ou não há dados disponíveis, aguarde 1 segundo antes de fazer a próxima solicitação
                time.sleep(1)

        except requests.exceptions.RequestException as e:
            st.error("Erro na solicitação: " + str(e))
            # Se houve um erro, aguarde 1 segundo antes de fazer a próxima solicitação
            time.sleep(1)

# Função principal do Streamlit
def main():
    st.title('Server Seed Check')
    check_server_seed()

if __name__ == '__main__':
    main()
