from flask import Flask, render_template, jsonify, request, redirect, url_for, flash, abort, Response
import requests
import json
import sqlite3
from datetime import datetime, date
import os
import re
from html import unescape
import pytz
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)

SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY:
    import secrets
    SECRET_KEY = secrets.token_hex(32)
    print(f"Warning: Generated temporary SECRET_KEY: {SECRET_KEY[:10]}...")

app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-for-local')
BLOGGER_URL = os.environ.get('BLOGGER_URL', "https://paradiseofgeeks.blogspot.com")
BLOGGER_JSON_FEED = f"{BLOGGER_URL}/feeds/posts/default?alt=json"

ADSENSE_PUBLISHER_ID = "ca-pub-7442313663988423"  
ADSENSE_ENABLED = True

def init_db():
    conn = sqlite3.connect('blog.db')  # Normal path works on Render!
    c = conn.cursor()
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS analytics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            page_views INTEGER DEFAULT 0,
            unique_visitors INTEGER DEFAULT 0,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Insert initial analytics row
    c.execute('SELECT COUNT(*) FROM analytics WHERE id = 1')
    if c.fetchone()[0] == 0:
        c.execute('INSERT INTO analytics (id, page_views) VALUES (1, 0)')
    
    conn.commit()
    conn.close()

init_db()

def clean_html_content(html_content):
    if not html_content:
        return ""

    clean_text = re.sub(r'<[^>]+>', ' ', html_content)
    clean_text = unescape(clean_text)
    clean_text = re.sub(r'\s+', ' ', clean_text).strip()
    
    return clean_text

def get_blogger_posts():
    try:
        response = requests.get(BLOGGER_JSON_FEED, timeout=10)
        if response.status_code == 200:
            data = response.json()
            posts = []
            
            for entry in data.get('feed', {}).get('entry', []):
                title = entry.get('title', {}).get('$t', 'No Title')
                
                content = entry.get('content', {}).get('$t', '')
                if not content:
                    content = entry.get('summary', {}).get('$t', '')
                
                thumbnail = None
                import re

                img_patterns = [
                    r'https://[^"\s]*blogger\.googleusercontent\.com[^"\s]*=w\d+-h\d+',  
                    r'src="(https://[^"]+\.(jpg|jpeg|png|gif|webp))"',  
                    r'src=\'(https://[^\']+\.(jpg|jpeg|png|gif|webp))\'', 
                ]
                
                for pattern in img_patterns:
                    match = re.search(pattern, content, re.IGNORECASE)
                    if match:
                        thumbnail = match.group(0) if '=' in match.group(0) else match.group(1)
                        if 'src="' in thumbnail:
                            thumbnail = thumbnail.replace('src="', '').replace('"', '')
                        elif "src='" in thumbnail:
                            thumbnail = thumbnail.replace("src='", '').replace("'", '')
                        break

                if not thumbnail:
                    colors = ['4ade80', '38bdf8', 'f472b6', 'f59e0b', '8b5cf6']
                    color_index = hash(title) % len(colors)
                    color = colors[color_index]
                    thumbnail = f"https://via.placeholder.com/400x200/{color}/0f172a?text={title[:15].replace(' ', '+')}"

                clean_text = re.sub(r'<[^>]+>', ' ', content)
                clean_text = re.sub(r'\s+', ' ', clean_text).strip()
                words = clean_text.split()[:50] 
                preview = ' '.join(words) + '...'

                url = BLOGGER_URL
                for link in entry.get('link', []):
                    if link.get('rel') == 'alternate':
                        url = link.get('href', BLOGGER_URL)
                        break
                published = entry.get('published', {}).get('$t', '')
                try:
                    date_obj = datetime.fromisoformat(published.replace('Z', '+00:00'))
                except:
                    date_obj = datetime.now()
                
                posts.append({
                    'id': entry.get('id', {}).get('$t', '').split('.')[-1],
                    'title': title,
                    'preview': preview,
                    'content': content,
                    'plain_content': clean_text,  
                    'thumbnail': thumbnail, 
                    'url': url,
                    'date': date_obj.strftime('%B %d, %Y'),
                    'categories': extract_categories(entry)  
                })
            
            return posts[:10]
        return []
    except Exception as e:
        print(f"Blogger fetch error: {e}")
        return [{
            'id': '1',
            'title': 'Master Linux Commands',
            'preview': 'Learn essential Linux commands for beginners. Master the terminal...',
            'content': '<p>Sample content</p>',
            'plain_content': 'Sample content',
            'thumbnail': 'https://via.placeholder.com/400x200/4ade80/0f172a?text=Linux+Tutorial',
            'date': 'January 28, 2024',
            'categories': ['Linux', 'Tutorial']
        }]
    
