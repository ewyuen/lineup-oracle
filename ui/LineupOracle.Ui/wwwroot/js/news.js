// Keeps the ticker small: a finished item removes itself, and the list never holds more than 50 items.
document.body.addEventListener("animationend", (event) => {
    if (event.target.classList.contains("news-item")) event.target.remove();
});
document.body.addEventListener("htmx:afterSwap", () => {
    const track = document.getElementById("news-track");
    while (track && track.children.length > 50) track.firstElementChild.remove();
});
