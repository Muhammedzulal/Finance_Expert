import 'package:flutter/material.dart';

import '../data/finance_repository.dart';
import '../models/models.dart';
import '../theme/app_colors.dart';
import '../utils/format.dart';
import '../widgets/common.dart';
import 'stock_detail_screen.dart';

/// Piyasa ekranı: GET /api/v1/stocks + her hissenin son fiyatı.
class MarketScreen extends StatefulWidget {
  const MarketScreen({super.key});

  @override
  State<MarketScreen> createState() => _MarketScreenState();
}

class _MarketScreenState extends State<MarketScreen> {
  final FinanceRepository _repo = FinanceRepository.instance;
  final TextEditingController _searchController = TextEditingController();

  int _selectedFilterIndex = 0;
  final List<String> _filters = ['Tümü', 'BIST', 'Diğer'];

  Loaded<List<Stock>>? _stocks;
  Map<String, Quote?> _quotes = {};
  String? _error;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _searchController.addListener(() => setState(() {}));
    _load();
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final Loaded<List<Stock>> stocks = await _repo.stocks();
      final Map<String, Quote?> quotes = await _repo.quotes(
        stocks.data.map((s) => s.symbol),
      );
      if (!mounted) return;
      setState(() {
        _stocks = stocks;
        _quotes = quotes;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  List<Stock> get _visibleStocks {
    final List<Stock> all = _stocks?.data ?? const [];
    final String query = _searchController.text.trim().toUpperCase();
    return all.where((s) {
      if (!s.isActive) return false;
      if (_selectedFilterIndex == 1 && s.market.toUpperCase() != 'BIST') {
        return false;
      }
      if (_selectedFilterIndex == 2 && s.market.toUpperCase() == 'BIST') {
        return false;
      }
      if (query.isEmpty) return true;
      return s.symbol.toUpperCase().contains(query) ||
          s.companyName.toUpperCase().contains(query);
    }).toList();
  }

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: RefreshIndicator(
        color: AppColors.accent,
        onRefresh: _load,
        child: ListView(
          padding: const EdgeInsets.all(20.0),
          children: [
            const ScreenHeader(title: 'Piyasa'),
            const SizedBox(height: 20),
            // Arama Çubuğu
            TextField(
              controller: _searchController,
              style: const TextStyle(color: Colors.white),
              textCapitalization: TextCapitalization.characters,
              decoration: InputDecoration(
                hintText: 'Hisse kodu veya şirket ara...',
                hintStyle: const TextStyle(
                  color: AppColors.subtle,
                  fontSize: 14,
                ),
                prefixIcon: const Icon(
                  Icons.search_rounded,
                  color: AppColors.subtle,
                ),
                filled: true,
                fillColor: AppColors.card,
                contentPadding: const EdgeInsets.symmetric(vertical: 14),
                enabledBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(14),
                  borderSide: const BorderSide(color: AppColors.border),
                ),
                focusedBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(14),
                  borderSide: const BorderSide(color: AppColors.accent),
                ),
              ),
            ),
            const SizedBox(height: 16),
            // Filtre Chip'leri
            Row(
              children: List.generate(_filters.length, (index) {
                final bool isSelected = _selectedFilterIndex == index;
                return Padding(
                  padding: const EdgeInsets.only(right: 10),
                  child: GestureDetector(
                    onTap: () => setState(() => _selectedFilterIndex = index),
                    child: Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 18,
                        vertical: 9,
                      ),
                      decoration: BoxDecoration(
                        color: isSelected ? AppColors.accent : AppColors.card,
                        borderRadius: BorderRadius.circular(20),
                        border: Border.all(
                          color: isSelected
                              ? AppColors.accent
                              : AppColors.border,
                        ),
                      ),
                      child: Text(
                        _filters[index],
                        style: TextStyle(
                          color: isSelected ? Colors.white : AppColors.muted,
                          fontSize: 13,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ),
                  ),
                );
              }),
            ),
            const SizedBox(height: 20),
            if (_stocks?.fromCache ?? false)
              OfflineBanner(cachedAt: _stocks!.cachedAt),
            _buildList(),
          ],
        ),
      ),
    );
  }

  Widget _buildList() {
    if (_stocks == null && _loading) return const LoadingBox(height: 240);
    if (_stocks == null) {
      return ErrorBox(message: _error ?? 'Hisseler alınamadı.', onRetry: _load);
    }
    final List<Stock> stocks = _visibleStocks;
    if (stocks.isEmpty) {
      return const EmptyBox(
        message: 'Aramanıza uyan hisse bulunamadı.',
        icon: Icons.search_off_rounded,
      );
    }
    final List<Widget> rows = [];
    for (int i = 0; i < stocks.length; i++) {
      if (i > 0) rows.add(listDivider);
      rows.add(_buildStockRow(stocks[i], _quotes[stocks[i].symbol]));
    }
    return CardBox(child: Column(children: rows));
  }

  Widget _buildStockRow(Stock stock, Quote? quote) {
    return InkWell(
      onTap: () => Navigator.push(
        context,
        MaterialPageRoute(
          builder: (_) => StockDetailScreen(
            symbol: stock.symbol,
            companyName: stock.companyName,
          ),
        ),
      ),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
        child: Row(
          children: [
            SymbolBadge(symbol: stock.symbol),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    stock.symbol,
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 15,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  const SizedBox(height: 3),
                  Text(
                    stock.companyName,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(color: AppColors.muted, fontSize: 12),
                  ),
                ],
              ),
            ),
            Column(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                Text(
                  quote == null ? '—' : formatMoney(quote.price),
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 15,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(height: 3),
                Text(
                  quote == null
                      ? 'Fiyat yok'
                      : '${quote.isDelayed ? 'Gecikmeli · ' : ''}${formatShortTime(quote.asOf)}',
                  style: TextStyle(
                    color: quote?.isDelayed ?? false
                        ? AppColors.warning
                        : AppColors.muted,
                    fontSize: 12,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
