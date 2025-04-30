from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from analysis import analyze_weather

app = Flask(__name__, static_folder='../frontend/static', template_folder='../frontend/templates')
CORS(app)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        data = request.json
        result = analyze_weather(
            int(data['year']),
            str(data['gp']),
            str(data['driver']),
            str(data['session_type'])
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': f'Invalid input: {str(e)}'})

if __name__ == '__main__':
    app.run(debug=True)