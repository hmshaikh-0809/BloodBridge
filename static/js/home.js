document.addEventListener("DOMContentLoaded", () => {

    // ---------- SLIDER CODE ----------
    let index = 0;
    const track = document.querySelector('.slider-track');
    const cards = document.querySelectorAll('.horizontal-card');

    window.nextCard = function () {
        index = (index + 1) % cards.length;
        track.style.transform = `translateX(-${index * 100}%)`;
    };

    window.prevCard = function () {
        index = (index - 1 + cards.length) % cards.length;
        track.style.transform = `translateX(-${index * 100}%)`;
    };

    setInterval(nextCard, 5000);

    // ---------- COUNTER CODE  ----------
    const counters = document.querySelectorAll(".counter");
    const statsSection = document.querySelector(".stats-section");

    const startCounter = () => {
        counters.forEach(counter => {
            const target = +counter.dataset.target;
            let current = 0;
            const increment = target / 80;

            const update = () => {
                current += increment;
                if (current < target) {
                    counter.innerText = Math.floor(current);
                    requestAnimationFrame(update);
                } else {
                    counter.innerText = target;
                }
            };
            update();
        });
    };

    const observer = new IntersectionObserver(entries => {
        if (entries[0].isIntersecting) {
            startCounter();
            observer.disconnect(); // run only once
        }
    }, { threshold: 0.3 });

    observer.observe(statsSection);

});