def create_plain_excerpt(html_content):
    if not html_content:
        return ""
    
    text = re.sub(r'<[^>]+>', ' ', html_content)
    text = re.sub(r'\s+', ' ', text).strip()
    text = unescape(text)
    
    return text

def extract_first_image(html_content):
    if not html_content:
        return None
    
    img_match = re.search(r'<img[^>]+src="([^">]+)"', html_content)
    if img_match:
        return img_match.group(1)
    
    return None

def extract_category(entry):
    try:
        categories = entry.get('category', [])
        if categories and isinstance(categories, list):
            for cat in categories:
                if isinstance(cat, dict) and 'term' in cat:
                    return cat['term'].replace('"', '')
        return "Tech"
    except:
        return "Tech"


def get_paginated_posts(page=1, per_page=6):
    posts = get_blogger_posts()
    start = (page - 1) * per_page
    end = start + per_page
    return posts[start:end]

def safe_clean_html(html_content):
    try:
        if not html_content:
            return ""
        
        html_content = html_content.replace('<br>', '\n').replace('<br/>', '\n').replace('<br />', '\n')

        html_content = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL)
        html_content = re.sub(r'<style[^>]*>.*?</style>', '', html_content, flags=re.DOTALL)
        html_content = re.sub(r'<div[^>]*>', '<p>', html_content)
        html_content = html_content.replace('</div>', '</p>')
        html_content = re.sub(r'\s+', ' ', html_content)
        html_content = unescape(html_content)
        
        return html_content.strip()
    except Exception as e:
        print(f"Error cleaning HTML: {e}")
        return re.sub(r'<[^>]+>', ' ', html_content)[:500] + '...'
    
def get_related_posts(current_post_id, current_post_title, all_posts, limit=3):
    related = []

    current_words = set(current_post_title.lower().split())
    
    for post in all_posts:
        if post['id'] == current_post_id:
            continue  
        

        post_words = set(post['title'].lower().split())
        common_words = current_words.intersection(post_words)
        
        if len(common_words) >= 1:  
            related.append({
                'post': post,
                'score': len(common_words)
            })

    related.sort(key=lambda x: x['score'], reverse=True)
    return [item['post'] for item in related[:limit]]

def get_fallback_posts(current_post_id, all_posts, limit=3):
    return [post for post in all_posts if post['id'] != current_post_id][:limit]


@app.route('/')
def home():
    posts = get_blogger_posts()

    featured = posts[0] if posts else None
 
    if featured and 'featured_content' not in featured:
        featured['featured_content'] = featured.get('content', '')
    
    seo_meta = generate_seo_meta(
        title="Tech Blog for Developers",
        description="Learn Linux, Python, AI, and web development with tutorials and guides."
    )
    
    return render_template('index.html', 
                         posts=posts[:3], 
                         featured=featured,
                         **seo_meta)

@app.route('/blog')
def blog():
    posts = get_blogger_posts()
    all_categories = {}
    for post in posts:
        for cat in post.get('categories', []):
            all_categories[cat] = all_categories.get(cat, 0) + 1

    category = request.args.get('category', '').lower()
    if category:
        filtered_posts = [
            p for p in posts 
            if any(cat.lower() == category for cat in p.get('categories', []))
        ]
    else:
        filtered_posts = posts
    
    seo_meta = generate_seo_meta(
        title="Programming Tutorials & Guides",
        description="Browse all tech articles about Linux, Python, AI, and web development.",
        keywords="programming tutorials, coding guides, tech articles, developer resources"
    )
    
    return render_template('blog.html', 
                         posts=filtered_posts,
                         all_categories=sorted(all_categories.keys()),
                         category_counts=all_categories,
                         **seo_meta)

