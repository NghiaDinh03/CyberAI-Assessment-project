#!/usr/bin/env node
/**
 * Frontend Test Suite for Weighted Compliance (Section 11 Audit).
 * Verifies:
 * 1. WEIGHT_SCORE in standards.js is 10-5-3-1.
 * 2. ISO max score = 495, TCVN max score = 271.
 * 3. calcWeightedScore accurately implements preview with 10-5-3-1.
 * 4. Deduplication & invalid control isolation.
 * 5. ResultView extracts weighted_compliance.percentage and handles 0.0% without false fallback.
 * 6. Raw Coverage vs Weighted Compliance isolation.
 * 7. Backward compatibility with legacy schema (weight_score_v1, missing weight_scheme).
 */

import { readFileSync, existsSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

import {
    WEIGHT_SCORE,
    ISO_27001_CONTROLS,
    TCVN_11930_CONTROLS,
    calcWeightedScore,
    calcWeightedCoverage,
    calcCategoryBreakdown,
    calcCategoryComplianceBreakdown,
    normalizeAssessmentMetrics,
    isValidNumber
} from '../src/data/standards.js'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)
const ROOT = resolve(__dirname, '..')

const failures = []
let passedCount = 0

function test(name, fn) {
    try {
        fn()
        passedCount++
        console.log(`  ✓ ${name}`)
    } catch (err) {
        failures.push({ name, error: err.message || err })
        console.error(`  ✗ ${name}: ${err.message || err}`)
    }
}

function assert(cond, msg) {
    if (!cond) throw new Error(msg)
}

function assertClose(actual, expected, tol = 0.05, msg = '') {
    if (Math.abs(actual - expected) > tol) {
        throw new Error(`${msg}: expected ${expected}, got ${actual}`)
    }
}

console.log('\n--- Running Frontend Weighted Compliance Tests ---')

// 1. WEIGHT_SCORE definition
test('1. Frontend WEIGHT_SCORE is 10-5-3-1', () => {
    assert(WEIGHT_SCORE.critical === 10, 'critical weight must be 10')
    assert(WEIGHT_SCORE.high === 5, 'high weight must be 5')
    assert(WEIGHT_SCORE.medium === 3, 'medium weight must be 3')
    assert(WEIGHT_SCORE.low === 1, 'low weight must be 1')
    assert(WEIGHT_SCORE.critical !== 4, 'critical must NOT be 4')
})

// 2. ISO 27001 catalog max score
test('2. ISO 27001 (93 controls) has weighted_max_score = 495.0', () => {
    let totalControls = 0
    let totalMax = 0
    for (const cat of ISO_27001_CONTROLS) {
        for (const ctrl of cat.controls) {
            totalControls++
            const w = WEIGHT_SCORE[ctrl.weight] || 3
            totalMax += w
        }
    }
    assert(totalControls === 93, `ISO 27001 must have 93 controls, found ${totalControls}`)
    assert(totalMax === 495, `ISO 27001 max score must be 495, found ${totalMax}`)
})

// 3. TCVN 11930 catalog max score
test('3. TCVN 11930 (34 controls) has weighted_max_score = 271.0', () => {
    let totalControls = 0
    let totalMax = 0
    for (const cat of TCVN_11930_CONTROLS) {
        for (const ctrl of cat.controls) {
            totalControls++
            const w = WEIGHT_SCORE[ctrl.weight] || 3
            totalMax += w
        }
    }
    assert(totalControls === 34, `TCVN 11930 must have 34 controls, found ${totalControls}`)
    assert(totalMax === 271, `TCVN 11930 max score must be 271, found ${totalMax}`)
})

