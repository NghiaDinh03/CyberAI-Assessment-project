'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import Link from 'next/link'
import styles from './page.module.css'

// ── Fake real-time data ────────────────────────────────────────────────────
const POOLS = [
    { id: 'iso-eth', name: 'ISO-ETH', apy: 142.7, tvl: 4820000, vol24h: 312000, token0: 'ISO', token1: 'ETH', risk: 'medium', trending: true },
    { id: 'cyberai-usdc', name: 'CYBERAI-USDC', apy: 87.3, tvl: 12400000, vol24h: 890000, token0: 'CYBERAI', token1: 'USDC', risk: 'low', trending: false },
    { id: 'sec-bnb', name: 'SEC-BNB', apy: 231.4, tvl: 1940000, vol24h: 178000, token0: 'SEC', token1: 'BNB', risk: 'high', trending: true },
    { id: 'audit-btc', name: 'AUDIT-BTC', apy: 64.8, tvl: 8100000, vol24h: 421000, token0: 'AUDIT', token1: 'BTC', risk: 'low', trending: false },
]

const TOKENOMICS = [
    { label: 'Yield Rewards', pct: 35, color: '#00ff9d' },
    { label: 'Team & Dev', pct: 15, color: '#ff00ff' },
    { label: 'Liquidity', pct: 25, color: '#00d4ff' },
    { label: 'DAO Treasury', pct: 15, color: '#ffcc00' },
    { label: 'Ecosystem', pct: 10, color: '#ff6b35' },
]

const INFRA_CHECKS = [
    { id: 'firewall', label: 'Firewall / WAF', status: 'pass', score: 95 },
    { id: 'encryption', label: 'Data Encryption', status: 'pass', score: 98 },
    { id: 'auth', label: 'Multi-Factor Auth', status: 'warn', score: 72 },
    { id: 'patch', label: 'Patch Management', status: 'pass', score: 88 },
    { id: 'backup', label: 'Backup Strategy', status: 'fail', score: 41 },
    { id: 'siem', label: 'SIEM / Logging', status: 'warn', score: 65 },
]

const CHAT_SUGGESTIONS = [
    'What is the safest yield pool?',
    'How does APY compound?',
    'Explain ISO 27001 for DeFi',
    'Audit my infrastructure',
]

const STATS = [
    { label: 'Total Value Locked', value: '$127.4M', delta: '+12.3%', up: true },
    { label: 'Active Farmers', value: '48,291', delta: '+8.7%', up: true },
    { label: 'Avg APY', value: '141.6%', delta: '+5.2%', up: true },
    { label: 'Security Score', value: '94/100', delta: '+2pts', up: true },
]

// ── Helpers ────────────────────────────────────────────────────────────────
function fmt(n) {
    if (n >= 1e6) return `$${(n / 1e6).toFixed(2)}M`
    if (n >= 1e3) return `$${(n / 1e3).toFixed(0)}K`
    return `$${n}`
}

function useTickingValue(base, range = 0.03) {
    const [val, setVal] = useState(base)
    useEffect(() => {
        const t = setInterval(() => {
            setVal(v => +(v + (Math.random() - 0.5) * base * range).toFixed(2))
        }, 2000)
        return () => clearInterval(t)
    }, [base, range])
    return val
}

// ── Cyberpunk scan-line background ────────────────────────────────────────
function CyberpunkGrid() {
    return <div className={styles.grid} aria-hidden="true" />
}

// ── Animated neon counter ─────────────────────────────────────────────────
function NeonCounter({ target, prefix = '', suffix = '', decimals = 0 }) {
    const [count, setCount] = useState(0)
    useEffect(() => {
        let start = 0
        const step = target / 60
        const t = setInterval(() => {
            start += step
            if (start >= target) { setCount(target); clearInterval(t) }
            else setCount(+start.toFixed(decimals))
        }, 16)
        return () => clearInterval(t)
    }, [target, decimals])
    return <span>{prefix}{count.toLocaleString()}{suffix}</span>
}

