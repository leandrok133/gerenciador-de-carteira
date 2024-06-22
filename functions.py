import pandas as pd
import numpy as np
from pandas.tseries.offsets import DateOffset
from datetime import date, timedelta
import yfinance as yf

#offsets são deltas entre a data atual e o valor inserido no parametro
offsets = [DateOffset(days=5), DateOffset(months=1), DateOffset(months=3), DateOffset(months=6), DateOffset(years=1), DateOffset(years=2)] 
delta_titles = ['5 dias', '1 mês', '3 meses', '6 meses', '1 ano', '2 anos', 'Ano até agora']
PERIOD_OPTIONS = ['5d','1mo','3mo','6mo','1y','2y', 'ytd']

#Itera sobre as tuplas de periodo opetion e offsets
TIMEDELTAS = {x: y for x, y in zip(PERIOD_OPTIONS, offsets)}
TITLES = {x: y for x, y in zip(PERIOD_OPTIONS, delta_titles)}


def iterar_sobre_df_book(df_book_var: pd.DataFrame, ativos_org_var={}) -> dict:
    for _, row in df_book_var.iterrows():
        if not any(row['ativo'] in sublist for sublist in ativos_org_var):  
            ativos_org_var[row["ativo"]] = row['exchange']
    
    ativos_org_var['BOVA11'] = '.SA'
    return ativos_org_var 

#Data Types
data_type_book={'date': 'datetime64', 'preco':'float64', 'tipo':'object', 'ativo':'object', 'exchange':'object', 'vol':'int64', 'valor_total':'float64'}
data_type_hist={'date': 'datetime64', 'symbol': 'object', 'close': 'float64'}
    
def format_dataframe(df: pd.DataFrame, data_type:dict):
    for col, d_type in data_type.items(): 
        if 'date' in d_type:
            df[col] = pd.to_datetime(df[col])
        else:
            df[col] = df[col].astype(d_type)
    return df

def verificar_existencia_ativo(ticker: str) -> bool:
    try:
        # Tenta obter os dados do ativo
        info = yf.Ticker(ticker).info
        return True
    except Exception as e:
        # Se ocorrer um erro, o ativo não existe ou houve algum problema
        return False

def atualizar_historical_data(df_historical_var: pd.DataFrame, ativos_org_var={}) -> pd.DataFrame:
    for symb_dict in ativos_org_var.items():
        symbol = ''.join(symb_dict)
        
        #Retorna o D-1'
        previus_day = date.today() - timedelta(days=1)
        str_previus_day = previus_day.strftime('%Y-%m-%d')
        
        # Verifica última data do symbol
        data_symbol = df_historical_var[df_historical_var.symbol==symbol]
        max_date_symbol = data_symbol.date.max()
        # Caso o ativo não exista, passamos uma data suficientemente antiga para que seja trazido todo histórico
        if pd.isnull(max_date_symbol):
            max_date_symbol = date(1900, 1, 1)
        str_max_date_symbol = max_date_symbol.strftime('%Y-%m-%d')
        
        if max_date_symbol < previus_day:
            # Consultar novos 
            nbr_try = 0
            # Realiza 5 tentativas
            while nbr_try < 5:
                try:
                    new_line =  yf.download(
                                    symbol,
                                    start = str_max_date_symbol,
                                    end = str_previus_day,
                                    interval='1d'
                                )[['Close']].reset_index()
                    # Insere uma coluna com o nome do symbol
                    new_line.insert(1, 'symbol', symbol)
                    
                    # Renomear todas as colunas para minúsculo
                    new_line.columns = new_line.columns.str.lower()
                    
                    # Formata o dataframe
                    new_line = format_dataframe(new_line, data_type_hist)
                    
                    # Adiciona os novos dados à base 
                    df_historical_var = pd.concat([df_historical_var, new_line], ignore_index=True)
                    
                    #para encerrar o laço
                    nbr_try = 5
                except:
                    nbr_try += 1
        
    
    # remove linhas duplicadas, dando preferência em manter as últimas linhas
    return df_historical_var.drop_duplicates(subset=['date', 'symbol'], keep='last')



