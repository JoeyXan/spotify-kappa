"""
Stream Processor - Arquitectura Kappa
Procesa eventos de interacciones de usuario en tiempo real
"""

import json
import time
import numpy as np
import pandas as pd
from datetime import datetime
from collections import defaultdict
from kafka import KafkaConsumer, KafkaProducer
from sklearn.preprocessing import StandardScaler
from sklearn.metrics.pairwise import cosine_similarity
import pickle
import threading

class KappaStreamProcessor:
    """
    Procesador de streams para Arquitectura Kappa
    Actualiza modelo en tiempo real con cada evento
    """
    
    def __init__(self, kafka_bootstrap_servers='localhost:9092'):
        self.kafka_servers = kafka_bootstrap_servers
        self.scaler = StandardScaler()
        self.tracks_df = None
        self.similarity_matrix = None
        self.user_interactions = defaultdict(list)
        self.track_popularity = defaultdict(int)
        self.track_features = {}
        
        self.audio_features = [
            'danceability', 'energy', 'key', 'loudness', 'mode',
            'speechiness', 'acousticness', 'instrumentalness',
            'liveness', 'valence', 'tempo'
        ]
        
        self.lock = threading.Lock()
        
    def load_initial_data(self, csv_path):
        """
        Carga datos iniciales y prepara el modelo base
        """
        print("Cargando dataset inicial...")
        df = pd.read_csv(csv_path)
        
        # Tomar muestra representativa
        df_sample = df.groupby('track_genre', group_keys=False).apply(
            lambda x: x.sample(min(len(x), 50), random_state=42)
        ).reset_index(drop=True)
        
        self.tracks_df = df_sample
        
        # Preparar features
        features = self.tracks_df[self.audio_features].fillna(0)
        features_scaled = self.scaler.fit_transform(features)
        
        # Calcular similitud inicial
        self.similarity_matrix = cosine_similarity(features_scaled)
        
        # Guardar features por track
        for idx, row in self.tracks_df.iterrows():
            self.track_features[row['track_id']] = features_scaled[idx]
        
        print(f"Modelo inicial cargado: {len(self.tracks_df)} canciones")
        
    def start_consumer(self):
        """
        Inicia el consumidor de Kafka para procesar eventos
        """
        try:
            consumer = KafkaConsumer(
                'user-interactions',
                bootstrap_servers=self.kafka_servers,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                auto_offset_reset='latest',
                enable_auto_commit=True
            )
            
            print("Consumidor de Kafka iniciado. Esperando eventos...")
            
            for message in consumer:
                event = message.value
                self.process_event(event)
                
        except Exception as e:
            print(f"Error en consumidor: {e}")
            
    def process_event(self, event):
        """
        Procesa un evento de interacción en tiempo real
        """
        with self.lock:
            user_id = event.get('user_id')
            track_id = event.get('track_id')
            interaction_type = event.get('interaction_type', 'play')
            timestamp = event.get('timestamp', datetime.now().isoformat())
            
            # Registrar interacción
            self.user_interactions[user_id].append({
                'track_id': track_id,
                'type': interaction_type,
                'timestamp': timestamp
            })
            
            # Mantener solo últimas 100 interacciones
            self.user_interactions[user_id] = self.user_interactions[user_id][-100:]
            
            # Actualizar popularidad
            weight = {'play': 1, 'like': 3, 'skip': -1}.get(interaction_type, 1)
            self.track_popularity[track_id] += weight
            
            print(f"Evento procesado: {user_id} - {interaction_type} - {track_id[:8]}...")
            
    def get_recommendations(self, track_id, user_id=None, top_n=10):
        """
        Genera recomendaciones en tiempo real
        """
        with self.lock:
            # Buscar índice de la canción
            track_idx = self.tracks_df[self.tracks_df['track_id'] == track_id].index
            
            if len(track_idx) == 0:
                return []
            
            track_idx = track_idx[0]
            
            # Obtener similitudes
            sim_scores = list(enumerate(self.similarity_matrix[track_idx]))
            sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)
            sim_scores = sim_scores[1:top_n*2]
            
            # Aplicar boost de popularidad
            boosted_scores = []
            for idx, score in sim_scores:
                track = self.tracks_df.iloc[idx]
                popularity_boost = self.track_popularity.get(track['track_id'], 0) * 0.01
                final_score = score + popularity_boost
                boosted_scores.append((idx, final_score, track))
            
            # Aplicar personalización por usuario
            if user_id and user_id in self.user_interactions:
                user_history = self.user_interactions[user_id]
                liked_tracks = [i['track_id'] for i in user_history if i['type'] == 'like']
                
                if liked_tracks:
                    liked_genres = set()
                    for tid in liked_tracks:
                        track_row = self.tracks_df[self.tracks_df['track_id'] == tid]
                        if not track_row.empty:
                            liked_genres.add(track_row.iloc[0]['track_genre'])
                    
                    # Boost por género preferido
                    for i, (idx, score, track) in enumerate(boosted_scores):
                        if track['track_genre'] in liked_genres:
                            boosted_scores[i] = (idx, score * 1.2, track)
            
            # Ordenar y retornar top N
            boosted_scores = sorted(boosted_scores, key=lambda x: x[1], reverse=True)
            boosted_scores = boosted_scores[:top_n]
            
            recommendations = []
            for idx, score, track in boosted_scores:
                recommendations.append({
                    'track_id': track['track_id'],
                    'track_name': track['track_name'],
                    'artists': track['artists'],
                    'track_genre': track['track_genre'],
                    'score': float(score),
                    'popularity': self.track_popularity.get(track['track_id'], 0)
                })
            
            return recommendations
    
    def get_user_profile(self, user_id):
        """
        Obtiene el perfil de un usuario basado en su historial
        """
        with self.lock:
            if user_id not in self.user_interactions:
                return None
            
            interactions = self.user_interactions[user_id]
            
            liked = [i for i in interactions if i['type'] == 'like']
            played = [i for i in interactions if i['type'] == 'play']
            skipped = [i for i in interactions if i['type'] == 'skip']
            
            return {
                'user_id': user_id,
                'total_interactions': len(interactions),
                'likes': len(liked),
                'plays': len(played),
                'skips': len(skipped),
                'recent_tracks': interactions[-5:]
            }
    
    def get_trending_tracks(self, top_n=10):
        """
        Obtiene las canciones más populares en tiempo real
        """
        with self.lock:
            sorted_tracks = sorted(
                self.track_popularity.items(),
                key=lambda x: x[1],
                reverse=True
            )[:top_n]
            
            trending = []
            for track_id, popularity in sorted_tracks:
                track_row = self.tracks_df[self.tracks_df['track_id'] == track_id]
                if not track_row.empty:
                    track = track_row.iloc[0]
                    trending.append({
                        'track_id': track_id,
                        'track_name': track['track_name'],
                        'artists': track['artists'],
                        'track_genre': track['track_genre'],
                        'popularity': popularity
                    })
            
            return trending
    
    def save_state(self, filepath='model_state.pkl'):
        """
        Guarda el estado actual del modelo
        """
        with self.lock:
            state = {
                'similarity_matrix': self.similarity_matrix,
                'scaler': self.scaler,
                'tracks_df': self.tracks_df,
                'user_interactions': dict(self.user_interactions),
                'track_popularity': dict(self.track_popularity),
                'track_features': self.track_features
            }
            
            with open(filepath, 'wb') as f:
                pickle.dump(state, f)
            
            print(f"Estado guardado en {filepath}")
    
    def load_state(self, filepath='model_state.pkl'):
        """
        Carga el estado del modelo
        """
        try:
            with open(filepath, 'rb') as f:
                state = pickle.load(f)
            
            self.similarity_matrix = state['similarity_matrix']
            self.scaler = state['scaler']
            self.tracks_df = state['tracks_df']
            self.user_interactions = defaultdict(list, state['user_interactions'])
            self.track_popularity = defaultdict(int, state['track_popularity'])
            self.track_features = state['track_features']
            
            print(f"Estado cargado desde {filepath}")
            return True
        except FileNotFoundError:
            print(f"Archivo {filepath} no encontrado")
            return False

if __name__ == "__main__":
    processor = KappaStreamProcessor()
    processor.load_initial_data('data/dataset.csv')
    processor.start_consumer()