// ── APY Calculator ─────────────────────────────────────────────────────────
function APYCalculator() {
    const [principal, setPrincipal] = useState(10000)
    const [apy, setApy] = useState(142.7)
    const [days, setDays] = useState(365)
    const [compound, setCompound] = useState(365)

    const result = principal * Math.pow(1 + apy / 100 / compound, compound * (days / 365))
    const profit = result - principal

    return (
        <div className={styles.calcCard}>
            <div className={styles.calcHeader}>
                <span className={styles.neonIcon}>⚡</span>
                <h3>APY Calculator</h3>
                <span className={styles.calcBadge}>Real-time</span>
            </div>
            <div className={styles.calcGrid}>
                <label className={styles.calcLabel}>
                    Principal (USD)
                    <div className={styles.inputWrap}>
                        <span className={styles.inputPrefix}>$</span>
                        <input type="number" className={styles.calcInput} value={principal}
                            onChange={e => setPrincipal(+e.target.value)} min={100} step={100} />
                    </div>
                </label>
                <label className={styles.calcLabel}>
                    APY (%)
                    <div className={styles.inputWrap}>
                        <input type="number" className={styles.calcInput} value={apy}
                            onChange={e => setApy(+e.target.value)} min={0.1} step={0.1} />
                        <span className={styles.inputSuffix}>%</span>
                    </div>
                </label>
                <label className={styles.calcLabel}>
                    Period (days)
                    <div className={styles.inputWrap}>
                        <input type="range" className={styles.calcRange} value={days}
                            onChange={e => setDays(+e.target.value)} min={1} max={730} />
                        <span className={styles.rangeVal}>{days}d</span>
                    </div>
                </label>
                <label className={styles.calcLabel}>
                    Compound
                    <select className={styles.calcSelect} value={compound} onChange={e => setCompound(+e.target.value)}>
                        <option value={1}>Annually</option>
                        <option value={12}>Monthly</option>
                        <option value={52}>Weekly</option>
                        <option value={365}>Daily</option>
                    </select>
                </label>
            </div>
            <div className={styles.calcResult}>
                <div className={styles.calcResultItem}>
                    <span className={styles.calcResultLabel}>Total Value</span>
                    <span className={styles.calcResultValue} style={{ color: '#00ff9d' }}>
                        ${result.toLocaleString(undefined, { maximumFractionDigits: 2 })}
                    </span>
                </div>
                <div className={styles.calcResultItem}>
                    <span className={styles.calcResultLabel}>Profit</span>
                    <span className={styles.calcResultValue} style={{ color: '#ff00ff' }}>
                        +${profit.toLocaleString(undefined, { maximumFractionDigits: 2 })}
                    </span>
                </div>
                <div className={styles.calcResultItem}>
                    <span className={styles.calcResultLabel}>ROI</span>
                    <span className={styles.calcResultValue} style={{ color: '#00d4ff' }}>
                        {((profit / principal) * 100).toFixed(2)}%
                    </span>
                </div>
            </div>
        </div>
    )
}

// ── Tokenomics Donut ───────────────────────────────────────────────────────
function TokenomicsDonut() {
    const size = 200, cx = 100, cy = 100, r = 70, strokeW = 28
    const circ = 2 * Math.PI * r
    let offset = 0
    const segments = TOKENOMICS.map(t => {
        const dash = (t.pct / 100) * circ
        const seg = { ...t, dasharray: `${dash - 2} ${circ - dash + 2}`, dashoffset: circ - offset }
        offset += dash
        return seg
    })
    return (
        <div className={styles.donutWrap}>
            <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className={styles.donut}>
                <circle cx={cx} cy={cy} r={r} fill="none" stroke="rgba(255,255,255,0.04)" strokeWidth={strokeW} />
                {segments.map((s, i) => (
                    <circle key={i} cx={cx} cy={cy} r={r} fill="none"
                        stroke={s.color} strokeWidth={strokeW}
                        strokeDasharray={s.dasharray}
                        strokeDashoffset={s.dashoffset}
                        style={{ transform: 'rotate(-90deg)', transformOrigin: 'center', filter: `drop-shadow(0 0 6px ${s.color})` }}
                    />
                ))}
                <text x={cx} y={cy - 8} textAnchor="middle" fill="#fff" fontSize="13" fontWeight="700">CYBERAI</text>
                <text x={cx} y={cy + 10} textAnchor="middle" fill="#888" fontSize="10">100M supply</text>
            </svg>
            <div className={styles.donutLegend}>
                {TOKENOMICS.map((t, i) => (
                    <div key={i} className={styles.legendItem}>
                        <span className={styles.legendDot} style={{ background: t.color, boxShadow: `0 0 6px ${t.color}` }} />
                        <span className={styles.legendLabel}>{t.label}</span>
                        <span className={styles.legendPct} style={{ color: t.color }}>{t.pct}%</span>
                    </div>
                ))}
            </div>
        </div>
    )
}

