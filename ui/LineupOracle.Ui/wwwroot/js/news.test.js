const test = require("node:test");
const assert = require("node:assert");
const { slideMs, startGapMs, trimQueue, nextRelease } = require("./news.js");

const LANE = 800;
const item = (name, extra = {}) => ({ name, isConnected: true, ...extra });

test("slideMs gives the same speed for narrow and wide items", () => {
    for (const width of [100, 640]) {
        const speed = (LANE + width) / (slideMs(width, LANE) / 1000);
        assert.strictEqual(speed, 80);
    }
});

test("a narrow item then a wide item never overlap", () => {
    const narrow = 100, wide = 640;
    const gap = startGapMs(narrow);
    const end = gap + slideMs(wide, LANE);
    // left edge at time t (ms) after an item's start: LANE - 80 * t / 1000
    for (let t = gap; t <= end; t += 50) {
        const narrowRight = LANE - 80 * (t / 1000) + narrow;
        const wideLeft = LANE - 80 * ((t - gap) / 1000);
        assert.ok(wideLeft >= narrowRight - 1e-6, `overlap at ${t}ms`);
    }
});

test("startGapMs floors at 3s and grows for wide items", () => {
    assert.strictEqual(startGapMs(100), 3000);
    assert.ok(startGapMs(640) > 3000);
    assert.strictEqual(startGapMs(640), (640 + 16) / 80 * 1000);
});

test("trimQueue keeps the newest 5 and reports dropped", () => {
    const q = Array.from({ length: 8 }, (_, i) => item(i));
    const { kept, dropped } = trimQueue(q, 5);
    assert.deepStrictEqual(kept.map((i) => i.name), [3, 4, 5, 6, 7]);
    assert.deepStrictEqual(dropped.map((i) => i.name), [0, 1, 2]);
});

test("trimQueue keeps a marker item", () => {
    const q = [item(0, { marker: true }), ...Array.from({ length: 6 }, (_, i) => item(i + 1))];
    const { kept, dropped } = trimQueue(q, 5);
    assert.strictEqual(kept.length, 5);
    assert.ok(kept.some((i) => i.marker));
    assert.deepStrictEqual(dropped.map((i) => i.name), [1, 2]);
});

test("trimQueue leaves an under-cap queue alone", () => {
    const q = [item(1), item(2)];
    const { kept, dropped } = trimQueue(q, 5);
    assert.strictEqual(kept.length, 2);
    assert.strictEqual(dropped.length, 0);
});

test("nextRelease waits before nextStart", () => {
    assert.deepStrictEqual(nextRelease([item(1)], 1000, 4000), { wait: 3000 });
});

test("nextRelease starts the head at or after nextStart", () => {
    const q = [item(1), item(2)];
    assert.strictEqual(nextRelease(q, 4000, 4000).item.name, 1);
    assert.strictEqual(q.length, 1);
    assert.strictEqual(nextRelease(q, 5000, 4000).item.name, 2);
});

test("nextRelease skips disconnected items", () => {
    const q = [item(1, { isConnected: false }), item(2)];
    assert.strictEqual(nextRelease(q, 0, 0).item.name, 2);
});

test("nextRelease handles an empty queue", () => {
    assert.strictEqual(nextRelease([], 0, 0), null);
    assert.strictEqual(nextRelease([item(1, { isConnected: false })], 0, 0), null);
});
