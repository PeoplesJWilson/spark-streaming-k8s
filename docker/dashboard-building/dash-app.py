from dash import Dash, html, dcc, Input, Output, ctx, callback, dash_table
from dash.exceptions import PreventUpdate
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import dash_bootstrap_components as dbc
from dash_bootstrap_templates import load_figure_template
from pymongo import MongoClient
import datetime
import plotly.figure_factory as ff
import pymongo
import os

DB_NAME  = os.environ["MONGO_DBNAME"]
MONGO_ENDPOINT = os.environ["MONGO_SERVER_PORT"]

client = MongoClient(f"mongodb://{MONGO_ENDPOINT}/")
db = client[DB_NAME]


template = "cyborg"
load_figure_template([template])

app = Dash(__name__, external_stylesheets=[dbc.themes.CYBORG])

stock_options = [{'label': symbol, 'value': symbol} 
                 for symbol in db.list_collection_names() 
                    if not symbol.endswith("supports") 
                        and not symbol.endswith("resistances")]

stock_ex = stock_options[0]['label']
not_trends = ['_id', 'datetime', 'open', 'high', 'low', 'close', 'volume','macd','signal', 'support', 'resistance']
cols = list(db[stock_ex].find_one().keys()) + ["none"]
trend_options = [{'label': symbol, 'value': symbol} for symbol in cols if symbol not in not_trends]

# desired layout --> check id's 
app.layout = html.Div(children = [
            dbc.Row([
                dbc.Col(html.H1('Fast Streaming with Spark Scala'), width = 9, style = {'margin-left':'7px','margin-top':'7px'})
            ]),
        html.Hr(),
            dbc.Row([
                dbc.Col(dcc.Dropdown(stock_options, stock_options[0]['value'], id = 'stocks')), 
                dbc.Col(dcc.Dropdown(trend_options, id = 'trends', placeholder="Select a trend")),
                dbc.Col(dcc.Dropdown(id = 'supports', placeholder="add detected support")), 
                dbc.Col(dcc.Dropdown(id = 'resistances', placeholder="add detected resistance"))
            ]),
        html.Br(),  
            dbc.Row([
                dbc.Col(dcc.Graph(id='live-candlestick'), width=9),
                dcc.Interval(
                    id='interval-component',
                    interval=10*1000, # in milliseconds
                    n_intervals=0
                    ),
                dbc.Col(dcc.Graph(id='supports-barplot'), width = 3)
            ]),
        html.Br(),
            dbc.Row([
                dbc.Col(dcc.Graph(id='live-macd'), width=9), 
                dbc.Col(dcc.Graph(id='resistance-barplot'), width=3)
            ])
    ]
)

@callback(Output('supports', 'value'),
          Output('resistances', 'value'),
          Output('trends', 'value'),
          Input('stocks', 'value'))
def reset_dropdowns(stock):
    return "none","none","none"


@callback(Output('supports', 'options'),
              Input('stocks', 'value'))
def update_support_options(stock):
    collection = db[stock]
    d_up = datetime.datetime.now()
    d_low = d_up - datetime.timedelta(days=5)
    data = collection.find({"datetime": {"$lt": d_up, "$gt": d_low}}).sort("datetime")
    df = pd.DataFrame(list(data))
    supports = df["support"].astype(float)
    opts = ["none"] + sorted(list(supports.values))

    support_options = [{'label': support, 'value': support} for support in opts if support != 0]
    return support_options

@callback(Output('resistances', 'options'),
              Input('stocks', 'value'))
def update_resistance_options(stock):
    collection = db[stock]
    d_up = datetime.datetime.now()
    d_low = d_up - datetime.timedelta(days=5)
    data = collection.find({"datetime": {"$lt": d_up, "$gt": d_low}}).sort("datetime")
    df = pd.DataFrame(list(data))
    res = df["resistance"].astype(float)
    opts = ["none"] + sorted(list(res.values))
    resistance_options = [{'label': support, 'value': support} for support in opts if support != 0]
    return resistance_options


@callback(Output('live-candlestick', 'figure'),
              Input('interval-component', 'n_intervals'), 
              Input('stocks', 'value'),
              Input('trends','value'),
              Input('supports', 'value'),
              Input('resistances', 'value'))