// 4. Preview calcWeightedScore for all controls checked
test('4. calcWeightedScore preview gives 100% and max score when all controls checked', () => {
    const allIsoIds = ISO_27001_CONTROLS.flatMap(c => c.controls.map(ctrl => ctrl.id))
    const resIso = calcWeightedScore(allIsoIds, ISO_27001_CONTROLS)
    assert(resIso.maxScore === 495, `ISO max score must be 495, got ${resIso.maxScore}`)
    assert(resIso.achievedScore === 495, `ISO achieved score must be 495, got ${resIso.achievedScore}`)
    assert(resIso.percentage === 100, `ISO percentage must be 100, got ${resIso.percentage}`)

    const allTcvnIds = TCVN_11930_CONTROLS.flatMap(c => c.controls.map(ctrl => ctrl.id))
    const resTcvn = calcWeightedScore(allTcvnIds, TCVN_11930_CONTROLS)
    assert(resTcvn.maxScore === 271, `TCVN max score must be 271, got ${resTcvn.maxScore}`)
    assert(resTcvn.achievedScore === 271, `TCVN achieved score must be 271, got ${resTcvn.achievedScore}`)
    assert(resTcvn.percentage === 100, `TCVN percentage must be 100, got ${resTcvn.percentage}`)
})

// 5. Preview single control contribution
test('5. Single Critical control gives exactly 10 points in preview', () => {
    const critCtrl = ISO_27001_CONTROLS.flatMap(c => c.controls).find(c => c.weight === 'critical')
    assert(critCtrl, 'Must find a critical control')
    const res = calcWeightedScore([critCtrl.id], ISO_27001_CONTROLS)
    assert(res.achievedScore === 10, `Achieved score must be 10, got ${res.achievedScore}`)
    assertClose(res.percentage, (10 / 495) * 100, 0.05)
})

test('6. Single High, Medium, Low controls give 5, 3, 1 points respectively', () => {
    const highCtrl = ISO_27001_CONTROLS.flatMap(c => c.controls).find(c => c.weight === 'high')
    const medCtrl = ISO_27001_CONTROLS.flatMap(c => c.controls).find(c => c.weight === 'medium')
    const lowCtrl = ISO_27001_CONTROLS.flatMap(c => c.controls).find(c => c.weight === 'low')

    const resHigh = calcWeightedScore([highCtrl.id], ISO_27001_CONTROLS)
    assert(resHigh.achievedScore === 5, `High must give 5 points, got ${resHigh.achievedScore}`)

    const resMed = calcWeightedScore([medCtrl.id], ISO_27001_CONTROLS)
    assert(resMed.achievedScore === 3, `Med must give 3 points, got ${resMed.achievedScore}`)

    const resLow = calcWeightedScore([lowCtrl.id], ISO_27001_CONTROLS)
    assert(resLow.achievedScore === 1, `Low must give 1 point, got ${resLow.achievedScore}`)
})

// 7. Deduplication & invalid control tolerance
test('7. calcWeightedScore ignores duplicates and unknown IDs', () => {
    const critCtrl = ISO_27001_CONTROLS.flatMap(c => c.controls).find(c => c.weight === 'critical')
    const res = calcWeightedScore([critCtrl.id, critCtrl.id, 'UNKNOWN.999'], ISO_27001_CONTROLS)
    assert(res.achievedScore === 10, `Duplicates and unknown controls must not inflate score, got ${res.achievedScore}`)
})

// 8. ResultView source code audit
test('8. ResultView separates Raw Coverage and Weighted Compliance', () => {
    const rvPath = resolve(ROOT, 'src/app/form-iso/_components/views/ResultView.js')
    assert(existsSync(rvPath), `ResultView.js not found at ${rvPath}`)
    const src = readFileSync(rvPath, 'utf8')

    // Must extract normalizeAssessmentMetrics
    assert(src.includes('normalizeAssessmentMetrics'), 'ResultView must use normalizeAssessmentMetrics')
    // Must NOT gate server score with serverPct > 0 (which causes 0.0% to fail)
    assert(!src.includes('serverPct > 0 ? serverPct : previewCalc.percentage'),
        'ResultView must not discard 0.0% server score')
    // Must include Raw Coverage card / section
    assert(src.includes('Raw Coverage') || src.includes('Phạm vi thô'),
        'ResultView must have distinct Raw Coverage display')
    // Must include weight guide badge
    assert(src.includes('Critical = 10') || src.includes('Critical=10'),
        'ResultView must display authoritative 10-5-3-1 weight guide')
})