@app.route('/post/<post_id>')
def post_detail(post_id):
    all_posts = get_blogger_posts()
    post_data = next((p for p in all_posts if p['id'] == post_id), None)
    
    if not post_data:
        try:
            response = requests.get(f"{BLOGGER_URL}/feeds/posts/default/{post_id}?alt=json")
            if response.status_code == 200:
                data = response.json()
                entry = data.get('entry', {})
                post_data = {
                    'id': post_id,
                    'title': entry.get('title', {}).get('$t', 'Post'),
                    'content': entry.get('content', {}).get('$t', 'Post not found'),
                    'plain_content': clean_html_content(entry.get('content', {}).get('$t', '')),
                    'url': f"{BLOGGER_URL}/{post_id}",
                    'date': datetime.now().strftime('%B %d, %Y'),
                    'thumbnail': extract_first_image(entry.get('content', {}).get('$t', '')) or 
                                f"https://via.placeholder.com/400x200/4ade80/0f172a?text={entry.get('title', {}).get('$t', 'Post')}",
                    'categories': extract_categories(entry)
                }
        except:
            post_data = {
                'id': post_id,
                'title': 'Post Not Found',
                'content': 'The requested post could not be loaded.',
                'plain_content': 'The requested post could not be loaded.',
                'url': '#',
                'date': datetime.now().strftime('%B %d, %Y'),
                'thumbnail': f"https://via.placeholder.com/400x200/f59e0b/0f172a?text=Post+Not+Found",
                'categories': ['Tech']
            }

    related_posts = get_related_posts(post_id, post_data['title'], all_posts, 3)

    if not related_posts:
        related_posts = get_fallback_posts(post_id, all_posts, 3)

    structured_data = {
        "@context": "https://schema.org",
        "@type": "BlogPosting",
        "headline": str(post_data['title']),
        "description": clean_html_content(post_data.get('content', ''))[:200] if post_data.get('content') else "",
        "image": post_data.get('thumbnail', ''),
        "datePublished": post_data['date'],
        "dateModified": post_data['date'],
        "author": {
            "@type": "Person",
            "name": "Paradise of Geeks"
        },
        "publisher": {
            "@type": "Organization",
            "name": "Paradise of Geeks"
        }
    }

    structured_data_json = json.dumps(structured_data, default=str)

    conn = sqlite3.connect('blog.db')
    c = conn.cursor()
    c.execute('UPDATE analytics SET page_views = page_views + 1 WHERE id = 1')
    conn.commit()
    conn.close()
    
    seo_meta = generate_seo_meta(
        title=post_data['title'],
        description=clean_html_content(post_data.get('content', ''))[:160] if post_data.get('content') else "",
        image=post_data.get('thumbnail', '')
    )
    
    return render_template('post.html', 
                         post=post_data, 
                         related_posts=related_posts,
                         structured_data_json=structured_data_json,
                         **seo_meta)

