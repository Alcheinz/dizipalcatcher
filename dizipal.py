#!/usr/bin/env python3
import sys
import subprocess
import time
import os
import urllib.parse
import concurrent.futures
import threading

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeRemainingColumn
    from rich.prompt import Prompt
    from rich import print as rprint
except ImportError:
    print("Arayüz kütüphanesi (rich) eksik. Lütfen yükleyin: pip3 install rich")
    sys.exit(1)

console = Console()

try:
    from playwright.sync_api import sync_playwright  # type: ignore
except ImportError:
    console.print(Panel.fit("[red]Gerekli kütüphaneler eksik.[/red]\n[yellow]İlk kullanım için şu komutları çalıştırın:[/yellow]\n[cyan]pip3 install playwright yt-dlp curl-cffi rich\npython3 -m playwright install firefox[/cyan]", title="Hata", border_style="red"))
    sys.exit(1)

def print_banner():
    banner = """[bold magenta]
  _____  _     _             _   _____       _       _                  
 |  __ \(_)   (_)           | | / ____|     | |     | |                 
 | |  | |_ _____ _ __   __ _| || |     __ _| |_ ___| |__   ___ _ __   
 | |  | | |_  / | '_ \ / _` | || |    / _` | __/ __| '_ \ / _ \ '__|  
 | |__| | |/ /| | |_) | (_| | || |___| (_| | || (__| | | |  __/ |     
 |_____/|_/___|_| .__/ \__,_|_| \_____\__,_|\__\___|_| |_|\___|_|     
                | |                                                    
                |_|                                                    
    [/bold magenta]
    [cyan]Dizipal & Cloudflare Bypass İndirici - v2.0[/cyan]
    [yellow]Geliştiren: Alcheinz[/yellow]
    """
    console.print(Panel(banner, border_style="magenta", expand=False))

