// Google Analytics Custom Events
class AnalyticsTracker {
    constructor() {
        this.trackingId = 'G-4C23MR10FW'; // Your Measurement ID
        this.isInitialized = false;
        this.init();
    }

    init() {
        if (typeof gtag !== 'undefined') {
            this.isInitialized = true;
            console.log('Analytics initialized');
            
            // Track page view
            this.trackPageView();
            
            // Set up event listeners
            this.setupEventTracking();
        }
    }

    trackPageView() {
        if (this.isInitialized) {
            const pagePath = window.location.pathname;
            gtag('event', 'page_view', {
                page_title: document.title,
                page_location: window.location.href,
                page_path: pagePath
            });
            
            // Send to your own database too
            this.sendToServer({
                event: 'page_view',
                path: pagePath,
                title: document.title
            });
        }
    }

    trackEvent(eventName, eventData = {}) {
        if (this.isInitialized) {
            gtag('event', eventName, eventData);
            
            // Send to your own database
            this.sendToServer({
                event: eventName,
                ...eventData,
                timestamp: new Date().toISOString()
            });
        }
    }

    trackBlogPostView(postId, postTitle) {
        this.trackEvent('view_post', {
            post_id: postId,
            post_title: postTitle,
            engagement_time_msec: 1000
        });
    }

    trackSearch(query, resultsCount) {
        this.trackEvent('search', {
            search_term: query,
            results_count: resultsCount
        });
    }

    trackAdClick(adId, adPosition) {
        this.trackEvent('ad_click', {
            ad_id: adId,
            ad_position: adPosition
        });
    }

    trackUserEngagement(timeSpent) {
        this.trackEvent('user_engagement', {
            engagement_time: timeSpent,
            session_id: this.getSessionId()
        });
    }

    sendToServer(data) {
        // Send to your Flask backend for analytics
        fetch('/api/track-analytics', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
        }).catch(console.error);
    }

    getSessionId() {
        let sessionId = sessionStorage.getItem('analytics_session_id');
        if (!sessionId) {
            sessionId = 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
            sessionStorage.setItem('analytics_session_id', sessionId);
        }
        return sessionId;
    }

    setupEventTracking() {
        // Track outbound links
        document.querySelectorAll('a[href^="http"]').forEach(link => {
            link.addEventListener('click', (e) => {
                if (!link.href.includes(window.location.hostname)) {
                    this.trackEvent('outbound_click', {
                        link_url: link.href,
                        link_text: link.textContent
                    });
                }
            });
        });

        // Track form submissions
        document.querySelectorAll('form').forEach(form => {
            form.addEventListener('submit', (e) => {
                const formId = form.id || 'unknown_form';
                this.trackEvent('form_submit', {
                    form_id: formId,
                    form_name: form.querySelector('[name]')?.name || 'unknown'
                });
            });
        });

        // Track video/article reading time
        let startTime = Date.now();
        window.addEventListener('beforeunload', () => {
            const timeSpent = Date.now() - startTime;
            if (timeSpent > 5000) { // Only track if spent >5 seconds
                this.trackUserEngagement(timeSpent);
            }
        });
    }
}

// Initialize analytics when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.analytics = new AnalyticsTracker();
});

// Make it available globally
window.trackEvent = (eventName, data) => {
    if (window.analytics) {
        window.analytics.trackEvent(eventName, data);
    }
};