# SourceSniff 🔍

**SourceSniff**, projelerinizdeki kaynak kodları ışık hızında bulmanızı sağlayan, FastAPI tabanlı, modern arayüzlü ve yerel olarak çalışan bir kod arama motorudur. 

Gelişmiş "Inverted Index" (Ters Dizin) mimarisi sayesinde, binlerce dosya arasından aradığınız kelimenin hangi dosyada ve hangi satırda olduğunu anında bulur. Ayrıca `watchdog` entegrasyonu sayesinde kodunuzdaki değişiklikleri anlık olarak takip eder ve indeksini arka planda sadece değişen dosyalar için günceller.

![SourceSniff UI Preview](https://via.placeholder.com/1000x500.png?text=SourceSniff+Dark+Mode+UI) *(Arayüzün ekran görüntüsünü buraya ekleyebilirsiniz)*

## ✨ Özellikler

- 🚀 **Işık Hızında Arama (Inverted Index):** Tüm projeyi baştan sona okumak yerine önbelleğe alınmış ters dizin kullanarak aramaları milisaniyeler içinde gerçekleştirir.
- 🔄 **Canlı Dosya İzleme (Watchdog):** Projenizde bir dosya eklediğinizde, güncellediğinizde veya sildiğinizde; SourceSniff bunu algılar ve tüm dizini baştan taramak yerine sadece o dosyayı indekse ekler/çıkarır.
- 🎨 **Modern Dark Mode Arayüz:** Tailwind CSS ile tasarlanmış Glassmorphism (cam efekti) detaylı, ortam aydınlatmalı (ambient glow) ve oldukça şık bir UI.
- ⚡ **Canlı Arama (Debounce):** Arama çubuğuna her harf yazdığınızda arama işlemi otomatik olarak tetiklenir.
- 🌈 **Syntax Highlighting:** Kod önizleme alanında eşleşen satırlar ve kod bloğu Highlight.js kullanılarak otomatik olarak renklendirilir. Aranan kelime kodun içinde özel bir renkle vurgulanır.
- 🛡️ **Akıllı Yoksayma:** `config.json` dosyasında belirlediğiniz `.git`, `node_modules`, `__pycache__` gibi klasörler tarama dışı bırakılarak performans artırılır.

## 🛠️ Teknoloji Yığını

- **Backend:** Python 3.11+, FastAPI, Uvicorn
- **Core Motoru:** Python Standart Kütüphanesi (`pathlib`, `re`, `json`, `threading`), Watchdog
- **Frontend:** HTML5, Vanilla JavaScript, Tailwind CSS, Highlight.js

## 📂 Proje Yapısı

```text
SourceSniff/
├── backend/
│   ├── main.py              # FastAPI giriş noktası ve statik dosya servisi
│   ├── models/
│   │   └── schemas.py       # Pydantic request/response veri modelleri
│   └── routes/
│       └── search.py        # /api/scan, /api/search, /api/status endpointleri
├── core/
│   ├── indexer.py           # Inverted index oluşturma, kaydetme ve modifiye etme
│   ├── parser.py            # Kaynak kodu temizleme ve kelimelere ayırma (Regex)
│   └── watcher.py           # Watchdog ile canlı dosya değişikliklerini izleme
├── frontend/
│   ├── index.html           # SPA Ana Arayüzü
│   ├── css/
│   │   └── style.css        # Özel Dark Mode ve animasyon stilleri
│   └── js/
│       └── app.js           # API iletişimi, arayüz mantığı ve debounce arama
├── data/                    # Oluşturulan index.json dosyasının barındığı dizin
├── config.json              # Kara liste (ignore list) ayarları
└── requirements.txt         # Bağımlılıklar
```

## 🚀 Kurulum ve Çalıştırma

1. **Projeyi Klonlayın:**
   ```bash
   git clone https://github.com/kullaniciadiniz/sourcesniff.git
   cd sourcesniff
   ```

2. **Bağımlılıkları Yükleyin:**
   Python'ın kurulu olduğundan emin olun.
   ```bash
   pip install -r requirements.txt
   ```

3. **Uygulamayı Başlatın:**
   ```bash
   python -m uvicorn backend.main:app --port 8000
   ```

4. **Kullanmaya Başlayın:**
   Tarayıcınızı açın ve **http://localhost:8000** adresine gidin.

## ⚙️ Kullanım Adımları

1. Arayüzün sol üst köşesindeki "Proje Dizini Tara" çubuğuna bilgisayarınızdaki herhangi bir proje klasörünün mutlak yolunu (Örn: `C:\Projects\my_app`) girin.
2. **Taramayı Başlat** butonuna tıklayın. Indexleme işlemi arka planda asenkron olarak yapılacaktır.
3. İşlem bittikten sonra ortadaki arama çubuğuna aradığınız sınıfı, fonksiyonu veya değişkeni yazın.
4. Sol panelde eşleşen dosyaları görün, üzerine tıklayarak sağ panelde Highlight.js ile renklendirilmiş kod önizlemesini inceleyin!

## 🤝 Katkıda Bulunma

Pull request'ler her zaman kabul edilir. Büyük değişiklikler için lütfen önce neyi değiştirmek istediğinizi tartışmak için bir *Issue* (sorun) açın.

## 📝 Lisans

Bu proje [MIT Lisansı](LICENSE) altında lisanslanmıştır.
