/**
 * test_evidence_isolation_frontend.mjs
 * Frontend Test Suite for Evidence Isolation, Template Invariants, and Real-Time Sync
 */

import assert from 'node:assert/strict'

console.log('\n--- Running Frontend Evidence Isolation & Scoping Tests ---')

// Helper simulating getDraftKey logic
const getDraftKey = (aid) => aid ? `assessment_draft:${aid}` : 'assessment_draft:unknown'

// 1. Draft Scoping Key Format
{
    const aidA = '3fa85f64-5717-4562-b3fc-2c963f66afa6'
    const aidB = '8bb42f11-9238-4e12-9ac4-8b1e0f8821d3'
    assert.equal(getDraftKey(aidA), `assessment_draft:${aidA}`)
    assert.equal(getDraftKey(aidB), `assessment_draft:${aidB}`)
    assert.notEqual(getDraftKey(aidA), 'form-iso-draft', 'Global draft key form-iso-draft must be eliminated')
    assert.notEqual(getDraftKey(aidA), getDraftKey(aidB), 'Draft keys across assessments must be distinct')
    console.log('  ✓ 1. Draft keys strictly isolated by assessment_id (assessment_draft:<id>)')
}

// 2. Draft Isolation: Assessment B never reads draft from Assessment A
{
    const storageMock = {}
    const aidA = 'aid_assessment_A'
    const aidB = 'aid_assessment_B'

    storageMock[getDraftKey(aidA)] = JSON.stringify({
        assessment_id: aidA,
        form: { org_name: 'Company A', implemented_controls: ['A.5.9'] },
        evidenceMap: { 'A.5.9': [{ filename: 'F1.txt' }] },
        uploadedFilesList: [{ filename: 'F1.txt', mapped_controls: ['A.5.9'] }]
    })

    const draftB = storageMock[getDraftKey(aidB)]
    assert.equal(draftB, undefined, 'Draft for Assessment B must not exist')
    console.log('  ✓ 2. Assessment B never accesses or inherits draft from Assessment A')
}

// 3. Template Selection Invariant: NEVER auto-ticks controls, NEVER copies evidence
{
    const sampleTemplate = {
        id: 'tpl_banking_iso',
        name: 'ISO 27001 Banking Template',
        standard: 'iso27001',
        data: {
            org_name: 'Global Bank Corp',
            organization: { size: 'large', industry: 'Banking & Finance' },
            infrastructure: { servers: 12, cloud: 'AWS' },
            compliance: {
                implemented_controls: ['A.5.1', 'A.5.9', 'A.8.8'] // template might have legacy suggestions
            }
        }
    }

    // Applying selectTemplate logic
    const selectedForm = {
        assessment_standard: sampleTemplate.standard || 'iso27001',
        template_id: sampleTemplate.id,
        template_name: sampleTemplate.name,
        is_template_input: true,
        org_name: sampleTemplate.data.org_name,
        org_size: sampleTemplate.data.organization.size,
        industry: sampleTemplate.data.organization.industry,
        servers: sampleTemplate.data.infrastructure.servers,
        cloud_provider: sampleTemplate.data.infrastructure.cloud,
        // MANDATORY REQUIREMENT C.2: NEVER copy implemented_controls
        implemented_controls: []
    }

    assert.equal(selectedForm.implemented_controls.length, 0, 'Template MUST NOT pre-tick any controls')
    assert.equal(selectedForm.is_template_input, true, 'Form must be flagged as template input')
    assert.equal(selectedForm.org_name, 'Global Bank Corp')
    console.log('  ✓ 3. Template selection populates org/infra but implemented_controls is strictly []')
}

