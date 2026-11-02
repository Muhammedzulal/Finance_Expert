import { FormEvent, useMemo, useState } from 'react'

type Screen = 'login' | 'home' | 'market' | 'wallet' | 'profile'
type IconName = 'home' | 'market' | 'wallet' | 'profile' | 'search' | 'bell' | 'arrow' | 'mail' | 'lock' | 'shield' | 'logout' | 'sparkles'

function Icon({ name, className = 'size-6' }: { name: IconName; className?: string }) {
  const paths: Record<IconName, React.ReactNode> = {
    home: <><path d="m3 11 9-8 9 8" /><path d="M5 10v10h14V10M9 20v-6h6v6" /></>,
    market: <><path d="M4 19V9M10 19V5M16 19v-7M22 19H2" /><path d="m3 7 6-4 6 5 6-5" /></>,
    wallet: <><path d="M4 6.5h14a3 3 0 0 1 3 3v9H5a2 2 0 0 1-2-2v-11a2 2 0 0 1 2-2h12" /><path d="M16 11h5v4h-5a2 2 0 0 1 0-4Z" /></>,
    profile: <><circle cx="12" cy="8" r="4" /><path d="M4.5 21a7.5 7.5 0 0 1 15 0" /></>,
    search: <><circle cx="11" cy="11" r="7" /><path d="m20 20-4-4" /></>,
    bell: <><path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9Z" /><path d="M10 21h4" /></>,
    arrow: <path d="m9 18 6-6-6-6" />,
    mail: <><rect x="3" y="5" width="18" height="14" rx="3" /><path d="m4 7 8 6 8-6" /></>,
    lock: <><rect x="4" y="10" width="16" height="11" rx="3" /><path d="M8 10V7a4 4 0 0 1 8 0v3M12 14v3" /></>,
    shield: <><path d="M12 3 5 6v5c0 4.8 2.8 8.2 7 10 4.2-1.8 7-5.2 7-10V6l-7-3Z" /><path d="m9 12 2 2 4-4" /></>,
    logout: <><path d="M10 5H5a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h5M14 8l4 4-4 4M8 12h10" /></>,
    sparkles: <><path d="m12 3 1.1 3.9L17 8l-3.9 1.1L12 13l-1.1-3.9L7 8l3.9-1.1L12 3Z" /><path d="m19 14 .7 2.3L22 17l-2.3.7L19 20l-.7-2.3L16 17l2.3-.7L19 14Z" /></>,
  }
  return <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[name]}</svg>
}

const navigation: { screen: Screen; label: string; icon: IconName }[] = [
  { screen: 'home', label: 'Ana Sayfa', icon: 'home' },
  { screen: 'market', label: 'Piyasa', icon: 'market' },
  { screen: 'wallet', label: 'Cüzdan', icon: 'wallet' },
  { screen: 'profile', label: 'Profil', icon: 'profile' },
]

const stocks = [
  { ticker: 'THYAO', name: 'Türk Hava Yolları', market: 'BIST 100', price: '312,75 ₺', change: '+%3,45', up: true },
  { ticker: 'AAPL', name: 'Apple Inc.', market: 'ABD', price: '7.842,10 ₺', change: '+%1,82', up: true },
  { ticker: 'GARAN', name: 'Garanti BBVA', market: 'BIST 100', price: '124,60 ₺', change: '-%1,20', up: false },
]

const holdings = [
  { ticker: 'THYAO', name: 'Türk Hava Yolları', count: '120 lot', value: '37.530,00 ₺', change: '+%3,45', up: true },
  { ticker: 'AAPL', name: 'Apple Inc.', count: '4 adet', value: '31.368,40 ₺', change: '+%1,82', up: true },
  { ticker: 'GARAN', name: 'Garanti BBVA', count: '250 lot', value: '31.150,00 ₺', change: '-%1,20', up: false },
]

