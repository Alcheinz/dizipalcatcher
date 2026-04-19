# 🎬 DizipalCatcher v2.0 (Premium HLS Downloader)

Modern, stabil ve güvenli terminal arayüzü ile Dizipal vb. Cloudflare destekli yayın sitelerinin arka planındaki asıl video ve ses bağlantılarını kopararak, saniyeler içinde bilgisayarınıza yüksek kalite (1080p vb.) indiren otonom Python scriptidir.

Geliştirici: **Alcheinz** ([@Alcheinz](https://github.com/Alcheinz))

---

## ✨ Özellikler

* **Cloudflare (Turnstile) / DDoS WAF Atlatma:** `playwright` kullanılarak güvenlik doğrulamaları otomatik aşılır, asıl yayıncı (Edge / CDN) sunucusu tespit edilir.
* **HTTP/2 Session Pooling:** Özel `curl_cffi` altyapısıyla her sekme için arka planda bağımsız bir Tarayıcı Oturumu açılarak C-Level çakışmalar donanımsal olarak aşılır.
* **Akıllı 429 Rate-Limit ByPass:** Sistem Cloudflare/Nginx hız limitine takılırsa hata vermek veya iptal olmak yerine *Global Soğutma Modu*na girerek tam 10 saniye tüm indirmeyi sessize alır, ardından kaldığı (atlamadan) yerden milisaniyesinde devam eder.
* **Yerleşik UX / UI Tasarımı:** Terminalde izlemesi keyifli animasyonlar, ayrılmış çift yönlü Progress bar, interaktif komut menüsü gibi özellikler bulundurur.
* **Yerleşik Hata Toleransı:** Her parça 10 kez üst üste denenebilir, başarıyla inen bir parça işlem yarım kalsa bile asla sıfırdan inmez (Kaldığı yerden devam destekler).
* **Agresif Temizlik İşlemi:** İndirme işlemini iptal etmek istediğinizde makinenizde gereksiz .ts (yarım yamalak) parça dosyası şişkinliği yapmaz, ortamı sterilize edip çıkar.
* **Ayrı Kanal Şifreleme/Birleştirme:** Yüksek kaliteli videolar için Görüntü (Video) ve Ses (Audio) kanallarını tek tek çözümler, indirir ve en son `ffmpeg` yardımıyla mükemmel senkronlanmış tek bir `.mp4` dosyası üretir.

---

## 🛠 Kurulum & Başlangıç

Projeyi kendi bilgisayarına kurmak veya klonlamak isteyen geliştiriciler için tam adımlar:

1. **Repoyu Klonlayın**
   ```bash
   git clone https://github.com/Alcheinz/dizipalchecker.git
   cd dizipalchecker
   ```

2. **Gereksinimleri Yükleyin**
   ```bash
   # Python paketlerini kur
   pip3 install -r requirements.txt
   
   # Cloudflare'i görünmez şekilde geçecek tarayıcıyı yükle
   python3 -m playwright install firefox
   ```

3. **FFMPEG Yükleyin (ZORUNLU ÖNERİ - MacOS için)**
   Görüntü ve Ses dosyası indirildikten sonra tek bir MP4 yapmak için FFMPEG aracına ihtiyacı vardır:
   ```bash
   brew install ffmpeg
   ```
   *(Eğer Homebrew yüklü değilse önce: `/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"` komutunu çalıştırın).*

---

## 🚀 Kullanım Taktikleri

Aracı kullanmak için `dizipal.py` komutunu çalıştırmanız yeterlidir; gerisini kendisi soracaktır:

**Seçenek 1 (İnteraktif Mod):**
```bash
python3 dizipal.py
```
*Bu komutu yazdığınızda, sizden yapıştırmanız için indirme adresini (URL) bizzat isteyecektir.*

**Seçenek 2 (Doğrudan Başlatma):**
```bash
python3 dizipal.py "https://dizipal...com/movies/film-linki"
```

### 🛑 Sistemi İptal Etmek (Temel Komut: `CTRL + C`)
Ekranda işlem akarken indirmeyi aniden iptal etmek veya durdurmak isterseniz klavyenizden **`Ctrl + C`** kombinasyonuna basın.
Sistem bunu algılayacak, o ana kadar indirilmiş bütün yarım geçici dosyaları, şişkinlik yapan klasörleri `(~/.dizipal_temp_...)` ve arta kalanları silerek yer kaplamasını önleyecektir. İşlem tamamen güvenlidir.

---

## ⚠️ Olası Hata Çözümleri
* **"Video akış linki bulunamadı" hatası:** Site içerisindeki Cloudflare Captcha korumasına denk gelinmiş olabilir. `dizipal.py` içerisindeki 28. satıra giderek `headless=True` değişkenini `headless=False` yapıp terminalden kodu tekrar tetiklerseniz, ekranınıza anlık olarak bir tarayıcı açılacaktır. Kutucuğu manuel işaretlediğinizde script videoyu alıp indirmeye devam edecektir.
* **"FFMPEG Bulunamadı" hatası:** İşlem başarılı bitmiştir fakat bilgisayarınızda ffmpeg aracı olmadığı için `.ts` dosyalarını birleştirememiştir. İndirilenler (*Downloads*) klasörünüze bakarsanız ses ve görüntünün ayrı dosyalar olarak indiğini görebilirsiniz (VLC Media Player ile ikisini senkronize olarak ekleyip direkt de izleyebilirsiniz).
