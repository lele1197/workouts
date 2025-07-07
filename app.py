from flask import Flask, render_template, request
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
from datetime import date, timedelta
import os

app = Flask(__name__)

@app.route("/")
def home():
    print("Current directory:", os.getcwd())
    print("Files in directory:", os.listdir())

    path_file = os.path.join(os.path.dirname(__file__), "workouts.csv")
    df = pd.read_csv(path_file)

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
            return 'Legs'
        if any(kw in name for kw in ['chest', 'bench', 'fly', 'push up', 'pullover']):
            return 'Chest'
        elif any(kw in name for kw in ['row', 'pulldown', 'pull up', 'chin up', 'back']):
            return 'Back'
        elif any(kw in name for kw in ['shoulder', 'deltoid', 'arnold press', 'front raise', 'lateral raise', 'alzate', 'overhead press', 'pike']):
            return 'Shoulders'
        elif any(kw in name for kw in ['tricep', 'skull', 'dip']) and 'chest' not in name:
            return 'Triceps'
        elif any(kw in name for kw in ['bicep', 'curl']):
            return 'Biceps'
        elif any(kw in name for kw in ['squat', 'glute', 'leg', 'calf', 'running']):
            return 'Legs'
        elif any(kw in name for kw in ['crunch', 'plank', 'sit up', 'knee raise', 'abs', 'core', 'flutter', 'toes']):
            return 'Core'
        else:
            return 'Unclassified'

    df['muscle_group'] = df['exercise_title'].apply(refined_assign_muscle_group)
    df = df[df['muscle_group'] != 'Unclassified']

    oggi = pd.to_datetime(date.today())
    last_workout = df['start_time'].max().date()
    days_since_last = (oggi.date() - last_workout).days

    week_start = oggi - timedelta(days=oggi.weekday())
    month_start = oggi.replace(day=1)
    year_start = oggi.replace(month=1, day=1)

    workouts_week = df[df['date'] >= week_start.date()]['title'].nunique()
    workouts_month = df[df['date'] >= month_start.date()]['title'].nunique()
    workouts_year = df[df['date'] >= year_start.date()]['title'].nunique()

    sets_per_group = df.groupby('muscle_group')['set_index'].count()
    volume_per_group = df.groupby('muscle_group')['volume'].sum()
    exercise_sessions = df[['date', 'exercise_title', 'muscle_group']].drop_duplicates()
    count_per_group = exercise_sessions.groupby('muscle_group')['exercise_title'].count()

    summary = pd.DataFrame({
        'Total Sets': sets_per_group,
        'Total Volume (kg x reps)': volume_per_group,
        'Workouts per Group': count_per_group
    }).fillna(0).astype(int)

    summary['% of Total'] = round(summary['Workouts per Group'] / summary['Workouts per Group'].sum() * 100, 1)
    summary = summary.sort_values(by='Workouts per Group', ascending=False)

    summary_html = summary.style \
        .background_gradient(subset=['Workouts per Group'], cmap='Blues') \
        .format({'Total Volume (kg x reps)': '{:,.0f}', '% of Total': '{:.1f}%'}) \
        .set_caption("Workout Summary by Muscle Group") \
        .to_html()

    # Graph 1
    monthly_sets = df.groupby(['month_str', 'muscle_group'])['set_index'].count().reset_index()
    fig1 = px.line(monthly_sets, x='month_str', y='set_index', color='muscle_group', markers=True,
                   title='Total Sets per Muscle Group - Monthly Trend')
    grafico1 = pio.to_html(fig1, full_html=False)

    # Graph 2
    monthly_workouts = df[['title', 'date', 'month_str', 'muscle_group']].drop_duplicates()
    monthly_workouts = monthly_workouts.groupby(['month_str', 'muscle_group']).size().reset_index(name='workouts')
    fig2 = px.bar(monthly_workouts, x='month_str', y='workouts', color='muscle_group', title='Workouts per Month')
    grafico2 = pio.to_html(fig2, full_html=False)

    # Graph 3
    weekly_data = df[['title', 'date', 'week', 'week_str', 'muscle_group']].drop_duplicates()
    weekly_data['week_num'] = weekly_data['week'].map({w: i+1 for i, w in enumerate(sorted(weekly_data['week'].unique()))})
    weekly_workouts = weekly_data.groupby(['week_num', 'muscle_group']).size().reset_index(name='workouts')
    fig3 = px.bar(weekly_workouts, x='week_num', y='workouts', color='muscle_group', title='Workouts per Week')
    fig3.update_layout(xaxis=dict(tickmode='linear', dtick=1))
    grafico3 = pio.to_html(fig3, full_html=False)

    # Graph 4
    weekly_sets = df.groupby('week_num')['set_index'].count()
    weekly_unique = df[['week_num', 'date']].drop_duplicates().groupby('week_num').count()['date']
    stats = pd.DataFrame({'Total Sets': weekly_sets, 'Workouts': weekly_unique}).reset_index()
    fig4 = go.Figure()
    fig4.add_trace(go.Scatter(x=stats['week_num'], y=stats['Total Sets'], mode='lines+markers', name='Total Sets'))
    fig4.add_trace(go.Scatter(x=stats['week_num'], y=stats['Workouts'], mode='lines+markers', name='Workouts', yaxis='y2'))
    fig4.update_layout(title='Sets and Workouts per Week',
                       xaxis=dict(title='Week', tickmode='linear', dtick=1),
                       yaxis=dict(title='Total Sets'),
                       yaxis2=dict(title='Workouts', overlaying='y', side='right', showgrid=False))
    grafico4 = pio.to_html(fig4, full_html=False)

    # Graph 5
    freq = df['exercise_title'].value_counts()
    valid_exercises = freq[freq >= 20].index
    avg_volume = df[df['exercise_title'].isin(valid_exercises)].groupby(['exercise_title', 'muscle_group'])['volume'].mean().reset_index()
    avg_volume = avg_volume.dropna(subset=['volume'])

    fig5 = px.scatter(avg_volume, x='muscle_group', y='volume', color='muscle_group',
                      size='volume', hover_name='exercise_title',
                      title='Average Volume per Exercise (min 20 sessions)')
    fig5.update_layout(showlegend=False)
    grafico5 = pio.to_html(fig5, full_html=False)

    # Graph 6
    frequent_exercises = freq[freq >= 20].index
    pivot = df[df['exercise_title'].isin(frequent_exercises)].pivot_table(index='exercise_title', columns='month_str', aggfunc='size', fill_value=0)
    fig6 = px.imshow(pivot, labels=dict(x="Month", y="Exercise", color="Frequency"),
                     x=pivot.columns, y=pivot.index,
                     title="Monthly Frequency of Exercises (min 20 times)")
    grafico6 = pio.to_html(fig6, full_html=False)

    # Graph 7
    df_clean = df.copy()
    vol_med = df_clean.groupby(['month_str', 'muscle_group']).agg(total_volume=('volume', 'sum'), total_sets=('set_index', 'count')).reset_index()
    vol_med['avg_volume_per_set'] = vol_med['total_volume'] / vol_med['total_sets']
    ordered_months = sorted(vol_med['month_str'].unique(), key=lambda x: pd.to_datetime(x))
    heat_df = vol_med.pivot(index='muscle_group', columns='month_str', values='avg_volume_per_set')
    heat_df = heat_df[ordered_months]
    fig7 = px.imshow(heat_df, labels=dict(x="Month", y="Muscle Group", color="Avg Volume/Set"),
                     title="Avg Volume per Set by Muscle Group")
    grafico7 = pio.to_html(fig7, full_html=False)

    return render_template("index.html",
        grafico1=grafico1, grafico2=grafico2, grafico3=grafico3,
        grafico4=grafico4, grafico5=grafico5, grafico6=grafico6, grafico7=grafico7,
        ultimo_allenamento=last_workout,
        giorni_da_ultimo=days_since_last,
        allenamenti_settimana=workouts_week,
        allenamenti_mese=workouts_month,
        allenamenti_anno=workouts_year,
        riepilogo_tabella=summary_html
    )

if __name__ == "__main__":
    app.run(debug=True)
