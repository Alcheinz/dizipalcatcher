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
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:135.0) Gecko/20100101 Firefox/135.0",
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
        
    # --- Linter ve Tip Düzeltmeleri ---
    assert video_url is not None
    safe_video_url = str(video_url)
    safe_referer = str(referer) if referer else url

    print(f"\n[+] Şifreli Playlist Adresi: {safe_video_url[:120]}...")
    if referer:
        print(f"[+] Referer bulundu: {referer[:60]}...")
    
    print("[*] Asıl sunucudan yayın paketleri tespit ediliyor...")
    
    from curl_cffi import requests
    import urllib.parse
    import concurrent.futures

    cookie_dict = {}
    if cookies and isinstance(cookies, list):
        for c in cookies:
            cookie_dict[c["name"]] = c["value"]
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:135.0) Gecko/20100101 Firefox/135.0",
        "Referer": safe_referer,
        "Origin": safe_referer.split("/iframe")[0],
        "Accept": "*/*",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Dest": "empty"
    }

    try:
        # Sadece Master requestleri için tekil bir işlem
        r_master = requests.get(safe_video_url, headers=headers, cookies=cookie_dict, impersonate="chrome110", timeout=20)
        
        lines = r_master.text.split("\n")
        video_variant_url = None
        audio_variant_url = None
        
        # Audio URI taraması
        for line in lines:
            if "URI=\"/edge/variant.php" in line and "TYPE=AUDIO" in line:
                audio_variant_url = line.split('URI="')[1].split('"')[0]
                break

        # Video URI taraması (STREAM-INF'in hemen altındaki satır)
        for i, line in enumerate(lines):
            if line.startswith("#EXT-X-STREAM-INF"):
                video_variant_url = lines[i+1].strip()
                break

        if not video_variant_url:
            print("\n[-] Hata: Master m3u8 içinde video yayın kalitesi bulunamadı!")
            sys.exit(1)
            
        base_url = f"{urllib.parse.urlparse(safe_video_url).scheme}://{urllib.parse.urlparse(safe_video_url).netloc}"
        
        # 2. Playlistleri Al ve TS URL'lerini çıkar
        def get_ts_list(variant_path):
            if not variant_path: return []
            full_variant = urllib.parse.urljoin(base_url, variant_path)
            r_var = requests.get(full_variant, headers=headers, cookies=cookie_dict, impersonate="chrome110", timeout=20)
            if r_var.status_code != 200: return []
            return [urllib.parse.urljoin(full_variant, l.strip()) for l in r_var.text.split("\n") if l.strip() and not l.strip().startswith("#")]

        video_ts_urls = get_ts_list(video_variant_url)
        audio_ts_urls = get_ts_list(audio_variant_url) if audio_variant_url else []
        
        print(f"[+] {len(video_ts_urls)} Görüntü parçası ve {len(audio_ts_urls)} Ses parçası bulundu!")

        # 3. İndirme havuzu
        movie_title = "Dizipal_Video"
        try:
            if "/movies/" in url:
                movie_title = url.split("/movies/")[1].split("?")[0].replace("-", "_")
        except:
            pass
            
        import os
        import threading
        
        downloads_dir = os.path.expanduser("~/Downloads")
        temp_dir = os.path.join(downloads_dir, f".dizipal_temp_{movie_title}")
        os.makedirs(temp_dir, exist_ok=True)
        
        thread_local = threading.local()
        rate_limit_event = threading.Event()
        rate_limit_event.set() # True means allowed to proceed
        
        def get_session():
            if not hasattr(thread_local, "session"):
                thread_local.session = requests.Session(impersonate="chrome110", headers=headers, cookies=cookie_dict)
            return thread_local.session
        
        def download_chunk(idx, chunk_url, prefix):
            retries = 10
            chunk_path = os.path.join(temp_dir, f"{prefix}_{idx}.ts")
            
            if os.path.exists(chunk_path) and os.path.getsize(chunk_path) > 1024:
                return idx, True, None
                
            sess = get_session()
            last_error = ""
            for _ in range(retries):
                rate_limit_event.wait() # Global blokaj varsa bekle
                try:
                    c_out = sess.get(chunk_url, timeout=20)
                    if c_out.status_code == 200:
                        with open(chunk_path, "wb") as f:
                            f.write(c_out.content)
                        return idx, True, None
                    elif c_out.status_code in (429, 403):
                        last_error = f"HTTP {c_out.status_code}"
                        # Sadece bir thread kilidi tetikler
                        if rate_limit_event.is_set():
                            rate_limit_event.clear()
                            time.sleep(10) # 10 saniye soğuma
                            rate_limit_event.set()
                    else:
                        last_error = f"HTTP {c_out.status_code}"
                        time.sleep(2)
                except Exception as e:
                    last_error = str(e)
                    time.sleep(2)
            return idx, False, last_error

        def process_queue(ts_urls, prefix, label):
            print(f"\n[*] {label} Kanalı İndiriliyor...")
            # Çekirdek sayısını 2'ye düşürdük, 429 yememek için
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                future_chunks = {executor.submit(download_chunk, i, l_url, prefix): i for i, l_url in enumerate(ts_urls)}
                downloaded_count = 0
                for future in concurrent.futures.as_completed(future_chunks):
                    i, success, err_msg = future.result()
                    if success:
                        downloaded_count += 1
                        print(f"\r[*] [%{int(downloaded_count/len(ts_urls)*100)}] {downloaded_count}/{len(ts_urls)}  ", end="")
                    else:
                        print(f"\n[-] Hata: {label} Parça #{i} indirilemedi! ({err_msg})")
            
            out_file = os.path.join(downloads_dir, f"{movie_title}_{prefix}.ts")
            print(f"\n[*] {label} Parçaları birleştiriliyor...")
            with open(out_file, "wb") as f_out:
                for i in range(len(ts_urls)):
                    chunk_path = os.path.join(temp_dir, f"{prefix}_{i}.ts")
                    if os.path.exists(chunk_path):
                        with open(chunk_path, "rb") as f_in:
                            f_out.write(f_in.read())
                        os.remove(chunk_path)
            return out_file

        video_out = process_queue(video_ts_urls, "video", "Görüntü (Video)")
        audio_out = process_queue(audio_ts_urls, "audio", "Ses (Audio)") if audio_ts_urls else None

        # FFMPEG Birleştirme Denemesi
        final_mp4 = os.path.join(downloads_dir, f"{movie_title}.mp4")
        if audio_out:
            print("\n[*] FFMPEG ile Görüntü ve Ses birleştiriliyor (Varsa)...")
            try:
                import subprocess
                subprocess.run(["ffmpeg", "-i", video_out, "-i", audio_out, "-c", "copy", final_mp4], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                os.remove(video_out)
                os.remove(audio_out)
                print(f"[+] Harika! FFMPEG ile mükemmel birleştirildi: {final_mp4}")
            except Exception:
                print("\n[!] FFMPEG sisteminizde yüklü değil!")
                print("    MacOS'ta tek başına ses ve görüntüyü aynı anda açabileceğiniz formattalar.")
                print("    Ya da terminale 'brew install ffmpeg' yazıp aracı bir daha çalıştırın.")
                print(f"    Görüntü Dosyası: {video_out}")
                print(f"    Ses Dosyası    : {audio_out}")
        else:
            os.rename(video_out, final_mp4)
            print(f"[+] İndirme tamamlandı: {final_mp4}")

        try: os.rmdir(temp_dir)
        except: pass

    except Exception as e:
        print(f"\n[!] Hata: İndirme işlemi başarısız oldu. Nedeni: {e}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('Kullanım: dizipal "url"')
        sys.exit(1)
        
    target_url = sys.argv[1]
    extract_and_download(target_url)
