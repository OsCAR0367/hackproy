"""
TECSUP - Sistema de Generación de Materiales Educativos con IA
Hackathon: Educación Superior sin Deserción Estudiantil
 
Backend Flask mejorado con endpoints adicionales y mejor estructura
"""
 
import os
import base64
import json
from datetime import datetime
from werkzeug.utils import secure_filename
from google import genai
from google.genai import types
from elevenlabs.client import ElevenLabs
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
 
# Configuración de APIs
GEMINI_API_KEY = "AIzaSyAEBGkJwIFYFftM5F-TjjxTke23fcZHytA"
ELEVENLABS_API_KEY = "sk_b02a6993ce3e8f1f921637ef88a7b6178a2f6ed6d14e9135"
 
# Configuración de carpetas
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'output'
ALLOWED_EXTENSIONS = {'mp3', 'wav', 'aac', 'ogg', 'flac', 'm4a', 'wma'}
 
# Crear carpetas si no existen
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
 
# Inicializar clientes
gemini_client = genai.Client(api_key=GEMINI_API_KEY)
elevenlabs_client = ElevenLabs(api_key=ELEVENLABS_API_KEY)
 
app = Flask(__name__)
CORS(app)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max
 
def allowed_file(filename):
    """Verificar si el archivo tiene una extensión válida"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
 
def get_file_size_mb(filepath):
    """Obtener tamaño del archivo en MB"""
    return os.path.getsize(filepath) / (1024 * 1024)
 
def transcribe_with_gemini(audio_path, progress_callback=None):
    """Transcribe audio using Gemini API con callback de progreso"""
    try:
        if progress_callback:
            progress_callback(10, "Leyendo archivo de audio...")
 
        with open(audio_path, 'rb') as f:
            audio_bytes = f.read()
 
        # Detectar el tipo MIME del archivo
        extension = audio_path.lower().split('.')[-1]
        mime_types = {
            'mp3': 'audio/mpeg',
            'wav': 'audio/wav',
            'aac': 'audio/aac',
            'ogg': 'audio/ogg',
            'flac': 'audio/flac',
            'm4a': 'audio/mp4',
            'wma': 'audio/x-ms-wma'
        }
        mime_type = mime_types.get(extension, 'audio/mpeg')
 
        if progress_callback:
            progress_callback(30, "Enviando a Gemini AI para transcripción...")
 
        response = gemini_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[
                '''Por favor, transcribe este audio de una clase o sesión educativa de TECSUP de forma detallada y completa.
 
                Instrucciones:
                - Transcribe todo el contenido fielmente
                - Mantén la estructura y puntuación adecuada
                - Si identificas términos técnicos, escríbelos correctamente
                - Si hay múltiples hablantes, indica cuando sea posible (Profesor, Estudiante, etc.)
                ''',
                types.Part.from_bytes(
                    data=audio_bytes,
                    mime_type=mime_type
                )
            ]
        )
 
        if progress_callback:
            progress_callback(50, "Transcripción completada ✓")
 
        transcription = response.text
        return transcription
    except Exception as e:
        print(f"Error en transcripción: {str(e)}")
        raise
 
def generate_summary_and_script(transcription, progress_callback=None):
    """Generate summary and podcast script using Gemini"""
    try:
        if progress_callback:
            progress_callback(60, "Generando resumen estructurado...")
 
        prompt = f"""
Eres un asistente educativo experto de TECSUP. Basándote en la siguiente transcripción de una clase, realiza dos tareas:
 
1. Genera un RESUMEN EDUCATIVO estructurado con:
   - Tema principal de la clase
   - Objetivos de aprendizaje
   - Conceptos clave explicados
   - Puntos importantes a recordar
   - Términos técnicos mencionados
 
2. Genera un GUION DE PODCAST educativo profesional que:
   - Tenga un tono conversacional pero académico
   - Incluya una introducción atractiva mencionando TECSUP
   - Desarrolle los conceptos principales de forma clara
   - Use ejemplos cuando sea apropiado
   - Tenga una conclusión con puntos de acción para el estudiante
   - Dure aproximadamente 3-5 minutos cuando se lea
 
