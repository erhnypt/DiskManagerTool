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
- Symlink'ler izlenmez, hardlink'ler bir kez sayılır; sunucu yalnızca 127.0.0.1'e bağlanır
