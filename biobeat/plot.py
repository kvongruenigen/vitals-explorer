import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd

def create_vitals_dashboard(df, user_tz):
    """
    Create an interactive dashboard of vital signs with enhanced features.

    Args:
        df (pd.DataFrame): DataFrame containing vital signs data
        user_tz (str): User's timezone for display purposes

    Returns:
        plotly.graph_objects.Figure: Interactive dashboard figure
    """
    # Create a copy to avoid modifying the original DataFrame
    df = df.copy()

    # Convert datetime to proper timezone
    df['datetime_tz'] = pd.to_datetime(df['datetime_tz']).dt.tz_convert(user_tz)

    # Define visual styling
    colors = {
        "sbp": "#E63946",     # Systolic BP - red
        "dbp": "#F4A261",     # Diastolic BP - orange
        "hr": "#457B9D",      # Heart rate - blue
        "spo2": "#2A9D8F",    # SpO2 - teal
        "rr": "#9B5DE5",      # Resp. rate - purple
        "temp": "#E9C46A"     # Temperature - yellow
    }

    # Retain the existing reference bands, using muted styling in the light theme.
    reference_ranges = {
        'sbp': (90, 120), 'dbp': (60, 80), 'hr': (60, 100),
        'spo2': (95, 100), 'rr': (12, 18), 'temp': (36.5, 37.3),
    }
    # Create figure with subplots
    fig = make_subplots(
        rows=2, cols=3,
        subplot_titles=(
            "SBP (mmHg)",
            "DBP (mmHg)",
            "Heart Rate (bpm)",
            "Oxygen Saturation (%)",
            "Respiration (breaths/min)",
            "Temperature (°C)"
        ),
        vertical_spacing=0.16,
        horizontal_spacing=0.09,
        specs=[
            [{"type": "xy"}] * 3,
            [{"type": "xy"}] * 3
        ]
    )

    # Add reference shading and traces for each vital sign
    for i, (vital, title) in enumerate([
        ("sbp", "Systolic BP"),
        ("dbp", "Diastolic BP"),
        ("hr", "Heart Rate"),
        ("spo2", "SpO₂"),
        ("rr", "Respiration Rate"),
        ("temp", "Temperature")
    ]):
        row = (i // 3) + 1
        col = (i % 3) + 1

        # Add the actual data trace
        fig.add_trace(
            go.Scatter(
                x=df['datetime_tz'],
                y=df[vital],
                mode='lines+markers',
                name=title,
                line=dict(color=colors[vital], width=2),
                marker=dict(size=6, opacity=0.7),
                hovertemplate=(
                    f"<b>{title}</b><br>"
                    "Time: %{x|%Y-%m-%d %H:%M:%S}<br>"
                    "Value: %{y}<br>"
                    "<extra></extra>"
                ),
                customdata=df[['sbp', 'dbp', 'hr', 'spo2', 'rr', 'temp']],
                hoverinfo="text+x+y"
            ),
            row=row, col=col
        )

        # Plotly skips shapes on empty subplots: add the band after its trace.
        low, high = reference_ranges[vital]
        fig.add_hrect(y0=low, y1=high, fillcolor='#b9e4c9', opacity=0.4,
                      line_width=0, layer='below', row=row, col=col)
        for threshold in (low, high):
            fig.add_hline(y=threshold, line_dash='dot', line_color='#88a795',
                          line_width=1, row=row, col=col)

        # Customize axes
        fig.update_xaxes(
            tickformat="%H:%M\n%Y-%m-%d",
            row=row, col=col
        )

    fig.update_layout(
        autosize=True, showlegend=False,
        margin=dict(t=48, b=48, l=48, r=28),
        template="plotly_white", hovermode="x unified",
        font=dict(family="Segoe UI, Helvetica Neue, Arial, sans-serif", size=11, color="#18324f"),
        plot_bgcolor="#f6fafb", paper_bgcolor="#ffffff",
        modebar=dict(bgcolor="#ffffff", color="#61758c", activecolor="#07858f"),
    )
    fig.update_annotations(font=dict(size=14, color="#18324f"))
    fig.update_xaxes(matches='x', gridcolor='#e1eaf1', nticks=4, zeroline=False)
    fig.update_yaxes(gridcolor='#e1eaf1', zeroline=False, nticks=5)
    return fig
