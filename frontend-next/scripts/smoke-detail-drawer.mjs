#!/usr/bin/env node
// Lightweight smoke test for DetailDrawer: verifies a11y attributes + i18n keys exist in source and en.json. Run: node frontend-next/scripts/smoke-detail-drawer.mjs

import { readFileSync, existsSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)
const ROOT = resolve(__dirname, '..')

const failures = []

function assert(cond, msg) {
    if (!cond) failures.push(msg)
}

// 1) Source file checks ------------------------------------------------------
const drawerPath = resolve(ROOT, 'src/app/form-iso/_components/DetailDrawer.js')
assert(existsSync(drawerPath), `DetailDrawer.js not found at ${drawerPath}`)

const src = readFileSync(drawerPath, 'utf8')

assert(/export default function DetailDrawer/.test(src),
    'DetailDrawer.js must export default function DetailDrawer')

assert(/role="dialog"/.test(src), 'DetailDrawer must set role="dialog"')
assert(/aria-modal="true"/.test(src), 'DetailDrawer must set aria-modal="true"')

// Three tab keys
for (const key of ['formIso.tab.criteria', 'formIso.tab.evidence', 'formIso.tab.ai']) {
    // The component composes the key as `formIso.tab.${id}` — assert the
    // template fragment + each individual id literal in the tabs array.
    // Cheap regex: just check the dotted string appears in some form.
    const camelTail = key.split('.').pop()
    assert(
        src.includes(camelTail),
        `DetailDrawer source must reference tab id "${camelTail}" (key ${key})`
    )
}
assert(/formIso\.tab\.\$\{id\}|formIso\.tab\./.test(
    src.replace(/`/g, '`')
), 'DetailDrawer must use the formIso.tab.<id> i18n template for tab labels')

// Esc handler + onClose
assert(/Escape/.test(src), 'DetailDrawer must handle the Escape key')
assert(/onClose/.test(src), 'DetailDrawer must call onClose')

// Mandatory-evidence gate (Step 5/6 contract)
assert(/evidenceFiles\.length\s*<\s*1/.test(src),
    'DetailDrawer footer toggle must enforce evidenceFiles.length < 1 gate')

// 2) i18n catalog checks -----------------------------------------------------
const enPath = resolve(ROOT, 'src/i18n/en.json')
assert(existsSync(enPath), `en.json not found at ${enPath}`)

const en = JSON.parse(readFileSync(enPath, 'utf8'))
const formIso = en.formIso || {}
const tab = formIso.tab || {}
for (const id of ['criteria', 'evidence', 'ai']) {
    assert(typeof tab[id] === 'string' && tab[id].length > 0,
        `en.json missing formIso.tab.${id}`)
}
assert(typeof formIso.evidenceRequiredHint === 'string',
    'en.json missing formIso.evidenceRequiredHint')
assert(typeof formIso.drawerTabs === 'string',
    'en.json missing formIso.drawerTabs (aria-label for tablist)')

// ---------------------------------------------------------------------------
if (failures.length > 0) {
    console.error('DetailDrawer smoke FAILED:')
    for (const f of failures) console.error('  - ' + f)
    process.exit(1)
}
console.log('DetailDrawer smoke OK — all assertions passed.')