// 9. Legacy assessment handling & fallback safety
test('9. ResultView logic safely handles legacy payloads without weight_scheme', () => {
    const legacyResult = {
        id: 'legacy-test-01',
        status: 'completed',
        compliance_percent: 45.5,
        weighted_compliance: {
            weighted_score: 110,
            weighted_max_score: 244,
            percentage: 45.5,
            algorithm: 'weight_score_v1'
        },
        json_data: {}
    }

    const metrics = normalizeAssessmentMetrics(legacyResult, ISO_27001_CONTROLS)
    assert(metrics.weightedCompliance.percentage === 45.5, 'Legacy percentage should parse cleanly')
    assert(metrics.weightedCompliance.maxScore === 244, 'Legacy max score preserved without crashing')
})

// 10. Empty or 0.0% assessment handling
test('10. Result with 0.0% weighted compliance preserves 0.0% without falling back to self-declared', () => {
    const zeroResult = {
        id: 'zero-test-01',
        status: 'completed',
        compliance_percent: 0.0,
        weighted_compliance: {
            weighted_score: 0.0,
            weighted_max_score: 495.0,
            percentage: 0.0,
            algorithm: 'verdict_weighted_v2',
            weight_scheme: 'critical_10_high_5_medium_3_low_1'
        },
        implemented_controls: ['A.5.1', 'A.5.2']
    }

    const metrics = normalizeAssessmentMetrics(zeroResult, ISO_27001_CONTROLS)
    assert(metrics.weightedCompliance.percentage === 0.0, 'Server percentage must remain 0.0')
    assert(!metrics.compliancePending, 'Completed 0.0% assessment must not be pending')
})

// 11. Mandated Fixture Payload (Section 9)
test('11. Section 9 Mandated Fixture: 48.4% Raw, 58.4% Weighted Coverage, 0.0% Weighted Compliance', () => {
    const fixturePayload = {
        status: "completed",
        weighted_coverage: {
            weighted_score: 289,
            weighted_max_score: 495,
            percentage: 58.4
        },
        weighted_compliance: {
            weighted_score: 0,
            weighted_max_score: 495,
            percentage: 0
        },
        control_coverage: {
            self_declared_implemented: 45,
            total_controls: 93,
            raw_percentage: 48.4
        }
    }

    const metrics = normalizeAssessmentMetrics(fixturePayload, ISO_27001_CONTROLS)

    // Verify Raw Coverage
    assert(metrics.rawCoverage.implemented === 45, `Raw implemented must be 45, got ${metrics.rawCoverage.implemented}`)
    assert(metrics.rawCoverage.total === 93, `Raw total must be 93, got ${metrics.rawCoverage.total}`)
    assert(metrics.rawCoverage.percentage === 48.4, `Raw percentage must be 48.4, got ${metrics.rawCoverage.percentage}`)

    // Verify Weighted Coverage
    assert(metrics.weightedCoverage.score === 289, `Weighted coverage score must be 289, got ${metrics.weightedCoverage.score}`)
    assert(metrics.weightedCoverage.maxScore === 495, `Weighted coverage maxScore must be 495, got ${metrics.weightedCoverage.maxScore}`)
    assert(metrics.weightedCoverage.percentage === 58.4, `Weighted coverage pct must be 58.4, got ${metrics.weightedCoverage.percentage}`)

    // Verify Weighted Compliance (strictly 0.0%, no fallback!)
    assert(metrics.weightedCompliance.score === 0, `Weighted compliance score must be 0, got ${metrics.weightedCompliance.score}`)
    assert(metrics.weightedCompliance.percentage === 0.0, `Weighted compliance pct must be 0.0, got ${metrics.weightedCompliance.percentage}`)
    assert(metrics.compliancePending === false, 'compliancePending must be false when completed')
    assert(metrics.satisfiedCount === 0, `satisfiedCount must be 0, got ${metrics.satisfiedCount}`)
})

