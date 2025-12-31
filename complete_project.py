import dash
from dash import html, dcc, dash_table
from dash.dependencies import Input, Output
import plotly.graph_objs as go
import plotly.express as px
import dash_bootstrap_components as dbc
import base64
import os
import pandas as pd
import numpy as np
from file_system import FileAllocationTable
from system_monitor import SystemProcessMonitor, RealFileManager

# Initialize components
app=dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP,
    'https://use.fontawesome.com/releases/v5.15.4/css/all.css'],suppress_callback_exceptions=True)
process_monitor=SystemProcessMonitor()
file_manager=RealFileManager()
file_system=FileAllocationTable()

app.layout=html.Div([
    dcc.Store(id="file-store",storage_type="memory"),
    html.H1("Operating System Dashboard", style={'textAlign':'center','marginBottom':'20px'}),
    dcc.Tabs(id="tabs",value='tab-process',children=[
        dcc.Tab(label='Process Management',value='tab-process'),
        dcc.Tab(label='File Management',value='tab-file'),
        dcc.Tab(label='Disk Fragmentation',value='tab-disk')
    ]),
    html.Div(id='tabs-content')
])

@app.callback(
    Output('tabs-content','children'),
    Input('tabs','value')
)
def render_content(tab):
    if tab=='tab-process':
        return html.Div([
            dcc.Graph(id='cpu-mem-graph'),
            html.H2("Running Processes"),
            dash_table.DataTable(
                id='process-table',
                columns=[
                    {"name":"PID","id":"pid"},
                    {"name":"Name","id":"name"},
                    {"name":"CPU %","id":"cpu"},
                    {"name":"Memory %","id":"memory"}
                ],
                style_cell={'textAlign':'left','padding':'5px'},
                style_header={'backgroundColor':'lightgrey','fontWeight':'bold'},
                style_table={'height':'400px','overflowY':'auto'},
                row_selectable="single",
                selected_rows=[]
            ),
            html.H2("Selected Process Details"),
            html.Div(id='process-details',style={'whiteSpace':'pre-wrap','border':'1px solid black','padding':'10px'}),
            dcc.Interval(id='interval-process',interval=1000,n_intervals=0)
        ])
    elif tab=='tab-file':
        return html.Div([
            dbc.Row([
                dbc.Col([
                    html.H3("File Operations", className="mt-3"),
                    dcc.Upload(
                        id='upload-file',
                        children=html.Div([
                            html.I(className="fas fa-upload mr-2"),
                            html.Span('Drag and Drop or ',style={'marginRight':'5px'}),
                            html.A('Select File',style={'color':'#007bff','textDecoration':'underline'})
                        ]),
                        style={
                            'width': '100%', 'height': '100px', 'lineHeight': '100px',
                            'borderWidth': '2px', 'borderStyle': 'dashed', 'borderRadius': '10px',
                            'textAlign': 'center', 'margin': '10px 0', 'backgroundColor': '#fafafa',
                            'cursor': 'pointer'
                        },
                        multiple=False,
                        accept='.txt,.csv,.xlsx,.pdf,.doc,.docx'
                    ),
                    html.Small("Accepted file types: TXT, CSV, XLSX, PDF, DOC, DOCX", 
                               style={'color':'#666'}),
                    dcc.Dropdown(
                        id='allocation-method',
                        options=[
                            {'label':'Continuous','value':'continuous'},
                            {'label':'Linked','value':'linked'},
                            {'label':'Indexed','value':'indexed'}
                        ],
                        value='continuous',
                        className="mb-2"
                    ),
                    html.Div(id='file-upload-output'),
                    html.H4("File System Status",className="mt-3"),
                    html.Div(id='file-system-metrics')
                ], width=4),
                
                dbc.Col([
                    html.H3("Disk Block Status"),
                    dcc.Graph(
                        id='disk-blocks-visual',
                        style={'height': '250px'},
                        config={'displayModeBar':False,'scrollZoom':True}
                    ),
                    html.H4("Files Table"),
                    dash_table.DataTable(
                        id='files-table',
                        columns=[
                            {'name':'File Name','id':'file_name'},
                            {'name':'Size (KB)','id':'size'},
                            {'name':'Blocks','id':'blocks'},
                            {'name':'Method','id':'method'}
                        ],
                        style_table={'overflowX':'auto','maxHeight':'200px','overflowY':'auto'}
                    )
                ],width=8)
            ])
        ])

    elif tab=='tab-disk':
        return html.Div([
            dbc.Row([
                dbc.Col([
                    html.H3("File Analysis",className="mt-3"),
                    dcc.Dropdown(
                        id='file-selector',
                        placeholder="Select a file to analyze",
                    ),
                    html.Div(id='fragmentation-metrics',className="mt-3"),
                ], width=4),
                
                dbc.Col([
                    html.H3("File Fragmentation Map"),
                    dcc.Graph(
                        id='fragmentation-visual',
                        style={'height':'250px'},
                        config={'displayModeBar':False}
                    ),
                    dcc.Graph(
                        id='block-distribution',
                        style={'height':'250px'},
                        config={'displayModeBar':False}
                    )
                ], width=8)
            ])
        ])