def definir_evolucao_patrimonial(df_historical_data: pd.DataFrame, df_book_data: pd.DataFrame) -> pd.DataFrame:
    # Agrupa o dataframe, pegando a última cotação para evitar duplicatas
    df_historical_data = df_historical_data.groupby(['date', 'symbol'])['close'].last().to_frame().reset_index()
    
    # Altera para datetime para que fique com o mesmo tido de dados que o df_book_data
    df_historical_data['date'] = pd.to_datetime(df_historical_data.date)
    
    # Pivota a tabela usando como valores 'close' e index date, gerando uma coluna para cada symbol
    df_historical_data = df_historical_data.pivot(values='close', columns='symbol', index='date')
    
    #cria dois dataframes auxiliares
    df_cotacoes = df_historical_data.copy()
    df_carteira = df_historical_data.copy()

    # substitui todos os 0s no DataFrame por valores NaN reenche para frente os valores ausentes com o último valor conhecido em cada coluna. 
    # Ou seja, substitui cada valor NaN com o valor mais recente e não nulo na mesma coluna. E por fim O método .fillna(0) substitui quaisquer
    # valores NaN restantes por 0.
    df_cotacoes = df_cotacoes.replace({0: np.nan}).ffill().fillna(0)
    # remove a string 'BMFBOVESPA' do titulo de cada linha dos dataframes cotacoes e carteira (splitando nos : que onde está a string)
    df_cotacoes.columns = [col.split(':')[-1] for col in df_cotacoes.columns]
    df_carteira.columns = [col.split(':')[-1] for col in df_carteira.columns]

    #deleta a coluna 'IBOV' dos dois dataframes 
    del df_carteira['BOVA11.SA'], df_cotacoes['BOVA11.SA']
    # faz um replace dos valores de compra e venda, na coluna 'tipo', quando for compra é 1 e quando for venda é -1 e depois multiplica os valores
    #da coluna 'vol' para que as quantidades fiquem com o sinal do tipo da operação, quantidade negativa quando for venda e quantidade positiva quando for compra
    df_book_data['vol'] = df_book_data['vol'] * df_book_data['tipo'].replace({'Compra': 1, 'Venda': -1})
    #altera o tipo dos valores da coluna data para datetime
    df_book_data['date'] = pd.to_datetime(df_book_data.date)
    #transforma o index do df nas datas
    df_book_data.index = df_book_data['date'] 
    #torna os valores da coluna 'date' iguais aos valores do index, para garantir que os dados sejam do mesmo tipo
    #df_book_data['date'] = df_book_data.index.date
    
    #seleciona todas as linhas e colunas do df_carteira e transforma tudo em zero, todas as células do df se tornam zero
    df_carteira.iloc[:, :] = 0

    #itera por todas as linhas do df_book_data e, para todas as céululas que possuirem valores maior que os valores da mesma céula no df_carteira, no caso maior que zero
    # vai ser colocada a quantidade real de cada ativo que o usuario possui (compra - venda) nas respectivas datas
    for _, row in df_book_data.iterrows():
        df_carteira.loc[df_carteira.index >= row['date'], row['ativo']+row['exchange']] += row['vol']
    
    #cria um novo df em que vai conter o valor total de cada ativo que o usuario possui, multiplicando as quantidade pelos respectivos preços de cada ativo
    df_patrimonio = df_cotacoes * df_carteira
   #cria uma nova coluna no df_patrimonio chamada 'soma, que vai conter justamente a soma do valor de todos os ativos em cada data, resultado no valor total em dinheiro 
     #substitui todos os valores NaN (valores nao encontrados, dados ausentes, por zero)
    df_patrimonio = df_patrimonio.fillna(0)
    #que o usuario tem em ativos por data
    df_patrimonio['soma'] = df_patrimonio.sum(axis=1)
    # cria um novo DataFrame que contém a quantidade de ações que cada ativo tem na carteira
    df_ops = df_carteira - df_carteira.shift(1)
    #multiplica os valores pelos valores das cotações atuais de cada ativo
    #basicamente nesse dataframe vamos ter o valor atualizada de cada ação, de acordo com o preço atual de cada ativo baseado na quantidade que existe comprada na
    #carteira do usuario
    df_ops = df_ops * df_cotacoes
    
    #cria uma nova coluna chamada evolucao patrimonial no df onde vamos pegar as diferenças dos valores da coluna soma entre datas adjacentes e diminuir dos valores
    #do df que contem as os valores de todas as açoes da carteira
    df_patrimonio['evolucao_patrimonial'] = df_patrimonio['soma'].diff() - df_ops.sum(axis=1)           # .plot()
    # e aqui realizamos a divisão para ver o percentual, armazenando esse valor em uma nova coluna chamada evolucao percentual
    df_patrimonio['evolucao_percentual'] = (df_patrimonio['evolucao_patrimonial'] / df_patrimonio['soma'])

    # cria uma lista chamada ev_total_list com o mesmo comprimento do DataFrame df_patrimonio e preenche todos os elementos da lista com o valor 1. vamos usar
    # esses valores de 1 justamente para incrementar ou decrementar o percentual da variacao de cada açao
    ev_total_list = [1]*len(df_patrimonio)
    df_patrimonio['evolucao_percentual'] = df_patrimonio['evolucao_percentual'].fillna(0)
    
    # calcula uma nova coluna "evolucao_cum" que armazena o valor acumulado da evolução percentual.
    for i, x in enumerate(df_patrimonio['evolucao_percentual'].to_list()[1:]):
        ev_total_list[i+1] = ev_total_list[i] * (1 + x)
        df_patrimonio['evolucao_cum'] = ev_total_list

    ### ALOCAÇÃO
    # Pega os últimos dados de quantidade de ativos da carteira
    df_qtd = df_carteira.tail(1).reset_index(drop=True).T.reset_index()
    df_qtd.columns = ['ticker', 'qtd']
    df_qtd = df_qtd[df_qtd.qtd>0]

    # Pega os últimos dados de patrimônio
    df_vl = df_patrimonio.tail(1).reset_index(drop=True).T.reset_index()
    df_vl.columns = ['ticker', 'vl']

    # Mescla os dados atuais de quantidade de ativos e valor para gerar um dataframe de alocação
    df_alocacao = df_qtd.merge(df_vl, how='inner', on='ticker')
    df_alocacao['pct'] = df_alocacao['vl']/df_alocacao['vl'].sum()
    
    return df_patrimonio, df_alocacao



def slice_df_timedeltas(df: pd.DataFrame, period_string: str) -> pd.DataFrame:
    if period_string == 'ytd':
        correct_timedelta = date.today().replace(month=1, day=1)
        correct_timedelta = pd.Timestamp(correct_timedelta)
    else:
        correct_timedelta = date.today() - TIMEDELTAS[period_string]
    df = df[df.date > correct_timedelta].sort_values('date')
    return df