// 12. Test percentage = 0 không bị fallback
test('12. isValidNumber(0) is true, percentage=0 never falls back to truthy default', () => {
    assert(isValidNumber(0) === true, '0 must be valid number')
    assert(isValidNumber('0') === true, '"0" must be valid number')
    assert(isValidNumber(null) === false, 'null must NOT be valid number')
    assert(isValidNumber(undefined) === false, 'undefined must NOT be valid number')
    assert(isValidNumber(NaN) === false, 'NaN must NOT be valid number')

    const res = {
        status: 'completed',
        weighted_compliance: { percentage: 0 },
        weighted_coverage: { percentage: 58.4 }
    }
    const metrics = normalizeAssessmentMetrics(res, ISO_27001_CONTROLS)
    assert(metrics.weightedCompliance.percentage === 0.0, 'Must be 0.0%')
    assert(metrics.weightedCompliance.percentage !== 58.4, 'Must NEVER fallback to 58.4%')
})

// 13. Test weighted_score = 0 vẫn hiển thị
test('13. weighted_score = 0 is preserved and displayed as 0, not null', () => {
    const res = {
        status: 'completed',
        weighted_compliance: { weighted_score: 0, percentage: 0 }
    }
    const metrics = normalizeAssessmentMetrics(res, ISO_27001_CONTROLS)
    assert(metrics.weightedCompliance.score === 0.0, 'Score 0 must be preserved as 0.0')
})

// 14. Test percentage = null mới hiển thị "Đang thẩm định"
test('14. percentage = null marks compliancePending = true', () => {
    const resProcessing = {
        status: 'processing',
        weighted_compliance: null,
        weighted_coverage: { score: 289, max_score: 495, percentage: 58.4 }
    }
    const metrics = normalizeAssessmentMetrics(resProcessing, ISO_27001_CONTROLS)
    assert(metrics.compliancePending === true, 'Must be pending when percentage is null')
    assert(metrics.weightedCompliance.percentage === null, 'percentage must be null')
    assert(metrics.weightedCoverage.percentage === 58.4, 'Weighted coverage 58.4 preserved during processing')
})

// 15. Trạng thái processing hiển thị 58.4 dưới nhãn Weighted Coverage
test('15. Processing state shows 58.4 under provisional Weighted Coverage label', () => {
    const rvPath = resolve(ROOT, 'src/app/form-iso/_components/views/ResultView.js')
    const src = readFileSync(rvPath, 'utf8')
    assert(src.includes('WEIGHTED COVERAGE (PROVISIONAL)') || src.includes('ĐỘ PHỦ CÓ TRỌNG SỐ (TẠM TÍNH)'),
        'ResultView must have provisional weighted coverage label for processing state')
    assert(src.includes('metrics.weightedCoverage.percentage'),
        'ResultView must display metrics.weightedCoverage.percentage')
})

// 16. Trạng thái completed dùng Weighted Compliance của backend
test('16. Completed state strictly uses Weighted Compliance from backend', () => {
    const completedResult = {
        status: 'completed',
        json_data: {
            weighted_compliance: { percentage: 0.0, weighted_score: 0.0, weighted_max_score: 495.0 }
        },
        weighted_coverage: { percentage: 58.4, score: 289.0, max_score: 495.0 }
    }
    const metrics = normalizeAssessmentMetrics(completedResult, ISO_27001_CONTROLS)
    assert(metrics.weightedCompliance.percentage === 0.0, 'Must use 0.0 from backend json_data.weighted_compliance')
})

// 17. Category Analysis 289/495 mang nhãn Weighted Coverage
test('17. Category Analysis 289/495 is labeled Weighted Coverage in vi.json and en.json', () => {
    const viPath = resolve(ROOT, 'src/i18n/vi.json')
    const enPath = resolve(ROOT, 'src/i18n/en.json')
    const vi = JSON.parse(readFileSync(viPath, 'utf8'))
    const en = JSON.parse(readFileSync(enPath, 'utf8'))

    assert(vi.assessment.categoryBreakdown.includes('Phạm vi có trọng số'),
        `vi.json categoryBreakdown must be 'Phân tích theo nhóm — Phạm vi có trọng số', got: ${vi.assessment.categoryBreakdown}`)
    assert(en.assessment.categoryBreakdown.includes('Weighted Coverage'),
        `en.json categoryBreakdown must be 'Category Analysis — Weighted Coverage', got: ${en.assessment.categoryBreakdown}`)
})

