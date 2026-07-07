# PNG Interceptor Drone Simülasyonu

İzinsiz uçan bir hedef drone'a fiziksel dalışla (çarpma) müdahale eden önleyici
drone'un 3B simülasyonu. Merkezde **oransal seyrüsefer güdümü (Proportional
Navigation Guidance, PNG)** var; kıyas baz çizgisi olarak **saf takip (pure
pursuit)** de uygulanmıştır. (İlham: arXiv:2409.17497)

## Kurulum

```
pip install -r requirements.txt
```

Bağımlılıklar: `numpy`, `matplotlib`, `pillow` (gif kaydı). Başka bağımlılık yok.

## Çalıştırma

```
# Bayrak senaryosu: dönen hedef, PNG ile dalış + 3B animasyon gif'i
python main.py --scenario turning --guidance png --animate

# PNG ve pure pursuit'i aynı figürde üst üste kıyasla
python main.py --scenario turning --guidance both

# Tüm hedef modellerinde metrik tablosu (ıska / süre / yol / maks ivme)
python main.py --compare

# Testler
python tests/test_guidance.py        # (veya: python -m pytest tests/)
```

Senaryolar: `cv` (sabit hız), `ca` (sabit ivme), `sm` (yılankavi),
`turning` (sabit dönüş hızıyla viraj — en önemlisi).
Çıktılar `cikti/` klasörüne kaydedilir. Tüm parametreler `config.py`'de;
sabit seed ile tekrarüretilebilir.

## Neden PNG, hedef dönerken EN KISA yolu üretir?

Hedefe doğru bakan hayali çizgiye **görüş hattı (LOS)** denir. İki cisim
gerçek bir çarpışma rotasındaysa bu çizgi uzayda **dönmez** — sadece kısalır.
(Denizcilerin kuralı: "kerteriz değişmiyorsa çarpışacaksınız.")

- **Pure pursuit** burnunu hep hedefin *şu anki* konumuna çevirir. Hedef
  dönerken bu, sürekli hedefin *eski* yerine koşmak demektir: önleyici hedefin
  kuyruğuna takılır, kavisli ve uzun bir yol uçar.
- **PNG** ise LOS'un dönüş hızını ölçer ve ona orantılı ("N katı") yanal ivme
  komutu üretir: `a = N · Vc · (Ω × r̂)`. Bu komut LOS dönüşünü **sıfıra sürer**.
  LOS dönmüyorsa geometri kendiliğinden çarpışma üçgenine oturmuştur: önleyici
  hedefin *gideceği* noktaya nişan almış olur, köşeyi keser ve neredeyse düz
  bir hat uçar. Hedef manevra yaptıkça LOS yeniden dönmeye başlar, PNG anında
  düzeltir — açık bir hedef tahmini yapmadan, sadece LOS ölçümüyle.

Örnek çıktı (aynı dönen hedef, aynı başlangıç; `--compare`):

| Senaryo | Güdüm | İsabet | Iska [m] | Süre [s] | Yol [m] |
|---------|-------|--------|----------|----------|---------|
| turning | PNG | EVET | 0.38 | 3.06 | **61.8** |
| turning | PurePursuit | EVET | 0.45 | 5.02 | 101.0 |

## Model ve varsayımlar

- Önleyici **nokta-kütle**: durum (p, v); kısıtlar `v_max`, `a_max`
  (yanal + toplam itki). Yerçekiminin itki tarafından sürekli telafi edildiği
  varsayılır (hover-yetenekli çok-rotor); entegrasyona ayrıca −g eklenmez.
- Hedef **kinematik**: CV / CA / sinüzoidal / dairesel viraj modelleri
  (`target_models.py`), tüm parametreler `config.py`'den.
- İsabet: `R < r_hit` (varsayılan 0.5 m ≈ iki gövde yarıçapı + pay).
  Iska mesafesi = kosum boyunca minimum R.

## Dosya yapısı

| Dosya | Görev |
|-------|-------|
| `config.py` | tüm parametreler + senaryo ön-tanımları |
| `dynamics.py` | önleyici nokta-kütle dinamiği (limitli entegrasyon) |
| `target_models.py` | CV / CA / SM / TURN hedef modelleri |
| `guidance.py` | **PNG** + pure pursuit (ortak arayüz) |
| `metrics.py` | isabet / ıska / süre / yol / ivme metrikleri |
| `simulator.py` | ana döngü (100 Hz sabit dt) |
| `visualize.py` | 3B animasyon (gif) + statik kıyas grafikleri |
| `main.py` | CLI |
| `tests/` | doğrulama testleri (PNG yakalar + pursuit'ten kısa yol) |

## İleri işler (yapılmadı, not)

- **Augmented PN**: hedef ivmesini telafi eden ek terim (CA/manevra hedeflerinde
  isabeti artırır).
- **Monte Carlo → CEP**: rastgele hedef başlangıçlarıyla istatistiksel hassasiyet.
- **Gerçekçi çok-rotor**: eğim/itki limitleri, kamera FOV/bakış-açısı kısıtı.
- **Gerçek uçuş yığını**: PX4 SITL + Gazebo + MAVSDK'ya taşıma — güdüm arayüzü
  (`a_cmd = law.command(p_i, v_i, p_t, v_t)`) buna hazır.
