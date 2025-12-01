import dash
from dash import dcc, html, Input, Output, State
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import math
import time
from urllib.parse import parse_qs

# Import the enhanced BigQuery radar chart functions
try:
    from enhanced_radar_v2_with_fast_state import (
        BigQueryRadarChartDataProvider,
        create_enhanced_radar_chart,
        create_detail_chart,
        get_performance_label
    )
    ENHANCED_V2_AVAILABLE = True
    print("✅ Enhanced BigQuery radar chart functions imported successfully")
except ImportError as e:
    print(f"⚠️  Enhanced V2 functions not available: {e}")
    ENHANCED_V2_AVAILABLE = False

import os

# BigQuery connection parameters
PROJECT_ID = os.environ.get('BIGQUERY_PROJECT', 'county-dashboard')
DATASET_ID = os.environ.get('BIGQUERY_DATASET', 'sustainability_data')

# County-specific password configuration
COUNTY_PASSWORDS = {
    '01001': 'autauga2024',  # Autauga County, AL
    '01003': 'baldwin2024',  # Baldwin County, AL
    # ... (copy all the county passwords from the original file)
    # For brevity, I'll just include a few examples here
    # You should copy ALL the county passwords from your original file
}

# Master password for all counties
MASTER_PASSWORD = 'county_dashboard_2024'

# Initialize the Dash app
app = dash.Dash(__name__, suppress_callback_exceptions=True)
app.title = "County Sustainability Dashboard - Secure Access"

# Initialize the enhanced data provider
if ENHANCED_V2_AVAILABLE:
    try:
        provider = BigQueryRadarChartDataProvider(
            PROJECT_ID,
            DATASET_ID,
            'display_names.csv'
        )
        print(f"✅ Enhanced BigQuery data provider initialized (Stage {provider.stage}/3)")
        print(f"📝 Display names: {len(provider.display_names_map)} mappings loaded")
    except Exception as e:
        print(f"⚠️  Enhanced provider initialization failed: {e}")
        provider = None
        ENHANCED_V2_AVAILABLE = False
else:
    provider = None

def validate_county_access(county_fips, password):
    """Validate if the provided password allows access to the specified county"""
    if not county_fips or not password:
        return False, "Missing county or password parameter"
    
    # Check master password first
    if MASTER_PASSWORD and password == MASTER_PASSWORD:
        return True, "Access granted with master password"
    
    # Check county-specific password
    if county_fips in COUNTY_PASSWORDS:
        if password == COUNTY_PASSWORDS[county_fips]:
            return True, f"Access granted for county {county_fips}"
        else:
            return False, f"Invalid password for county {county_fips}"
    else:
        return False, f"County {county_fips} not configured for access"

def get_all_counties():
    """Get list of all counties from BigQuery"""
    if ENHANCED_V2_AVAILABLE and provider:
        try:
            counties_df = provider.get_all_counties()
            if not counties_df.empty:
                print(f"✅ Found {len(counties_df)} counties from BigQuery")
                return counties_df
        except Exception as e:
            print(f"⚠️  Failed to get counties: {e}")
    
    return pd.DataFrame(columns=['fips_code', 'county_name', 'state_code', 'state_name'])

def get_county_metrics(county_fips):
    """Get all metrics for a specific county from BigQuery"""
    if ENHANCED_V2_AVAILABLE and provider:
        try:
            county_info, structured_data = provider.get_county_metrics(county_fips)
            if not county_info.empty and structured_data:
                print(f"✅ Loaded data for county {county_fips}")
                return county_info, structured_data
        except Exception as e:
            print(f"❌ Failed to load county data: {e}")
    
    return pd.DataFrame(), {}

def get_submetric_details(county_fips, top_level, sub_category):
    """Get detailed metrics from BigQuery"""
    if ENHANCED_V2_AVAILABLE and provider:
        try:
            details_df = provider.get_submetric_details(county_fips, top_level, sub_category)
            return details_df
        except Exception as e:
            print(f"❌ Failed to load submetric details: {e}")
    
    return pd.DataFrame()

