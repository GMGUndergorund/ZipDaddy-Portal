import re
from urllib.parse import urlparse
from flask import render_template, request, redirect, url_for, session, flash, abort
from sqlalchemy import func
from app import app, db
from models import Game

# Admin credentials
ADMIN_USERNAME = "Zipdaddy"
ADMIN_PASSWORD = "Kareem.1707"

def is_admin():
    """Check if user is logged in as admin"""
    return session.get('admin_logged_in', False)

def validate_url(url):
    """Validate if URL is properly formatted"""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc]) and result.scheme in ['http', 'https']
    except:
        return False

def validate_image_url(url):
    """Validate if URL points to an image"""
    if not url:
        return True  # Optional field
    if not validate_url(url):
        return False
    # Check for common image extensions
    image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg']
    return any(url.lower().endswith(ext) for ext in image_extensions)

@app.route('/')
def index():
    """Homepage with game listing, search, and filter functionality"""
    search = request.args.get('search', '').strip()
    genre_filter = request.args.get('genre', '').strip()
    sort_by = request.args.get('sort', 'newest')
    
    # Start with base query
    query = Game.query
    
    # Apply search filter
    if search:
        query = query.filter(Game.title.ilike(f'%{search}%'))
    
    # Apply genre filter
    if genre_filter:
        query = query.filter(Game.genres.ilike(f'%{genre_filter}%'))
    
    # Apply sorting
    if sort_by == 'alphabetical':
        query = query.order_by(Game.title)
    else:  # newest
        query = query.order_by(Game.created_at.desc())
    
    games = query.all()
    
    # Get all unique genres for filter dropdown
    all_games = Game.query.all()
    all_genres = set()
    for game in all_games:
        all_genres.update(game.get_genres_list())
    all_genres = sorted(list(all_genres))
    
    return render_template('index.html', 
                         games=games, 
                         search=search, 
                         genre_filter=genre_filter,
                         sort_by=sort_by,
                         all_genres=all_genres,
                         is_admin=is_admin())

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Admin login page"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            flash('Successfully logged in!', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid username or password!', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """Admin logout"""
    session.pop('admin_logged_in', None)
    flash('Successfully logged out!', 'info')
    return redirect(url_for('index'))

@app.route('/admin')
def admin_dashboard():
    """Admin dashboard with statistics"""
    if not is_admin():
        flash('Access denied. Please log in as admin.', 'danger')
        return redirect(url_for('login'))
    
    # Calculate statistics
    total_games = Game.query.count()
    
    # Get genre statistics
    all_games = Game.query.all()
    genre_counts = {}
    for game in all_games:
        for genre in game.get_genres_list():
            genre_counts[genre] = genre_counts.get(genre, 0) + 1
    
    # Sort genres by count
    top_genres = sorted(genre_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    
    return render_template('admin_dashboard.html', 
                         total_games=total_games,
                         top_genres=top_genres)

@app.route('/upload', methods=['GET', 'POST'])
def upload_game():
    """Upload new game (admin only)"""
    if not is_admin():
        flash('Access denied. Please log in as admin.', 'danger')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        # Get form data
        title = request.form.get('title', '').strip()
        download_link = request.form.get('download_link', '').strip()
        description = request.form.get('description', '').strip()
        genres = request.form.get('genres', '').strip()
        cover_image = request.form.get('cover_image', '').strip()
        
        # Validation
        errors = []
        
        if not title:
            errors.append("Title is required.")
        elif Game.query.filter_by(title=title).first():
            errors.append("A game with this title already exists.")
        
        if not download_link:
            errors.append("Download link is required.")
        elif not validate_url(download_link):
            errors.append("Download link must be a valid URL starting with http:// or https://")
        
        if cover_image and not validate_image_url(cover_image):
            errors.append("Cover image must be a valid image URL.")
        
        if errors:
            for error in errors:
                flash(error, 'danger')
        else:
            # Create new game
            game = Game(
                title=title,
                download_link=download_link,
                description=description if description else None,
                genres=genres if genres else None,
                cover_image=cover_image if cover_image else None
            )
            
            try:
                db.session.add(game)
                db.session.commit()
                flash(f'Game "{title}" uploaded successfully!', 'success')
                return redirect(url_for('admin_dashboard'))
            except Exception as e:
                db.session.rollback()
                flash('Error uploading game. Please try again.', 'danger')
                app.logger.error(f"Error uploading game: {e}")
    
    return render_template('upload.html')

@app.route('/game/<int:game_id>')
def game_detail(game_id):
    """Game detail page"""
    game = Game.query.get_or_404(game_id)
    return render_template('game_detail.html', game=game, is_admin=is_admin())

@app.route('/edit/<int:game_id>', methods=['GET', 'POST'])
def edit_game(game_id):
    """Edit game (admin only)"""
    if not is_admin():
        flash('Access denied. Please log in as admin.', 'danger')
        return redirect(url_for('login'))
    
    game = Game.query.get_or_404(game_id)
    
    if request.method == 'POST':
        # Get form data
        title = request.form.get('title', '').strip()
        download_link = request.form.get('download_link', '').strip()
        description = request.form.get('description', '').strip()
        genres = request.form.get('genres', '').strip()
        cover_image = request.form.get('cover_image', '').strip()
        
        # Validation
        errors = []
        
        if not title:
            errors.append("Title is required.")
        elif title != game.title and Game.query.filter_by(title=title).first():
            errors.append("A game with this title already exists.")
        
        if not download_link:
            errors.append("Download link is required.")
        elif not validate_url(download_link):
            errors.append("Download link must be a valid URL starting with http:// or https://")
        
        if cover_image and not validate_image_url(cover_image):
            errors.append("Cover image must be a valid image URL.")
        
        if errors:
            for error in errors:
                flash(error, 'danger')
        else:
            # Update game
            game.title = title
            game.download_link = download_link
            game.description = description if description else None
            game.genres = genres if genres else None
            game.cover_image = cover_image if cover_image else None
            
            try:
                db.session.commit()
                flash(f'Game "{title}" updated successfully!', 'success')
                return redirect(url_for('game_detail', game_id=game.id))
            except Exception as e:
                db.session.rollback()
                flash('Error updating game. Please try again.', 'danger')
                app.logger.error(f"Error updating game: {e}")
    
    return render_template('edit_game.html', game=game)

@app.route('/delete/<int:game_id>', methods=['POST'])
def delete_game(game_id):
    """Delete game (admin only)"""
    if not is_admin():
        flash('Access denied. Please log in as admin.', 'danger')
        return redirect(url_for('login'))
    
    game = Game.query.get_or_404(game_id)
    title = game.title
    
    try:
        db.session.delete(game)
        db.session.commit()
        flash(f'Game "{title}" deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error deleting game. Please try again.', 'danger')
        app.logger.error(f"Error deleting game: {e}")
    
    return redirect(url_for('admin_dashboard'))

@app.route('/stats')
def stats():
    """Public statistics page"""
    # Total games
    total_games = Game.query.count()
    
    # Genre statistics
    all_games = Game.query.all()
    genre_counts = {}
    for game in all_games:
        for genre in game.get_genres_list():
            genre_counts[genre] = genre_counts.get(genre, 0) + 1
    
    # Top 5 genres
    top_genres = sorted(genre_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    
    # Last 5 added games
    recent_games = Game.query.order_by(Game.created_at.desc()).limit(5).all()
    
    return render_template('stats.html', 
                         total_games=total_games,
                         top_genres=top_genres,
                         recent_games=recent_games)

@app.route('/genre/<genre_name>')
def genre_page(genre_name):
    """Display all games in a specific genre"""
    games = Game.query.filter(Game.genres.ilike(f'%{genre_name}%')).order_by(Game.created_at.desc()).all()
    
    # Filter games that actually contain the exact genre
    filtered_games = []
    for game in games:
        if genre_name in game.get_genres_list():
            filtered_games.append(game)
    
    return render_template('index.html', 
                         games=filtered_games,
                         genre_filter=genre_name,
                         all_genres=[],
                         search='',
                         sort_by='newest',
                         is_admin=is_admin(),
                         genre_page_title=f'Games in "{genre_name}"')
