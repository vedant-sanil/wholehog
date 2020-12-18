import re
import nltk 
import plotly
import spacy
from flask import request
import dash
import dash_core_components as dcc 
import dash_html_components as html 
import plotly.graph_objects as go
import pandas as pd 
from nltk.tokenize import sent_tokenize
from sklearn.manifold import TSNE
from sklearn.cluster import KMeans 
from spacy.lang.en.stop_words import STOP_WORDS
from sentence_transformers import SentenceTransformer

class TopicModeller():
    def __init__(self, sentence_df, min_char_len=50):
        sents = ''
        nlp = spacy.load('en_core_web_sm')
        embedder = SentenceTransformer('bert-base-nli-stsb-mean-tokens')
        self.tsne_df1 = pd.DataFrame()

        for idx, sent in enumerate(sentence_df['sentence']):
            sent = sent.strip()
            if sent[-1] != '.':
                sent+='.'
            sents += sent
            sents += ' '

        dfs = sent_tokenize(sents)
        df1 = dfs
        df_len = ', '.join(df1)
        df_len = len(df_len)
        dfs=[re.sub(r'[[^()]*]', '', i) for i in dfs]
        dfs=[re.sub('^n', '', i) for i in dfs]
        dfs=[re.sub('^n', '', i) for i in dfs]
        dfs=[re.sub('• ', '', i) for i in dfs]
        dfs=[ i for i in df1 if len(i) >= min_char_len ]

        self.dfs = dfs
        self.corpus_embeddings = embedder.encode(dfs)

    def project(self, topics=None, init='random', perplexity=100):
        '''
            Generate t-SNE embeddings and cluster using 
            k-Means.
        '''
        tsne = TSNE(n_components=2, init=init, random_state=10, perplexity=perplexity)
        tsne_df = tsne.fit_transform(self.corpus_embeddings)
        print('reducing embeddings dimensions')
        print('==============================')
        x = tsne_df
        wcss = []
        if not topics:
            for i in range(1, 11):
                kmeans = KMeans(n_clusters = i, init = 'k-means++', max_iter = 300, n_init = 10, random_state = 0)
                kmeans.fit(x)
                wcss.append(kmeans.inertia_)
            n_clusters = 5
        else:
            n_clusters = topics

        #Applying kmeans to the dataset / Creating the kmeans classifier
        kmeans = KMeans(n_clusters = int(n_clusters), init = 'k-means++', max_iter = 300, n_init = 10, random_state = 0)
        y_kmeans = kmeans.fit_predict(x)
        y_kmeans1=pd.DataFrame(y_kmeans)
        y_kmeans1=y_kmeans1.rename(columns={0:"label"})
        # Append words to list
        tsne_df1=pd.DataFrame(tsne_df)
        tsne_df1=tsne_df1.join(y_kmeans1)
        dfs=pd.DataFrame(self.dfs)
        dfs=dfs.rename(columns={0:'text'})
        self.tsne_df1=tsne_df1.join(dfs)

        return self.tsne_df1

    def plot(self, app_name, port_num=9000):
        '''
            Uses dash to interactively plot topic clusters.
        '''
        if self.tsne_df1.empty:
            raise NotImplementedError('t-SNE embeddings have not been computed. Use the cluster_embeddings method to compute t-SNE embeddings and cluster them.')

        just_domain = app_name
        fig = go.Figure(data=go.Scatter(x=self.tsne_df1[0],
                                        y=self.tsne_df1[1],
                                        textfont=dict(
                                        family="sans serif",
                                        size=8),
                                        text=self.tsne_df1['text'],
                                        hovertemplate=
                                        "<b>Topic: %{marker.color}</b><br><br>" +
                                        "Text: %{text}<br>" +
                                        "<extra></extra>",
                                        marker=dict(
                                        color=self.tsne_df1['label'],   
                                        colorbar=dict(
                                        title="Topics"),
                                        colorscale="Viridis"),
                                        mode='markers'))

        fig.update_traces(textposition='top center')
        fig.update_layout(title='App Review for: {}'.format(app_name))
        fig.update_layout(showlegend=False)

        app = dash.Dash()
        app.layout = html.Div([
                        dcc.Location(id='url', refresh=False),
                        dcc.Link('Navigate to "/"', href='/'),
                        html.Br(),
                        dcc.Link('Navigate to "/shutdown"', href='/shutdown'),

                        # content will be rendered in this element
                        html.Div(id='page-content')
                        #dcc.Graph(figure=fig)
                        ])

        app.run_server(debug=True,
                       host="127.0.0.1", 
                       port=port_num)
        
        def shutdown():
            func = request.environ.get('werkzeug.server.shutdown')
            if func is None:
                raise RuntimeError('Not running with Werkzeug server')
            func()

        @app.callback(dash.dependencies.Output('page-content', 'children'),
                    [dash.dependencies.Input('url', 'pathname')])
        def display_page(pathname):
            print(pathname)
            if '/shutdown' in pathname:
                shutdown()
            return html.Div([
                html.H3('You are on page {}'.format(pathname))
            ])
