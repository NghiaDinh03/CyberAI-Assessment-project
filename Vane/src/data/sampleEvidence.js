/**
 * Manifest of sample-evidence assets bundled under
 * `frontend-next/public/sampleEvidence/`. Each entry maps to specific
 * ISO 27001:2022 Annex A controls so the Evidence Library can group
 * them by category.
 *
 * All files are placeholder/demo only — see `public/sampleEvidence/README.md`.
 */
export const SAMPLE_EVIDENCE_BASE = '/sampleEvidence'

export const SAMPLE_EVIDENCE = [
    // ── A.5 Organizational Controls ─────────────────────────────────
    {
        id: 'a5-info-security-policy',
        filename: 'A5-information-security-policy.md',
        path: `${SAMPLE_EVIDENCE_BASE}/A5-information-security-policy.md`,
        mime: 'text/markdown',
        kind: 'document',
        category: 'A.5',
        controls: ['A.5.1', 'A.5.2', 'A.5.3', 'A.5.4', 'A.5.31', 'A.5.36'],
        labelKey: 'sampleEvidence.infoSecPolicy',
        fallbackLabel: 'Information Security Policy (ISMS-POL-001)',
        descriptionKey: 'sampleEvidence.infoSecPolicyDesc',
        fallbackDescription: 'Comprehensive ISMS policy covering classification, access control, incident management, and business continuity. Maps to A.5.1–A.5.4.',
    },
    {
        id: 'a5-access-control-matrix',
        filename: 'A5-access-control-matrix.md',
        path: `${SAMPLE_EVIDENCE_BASE}/A5-access-control-matrix.md`,
        mime: 'text/markdown',
        kind: 'document',
        category: 'A.5',
        controls: ['A.5.15', 'A.5.16', 'A.5.17', 'A.5.18'],
        labelKey: 'sampleEvidence.accessControlMatrix',
        fallbackLabel: 'Access Control Matrix (ISMS-ACM-001)',
        descriptionKey: 'sampleEvidence.accessControlMatrixDesc',
        fallbackDescription: 'Role-based access matrix for ERP, cloud, and network systems with PAM and lifecycle management. Maps to A.5.15–A.5.18.',
    },
    {
        id: 'a5-incident-response-plan',
        filename: 'A5-incident-response-plan.md',
        path: `${SAMPLE_EVIDENCE_BASE}/A5-incident-response-plan.md`,
        mime: 'text/markdown',
        kind: 'document',
        category: 'A.5',
        controls: ['A.5.24', 'A.5.25', 'A.5.26', 'A.5.27', 'A.5.28'],
        labelKey: 'sampleEvidence.incidentResponsePlan',
        fallbackLabel: 'Incident Response Plan (ISMS-IRP-001)',
        descriptionKey: 'sampleEvidence.incidentResponsePlanDesc',
        fallbackDescription: 'Full IRP with classification, response phases, evidence collection, and testing schedule. Maps to A.5.24–A.5.28.',
    },

    // ── A.6 People Controls ─────────────────────────────────────────
    {
        id: 'a6-security-awareness-training',
        filename: 'A6-security-awareness-training.md',
        path: `${SAMPLE_EVIDENCE_BASE}/A6-security-awareness-training.md`,
        mime: 'text/markdown',
        kind: 'document',
        category: 'A.6',
        controls: ['A.6.1', 'A.6.3', 'A.6.8'],
        labelKey: 'sampleEvidence.securityTraining',
        fallbackLabel: 'Security Awareness Training Program (ISMS-TRN-001)',
        descriptionKey: 'sampleEvidence.securityTrainingDesc',
        fallbackDescription: 'Training program with completion records, phishing simulation results, and background screening procedures. Maps to A.6.1, A.6.3, A.6.8.',
    },

    // ── A.7 Physical Controls ───────────────────────────────────────
    {
        id: 'a7-physical-security-assessment',
        filename: 'A7-physical-security-assessment.md',
        path: `${SAMPLE_EVIDENCE_BASE}/A7-physical-security-assessment.md`,
        mime: 'text/markdown',
        kind: 'document',
        category: 'A.7',
        controls: ['A.7.1', 'A.7.2', 'A.7.4', 'A.7.5', 'A.7.7', 'A.7.8'],
        labelKey: 'sampleEvidence.physicalSecurity',
        fallbackLabel: 'Physical Security Assessment Report (ISMS-PHY-001)',
        descriptionKey: 'sampleEvidence.physicalSecurityDesc',
        fallbackDescription: 'Physical access controls, CCTV surveillance, environmental controls, and clean desk audit results. Maps to A.7.1–A.7.14.',
    },

    // ── A.8 Technology Controls ─────────────────────────────────────
    {
        id: 'a8-technology-security-baseline',
        filename: 'A8-technology-security-baseline.md',
        path: `${SAMPLE_EVIDENCE_BASE}/A8-technology-security-baseline.md`,
        mime: 'text/markdown',
        kind: 'document',
        category: 'A.8',
        controls: ['A.8.1', 'A.8.8', 'A.8.9', 'A.8.15', 'A.8.20', 'A.8.24', 'A.8.25'],
        labelKey: 'sampleEvidence.techBaseline',
        fallbackLabel: 'Technology Security Baseline (ISMS-TECH-001)',
        descriptionKey: 'sampleEvidence.techBaselineDesc',
        fallbackDescription: 'Endpoint security, network segmentation, cryptography standards, SDLC security gates, and backup procedures. Maps to A.8.1–A.8.34.',
    },

    // ── Legacy sample files (generic) ───────────────────────────────
    {
        id: 'lorem-policy',
        filename: 'lorem-policy.pdf',
        path: `${SAMPLE_EVIDENCE_BASE}/lorem-policy.pdf`,
        mime: 'application/pdf',
        kind: 'document',
        category: 'generic',
        controls: [],
        labelKey: 'sampleEvidence.loremPolicy',
        fallbackLabel: 'Lorem-ipsum policy (sample PDF)',
        descriptionKey: 'sampleEvidence.loremPolicyDesc',
        fallbackDescription: 'Generic placeholder PDF for testing upload flow.',
    },
    {
        id: 'screenshot-generic-1',
        filename: 'screenshot-generic-1.png',
        path: `${SAMPLE_EVIDENCE_BASE}/screenshot-generic-1.png`,
        mime: 'image/png',
        kind: 'image',
        category: 'generic',
        controls: [],
        labelKey: 'sampleEvidence.screenshot1',
        fallbackLabel: 'Generic screenshot #1 (sample PNG)',
        descriptionKey: 'sampleEvidence.screenshot1Desc',
        fallbackDescription: 'Placeholder screenshot for testing image preview.',
    },
    {
        id: 'screenshot-generic-2',
        filename: 'screenshot-generic-2.png',
        path: `${SAMPLE_EVIDENCE_BASE}/screenshot-generic-2.png`,
        mime: 'image/png',
        kind: 'image',
        category: 'generic',
        controls: [],
        labelKey: 'sampleEvidence.screenshot2',
        fallbackLabel: 'Generic screenshot #2 (sample PNG)',
        descriptionKey: 'sampleEvidence.screenshot2Desc',
        fallbackDescription: 'Placeholder screenshot for testing image preview.',
    },
]

/** Evidence categories for grouping in the Evidence Library UI. */
export const EVIDENCE_CATEGORIES = [
    { id: 'A.5', label: 'A.5 — Organizational Controls', icon: '🏢' },
    { id: 'A.6', label: 'A.6 — People Controls', icon: '👥' },
    { id: 'A.7', label: 'A.7 — Physical Controls', icon: '🏗️' },
    { id: 'A.8', label: 'A.8 — Technology Controls', icon: '💻' },
]

export function getSampleEvidence() {
    return SAMPLE_EVIDENCE
}

/** Get sample evidence filtered by category (e.g. 'A.5'). */
export function getSampleEvidenceByCategory(category) {
    if (!category || category === 'all') return SAMPLE_EVIDENCE.filter(e => e.category !== 'generic')
    return SAMPLE_EVIDENCE.filter(e => e.category === category)
}

/** Get sample evidence that maps to a specific control ID (e.g. 'A.5.1'). */
export function getSampleEvidenceForControl(controlId) {
    return SAMPLE_EVIDENCE.filter(e => e.controls.includes(controlId))
}
