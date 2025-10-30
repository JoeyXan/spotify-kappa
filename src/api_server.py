"""
API REST - Arquitectura Kappa
Expone endpoints para consultar recomendaciones
"""

from flask import Flask, jsonify, request, render_template_string
from flask_cors import CORS
import threading
from stream_processor import KappaStreamProcessor
from event_producer import EventProducer

app = Flask(__name__)
CORS(app)

# Instancia global del procesador
processor = None
producer = None

def init_processor():
    """
    Inicializa el procesador en un thread separado
    """
    global processor
    processor = KappaStreamProcessor()
    
    # Intentar cargar estado guardado
    if not processor.load_state('model_state.pkl'):
        processor.load_initial_data('data/dataset.csv')
    
    # Iniciar consumidor en thread separado
    consumer_thread = threading.Thread(target=processor.start_consumer, daemon=True)
    consumer_thread.start()

def init_producer():
    """
    Inicializa el productor de eventos
    """
    global producer
    producer = EventProducer()
    producer.load_tracks('data/dataset.csv')

@app.route('/')
def home():
    """
    Página principal con dashboard
    """
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Sistema de Recomendación - Arquitectura Kappa</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 1200px;
                margin: 0 auto;
                padding: 20px;
                background-color: #f5f5f5;
            }
            h1 {
                color: #333;
                border-bottom: 3px solid #1DB954;
                padding-bottom: 10px;
            }
            .container {
                background: white;
                padding: 20px;
                border-radius: 8px;
                margin-bottom: 20px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            .endpoint {
                background: #f9f9f9;
                padding: 15px;
                margin: 10px 0;
                border-left: 4px solid #1DB954;
            }
            .method {
                display: inline-block;
                padding: 3px 8px;
                background: #1DB954;
                color: white;
                border-radius: 3px;
                font-weight: bold;
                margin-right: 10px;
            }
            code {
                background: #f4f4f4;
                padding: 2px 6px;
                border-radius: 3px;
                font-family: monospace;
            }
            .stats {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 15px;
                margin-top: 20px;
            }
            .stat-card {
                background: linear-gradient(135deg, #1DB954 0%, #1ed760 100%);
                color: white;
                padding: 20px;
                border-radius: 8px;
                text-align: center;
            }
            .stat-value {
                font-size: 32px;
                font-weight: bold;
            }
            .stat-label {
                font-size: 14px;
                opacity: 0.9;
            }
        </style>
    </head>
    <body>
        <h1>Sistema de Recomendación de Música - Arquitectura Kappa</h1>
        
        <div class="container">
            <h2>Estado del Sistema</h2>
            <div class="stats" id="stats">
                <div class="stat-card">
                    <div class="stat-value" id="total-tracks">-</div>
                    <div class="stat-label">Canciones</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value" id="total-users">-</div>
                    <div class="stat-label">Usuarios Activos</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value" id="total-interactions">-</div>
                    <div class="stat-label">Interacciones</div>
                </div>
            </div>
        </div>
        
        <div class="container">
            <h2>Endpoints Disponibles</h2>
            
            <div class="endpoint">
                <span class="method">GET</span>
                <code>/api/stats</code>
                <p>Obtiene estadísticas del sistema</p>
            </div>
            
            <div class="endpoint">
                <span class="method">GET</span>
                <code>/api/tracks</code>
                <p>Lista todas las canciones disponibles</p>
            </div>
            
            <div class="endpoint">
                <span class="method">POST</span>
                <code>/api/recommend</code>
                <p>Obtiene recomendaciones para una canción</p>
                <p>Body: <code>{"track_id": "...", "user_id": "...", "top_n": 10}</code></p>
            </div>
            
            <div class="endpoint">
                <span class="method">POST</span>
                <code>/api/interact</code>
                <p>Registra una interacción de usuario</p>
                <p>Body: <code>{"user_id": "...", "track_id": "...", "interaction_type": "play|like|skip"}</code></p>
            </div>
            
            <div class="endpoint">
                <span class="method">GET</span>
                <code>/api/trending</code>
                <p>Obtiene las canciones más populares en tiempo real</p>
            </div>
            
            <div class="endpoint">
                <span class="method">GET</span>
                <code>/api/user/&lt;user_id&gt;</code>
                <p>Obtiene el perfil de un usuario</p>
            </div>
        </div>
        
        <script>
            function updateStats() {
                fetch('/api/stats')
                    .then(r => r.json())
                    .then(data => {
                        document.getElementById('total-tracks').textContent = data.total_tracks;
                        document.getElementById('total-users').textContent = data.total_users;
                        document.getElementById('total-interactions').textContent = data.total_interactions;
                    });
            }
            
            updateStats();
            setInterval(updateStats, 5000);
        </script>
    </body>
    </html>
    """
    return render_template_string(html)

@app.route('/api/stats')
def get_stats():
    """
    Obtiene estadísticas del sistema
    """
    total_interactions = sum(len(interactions) for interactions in processor.user_interactions.values())
    
    return jsonify({
        'total_tracks': len(processor.tracks_df),
        'total_users': len(processor.user_interactions),
        'total_interactions': total_interactions,
        'track_popularity_count': len(processor.track_popularity)
    })

@app.route('/api/tracks')
def get_tracks():
    """
    Lista todas las canciones
    """
    tracks = processor.tracks_df[['track_id', 'track_name', 'artists', 'track_genre']].head(100).to_dict('records')
    return jsonify(tracks)

@app.route('/api/recommend', methods=['POST'])
def get_recommendations():
    """
    Obtiene recomendaciones para una canción
    """
    data = request.json
    track_id = data.get('track_id')
    user_id = data.get('user_id')
    top_n = data.get('top_n', 10)
    
    if not track_id:
        return jsonify({'error': 'track_id es requerido'}), 400
    
    recommendations = processor.get_recommendations(track_id, user_id, top_n)
    
    return jsonify({
        'track_id': track_id,
        'user_id': user_id,
        'recommendations': recommendations
    })

@app.route('/api/interact', methods=['POST'])
def register_interaction():
    """
    Registra una interacción de usuario
    """
    data = request.json
    user_id = data.get('user_id')
    track_id = data.get('track_id')
    interaction_type = data.get('interaction_type', 'play')
    
    if not user_id or not track_id:
        return jsonify({'error': 'user_id y track_id son requeridos'}), 400
    
    # Enviar evento a Kafka
    event = producer.send_interaction(user_id, track_id, interaction_type)
    
    return jsonify({
        'success': True,
        'event': event
    })

@app.route('/api/trending')
def get_trending():
    """
    Obtiene canciones trending
    """
    top_n = request.args.get('top_n', 10, type=int)
    trending = processor.get_trending_tracks(top_n)
    
    return jsonify(trending)

@app.route('/api/user/<user_id>')
def get_user_profile(user_id):
    """
    Obtiene perfil de usuario
    """
    profile = processor.get_user_profile(user_id)
    
    if not profile:
        return jsonify({'error': 'Usuario no encontrado'}), 404
    
    return jsonify(profile)

@app.route('/api/search')
def search_tracks():
    """
    Busca canciones por nombre
    """
    query = request.args.get('q', '')
    
    if not query:
        return jsonify([])
    
    results = processor.tracks_df[
        processor.tracks_df['track_name'].str.contains(query, case=False, na=False)
    ].head(20)
    
    return jsonify(results[['track_id', 'track_name', 'artists', 'track_genre']].to_dict('records'))

if __name__ == '__main__':
    print("Inicializando sistema...")
    init_processor()
    init_producer()
    print("Sistema listo. Iniciando API...")
    app.run(host='0.0.0.0', port=5000, debug=False)
