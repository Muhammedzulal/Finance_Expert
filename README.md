# Finance_Expert
Mobil Programlama projemiz

## Dokümantasyon

Haber toplama, AI analizi, REST API ve Android modülleri için mimari ve veri formatları.

- [Mimari ve veri akışı](docs/mimari.md)
- [JSON sözleşmeleri ve API taslağı](docs/veri-sozlesmeleri.md)
- [Git ve PR kuralları](CONTRIBUTING.md)
- [Haber analizi dili ve uyarılar](docs/analiz-ilkeleri.md)
- [JSON şemaları](contracts/finance-v1.schema.json)
- [Örnek JSON verileri](contracts/examples.json)

Sözleşmeleri doğrulamak için Python 3.11 veya üzeriyle:

```sh
python -m pip install -r requirements-contracts.txt
python tools/validate_contracts.py
```

Bu kontrol ağ bağlantısı, fiyat servisi veya LLM anahtarı gerektirmez.