def update_live_candlestick(n, stock, trend, support, resistance):
    print(stock)
    collection = db[stock]
    d_up = datetime.datetime.now()
    d_low = d_up - datetime.timedelta(days=5)
    data = collection.find({"datetime": {"$lt": d_up, "$gt": d_low}}).sort("datetime")

    df = pd.DataFrame(list(data))
    print(df.columns)
    fig = go.Figure()

    fig.add_trace(go.Candlestick(x=df['datetime'],
                open=df['open'], high=df['high'],
                low=df['low'], close=df['close'], name="candlesticks")
                    )
    
    if (trend is not None) and (trend != "none") :
        fig.add_trace(go.Scatter(x=df["datetime"],
                    y=df[trend].astype(float).round(2), name=trend, line_color="#0000ff"
                    ))
    
    if (support is not None) and (support != "none") :
        fig.add_hline(y=support, line_width=3, line_dash="dash", line_color="green")

    if (resistance is not None) and (resistance != "none") :
        fig.add_hline(y=resistance, line_width=3, line_dash="dash", line_color="red")

    fig.update_layout(margin=go.layout.Margin(
        l=40,r=20,b=20,t=20))

    fig.update_layout(showlegend=False)
    fig.update_xaxes(rangebreaks=[dict(bounds=[16, 9.5], pattern="hour"),
                              dict(bounds=['sat', 'mon'])])


    return fig

@callback(Output('supports-barplot', 'figure'),
              Input('stocks', 'value'))
def update_supports_barplot(stock):
    print(stock)
    collection = db[stock]
    d_up = datetime.datetime.now()
    d_low = d_up - datetime.timedelta(days=5)
    data = collection.find({"datetime": {"$lt": d_up, "$gt": d_low}}).sort("datetime")

    df = pd.DataFrame(list(data))
    print(df.columns)
    df = df[["datetime", "support"]]
    df["support"] = df["support"].astype(float)
    df = df[df["support"] != 0]
    df = df.drop_duplicates()
    fig = go.Figure()

        
    fig.add_trace(go.Scatter(x=df["datetime"],
                    y=df["support"].astype(float),
                    marker_color='aquamarine', name="support"
                    ))

    fig.update_layout(margin=go.layout.Margin(
        l=40,r=20,b=20,t=60))
    
    fig.update_layout(
        title="Supports"
    )

    fig.update_xaxes(rangebreaks=[dict(bounds=[16, 9.5], pattern="hour"),
                              dict(bounds=['sat', 'mon'])])


    return fig


@callback(Output('resistance-barplot', 'figure'),
              Input('stocks', 'value'))
def update_resistances_barplot(stock):
    print(stock)
    collection = db[stock]
    d_up = datetime.datetime.now()
    d_low = d_up - datetime.timedelta(days=5)
    data = collection.find({"datetime": {"$lt": d_up, "$gt": d_low}}).sort("datetime")

    df = pd.DataFrame(list(data))
    df = df[["datetime", "resistance"]]
    df["resistance"] = df["resistance"].astype(float)
    df = df[df["resistance"] != 0]
    df = df.drop_duplicates()
    print(df.columns)
    fig = go.Figure()


        
    fig.add_trace(go.Scatter(x=df["datetime"],
                    y=df["resistance"],
                    marker_color='red', name="resistance"
                    ))

    fig.update_layout(margin=go.layout.Margin(
        l=40,r=20,b=20,t=60))
    fig.update_layout(
        title="Resistances"
    )
    fig.update_xaxes(rangebreaks=[dict(bounds=[16, 9.5], pattern="hour"),
                              dict(bounds=['sat', 'mon'])])


    return fig






@callback(Output('live-macd', 'figure'),
              Input('interval-component', 'n_intervals'), 
              Input('stocks', 'value'))
def update_live_macd(n, stock):
    print(stock)
    collection = db[stock]
    d_up = datetime.datetime.now()
    d_low = d_up - datetime.timedelta(days=3)
    data = collection.find({"datetime": {"$lt": d_up, "$gt": d_low}}).sort("datetime", pymongo.DESCENDING)

    df = pd.DataFrame(list(data))
    print(df.columns)
    df["hist"] = df["macd"].astype(float) - df["signal"].astype(float)
    df_green = df[df["hist"] >= 0]
    df_red = df[df["hist"] < 0]


    fig = go.Figure()
    fig.add_trace(go.Bar(x=df_green["datetime"],
                    y=df_green["hist"],
                    marker_color='aquamarine', name="hist"
                    ))
    fig.add_trace(go.Bar(x=df_red["datetime"],
                    y=df_red["hist"],
                    marker_color='red', name="hist"
                    ))
    
    fig.add_trace(go.Scatter(x=df["datetime"],
                    y=df["macd"], name="macd"
                    ))
    fig.add_trace(go.Scatter(x=df["datetime"],
                    y=df["signal"], name="signal"
                    ))

    fig.update_xaxes(rangebreaks=[dict(bounds=[16, 9.5], pattern="hour"),
                              dict(bounds=['sat', 'mon'])])
    
    fig.update_layout(showlegend=False)
    fig.update_layout(margin=go.layout.Margin(
        l=40,r=20,b=20,t=60
    ))
    fig.update_layout(
        title="MACD"
    )
   
    return fig
      

if __name__ == '__main__':
    app.run_server(host='0.0.0.0', port = 8050, debug=True)
