# CV ve mülakat hazırlığı

## Türkçe CV

**Customer Behavior & Sales Analytics — Python, SQL, Pandas, Matplotlib**

- UCI Online Retail işlem verisini indiren, temizleyen ve SQLite üzerinde birleştirip analiz eden tekrarlanabilir bir veri analizi akışı geliştirdim.
- Müşteri satın alma örüntülerini RFM segmentasyonu, sipariş bazlı betimsel istatistikler ve aylık satış trendleriyle inceledim.
- Aylık ve haftalık satış örüntülerini görselleştirdim; eksik dönemleri ve müşteri kimliği eksik kayıtları ayrı ele aldım, SQL sonuçlarını Pandas ile doğruladım.

## English CV

**Customer Behavior & Sales Analytics — Python, SQL, Pandas, Matplotlib**

- Built a reproducible workflow to download, clean, join and analyze real UCI Online Retail transactions using Python and SQLite.
- Investigated purchasing patterns, customer segments and gross sales trends through RFM analysis and order-level descriptive statistics.
- Created visual reports on monthly and weekly sales patterns, with explicit handling of partial periods and anonymous transactions and SQL/Pandas reconciliation checks.

## Mülakatta açıklaman gerekenler

1. Neden müşteri kimliği olmayan kayıtları tümüyle silmedin? Genel satış ölçümü için geçerli olabilirler; müşteri analizi için kimlik gerekir.
2. Neden Frequency satır sayısı değil? Bir sipariş çok sayıda ürün kalemi içerebilir.
3. RFM bir AI modeli mi? Hayır; deterministik ve açıklanabilir segmentasyon. Tahmin modeli ayrıca hedef tanımı, zamansal ayrım ve değerlendirme gerektirir.
4. Neden Aralık 2011 düşüşünü iş kaybı olarak yorumlamadın? Gözlem yalnızca ilk dokuz günü kapsar.
5. Neden brüt satış diyorsun? İptaller/iade hareketleri dışarıda; net muhasebe geliri hesaplanmıyor.
6. Bir SQL JOIN nasıl tutarı şişirir? Boyut tablosunda aynı anahtardan birden çok satır varsa işlem satırı çoğalır. Benzersiz ürün anahtarı ve satır sayısı kontrolü bunu engeller.

Projeyi kendi ortamında çalıştır, SQL sorgularını ve temizleme varsayımlarını incele. CV'deki birinci tekil şahıs ifadelerini çalışmayı anlayıp sahiplenebildiğinde kullan. Ölçülmemiş satış artışı, churn doğruluğu veya ticari uygulama deneyimi ekleme.
