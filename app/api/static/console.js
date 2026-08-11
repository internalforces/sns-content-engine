(() => {
  "use strict";

  if (typeof window.matchMedia !== "function") return;

  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  if (
    reduceMotion.matches ||
    !window.gsap ||
    !window.ScrollTrigger ||
    typeof window.gsap.registerPlugin !== "function" ||
    typeof window.gsap.matchMedia !== "function"
  ) {
    return;
  }

  const gsap = window.gsap;
  const ScrollTrigger = window.ScrollTrigger;

  try {
    gsap.registerPlugin(ScrollTrigger);
    const media = gsap.matchMedia();

    media.add(
      "(min-width: 901px) and (prefers-reduced-motion: no-preference)",
      () => {
        document.querySelectorAll("[data-review-story]").forEach((story) => {
          const heading = story.querySelector("[data-review-pin]");
          const cards = Array.from(story.querySelectorAll("[data-stack-card]"));

          if (!heading || cards.length === 0) return;

          ScrollTrigger.create({
            trigger: story,
            endTrigger: cards[cards.length - 1],
            start: "top 5rem",
            end: "bottom 60%",
            pin: heading,
            pinSpacing: false,
          });

          cards.forEach((card, index) => {
            gsap.fromTo(
              card,
              { y: 72, scale: 0.96 },
              {
                y: 0,
                scale: 1,
                ease: "none",
                zIndex: index + 1,
                scrollTrigger: {
                  trigger: card,
                  start: "top 88%",
                  end: "top 42%",
                  scrub: 0.6,
                },
              },
            );
          });
        });

        document.querySelectorAll("[data-marquee]").forEach((marquee) => {
          gsap.to(marquee, {
            xPercent: -50,
            duration: 42,
            ease: "none",
            repeat: -1,
          });
        });
      },
    );
  } catch (_) {
    // Motion is optional; the server-rendered document stays usable on failure.
  }
})();