function Login({ onLogin }: { onLogin: () => void }) {
  function submit(event: FormEvent) {
    event.preventDefault()
    onLogin()
  }
  return (
    <main className="relative min-h-dvh overflow-hidden bg-ink text-white">
      <div className="absolute -right-28 -top-28 size-80 rounded-full bg-mint-glow blur-3xl" />
      <div className="relative mx-auto flex min-h-dvh max-w-md flex-col justify-center px-6 py-12">
        <div className="mb-10 grid size-16 place-items-center rounded-2xl bg-mint shadow-button"><Icon name="market" className="size-9" /></div>
        <p className="text-sm font-bold tracking-brand text-mint">FINANCE EXPERT</p>
        <h1 className="mt-4 text-4xl font-bold leading-tight">Finansal geleceğinizi <span className="text-mint-light">akıllıca yönetin.</span></h1>
        <p className="mt-4 text-white-muted">Yapay zekâ destekli yatırım asistanınıza hoş geldiniz.</p>
        <form onSubmit={submit} className="mt-10 space-y-5">
          <label className="block"><span className="mb-2 block text-sm font-bold">E-posta</span><span className="flex h-14 items-center gap-3 rounded-2xl border border-white-border bg-white-input px-4 focus-within:border-mint"><Icon name="mail" className="size-5 text-white-muted" /><input required type="email" placeholder="E-posta adresiniz" className="flex-1 bg-transparent outline-none placeholder:text-white-placeholder" /></span></label>
          <label className="block"><span className="mb-2 block text-sm font-bold">Şifre</span><span className="flex h-14 items-center gap-3 rounded-2xl border border-white-border bg-white-input px-4 focus-within:border-mint"><Icon name="lock" className="size-5 text-white-muted" /><input required type="password" placeholder="Şifreniz" className="flex-1 bg-transparent outline-none placeholder:text-white-placeholder" /></span></label>
          <button type="submit" className="flex h-14 w-full items-center justify-center gap-2 rounded-2xl bg-mint font-bold shadow-button">Giriş Yap <Icon name="arrow" className="size-5" /></button>
        </form>
      </div>
    </main>
  )
}

function Header({ title }: { title: string }) {
  return <header className="flex items-center justify-between px-5 pb-6 pt-safe"><div><p className="text-xs font-bold tracking-brand text-mint">FINANCE EXPERT</p><h1 className="mt-2 text-2xl font-bold">{title}</h1></div><button type="button" className="relative grid size-11 place-items-center rounded-2xl border border-white-border bg-white-input"><Icon name="bell" className="size-5" /><span className="absolute right-2 top-2 size-2 rounded-full bg-mint" /></button></header>
}

function Home() {
  const news = ['ASELSAN yeni ihracat sözleşmesi imzaladı', 'Bankacılık endeksi güne güçlü başladı']
  return <><Header title="Merhaba, Furkan" /><section className="px-5"><div className="rounded-card bg-gradient-to-br from-navy to-navy-light p-6 shadow-summary"><p className="text-sm text-white-muted">Sanal Bakiye</p><p className="mt-3 text-3xl font-bold">100.000,00 ₺</p><div className="mt-5 flex justify-between border-t border-white-faint pt-4"><span className="text-sm text-white-muted">Bugünkü değişim</span><span className="font-bold text-mint-light">+%2,51</span></div></div></section><section className="mt-8 px-5"><h2 className="text-xl font-bold">Piyasa Gündemi</h2><div className="mt-4 space-y-3">{news.map((item) => <article key={item} className="rounded-2xl border border-white-border bg-white-input p-4"><span className="text-xs font-bold text-mint">GÜNCEL HABER</span><h3 className="mt-2 font-bold">{item}</h3><span className="mt-3 inline-flex items-center gap-2 rounded-full bg-mint-tint px-3 py-2 text-xs font-bold text-mint-light"><Icon name="sparkles" className="size-4" /> Pozitif Etki</span></article>)}</div></section></>
}

function Market() {
  const [category, setCategory] = useState('Tümü')
  const [query, setQuery] = useState('')
  const filtered = useMemo(() => stocks.filter((s) => (category === 'Tümü' || s.market === category) && `${s.ticker} ${s.name}`.toLocaleLowerCase('tr').includes(query.toLocaleLowerCase('tr'))), [category, query])
  return <><Header title="Piyasa" /><section className="px-5"><label className="flex h-14 items-center gap-3 rounded-2xl border border-white-border bg-white-input px-4"><Icon name="search" className="size-5 text-white-muted" /><input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Hisse veya ETF ara..." className="flex-1 bg-transparent outline-none placeholder:text-white-placeholder" /></label><div className="flex gap-2 py-5">{['Tümü', 'BIST 100', 'ABD'].map((item) => <button key={item} onClick={() => setCategory(item)} className={`rounded-full px-4 py-2 text-sm font-bold ${category === item ? 'bg-mint' : 'border border-white-border bg-white-input text-white-muted'}`}>{item}</button>)}</div><AssetList assets={filtered.map((s) => ({ ...s, sub: s.name, value: s.price }))} /></section></>
}

