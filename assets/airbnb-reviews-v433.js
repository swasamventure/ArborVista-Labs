(() => {
  'use strict';

  const section = document.querySelector('[data-airbnb-reviews-section]');
  if (!section) return;

  const setText = (selector, value) => {
    const node = section.querySelector(selector);
    if (node && value !== undefined && value !== null) node.textContent = String(value);
  };

  const formatDate = iso => {
    const date = new Date(iso);
    if (Number.isNaN(date.getTime())) return '';
    return new Intl.DateTimeFormat('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    }).format(date);
  };

  fetch('data/airbnb-reviews.json?v=4.3.3-final-verified-reviews', {
    cache: 'no-store',
    headers: { 'Accept': 'application/json' }
  })
    .then(response => {
      if (!response.ok) throw new Error(`Airbnb review snapshot HTTP ${response.status}`);
      return response.json();
    })
    .then(data => {
      setText('[data-airbnb-rating]', Number(data.rating).toFixed(2));
      setText('[data-airbnb-review-count]', data.reviewCount);
      setText('[data-airbnb-guest-favorite]', data.guestFavorite ? 'Guest favorite' : 'Airbnb guest rating');
      setText('[data-airbnb-five-star]', `${data.fiveStarPercent}%`);

      const categories = data.categoryRatings || {};
      setText('[data-airbnb-communication]', Number(categories.communication).toFixed(1));
      setText('[data-airbnb-cleanliness]', Number(categories.cleanliness).toFixed(1));
      setText('[data-airbnb-accuracy]', Number(categories.accuracy).toFixed(1));
      setText('[data-airbnb-checkin]', Number(categories.checkIn).toFixed(1));

      const featured = Array.isArray(data.featuredReviews) ? data.featuredReviews[0] : null;
      if (featured) {
        setText('[data-airbnb-featured-review]', `“${featured.excerpt}”`);
        setText('[data-airbnb-featured-label]', featured.sourceLabel || 'Verified Airbnb guest excerpt');
      }

      const themes = section.querySelector('[data-airbnb-review-themes]');
      if (themes && Array.isArray(data.reviewThemes)) {
        themes.replaceChildren(...data.reviewThemes.slice(0, 5).map(theme => {
          const tag = document.createElement('span');
          tag.textContent = theme.label;
          tag.title = `${theme.mentions} Airbnb review mentions`;
          return tag;
        }));
      }

      const dateNode = section.querySelector('[data-airbnb-last-checked]');
      if (dateNode && data.lastCheckedAt) {
        dateNode.dateTime = data.lastCheckedAt;
        dateNode.textContent = formatDate(data.lastCheckedAt);
      }

      const link = section.querySelector('[data-airbnb-reviews-link]');
      if (link && data.sourceUrl) link.href = data.sourceUrl;

      section.dataset.reviewSnapshotLoaded = 'true';
    })
    .catch(error => {
      // Preserve server-rendered fallback content when the local JSON cannot be loaded.
      section.dataset.reviewSnapshotLoaded = 'fallback';
      console.warn('Using embedded Airbnb review fallback:', error.message);
    });
})();
