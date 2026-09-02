import { useEffect, useRef, useState } from 'react';

/**
 * Returns a ref to attach to a container element.
 * Once the element enters the viewport, `inView` becomes true
 * and the ref element gets the `in-view` class added.
 */
export function useScrollAnimation<T extends HTMLElement = HTMLDivElement>(threshold = 0.12) {
  const ref = useRef<T | null>(null);
  const [inView, setInView] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setInView(true);
          el.classList.add('in-view');
          observer.unobserve(el);
        }
      },
      { threshold }
    );

    observer.observe(el);
    return () => observer.disconnect();
  }, [threshold]);

  return { ref, inView };
}

/**
 * Observes multiple child elements inside a container
 * and staggers their `in-view` class addition.
 */
export function useStaggerAnimation<T extends HTMLElement = HTMLDivElement>(
  threshold = 0.1,
  staggerMs = 80,
) {
  const containerRef = useRef<T | null>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const children = Array.from(container.querySelectorAll<HTMLElement>('.stagger-child'));

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          children.forEach((child, i) => {
            setTimeout(() => {
              child.classList.add('in-view');
            }, i * staggerMs);
          });
          observer.unobserve(container);
        }
      },
      { threshold }
    );

    observer.observe(container);
    return () => observer.disconnect();
  }, [threshold, staggerMs]);

  return containerRef;
}
