/**
 * test_export_frontend.mjs
 * Frontend Test Suite for Artefact Export Handlers, RFC 5987 Filename Parsing, and Error Feedback
 */

import assert from 'node:assert/strict'

console.log('\n--- Running Frontend Artefact Export Tests ---')

// 1. Filename extraction helper from Content-Disposition header
const getFilenameFromHeader = (header, fallbackName) => {
    if (!header) return fallbackName
    const utf8Match = header.match(/filename\*=UTF-8''([^;]+)/i)
    if (utf8Match && utf8Match[1]) {
        try {
            return decodeURIComponent(utf8Match[1].replace(/['"]/g, ''))
        } catch (e) {}
    }
    const match = header.match(/filename="?([^";]+)"?/i)
    if (match && match[1]) {
        return match[1].trim()
    }
    return fallbackName
}

// Test 1.1: UTF-8 RFC 5987 / RFC 6266 filename decoding
{
    const header = "attachment; filename=\"IT_Audit_Report_163f3f6b_Cong_ty.docx\"; filename*=UTF-8''IT_Audit_Report_163f3f6b_C%C3%B4ng_ty_TNHH_MTV_H%E1%BA%A1_t%E1%BA%A7ng_N%C4%83ng_l%C6%B0%E1%BB%A3ng_An_Ph%C3%BA.docx"
    const parsed = getFilenameFromHeader(header, "default.docx")
    assert.equal(parsed, "IT_Audit_Report_163f3f6b_Công_ty_TNHH_MTV_Hạ_tầng_Năng_lượng_An_Phú.docx")
    console.log('  ✓ 1. Correctly decodes RFC 5987 UTF-8 Vietnamese filename from Content-Disposition')
}

// Test 1.2: Fallback to ASCII filename when UTF-8 parameter absent
{
    const header = 'attachment; filename="Risk_Register_163f3f6b_Report.xlsx"'
    const parsed = getFilenameFromHeader(header, "default.xlsx")
    assert.equal(parsed, "Risk_Register_163f3f6b_Report.xlsx")
    console.log('  ✓ 2. Correctly falls back to standard ASCII filename if filename* is absent')
}

// Test 1.3: Default filename when header missing
{
    const parsed = getFilenameFromHeader(null, "fallback_report.docx")
    assert.equal(parsed, "fallback_report.docx")
    console.log('  ✓ 3. Uses fallback filename when Content-Disposition header is null/undefined')
}

// 2. Export endpoints and assessment ID resolution
const resolveEndpoint = (type, result) => {
    const aid = result?.id || result?.assessment_id || ''
    if (!aid) return null
    switch (type) {
        case 'docx':
            return `/api/iso27001/assessments/${aid}/export-docx`
        case 'risk':
            return `/api/iso27001/assessments/${aid}/export-risk-register`
        case 'pdf':
            return `/api/iso27001/assessments/${aid}/export-pdf`
        case 'soa':
            return '/api/iso27001/soa/export'
        case 'trace':
            return `/api/iso27001/assessments/${aid}/audit-trace`
        default:
            return null
    }
}

// Test 2.1: Endpoint paths with UUID
{
    const res = { id: '163f3f6b-1265-41ac-acab-10f9d7580da5' }
    assert.equal(resolveEndpoint('docx', res), '/api/iso27001/assessments/163f3f6b-1265-41ac-acab-10f9d7580da5/export-docx')
    assert.equal(resolveEndpoint('risk', res), '/api/iso27001/assessments/163f3f6b-1265-41ac-acab-10f9d7580da5/export-risk-register')
    assert.equal(resolveEndpoint('pdf', res), '/api/iso27001/assessments/163f3f6b-1265-41ac-acab-10f9d7580da5/export-pdf')
    assert.equal(resolveEndpoint('soa', res), '/api/iso27001/soa/export')
    assert.equal(resolveEndpoint('trace', res), '/api/iso27001/assessments/163f3f6b-1265-41ac-acab-10f9d7580da5/audit-trace')
    console.log('  ✓ 4. All 5 endpoints resolve exact assessment ID path')
}

// Test 2.2: Endpoint paths with fallback assessment_id property
{
    const res = { assessment_id: '163f3f6b' }
    assert.equal(resolveEndpoint('docx', res), '/api/iso27001/assessments/163f3f6b/export-docx')
    assert.equal(resolveEndpoint('risk', res), '/api/iso27001/assessments/163f3f6b/export-risk-register')
    console.log('  ✓ 5. Handles both result.id and result.assessment_id fallback')
}

// 3. Error Handling and State Simulation
const simulateExport = async (mockResponse, { onShowToast, onSetError }) => {
    if (!mockResponse.ok) {
        let detail = `Lỗi tải file (HTTP ${mockResponse.status})`
        try {
            const errJson = await mockResponse.json()
            detail = errJson.detail || errJson.error || detail
        } catch (e) {
            const text = await mockResponse.text()
            if (text) detail = text.slice(0, 150)
        }
        onSetError(detail)
        onShowToast(detail, 'error')
        return { success: false, error: detail }
    } else {
        const cd = mockResponse.headers.get('content-disposition')
        const filename = getFilenameFromHeader(cd, 'default.bin')
        onShowToast(`Đã tải thành công: ${filename}`, 'success')
        return { success: true, filename }
    }
}

// Test 3.1: 500 error body parsing with detail/error message
{
    let displayedError = null
    let toastType = null
    const mock500 = {
        ok: false,
        status: 500,
        json: async () => ({ error: 'Internal server error', detail: 'Database connection failed' }),
        text: async () => '{"error": "Internal server error"}'
    }

    const res = await simulateExport(mock500, {
        onShowToast: (msg, type) => { toastType = type },
        onSetError: (err) => { displayedError = err }
    })

    assert.equal(res.success, false)
    assert.equal(displayedError, 'Database connection failed')
    assert.equal(toastType, 'error')
    console.log('  ✓ 6. HTTP 500 error extracts detail, updates error banner and triggers error toast')
}

// Test 3.2: 404 error for non-existent assessment
{
    let displayedError = null
    const mock404 = {
        ok: false,
        status: 404,
        json: async () => ({ detail: 'Assessment not found' }),
        text: async () => '{"detail": "Assessment not found"}'
    }

    const res = await simulateExport(mock404, {
        onShowToast: () => {},
        onSetError: (err) => { displayedError = err }
    })

    assert.equal(res.success, false)
    assert.equal(displayedError, 'Assessment not found')
    console.log('  ✓ 7. HTTP 404 error displays structured "Assessment not found" notice')
}

// Test 3.3: 400 error for incomplete assessment
{
    let displayedError = null
    const mock400 = {
        ok: false,
        status: 400,
        json: async () => ({ error: "Assessment not completed yet (current status: 'processing')" }),
        text: async () => '{"error": "Assessment not completed yet"}'
    }

    const res = await simulateExport(mock400, {
        onShowToast: () => {},
        onSetError: (err) => { displayedError = err }
    })

    assert.equal(res.success, false)
    assert.ok(displayedError.includes('not completed yet'))
    console.log('  ✓ 8. HTTP 400 incomplete assessment displays informative status reason')
}

// Test 3.4: 200 Success triggers success toast with decoded filename
{
    let toastMessage = null
    let toastType = null
    const mock200 = {
        ok: true,
        status: 200,
        headers: {
            get: (name) => name.toLowerCase() === 'content-disposition'
                ? "attachment; filename=\"Risk_Register_163f3f6b_An_Phu.xlsx\"; filename*=UTF-8''Risk_Register_163f3f6b_An_Ph%C3%BA.xlsx"
                : null
        }
    }

    const res = await simulateExport(mock200, {
        onShowToast: (msg, type) => { toastMessage = msg; toastType = type },
        onSetError: () => {}
    })

    assert.equal(res.success, true)
    assert.equal(res.filename, 'Risk_Register_163f3f6b_An_Phú.xlsx')
    assert.equal(toastType, 'success')
    assert.ok(toastMessage.includes('Risk_Register_163f3f6b_An_Phú.xlsx'))
    console.log('  ✓ 9. HTTP 200 download decodes filename and triggers success notification')
}

console.log('\n=============================================')
console.log('Frontend Export Tests PASSED: all 9 tests passed cleanly!')
console.log('=============================================\n')
