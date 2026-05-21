import os
import subprocess
from faster_whisper import WhisperModel

class Transcriber:
    def __init__(self, model_size="large-v3-turbo"):
        print(f"Loading Whisper model: {model_size}...")
        # device="cpu", compute_type="int8" is very fast on M1 Pro
        self.model = WhisperModel(model_size, device="cpu", compute_type="int8")

    def extract_audio(self, video_path, audio_path):
        print(f"Extracting audio to: {audio_path}...")
        # Convert to 16kHz mono wav
        cmd = [
            "ffmpeg", "-y", "-i", video_path,
            "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le",
            audio_path
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def transcribe(self, audio_path):
        print("Starting transcription...")
        segments, info = self.model.transcribe(audio_path, beam_size=5)
        
        print(f"Detected language: {info.language} with probability {info.language_probability:.2f}")
        
        results = []
        for segment in segments:
            results.append({
                "start": segment.start,
                "end": segment.end,
                "text": segment.text.strip()
            })
            # Real-time feedback
            # print(f"[{segment.start:.2f}s -> {segment.end:.2f}s] {segment.text}")
            
        return results

def format_timestamp(seconds):
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes:02d}:{secs:02d}"

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python transcriber.py <video_path>")
        sys.exit(1)
    
    video_path = sys.argv[1]
    audio_path = "temp_audio.wav"
    
    transcriber = Transcriber()
    transcriber.extract_audio(video_path, audio_path)
    segments = transcriber.transcribe(audio_path)
    
    for s in segments:
        print(f"[{format_timestamp(s['start'])}] {s['text']}")
    
    # Cleanup
    if os.path.exists(audio_path):
        os.remove(audio_path)