function AssetList({ assets }: { assets: { ticker: string; sub: string; value: string; change: string; up: boolean }[] }) {
  return <div className="overflow-hidden rounded-card border border-white-border bg-white-input">{assets.map((asset) => <button key={asset.ticker} className="flex w-full items-center gap-3 border-b border-white-faint p-4 text-left last:border-0"><span className="grid size-11 place-items-center rounded-xl bg-white-faint text-xs font-bold text-mint-light">{asset.ticker.slice(0, 2)}</span><span className="min-w-0 flex-1"><b className="block text-sm">{asset.ticker}</b><span className="block truncate text-xs text-white-muted">{asset.sub}</span></span><span className="text-right"><b className="block text-sm">{asset.value}</b><span className={`text-xs font-bold ${asset.up ? 'text-mint-light' : 'text-red-light'}`}>{asset.change}</span></span></button>)}</div>
}

function Wallet() {
  return <><Header title="Sanal Cüzdanım" /><section className="px-5"><div className="rounded-card bg-gradient-to-br from-navy to-navy-light p-6 shadow-summary"><p className="text-sm text-white-muted">Toplam Portföy Değeri</p><p className="mt-3 text-3xl font-bold">125.430,00 ₺</p><div className="mt-5 flex justify-between border-t border-white-faint pt-4"><span className="text-sm text-white-muted">Toplam kâr / zarar</span><span className="font-bold text-mint-light">+%12,4</span></div></div><div className="mt-4 grid grid-cols-2 gap-3"><button className="h-14 rounded-2xl bg-mint font-bold">Para Yatır</button><button className="h-14 rounded-2xl border border-white-border bg-white-input font-bold">Hisse Al</button></div><h2 className="mb-4 mt-8 text-xl font-bold">Varlıklarım</h2><AssetList assets={holdings.map((h) => ({ ticker: h.ticker, sub: `${h.name} · ${h.count}`, value: h.value, change: h.change, up: h.up }))} /></section></>
}

function Profile({ onLogout }: { onLogout: () => void }) {
  const settings: { label: string; icon: IconName }[] = [{ label: 'Hesap Bilgileri', icon: 'profile' }, { label: 'Bildirim Ayarları', icon: 'bell' }, { label: 'Güvenlik', icon: 'shield' }]
  return <><Header title="Profil" /><section className="px-5"><div className="rounded-card border border-white-border bg-white-input p-7 text-center"><div className="mx-auto grid size-24 place-items-center rounded-avatar border-4 border-mint bg-navy text-2xl font-bold">FT</div><h2 className="mt-5 text-xl font-bold">Furkan Taşkıran</h2><p className="mt-1 text-sm text-white-muted">furkan.taskiran@email.com</p></div><div className="mt-7 overflow-hidden rounded-card border border-white-border bg-white-input">{settings.map((item) => <button key={item.label} className="flex w-full items-center gap-4 border-b border-white-faint p-4 last:border-0"><span className="grid size-10 place-items-center rounded-xl bg-mint-tint text-mint-light"><Icon name={item.icon} className="size-5" /></span><span className="flex-1 text-left font-bold">{item.label}</span><Icon name="arrow" className="size-5 text-white-muted" /></button>)}</div><button onClick={onLogout} className="mt-4 flex w-full items-center gap-3 rounded-2xl border border-red-border bg-red-tint p-4 font-bold text-red-light"><Icon name="logout" className="size-5" />Çıkış Yap</button></section></>
}

function BottomNav({ screen, onChange }: { screen: Screen; onChange: (screen: Screen) => void }) {
  return <nav className="fixed inset-x-0 bottom-0 z-20 mx-auto max-w-md border-t border-white-border bg-nav px-2 pb-safe shadow-nav backdrop-blur-sm"><div className="grid h-20 grid-cols-4">{navigation.map((item) => { const active = item.screen === screen; return <button key={item.screen} onClick={() => onChange(item.screen)} className={`relative flex flex-col items-center justify-center gap-1 text-xs font-semibold ${active ? 'text-mint' : 'text-white-muted'}`}>{active && <span className="absolute top-0 h-1 w-7 rounded-full bg-mint" />}<span className={`grid size-8 place-items-center rounded-xl ${active ? 'bg-mint-tint' : ''}`}><Icon name={item.icon} className="size-5" /></span>{item.label}</button> })}</div></nav>
}

export default function App() {
  const [screen, setScreen] = useState<Screen>('login')
  if (screen === 'login') return <Login onLogin={() => setScreen('home')} />
  return <main className="min-h-dvh bg-ink text-white"><div className="mx-auto min-h-dvh max-w-md pb-28">{screen === 'home' && <Home />}{screen === 'market' && <Market />}{screen === 'wallet' && <Wallet />}{screen === 'profile' && <Profile onLogout={() => setScreen('login')} />}</div><BottomNav screen={screen} onChange={setScreen} /></main>
}
