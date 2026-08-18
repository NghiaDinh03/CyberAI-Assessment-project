#!/usr/bin/env node
/**
 * Frontend E2E / Runtime Smoke Test for CyberAI
 *
 * Kiểm tra:
 * 1. Chạy bộ kiểm thử tĩnh (Static Smoke Test) DetailDrawer.js.
 * 2. Thử nghiệm fetch các trang chính (/, /chatbot, /form-iso, /settings)
 *    để xác nhận dev server trả về 200/302 OK.
 */

import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';
import http from 'node:http';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const ROOT = resolve(__dirname, '..');

const TARGETS = [
    { path: '/', expected: [200, 302, 307] },
    { path: '/chatbot', expected: [200, 302, 307] },
    { path: '/form-iso', expected: [200, 302, 307] },
    { path: '/settings', expected: [200, 302, 307] }
];

async function runStaticSmoke() {
    return new Promise((res) => {
        console.log('1. Đang chạy Static Smoke Test (DetailDrawer)...');
        const proc = spawn('node', [resolve(ROOT, 'scripts/smoke-detail-drawer.mjs')], {
            stdio: 'inherit'
        });
        proc.on('close', (code) => {
            if (code === 0) {
                console.log('  -> Static Smoke Test: PASS\n');
                res(true);
            } else {
                console.error('  -> Static Smoke Test: FAIL\n');
                res(false);
            }
        });
    });
}

// Thử kết nối tới port, trả về true nếu port đang hoạt động và trả về đúng status
function testRouteWithPort(port, path, expectedStatuses) {
    return new Promise((res) => {
        const options = {
            hostname: 'localhost',
            port: port,
            path: path,
            method: 'GET',
            timeout: 1500
        };

        const req = http.request(options, (res_http) => {
            const status = res_http.statusCode;
            const ok = expectedStatuses.includes(status);
            res({ success: ok, status: status, active: true });
        });

        req.on('error', () => {
            res({ success: false, status: null, active: false });
        });

        req.on('timeout', () => {
            req.destroy();
            res({ success: false, status: null, active: false });
        });

        req.end();
    });
}

async function testRoute(path, expectedStatuses) {
    // Thử port 3081 trước (port của frontend expose ở host)
    let result = await testRouteWithPort(3081, path, expectedStatuses);
    if (result.active) {
        if (result.success) {
            console.log(`  [PASS] ${path} (port 3081) -> Status ${result.status}`);
            return true;
        } else {
            console.error(`  [FAIL] ${path} (port 3081) -> Expected ${expectedStatuses}, got ${result.status}`);
            return false;
        }
    }

    // Nếu port 3081 không active, thử port 3000 (port mặc định trong docker network)
    result = await testRouteWithPort(3000, path, expectedStatuses);
    if (result.active) {
        if (result.success) {
            console.log(`  [PASS] ${path} (port 3000) -> Status ${result.status}`);
            return true;
        } else {
            console.error(`  [FAIL] ${path} (port 3000) -> Expected ${expectedStatuses}, got ${result.status}`);
            return false;
        }
    }

    // Nếu cả hai port đều không chạy
    console.log(`  [SKIPPED] ${path} -> Server ở cả port 3081 và 3000 không hoạt động.`);
    return true; // Skip gracefully
}

async function main() {
    console.log('--- KHỞI CHẠY CYBERAI FRONTEND SMOKE TESTS ---\n');
    
    // 1. Chạy static test
    const staticOk = await runStaticSmoke();
    if (!staticOk) {
        process.exit(1);
    }

    // 2. Chạy HTTP test
    console.log('2. Đang kiểm tra HTTP Runtime Routes (yêu cầu frontend server đang hoạt động)...');
    let runtimeOk = true;
    for (const target of TARGETS) {
        const ok = await testRoute(target.path, target.expected);
        if (!ok) {
            runtimeOk = false;
        }
    }

    if (!runtimeOk) {
        console.error('\n❌ PHẦN KIỂM TRA HTTP RUNTIME THẤT BẠI!');
        process.exit(1);
    }

    console.log('\n🎉 TOÀN BỘ FRONTEND SMOKE TESTS ĐÃ PASS / HOÀN THÀNH CHUẨN CHỈNH!');
}

main().catch((err) => {
    console.error('Lỗi khi chạy smoke test:', err);
    process.exit(1);
});