def create_access_denied_layout(error_message="Access Denied"):
    """Create layout for access denied scenarios"""
    return html.Div([
        html.Div([
            html.H1("🔒 Access Denied", className="text-3xl font-bold text-red-600 mb-4"),
            html.P(error_message, className="text-lg text-gray-700 mb-6"),
            html.Div([
                html.H3("How to Access:", className="text-xl font-semibold mb-3"),
                html.Ul([
                    html.Li("Contact your county administrator for the correct access URL"),
                    html.Li("Ensure you have the correct county code and password"),
                    html.Li("URL format: yourdomain.com/?county=XXXXX&key=password"),
                ], className="list-disc list-inside space-y-2 text-gray-600")
            ], className="bg-gray-50 p-4 rounded-lg"),
        ], className="max-w-md mx-auto bg-white p-8 rounded-lg shadow-lg mt-20")
    ], className="min-h-screen bg-gray-100 flex items-center justify-center")

def create_dashboard_layout(county_fips, county_info, structured_data):
    """Create the main dashboard layout for authenticated users"""
    county_name = f"{county_info.iloc[0]['county_name']}, {county_info.iloc[0]['state_code']}"
    
    # Create initial radar chart
    initial_radar_fig = create_enhanced_radar_chart(structured_data, county_name, provider, county_fips)
    
    return html.Div([
        # Header
        html.Div([
            html.H1(f"{county_name} Sustainability Dashboard", 
                    className="text-3xl font-bold text-center text-gray-800 mb-2"),
            
            html.Div([
                html.Span(
                    f"✅ Stage {provider.stage}/3 Data Available" if ENHANCED_V2_AVAILABLE and provider else "❌ No Enhanced Data",
                    className=f"text-sm px-3 py-1 rounded-full text-white " + 
                             ("bg-green-600" if ENHANCED_V2_AVAILABLE and provider and provider.stage >= 2 else "bg-red-600")
                ),
                html.Span(
                    f"• {provider.comparison_mode.title()} Comparison" if ENHANCED_V2_AVAILABLE and provider else "",
                    className="text-xs text-gray-600 ml-2"
                ),
                html.Span(
                    f"🔒 Secure Access • County: {county_fips}",
                    className="text-xs text-green-600 ml-4 font-medium"
                )
            ], className="text-center mb-4")
        ], className="bg-white p-6 rounded-lg shadow-md mb-6"),
        
        # Main content
        html.Div([
            # Radar chart section
            html.Div([
                dcc.Graph(
                    id='radar-chart',
                    figure=initial_radar_fig,
                    style={'height': '700px'}
                )
            ], className="bg-white p-6 rounded-lg shadow-md", style={'width': '65%'}),
            
            # Summary section
            html.Div([
                html.Div([
                    html.H3("Quick Stats", className="text-lg font-semibold mb-4"),
                    html.Div(id='summary-stats')
                ], className="bg-white p-4 rounded-lg shadow-md mb-4"),
                
                html.Div([
                    html.H3("Comparison Mode", className="text-lg font-semibold mb-4"),
                    html.Div([
                        html.Button(
                            "National Comparison", 
                            id='national-mode-btn',
                            className="w-full mb-2 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
                        ),
                        html.Button(
                            "Compare with State", 
                            id='state-mode-btn',
                            className="w-full mb-2 px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700"
                        ),
                        html.Div(id='comparison-status', className="text-xs text-gray-600 mt-2")
                    ])
                ], className="bg-white p-4 rounded-lg shadow-md mb-4"),
                
                html.Div([
                    html.H3("Instructions", className="text-lg font-semibold mb-4"),
                    html.Ul([
                        html.Li("Click on radar chart points to see detailed metrics"),
                        html.Li("People (Purple), Productivity (Yellow), Place (Green)"),
                        html.Li("Switch between National and State comparisons"),
                        html.Li("Hover for detailed information")
                    ], className="text-sm text-gray-600 space-y-1 list-disc list-inside")
                ], className="bg-white p-4 rounded-lg shadow-md")
            ], style={'width': '33%', 'marginLeft': '2%'})
        ], className="flex"),
        
        # Detail section
        html.Div([
            html.H2(id='detail-title', className="text-xl font-semibold mb-4", 
                   children="Click on a radar chart point to view detailed metrics"),
            dcc.Graph(id='detail-chart', figure=go.Figure())
        ], id='detail-section', className="bg-white p-6 rounded-lg shadow-md mt-6", 
           style={'display': 'none'}),
        
        # Data stores
        dcc.Store(id='county-data-store', data=structured_data),
        dcc.Store(id='selected-county-info', data={
            'county_name': county_info.iloc[0]['county_name'],
            'state_code': county_info.iloc[0]['state_code'],
            'fips': county_fips
        }),
        dcc.Store(id='comparison-mode-store', data='national'),
        dcc.Store(id='authentication-store', data={'authenticated': True, 'county_fips': county_fips})
        
    ], className="min-h-screen bg-gray-100 p-6 max-w-7xl mx-auto")