// ── Mini Chatbot ───────────────────────────────────────────────────────────
function ChatbotWidget() {
    const [open, setOpen] = useState(false)
    const [msgs, setMsgs] = useState([
        { role: 'assistant', text: 'Hello, farmer. I\'m CyberAI — your on-chain security & yield intelligence. Ask me anything.' }
    ])
    const [input, setInput] = useState('')
    const [typing, setTyping] = useState(false)
    const endRef = useRef(null)

    useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [msgs])

    const send = useCallback(async (text) => {
        if (!text.trim()) return
        setMsgs(p => [...p, { role: 'user', text }])
        setInput('')
        setTyping(true)
        try {
            const res = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: text, session_id: 'landing_widget' })
            })
            const data = await res.json()
            setMsgs(p => [...p, { role: 'assistant', text: data.response || 'No response.' }])
        } catch {
            setMsgs(p => [...p, { role: 'assistant', text: 'Backend offline. Try again later.' }])
        }
        setTyping(false)
    }, [])

    return (
        <>
            <button className={`${styles.chatFab} ${open ? styles.chatFabOpen : ''}`}
                onClick={() => setOpen(o => !o)} aria-label="Open AI Chat">
                <span className={styles.chatFabIcon}>{open ? '✕' : '🤖'}</span>
                {!open && <span className={styles.chatFabPulse} />}
            </button>

            {open && (
                <div className={styles.chatWindow}>
                    <div className={styles.chatHeader}>
                        <span className={styles.chatOnline} />
                        <span>CyberAI Assistant</span>
                        <span className={styles.chatModel}>gemini-3-flash</span>
                    </div>
                    <div className={styles.chatMessages}>
                        {msgs.map((m, i) => (
                            <div key={i} className={`${styles.chatMsg} ${m.role === 'user' ? styles.chatMsgUser : styles.chatMsgBot}`}>
                                {m.text}
                            </div>
                        ))}
                        {typing && <div className={`${styles.chatMsg} ${styles.chatMsgBot} ${styles.chatTyping}`}>
                            <span /><span /><span />
                        </div>}
                        <div ref={endRef} />
                    </div>
                    <div className={styles.chatSuggestions}>
                        {CHAT_SUGGESTIONS.map((s, i) => (
                            <button key={i} className={styles.chatChip} onClick={() => send(s)}>{s}</button>
                        ))}
                    </div>
                    <div className={styles.chatInputRow}>
                        <input className={styles.chatInput} value={input} placeholder="Ask CyberAI..."
                            onChange={e => setInput(e.target.value)}
                            onKeyDown={e => e.key === 'Enter' && send(input)} />
                        <button className={styles.chatSend} onClick={() => send(input)}>↑</button>
                    </div>
                </div>
            )}
        </>
    )
}