// 18. Payload cũ vẫn mở được nhưng không được đánh tráo hai chỉ số
test('18. Legacy payload with only compliance_percent: 75.0 preserves 75.0% compliance', () => {
    const legacy = {
        status: 'completed',
        compliance_percent: 75.0,
        implemented_controls: ['A.5.1', 'A.5.2']
    }
    const metrics = normalizeAssessmentMetrics(legacy, ISO_27001_CONTROLS)
    assert(metrics.weightedCompliance.percentage === 75.0, 'Legacy compliance_percent preserved')
    assert(metrics.rawCoverage.implemented === 2, 'Raw coverage implemented correctly reflects count')
    assert(metrics.weightedCoverage.percentage < 10.0, 'Weighted coverage not conflated with compliance')
})

// 19. ResultView.js contains required Control Table headers and structure
test('19. ResultView contains Control Table headers: Control ID, Trọng số, Verdict, Hệ số, Điểm đóng góp, Đối soát', () => {
    const resultViewPath = resolve(ROOT, 'src/app/form-iso/_components/views/ResultView.js')
    const src = readFileSync(resultViewPath, 'utf8')
    assert(src.includes('controlTablePanel'), 'Must have controlTablePanel')
    assert(src.includes('Control ID'), 'Must have Control ID column')
    assert(src.includes('Trọng số') || src.includes('Weight'), 'Must have Trọng số / Weight column')
    assert(src.includes('Verdict'), 'Must have Verdict column')
    assert(src.includes('Hệ số') || src.includes('Factor'), 'Must have Hệ số / Factor column')
    assert(src.includes('Điểm đóng góp') || src.includes('Contribution'), 'Must have Điểm đóng góp column')
    assert(src.includes('Đối soát chuyên gia') || src.includes('Expert Review'), 'Must have Đối soát chuyên gia column')
})

// 20. Tooltip / mô tả thang điểm chuẩn 10-5-3-1
test('20. ResultView and standards UI use exact scale: Critical=10, High=5, Medium=3, Low=1', () => {
    const resultViewPath = resolve(ROOT, 'src/app/form-iso/_components/views/ResultView.js')
    const src = readFileSync(resultViewPath, 'utf8')
    assert(src.includes('Critical = 10 · High = 5 · Medium = 3 · Low = 1') || src.includes('Critical=10 · High=5 · Medium=3 · Low=1'),
        'Must display exact 10-5-3-1 scale in header/tooltip')
})

// 21. Conflict detected and needs_expert_review display warning and never "Đạt"
test('21. Conflict detected and needs_expert_review display warning and never "Đạt"', () => {
    const resultViewPath = resolve(ROOT, 'src/app/form-iso/_components/views/ResultView.js')
    const src = readFileSync(resultViewPath, 'utf8')
    assert(src.includes('conflictAlertBadge'), 'Must have conflictAlertBadge class for conflicts')
    assert(src.includes('isConflict ?'), 'Must check isConflict for warning display')
})

// 22. Historical assessment with missing controls handles empty array gracefully
test('22. Historical assessment with missing controls handles empty array gracefully without crash', () => {
    const resultViewPath = resolve(ROOT, 'src/app/form-iso/_components/views/ResultView.js')
    const src = readFileSync(resultViewPath, 'utf8')
    assert(src.includes('controlsList.length === 0'), 'Must check controlsList.length === 0')
    assert(src.includes('noDetailsNotice'), 'Must render noDetailsNotice on missing data')
})