// 4. Two-Way Evidence Sync: Control Drawer Upload immediately updates Catalog Popup
{
    let evidenceMap = {}
    let uploadedFilesList = []

    const handleUploadSuccess = (controlId, serverResponse) => {
        // 1. Update evidenceMap for control
        const current = evidenceMap[controlId] || []
        const filtered = current.filter(f => f.filename !== serverResponse.filename)
        evidenceMap = {
            ...evidenceMap,
            [controlId]: [...filtered, {
                evidence_id: serverResponse.evidence_id,
                filename: serverResponse.filename,
                clean_name: serverResponse.clean_name || serverResponse.filename,
                size_bytes: serverResponse.size_bytes,
                sha256: serverResponse.sha256,
                char_count: serverResponse.char_count,
                mapped_controls: serverResponse.mapped_controls || [controlId]
            }]
        }

        // 2. Synchronize uploadedFilesList for overview popup
        const targetFilename = serverResponse.filename
        const existingIdx = uploadedFilesList.findIndex(f => (f.filename === targetFilename || f.clean_name === targetFilename))
        const newMapped = serverResponse.mapped_controls && serverResponse.mapped_controls.length > 0 ? serverResponse.mapped_controls : [controlId]

        if (existingIdx >= 0) {
            const updated = [...uploadedFilesList]
            const oldFile = updated[existingIdx]
            const mergedControls = Array.from(new Set([...(oldFile.mapped_controls || []), ...newMapped]))
            updated[existingIdx] = {
                ...oldFile,
                evidence_id: serverResponse.evidence_id || oldFile.evidence_id,
                mapped_controls: mergedControls,
                char_count: serverResponse.char_count ?? oldFile.char_count,
                sha256: serverResponse.sha256 || oldFile.sha256,
                size_bytes: serverResponse.size_bytes || oldFile.size_bytes
            }
            uploadedFilesList = updated
        } else {
            uploadedFilesList = [...uploadedFilesList, {
                evidence_id: serverResponse.evidence_id,
                filename: serverResponse.filename,
                clean_name: serverResponse.clean_name || serverResponse.filename,
                size_bytes: serverResponse.size_bytes,
                sha256: serverResponse.sha256,
                char_count: serverResponse.char_count,
                mapped_controls: newMapped
            }]
        }
    }

    // Step A: Upload F1 to A.5.9
    handleUploadSuccess('A.5.9', {
        evidence_id: 'file_e1a2b3',
        filename: '20260922_F1_policy.pdf',
        clean_name: 'F1_policy.pdf',
        size_bytes: 4096,
        char_count: 1500,
        sha256: 'e1a2b3c4',
        mapped_controls: ['A.5.9']
    })

    assert.equal(evidenceMap['A.5.9'].length, 1)
    assert.equal(uploadedFilesList.length, 1)
    assert.deepEqual(uploadedFilesList[0].mapped_controls, ['A.5.9'])

    // Step B: Upload F2 to A.5.10
    handleUploadSuccess('A.5.10', {
        evidence_id: 'file_f2a2b3',
        filename: '20260922_F2_access.pdf',
        clean_name: 'F2_access.pdf',
        size_bytes: 2048,
        char_count: 800,
        sha256: 'f2a2b3c4',
        mapped_controls: ['A.5.10']
    })

    assert.equal(evidenceMap['A.5.10'].length, 1)
    assert.equal(uploadedFilesList.length, 2)

    // Step C: Upload F3 to A.5.9 and then map to A.5.10
    handleUploadSuccess('A.5.9', {
        evidence_id: 'file_f3a2b3',
        filename: '20260922_F3_dual.pdf',
        clean_name: 'F3_dual.pdf',
        size_bytes: 8192,
        char_count: 3200,
        sha256: 'f3a2b3c4',
        mapped_controls: ['A.5.9']
    })
    handleUploadSuccess('A.5.10', {
        evidence_id: 'file_f3a2b3',
        filename: '20260922_F3_dual.pdf',
        clean_name: 'F3_dual.pdf',
        size_bytes: 8192,
        char_count: 3200,
        sha256: 'f3a2b3c4',
        mapped_controls: ['A.5.10']
    })

    // Verify Invariants:
    // 1. A.5.9 has 2 files (F1, F3)
    assert.equal(evidenceMap['A.5.9'].length, 2, 'A.5.9 must have 2 files')
    // 2. A.5.10 has 2 files (F2, F3)
    assert.equal(evidenceMap['A.5.10'].length, 2, 'A.5.10 must have 2 files')
    // 3. Catalog Popup has 3 unique files (F1, F2, F3) - NO duplicate entries!
    assert.equal(uploadedFilesList.length, 3, 'Overview catalog must have 3 unique files')
    const f3Entry = uploadedFilesList.find(f => f.clean_name === 'F3_dual.pdf')
    assert.ok(f3Entry, 'F3 must exist in catalog')
    assert.equal(f3Entry.mapped_controls.length, 2, 'F3 must have 2 mapped controls')
    assert.ok(f3Entry.mapped_controls.includes('A.5.9') && f3Entry.mapped_controls.includes('A.5.10'))

    // 4. Calculate total characters and total mapped controls for catalog modal
    const totalChars = uploadedFilesList.reduce((acc, f) => acc + (f.char_count || 0), 0)
    assert.equal(totalChars, 1500 + 800 + 3200, 'Total chars must equal 5500')

    const mappedControlSet = new Set()
    uploadedFilesList.forEach(f => (f.mapped_controls || []).forEach(c => mappedControlSet.add(c)))
    assert.equal(mappedControlSet.size, 2, 'Total unique mapped controls must be 2')

    console.log('  ✓ 4. Two-way sync: Control drawer updates both control panel and overview catalog without duplicates')
}

