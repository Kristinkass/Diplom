from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    username = db.Column(db.String(80), nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    phone = db.Column(db.String(20))
    role = db.Column(db.String(20), default='client')  # 'client', 'admin'
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_admin(self):
        return self.role == 'admin'

    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'username': self.username,
            'role': self.role,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    def __repr__(self):
        return f'<User {self.email}>'


class Place(db.Model):
    __tablename__ = 'places'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(50), nullable=False)  # 'desk', 'room', 'office'
    description = db.Column(db.Text)
    x = db.Column(db.Integer, nullable=False)
    y = db.Column(db.Integer, nullable=False)
    width = db.Column(db.Integer, default=1)
    height = db.Column(db.Integer, default=1)
    status = db.Column(db.String(20), default='free')
    price_per_hour = db.Column(db.Float, default=150.0)
    rating = db.Column(db.Float, default=0.0)
    rating_count = db.Column(db.Integer, default=0)
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Place {self.name}>'

    def get_current_booking(self):
        now = datetime.now()
        today = now.date()
        current_time = now.time()
        return Booking.query.filter(
            Booking.place_id == self.id,
            Booking.status == 'active',
            Booking.booking_date == today,
            Booking.start_time <= current_time,
            Booking.end_time > current_time
        ).first()

    def to_dict(self):
        now = datetime.now()
        today = now.date()
        current_time = now.time()
        current_booking = self.get_current_booking()
        is_occupied_now = current_booking is not None

        new_status = 'occupied' if is_occupied_now else 'free'
        if self.status != new_status:
            self.status = new_status
            try:
                db.session.commit()
            except:
                db.session.rollback()

        occupied_until = current_booking.end_time.strftime('%H:%M') if current_booking else None

        return {
            'id': self.id,
            'name': self.name,
            'type': self.type,
            'x': self.x,
            'y': self.y,
            'width': self.width,
            'height': self.height,
            'status': self.status,
            'price_per_hour': self.price_per_hour,
            'rating': round(self.rating, 1) if self.rating else 0.0,
            'rating_count': self.rating_count,
            'active': self.active,
            'occupied_until': occupied_until
        }

    def update_rating(self, new_rating):
        try:
            current_total = self.rating * self.rating_count
            self.rating_count += 1
            self.rating = (current_total + new_rating) / self.rating_count
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            print(f"Ошибка обновления рейтинга: {e}")
            return False


class Booking(db.Model):
    __tablename__ = 'bookings'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    place_id = db.Column(db.Integer, db.ForeignKey('places.id', ondelete='CASCADE'), nullable=False)
    booking_date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    duration_hours = db.Column(db.Float, nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='active')
    user_rating = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='bookings', lazy='joined')
    place = db.relationship('Place', backref='bookings', lazy='joined')

    def to_dict(self):
        return {
            'id': self.id,
            'place_id': self.place_id,
            'place_name': self.place.name if self.place else 'Unknown',
            'booking_date': self.booking_date.strftime('%Y-%m-%d') if self.booking_date else None,
            'start_time': self.start_time.strftime('%H:%M') if self.start_time else None,
            'end_time': self.end_time.strftime('%H:%M') if self.end_time else None,
            'duration_hours': self.duration_hours,
            'total_price': self.total_price,
            'status': self.status,
            'user_rating': self.user_rating,
            'created_at': self.created_at.strftime('%d.%m.%Y %H:%M')
        }


class Rating(db.Model):
    __tablename__ = 'ratings'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    place_id = db.Column(db.Integer, db.ForeignKey('places.id', ondelete='CASCADE'), nullable=False)
    booking_id = db.Column(db.Integer, db.ForeignKey('bookings.id', ondelete='CASCADE'))
    score = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Rating {self.score} for place {self.place_id}>'


class Tariff(db.Model):
    __tablename__ = 'tariffs'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(50), nullable=False)
    price = db.Column(db.Float, nullable=False)
    duration_hours = db.Column(db.Integer)
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# ================== ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ ==================