@app.route('/search')
def search():
    try:
        query = request.args.get('q', '').strip().lower()
        sort_by = request.args.get('sort', 'relevance')
        
        # Get posts with error handling
        try:
            all_posts = get_blogger_posts()
        except Exception as e:
            print(f"Error getting posts: {e}")
            all_posts = []
        
        results = []
        
        if query and all_posts:
            # Simple search
            for post in all_posts:
                if query in post['title'].lower() or query in post.get('preview', '').lower():
                    results.append(post)
        else:
            results = all_posts
        
        # Sort results
        if sort_by == 'recent':
            results.sort(key=lambda x: x.get('date', ''), reverse=True)
        elif sort_by == 'title':
            results.sort(key=lambda x: x['title'].lower())
        
        seo_meta = generate_seo_meta(
            title=f"Search Results: '{query}'" if query else "Search Articles",
            description=f"Search results for {query}" if query else "Search tech articles",
            keywords="search, tutorials, programming"
        )
        
        return render_template('search_results.html',
                             results=results[:12],
                             search_query=query,
                             sort=sort_by,
                             page=1,
                             total_pages=1,
                             total_results=len(results),
                             categories=[],
                             **seo_meta)
        
    except Exception as e:
        print(f"Search error: {e}")
        # Return simple error page
        return render_template('search_results.html',
                             results=[],
                             search_query=request.args.get('q', ''),
                             error="Search temporarily unavailable")

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    message_sent = False
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        message = request.form.get('message', '').strip()
    
        if not name or not email or not message:
            flash('All fields are required!', 'error')
        elif '@' not in email or '.' not in email:
            flash('Please enter a valid email address!', 'error')
        else:
            try:
                conn = sqlite3.connect('blog.db')
                c = conn.cursor()
                c.execute('''
                    CREATE TABLE IF NOT EXISTS contacts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        email TEXT NOT NULL,
                        message TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                c.execute('INSERT INTO contacts (name, email, message) VALUES (?, ?, ?)',
                         (name, email, message))
                conn.commit()
                conn.close()
                
                flash('Message sent successfully! We\'ll get back to you soon.', 'success')
                message_sent = True
                
            except Exception as e:
                print(f"Error saving contact: {e}")
                flash('Error sending message. Please try again later.', 'error')
    
    seo_meta = generate_seo_meta(
        title="Contact Us - Paradise of Geeks",
        description="Get in touch with Paradise of Geeks. Send your questions, suggestions, or feedback about tech tutorials.",
        keywords="contact, get in touch, feedback, suggestions, tech support"
    )
    
    return render_template('contact.html', 
                         message_sent=message_sent,
                         **seo_meta)


@app.route('/api/all-posts')
def api_all_posts():
    posts = get_blogger_posts()
    return jsonify({'success': True, 'posts': posts})

@app.route('/api/paginated-posts')
def api_paginated_posts():
    page = request.args.get('page', 1, type=int)
    posts = get_paginated_posts(page, 6)
    return jsonify({'success': True, 'posts': posts})

@app.route('/api/analytics')
def api_analytics():
    conn = sqlite3.connect('blog.db')
    c = conn.cursor()
    c.execute('SELECT page_views FROM analytics WHERE id = 1')
    views = c.fetchone()[0]
    conn.close()
    
    return jsonify({'views': views})

@app.route('/api/track-view', methods=['POST'])
def api_track_view():
    try:
        conn = sqlite3.connect('blog.db')
        c = conn.cursor()
        c.execute('UPDATE analytics SET page_views = page_views + 1 WHERE id = 1')
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500

@app.errorhandler(403)
def forbidden_error(error):
    return render_template('error.html', error_code=403, error_message="Access Forbidden"), 403

@app.context_processor
def inject_adsense():
    return {
        'adsense_publisher_id': ADSENSE_PUBLISHER_ID,
        'ads_enabled': ADSENSE_ENABLED
    }

@app.route('/api/track-ad-click', methods=['POST'])
def track_ad_click():
    data = request.json
    print(f"Ad clicked: {data.get('ad_id')}")
    return jsonify({'success': True})

@app.route('/api/track-analytics', methods=['POST'])
def track_analytics():
    try:
        data = request.json
        
        conn = sqlite3.connect('blog.db')
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS analytics_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT,
                event_data TEXT,
                page_url TEXT,
                user_agent TEXT,
                ip_address TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        c.execute('''
            INSERT INTO analytics_events 
            (event_type, event_data, page_url, user_agent, ip_address)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            data.get('event'),
            json.dumps(data),
            request.referrer,
            request.user_agent.string,
            request.remote_addr
        ))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
    except Exception as e:
        print(f"Analytics error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/get-analytics')
def get_analytics():
    conn = sqlite3.connect('blog.db')
    c = conn.cursor()

    c.execute('''
        SELECT 
            COUNT(*) as total_visits,
            COUNT(DISTINCT ip_address) as unique_visitors,
            SUM(CASE WHEN event_type = 'page_view' THEN 1 ELSE 0 END) as page_views,
            SUM(CASE WHEN event_type = 'view_post' THEN 1 ELSE 0 END) as post_views
        FROM analytics_events 
        WHERE DATE(created_at) = DATE('now')
    ''')
    today_stats = c.fetchone()

    c.execute('''
        SELECT 
            json_extract(event_data, '$.post_title') as post_title,
            COUNT(*) as views
        FROM analytics_events 
        WHERE event_type = 'view_post'
        GROUP BY json_extract(event_data, '$.post_id')
        ORDER BY views DESC
        LIMIT 5
    ''')
    top_posts = c.fetchall()
    
    conn.close()
    
    return jsonify({
        'today': {
            'total_visits': today_stats[0] or 0,
            'unique_visitors': today_stats[1] or 0,
            'page_views': today_stats[2] or 0,
            'post_views': today_stats[3] or 0
        },
        'top_posts': [
            {'title': post[0] or 'Unknown', 'views': post[1]} 
            for post in top_posts
        ]
    })

def generate_seo_meta(title=None, description=None, keywords=None, image=None):
    """Generate SEO metadata for pages"""
    from flask import url_for  
    
    return {
        'seo_title': title,
        'seo_description': description or "Tech blog covering Linux, Python, AI, and web development.",
        'seo_keywords': keywords or "Linux, Python, programming, web development, AI, tutorials",
        'seo_image': image or url_for('static', filename='images/og-default.jpg', _external=True)
    }

def extract_categories(entry):
    categories = []
    cat_data = entry.get('category', [])
    if isinstance(cat_data, list):
        for cat in cat_data:
            if isinstance(cat, dict) and 'term' in cat:
                cat_name = cat['term'].strip('"')
                if cat_name and cat_name.lower() not in ['uncategorized', 'general']:
                    categories.append(cat_name)

    if not categories:
        title = entry.get('title', {}).get('$t', '').lower()
        common_tags = ['linux', 'python', 'tutorial', 'web', 'devops', 'ai', 'programming', 'beginners']
        for tag in common_tags:
            if tag in title:
                categories.append(tag.capitalize())
    
    return categories[:3] 

def generate_blog_post_schema(post):
    from flask import url_for
    
    return {
        "@context": "https://schema.org",
        "@type": "BlogPosting",
        "headline": post['title'],
        "description": post['content'][:200],
        "image": post.get('image', url_for('static', filename='images/blog-default.jpg', _external=True)),
        "datePublished": post.get('timestamp', ''),
        "dateModified": post.get('timestamp', ''),
        "author": {
            "@type": "Person",
            "name": post.get('author', 'Paradise of Geeks')
        },
        "publisher": {
            "@type": "Organization",
            "name": "Paradise of Geeks",
            "logo": {
                "@type": "ImageObject",
                "url": url_for('static', filename='images/logo.png', _external=True)
            }
        },
        "mainEntityOfPage": {
            "@type": "WebPage",
            "@id": post['url']
        }
    }

@app.route('/sitemap.xml')
def sitemap():
    posts = get_blogger_posts()
    base_url = request.host_url.rstrip('/')

    urls = [
        {'loc': f'{base_url}/', 'changefreq': 'daily', 'priority': '1.0'},
        {'loc': f'{base_url}/blog', 'changefreq': 'daily', 'priority': '0.9'},
        {'loc': f'{base_url}/contact', 'changefreq': 'monthly', 'priority': '0.7'},
        {'loc': f'{base_url}/search', 'changefreq': 'weekly', 'priority': '0.6'},
    ]
    
    for post in posts:
        urls.append({
            'loc': f'{base_url}/post/{post["id"]}',
            'lastmod': datetime.now().strftime('%Y-%m-%d'),
            'changefreq': 'monthly',
            'priority': '0.8'
        })

    xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    
    for url in urls:
        xml += '  <url>\n'
        xml += f'    <loc>{url["loc"]}</loc>\n'
        if 'lastmod' in url:
            xml += f'    <lastmod>{url["lastmod"]}</lastmod>\n'
        xml += f'    <changefreq>{url["changefreq"]}</changefreq>\n'
        xml += f'    <priority>{url["priority"]}</priority>\n'
        xml += '  </url>\n'
    
    xml += '</urlset>'
    
    return Response(xml, mimetype='application/xml')

@app.route('/robots.txt')
def robots():
    robots_txt = """User-agent: *
    Allow: /
    Disallow: /admin
    Disallow: /api/

    Sitemap: {}/sitemap.xml
    """.format(request.host_url.rstrip('/'))
    return Response(robots_txt, mimetype='text/plain')

@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    return response

@app.after_request
def add_cache_headers(response):
    if request.endpoint == 'static':
        response.cache_control.max_age = 31536000 
    elif request.endpoint in ['home', 'blog', 'post_detail']:
        response.cache_control.max_age = 300  
    return response

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)