# Main App Layout
app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    html.Div(id='main-content')
])

# Authentication and Main Layout Callback
@app.callback(
    Output('main-content', 'children'),
    [Input('url', 'search')]
)
def authenticate_and_display(url_search):
    """Main authentication callback"""
    if not url_search:
        return create_access_denied_layout("No access parameters provided")
    
    try:
        query_params = parse_qs(url_search.lstrip('?'))
        county_fips = query_params.get('county', [None])[0]
        password = query_params.get('key', [None])[0]
    except:
        return create_access_denied_layout("Invalid URL format")
    
    is_valid, message = validate_county_access(county_fips, password)
    
    if not is_valid:
        return create_access_denied_layout(f"Authentication failed: {message}")
    
    try:
        county_info, structured_data = get_county_metrics(county_fips)
        
        if county_info.empty:
            return create_access_denied_layout(f"No data found for county {county_fips}")
        
        if ENHANCED_V2_AVAILABLE and provider:
            provider.set_comparison_mode('national')
        
        print(f"✅ Authenticated access for county {county_fips}")
        return create_dashboard_layout(county_fips, county_info, structured_data)
        
    except Exception as e:
        print(f"❌ Error loading county data: {e}")
        return create_access_denied_layout(f"Error loading data: {str(e)}")

# Update county data based on comparison mode
@app.callback(
    [Output('county-data-store', 'data'),
     Output('selected-county-info', 'data')],
    [Input('comparison-mode-store', 'data')],
    [State('authentication-store', 'data')]
)
def update_county_data(comparison_mode, auth_data):
    """Update county data based on comparison mode"""
    if not auth_data or not auth_data.get('authenticated'):
        return {}, {}
    
    county_fips = auth_data.get('county_fips')
    if not county_fips:
        return {}, {}
    
    if ENHANCED_V2_AVAILABLE and provider:
        if comparison_mode == 'state':
            counties_df = get_all_counties()
            county_row = counties_df[counties_df['fips_code'] == county_fips]
            if not county_row.empty:
                state_code = county_row.iloc[0]['state_code']
                provider.set_comparison_mode('state', state_code)
        else:
            provider.set_comparison_mode('national')
    
    county_info, structured_data = get_county_metrics(county_fips)
    
    if county_info.empty:
        return {}, {}
    
    county_details = {
        'county_name': county_info.iloc[0]['county_name'],
        'state_code': county_info.iloc[0]['state_code'],
        'fips': county_fips
    }
    
    return structured_data, county_details

# Update radar chart
@app.callback(
    Output('radar-chart', 'figure'),
    [Input('county-data-store', 'data'),
     Input('selected-county-info', 'data')],
    [State('authentication-store', 'data')]
)
def update_radar_chart(county_data, county_info, auth_data):
    """Update radar chart"""
    if not auth_data or not auth_data.get('authenticated'):
        return go.Figure()
    
    if not county_data or not county_info:
        return go.Figure()
    
    county_name = f"{county_info['county_name']}, {county_info['state_code']}"
    county_fips = county_info['fips']
    return create_enhanced_radar_chart(county_data, county_name, provider, county_fips)

