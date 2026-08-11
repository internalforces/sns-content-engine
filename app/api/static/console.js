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
  const root = document.documentElement;
  let media;

  const revertSetup = (setup) => {
    root.classList.remove("console-motion-ready");
    setup.animations.forEach((animation) => animation.kill());
    setup.triggers.forEach((trigger) => trigger.kill());
    if (setup.elements.length > 0) {
      gsap.set(setup.elements, { clearProps: "transform,zIndex" });
    }
  };

  try {
    gsap.registerPlugin(ScrollTrigger);
    media = gsap.matchMedia();

    media.add(
      "(min-width: 901px) and (prefers-reduced-motion: no-preference)",
      () => {
        const setup = { animations: [], triggers: [], elements: [] };

        try {
          document.querySelectorAll("[data-review-story]").forEach((story) => {
            const heading = story.querySelector("[data-review-pin]");
            const cards = Array.from(story.querySelectorAll("[data-stack-card]"));

            if (!heading || cards.length === 0) return;

            setup.elements.push(heading, ...cards);
            setup.triggers.push(
              ScrollTrigger.create({
                trigger: story,
                endTrigger: cards[cards.length - 1],
                start: "top 5rem",
                end: "bottom 60%",
                pin: heading,
                pinSpacing: false,
              }),
            );

            cards.forEach((card, index) => {
              const animation = gsap.fromTo(
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
              setup.animations.push(animation);
              if (animation.scrollTrigger) {
                setup.triggers.push(animation.scrollTrigger);
              }
            });
          });

          document.querySelectorAll("[data-marquee]").forEach((marquee) => {
            setup.elements.push(marquee);
            setup.animations.push(
              gsap.to(marquee, {
                xPercent: -50,
                duration: 42,
                ease: "none",
                repeat: -1,
              }),
            );
          });

          if (setup.animations.length > 0 || setup.triggers.length > 0) {
            root.classList.add("console-motion-ready");
          }
        } catch (_) {
          revertSetup(setup);
          return undefined;
        }

        return () => revertSetup(setup);
      },
    );
  } catch (_) {
    if (media) {
      media.revert();
    }
    root.classList.remove("console-motion-ready");
  }
})();
