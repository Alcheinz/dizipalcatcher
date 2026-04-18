# DizipalCatcher 🎥

Dizipal ve benzeri video sitelerinden videoları güvenlik duvarlarını (Cloudflare, JWT Obfuscation, WAF, TLS Fingerprint) aşarak en yüksek kalitede indiren bir terminal aracı.

## 🚀 Özellikler

- **Cloudflare Bypass**: Playwright kullanarak bot korumalarını aşar.
- **JWT Decoding**: `master.php` üzerinden gelen şifreli yayın linklerini çözerek Cloudflare'in TLS engeline takılmayan doğrudan CDN bağlantılarını bulur.
- **WAF Evading**: Dinamik `Referer` ve `Origin` başlıkları ile sunucu tarafındaki "Cross-Origin" engellerini atlatır.
- **TLS Fingerprinting**: `curl-cffi` ve `yt-dlp` impersonate özelliği sayesinde gerçek bir Chrome tarayıcısıymış gibi davranır.

## 📦 Kurulum

1.  **Bağımlılıkları Yükleyin:**
    ```bash
    pip3 install -r requirements.txt
    ```

2.  **Tarayıcı Motorunu Kurun:**
    ```bash
    python3 -m playwright install firefox
    ```

3.  **Sistem Komutu Olarak Ayarlayın (Mac/Linux):**
    ```bash
    sudo ln -s $(pwd)/dizipal /usr/local/bin/dizipal
    ```

## 🛠 Kullanım

Terminalinize gelip indirmek istediğiniz dizipal linkini vermeniz yeterlidir:

```bash
dizipal "https://dizipalXXXX.com/movies/film-linki"
```

## 🧠 Teknik Detaylar

Bu proje, standart video indirme araçlarının Dizipal üzerinde neden başarısız olduğunu analiz ederek geliştirilmiştir:
- **Challenge**: Dizipal, video kaynaklarını `master.php` adında bir API üzerinden JWT token ile döner.
- **Bypass**: Script, bu token'ı yakalar, Base64/JSON modülleri ile kendi içinde çözer (`Decode`).
- **Optimization**: Token içindeki ham IP adreslerinin `Timeout` vermesi sebebiyle, yine token içinden çıkan alternatif HTTPS domain rotalarına geçiş yapar.
- **Anti-Bot**: `yt-dlp`'ye `--impersonate chrome` argümanı eklenerek Cloudflare TLS şifreleme denetimini aşması sağlanır.

## 🤝 Katkıda Bulunma

Bu proje eğitim amaçlı geliştirilmiştir. Site yapısı değiştikçe sniffing heuristiklerinin güncellenmesi gerekebilir.

---
**Geliştirici:** Furkan & Antigravity AI