# Update comparison mode
@app.callback(
    Output('comparison-mode-store', 'data'),
    [Input('national-mode-btn', 'n_clicks'),
     Input('state-mode-btn', 'n_clicks')],
    [State('comparison-mode-store', 'data')]
)
def update_comparison_mode(national_clicks, state_clicks, current_mode):
    """Update comparison mode"""
    import dash
    ctx = dash.callback_context
    if not ctx.triggered:
        return current_mode
    
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    if button_id == 'national-mode-btn':
        return 'national'
    elif button_id == 'state-mode-btn':
        return 'state'
    
    return current_mode

# Update summary stats
@app.callback(
    Output('summary-stats', 'children'),
    [Input('county-data-store', 'data'),
     Input('comparison-mode-store', 'data')]
)
def update_summary_stats(county_data, comparison_mode):
    """Update summary stats"""
    if not county_data:
        return "No data available"
    
    category_colors = {
        'People': '#5760a6',
        'Productivity': '#c0b265',
        'Place': '#588f57'
    }
    
    stats_items = []
    for category in ['People', 'Productivity', 'Place']:
        if category in county_data and county_data[category]:
            subcats = county_data[category]
            avg_score = round(sum(subcats.values()) / len(subcats), 1)
            color = category_colors[category]
            
            stats_items.append(
                html.Div([
                    html.Div([
                        html.Span(category.upper(), className="font-medium text-white text-sm"),
                    ], className="px-3 py-1 rounded", style={'backgroundColor': color}),
                    html.Span(f"{avg_score}%", className="text-lg font-bold", style={'color': color})
                ], className="flex justify-between items-center p-3 bg-gray-50 rounded mb-2")
            )
    
    return stats_items

# Handle radar chart clicks
@app.callback(
    [Output('detail-section', 'style'),
     Output('detail-title', 'children'),
     Output('detail-chart', 'figure')],
    [Input('radar-chart', 'clickData')],
    [State('selected-county-info', 'data')]
)
def handle_radar_click(clickData, county_info):
    """Handle radar chart clicks"""
    if not clickData or not county_info:
        return {'display': 'none'}, "", go.Figure()
    
    try:
        point_data = clickData['points'][0]
        custom_data = point_data.get('customdata', [])
        
        if len(custom_data) >= 2:
            top_level = custom_data[0]
            sub_category = custom_data[1]
            
            details_df = get_submetric_details(county_info['fips'], top_level, sub_category)
            
            if not details_df.empty:
                title = f"{sub_category} Metrics - {county_info['county_name']}, {county_info['state_code']}"
                detail_fig = create_detail_chart(details_df, title, provider.comparison_mode)
                
                return {'display': 'block'}, title, detail_fig
    
    except Exception as e:
        print(f"Error handling click: {e}")
    
    return {'display': 'none'}, "", go.Figure()

# Custom CSS
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''

server = app.server

if __name__ == '__main__':
    print("\n🔒 SECURE COUNTY SUSTAINABILITY DASHBOARD - BIGQUERY VERSION")
    print("=" * 70)
    
    if ENHANCED_V2_AVAILABLE and provider:
        print(f"✅ Connected to BigQuery (Stage {provider.stage}/3)")
        print(f"   Project: {PROJECT_ID}")
        print(f"   Dataset: {DATASET_ID}")
    else:
        print("❌ BigQuery connection failed")
    
    print(f"\n📋 Access URL Format:")
    print(f"   http://localhost:8050/?county=01001&key=autauga2024")
    
    print(f"\n🌐 Starting secure dashboard on http://localhost:8050")
    print("=" * 70)
    
    app.run(debug=True, host='0.0.0.0', port=8050)