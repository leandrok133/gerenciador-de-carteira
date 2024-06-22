import dash
import dash_bootstrap_components as dbc
import os

# Work path
work_path = os.getcwd()

# Assets path
assets_path = os.path.join(work_path, 'assets')

# Data path
book_data_path = os.path.join(assets_path, 'book_data.csv')
historical_data_path = os.path.join(assets_path, 'historical_data.csv')


estilos = ["https://cdnjs.cloudflare.com/ajax/libs/font-awesome/4.7.0/css/font-awesome.min.css", "https://fonts.googleapis.com/icon?family=Material+Icons"]

app = dash.Dash(
                external_stylesheets = estilos + [dbc.themes.BOOTSTRAP],
                assets_folder = assets_path
)

app.config['suppress_callback_exceptions'] = True
app.scripts.config.serve_locally = True
server = app.server