import black
import os
import argparse

import dash
import dash_bootstrap_components as dbc
from dash import dcc, html
from dash.dependencies import Input, Output, State
import plotly.express as px
import pandas as pd
import openai

OPENAI_KEY = os.getenv("OPENAI_KEY")
assert OPENAI_KEY, "The openai key is not set!"
openai.api_key = OPENAI_KEY
COL_HEIGHT = "700px"
PLOT_HEIGHT = "500px"

CHAT_LOG = []
OAI_MESSAGES = []

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.DARKLY])
server = app.server


def get_chat_completion(oai_messages):
  completion = openai.ChatCompletion.create(
    model="gpt-3.5-turbo",
    messages=oai_messages,
    temperature=0
  )
  output = completion.choices[0].message.content
  return output


def construct_chat(chat_log):
  chat = []
  for msg in chat_log:
    if msg['role'] == 'system':
      chat.append(html.Div(dcc.Markdown(msg['content'], style={"padding": "10px",
                                                         "background-color": "#222", "border-radius": "5px",
                                                         "width": "100%", "margin-bottom": "10px"}),
                           style={"display": "flex", "justify-content": "flex-end"}))
    elif msg['role'] == 'user':
      chat.append(html.Div(html.P(msg['content'], style={"padding": "10px",
                                                         "background-color": "#222", "border-radius": "5px",
                                                         "width": "600px", "margin-bottom": "10px"}),
                           style={"display": "flex", "justify-content": "flex-end"}))
    elif msg['role'] == 'assistant':
      chat.append(html.Div(html.Code(msg['content'], style={"padding": "10px",
                                                         "background-color": "#222", "border-radius": "5px",
                                                         "width": "600px", "margin-bottom": "10px"}),
                           style={"display": "flex", "justify-content": "flex-start"}))
  return chat


def get_layout(app):
  controls = [
    dbc.InputGroup(
      [
        dbc.Input(id="input-group-button-input", placeholder="What do you want to plot?"),
        dbc.Button("justplotit!", id="input-group-button", n_clicks=0, color="info"),
      ]
    )
  ]
  graph = [
    dbc.CardHeader("Plot"),
    dbc.CardBody(dcc.Graph(id="output-graph", style={"height": PLOT_HEIGHT}), style={"height": COL_HEIGHT}),
  ]
  chat_chat = [
    dbc.CardHeader("Chat"),
    dbc.CardBody(
      [
        html.Div(construct_chat(CHAT_LOG), id="chat", style={"margin": "5px", "min-height": "100px", "max-height": "800px", "overflow-y": "scroll", "width": "100%"}),
        html.Div(controls, style={"margin-bottom": "5px"}),
      ], style={'display': 'flex', 'flex-direction': 'column', 'justify-content': 'space-between', 'align-items': 'stretch', "height": COL_HEIGHT}
    )
  ]

  app.layout = dbc.Container(
    [
      html.H1("justplotit", style={"margin": "20px", "text-align": "center", "font-size": "75px"}),
      dbc.Row(
        [
          dbc.Col(dbc.Spinner(dbc.Card(graph))),
          dbc.Col(dbc.Card(chat_chat))
        ],
        style={"padding-bottom": "15px"},
      )
    ],
    fluid=True,
  )


@app.callback(
  [Output("output-graph", "figure"), Output("chat", "children"), Output("input-group-button-input", "value")],
  [Input("input-group-button", "n_clicks"), Input("input-group-button-input", "n_submit")],
  [State("input-group-button-input", "value")],
)
def generate_graph(n_clicks, n_submit, text):
  if text is None:
    return dash.no_update, dash.no_update, ''
  OAI_MESSAGES.append(
    {
      'role': 'user',
      'content': f"""Query: {text} \n Answer: <insert code>"""})
  CHAT_LOG.append({'role': 'user', 'content': text})

  output = get_chat_completion(OAI_MESSAGES)
  formatted = black.format_str(output, mode=black.FileMode(line_length=50))
  OAI_MESSAGES.append({'role': 'assistant', 'content': formatted})
  CHAT_LOG.append({'role': 'assistant', 'content': formatted})

  try:
    fig = eval(output)
  except Exception as e:
    fig = px.line(title=f"Exception: {e}. Please try again!")

  chat = construct_chat(CHAT_LOG)

  return fig, chat, ''


if __name__ == "__main__":
  parser = argparse.ArgumentParser()
  parser.add_argument("--file", help="name of the csv file")
  args = parser.parse_args()
  print(f"Using file: {args.file}")
  assert args.file, "Please provide a csv file!"
  assert os.path.exists(args.file), "The file does not exist!"
  df = pd.read_csv(args.file)
  # df = pd.read_csv("/home/nuwandavek/Documents/data.csv")
  # df = df[df['Year'] == 2015].dropna()
  # df = df[['Entity', 'Population density', 'GDP per capita, PPP (constant 2017 international $)', 'Population (historical estimates)', 'Continent']]
  # df.columns = ['Country', 'Population density', 'GDP per capita', 'Population', 'Continent']

  # df.to_csv("world.csv", index=False)

  columns = str(df.columns.tolist())
  CHAT_LOG.append({'role': 'system', 'content': f"""
                   Welcome to justplotit!

                   The file loaded is `{args.file}`.

                   You can plot any column in the following dataset:`{columns}`

                   """})
  OAI_MESSAGES.append({'role': 'system', 'content': f"""You are a plotting helper. Write single line expressions to plot stuff in plotly express.
                      Columns in the dataset: {columns}"""})

  get_layout(app)
  app.run_server(debug=False)