def create_sample_data():
    """Создание тестовых данных"""
    print("Создание тестовых данных...")
    try:
        if User.query.filter_by(role='admin').count() == 0:
            admin = User(
                email='admin@coworking.com',
                username='Администратор',
                phone='+79990001122',
                role='admin',
                active=True
            )
            admin.set_password('123456')
            db.session.add(admin)

            user = User(
                email='user@example.com',
                username='Тестовый Пользователь',
                phone='+79993334455',
                role='client',
                active=True
            )
            user.set_password('user123')
            db.session.add(user)

        if Place.query.count() == 0:
            places = [
                {'name': 'Стол 1', 'type': 'desk', 'x': 100, 'y': 20, 'price_per_hour': 150},
                {'name': 'Стол 2', 'type': 'desk', 'x': 400, 'y': 20, 'price_per_hour': 150},
                {'name': 'Стол 3', 'type': 'desk', 'x': 3, 'y': 1, 'price_per_hour': 150},
                {'name': 'Стол 4', 'type': 'desk', 'x': 4, 'y': 1, 'price_per_hour': 150},
                {'name': 'Стол 5', 'type': 'desk', 'x': 5, 'y': 1, 'price_per_hour': 150},
                {'name': 'Стол 6', 'type': 'desk', 'x': 6, 'y': 1, 'price_per_hour': 150},
                {'name': 'Стол 7', 'type': 'desk', 'x': 1, 'y': 2, 'price_per_hour': 150},
                {'name': 'Стол 8', 'type': 'desk', 'x': 2, 'y': 2, 'price_per_hour': 150},
                {'name': 'Стол 9', 'type': 'desk', 'x': 3, 'y': 2, 'price_per_hour': 150},
                {'name': 'Стол 10', 'type': 'desk', 'x': 4, 'y': 2, 'price_per_hour': 150},
                {'name': 'Переговорная A', 'type': 'room', 'x': 1, 'y': 4, 'width': 2, 'height': 2, 'price_per_hour': 500},
                {'name': 'Переговорная B', 'type': 'room', 'x': 4, 'y': 4, 'width': 2, 'height': 2, 'price_per_hour': 500},
                {'name': 'Переговорная C', 'type': 'room', 'x': 7, 'y': 4, 'width': 2, 'height': 2, 'price_per_hour': 500},
                {'name': 'Офис 1', 'type': 'office', 'x': 1, 'y': 7, 'width': 3, 'height': 2, 'price_per_hour': 800},
                {'name': 'Офис 2', 'type': 'office', 'x': 5, 'y': 7, 'width': 3, 'height': 2, 'price_per_hour': 800},
            ]
            for place_data in places:
                place = Place(**place_data)
                db.session.add(place)

        db.session.commit()
        print("Тестовые данные созданы!")
    except Exception as e:
        db.session.rollback()
        print(f"Ошибка при создании тестовых данных: {e}")


def update_booking_statuses():
    """Автоматически обновлять статусы бронирований"""
    try:
        now = datetime.now()
        today = now.date()
        current_time = now.time()

        bookings_to_complete = Booking.query.filter(
            Booking.status == 'active',
            db.or_(
                Booking.booking_date < today,
                db.and_(
                    Booking.booking_date == today,
                    Booking.end_time <= current_time
                )
            )
        ).all()

        for booking in bookings_to_complete:
            booking.status = 'completed'

        if bookings_to_complete:
            db.session.commit()
            print(f"Обновлено {len(bookings_to_complete)} бронирований")
            return len(bookings_to_complete)
    except Exception as e:
        db.session.rollback()
        print(f"Ошибка обновления статусов: {e}")
    return 0


def init_db(app):
    with app.app_context():
        print("Создание/проверка таблиц базы данных...")
        db.create_all()
        print("Таблицы базы данных готовы")

        create_sample_data()
        completed = update_booking_statuses()
        if completed > 0:
            print(f"Автоматически завершено {completed} бронирований")