# PROCESS MANAGEMENT
@app.callback(Output('cpu-mem-graph','figure'),Input('interval-process','n_intervals'))
def update_cpu_mem_graph(n):
    times, cpu, mem=process_monitor.get_live_cpu_mem()
    fig=go.Figure()
    fig.add_trace(go.Scatter(x=times,y=cpu,mode='lines+markers',name='CPU %'))
    fig.add_trace(go.Scatter(x=times,y=mem,mode='lines+markers',name='Memory %'))
    fig.update_layout(
        xaxis_title='Time', yaxis_title='Usage %',yaxis=dict(range=[0,100]),
        margin=dict(l=40,r=40,t=40,b=40),
        xaxis=dict(tickformat="%H:%M:%S",tickangle=45,nticks=20)
    )
    return fig

@app.callback(Output('process-table','data'), Input('interval-process','n_intervals'))
def update_process_table(n):
    return process_monitor.get_all_processes()

@app.callback(Output('process-details','children'),
              [Input('process-table','selected_rows'),
               Input('process-table','data')])

def display_process_info(selected_rows,data):
    if not selected_rows or not data:
        return "Click on a process to see details."
    pid = data[selected_rows[0]]['pid']
    return process_monitor.get_process_details(pid)

# FILE MANAGEMENT
def parse_uploaded_file(contents, filename):
    try:
        if not contents:
            print("Error: Empty file contents")
            raise Exception("No file content provided")
            
        if not filename:
            print("Error: No filename provided")
            raise Exception("No filename provided")
        
        if ',' not in contents:
            print("Error: Invalid content format - missing comma separator")
            raise Exception("Invalid file content format - not a proper data URI")
        
        header, content_string = contents.split(',',1)
        print(f"Content type header: {header}")
        if not header.startswith('data:'):
            print("Error: Invalid content type header - missing 'data:' prefix")
            raise Exception("Invalid file format - missing content type header")

        try:
            mime_type=header.split(';')[0].split(':')[1]
            print(f"Detected MIME type: {mime_type}")
        except Exception as e:
            print(f"Error parsing MIME type: {str(e)}")
            mime_type="application/octet-stream"
            
        try:
            print("Attempting to decode base64 content.")
            decoded = base64.b64decode(content_string)
        except Exception as e:
            raise Exception(f"Failed to decode file content: {str(e)}")
        
        try:
            mime_types={
                '.csv':['text/csv','application/csv','text/plain'],
                '.txt':['text/plain'],
                '.pdf':['application/pdf'],
                '.doc':['application/msword'],
                '.docx':['application/vnd.openxmlformats-officedocument.wordprocessingml.document'],
                '.xls':['application/vnd.ms-excel'],
                '.xlsx':['application/vnd.openxmlformats-officedocument.spreadsheetml.sheet']
            }
            file_ext=os.path.splitext(filename.lower())[1]
            print("\nValidating file type: "+str(file_ext))
            print("Actual MIME type: "+str(mime_type))

            if file_ext not in mime_types:
                print("Error: Unsupported file extension: " + str(file_ext))
                raise Exception("Unsupported file type: {}. Supported types are: {}".format(file_ext, ", ".join(mime_types.keys())))
            
            if filename.lower().endswith('.csv'):
                try:
                    text_content=decoded.decode('utf-8')
                except UnicodeDecodeError:
                    print("UTF-8 decode failed trying Latin-1")
                    text_content=decoded.decode('latin-1')
                return decoded  
                
            elif filename.lower().endswith(('.xls','.xlsx')):
                return decoded 
                
            elif filename.lower().endswith(('.txt', '.log')):
                try:
                    decoded.decode('utf-8') 
                except UnicodeDecodeError:
                    print("Warning: Text file contains non-UTF-8 characters")
                return decoded
                
            elif filename.lower().endswith('.pdf'):
                if not decoded.startswith(b'%PDF-'):
                    raise Exception("Invalid PDF file format")
                return decoded
                
            elif filename.lower().endswith(('.doc','.docx')):
                doc_signatures=[b'\xD0\xCF\x11\xE0', b'PK\x03\x04']
                if not any(decoded.startswith(sig) for sig in doc_signatures):
                    raise Exception("Invalid Word document format")
                return decoded
                
            else:
                print("Treating "+str(filename)+" as binary file")
                return decoded
                
        except Exception as e:
            print("Error processing "+filename + ": "+str(e))
            raise Exception("Error processing "+filename +" : "+str(e))

    except Exception as e:
        print("Error processing "+filename +": "+str(e))
        raise Exception("Could not process file " +filename+": "+str(e))
    
