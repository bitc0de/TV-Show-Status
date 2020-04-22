from flask import Flask, render_template, session, request, redirect, url_for, jsonify
from flask_bootstrap import Bootstrap
import os
os.environ["OMP_NUM_THREADS"] = "1"
import numpy as np
import plotly
import requests
from bs4 import BeautifulSoup
import plotly.figure_factory as ff
from imdb import IMDb
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
import plotly.graph_objects as go
app = Flask(__name__)
app.config['SECRET_KEY'] = 'ABCD'
Bootstrap(app)
# pip install Werkzeug==0.16.0 will work. Other version might give error
figures = {}


def draw_heatmap(ID):
    ia = IMDb()
    movies = ia.search_movie(ID)
    print ("ID:")
    print (movies[0].movieID)
    ID = movies[0].movieID
    page = ia.get_imdbURL(movies[0])
    print (page)
    content = requests.get(page).content
    soup = BeautifulSoup(content,'lxml')
    image = soup.find('img')
    image_url = image['src']
    print (image_url)
    figures ['imgurl'] = image_url




    series = ia.get_movie(movies[0].movieID)
    ia.update(series, 'episodes')

    def get_ratings(series):
        fin_list = []
        for season in sorted(series['episodes']):
            ep_list = []
            for episode in sorted(series['episodes'][season]):
                result = series['episodes'][season][episode]
                try:
                    rating = round(result.get('rating'), 2)
                except TypeError:
                    rating = 0
                ep_list.append(rating)
            fin_list.append(ep_list)
        return fin_list

    fin_list = get_ratings(series)

    def get_max_number_of_episodes(fin_list):
        temp = []
        for l in fin_list:
            temp.append(len(l))
        return max(temp)

    max_episode = get_max_number_of_episodes(fin_list)
    max_episode += 1

    def get_heatmap_array(max_episode):
        fin_list = []
        for season in sorted(series['episodes']):
            ep_list = [0] * max_episode
            for episode in sorted(series['episodes'][season]):
                result = series['episodes'][season][episode]
                try:
                    rating = round(result.get('rating'), 2)
                except TypeError:
                    rating = 0
                for i, values in enumerate(ep_list):
                    if i == episode:
                        ep_list[i] = rating
            fin_list.append(ep_list)
        fin_array = np.array([np.array(xi) for xi in fin_list])
        x_episodes = np.arange(0, max_episode)
        x_episodes = x_episodes.tolist()
        y_seasons = sorted(series['episodes'])
        return x_episodes, y_seasons, fin_array

    x_episodes, y_seasons, fin_array = get_heatmap_array(max_episode)

    def plotly_heatmap(x_episodes, y_seasons, fin_array):
        if len(y_seasons) <= 10:
            adj_height = 500
        elif len(y_seasons) >= 10:
            adj_height = 800

        colorscale = [[0.0, 'rgb(191,6,6)'], [.2, 'rgb(191,71,6)'],
                      [.4, 'rgb(191,126,6)'], [.6, 'rgb(191,176,6)'],
                      [.8, 'rgb(154,191,6)'], [1.0, 'rgb(0,227,45)']]

        fig = ff.create_annotated_heatmap(z=fin_array, x=x_episodes, y=y_seasons,
                                          zmin=0, zmax=10, colorscale=colorscale,
                                          hoverongaps=False, font_colors=['white'],
                                          hovertemplate='<i>Season</i>: %{y}' +
                                                        '<br>Episode: %{x}' +
                                                        '<br>Rating: %{z}' +
                                                        '<extra></extra>',
                                          annotation_text=fin_array, showlegend=False)

        fig.update_layout(
            height=adj_height,
            xaxis_title="Episode #",
            yaxis_title="Season #",
            font=dict(
                family="Roboto",
                size=14,
                color="#000000"
            ),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            xaxis=dict(tickmode='linear', fixedrange=True),
            yaxis=dict(autorange="reversed", fixedrange=True),
            hoverlabel=dict(bgcolor="white"), showlegend=False
        )

        fig['data'][0]['showscale'] = True
        # fig.show(config=dict(displayModeBar=False))
        fig_json = fig.to_json()
        return fig_json

    heatmap = plotly_heatmap(x_episodes, y_seasons, fin_array)

    def get_linechart():
        y_rating = []
        x_season_episode = []
        ep_name = []

        for season in sorted(series['episodes']):
            for episode in sorted(series['episodes'][season]):
                result = series['episodes'][season][episode]
                try:
                    rating = round(result.get('rating'), 2)
                except TypeError:
                    rating = None
                x_season_episode.append('S{}E{}'.format(season, episode))
                y_rating.append(rating)
                ep_name.append(result)

        best_ep_num = x_season_episode[y_rating.index(np.nanmax(np.array(y_rating, dtype=np.float64)))]
        best_ep_name = ep_name[y_rating.index(np.nanmax(np.array(y_rating, dtype=np.float64)))]
        worst_ep_num = x_season_episode[y_rating.index(np.nanmin(np.array(y_rating, dtype=np.float64)))]
        worst_ep_name = ep_name[y_rating.index(np.nanmin(np.array(y_rating, dtype=np.float64)))]

        fig = go.Figure(data=go.Scatter(x=x_season_episode, y=y_rating, hovertemplate='<b>Episode</b>: %{x}' +
                                                                                      '<br>Rating: %{y}' +
                                                                                      '<extra></extra>',
                                        line=dict(color='firebrick', width=4)

                                        ))
        fig.update_xaxes(tickangle=0, nticks=10,
                         showline=True,
                         showgrid=False,
                         showticklabels=True,
                         linecolor='rgb(204, 204, 204)',
                         linewidth=1)
        fig.update_yaxes(rangemode="tozero",
                         showticklabels=True, ticks="outside", tickwidth=1, nticks=11, showline=True,
                         linecolor='rgb(204, 204, 204)')

        fig.update_layout(
            xaxis_title="Episode",
            yaxis_title="Rating",
            font=dict(
                family="Roboto",
                size=17,
                color="#000000"
            ),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            hoverlabel=dict(bgcolor="white")
        )
        fig_json = fig.to_json()
        return fig_json, best_ep_num, best_ep_name, worst_ep_num, worst_ep_name

    line_chart, best_ep_num, best_ep_name, worst_ep_num, worst_ep_name = get_linechart()

    title = series['title']

    return heatmap, line_chart, title, best_ep_num, best_ep_name, worst_ep_num, worst_ep_name




