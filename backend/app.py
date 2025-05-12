from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from datetime import datetime
import fastf1
from fastf1.core import DataNotLoadedError
from functools import lru_cache
from analysis import analyze_weather

# --------------------------------------------------------
# Flask application for F1 Analytics Pro (app.py)
# --------------------------------------------------------

# Configure FastF1 cache (local folder for downloaded data)
fastf1.Cache.enable_cache('./f1_cache')

# Initialize Flask app and enable CORS
app = Flask(
    __name__,
    static_folder='../frontend/static',
    template_folder='../frontend/templates'
)
CORS(app)

@app.route('/')
def landing():
    """Serve the landing page"""
    return render_template('landing.html')

@app.route('/weather')
def weather_analyzer():
    """Serve the weather analysis tool"""
    return render_template('weather.html')

@app.route('/api/years')
def get_years():
    """Return a list of seasons from 1950 up to the current year"""
    current_year = datetime.now().year
    return jsonify(list(range(1950, current_year + 1)))

# Internal helper to fetch teams, cached per year
def _fetch_teams_for_year(year):
    schedule = fastf1.get_event_schedule(year)
    events = schedule[schedule['EventFormat'].str.lower() != 'testing']
    if events.empty:
        raise ValueError(f'No events found for {year}')

    first_event = events.iloc[0]
    gp_name = first_event['EventName']
    session = fastf1.get_session(year, gp_name, 'R')
    session.load(telemetry=False, weather=False, messages=False)

    teams = {}
    cols = session.results.columns
    for _, result in session.results.iterrows():
        team_name = result.get('Team') or result.get('TeamName') or 'Unknown Team'
        if 'FullName' in cols:
            driver_name = result.get('FullName', 'Unknown Driver')
        else:
            first = result.get('FirstName', '')
            last = result.get('LastName', '')
            driver_name = f"{first} {last}".strip() or 'Unknown Driver'

        driver_number = result.get('DriverNumber') or result.get('CarNumber', 'N/A')
        driver_code = result.get('Abbreviation') or result.get('DriverCode', '')

        teams.setdefault(team_name, []).append({
            'name': driver_name,
            'number': driver_number,
            'code': driver_code
        })

    return [{'name': team, 'drivers': drivers} for team, drivers in teams.items()]
# Cache the helper per year
_fetch_teams_for_year = lru_cache(maxsize=16)(_fetch_teams_for_year)

@app.route('/api/teams')
def get_teams():
    """Return teams and their drivers for a given season year."""
    year_str = request.args.get('year')
    if not year_str:
        return jsonify({'error': 'Year parameter required'}), 400
    try:
        year = int(year_str)
        teams = _fetch_teams_for_year(year)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    return jsonify(teams)

@app.route('/api/gps')
def get_gps():
    """Return list of Grand Prix names and countries for a given season"""
    year_str = request.args.get('year')
    if not year_str:
        return jsonify({'error': 'Year parameter required'}), 400
    try:
        year = int(year_str)
    except ValueError:
        return jsonify({'error': 'Invalid year parameter'}), 400

    schedule = fastf1.get_event_schedule(year)
    events = [{'name': e['EventName'], 'country': e['Country']} for _, e in schedule.iterrows()]
    return jsonify(events)

@app.route('/api/drivers')
def get_drivers():
    """Return list of driver codes who participated in a given GP session"""
    year_str = request.args.get('year')
    gp = request.args.get('gp')
    session_type = request.args.get('session_type', 'R')
    
    if not year_str or not gp:
        return jsonify({'error': 'Year and GP parameters required'}), 400
    
    try:
        year = int(year_str)
    except ValueError:
        return jsonify({'error': 'Invalid year parameter'}), 400

    try:
        # First verify the GP exists in the schedule
        schedule = fastf1.get_event_schedule(year)
        if gp not in schedule['EventName'].values:
            return jsonify({'error': f'Grand Prix {gp} not found in {year}'}), 404

        # Load session data
        session = fastf1.get_session(year, gp, session_type)
        
        try:
            # First try to get drivers from laps
            session.load(laps=True, telemetry=False, weather=False, messages=False)
            if not session.laps.empty:
                driver_codes = session.laps['Driver'].unique().tolist()
                return jsonify(sorted(driver_codes))
        except DataNotLoadedError:
            # Fallback to session results if laps unavailable
            session.load(telemetry=False, weather=False, messages=False)
            if not session.results.empty:
                driver_codes = session.results['Abbreviation'].dropna().unique().tolist()
                return jsonify(sorted(driver_codes))

        # Final fallback to driver info
        session.load(telemetry=False, weather=False, messages=False)
        if session.drivers:
            return jsonify(sorted(session.drivers))

        return jsonify({'error': f'No driver data available for {gp} {year} {session_type}'}), 404

    except DataNotLoadedError:
        return jsonify({'error': f'Session data not available for {gp} {year} {session_type}'}), 404
    except Exception as e:
        app.logger.error(f'Error loading drivers: {str(e)}')
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500
    
@app.route('/analyze', methods=['POST'])
def analyze():
    """Perform weather impact analysis for a selected year, GP, driver, and session type"""
    data = request.json or {}
    try:
        year = int(data['year'])
        gp = str(data['gp'])
        driver = str(data['driver'])
        session_type = str(data['session_type'])
    except (KeyError, ValueError) as e:
        return jsonify({'success': False, 'error': f'Invalid input: {e}'}), 400

    result = analyze_weather(year, gp, driver, session_type)
    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True)