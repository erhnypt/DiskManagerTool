# DiskManagerTool

Disk Inventory X benzeri disk kullanım görselleştirici. Python (yalnızca standart kütüphane) + tarayıcıda treemap.

## Kolay başlatma

- **`DiskManager.command`** dosyasına çift tıkla (Finder'da). Terminal açılır, sunucu o pencerede çalışır, tarayıcı gelir. Durdurmak için pencereyi kapat.
- **`./make_app.sh`** bir kez çalıştırılırsa `~/Applications/Disk Manager.app` oluşur (Spotlight'tan açılır); bu uygulama yalnızca `DiskManager.command`'ı Terminal'de açar.
  Sunucuyu uygulamanın arka plan sürecine koymak denendi ama macOS o süreci kapattığı için vazgeçildi.
- Zaten çalışan aynı sürüm varsa yalnızca tarayıcı açılır; `git pull` sonrası eski sunucu kendiliğinden kapatılıp yenisi başlatılır.
- Sorun olursa `Teshis.command` bilgileri toplar ve panoya kopyalar.
- İlk açılışta macOS "geliştirici doğrulanamadı" derse: sağ tık → Aç.

## Tüm disk taraması

Uygulama açılır açılmaz **tüm diski (`/`) kendiliğinden tarar**, klasör sormaz; "Yeniden tara" düğmesi aynısını tekrarlar. Sanal dosya sistemleri, `/Volumes` ve macOS'ta `/System/Volumes` (Data birimi firmlink'lerle zaten `/Users` vb. olarak görünür, ayrıca taramak her şeyi iki kez sayardı) atlanır.
**Önemli:** macOS izin vermeyen klasörleri (Mail, Fotoğraflar, Safari…) okuyamaz. Tam sonuç için *Sistem Ayarları → Gizlilik ve Güvenlik → Tam Disk Erişimi*'ne Terminal'i  ekle. Okunamayan öğe sayısı durum çubuğunda görünür.

## Komut satırı

```bash
python3 -m diskmanager              # tüm diski tara, tarayıcıyı aç
python3 -m diskmanager ~/Documents  # isteğe bağlı: yalnızca bir klasör
python3 -m diskmanager --port 9000  # veya arayüzden klasör girip "Tara"
python3 -m unittest discover -s tests -t .
```

- Treemap: alan = disk üzerindeki gerçek boyut (`st_blocks`), renk = dosya türü
- Sol: tembel yüklenen klasör ağacı; sağ: dosya türü istatistikleri
- Çift tıkla: klasöre yakınlaş; üstte breadcrumb
- Bir dosya seçip "Finder'da göster" (macOS `open -R`; Linux`xdg-open`, Windows `explorer /select`)
- Symlink'ler izlenmez, hardlink'ler bir kez sayılır; sunucu yalnızca 127.0.0.1'e bağlanır

## AppCleaner

Üstteki **Uygulamalar** sekmesi `/Applications` ve `~/Applications` içindeki uygulamaları boyutlarıyla listeler.
Bir uygulamayı seçince `~/Library` altındaki artık dosyalar (Application Support, Caches, Preferences, Containers, …) bulunur;
işaretlediklerini **Çöp Kutusu'na taşır** (kalıcı silme yok). Eşleşme muhafazakâr: bundle id veya tam uygulama adı.
`com.apple.*` sistem uygulamaları kaldırılamaz; sunucu yalnızca son aramada listelenen yolları kabul eder.

## En büyük 100 dosya ve Çöp Kutusu

- Sağ panelde **En büyük 100** sekmesi: bir satıra tıklayınca treemap'te o dosyaya gider ve seçer.
- Treemap/ağaçta seçilen öğe için **Çöp Kutusu'na taşı** (onaylı, kalıcı silme yok). Taşınınca boyutlar ve listeler anında güncellenir.
- Yalnızca taranmış ağaçtaki yollar kabul edilir; tarama kökünün kendisi taşınamaz.

## Arama ve Önbellek temizliği

- **Uygulamalar** sekmesinde üstteki kutu uygulamaları ad veya bundle id'ye göre filtreler.
- **Önbellek** sekmesi `~/Library/Caches` ve `~/Library/Logs` içindeki üst düzey öğeleri boyuta göre listeler; işaretlediklerini Çöp Kutusu'na taşır. Yalnızca son listelemedeki yollar kabul edilir.