class DropDownForm(FlaskForm):
    name = StringField('Search')
    submit = SubmitField('Sign Up')


@app.route('/', methods=['GET', 'POST'])
def index():
    name = StringField('Search')
    form = DropDownForm()


    pass
    if form.validate_on_submit():
        print(form.name.data)

        heat_map, line_chart, title, best_ep_num, best_ep_name, worst_ep_num, worst_ep_name = draw_heatmap(
            form.name.data)
        figures['heat_map'] = heat_map
        figures['line_chart'] = line_chart
        figures['title'] = title
        figures['best_ep_num'] = best_ep_num
        figures['best_ep_name'] = best_ep_name
        figures['worst_ep_num'] = worst_ep_num
        figures['worst_ep_name'] = worst_ep_name
        return redirect(url_for('viz'))

    return render_template('index.html', form=form)


@app.route('/viz', methods=['GET', 'POST'])
def viz():
    heat_map = plotly.io.from_json(figures['heat_map'], output_type='Figure', skip_invalid=False)
    heat_map = plotly.offline.plot(heat_map, config={"displayModeBar": False}, show_link=False,
                                   include_plotlyjs=False, output_type='div')

    line_chart = plotly.io.from_json(figures['line_chart'], output_type='Figure', skip_invalid=False)
    line_chart = plotly.offline.plot(line_chart, config={"displayModeBar": False}, show_link=False,
                                     include_plotlyjs=False, output_type='div')

    title = figures['title']
    imgurl = figures['imgurl']
    best_ep_num = figures['best_ep_num']
    best_ep_name = figures['best_ep_name']
    worst_ep_num = figures['worst_ep_num']
    worst_ep_name = figures['worst_ep_name']
    return render_template('viz.html', hm=heat_map, lc=line_chart, title=title, imgurl=imgurl,
                           best_ep_num=best_ep_num, best_ep_name=best_ep_name, worst_ep_num=worst_ep_num,
                           worst_ep_name=worst_ep_name)


if __name__ == '__main__':
    app.run()
