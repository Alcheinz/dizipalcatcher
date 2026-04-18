#!/usr/bin/env python3
import sys
import subprocess
import time
import base64
import json
from urllib.parse import urlparse
try:
    from playwright.sync_api import sync_playwright  # type: ignore
except ImportError:
    print("Gerekli kütüphaneler eksik. İlk kullanım için şu komutları çalıştırın:")
    print("pip install playwright yt-dlp")
    print("playwright install firefox")
    sys.exit(1)

def extract_and_download(url):
    print(f"[*] {url} adresi inceleniyor...")
    video_url = None
    referer = None
    cookies = None
    
    with sync_playwright() as p:
        browser = p.firefox.launch(headless=False)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/115.0",
            viewport={"width": 1280, "height": 720}
        )
        page = context.new_page()
        
        def handle_request(request):
            nonlocal video_url, referer
            req_url = request.url
            if video_url is None:
                if (".m3u8" in req_url or ".mp4" in req_url or "master.php" in req_url) and ".js" not in req_url and ".css" not in req_url:
                    if "chunk" not in req_url and "track" not in req_url and "segment" not in req_url and "vtt_" not in req_url:
                        video_url = req_url
                        referer = request.headers.get('referer', url)
        
        page.on("request", handle_request)
        
        try:
            print("[*] Sayfa yükleniyor, Cloudflare/DDoS doğrulaması geçiliyor olabilir (Lütfen bekleyin)...")
            page.goto(url, wait_until="domcontentloaded", timeout=45000)
            
            time.sleep(5)
            page.mouse.click(640, 360)
            time.sleep(1)
            page.mouse.click(640, 360)

            for f in page.frames:
                try:
                    f.click("body", timeout=1000)
                except:
                    pass

            for i in range(15):
                if video_url:
                    break
                time.sleep(1)
                
        except Exception as e:
            pass
        finally:
            cookies = context.cookies()
            browser.close()

    if not video_url:
        print("[!] Hata: Video akış linki (m3u8) sayfada bulunamadı.")
        print("    Muhtemelen Cloudflare güvenlik engeline takıldı.")
        print("    Eğer sürekli bu hatayı alıyorsanız script içerisindeki 'headless=True' kısmını 'headless=False' yapıp CAPTCHA'yı elle çözmeyi deneyebilirsiniz.")
        sys.exit(1)
        
    # Linter hatalarını gidermek için tipleri netleştir
    assert video_url is not None
    safe_video_url = str(video_url)
    safe_referer = str(referer) if referer else url

    # JWT Token Çözme: Eğer link master.php ise, asıl CDN ip'sini (m3u8) ayıkla!
    # Youtube-DL (yt-dlp) Cloudflare'in TLS korumasına takılıyor, o yüzden Cloudflare'in arkasından dolaşmalıyız.
    if "master.php" in safe_video_url and "t=" in safe_video_url:
        try:
            token = safe_video_url.split("t=")[1].split("&")[0]
            if "." in token:
                # Dizipal tokenlerinde JWT header eksik. Düz "payload.signature" olarak geliyor.
                # O yüzden payload kısmı index 0'da yer alır!
                payload = token.split(".")[0]
            else:
                payload = token
                
            payload += "=" * ((4 - len(payload) % 4) % 4)
            import base64, json
            decoded = base64.urlsafe_b64decode(payload).decode('utf-8')
            data = json.loads(decoded)
            
            d_info = data.get("data", {})
            real_m3u8 = d_info.get("u")
            
            if real_m3u8:
                # Raw HTTP IP Timeout (Zaman aşımı) veriyor. JWT içindeki sağlam HTTPS domain rotasını kullanalım:
                folder = d_info.get("server_base_folder")
                domains = d_info.get("domains", [])
                
                if folder and domains and f"/{folder}/" in real_m3u8:
                    try:
                        path_part = real_m3u8.split(f"/{folder}/", 1)[1]
                        d_name = domains[0].get("d_name")
                        d_prefix = domains[0].get("d_url_prefix")
                        if d_name and d_prefix:
                            real_m3u8 = f"https://{d_name}/{d_prefix}/{path_part}"
                            print("\n[+] HTTP ham IP engelli tespit edildi. Sorunsuz HTTPS aktarım domainine geçiş yapıldı!")
                    except Exception:
                        pass
                
                print("\n[+] JWT Şifresi kırıldı, asıl sunucu dizini başarıyla çözüldü!")
                safe_video_url = real_m3u8
        except Exception as e:
            print(f"[-] JWT şifre çözümü başarısız: {e}")

    print(f"\n[+] Video kaynağı bulundu: {safe_video_url}...")
    if referer:
        print(f"[+] Referer bulundu: {referer[:60]}...")
    
    cookies_str = ""
    if cookies and isinstance(cookies, list):
        cookies_str = "; ".join([f"{c.get('name')}={c.get('value')}" for c in cookies if isinstance(c, dict)])
    print("[*] yt-dlp ile indirme asıl sunucudan başlatılıyor...")
    
    dynamic_origin = f"{urlparse(safe_referer).scheme}://{urlparse(safe_referer).netloc}" if safe_referer else "https://dizipal1549.com"
    
    yt_cmd = [
        sys.executable, "-m", "yt_dlp",
        "-f", "bestvideo+bestaudio/best",
        "--merge-output-format", "mp4",
        "--add-header", f"Referer:{safe_referer}",
        "--add-header", "User-Agent:Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/115.0",
        "--add-header", f"Cookie:{cookies_str}",
        "--add-header", f"Origin:{dynamic_origin}",
        "--impersonate", "chrome",
        "-o", "%(title)s.%(ext)s",
        safe_video_url
    ]
    
    try:
        subprocess.run(yt_cmd, check=True)
        print("\n[+] İndirme başarıyla tamamlandı!")
    except FileNotFoundError:
        print("\n[!] Hata: Sistemde 'yt-dlp' bulunamadı.")
        print("    Lütfen yt-dlp aracını kurun: 'pip install yt-dlp' veya 'brew install yt-dlp'")
    except subprocess.CalledProcessError:
        print("\n[!] Hata: İndirme işlemi başarısız ile sonuçlandı. m3u8 video URL zaman aşımına uğramış olabilir.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('Kullanım: dizipal "url"')
        sys.exit(1)
        
    target_url = sys.argv[1]
    extract_and_download(target_url)
