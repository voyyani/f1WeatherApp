import os
import fastf1
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from io import BytesIO
import base64

def analyze_weather(year, gp, driver, session_type):
    try:
        # Configure cache and matplotlib
        cache_dir = './f1_cache'
        os.makedirs(cache_dir, exist_ok=True)
        fastf1.Cache.enable_cache(cache_dir)
        plt.switch_backend('Agg')

        # Load session data
        session = fastf1.get_session(int(year), gp, session_type)
        session.load(telemetry=True, weather=True)
        
        # Get driver data
        driver_laps = session.laps.pick_drivers([driver.upper()])
        weather_data = session.weather_data
        
        # Merge and clean data
        merged = pd.merge_asof(
            driver_laps.sort_values('LapStartTime'),
            weather_data.reset_index().sort_values('Time'),
            left_on='LapStartTime',
            right_on='Time'
        )
        
        valid_laps = merged[
            (merged['IsAccurate']) & 
            (merged['LapTime'].notna())
        ].copy()
        
        if valid_laps.empty:
            return {'success': False, 'error': 'No valid laps found'}
        
        # Convert data types
        valid_laps['LapNumber'] = valid_laps['LapNumber'].astype(int)
        valid_laps['TrackTemp'] = valid_laps['TrackTemp'].astype(float)
        valid_laps['Rainfall'] = valid_laps['Rainfall'].astype(float)
        valid_laps['LapTime_sec'] = valid_laps['LapTime'].dt.total_seconds().astype(float)
        
        # Calculate correlations
        temp_corr = valid_laps['TrackTemp'].corr(valid_laps['LapTime_sec'])
        rain_corr = valid_laps['Rainfall'].corr(valid_laps['LapTime_sec']) if valid_laps['Rainfall'].nunique() > 1 else None
        
        # Generate plot with improved styling
        plt.style.use('dark_background')
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
        fig.suptitle(f'{driver} - {gp} {year} ({session_type})\nWeather Impact Analysis', 
                    fontsize=14, y=1.02, color='white', fontweight='bold')

        # Temperature Plot
        ax1.plot(valid_laps['LapNumber'], valid_laps['LapTime_sec'], 
                color='#FF1801', linewidth=2, label='Lap Time')
        ax1.set_ylabel('Lap Time (seconds)', 
                      color='white', fontsize=12, fontweight='bold')
        ax1.tick_params(axis='y', colors='white')
        ax1.grid(alpha=0.3, linestyle='--')
        
        ax_temp = ax1.twinx()
        ax_temp.plot(valid_laps['LapNumber'], valid_laps['TrackTemp'], 
                    color='#00FFFF', linewidth=2, linestyle=':', label='Track Temperature')
        ax_temp.set_ylabel('Temperature (°C)', 
                          color='#00FFFF', fontsize=12, fontweight='bold')
        ax_temp.tick_params(axis='y', colors='#00FFFF')

        # Rainfall Plot
        ax2.plot(valid_laps['LapNumber'], valid_laps['LapTime_sec'], 
                color='#FF1801', linewidth=2)
        ax2.set_xlabel('Lap Number', 
                      color='white', fontsize=12, fontweight='bold')
        ax2.set_ylabel('Lap Time (seconds)', 
                      color='white', fontsize=12, fontweight='bold')
        ax2.tick_params(colors='white')
        ax2.grid(alpha=0.3, linestyle='--')
        
        ax_rain = ax2.twinx()
        ax_rain.plot(valid_laps['LapNumber'], valid_laps['Rainfall'], 
                    color='#CCFF00', linewidth=2, linestyle='-.', label='Rainfall')
        ax_rain.set_ylabel('Rainfall (mm/h)', 
                          color='#CCFF00', fontsize=12, fontweight='bold')
        ax_rain.tick_params(axis='y', colors='#CCFF00')

        # Add legends
        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax_temp.get_legend_handles_labels()
        ax1.legend(lines1 + lines2, labels1 + labels2, 
                 loc='upper left', 
                 framealpha=0.2, 
                 facecolor='black',
                 fontsize=10)

        lines3, labels3 = ax_rain.get_legend_handles_labels()
        ax_rain.legend(lines3, labels3,
                      loc='upper right',
                      framealpha=0.2,
                      facecolor='black',
                      fontsize=10)

        # Adjust layout
        plt.tight_layout(pad=3.0)
        
        # Save to buffer
        buf = BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight', dpi=100)
        plt.close()
        
        return {
            'success': True,
            'plot': base64.b64encode(buf.getvalue()).decode('utf-8'),
            'temp_corr': float(temp_corr),
            'rain_corr': float(rain_corr) if rain_corr else None
        }
        
    except Exception as e:
        return {'success': False, 'error': str(e)}