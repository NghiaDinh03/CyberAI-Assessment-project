'use client'

export default function SvgGauge({ percent = 0, size = 120, color = 'var(--accent-blue)' }) {
    const r = (size - 16) / 2
    const circ = 2 * Math.PI * r
    const validPct = Math.max(0, Math.min(100, isNaN(percent) ? 0 : percent))
    const strokeDashoffset = circ - (validPct / 100) * circ

    return (
        <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
            <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="8" />
            <circle
                cx={size / 2}
                cy={size / 2}
                r={r}
                fill="none"
                stroke={color}
                strokeWidth="8"
                strokeDasharray={circ}
                strokeDashoffset={strokeDashoffset}
                strokeLinecap="round"
                transform={`rotate(-90 ${size / 2} ${size / 2})`}
                style={{ transition: 'stroke-dashoffset 0.8s ease' }}
            />
        </svg>
    )
}
