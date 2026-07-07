import altair as alt


def heart_rate_chart(trends):
    return alt.Chart(trends).mark_line().encode(x='time:T', y='heart_rate:Q')


def spo2_chart(trends):
    return alt.Chart(trends).mark_line(color='#4caf50').encode(x='time:T', y='spo2:Q')


def temperature_chart(trends):
    return alt.Chart(trends).mark_line(color='#ff9800').encode(x='time:T', y='temperature:Q')