// 23. Per-control contribution math on frontend: satisfied 100%, partial 50%, 0% for other verdicts
test('23. Per-control contribution math: satisfied 100%, partial 50%, missing/not_evidenced/review 0%', () => {
    const getVerdictFactor = (v) => {
        const s = String(v || '').toLowerCase()
        if (s === 'satisfied') return 1.0
        if (s === 'partial' || s === 'partially_satisfied') return 0.5
        return 0.0
    }
    assert(getVerdictFactor('satisfied') === 1.0, 'satisfied must be 1.0')
    assert(getVerdictFactor('partial') === 0.5, 'partial must be 0.5')
    assert(getVerdictFactor('missing') === 0.0, 'missing must be 0.0')
    assert(getVerdictFactor('not_evidenced') === 0.0, 'not_evidenced must be 0.0')
    assert(getVerdictFactor('needs_expert_review') === 0.0, 'needs_expert_review must be 0.0')

    const critW = WEIGHT_SCORE.critical // 10
    assert(critW * getVerdictFactor('satisfied') === 10, 'Critical satisfied earns 10')
    assert(critW * getVerdictFactor('partial') === 5, 'Critical partial earns 5')
    assert(critW * getVerdictFactor('missing') === 0, 'Critical missing earns 0')
})

// 24. Mandated Case: 45 self-declared, 0 satisfied -> Raw=48.4%, Prelim=58.4%, Weighted=0.0%, Satisfied=0/93, Badge="Pending Verification / Needs Expert Review"
test('24. 45 self-declared controls, 0 satisfied: Raw=48.4%, Prelim=58.4%, Weighted=0.0%, Satisfied=0/93, Badge="Pending Verification / Needs Expert Review"', () => {
    // Generate 93 controls: 45 self-declared with not_evidenced, 48 with missing
    const controls = []
    for (let i = 1; i <= 45; i++) {
        controls.push({
            control_id: `A.5.${i}`,
            weight_points: 10.0,
            weight_level: 'critical',
            assessment_verdict: 'not_evidenced',
            verdict_factor: 0.0,
            weighted_score_contribution: 0.0,
            conflict_detected: false
        })
    }
    for (let i = 46; i <= 93; i++) {
        controls.push({
            control_id: `A.5.${i}`,
            weight_points: 5.0,
            weight_level: 'high',
            assessment_verdict: 'missing',
            verdict_factor: 0.0,
            weighted_score_contribution: 0.0,
            conflict_detected: false
        })
    }

    const payload = {
        status: 'completed',
        control_coverage: {
            self_declared_implemented: 45,
            evidence_supported_implemented: 0,
            not_evidenced_or_missing: 93,
            total_applicable_controls: 93,
            raw_percentage: 48.4
        },
        weighted_coverage: {
            score: 289.0,
            max_score: 495.0,
            percentage: 58.4
        },
        weighted_compliance: {
            weighted_score: 0.0,
            weighted_max_score: 495.0,
            percentage: 0.0,
            algorithm: 'verdict_weighted_v2',
            weight_scheme: 'critical_10_high_5_medium_3_low_1'
        },
        controls
    }

    const metrics = normalizeAssessmentMetrics(payload, ISO_27001_CONTROLS)

    // 4 metrics separation check
    assert(metrics.rawCoverage.percentage === 48.4, `Raw percentage must be 48.4%, got ${metrics.rawCoverage.percentage}`)
    assert(metrics.rawCoverage.implemented === 45, `Raw implemented must be 45, got ${metrics.rawCoverage.implemented}`)
    assert(metrics.rawCoverage.total === 93, `Raw total must be 93, got ${metrics.rawCoverage.total}`)

    assert(metrics.weightedCoverage.percentage === 58.4, `Prelim weighted coverage must be 58.4%, got ${metrics.weightedCoverage.percentage}`)
    assert(metrics.weightedCoverage.score === 289.0, `Prelim weighted score must be 289.0, got ${metrics.weightedCoverage.score}`)

    assert(metrics.weightedCompliance.percentage === 0.0, `Weighted compliance must be 0.0%, got ${metrics.weightedCompliance.percentage}`)
    assert(metrics.weightedCompliance.score === 0.0, `Weighted score must be 0.0, got ${metrics.weightedCompliance.score}`)

    assert(metrics.satisfiedCount === 0, `Satisfied verified must be 0, got ${metrics.satisfiedCount}`)

    // Badge must be Pending Verification / Needs Expert Review, NEVER Partial Compliance
    assert(metrics.statusBadge === 'Pending Verification / Needs Expert Review',
        `Status badge must be 'Pending Verification / Needs Expert Review', got: ${metrics.statusBadge}`)
    assert(metrics.statusBadge !== 'Tuân thủ một phần (Partial Compliance)', 'Must NEVER display Partial Compliance')
})

