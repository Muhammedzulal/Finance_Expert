-- Finance Expert - BIST hisse listesi (seed)
--
-- Haber, fiyat ve sanal alim-satim uclari yalnizca stocks tablosunda
-- aktif olan hisseleri kabul eder. Bu dosya olmadan bos bir veritabaninda
-- hisse kodu tasiyan her haber ve fiyat 422 ile reddedilir.
--
-- Liste Web_scaper/news_adapter.py icindeki COMPANY_SYMBOL_MAP ile
-- ayni sembolleri icerir; oraya hisse eklenirse buraya da eklenmelidir.
--
-- Docker Compose bu dosyayi yalnizca MySQL volume'u ilk kez olusturulurken
-- calistirir. Var olan bir veritabanina elle yuklemek icin:
--   mysql -u <kullanici> -p finance_expert < database/02_seed_stocks.sql
-- INSERT IGNORE sayesinde tekrar calistirmak zararsizdir.

INSERT IGNORE INTO stocks (symbol, company_name, market, is_active) VALUES
  -- Havacilik ve ulastirma
  ('THYAO', 'Türk Hava Yolları', 'BIST', TRUE),
  ('PGSUS', 'Pegasus Hava Taşımacılığı', 'BIST', TRUE),
  ('TAVHL', 'TAV Havalimanları Holding', 'BIST', TRUE),
  -- Bankacilik ve finans
  ('GARAN', 'Türkiye Garanti Bankası', 'BIST', TRUE),
  ('AKBNK', 'Akbank', 'BIST', TRUE),
  ('ISCTR', 'Türkiye İş Bankası (C)', 'BIST', TRUE),
  ('YKBNK', 'Yapı ve Kredi Bankası', 'BIST', TRUE),
  ('SKBNK', 'Şekerbank', 'BIST', TRUE),
  ('HALKB', 'Türkiye Halk Bankası', 'BIST', TRUE),
  ('VAKBN', 'Türkiye Vakıflar Bankası', 'BIST', TRUE),
  -- Savunma, teknoloji ve telekomunikasyon
  ('ASELS', 'Aselsan Elektronik', 'BIST', TRUE),
  ('TCELL', 'Turkcell İletişim Hizmetleri', 'BIST', TRUE),
  ('TTKOM', 'Türk Telekomünikasyon', 'BIST', TRUE),
  ('KONTR', 'Kontrolmatik Teknoloji', 'BIST', TRUE),
  ('ASTOR', 'Astor Enerji', 'BIST', TRUE),
  -- Holding, sanayi ve enerji
  ('KCHOL', 'Koç Holding', 'BIST', TRUE),
  ('SAHOL', 'Hacı Ömer Sabancı Holding', 'BIST', TRUE),
  ('TUPRS', 'Tüpraş', 'BIST', TRUE),
  ('SISE', 'Türkiye Şişe ve Cam Fabrikaları', 'BIST', TRUE),
  ('EREGL', 'Ereğli Demir ve Çelik', 'BIST', TRUE),
  ('KRDMD', 'Kardemir (D)', 'BIST', TRUE),
  ('PETKM', 'Petkim Petrokimya', 'BIST', TRUE),
  ('FROTO', 'Ford Otomotiv Sanayi', 'BIST', TRUE),
  ('TOASO', 'Tofaş Türk Otomobil Fabrikası', 'BIST', TRUE),
  ('CEMAS', 'Çemaş Döküm Sanayi', 'BIST', TRUE),
  ('MERCN', 'Mercan Kimya', 'BIST', TRUE),
  ('ENJSA', 'Enerjisa Enerji', 'BIST', TRUE),
  ('ALARK', 'Alarko Holding', 'BIST', TRUE),
  ('SASA', 'Sasa Polyester', 'BIST', TRUE),
  ('HEKTS', 'Hektaş Ticaret', 'BIST', TRUE),
  ('KLRHO', 'Kiler Holding', 'BIST', TRUE),
  -- Perakende, tuketim ve gida
  ('BIMAS', 'BİM Birleşik Mağazalar', 'BIST', TRUE),
  ('MGROS', 'Migros Ticaret', 'BIST', TRUE),
  ('SOKM', 'Şok Marketler Ticaret', 'BIST', TRUE),
  ('ULKER', 'Ülker Bisküvi', 'BIST', TRUE),
  ('VESTL', 'Vestel Elektronik', 'BIST', TRUE),
  ('MAVI', 'Mavi Giyim', 'BIST', TRUE),
  ('OTKAR', 'Otokar Otomotiv ve Savunma', 'BIST', TRUE);