@app.callback(
    [
        Output('disk-blocks-visual','figure'),
        Output('files-table','data'),
        Output('file-system-metrics','children'),
        Output('file-upload-output','children'),
        Output('file-store','data')
    ],
    [
        Input('upload-file','contents'),
        Input('upload-file','filename'),
        Input('allocation-method','value')
    ]
)
def update_file_system(contents, filename, method):
    file_list=list(file_system.file_table.keys())
    if contents is None:
        empty_fig=go.Figure()
        empty_fig.add_annotation(
            text="Upload a file to see storage allocation",
            xref="paper",yref="paper",
            x=0.5,y=0.5,showarrow=False
        )
        metrics_placeholder=""  
        upload_output=html.Div([
            html.I(className="fas fa-upload",style={'marginRight':'10px'}),
            "Upload a file to begin analysis"
        ])
        return empty_fig, [], metrics_placeholder, upload_output, file_list

    try:
        if not filename:
            raise Exception("No filename provided")
        file_content=parse_uploaded_file(contents,filename)
        if file_content is None:
            raise Exception("Could not parse the file")
        file_info=file_manager.analyze_file(filename,file_content)
        file_system.set_allocation_method(method)
        success, msg=file_system.allocate_file(filename, file_info['size'])
        if not success:
            empty_fig = go.Figure()
            empty_fig.add_annotation(
                text="Allocation failed",
                xref="paper", yref="paper",
                x=0.5,y=0.5,showarrow=False
            )
            files_data=[
                {
                    'file_name':fname,
                    'size':info['size'],
                    'blocks':str(info.get('blocks',info.get('data_blocks', []))),
                    'method':info['method']
                }
                for fname, info in file_system.file_table.items()
            ]
            error_upload_output=html.Div([
                html.P("Error: " +msg,style={'color':'red'}),
                html.P("File size: "+str(file_info["size"])+" bytes"),
                html.P("Try a different allocation method or free up space")
            ])
            return empty_fig, files_data, "", error_upload_output, file_list
        file_manager.uploaded_files[filename]=file_info
        file_list=list(file_system.file_table.keys())
        blocks=file_system.get_file_layout()
        WINDOW_SIZE=100
        file_blocks=[]
        if filename in file_system.file_table:
            info=file_system.file_table.get(filename, {})
            if 'blocks' in info:
                file_blocks=info.get('blocks',[])
            elif 'data_blocks' in info:
                file_blocks=info.get('data_blocks',[])

        if file_blocks:
            min_b=min(file_blocks)
            max_b=max(file_blocks)
            center=(min_b+max_b)//2
            start_idx=max(0,center-WINDOW_SIZE//2)
        else:
            start_idx=0
        end_idx=start_idx+WINDOW_SIZE
        total_blocks=len(blocks)
        if end_idx > total_blocks:
            end_idx=total_blocks
            start_idx=max(0,end_idx-WINDOW_SIZE)

        fig=go.Figure()
        colors={'free':'lightgrey','used':'rgb(50,168,82)','fragmented':'rgb(255,165,0)'}
        x_vals=list(range(start_idx, end_idx))
        for i in x_vals:
            block=blocks[i]
            color=colors['free']
            if block['used']:
                color=colors['fragmented'] if block['next'] is not None else colors['used']

            hover_text="Block "+str(i)+"<br>"
            if block['files']:
                hover_text+="Files:"+", ".join(block['files'])+"<br>"
            if block['next'] is not None:
                hover_text+="Next Block: " + str(block['next'])+"<br>"
            if block['fragments']:
                hover_text+="Fragments:"+str(block['fragments'])
            fig.add_trace(go.Bar(
                x=[i],
                y=[1],
                marker_color=color,
                hovertext=hover_text,
                hoverinfo='text',
                showlegend=False
            ))

        fig.update_layout(
            title=f'Storage Layout (blocks {start_idx}-{end_idx-1})-{filename}',
            xaxis_title='Block Number',
            yaxis_title='',
            height=300,
            bargap=0,
            bargroupgap=0,
            margin=dict(l=20, r=20, t=40, b=20),
            xaxis=dict(range=[start_idx - 0.5, end_idx - 0.5])
        )

        files_data=[
            {
                'file_name':fname,
                'size':info['size'],
                'blocks':str(info.get('blocks',info.get('data_blocks',[]))),
                'method':info['method']
            }
            for fname, info in file_system.file_table.items()
        ]

        storage_info=file_manager.get_storage_info()
        total_gb=storage_info['total_size']/(1024**3)
        used_gb=storage_info['used_space']/(1024**3)
        free_gb=storage_info['available_space']/(1024**3)
        utilization=storage_info['utilization']
        metrics=html.Div([
            html.Div([html.I(className="fas fa-hdd",style={'marginRight': '10px'}),html.Strong("Storage Status")],
                     style={'fontSize':'1.2em','marginBottom':'15px'}),
            html.Div([
                html.P([html.Strong("Total Storage: "), html.Span(f"{total_gb:.2f} GB")]),
                html.P([html.Strong("Free Space: "), html.Span(f"{free_gb:.2f} GB",
                          style={'color': 'green' if free_gb > total_gb * 0.2 else 'orange'})]),
                html.P([html.Strong("Used Space: "), html.Span(f"{used_gb:.2f} GB", style={'color': 'blue'})]),
                html.Div([html.Strong("Storage Utilization: "),
                          dbc.Progress([dbc.Progress(value=utilization,
                                                     color="success" if utilization < 70 else "warning" if utilization < 90 else "danger",
                                                     bar=True, label=f"{utilization:.1f}%")], style={'height': '20px'})]),
                html.P([html.Strong("Total Files: "), html.Span(f"{len(file_manager.get_all_files())}")])
            ], style={'backgroundColor': '#f8f9fa', 'padding': '15px', 'borderRadius': '8px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.1)'})
        ])

        success_message=html.Div([
            html.Div([html.I(className="fas fa-check-circle", style={'color': 'green','marginRight':'10px'}), "File uploaded successfully!"],
                     style={'color':'green','fontWeight':'bold','fontSize':'1.2em'}),
            html.Div([
                html.P([html.Strong("File: "),filename]),
                html.P([html.Strong("Size: "),(f"{file_info['size']/1024/1024:.2f} MB" if file_info['size'] > 1024*1024 else f"{file_info['size']/1024:.2f} KB")]),
                html.P([html.Strong("Allocation Method: "),method.capitalize()])
            ], style={'marginTop': '10px', 'backgroundColor': '#f8f9fa', 'padding': '10px', 'borderRadius': '5px'})
        ])
        return fig, files_data, metrics, success_message, file_list

    except Exception as e:
        print("Error in file upload: "+str(e))
        error_message=html.Div([
            html.Div([html.I(className="fas fa-exclamation-circle", style={'color':'red','marginRight':'10px'}), "Error processing file"],
                     style={'color':'red','fontWeight':'bold','fontSize':'1.2em'}),
            html.Div([html.P(str(e)),html.Hr(),html.P(["Please try: ",html.Ul([html.Li("A different allocation method"), html.Li("A smaller file"), html.Li("A supported file type")])])],
                     style={'marginTop':'10px','backgroundColor':'#fff3f3','padding':'10px','borderRadius': '5px'})
        ])
        empty_fig=go.Figure()
        empty_fig.add_annotation(text="No data to display",xref="paper",yref="paper",x=0.5,y=0.5,showarrow=False)
        file_list=list(file_system.file_table.keys())
        files_data=[
            {
                'file_name':fname,
                'size':info['size'],
                'blocks':str(info.get('blocks',info.get('data_blocks', []))),
                'method':info['method']
            }
            for fname, info in file_system.file_table.items()
        ]
        return empty_fig, files_data, "", error_message, file_list

@app.callback(
    Output('file-selector','options'),
    Input('file-store','data')
)
def update_file_list(file_list):
    if not file_list:
        return []
    return [{'label': name, 'value': name} for name in file_list]

# DISK FRAGMENTATION
@app.callback(
    [Output('fragmentation-visual', 'figure'),
     Output('block-distribution', 'figure'),
     Output('fragmentation-metrics', 'children')],
    [Input('file-selector', 'value')]
)
def update_fragmentation_analysis(filename):
    if not filename:
        raise dash.exceptions.PreventUpdate

    file_info=file_manager.get_file_info(filename)
    if not file_info:
        return {}, {}, html.Div("No file information available")

    fragments=pd.DataFrame(file_info.get('fragments', []))
    frag_fig=go.Figure()
    for idx, frag in fragments.iterrows():
        start=frag.get('start',0)
        size=frag.get('size',0)
        blocks=frag.get('blocks',0)
        frag_fig.add_trace(go.Bar(
            x=[start],
            y=[blocks],
            width=[size],
            name=f'Fragment {idx+1}',
            hovertemplate=(
                f'Fragment {idx+1}<br>' +
                'Start: %{x}<br>' +
                'Size: %{width} bytes<br>' +
                'Blocks: %{y}<extra></extra>'
            )
        ))
    frag_fig.update_layout(
        title = 'File Fragments Map - ' +str(filename),
        xaxis_title='File Position (bytes)',
        yaxis_title='Number of Blocks',
        showlegend=True,
        height=200,
        barmode='overlay',
        bargap=0,
        margin=dict(l=20, r=20, t=30, b=20),
        plot_bgcolor='white',
        paper_bgcolor='white',
        font=dict(size=10)
    )

    try:
        file_size=int(file_info.get('size',0))
        if file_size > 0:
            frag_fig.update_xaxes(range=[0,file_size])
    except Exception:
        pass

    block_sizes = pd.DataFrame({
        "size": [
            frag.get("size",0)
            for frag in file_info.get("fragments",[])
        ],
        "fragment": [
            "Fragment "+str(i+1)
            for i in range(len(file_info.get("fragments", [])))
        ]
    })
    dist_fig=px.bar(
        block_sizes,
        x='fragment',
        y='size',
        title='Fragment Size Distribution',
        labels={'size': 'Size (bytes)', 'fragment': 'Fragment'},
        height=200
    )

    dist_fig.update_layout(
        margin=dict(l=20, r=20, t=30, b=20),
        plot_bgcolor='white',
        paper_bgcolor='white',
        font=dict(size=10),
        showlegend=False
    )

    metrics = html.Div([
       html.P("File Size: "+str(file_info.get('size',0))+" bytes"),
        html.P("Number of Blocks: "+str(file_info.get('num_blocks',0))),
        html.P("Number of Fragments: "+str(len(file_info.get('fragments',[])))),
        html.P("Fragmentation Score:{:.2f}%".format(file_info.get('fragmentation_score',0))),
    ], style={'padding':'10px','backgroundColor':'#f8f9fa','borderRadius': '5px'})
    return frag_fig, dist_fig, metrics

if __name__=='__main__':
    app.run(debug=True)