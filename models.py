from datetime import datetime
from app import db

class Game(db.Model):
    """Game model for storing game information"""
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False, unique=True)
    download_link = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text, nullable=True)
    genres = db.Column(db.String(200), nullable=True)  # Comma-separated genres
    cover_image = db.Column(db.String(300), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Game {self.title}>'
    
    def get_genres_list(self):
        """Return genres as a list, splitting by comma"""
        if self.genres:
            return [genre.strip() for genre in self.genres.split(',') if genre.strip()]
        return []
    
    def get_short_description(self, max_length=100):
        """Return a shortened version of the description"""
        if not self.description:
            return "No description available."
        if len(self.description) <= max_length:
            return self.description
        return self.description[:max_length].rsplit(' ', 1)[0] + '...'
