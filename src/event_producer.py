"""
Event Producer - Genera eventos de interacciones de usuario
"""

import json
import time
import random
from datetime import datetime
from kafka import KafkaProducer
import pandas as pd

class EventProducer:
    """
    Productor de eventos para simular interacciones de usuario
    """
    
    def __init__(self, kafka_bootstrap_servers='localhost:9092'):
        self.producer = KafkaProducer(
            bootstrap_servers=kafka_bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        self.tracks = []
        
    def load_tracks(self, csv_path):
        """
        Carga el catálogo de canciones
        """
        df = pd.read_csv(csv_path)
        self.tracks = df[['track_id', 'track_name', 'artists']].to_dict('records')
        print(f"Cargadas {len(self.tracks)} canciones")
        
    def send_interaction(self, user_id, track_id, interaction_type='play'):
        """
        Envía un evento de interacción a Kafka
        """
        event = {
            'user_id': user_id,
            'track_id': track_id,
            'interaction_type': interaction_type,
            'timestamp': datetime.now().isoformat()
        }
        
        self.producer.send('user-interactions', value=event)
        self.producer.flush()
        
        return event
    
    def simulate_user_activity(self, num_users=10, duration_seconds=60):
        """
        Simula actividad de usuarios por un tiempo determinado
        """
        print(f"Simulando actividad de {num_users} usuarios por {duration_seconds} segundos...")
        
        start_time = time.time()
        event_count = 0
        
        while time.time() - start_time < duration_seconds:
            user_id = f"user_{random.randint(1, num_users)}"
            track = random.choice(self.tracks)
            interaction_type = random.choices(
                ['play', 'like', 'skip'],
                weights=[0.7, 0.2, 0.1]
            )[0]
            
            event = self.send_interaction(user_id, track['track_id'], interaction_type)
            event_count += 1
            
            print(f"[{event_count}] {user_id} - {interaction_type} - {track['track_name'][:30]}")
            
            time.sleep(random.uniform(0.5, 2.0))
        
        print(f"Simulación completada: {event_count} eventos generados")

if __name__ == "__main__":
    producer = EventProducer()
    producer.load_tracks('data/dataset.csv')
    producer.simulate_user_activity(num_users=5, duration_seconds=30)
