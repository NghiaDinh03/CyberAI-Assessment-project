import styles from './Skeleton.module.css'

/** Single line placeholder — width controls the visual width */
export function SkeletonLine({ width = '100%', height = '0.85rem' }) {
    return (
        <div
            className={styles.shimmer}
            style={{ width, height, borderRadius: '4px' }}
            aria-hidden="true"
        />
    )
}

/** Block / card placeholder */
export function SkeletonBlock({ height = '120px', width = '100%' }) {
    return (
        <div
            className={styles.shimmer}
            style={{ width, height, borderRadius: '10px' }}
            aria-hidden="true"
        />
    )
}

/** Pre-composed card with avatar + 3 lines */
export function SkeletonCard() {
    return (
        <div className={styles.card} aria-hidden="true">
            <div className={styles.cardHeader}>
                <div className={`${styles.shimmer} ${styles.avatar}`} />
                <div className={styles.cardHeaderLines}>
                    <SkeletonLine width="55%" height="0.8rem" />
                    <SkeletonLine width="35%" height="0.65rem" />
                </div>
            </div>
            <div className={styles.cardBody}>
                <SkeletonLine width="100%" />
                <SkeletonLine width="88%" />
                <SkeletonLine width="65%" />
            </div>
        </div>
    )
}

/** Table skeleton with configurable rows and columns */
export function SkeletonTable({ rows = 5, cols = 4 }) {
    return (
        <div className={styles.table} aria-hidden="true">
            {/* Header row */}
            <div className={styles.tableRow}>
                {Array.from({ length: cols }).map((_, ci) => (
                    <div key={ci} className={styles.tableCell}>
                        <div className={`${styles.shimmer} ${styles.tableHeader}`} />
                    </div>
                ))}
            </div>
            {/* Body rows */}
            {Array.from({ length: rows }).map((_, ri) => (
                <div key={ri} className={`${styles.tableRow} ${styles.tableBodyRow}`}>
                    {Array.from({ length: cols }).map((_, ci) => (
                        <div key={ci} className={styles.tableCell}>
                            <div
                                className={styles.shimmer}
                                style={{
                                    height: '0.8rem',
                                    borderRadius: '4px',
                                    width: ci === 0 ? '80%' : ci === cols - 1 ? '40%' : '70%',
                                }}
                            />
                        </div>
                    ))}
                </div>
            ))}
        </div>
    )
}
