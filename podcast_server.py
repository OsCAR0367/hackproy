import os
import base64
from google import genai
from google.genai import types
from elevenlabs.client import ElevenLabs
from flask import Flask, request, jsonify
from flask_cors import CORS

# Configuración de APIs
GEMINI_API_KEY = "AIzaSyAbdb0DY17CCQ0HflTUGXV73DYvtIyDEmw"
ELEVENLABS_API_KEY = "sk_b5f35fd39f4f29f87b1144ea8c7ca05bce4ed58f6658886c"

# Inicializar clientes
gemini_client = genai.Client(api_key=GEMINI_API_KEY)
elevenlabs_client = ElevenLabs(api_key=ELEVENLABS_API_KEY)

app = Flask(__name__)
CORS(app)

def transcribe_with_gemini(audio_path):
    """Transcribe audio using Gemini API"""
    try:
        print(f"Leyendo archivo de audio: {audio_path}")
        with open(audio_path, 'rb') as f:
            audio_bytes = f.read()
        
        # Detectar el tipo MIME del archivo
        extension = audio_path.lower().split('.')[-1]
        mime_types = {
            'mp3': 'audio/mpeg',
            'wav': 'audio/wav',
            'aac': 'audio/aac',
            'ogg': 'audio/ogg',
            'flac': 'audio/flac'
        }
        mime_type = mime_types.get(extension, 'audio/mpeg')
        
        print("Enviando audio a Gemini para transcripción...")
        response = gemini_client.models.generate_content(
            model='gemini-2.5-flash-lite',
            contents=[
                'Por favor, transcribe este audio de forma detallada y completa.',
                types.Part.from_bytes(
                    data=audio_bytes,
                    mime_type=mime_type
                )
            ]
        )
        
        transcription = response.text
        print("Transcripción completada")
        return transcription
    except Exception as e:
        print(f"Error en transcripción: {str(e)}")
        raise

def generate_summary_and_script(transcription):
    """Generate summary and podcast script using Gemini"""
    try:
        print("Generando resumen y guion de podcast...")
        prompt = f"""
Basándote en la siguiente transcripción, realiza dos tareas:

1. Genera un RESUMEN conciso de los puntos principales (máximo 3-4 párrafos)
2. Genera un GUION DE PODCAST profesional y atractivo basado en el contenido

Formato de salida:
=== RESUMEN ===
[Tu resumen aquí]

=== GUION DE PODCAST ===
[Tu guion de podcast aquí]

El guion de podcast debe:
- Tener un tono conversacional y atractivo
- Incluir una introducción enganchadora
- Desarrollar los puntos principales de forma clara
- Tener una conclusión memorable
- Durar aproximadamente 2-3 minutos cuando se lea

TRANSCRIPCIÓN:
{transcription}
"""
        
        response = gemini_client.models.generate_content(
            model='gemini-2.5-flash-lite',
            contents=[prompt]
        )
        
        result = response.text
        print("Resumen y guion generados")
        
        # Separar el resumen y el guion
        parts = result.split('=== GUION DE PODCAST ===')
        summary = parts[0].replace('=== RESUMEN ===', '').strip()
        script = parts[1].strip() if len(parts) > 1 else result
        
        return summary, script
    except Exception as e:
        print(f"Error generando contenido: {str(e)}")
        raise

def generate_podcast_audio(script):
    """Generate podcast audio using ElevenLabs"""
    try:
        print("Generando audio del podcast con ElevenLabs...")
        
        # Usar una voz predeterminada de ElevenLabs
        # Rachel (21m00Tcm4TlvDq8ikWAM) es una voz popular para podcasts
        voice_id = "21m00Tcm4TlvDq8ikWAM"
        
        # Usando Flash v2.5 - el modelo más económico (0.5 créditos por cada 2 caracteres)
        audio_generator = elevenlabs_client.text_to_speech.convert(
            text=script,
            voice_id=voice_id,
            model_id="eleven_flash_v2_5",
            output_format="mp3_44100_128"
        )
        
        # Guardar el audio en D:/
        output_path = "D:/podcast_generado.mp3"
        
        print(f"Guardando podcast en: {output_path}")
        with open(output_path, 'wb') as f:
            for chunk in audio_generator:
                if chunk:
                    f.write(chunk)
        
        print("Podcast generado exitosamente")
        return output_path
    except Exception as e:
        print(f"Error generando audio: {str(e)}")
        raise

@app.route('/process_audio', methods=['POST'])
def process_audio():
    """Main endpoint to process audio file"""
    try:
        data = request.json
        audio_path = data.get('audio_path')
        
        if not audio_path:
            return jsonify({'error': 'No se proporcionó la ruta del audio'}), 400
        
        if not os.path.exists(audio_path):
            return jsonify({'error': f'El archivo no existe: {audio_path}'}), 404
        
        # Paso 1: Transcribir audio
        print("\n=== PASO 1: TRANSCRIPCIÓN ===")
        transcription = transcribe_with_gemini(audio_path)
        
        # Paso 2: Generar resumen y guion
        print("\n=== PASO 2: GENERACIÓN DE CONTENIDO ===")
        summary, script = generate_summary_and_script(transcription)
        
        # Paso 3: Generar audio del podcast
        print("\n=== PASO 3: GENERACIÓN DE AUDIO ===")
        podcast_path = generate_podcast_audio(script)
        
        print("\n=== PROCESO COMPLETADO ===")
        
        return jsonify({
            'success': True,
            'transcription': transcription,
            'summary': summary,
            'script': script,
            'podcast_path': podcast_path,
            'message': 'Podcast generado exitosamente'
        })
        
    except Exception as e:
        print(f"\n=== ERROR ===")
        print(str(e))
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'ok', 'message': 'Servidor funcionando correctamente'})

if __name__ == '__main__':
    print("=== INICIANDO SERVIDOR DE GENERACIÓN DE PODCASTS ===")
    print("Servidor disponible en: http://localhost:5000")
    print("Asegúrate de que el directorio D:/ existe y tienes permisos de escritura")
    app.run(debug=True, host='0.0.0.0', port=5000)