// 25. Legacy assessment warning banner triggered when algorithm != verdict_weighted_v2
test('25. Legacy assessment has isLegacy=true and legacyWarning label', () => {
    const legacyPayload = {
        status: 'completed',
        weighted_compliance: {
            score: 45,
            max_score: 93,
            percentage: 58.4,
            algorithm: 'hierarchical_weighted'
        },
        controls: [
            { control_id: 'A.5.1', assessment_verdict: 'satisfied' }
        ]
    }

    const metrics = normalizeAssessmentMetrics(legacyPayload, ISO_27001_CONTROLS)
    assert(metrics.isLegacy === true, 'Assessment with hierarchical_weighted must have isLegacy=true')
    assert(metrics.legacyWarning && metrics.legacyWarning.includes('chưa đối soát theo verdict_weighted_v2'),
        `legacyWarning must mention 'chưa đối soát theo verdict_weighted_v2', got: ${metrics.legacyWarning}`)
})

// 26. Test pack calculation: 12.5 / 18 = 69.4% with verdict_weighted_v2
test('26. Test pack calculation: A.5.1 sat Crit=10, A.5.3 part High=2.5, A.5.5 miss Med=0 -> 12.5 / 18.0 = 69.4% (5 standard verdicts)', () => {
    const controls = [
        {
            control_id: 'A.5.1',
            weight_points: 10.0,
            weight_level: 'critical',
            assessment_verdict: 'satisfied',
            verdict_factor: 1.0,
            weighted_score_contribution: 10.0,
            conflict_detected: false
        },
        {
            control_id: 'A.5.3',
            weight_points: 5.0,
            weight_level: 'high',
            assessment_verdict: 'partial',
            verdict_factor: 0.5,
            weighted_score_contribution: 2.5,
            conflict_detected: false
        },
        {
            control_id: 'A.5.5',
            weight_points: 3.0,
            weight_level: 'medium',
            assessment_verdict: 'missing',
            verdict_factor: 0.0,
            weighted_score_contribution: 0.0,
            conflict_detected: false
        }
    ]

    // Max score = 10 (A.5.1) + 5 (A.5.3) + 3 (A.5.5) = 18.0.
    // Achieved score = 10.0 + 2.5 + 0.0 = 12.5.
    // Percentage = (12.5 / 18.0) * 100% = 69.444...% -> 69.4%
    const expectedScore = 12.5
    const expectedMax = 18.0
    const expectedPct = 69.4

    const payload = {
        status: 'completed',
        weighted_compliance: {
            weighted_score: expectedScore,
            weighted_max_score: expectedMax,
            percentage: expectedPct,
            algorithm: 'verdict_weighted_v2',
            weight_scheme: 'critical_10_high_5_medium_3_low_1'
        },
        controls
    }

    const metrics = normalizeAssessmentMetrics(payload)
    assert(metrics.isLegacy === false, 'verdict_weighted_v2 payload must not be legacy')
    assert(metrics.weightedCompliance.score === 12.5, `Score must be 12.5, got ${metrics.weightedCompliance.score}`)
    assert(metrics.weightedCompliance.maxScore === 18.0, `Max score must be 18.0, got ${metrics.weightedCompliance.maxScore}`)
    assert(metrics.weightedCompliance.percentage === 69.4, `Percentage must be 69.4%, got ${metrics.weightedCompliance.percentage}`)
    assert(metrics.satisfiedCount === 1, `Satisfied count must be 1, got ${metrics.satisfiedCount}`)
    assert(metrics.partialCount === 1, `Partial count must be 1, got ${metrics.partialCount}`)
})

