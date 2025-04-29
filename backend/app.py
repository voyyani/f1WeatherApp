from flask import Flask, request, jsonify, render_template
from flask_cors import CORS  # <-- CORS fix
from analysis import analyze_weather

app = Flask(__name__,
            static_folder='../frontend/static',
            template_folder='../frontend/templates')

# Enable CORS for all routes
CORS(app)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    data = request.json
    result = analyze_weather(
        data['year'],
        data['gp'], 
        data['driver'],
        data['session_type']
    )
    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True)