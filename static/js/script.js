// Main JavaScript file for Paradise of Geeks

// DOM Ready
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

// Initialize all app features
function initializeApp() {
    setupMobileMenu();
    setupAnimations();
    setupTheme();
    setupAnalytics();
    setupBlogFeatures();
}

// Mobile Menu Toggle
function setupMobileMenu() {
    const menuBtn = document.querySelector('.mobile-menu-btn');
    const nav = document.querySelector('.nav-main');
    
    if (menuBtn && nav) {
        menuBtn.addEventListener('click', () => {
            nav.classList.toggle('active');
        });
        
        // Close menu when clicking outside
        document.addEventListener('click', (e) => {
            if (!nav.contains(e.target) && !menuBtn.contains(e.target)) {
                nav.classList.remove('active');
            }
        });
    }
}

// Animations and Effects
function setupAnimations() {
    // Add fade-in animation to elements
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('fade-in');
            }
        });
    }, observerOptions);
    
    // Observe all cards and sections
    document.querySelectorAll('.card, section, .post-card').forEach(el => {
        observer.observe(el);
    });
    
    // Floating particle effect
    const particles = document.querySelectorAll('.bg-particle');
    particles.forEach(particle => {
        const x = Math.random() * 20 - 10;
        const y = Math.random() * 20 - 10;
        particle.style.setProperty('--x', `${x}px`);
        particle.style.setProperty('--y', `${y}px`);
    });
}

// Theme Management (Light/Dark mode ready)
function setupTheme() {
    const themeToggle = document.getElementById('theme-toggle');
    if (themeToggle) {
        themeToggle.addEventListener('click', () => {
            document.body.classList.toggle('light-mode');
            localStorage.setItem('theme', document.body.classList.contains('light-mode') ? 'light' : 'dark');
        });
    }
    
    // Load saved theme
    const savedTheme = localStorage.getItem('theme') || 'dark';
    if (savedTheme === 'light') {
        document.body.classList.add('light-mode');
    }
}

// Analytics Tracking
function setupAnalytics() {
    // Track page views
    trackPageView();
    
    // Track outbound links
    document.querySelectorAll('a[href^="http"]').forEach(link => {
        link.addEventListener('click', (e) => {
            const url = link.getAttribute('href');
            if (!url.includes(window.location.hostname)) {
                trackEvent('outbound_click', { url: url });
            }
        });
    });
}

function trackPageView() {
    const path = window.location.pathname;
    console.log(`[Analytics] Page view: ${path}`);
    
    // Send to your analytics endpoint
    fetch('/api/track-view', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: path })
    }).catch(console.error);
}

function trackEvent(eventName, data = {}) {
    console.log(`[Analytics] Event: ${eventName}`, data);
}

// Blog Features
function setupBlogFeatures() {
    // Search functionality
    const searchInput = document.getElementById('blog-search');
    if (searchInput) {
        searchInput.addEventListener('input', debounce(searchPosts, 300));
    }
    
    // Load more posts
    const loadMoreBtn = document.getElementById('load-more');
    if (loadMoreBtn) {
        loadMoreBtn.addEventListener('click', loadMorePosts);
    }
    
    // Copy code blocks
    document.querySelectorAll('pre code').forEach(block => {
        const copyBtn = document.createElement('button');
        copyBtn.className = 'copy-code-btn';
        copyBtn.innerHTML = '<i class="fas fa-copy"></i>';
        copyBtn.title = 'Copy code';
        
        copyBtn.addEventListener('click', () => {
            navigator.clipboard.writeText(block.textContent).then(() => {
                copyBtn.innerHTML = '<i class="fas fa-check"></i>';
                setTimeout(() => {
                    copyBtn.innerHTML = '<i class="fas fa-copy"></i>';
                }, 2000);
            });
        });
        
        block.parentElement.style.position = 'relative';
        block.parentElement.appendChild(copyBtn);
    });
}

// Search blog posts
async function searchPosts(event) {
    const query = event.target.value.trim().toLowerCase();
    const posts = document.querySelectorAll('.post-card');
    
    if (query.length < 2) {
        posts.forEach(post => post.style.display = 'block');
        return;
    }
    
    try {
        const response = await fetch(`/api/all-posts`);
        const data = await response.json();
        
        posts.forEach(post => {
            const title = post.querySelector('h3').textContent.toLowerCase();
            const content = post.querySelector('p').textContent.toLowerCase();
            const matches = title.includes(query) || content.includes(query);
            post.style.display = matches ? 'block' : 'none';
        });
    } catch (error) {
        console.error('Search error:', error);
    }
}

// Load more posts
async function loadMorePosts() {
    const btn = this;
    const currentPage = parseInt(btn.dataset.page || '1');
    const container = document.getElementById('posts-container');
    
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Loading...';
    
    try {
        const response = await fetch(`/api/paginated-posts?page=${currentPage + 1}`);
        const data = await response.json();
        
        if (data.success && data.posts.length > 0) {
            btn.dataset.page = currentPage + 1;
            
            data.posts.forEach(post => {
                const postHTML = createPostHTML(post);
                container.insertAdjacentHTML('beforeend', postHTML);
            });
            
            // Hide button if no more posts
            if (data.posts.length < 6) {
                btn.style.display = 'none';
            }
        } else {
            btn.style.display = 'none';
        }
    } catch (error) {
        console.error('Load more error:', error);
    } finally {
        btn.disabled = false;
        btn.textContent = 'Load More';
    }
}

// Create post HTML
function createPostHTML(post) {
    return `
        <div class="post-card card fade-in">
            <div class="post-header">
                <span class="post-category">Tech</span>
                <span class="post-date">${post.date}</span>
            </div>
            <h3 class="post-title">${post.title}</h3>
            <p class="post-excerpt">${post.content.substring(0, 150)}...</p>
            <a href="/post/${post.id}" class="btn btn-outline">
                Read Article <i class="fas fa-arrow-right"></i>
            </a>
        </div>
    `;
}

// Utility: Debounce function
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Utility: Format date
function formatDate(dateString) {
    const options = { year: 'numeric', month: 'long', day: 'numeric' };
    return new Date(dateString).toLocaleDateString('en-US', options);
}

// Export for browser console debugging
window.BlogApp = {
    searchPosts,
    loadMorePosts,
    trackEvent,
    formatDate
};

// Lazy load images
document.addEventListener('DOMContentLoaded', () => {
    const lazyImages = document.querySelectorAll('img[data-src]');
    
    const imageObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const img = entry.target;
                img.src = img.dataset.src;
                img.classList.add('loaded');
                imageObserver.unobserve(img);
            }
        });
    });
    
    lazyImages.forEach(img => imageObserver.observe(img));
});