

import plotly.graph_objects as go
from dash import Dash, Input, Output, State, callback, dash_table, dcc, html

import pandas as pd
import requests
import json
import numpy as np
import pandas as pd
import polyline
import requests
import warnings
warnings.filterwarnings("ignore")


import pymongo
conn = 'mongodb+srv://george_1234:fisherfish12@cluster0.lme5u.mongodb.net/?tlsAllowInvalidCertificates=true'
client = pymongo.MongoClient(conn, retryWrites=False)
mdb = client['class']

df = pd.DataFrame(mdb['records'].find()).drop('_id',axis=1)
df_worker = pd.DataFrame(mdb['wok'].find()).drop('_id',axis=1)

def parse_table2(df):

    df.time = df.time.map(lambda j: str(int(j/60))+':'+str(int(j%60)))

    def get_s_data(point1, point2):

        point1 = (',').join([str(point1[1]),str(point1[0])])
        point2 = (',').join([str(point2[1]),str(point2[0])])
        point= (';').join([str(point1), str(point2)])
        g=f'http://92.53.84.30:5000/route/v1/driving/{point}'
        r = requests.get(g)
        h = polyline.decode(r.json()['routes'][0]['geometry'])

        return h

        
    fig = go.Figure()

    tok = 'pk.eyJ1IjoiZ2VvcmdlcG9wMTIzIiwiYSI6ImNsM2VzaDE2cTAybDIzam1vbjlodTlqdWMifQ.mMpWkaLQcGvSLDrqmBON8Q'

    for route in df.n.unique():
        route = df.loc[df.n==route]
        route0 = []
        for i in range(len(route) - 1):
            route0+=get_s_data(route[['lat', 'lon']].iloc[i].to_list(), route[['lat', 'lon']].iloc[i+1].to_list())


        route0 = pd.DataFrame(route0)
        fig.add_trace(go.Scattermapbox(
            mode = "lines",
            lon = route0[1],
            lat = route0[0],
            marker = {'size': 20},hoverinfo='none'))
        

    fig.add_trace(go.Scattermapbox(
        mode = "markers",
        lon = df['lon'],
        lat = df['lat'],
        marker = {'size': 10}, text=df['time']))

    fig.update_layout(height=1000, width = 1150,
        autosize=True,
        hovermode='closest',
        mapbox = dict(
            accesstoken=tok,
            bearing=0,
            center=dict(
                lat=df['lat'].mean(),
                lon=df['lon'].mean()
            ),
            pitch=0,
            zoom=12
        ),
    )
    return fig


external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

app = Dash(__name__, external_stylesheets=external_stylesheets)

app.layout = html.Div([dash_table.DataTable(
                id='table-output',
                data=df.to_dict('records'),
                columns=[{'id': c, 'name': c} for c in df.columns],
                editable=True,
                filter_action="native",
                sort_action="native",
                row_selectable='multi',
                #row_deletable=True,
                selected_rows=[],
                page_action='native',
                page_current=0,
                page_size=10),
                html.Button('Update', id='update', n_clicks=0),
                html.Div(id='output-datatsa')
            
])


@callback(
    Output('output-datatsa', 'children')
    , [Input('update', 'n_clicks')])
def logout_dashboard(n_clicks):

    global df, df_worker
    if n_clicks > 0:

                
        df = pd.DataFrame(mdb['records'].find()).drop('_id',axis=1)
        df_worker = pd.DataFrame(mdb['wok'].find()).drop('_id',axis=1)

        df_worker = df_worker[['lat','lon','ФИО','Грейд']].rename(columns={'Грейд':"skills"})

        df_worker["skills"]=df_worker["skills"].map({'Синьор':[3,2,1],'Мидл':[2,1],'Джун':[1] })

        df_worker["start"]=df_worker[['lon','lat']].apply(lambda x: list(x),1)
        df_worker["end"]=df_worker[['lon','lat']].apply(lambda x: list(x),1)
        df_worker["time_window"]=[[0,3600*8]]*len(df_worker)
        df_worker["id"]=df_worker.index
        df_worker["profile"]="car"

        body ={}
        body["vehicles"]=df_worker[["profile","id","start","end","skills","time_window"]].to_dict('records')

        
        df['skills'] = 0
        df.loc[((df.iloc[:,4]>7)&( df.iloc[:,5]>0 )) | (df.iloc[:,4]>14),'skills'] = 3
        df.loc[(df.iloc[:,5]>0) & (df.iloc[:,5]/df.iloc[:,4]<0.5),'skills'] = 2
        df.loc[(df.iloc[:,2]=='вчера') | (df.iloc[:,3]=='нет'),'skills'] = 1
        df['skill_name'] = df['skills'].map({3:'Выезд на точку для стимулирования выдач',
                                                      2:'Обучение агента',
                                                      1:'Обучение агента'})

        df=df.loc[df['skills'] != 0]
        print(df.shape)
        df["service"] = df['skills'].map({3:4*3600,2:2*3600,1:1.5*3600})
        df["location"]=df[['lon','lat']].apply(lambda x: list(x),1)
        df["id"]=df.index
        df["amount"] = [[1]]*len(df)
        body["jobs"]= df[["id","service","location","skills"]].to_dict('records')
        for i in body["jobs"]:
            i["time_windows"]=[[0,3600*8]]
            i['skills']=[i['skills']]
    
        


        headers = {'content-type' : 'application/json'}
        call = requests.post('http://leda.jupiter.icn.su:3000/', json=body, headers=headers)

        print(call.status_code, call.reason)
        resu = pd.DataFrame()
        for i in call.json()["routes"]:
            dar2 = pd.DataFrame(i["steps"]).drop(['waiting_time','job','service'],axis=1)
            dar2["vehicle"]=i["vehicle"]
            resu=pd.concat([resu,dar2],axis = 0)

        resu['lat']=resu['location'].map(lambda x: x[1])
        resu['lon']=resu['location'].map(lambda x: x[0])
        resu['time'] =resu['arrival']/60
        resu['n']=resu["vehicle"]
        resu = resu.merge(df[['id','skill_name',"service"]],on='id',how='left')

        df_worker['vehicle']=df_worker['id']
        df_worker=df_worker.drop(['lat','lon','id',"time_window",'start',"end"],axis=1)
        print(df_worker)
        print(df.loc[~df["id"].isin(resu['id'].unique()),['skills']])

        result = resu.merge(df_worker,on=['vehicle'])
        

        return html.Div([

        dash_table.DataTable(
            result.to_dict('records'),
            [{'name': i, 'id': i} for i in result.columns], 
             editable=True,
            sort_action="native",
            sort_mode='multi',page_action='native',
            page_current=0,page_size=10,
            export_format="xlsx",
        ),
        dcc.Graph(
            id='map',
            figure=parse_table2(result))

        ])



if __name__ == '__main__':
    import platform

    if platform.system() == 'Windows':
        app.run_server(debug=False)
    else:
        app.run_server(host='0.0.0.0', port=8080)