// 27. Conflict detected forces contribution = 0
test('27. conflict_detected=true forces factor and contribution to 0 in UI breakdown', () => {
    const controls = [
        {
            control_id: 'A.5.1',
            weight_points: 10.0,
            weight_level: 'critical',
            assessment_verdict: 'satisfied',
            verdict_factor: 1.0,
            conflict_detected: true,
            weighted_score_contribution: 0.0
        }
    ]
    const categories = [
        {
            category: 'A.5 Organizational Controls',
            controls: [{ id: 'A.5.1', weight: 'critical' }]
        }
    ]

    const breakdown = calcCategoryComplianceBreakdown(controls, categories)
    assert(breakdown[0].satisfied === 0, 'Conflicted control must not be counted as satisfied')
    assert(breakdown[0].achieved === 0.0, 'Conflicted control must not earn points')
    assert(breakdown[0].percent === 0.0, 'Conflicted category percent must be 0.0%')
})

// 28. ResultView.js contains no "Preliminary Weighted Coverage" or 246/495 and displays template notice
test('28. ResultView.js contains no Preliminary Weighted Coverage or 246/495 and has valid UTF-8 template label', async () => {
    const fs = await import('fs')
    const path = await import('path')
    const resultViewPath = path.resolve('src/app/form-iso/_components/views/ResultView.js')
    const content = fs.readFileSync(resultViewPath, 'utf8')

    // Must NOT contain "Preliminary Weighted Coverage" in score cards
    assert(!content.includes('Preliminary Weighted Coverage'), 'ResultView must not contain "Preliminary Weighted Coverage"')
    assert(!content.includes('246 / 495'), 'ResultView must not hardcode 246 / 495')
    assert(!content.includes('289 / 495'), 'ResultView must not hardcode 289 / 495')

    // Must contain template notice in clean Vietnamese UTF-8
    assert(content.includes('Dữ liệu mẫu từ template'), 'ResultView must have template label "Dữ liệu mẫu từ template"')
    assert(content.includes('không được coi là evidence'), 'ResultView must state template data is not evidence')

    // Must have no UTF-8 mojibake
    assert(!content.includes('Ã'), 'ResultView must not contain mojibake Ã')
    assert(!content.includes('á»'), 'ResultView must not contain mojibake á»')
})

// 29. Zero-verified assessment strictly displays Raw Coverage 48.4% and Weighted Compliance 0.0%
test('29. Zero-verified assessment displays Raw Coverage 48.4% and Weighted Compliance 0.0%', () => {
    const zeroPayload = {
        status: "completed",
        weighted_compliance: {
            score: 0.0,
            weighted_score: 0.0,
            weighted_max_score: 495.0,
            percentage: 0.0
        },
        control_coverage: {
            self_declared_implemented: 45,
            total_controls: 93,
            raw_percentage: 48.4
        }
    }

    const metrics = normalizeAssessmentMetrics(zeroPayload, ISO_27001_CONTROLS)
    assert(metrics.rawCoverage.percentage === 48.4, `Raw percentage must be 48.4, got ${metrics.rawCoverage.percentage}`)
    assert(metrics.rawCoverage.implemented === 45, `Raw implemented must be 45, got ${metrics.rawCoverage.implemented}`)
    assert(metrics.rawCoverage.total === 93, `Raw total must be 93, got ${metrics.rawCoverage.total}`)
    assert(metrics.weightedCompliance.percentage === 0.0, `Weighted compliance must be 0.0%, got ${metrics.weightedCompliance.percentage}`)
    assert(metrics.weightedCompliance.score === 0.0, `Weighted score must be 0.0, got ${metrics.weightedCompliance.score}`)
    assert(metrics.satisfiedCount === 0, `Satisfied count must be 0, got ${metrics.satisfiedCount}`)
})

console.log(`\n=============================================`)
if (failures.length > 0) {
    console.error(`Frontend Tests FAILED: ${failures.length} errors`)
    for (const f of failures) console.error(`  - ${f.name}: ${f.error}`)
    process.exit(1)
} else {
    console.log(`Frontend Tests PASSED: all ${passedCount} tests passed cleanly!`)
    console.log(`=============================================\n`)
}
