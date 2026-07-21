import altair as alt
from src.ui import get_theme


def _theme_color(light, dark):
    return dark if get_theme() == "Dark" else light


def heart_rate_chart(trends):
    return (
        alt.Chart(trends)
        .mark_line(color=_theme_color("#2563eb", "#60a5fa"))
        .encode(x='time:T', y='heart_rate:Q')
        .configure_view(fill='transparent')
    )


def spo2_chart(trends):
    return (
        alt.Chart(trends)
        .mark_line(color=_theme_color("#16a34a", "#34d399"))
        .encode(x='time:T', y='spo2:Q')
        .configure_view(fill='transparent')
    )


def temperature_chart(trends):
    return (
        alt.Chart(trends)
        .mark_line(color=_theme_color("#d97706", "#fbbf24"))
        .encode(x='time:T', y='temperature:Q')
        .configure_view(fill='transparent')
    )