Formato de salida:
=== RESUMEN EDUCATIVO ===
**Tema Principal:** [tema]
 
**Objetivos de Aprendizaje:**
- [objetivo 1]
- [objetivo 2]
 
**Conceptos Clave:**
- [concepto 1]: [explicación breve]
- [concepto 2]: [explicación breve]
 
**Puntos Importantes:**
- [punto 1]
- [punto 2]
 
**Términos Técnicos:**
- [término 1]: [definición]
 
=== GUION DE PODCAST ===
[Tu guion de podcast aquí - debe ser natural para leer en voz alta]
 
TRANSCRIPCIÓN DE LA CLASE:
{transcription}
"""
 
        response = gemini_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[prompt]
        )
 
        result = response.text
 
        if progress_callback:
            progress_callback(75, "Contenido educativo generado ✓")
 
        # Separar el resumen y el guion
        parts = result.split('=== GUION DE PODCAST ===')
        summary = parts[0].replace('=== RESUMEN EDUCATIVO ===', '').strip()
        script = parts[1].strip() if len(parts) > 1 else result
 
        return summary, script
    except Exception as e:
        print(f"Error generando contenido: {str(e)}")
        raise
 
def generate_podcast_audio(script, output_filename, progress_callback=None):
    """Generate podcast audio using ElevenLabs"""
    try:
        if progress_callback:
            progress_callback(85, "Generando audio profesional del podcast...")
 
        # Usar voz en español latino
        voice_id = "EXAVITQu4vr4xnSDxMaL"  # Bella - voz femenina en español
 
        audio_generator = elevenlabs_client.text_to_speech.convert(
            text=script,
            voice_id=voice_id,
            model_id="eleven_turbo_v2_5",
            output_format="mp3_44100_128"
        )
 
        output_path = os.path.join(app.config['OUTPUT_FOLDER'], output_filename)
 
        with open(output_path, 'wb') as f:
            for chunk in audio_generator:
                if chunk:
                    f.write(chunk)
 
        if progress_callback:
            progress_callback(95, "Podcast generado exitosamente ✓")
 
        return output_path
    except Exception as e:
        print(f"Error generando audio: {str(e)}")
        raise
 
@app.route('/upload_audio', methods=['POST'])
def upload_audio():
    """Endpoint para subir archivo de audio con drag & drop"""
    try:
        if 'audio' not in request.files:
            return jsonify({'error': 'No se encontró el archivo de audio'}), 400
 
        file = request.files['audio']
 
        if file.filename == '':
            return jsonify({'error': 'No se seleccionó ningún archivo'}), 400
 
        if not allowed_file(file.filename):
            return jsonify({
                'error': f'Formato no válido. Formatos aceptados: {", ".join(ALLOWED_EXTENSIONS)}'
            }), 400
 
        # Guardar archivo con nombre seguro
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_filename = f"{timestamp}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
 
        file.save(filepath)
 
        # Obtener información del archivo
        file_size = get_file_size_mb(filepath)
 
        return jsonify({
            'success': True,
            'filename': unique_filename,
            'filepath': filepath,
            'size_mb': round(file_size, 2),
            'message': 'Archivo subido exitosamente'
        })
 
    except Exception as e:
        return jsonify({'error': str(e)}), 500
 
@app.route('/process_audio', methods=['POST'])
def process_audio():
    """Main endpoint to process audio file - versión mejorada con progreso"""
    try:
        data = request.json
        audio_path = data.get('audio_path')
        filename = data.get('filename', 'audio')
 
        if not audio_path:
            return jsonify({'error': 'No se proporcionó la ruta del audio'}), 400
 
        if not os.path.exists(audio_path):
            return jsonify({'error': f'El archivo no existe: {audio_path}'}), 404
 
        # Información inicial
        file_size = get_file_size_mb(audio_path)
        start_time = datetime.now()
 
        # Paso 1: Transcribir audio
        print("\n=== PASO 1: TRANSCRIPCIÓN ===")
        transcription = transcribe_with_gemini(audio_path)
 
        # Guardar transcripción
        trans_filename = f"transcription_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        trans_path = os.path.join(app.config['OUTPUT_FOLDER'], trans_filename)
        with open(trans_path, 'w', encoding='utf-8') as f:
            f.write(transcription)
 
        # Paso 2: Generar resumen y guion
        print("\n=== PASO 2: GENERACIÓN DE CONTENIDO ===")
        summary, script = generate_summary_and_script(transcription)
 
        # Guardar resumen
        summary_filename = f"summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        summary_path = os.path.join(app.config['OUTPUT_FOLDER'], summary_filename)
        with open(summary_path, 'w', encoding='utf-8') as f:
            f.write(summary)
 
        # Guardar guion
        script_filename = f"script_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        script_path = os.path.join(app.config['OUTPUT_FOLDER'], script_filename)
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(script)
 
        # Paso 3: Generar audio del podcast
        print("\n=== PASO 3: GENERACIÓN DE AUDIO ===")
        podcast_filename = f"podcast_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3"
        podcast_path = generate_podcast_audio(script, podcast_filename)
 
        # Calcular tiempo total
        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()
 
        print("\n=== PROCESO COMPLETADO ===")
 
        return jsonify({
            'success': True,
            'transcription': transcription,
            'summary': summary,
            'script': script,
            'files': {
                'transcription': trans_filename,
                'summary': summary_filename,
                'script': script_filename,
                'podcast': podcast_filename
            },
            'metadata': {
                'file_size_mb': round(file_size, 2),
                'processing_time_seconds': round(processing_time, 2),
                'transcription_length': len(transcription),
                'timestamp': datetime.now().isoformat()
            },
            'message': 'Podcast y materiales generados exitosamente'
        })
 
    except Exception as e:
        print(f"\n=== ERROR ===")
        print(str(e))
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
 
@app.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    """Endpoint para descargar archivos generados"""
    try:
        filepath = os.path.join(app.config['OUTPUT_FOLDER'], filename)
        if os.path.exists(filepath):
            return send_file(filepath, as_attachment=True)
        else:
            return jsonify({'error': 'Archivo no encontrado'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500
 
@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint mejorado"""
    return jsonify({
        'status': 'ok',
        'message': 'TECSUP - Sistema de Generación de Materiales Educativos',
        'version': '2.0',
        'services': {
            'gemini': 'connected',
            'elevenlabs': 'connected'
        },
        'upload_folder': app.config['UPLOAD_FOLDER'],
        'output_folder': app.config['OUTPUT_FOLDER']
    })
 
