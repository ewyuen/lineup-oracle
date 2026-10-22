// Keeps the ticker small: a finished item removes itself, and the list never holds more than 50 items.
// New items wait offscreen and enter one at a time at one constant speed, so they never overlap.
const SPEED = 80;       // px per second, the same for every item
const MIN_GAP_MS = 3000; // least time between two item starts
const MARGIN = 16;      // px of clear space behind the previous item
const MAX_WAITING = 5;

function slideMs(itemWidth, laneWidth) {
    return (laneWidth + itemWidth) / SPEED * 1000;
}

function startGapMs(previousWidth) {
    return Math.max(MIN_GAP_MS, (previousWidth + MARGIN) / SPEED * 1000);
}

function hasMarker(item) {
    return item.querySelector ? !!item.querySelector(".news-marker") : !!item.marker;
}

// Keeps the newest `max` items; the oldest are dropped first, and a restart marker is never dropped.
function trimQueue(queue, max) {
    const dropped = [];
    let excess = queue.length - max;
    const kept = queue.filter((item) => {
        if (excess > 0 && !hasMarker(item)) {
            excess--;
            dropped.push(item);
            return false;
        }
        return true;
    });
    return { kept, dropped };
}

// Removes items that left the page, then returns {item} to start now, {wait} in ms, or null for an empty queue.
function nextRelease(queue, now, nextStart) {
    while (queue.length > 0 && !queue[0].isConnected) queue.shift();
    if (queue.length === 0) return null;
    if (now < nextStart) return { wait: nextStart - now };
    return { item: queue.shift() };
}

if (typeof module !== "undefined") module.exports = { slideMs, startGapMs, trimQueue, nextRelease };

if (typeof document !== "undefined") {
    document.body.addEventListener("animationend", (event) => {
        if (event.target.classList.contains("news-item")) event.target.remove();
    });
    document.body.addEventListener("htmx:afterSwap", () => {
        const track = document.getElementById("news-track");
        while (track && track.children.length > 50) track.firstElementChild.remove();
    });

    // shortcut: timers are throttled in background tabs, so items may enter in a burst on return; the cap of 5 bounds it.
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)");
    let queue = [];
    let nextStart = 0;
    let timer = null;

    const pump = () => {
        timer = null;
        for (;;) {
            const next = nextRelease(queue, Date.now(), nextStart);
            if (!next) return;
            if (next.wait !== undefined) {
                timer = setTimeout(pump, next.wait);
                return;
            }
            const item = next.item;
            const lane = item.parentElement;
            const width = item.offsetWidth;
            item.style.animationDuration = slideMs(width, lane ? lane.clientWidth : 0) + "ms";
            item.classList.add("news-run");
            nextStart = Date.now() + startGapMs(width);
        }
    };

    const enqueue = (items) => {
        for (const item of items) {
            if (!item.classList.contains("news-run") && !queue.includes(item)) queue.push(item);
        }
        const { kept, dropped } = trimQueue(queue, MAX_WAITING);
        dropped.forEach((item) => item.remove());
        queue = kept;
        if (timer === null) pump();
    };

    const collect = (nodes) => {
        const found = [];
        for (const node of nodes) {
            if (node.nodeType !== 1) continue;
            if (node.classList.contains("news-item")) found.push(node);
            found.push(...node.querySelectorAll(".news-item"));
        }
        return found;
    };

    if (!reduced.matches) {
        new MutationObserver((mutations) => {
            if (reduced.matches) return;
            const found = collect(mutations.flatMap((m) => [...m.addedNodes]));
            if (found.length > 0) enqueue(found);
        }).observe(document.body, { childList: true, subtree: true });
        enqueue([...document.querySelectorAll(".news-item")]);
    }
}
