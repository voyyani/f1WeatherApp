# backend/analysis.py
import os
import fastf1
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from io import BytesIO
import base64

def analyze_weather(year, gp, driver, session_type):
    """Analyze weather impact for a specific F1 session"""
    temp_corr = None
    rain_corr = None
    plot_url = None
    
    try:
        # Set up cache
        cache_path = './f1_cache'
        os.makedirs(cache_path, exist_ok=True)
        fastf1.Cache.enable_cache(cache_path)

        # Load session data
        session = fastf1.get_session(year, gp, session_type)
        session.load(telemetry=True, weather=True)
        
        # Get driver laps
        driver_laps = session.laps.pick_drivers([driver]).copy()
        
        # Merge with weather data
        merged_data = pd.merge_asof(
            driver_laps.sort_values('LapStartTime'),
            session.weather_data.reset_index().sort_values('Time'),
            left_on='LapStartTime',
            right_on='Time',
            direction='nearest'
        ).copy()

        # Filter valid laps
        valid_laps = merged_data[
            (merged_data['LapTime'].notna()) &
            (merged_data['IsAccurate'])
        ].copy()

        if valid_laps.empty:
            return {'success': False, 'error': 'No valid laps found'}

        # Process data
        valid_laps.loc[:, 'Rainfall'] = valid_laps['Rainfall'].fillna(0)
        valid_laps.loc[:, 'LapTime_sec'] = valid_laps['LapTime'].dt.total_seconds()

        # Calculate correlations
        temp_corr = valid_laps['TrackTemp'].corr(valid_laps['LapTime_sec'])
        
        if valid_laps['Rainfall'].nunique() > 1:
            rain_corr = valid_laps['Rainfall'].corr(valid_laps['LapTime_sec'])
        else:
            rain_corr = np.nan

        # Generate plot
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
        
        # Track Temperature plot
        ax1.plot(valid_laps['LapNumber'], valid_laps['LapTime_sec'], 'r-')
        ax1.set_ylabel('Lap Time (s)', color='red')
        ax1_temp = ax1.twinx()
        ax1_temp.plot(valid_laps['LapNumber'], valid_laps['TrackTemp'], 'b-')
        ax1_temp.set_ylabel('Track Temp (°C)', color='blue')

        # Rainfall plot
        ax2.plot(valid_laps['LapNumber'], valid_laps['LapTime_sec'], 'r-')
        ax2.set_xlabel('Lap Number')
        ax2.set_ylabel('Lap Time (s)', color='red')
        ax2_rain = ax2.twinx()
        ax2_rain.plot(valid_laps['LapNumber'], valid_laps['Rainfall'], 'g-')
        ax2_rain.set_ylabel('Rainfall (mm/h)', color='green')

        # Save plot to bytes
        img = BytesIO()
        plt.savefig(img, format='png', bbox_inches='tight')
        plt.close()
        img.seek(0)
        plot_url = base64.b64encode(img.getvalue()).decode('utf-8')

        return {
            'success': True,
            'plot': plot_url,
            'temp_corr': float(temp_corr) if not np.isnan(temp_corr) else None,
            'rain_corr': float(rain_corr) if not np.isnan(rain_corr) else None
        }

    except Exception as e:
        return {'success': False, 'error': str(e)}