def extract_and_download(url):
    video_url = None
    referer = None
    cookies = None
    
    with console.status(f"[bold green]Playwright Firefox Başlatılıyor... Sayfa Yükleniyor:[/bold green] [cyan]{url}[/cyan]", spinner="bouncingBar") as status:
        with sync_playwright() as p:
            browser = p.firefox.launch(headless=True)
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
                status.update("[bold yellow]Cloudflare Doğrulaması Algılandı, Oynatıcı Tetikleniyor... (Lütfen bekleyin)[/bold yellow]")
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
        console.print(Panel("[bold red]Hata: Video akış linki sayfada bulunamadı.[/bold red]\n[yellow]Cloudflare Captcha paneline takılmış olabilirsiniz veya girdiğiniz sitede video öğesi yok.[/yellow]\n[italic]Script içerisindeki 'headless=True' komutunu 'False' yaparak manuel doğrulama deneyebilirsiniz.[/italic]", title="Video Bulunamadı!", border_style="red"))
        sys.exit(1)
        
    assert video_url is not None
    safe_video_url = str(video_url)
    safe_referer = str(referer) if referer else url

    console.print(f"[bold green]✔[/bold green] [cyan]Şifreli Playlist Adresi:[/cyan] {safe_video_url[:90]}...")
    if referer:
        console.print(f"[bold green]✔[/bold green] [cyan]Referer Bulundu:[/cyan] {referer[:60]}...")
    
    with console.status("[bold magenta]Asıl sunucuyla el sıkışılıyor, M3U8 kanalları taranıyor...[/bold magenta]", spinner="dots"):
        from curl_cffi import requests
        
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
            r_master = requests.get(safe_video_url, headers=headers, cookies=cookie_dict, impersonate="chrome110", timeout=20)
            lines = r_master.text.split("\n")
            video_variant_url = None
            audio_variant_url = None
            
            for line in lines:
                if "URI=\"/edge/variant.php" in line and "TYPE=AUDIO" in line:
                    audio_variant_url = line.split('URI="')[1].split('"')[0]
                    break

            for i, line in enumerate(lines):
                if line.startswith("#EXT-X-STREAM-INF"):
                    video_variant_url = lines[i+1].strip()
                    break

            if not video_variant_url:
                console.print("[bold red]Hata: Master m3u8 içinde video yayın kalitesi bulunamadı![/bold red]")
                sys.exit(1)
                
            base_url = f"{urllib.parse.urlparse(safe_video_url).scheme}://{urllib.parse.urlparse(safe_video_url).netloc}"
            
            def get_ts_list(variant_path):
                if not variant_path: return []
                full_variant = urllib.parse.urljoin(base_url, variant_path)
                r_var = requests.get(full_variant, headers=headers, cookies=cookie_dict, impersonate="chrome110", timeout=20)
                if r_var.status_code != 200: return []
                return [urllib.parse.urljoin(full_variant, l.strip()) for l in r_var.text.split("\n") if l.strip() and not l.strip().startswith("#")]

            video_ts_urls = get_ts_list(video_variant_url)
            audio_ts_urls = get_ts_list(audio_variant_url) if audio_variant_url else []
            
        except Exception as e:
            console.print(f"[bold red]Ağ Hatası: Sunucudan çalma listesi alınamadı ({str(e)})[/bold red]")
            sys.exit(1)
            
    console.print(Panel(f"[bold yellow]Görüntü Parçacıkları:[/bold yellow] [green]{len(video_ts_urls)}[/green]\n[bold yellow]Ses Parçacıkları:[/bold yellow] [green]{len(audio_ts_urls) if audio_ts_urls else 'Bütünleşik (Ayrı kanal yok)'}[/green]", title="Yayın Bilgisi", border_style="blue", expand=False))

    movie_title = "Dizipal_Video"
    try:
        if "/movies/" in url:
            movie_title = url.split("/movies/")[1].split("?")[0].replace("-", "_")
    except:
        pass
        
    downloads_dir = os.path.expanduser("~/Downloads")
    temp_dir = os.path.join(downloads_dir, f".dizipal_temp_{movie_title}")
    os.makedirs(temp_dir, exist_ok=True)
    
    thread_local = threading.local()
    rate_limit_event = threading.Event()
    rate_limit_event.set()
    
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
            rate_limit_event.wait()
            try:
                c_out = sess.get(chunk_url, timeout=20)
                if c_out.status_code == 200:
                    with open(chunk_path, "wb") as f:
                        f.write(c_out.content)
                    return idx, True, None
                elif c_out.status_code in (429, 403):
                    last_error = f"HTTP {c_out.status_code}"
                    if rate_limit_event.is_set():
                        rate_limit_event.clear()
                        time.sleep(10)
                        rate_limit_event.set()
                else:
                    last_error = f"HTTP {c_out.status_code}"
                    time.sleep(2)
            except Exception as e:
                last_error = str(e)
                time.sleep(2)
        return idx, False, last_error

    try:
        def process_queue(ts_urls, prefix, label, color):
            console.print(f"\n[bold {color}]▶ {label} İndirmesi Başlıyor...[/bold {color}]")
            out_file = os.path.join(downloads_dir, f"{movie_title}_{prefix}.ts")
            
            with Progress(
                SpinnerColumn(),
                TextColumn(f"[{color}][progress.description]{{task.description}}"),
                BarColumn(complete_style=color, finished_style="bold green"),
                TaskProgressColumn(),
                TimeRemainingColumn(),
                console=console
            ) as progress:
                
                task_id = progress.add_task(f"{label} İndiriliyor...", total=len(ts_urls))
                
                with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                    future_chunks = {executor.submit(download_chunk, i, l_url, prefix): i for i, l_url in enumerate(ts_urls)}
                    for future in concurrent.futures.as_completed(future_chunks):
                        i, success, err_msg = future.result()
                        if success:
                            progress.update(task_id, advance=1)
                        else:
                            console.print(f"[bold red][-] Hata:[/bold red] {label} Parça #{i} indirilemedi! ({err_msg})", highlight=False)
            
            with console.status(f"[bold {color}]{label} Bütünleştiriliyor... Lütfen bekleyin.[/bold {color}]"):
                with open(out_file, "wb") as f_out:
                    for i in range(len(ts_urls)):
                        chunk_path = os.path.join(temp_dir, f"{prefix}_{i}.ts")
                        if os.path.exists(chunk_path):
                            with open(chunk_path, "rb") as f_in:
                                f_out.write(f_in.read())
                            os.remove(chunk_path)
            return out_file

        video_out = process_queue(video_ts_urls, "video", "Görüntü (1080p)", "cyan")
        audio_out = process_queue(audio_ts_urls, "audio", "Ses (Türkçe)", "magenta") if audio_ts_urls else None

        final_mp4 = os.path.join(downloads_dir, f"{movie_title}.mp4")
        if audio_out:
            with console.status("[bold yellow]Formatlar Birleştiriliyor (FFMPEG Muxing)...[/bold yellow]"):
                try:
                    subprocess.run(["ffmpeg", "-i", video_out, "-i", audio_out, "-c", "copy", final_mp4], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    os.remove(video_out)
                    os.remove(audio_out)
                    console.print(Panel(f"[bold green]Mükemmel![/bold green] İndirme ve MP4 Dönüşümü Tamamlandı.\n[cyan]Dosya:[/cyan] {final_mp4}", title="🎉 İşlem Bitti", border_style="green"))
                except Exception:
                    console.print(Panel(f"[bold red]FFMPEG Bulunamadı![/bold red]\n[yellow]Ses ve görüntü MP4'e otomatik olarak dönüştürülemedi.[/yellow]\nBilgisayarınıza ffmpeg kurarsanız ([cyan]brew install ffmpeg[/cyan]) sistem bunu otomatik yapar.\nŞu an için MacOS (VLC vs) ile eşzamanlı açabilirsiniz.\n\n[cyan]Görüntü:[/cyan] {video_out}\n[cyan]Ses:[/cyan] {audio_out}", title="Kısmi Başarı", border_style="yellow"))
        else:
            os.rename(video_out, final_mp4)
            console.print(Panel(f"[bold green]Mükemmel![/bold green] İndirme Tamamlandı.\n[cyan]Video Dosyası:[/cyan] {final_mp4}", title="🎉 İşlem Bitti", border_style="green"))

        try: os.rmdir(temp_dir)
        except: pass

    except KeyboardInterrupt:
        console.print("\n[bold red]✕ İndirme işlemi iptal edildi! (CTRL+C) Yarıda kalan veriler siliniyor...[/bold red]")
        import shutil
        if 'temp_dir' in locals():
            shutil.rmtree(temp_dir, ignore_errors=True)
        if 'video_out' in locals() and os.path.exists(video_out):
            os.remove(video_out)
        if 'audio_out' in locals() and audio_out and os.path.exists(audio_out):
            os.remove(audio_out)
        console.print("[green]Sistem başarıyla temizlendi.[/green]")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[bold red][!] Hata: İndirme işlemi başarısız oldu. Nedeni:[/bold red] {e}")

if __name__ == "__main__":
    print_banner()
    
    if len(sys.argv) > 1:
        target_url = sys.argv[1]
    else:
        target_url = Prompt.ask("[bold cyan]Lütfen indirmek istediğiniz Dizipal linkini yapıştırın[/bold cyan]")
        if not target_url:
            console.print("[red]Geçerli bir link girmediniz.[/red]")
            sys.exit(1)
            
    extract_and_download(target_url.strip())
