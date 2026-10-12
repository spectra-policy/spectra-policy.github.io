// Control-free, GIF-style loops. Stop offscreen playback and respect reduced motion.
(() => {
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  const videos = document.querySelectorAll('video[data-play-in-view]');
  const visible = new Set();
  const update = video => {
    video.autoplay = !reducedMotion.matches;
    if (reducedMotion.matches || document.hidden || !visible.has(video)) {
      video.pause();
    } else {
      video.play().catch(() => {});
    }
  };
  videos.forEach(video => {
    video.controls = false;
    video.muted = true;
    video.loop = true;
    video.autoplay = !reducedMotion.matches;
    video.pause();
  });
  if ('IntersectionObserver' in window) {
    const observer = new IntersectionObserver(entries => {
      for (const entry of entries) {
        if (entry.isIntersecting) visible.add(entry.target);
        else visible.delete(entry.target);
        update(entry.target);
      }
    }, { threshold: 0.1 });
    videos.forEach(video => observer.observe(video));
  } else {
    videos.forEach(video => { visible.add(video); update(video); });
  }
  reducedMotion.addEventListener('change', () => videos.forEach(update));
  document.addEventListener('visibilitychange', () => videos.forEach(update));
})();
