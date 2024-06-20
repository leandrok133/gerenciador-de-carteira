from dash import dcc, Input, Output, State, no_update, html
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objects as go

from menu_styles import *
from functions import *
from instance import *


layout = dbc.Container([
    dbc.Row([
        dbc.Col([
            dcc.Graph(id='line_graph', config={"displayModeBar": False, "showTips": False}, className='graph_line')    
            ], xs=12, md=9,),
        dbc.Col([
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            dbc.Row([
                                dbc.Col([
                                    dbc.Row([
                                        dbc.Col([
                                            html.H5('Ativo', className='textoQuartenarioBranco')
                                        ], md=4, style={'text-align': 'left'}),                              
                                        # dbc.Col([
                                        #     html.H5('Qtd', className='textoQuartenarioBranco')
                                        # ], md=2, style={'text-align': 'left'}),
                                        dbc.Col([
                                            html.H5('Alocação', className='textoQuartenarioBranco')
                                        ], md=3, style={'text-align': 'left'}),
                                        dbc.Col([
                                            html.H5('Valor', className='textoQuartenarioBranco')
                                        ], md=5, style={'text-align': 'left'}),
                                    ]),
                                ], md=12, xs=12, style={'text-align': 'left'})
                            ])
                        ])
                    ], className='cards_aloc_head')
                ])
            ], className='g-2 my-auto'),
            dbc.Row(id='tb_alocacao', className='g-2 my-auto')    
            ], xs=12, md=3,)
    ])
], fluid=True)

def card_alocacao(info_alocacao):
    new_card = dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            dbc.Row([
                                dbc.Col([
                                    html.H5(str(info_alocacao.get('ticker')), className='textoQuartenarioBranco')
                                ], md=4, style={'text-align': 'left'}),                              
                                # dbc.Col([
                                #     html.H5(str(info_alocacao.get('qtd')), className='textoQuartenarioBranco')
                                # ], md=2, style={'text-align': 'left'}),
                                dbc.Col([
                                    html.H5(f"{info_alocacao.get('pct'):.2f}%", className='textoQuartenarioBranco')
                                ], md=3, style={'text-align': 'left'}),
                                dbc.Col([
                                    html.H5('{:,.2f}'.format(info_alocacao.get('vl')), className='textoQuartenarioBranco')
                                ], md=5, style={'text-align': 'left'}),
                            ]),
                        ], md=12, xs=12, style={'text-align': 'left'})
                    ])
                ])
            ], className='cards_aloc')
        ])
    ], className='g-2 my-auto')
    return new_card

# =========  Callbacks  =========== #
# callback line graph
@app.callback(
    Output('line_graph', 'figure'),
    Input('dropdown_card1', 'value'),
    Input('period_input', 'value'),
    Input('profit_switch', 'value'),
    Input('book_data_store', 'data'),
    State('historical_data_store', 'data'),
)
def line_graph(dropdown, period, profit_switch, book_info, historical_info):
    if dropdown == None:
        return no_update
    if type(dropdown) != list: dropdown = [dropdown]
    dropdown = ['BOVA11.SA'] + dropdown

    df_hist = pd.DataFrame(historical_info)
    df_hist['date'] = pd.to_datetime(df_hist['date'], format='%Y-%m-%d')
    df_hist = slice_df_timedeltas(df_hist, period)

    fig = go.Figure()

    if profit_switch:#Evolução de ativos
        df_hist = df_hist[df_hist['symbol'].str.contains('|'.join(dropdown))]
        for n, ticker in enumerate(dropdown):
            df_aux = df_hist[df_hist.symbol.str.contains(ticker)]
            df_aux.dropna(inplace=True)
            df_aux.close = df_aux.close / df_aux.close.iloc[0] - 1
            fig.add_trace(go.Scatter(x=df_aux.date, y=df_aux.close*100, mode='lines', name=ticker, line=dict(color=LISTA_DE_CORES_LINHAS[n])))
        
    else:#Evolução da carteira
        df_book = pd.DataFrame(book_info)  
        df_patrimonio, _ = definir_evolucao_patrimonial(df_hist, df_book)

        df_benchmark = df_hist[df_hist.symbol.str.contains('BOVA11.SA')]
        df_benchmark.dropna(inplace=True)
        df_benchmark.close = df_benchmark.close / df_benchmark.close.iloc[0] - 1
        fig.add_trace(go.Scatter(x=df_benchmark.date, y=df_benchmark.close*100, mode='lines', name='BOVA11', line=dict(color=LISTA_DE_CORES_LINHAS[0])))

        fig.add_trace(go.Scatter(x=df_patrimonio.index, y=(df_patrimonio['evolucao_cum']- 1) * 100, mode='lines', name='Evolução Patrimonial', line=dict(color=LINHA_EVOLUCAO_PATRIMONIAL)))
    
    fig.update_layout(MAIN_CONFIG_2, showlegend=True, yaxis={'ticksuffix': '%'}, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', hoverlabel=HOVER_LINE_GRAPH)
    fig.update_xaxes(tickfont=dict(family='Nexa', size=AXIS_FONT_SIZE, color=AXIS_VALUES_COLOR), gridcolor=LINHAS_DE_GRADE)
    fig.update_yaxes(tickfont=dict(family='Nexa', size=AXIS_FONT_SIZE, color=AXIS_VALUES_COLOR), gridcolor=LINHAS_DE_GRADE, zerolinecolor=LINHA_ZERO_X)
    
    return fig

# callback para atulizar o dropdown
@app.callback(
    Output('dropdown_card1', 'value'),
    Output('dropdown_card1', 'options'),
    Input('book_data_store', 'data'),
)
def update_dropdown(book):
    df = pd.DataFrame(book)
    unique = df['ativo'].unique()
    try:
       dropdown = [unique[0], [{'label': x, 'value': x} for x in unique]]
    except:
        dropdown = ['', [{'label': x, 'value': x} for x in unique]]
    
    return dropdown


# callback tb_alocacao
@app.callback(
    Output('tb_alocacao', 'children'),
    Input('book_data_store', 'data'),
    State('historical_data_store', 'data'),
)
def tb_alocacao(book_info, historical_info):
    df_hist = pd.DataFrame(historical_info)
    df_hist['date'] = pd.to_datetime(df_hist['date'], format='%Y-%m-%d')
    df_book = pd.DataFrame(book_info)  
    _, df_alocacao = definir_evolucao_patrimonial(df_hist, df_book)

    # Ordenar pelo valor de pct do maior para o menor
    df_alocacao = df_alocacao.sort_values(by='pct', ascending=False)

    # Converter pct para representação em porcentagem
    df_alocacao['pct'] = df_alocacao['pct'] * 100

    # Itera sobre as linhas do DataFrame
    cards_aloc = []
    for index, row in df_alocacao.iterrows():
        # Converte cada linha em um dicionário
        info_alocacao = row.to_dict()
        # Adiciona o dicionário à lista
        cards_aloc.append(card_alocacao(info_alocacao))
    
    return  dbc.Col([*cards_aloc])