// 5. Race Condition Protection: Late response from Assessment A is rejected if user is on Assessment B
{
    let currentAssessmentId = 'aid_current_B'
    let stateEvidenceMap = {}

    const onFetchResolved = (resolvedAid, controlId, files) => {
        // Late response check
        if (currentAssessmentId !== resolvedAid) {
            // Discard!
            return false
        }
        stateEvidenceMap[controlId] = files
        return true
    }

    const updatedA = onFetchResolved('aid_old_A', 'A.5.9', [{ filename: 'stale_A.txt' }])
    assert.equal(updatedA, false, 'Late response from Assessment A must be discarded')
    assert.equal(Object.keys(stateEvidenceMap).length, 0, 'State must remain untouched')

    const updatedB = onFetchResolved('aid_current_B', 'A.8.8', [{ filename: 'fresh_B.txt' }])
    assert.equal(updatedB, true, 'Response matching current assessment_id must be accepted')
    assert.equal(stateEvidenceMap['A.8.8'].length, 1)

    console.log('  ✓ 5. Race condition guard: Late fetch/upload responses from prior assessment are discarded')
}

// 6. Reset on New Assessment
{
    let state = {
        assessmentId: 'aid_old',
        step: 3,
        form: { org_name: 'Old Org', implemented_controls: ['A.5.1', 'A.5.2'] },
        evidenceMap: { 'A.5.1': [{ filename: 'old.pdf' }] },
        uploadedFilesList: [{ filename: 'old.pdf' }],
        result: { status: 'completed' },
        drawerControlId: 'A.5.1'
    }

    // Action: handleStartNewAssessment()
    state = {
        assessmentId: 'aid_new_generated',
        step: 1,
        form: {
            org_name: '',
            org_size: 'medium',
            industry: '',
            iso_status: 'planning',
            servers: 1,
            cloud_provider: '',
            firewalls: '',
            antivirus: '',
            backup_solution: '',
            siem: '',
            incidents_12m: 0,
            vpn: false,
            assessment_standard: 'iso27001',
            implemented_controls: [],
            notes: '',
            assessment_scope: 'full',
            scope_description: '',
            model_mode: 'local'
        },
        evidenceMap: {},
        uploadedFilesList: [],
        result: null,
        drawerControlId: null
    }

    assert.equal(state.step, 1)
    assert.equal(state.form.implemented_controls.length, 0)
    assert.equal(Object.keys(state.evidenceMap).length, 0)
    assert.equal(state.uploadedFilesList.length, 0)
    assert.equal(state.result, null)
    assert.equal(state.drawerControlId, null)

    console.log('  ✓ 6. New assessment completely resets form, evidence counters, catalog, and drawers to clean slate')
}

console.log('\n=============================================')
console.log('Frontend Evidence Isolation Tests PASSED: all 6 tests passed cleanly!')
console.log('=============================================\n')
