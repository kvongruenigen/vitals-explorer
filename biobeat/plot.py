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

    # Calculate time range for title
    min_time = df['datetime_tz'].min()
    max_time = df['datetime_tz'].max()
    duration = max_time - min_time

    # Define visual styling
    colors = {
        "sbp": "#E63946",     # Systolic BP - red
        "dbp": "#F4A261",     # Diastolic BP - orange
        "hr": "#457B9D",      # Heart rate - blue
        "spo2": "#2A9D8F",    # SpO2 - teal
        "rr": "#9B5DE5",      # Resp. rate - purple
        "temp": "#E9C46A"     # Temperature - yellow
    }

    # Define normal ranges for each parameter (for background shading)
    normal_ranges = {
        "sbp": (90, 120), # mmHg
        "dbp": (60, 80), # mmHg
        "hr": (60, 100), # bpm
        "spo2": (95, 100), # %
        "rr": (12, 18), # breaths/min
        "temp": (36.5, 37.3)  # Celsius
    }

    # Create figure with subplots
    fig = make_subplots(
        rows=3, cols=2,
        subplot_titles=(
            "Systolic Blood Pressure (mmHg)",
            "Diastolic Blood Pressure (mmHg)",
            "Heart Rate (bpm)",
            "Oxygen Saturation (%)",
            "Respiration Rate (breaths/min)",
            "Temperature (°C)"
        ),
        vertical_spacing=0.15,  # Increased spacing
        horizontal_spacing=0.1,
        specs=[
            [{"type": "xy"}, {"type": "xy"}],
            [{"type": "xy"}, {"type": "xy"}],
            [{"type": "xy"}, {"type": "xy"}]
        ]
    )

    # Add normal range shading and traces for each vital sign
    for i, (vital, title) in enumerate([
        ("sbp", "Systolic BP"),
        ("dbp", "Diastolic BP"),
        ("hr", "Heart Rate"),
        ("spo2", "SpO₂"),
        ("rr", "Respiration Rate"),
        ("temp", "Temperature")
    ]):
        row = (i // 2) + 1
        col = (i % 2) + 1

        # Add normal range background
        if vital in normal_ranges:
            low, high = normal_ranges[vital]
            fig.add_shape(
                type="rect",
                x0=min_time, y0=low,
                x1=max_time, y1=high,
                fillcolor="lightgreen",
                opacity=0.2,
                layer="below",
                line_width=0,
                row=row, col=col
            )

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

        # Add threshold lines for normal ranges
        if vital in normal_ranges:
            low, high = normal_ranges[vital]
            for threshold, dash in [(low, "dash"), (high, "dash")]:
                fig.add_hline(
                    y=threshold,
                    line_dash=dash,
                    line_color="gray",
                    opacity=0.7,
                    annotation_text=f"{threshold}",
                    annotation_position="bottom right",
                    row=row, col=col
                )

        # Customize axes
        fig.update_xaxes(
            # title_text="Time" if row == 3 else "",  # Only show x-axis title on bottom row
            tickformat="%H:%M\n%Y-%m-%d",
            row=row, col=col
        )

    # Update layout with professional styling
    fig.update_layout(
        height=1200,
        title=dict(
            text=f"<b>Vital Signs Dashboard</b><br><span style='font-size:14px'>Time Range: {min_time.strftime('%Y-%m-%d %H:%M')} to {max_time.strftime('%Y-%m-%d %H:%M')} | Duration: {duration.days}d {duration.seconds//3600}h | Timezone: {user_tz}</span>",
            x=0.5,
            xanchor="center",
            font=dict(size=24),
            y=0.95  # Position title higher
        ),
        showlegend=False,
        margin=dict(t=150, b=80, l=50, r=50),  # Increased top and bottom margins
        template="plotly_white",
        hovermode="x unified",
        plot_bgcolor='rgba(240,240,240,0.8)',
        paper_bgcolor='rgba(255,255,255,0.9)'
    )

    # Link all x-axes for synchronized zoom/pan
    fig.update_layout(
        xaxis1=dict(matches='x3'),
        xaxis2=dict(matches='x3'),
        xaxis3=dict(matches='x5'),
        xaxis4=dict(matches='x5'),
        xaxis5=dict(domain=[0, 0.45]),  # Adjust domain to prevent overlap
        xaxis6=dict(domain=[0.55, 1])   # Adjust domain to prevent overlap
    )

    return fig
