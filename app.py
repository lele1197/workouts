from flask import Flask, render_template
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio

app = Flask(__name__)

@app.route("/")
def home():

    df = pd.read_csv("workouts.csv")
    df['start_time'] = pd.to_datetime(df['start_time'], format='%d %b %Y, %H:%M', errors='coerce')
    df = df.dropna(subset=['start_time'])

    df['year'] = df['start_time'].dt.year
    df['volume'] = df['weight_kg'] * df['reps']
    df['month'] = df['start_time'].dt.to_period('M')
    df['month_str'] = df['month'].astype(str)
    df['week'] = df['start_time'].dt.to_period('W')
    df['week_str'] = df['week'].astype(str)
    df['date'] = df['start_time'].dt.date
    df['week_num'] = df['week'].apply(lambda x: x.start_time).rank(method='dense').astype(int)

    def refined_assign_muscle_group(exercise):
        name = str(exercise).lower()
        if 'leg curl' in name or 'seated leg curl' in name:
            return 'Gambe'
        if any(kw in name for kw in ['chest', 'bench', 'fly', 'push up', 'pullover']):
            return 'Petto'
        elif any(kw in name for kw in ['row', 'pulldown', 'pull up', 'chin up', 'back']):
            return 'Dorso'
        elif any(kw in name for kw in ['shoulder', 'deltoid', 'arnold press', 'front raise', 'lateral raise', 'alzate', 'overhead press', 'pike']):
            return 'Spalle'
        elif any(kw in name for kw in ['tricep', 'skull', 'dip']) and 'chest' not in name:
            return 'Tricipiti'
        elif any(kw in name for kw in ['bicep', 'curl']):
            return 'Bicipiti'
        elif any(kw in name for kw in ['squat', 'glute', 'leg', 'calf', 'running']):
            return 'Gambe'
        elif any(kw in name for kw in ['crunch', 'plank', 'sit up', 'knee raise', 'abs', 'core', 'flutter', 'toes']):
            return 'Core'
        else:
            return 'Non classificato'

    df['muscle_group'] = df['exercise_title'].apply(refined_assign_muscle_group)
    df = df[df['muscle_group'] != 'Non classificato']

    # Grafico 1
    serie_mensili = df.groupby(['month_str', 'muscle_group'])['set_index'].count().reset_index()
    fig1 = px.line(serie_mensili, x='month_str', y='set_index', color='muscle_group', markers=True,
                   title='📈 Serie totali per gruppo muscolare - andamento mensile')
    grafico1 = pio.to_html(fig1, full_html=False)

    # Grafico 2
    monthly = df[['title', 'date', 'month_str', 'muscle_group']].drop_duplicates()
    monthly = monthly.groupby(['month_str', 'muscle_group']).size().reset_index(name='allenamenti')
    fig2 = px.bar(monthly, x='month_str', y='allenamenti', color='muscle_group', title='Allenamenti per mese')
    grafico2 = pio.to_html(fig2, full_html=False)

    # Grafico 3
    daily_unique = df[['title', 'date', 'week', 'week_str', 'muscle_group']].drop_duplicates()
    daily_unique['week_num'] = daily_unique['week'].map({w: i+1 for i, w in enumerate(sorted(daily_unique['week'].unique()))})
    weekly = daily_unique.groupby(['week_num', 'muscle_group']).size().reset_index(name='allenamenti')
    fig3 = px.bar(weekly, x='week_num', y='allenamenti', color='muscle_group', title='Allenamenti per settimana')
    fig3.update_layout(xaxis=dict(tickmode='linear', dtick=1))
    grafico3 = pio.to_html(fig3, full_html=False)

    # Grafico 4
    serie_settimanali = df.groupby('week_num')['set_index'].count()
    allenamenti_settimanali = df[['week_num', 'date']].drop_duplicates().groupby('week_num').count()['date']
    weekly_stats = pd.DataFrame({'Serie Totali': serie_settimanali, 'Allenamenti': allenamenti_settimanali}).reset_index()
    fig4 = go.Figure()
    fig4.add_trace(go.Scatter(x=weekly_stats['week_num'], y=weekly_stats['Serie Totali'], mode='lines+markers', name='Serie Totali'))
    fig4.add_trace(go.Scatter(x=weekly_stats['week_num'], y=weekly_stats['Allenamenti'], mode='lines+markers', name='Allenamenti', yaxis='y2'))
    fig4.update_layout(title='Serie totali e Allenamenti per settimana',
                       xaxis=dict(title='Settimana', tickmode='linear', dtick=1),
                       yaxis=dict(title='Serie Totali'),
                       yaxis2=dict(title='Allenamenti', overlaying='y', side='right', showgrid=False))
    grafico4 = pio.to_html(fig4, full_html=False)

    # Grafico 5
    frequenze = df['exercise_title'].value_counts()
    esercizi_validi = frequenze[frequenze >= 20].index
    media_volume = df[df['exercise_title'].isin(esercizi_validi)].groupby(['exercise_title', 'muscle_group'])['volume'].mean().reset_index()
    media_volume = media_volume.dropna(subset=['volume'])  # 🔥 Elimina valori NaN

    fig5 = px.scatter(media_volume, x='muscle_group', y='volume', color='muscle_group',
                      size='volume', hover_name='exercise_title',
                      title='💥 Media volume per esercizio (almeno 20 esecuzioni)')
    fig5.update_layout(showlegend=False)
    grafico5 = pio.to_html(fig5, full_html=False)

    # Grafico 6
    esercizi_frequenti = frequenze[frequenze >= 20].index
    pivot = df[df['exercise_title'].isin(esercizi_frequenti)].pivot_table(index='exercise_title', columns='month_str', aggfunc='size', fill_value=0)
    fig6 = px.imshow(pivot, labels=dict(x="Mese", y="Esercizio", color="Frequenza"),
                     x=pivot.columns, y=pivot.index,
                     title="🗓️ Frequenza mensile degli esercizi (minimo 20 volte)")
    grafico6 = pio.to_html(fig6, full_html=False)

    # Grafico 7
    df_clean = df.copy()
    volume_medio = df_clean.groupby(['month_str', 'muscle_group']).agg(volume_totale=('volume', 'sum'), serie_totali=('set_index', 'count')).reset_index()
    volume_medio['volume_medio_per_serie'] = volume_medio['volume_totale'] / volume_medio['serie_totali']
    mesi_ordinati = sorted(volume_medio['month_str'].unique(), key=lambda x: pd.to_datetime(x))
    heatmap_df = volume_medio.pivot(index='muscle_group', columns='month_str', values='volume_medio_per_serie')
    heatmap_df = heatmap_df[mesi_ordinati]
    fig7 = px.imshow(heatmap_df, labels=dict(x="Mese", y="Gruppo Muscolare", color="Volume Medio/Serie"),
                     title="📊 Volume medio per serie per gruppo muscolare")
    grafico7 = pio.to_html(fig7, full_html=False)

    return render_template("index.html", grafico1=grafico1, grafico2=grafico2, grafico3=grafico3,
                           grafico4=grafico4, grafico5=grafico5, grafico6=grafico6, grafico7=grafico7)

if __name__ == "__main__":
    app.run(debug=True)