@app.route('/stats', methods=['GET'])
def get_stats():
    """Obtener estadísticas del sistema"""
    try:
        # Contar archivos procesados
        output_files = os.listdir(app.config['OUTPUT_FOLDER'])
        podcasts = [f for f in output_files if f.startswith('podcast_')]
        transcriptions = [f for f in output_files if f.startswith('transcription_')]
 
        return jsonify({
            'total_podcasts': len(podcasts),
            'total_transcriptions': len(transcriptions),
            'total_files': len(output_files)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
 
if __name__ == '__main__':
    print("=" * 80)
    print("🎓 TECSUP - SISTEMA DE GENERACIÓN DE MATERIALES EDUCATIVOS CON IA")
    print("=" * 80)
    print("Hackathon: Educación Superior sin Deserción Estudiantil")
    print("\nServidor disponible en: http://localhost:5000")
    print(f"Carpeta de uploads: {UPLOAD_FOLDER}")
    print(f"Carpeta de output: {OUTPUT_FOLDER}")
    print("\nEndpoints disponibles:")
    print("  - POST /upload_audio  : Subir archivo de audio")
    print("  - POST /process_audio : Procesar audio y generar materiales")
    print("  - GET  /download/<file>: Descargar archivo generado")
    print("  - GET  /health        : Estado del servidor")
    print("  - GET  /stats         : Estadísticas del sistema")
    print("\n" + "=" * 80)
 
    app.run(debug=True, host='0.0.0.0', port=5000)
 