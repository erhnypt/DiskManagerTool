# DiskManagerTool

Disk Inventory X benzeri disk kullanım görselleştirici. Python (yalnızca standart kütüphane) + tarayıcıda treemap.

```bash
python3 -m diskmanager ~            # klasörü tara, tarayıcıyı aç
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
