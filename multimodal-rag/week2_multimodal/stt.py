from pydub import AudioSegment
from pydub import utils as pydub_utils
from dotenv import load_dotenv
import os

# ffmpeg yolunu manuel belirt
pydub_utils.get_encoder_name = lambda: r"C:\Users\merve\Desktop\ffmpeg\bin\ffmpeg.exe"
AudioSegment.converter = r"C:\Users\merve\Desktop\ffmpeg\bin\ffmpeg.exe"
AudioSegment.ffprobe   = r"C:\Users\merve\Desktop\ffmpeg\bin\ffprobe.exe"
os.environ["PATH"] += r";C:\Users\merve\Desktop\ffmpeg\bin"

# Tam yolu belirt
load_dotenv(r"C:\Users\merve\Desktop\miuul_generative_ai\Multimodal Assistant\.env")

# Key'i kontrol et
api_key = os.getenv("GROQ_API_KEY")


from groq import Groq
client = Groq(api_key=api_key)

def ses_to_metin(dosya_yolu: str, metadata_ekle: bool = False) -> dict:
    if not os.path.exists(dosya_yolu):
        raise FileNotFoundError(f"Dosya bulunamadı: {dosya_yolu}")
    
    # Dosyayı sıkıştır — mono, düşük bitrate
    print("Ses hazırlanıyor...")
    ses = AudioSegment.from_file(dosya_yolu)
    ses = ses.set_frame_rate(16000).set_channels(1)
    
    # Geçici mp3 olarak kaydet — çok daha küçük
    gecici = dosya_yolu.rsplit(".", 1)[0] + "_temp.mp3"
    ses.export(gecici, format="mp3", bitrate="32k")
    
    boyut_mb = os.path.getsize(gecici) / (1024*1024)
    print(f"Sıkıştırılmış boyut: {boyut_mb:.1f}MB")
    
    with open(gecici, "rb") as f:
        sonuc = client.audio.transcriptions.create(
            file=(os.path.basename(gecici), f),
            model="whisper-large-v3-turbo",
            language="tr"
        )
    
    os.remove(gecici)
    print("Tamamlandı!")
    return {"tam_metin": sonuc.text}

if __name__ == "__main__":
    test_dosyasi = "C:\\Users\\merve\\Desktop\\miuul_generative_ai\\Multimodal Assistant\\multimodal-rag\\week2_multimodal\\data\\20251216_201107.m4a"
    
    if os.path.exists(test_dosyasi):
        metin = ses_to_metin(test_dosyasi)
        print(f"\nÇevrilen metin: {metin}")
    else:
        print("Dosya bulunamadı!")