// ── Main Landing Page ──────────────────────────────────────────────────────
export default function LandingPage() {
    const [walletConnected, setWalletConnected] = useState(false)
    const [walletAddr, setWalletAddr] = useState('')
    const [activePool, setActivePool] = useState(null)
    const [infraRunning, setInfraRunning] = useState(false)
    const [infraDone, setInfraDone] = useState(false)
    const [infraResults, setInfraResults] = useState(INFRA_CHECKS)
    const [poolApys, setPoolApys] = useState(POOLS.map(p => p.apy))

    // Tick pool APYs
    useEffect(() => {
        const t = setInterval(() => {
            setPoolApys(prev => prev.map(a => +(a + (Math.random() - 0.5) * 2).toFixed(1)))
        }, 3000)
        return () => clearInterval(t)
    }, [])

    const connectWallet = async () => {
        if (walletConnected) { setWalletConnected(false); setWalletAddr(''); return }
        // Simulate wallet connect
        await new Promise(r => setTimeout(r, 800))
        const addr = '0x' + Array.from({ length: 40 }, () => Math.floor(Math.random() * 16).toString(16)).join('')
        setWalletAddr(addr)
        setWalletConnected(true)
    }

    const runInfraAssessment = async () => {
        setInfraRunning(true)
        setInfraDone(false)
        // Simulate progressive scan
        const updated = [...INFRA_CHECKS]
        for (let i = 0; i < updated.length; i++) {
            await new Promise(r => setTimeout(r, 400))
            const noise = (Math.random() - 0.5) * 10
            updated[i] = { ...updated[i], score: Math.min(100, Math.max(0, +(updated[i].score + noise).toFixed(0))) }
            setInfraResults([...updated])
        }
        setInfraRunning(false)
        setInfraDone(true)
    }

    const overallScore = Math.round(infraResults.reduce((a, c) => a + c.score, 0) / infraResults.length)

    return (
        <div className={styles.root}>
            <CyberpunkGrid />

            {/* ── Navbar ── */}
            <nav className={styles.navbar}>
                <div className={styles.navBrand}>
                    <span className={styles.navLogo}>⬡</span>
                    <span className={styles.navName}>CyberAI<span className={styles.navSub}>.FARM</span></span>
                </div>
                <div className={styles.navLinks}>
                    <a href="#pools" className={styles.navLink}>Pools</a>
                    <a href="#tokenomics" className={styles.navLink}>Tokenomics</a>
                    <a href="#assessment" className={styles.navLink}>Assessment</a>
                    <Link href="/chatbot" className={styles.navLink}>AI Chat</Link>
                </div>
                <button className={`${styles.walletBtn} ${walletConnected ? styles.walletBtnActive : ''}`}
                    onClick={connectWallet}>
                    {walletConnected
                        ? <><span className={styles.walletDot} />{walletAddr.slice(0, 6)}...{walletAddr.slice(-4)}</>
                        : '⬡ Connect Wallet'}
                </button>
            </nav>

            {/* ── Hero ── */}
            <section className={styles.hero}>
                <div className={styles.heroGlow} />
                <div className={styles.heroContent}>
                    <div className={styles.heroBadge}>
                        <span className={styles.heroBadgeDot} />
                        LIVE ON MAINNET · ISO 27001 AUDITED
                    </div>
                    <h1 className={styles.heroTitle}>
                        <span className={styles.heroTitleLine1}>AI-POWERED</span>
                        <span className={styles.heroTitleLine2}>YIELD FARMING</span>
                        <span className={styles.heroTitleLine3}>PLATFORM</span>
                    </h1>
                    <p className={styles.heroSub}>
                        Enterprise-grade security assessment meets DeFi yield optimization.
                        Audit your infrastructure, farm with confidence.
                    </p>
                    <div className={styles.heroCTA}>
                        <button className={styles.btnPrimary} onClick={connectWallet}>
                            {walletConnected ? '✓ Connected' : '⬡ Launch App'}
                        </button>
                        <Link href="/form-iso" className={styles.btnSecondary}>
                            Run Security Audit →
                        </Link>
                    </div>
                </div>

                {/* Stats strip */}
                <div className={styles.statsStrip}>
                    {STATS.map((s, i) => (
                        <div key={i} className={styles.statItem}>
                            <span className={styles.statValue}>{s.value}</span>
                            <span className={styles.statLabel}>{s.label}</span>
                            <span className={`${styles.statDelta} ${s.up ? styles.statUp : styles.statDown}`}>{s.delta}</span>
                        </div>
                    ))}
                </div>
            </section>

            {/* ── APY Calculator ── */}
            <section className={styles.section} id="calculator">
                <div className={styles.sectionHead}>
                    <span className={styles.sectionTag}>// CALCULATOR</span>
                    <h2 className={styles.sectionTitle}>Yield <span className={styles.neonGreen}>Calculator</span></h2>
                    <p className={styles.sectionSub}>Simulate compound returns across any pool</p>
                </div>
                <APYCalculator />
            </section>

            {/* ── Liquidity Pools ── */}
            <section className={styles.section} id="pools">
                <div className={styles.sectionHead}>
                    <span className={styles.sectionTag}>// LIQUIDITY POOLS</span>
                    <h2 className={styles.sectionTitle}>Active <span className={styles.neonCyan}>Pools</span></h2>
                    <p className={styles.sectionSub}>Real-time APY — updates every 3 seconds</p>
                </div>
                <div className={styles.poolsGrid}>
                    {POOLS.map((pool, i) => (
                        <div key={pool.id}
                            className={`${styles.poolCard} ${activePool === pool.id ? styles.poolCardActive : ''}`}
                            onClick={() => setActivePool(activePool === pool.id ? null : pool.id)}>
                            {pool.trending && <span className={styles.poolTrending}>🔥 TRENDING</span>}
                            <div className={styles.poolTop}>
                                <div className={styles.poolPair}>
                                    <span className={styles.poolToken} style={{ background: i % 2 === 0 ? '#00ff9d22' : '#00d4ff22' }}>
                                        {pool.token0}
                                    </span>
                                    <span className={styles.poolSlash}>/</span>
                                    <span className={styles.poolToken} style={{ background: '#ff00ff22' }}>
                                        {pool.token1}
                                    </span>
                                </div>
                                <span className={`${styles.poolRisk} ${styles[`risk_${pool.risk}`]}`}>{pool.risk}</span>
                            </div>
                            <div className={styles.poolApy}>
                                <span className={styles.poolApyVal}>{poolApys[i].toFixed(1)}%</span>
                                <span className={styles.poolApyLabel}>APY</span>
                            </div>
                            <div className={styles.poolStats}>
                                <div>
                                    <div className={styles.poolStatLabel}>TVL</div>
                                    <div className={styles.poolStatVal}>{fmt(pool.tvl)}</div>
                                </div>
                                <div>
                                    <div className={styles.poolStatLabel}>24h Vol</div>
                                    <div className={styles.poolStatVal}>{fmt(pool.vol24h)}</div>
                                </div>
                            </div>
                            {activePool === pool.id && (
                                <div className={styles.poolExpanded}>
                                    <button className={styles.btnDeposit}>Deposit Now</button>
                                    <Link href="/form-iso" className={styles.btnAudit}>Audit First →</Link>
                                </div>
                            )}
                        </div>
                    ))}
                </div>
            </section>

            {/* ── Tokenomics ── */}
            <section className={styles.section} id="tokenomics">
                <div className={styles.sectionHead}>
                    <span className={styles.sectionTag}>// TOKENOMICS</span>
                    <h2 className={styles.sectionTitle}><span className={styles.neonPurple}>CYBERAI</span> Token</h2>
                    <p className={styles.sectionSub}>100,000,000 total supply · Deflationary mechanism</p>
                </div>
                <div className={styles.tokenomicsWrap}>
                    <TokenomicsDonut />
                    <div className={styles.tokenStats}>
                        <div className={styles.tokenStatCard}>
                            <span className={styles.tokenStatLabel}>Token Price</span>
                            <span className={styles.tokenStatVal} style={{ color: '#00ff9d' }}>$2.847</span>
                            <span className={styles.tokenStatDelta}>+14.3% (24h)</span>
                        </div>
                        <div className={styles.tokenStatCard}>
                            <span className={styles.tokenStatLabel}>Market Cap</span>
                            <span className={styles.tokenStatVal} style={{ color: '#00d4ff' }}>$284.7M</span>
                            <span className={styles.tokenStatDelta}>Rank #142</span>
                        </div>
                        <div className={styles.tokenStatCard}>
                            <span className={styles.tokenStatLabel}>Circulating</span>
                            <span className={styles.tokenStatVal} style={{ color: '#ff00ff' }}>62.4M</span>
                            <span className={styles.tokenStatDelta}>62.4% of supply</span>
                        </div>
                        <div className={styles.tokenStatCard}>
                            <span className={styles.tokenStatLabel}>Burned</span>
                            <span className={styles.tokenStatVal} style={{ color: '#ffcc00' }}>3.21M</span>
                            <span className={styles.tokenStatDelta}>3.21% burned 🔥</span>
                        </div>
                    </div>
                </div>
            </section>

            {/* ── Infrastructure Assessment ── */}
            <section className={styles.section} id="assessment">
                <div className={styles.sectionHead}>
                    <span className={styles.sectionTag}>// ĐÁNH GIÁ HẠ TẦNG</span>
                    <h2 className={styles.sectionTitle}>Infrastructure <span className={styles.neonRed}>Assessment</span></h2>
                    <p className={styles.sectionSub}>Real-time security scoring powered by CyberAI · ISO 27001:2022</p>
                </div>
                <div className={styles.infraWrap}>
                    <div className={styles.infraScore}>
                        <div className={styles.infraScoreCircle}
                            style={{ '--score': overallScore, '--color': overallScore >= 80 ? '#00ff9d' : overallScore >= 60 ? '#ffcc00' : '#ff4444' }}>
                            <span className={styles.infraScoreVal}>{overallScore}</span>
                            <span className={styles.infraScoreLabel}>/ 100</span>
                        </div>
                        <p className={styles.infraScoreText}>
                            {overallScore >= 80 ? '✅ Secure to Farm' : overallScore >= 60 ? '⚠️ Moderate Risk' : '🚨 High Risk'}
                        </p>
                        <button className={styles.btnScan}
                            onClick={runInfraAssessment}
                            disabled={infraRunning}>
                            {infraRunning ? '⟳ Scanning...' : infraDone ? '⟳ Re-scan' : '▶ Run Assessment'}
                        </button>
                        <Link href="/form-iso" className={styles.btnFullAudit}>Full ISO Audit →</Link>
                    </div>
                    <div className={styles.infraChecks}>
                        {infraResults.map((c, i) => (
                            <div key={c.id} className={styles.infraCheck}
                                style={{ '--delay': `${i * 0.08}s` }}>
                                <div className={styles.infraCheckLeft}>
                                    <span className={`${styles.infraDot} ${styles[`dot_${c.status}`]}`} />
                                    <span className={styles.infraCheckLabel}>{c.label}</span>
                                </div>
                                <div className={styles.infraCheckRight}>
                                    <div className={styles.infraBar}>
                                        <div className={styles.infraBarFill}
                                            style={{
                                                width: infraRunning || infraDone ? `${c.score}%` : '0%',
                                                background: c.score >= 80 ? '#00ff9d' : c.score >= 60 ? '#ffcc00' : '#ff4444',
                                                boxShadow: c.score >= 80 ? '0 0 8px #00ff9d' : c.score >= 60 ? '0 0 8px #ffcc00' : '0 0 8px #ff4444',
                                            }}
                                        />
                                    </div>
                                    <span className={styles.infraScore2}>{c.score}</span>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* ── Trust Indicators ── */}
            <section className={styles.trustSection}>
                <div className={styles.trustGrid}>
                    {[
                        { icon: '🛡️', title: 'ISO 27001:2022', sub: 'Certified Security' },
                        { icon: '🔒', title: 'Smart Contract', sub: 'Audited by CertiK' },
                        { icon: '⚡', title: '99.97% Uptime', sub: 'Enterprise SLA' },
                        { icon: '🌐', title: 'Multi-chain', sub: 'ETH · BSC · Polygon' },
                        { icon: '🤖', title: 'AI-Powered', sub: 'RAG + LLM Analysis' },
                        { icon: '🏦', title: '$127M+ TVL', sub: 'Battle-tested Protocol' },
                    ].map((t, i) => (
                        <div key={i} className={styles.trustCard}>
                            <span className={styles.trustIcon}>{t.icon}</span>
                            <span className={styles.trustTitle}>{t.title}</span>
                            <span className={styles.trustSub}>{t.sub}</span>
                        </div>
                    ))}
                </div>
            </section>

            {/* ── Footer ── */}
            <footer className={styles.footer}>
                <div className={styles.footerBrand}>⬡ CyberAI.FARM</div>
                <div className={styles.footerLinks}>
                    <Link href="/chatbot">AI Chat</Link>
                    <Link href="/form-iso">Security Audit</Link>
                    <Link href="/analytics">Analytics</Link>
                    <a href="#">GitHub</a>
                    <a href="#">Docs</a>
                </div>
                <div className={styles.footerCopy}>© 2026 CyberAI Assessment Platform · ISO 27001:2022 Compliant</div>
            </footer>

            {/* ── Floating Chatbot ── */}
            <ChatbotWidget />
        </div>
    )
}
