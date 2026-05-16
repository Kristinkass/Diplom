"""
Модель данных, соответствующая предметной области:
Coworking -> Floor -> Location -> Place
User (admin/manager/client) бронирует Service по конкретному Tariff —
бронь (Booking) ссылается на Place, Service и Tariff.

Геометрия (x, y, width, height) хранится не в БД, а в static/layout.json,
сопоставляется по уникальному коду места (Place.code).
"""

import json
import os
from datetime import datetime

from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

db = SQLAlchemy()

# ---------------------------------------------------------------------------
#  Загрузка геометрии и справочника услуг/тарифов из layout.json
# ---------------------------------------------------------------------------
LAYOUT_PATH = os.path.join(os.path.dirname(__file__), 'static', 'layout.json')
_LAYOUT_CACHE = None


def load_layout():
    """Читаем layout.json (с кешированием)."""
    global _LAYOUT_CACHE
    if _LAYOUT_CACHE is None:
        with open(LAYOUT_PATH, 'r', encoding='utf-8') as f:
            _LAYOUT_CACHE = json.load(f)
    return _LAYOUT_CACHE


def reload_layout():
    """Сбросить кеш layout.json (после записи)."""
    global _LAYOUT_CACHE
    _LAYOUT_CACHE = None


def get_place_geometry(code):
    """Вернёт {x, y, width, height} для места по его коду."""
    for p in load_layout().get('places', []):
        if p['code'] == code:
            return {
                'x': p['x'], 'y': p['y'],
                'width': p['width'], 'height': p['height'],
                'rotation': p.get('rotation', 0),
                'floor': p.get('floor', 1)
            }
    return {'x': 0, 'y': 0, 'width': 100, 'height': 100, 'rotation': 0, 'floor': 1}


def save_place_geometry(code, x, y):
    """Обновить координаты места в layout.json и сбросить кеш."""
    layout = load_layout()
    for p in layout.get('places', []):
        if p['code'] == code:
            p['x'] = int(x)
            p['y'] = int(y)
            break
    else:
        return False
    with open(LAYOUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(layout, f, ensure_ascii=False, indent=2)
    reload_layout()
    return True


def add_place_to_layout(place_dict):
    """Добавить новое место в layout.json. place_dict = {code, name, location, kind, mobile, x, y, width, height, price_per_hour, capacity}."""
    layout = load_layout()
    layout.setdefault('places', []).append(place_dict)
    with open(LAYOUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(layout, f, ensure_ascii=False, indent=2)
    reload_layout()
    return True


def remove_place_from_layout(code):
    """Удалить место из layout.json по коду."""
    layout = load_layout()
    places = layout.get('places', [])
    new_places = [p for p in places if p['code'] != code]
    if len(new_places) == len(places):
        return False  # не нашли
    layout['places'] = new_places
    with open(LAYOUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(layout, f, ensure_ascii=False, indent=2)
    reload_layout()
    return True


def generate_place_code(kind, location_code):
    """Сгенерировать уникальный код для нового места, например '1Б-07'."""
    layout = load_layout()
    existing = {p['code'] for p in layout.get('places', [])}
    prefix = location_code + '-'
    max_n = 0
    for c in existing:
        if c.startswith(prefix):
            try:
                n = int(c[len(prefix):])
                if n > max_n:
                    max_n = n
            except ValueError:
                pass
    return prefix + str(max_n + 1).zfill(2)


def resize_place(code, width, height):
    """Изменить размеры места в layout.json."""
    layout = load_layout()
    for p in layout.get('places', []):
        if p['code'] == code:
            p['width'] = int(width)
            p['height'] = int(height)
            break
    else:
        return False
    with open(LAYOUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(layout, f, ensure_ascii=False, indent=2)
    reload_layout()
    return True


def rotate_place(code, rotation):
    layout = load_layout()
    for p in layout.get('places', []):
        if p['code'] == code:
            p['rotation'] = int(rotation) % 360
            break
    else:
        return False
    with open(LAYOUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(layout, f, ensure_ascii=False, indent=2)
    reload_layout()
    return True


# --- Стены ---
def load_walls():
    return load_layout().get('walls', [])


def save_walls(walls):
    layout = load_layout()
    layout['walls'] = walls
    with open(LAYOUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(layout, f, ensure_ascii=False, indent=2)
    reload_layout()


def add_wall(x1, y1, x2, y2, protected=False, floor=1):
    walls = load_walls()
    wall_id = max([w.get('id', 0) for w in walls], default=0) + 1
    walls.append({
        'id': wall_id,
        'x1': int(x1), 'y1': int(y1), 'x2': int(x2), 'y2': int(y2),
        'protected': bool(protected),
        'floor': int(floor or 1),
    })
    save_walls(walls)
    return wall_id


def delete_wall(wall_id):
    walls = load_walls()
    target = next((w for w in walls if w.get('id') == wall_id), None)
    if target is None:
        raise ValueError('Стена не найдена')
    if target.get('protected'):
        raise PermissionError('Эту стену нельзя удалить (несущая)')
    walls = [w for w in walls if w.get('id') != wall_id]
    save_walls(walls)
    # заодно удаляем двери на этой стене
    doors = [d for d in load_doors() if d.get('wall_id') != wall_id]
    save_doors(doors)


# --- Двери ---
def load_doors():
    return load_layout().get('doors', [])


def save_doors(doors):
    layout = load_layout()
    layout['doors'] = doors
    with open(LAYOUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(layout, f, ensure_ascii=False, indent=2)
    reload_layout()


def add_door(wall_id, position, floor=1):
    doors = load_doors()
    door_id = max([d.get('id', 0) for d in doors], default=0) + 1
    doors.append({'id': door_id, 'wall_id': int(wall_id), 'position': float(position), 'width': 50, 'floor': int(floor or 1)})
    save_doors(doors)
    return door_id


def move_door(door_id, wall_id, position):
    doors = load_doors()
    for d in doors:
        if d.get('id') == int(door_id):
            d['wall_id'] = int(wall_id)
            d['position'] = max(0.0, min(1.0, float(position)))
            break
    else:
        return False
    save_doors(doors)
    return True


def delete_door(door_id):
    doors = [d for d in load_doors() if d.get('id') != door_id]
    save_doors(doors)


# ---------------------------------------------------------------------------
#  Сущности предметной области
# ---------------------------------------------------------------------------
class Coworking(db.Model):
    __tablename__ = 'coworkings'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    address = db.Column(db.String(255), nullable=False)
    floors = db.relationship('Floor', backref='coworking', cascade='all, delete-orphan')


class Floor(db.Model):
    __tablename__ = 'floors'
    id = db.Column(db.Integer, primary_key=True)
    coworking_id = db.Column(db.Integer, db.ForeignKey('coworkings.id', ondelete='CASCADE'), nullable=False)
    number = db.Column(db.Integer, nullable=False)
    name = db.Column(db.String(80))
    locations = db.relationship('Location', backref='floor', cascade='all, delete-orphan')


class Location(db.Model):
    __tablename__ = 'locations'
    id = db.Column(db.Integer, primary_key=True)
    floor_id = db.Column(db.Integer, db.ForeignKey('floors.id', ondelete='CASCADE'), nullable=False)
    code = db.Column(db.String(16), unique=True, nullable=False)   # 1А, 1Б, 2А ...
    name = db.Column(db.String(120), nullable=False)
    kind = db.Column(db.String(40), nullable=False)                # office_zone / desk_zone / room_zone / openspace_zone
    places = db.relationship('Place', backref='location', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Location {self.code} {self.name}>'


# ---------------------------------------------------------------------------
#  Пользователи (админ / менеджер / клиент)
# ---------------------------------------------------------------------------
class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    username = db.Column(db.String(80), nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    phone = db.Column(db.String(20))
    # admin | manager | client
    role = db.Column(db.String(20), default='client')
    # Только для client: subscription | hourly
    visitor_kind = db.Column(db.String(20), default='hourly')
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_admin(self):
        return self.role == 'admin'

    def is_manager(self):
        return self.role == 'manager'

    def is_visitor(self):
        return self.role == 'client'

    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'username': self.username,
            'role': self.role,
            'visitor_kind': self.visitor_kind,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f'<User {self.email} ({self.role})>'


# ---------------------------------------------------------------------------
#  Рабочее место
# ---------------------------------------------------------------------------
class Place(db.Model):
    __tablename__ = 'places'

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(32), unique=True, nullable=False)   # 1А-01, OS-01 ...
    name = db.Column(db.String(100), nullable=False)
    location_id = db.Column(db.Integer, db.ForeignKey('locations.id', ondelete='CASCADE'), nullable=False)
    # desk | room | office | openspace
    kind = db.Column(db.String(20), nullable=False)
    mobile = db.Column(db.Boolean, default=False)   # стационарное / мобильное место
    description = db.Column(db.Text)
    status = db.Column(db.String(20), default='free')
    price_per_hour = db.Column(db.Float, default=150.0)
    rating = db.Column(db.Float, default=0.0)
    rating_count = db.Column(db.Integer, default=0)
    active = db.Column(db.Boolean, default=True)
    capacity = db.Column(db.Integer, default=1)
    maintenance = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # ---- Совместимость со старым кодом, который обращается к place.type ----
    @property
    def type(self):
        """Раньше Place.type было relationship на PlaceType с .name.
        Сейчас kind хранится строкой — отдаём её напрямую."""
        return self.kind

    def __repr__(self):
        return f'<Place {self.code} {self.name}>'

    # ---- Бронирования ----
    def get_current_booking(self):
        now = datetime.now()
        return Booking.query.filter(
            Booking.place_id == self.id,
            Booking.status == 'active',
            Booking.booking_date == now.date(),
            Booking.start_time <= now.time(),
            Booking.end_time > now.time()
        ).first()

    def get_current_occupancy(self):
        now = datetime.now()
        return Booking.query.filter(
            Booking.place_id == self.id,
            Booking.status == 'active',
            Booking.booking_date == now.date(),
            Booking.start_time <= now.time(),
            Booking.end_time > now.time()
        ).count()

    def get_occupancy_at(self, booking_date, start_time, end_time):
        return Booking.query.filter(
            Booking.place_id == self.id,
            Booking.booking_date == booking_date,
            Booking.status == 'active',
            Booking.start_time < end_time,
            Booking.end_time > start_time
        ).count()

    def get_seats_status_at(self, booking_date, start_time, end_time):
        """Какие места заняты на пересекающемся интервале.

        Возвращает: {
          'taken_seats': [int, ...],     # занятые конкретные места (seat_number)
          'whole_table_taken': bool,      # есть ли бронь стола целиком
        }
        """
        overlapping = Booking.query.filter(
            Booking.place_id == self.id,
            Booking.booking_date == booking_date,
            Booking.status == 'active',
            Booking.start_time < end_time,
            Booking.end_time > start_time,
        ).all()
        taken = [b.seat_number for b in overlapping if b.seat_number is not None]
        whole = any(b.seat_number is None for b in overlapping)
        return {'taken_seats': sorted(set(taken)), 'whole_table_taken': whole}

    def get_seats_status_now(self):
        """Какие места заняты прямо сейчас."""
        now = datetime.now()
        return self.get_seats_status_at(now.date(), now.time(), now.time())

    def to_dict(self):
        geom = get_place_geometry(self.code)

        if self.maintenance:
            return {
                'id': self.id, 'code': self.code, 'name': self.name,
                'type': self.kind, 'kind': self.kind, 'mobile': self.mobile,
                'location_code': self.location.code if self.location else None,
                'x': geom['x'], 'y': geom['y'],
                'width': geom['width'], 'height': geom['height'],
                'rotation': geom.get('rotation', 0),
                'floor': geom.get('floor', 1),
                'status': 'maintenance',
                'price_per_hour': self.price_per_hour,
                'rating': round(self.rating, 1) if self.rating else 0.0,
                'rating_count': self.rating_count,
                'active': self.active, 'capacity': self.capacity,
                'maintenance': True,
                'current_occupancy': 0, 'occupied_until': None,
                'taken_seats': [], 'whole_table_taken': False,
            }

        is_openspace = self.kind == 'openspace'
        current_occupancy = self.get_current_occupancy()

        if is_openspace:
            is_occupied_now = current_occupancy >= self.capacity
        else:
            is_occupied_now = self.get_current_booking() is not None

        new_status = 'occupied' if is_occupied_now else 'free'
        if self.status != new_status:
            self.status = new_status
            try:
                db.session.commit()
            except Exception:
                db.session.rollback()

        occupied_until = None
        if is_occupied_now and not is_openspace:
            cur = self.get_current_booking()
            if cur:
                occupied_until = cur.end_time.strftime('%H:%M')

        seats_status = self.get_seats_status_now()

        return {
            'id': self.id, 'code': self.code, 'name': self.name,
            'type': self.kind, 'kind': self.kind, 'mobile': self.mobile,
            'location_code': self.location.code if self.location else None,
            'x': geom['x'], 'y': geom['y'],
            'width': geom['width'], 'height': geom['height'],
            'rotation': geom.get('rotation', 0),
            'floor': geom.get('floor', 1),
            'status': self.status,
            'price_per_hour': self.price_per_hour,
            'rating': round(self.rating, 1) if self.rating else 0.0,
            'rating_count': self.rating_count,
            'active': self.active, 'capacity': self.capacity,
            'maintenance': self.maintenance,
            'current_occupancy': current_occupancy,
            'occupied_until': occupied_until,
            'taken_seats': seats_status['taken_seats'],
            'whole_table_taken': seats_status['whole_table_taken'],
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


# ---------------------------------------------------------------------------
#  Услуги и тарифы
# ---------------------------------------------------------------------------
class Service(db.Model):
    __tablename__ = 'services'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(32), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    # place_short | place_month | location_short
    kind = db.Column(db.String(40), nullable=False)
    active = db.Column(db.Boolean, default=True)
    tariffs = db.relationship('Tariff', backref='service', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Service {self.code}>'


class Tariff(db.Model):
    __tablename__ = 'tariffs'
    id = db.Column(db.Integer, primary_key=True)
    service_id = db.Column(db.Integer, db.ForeignKey('services.id', ondelete='CASCADE'), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    price = db.Column(db.Float, nullable=False)
    duration_hours = db.Column(db.Integer)   # null = безлимит/абонемент
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'service_id': self.service_id,
            'service_code': self.service.code if self.service else None,
            'name': self.name,
            'price': self.price,
            'duration_hours': self.duration_hours,
        }


# ---------------------------------------------------------------------------
#  Аренда (Бронирование)
# ---------------------------------------------------------------------------
class Booking(db.Model):
    __tablename__ = 'bookings'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    place_id = db.Column(db.Integer, db.ForeignKey('places.id', ondelete='CASCADE'), nullable=False)
    service_id = db.Column(db.Integer, db.ForeignKey('services.id', ondelete='SET NULL'), nullable=True)
    tariff_id = db.Column(db.Integer, db.ForeignKey('tariffs.id', ondelete='SET NULL'), nullable=True)

    # NULL = бронь стола целиком; число 1..capacity = конкретное место за столом
    seat_number = db.Column(db.Integer, nullable=True)

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
    service = db.relationship('Service', lazy='joined')
    tariff = db.relationship('Tariff', lazy='joined')

    def to_dict(self):
        return {
            'id': self.id,
            'place_id': self.place_id,
            'place_name': self.place.name if self.place else 'Unknown',
            'seat_number': self.seat_number,
            'service': self.service.name if self.service else None,
            'tariff': self.tariff.name if self.tariff else None,
            'booking_date': self.booking_date.strftime('%Y-%m-%d') if self.booking_date else None,
            'start_time': self.start_time.strftime('%H:%M') if self.start_time else None,
            'end_time': self.end_time.strftime('%H:%M') if self.end_time else None,
            'duration_hours': self.duration_hours,
            'total_price': self.total_price,
            'status': self.status,
            'user_rating': self.user_rating,
            'created_at': self.created_at.strftime('%d.%m.%Y %H:%M'),
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


# ---------------------------------------------------------------------------
#  Сидинг тестовых данных из layout.json
# ---------------------------------------------------------------------------
def create_sample_data():
    print("Создание тестовых данных...")
    try:
        layout = load_layout()

        # 1. Coworking + Floor
        if Coworking.query.count() == 0:
            cw_data = layout['coworking']
            cw = Coworking(name=cw_data['name'], address=cw_data['address'])
            db.session.add(cw)
            db.session.flush()
            fl_data = layout['floor']
            fl = Floor(coworking_id=cw.id, number=fl_data['number'], name=fl_data['name'])
            db.session.add(fl)
            db.session.commit()
            print("✓ Создан коворкинг и этаж")

        floor = Floor.query.first()

        # 2. Locations
        for loc_data in layout['locations']:
            if not Location.query.filter_by(code=loc_data['code']).first():
                db.session.add(Location(
                    floor_id=floor.id,
                    code=loc_data['code'],
                    name=loc_data['name'],
                    kind=loc_data['kind'],
                ))
        db.session.commit()
        print(f"✓ Локации: {Location.query.count()}")

        # 3. Places
        for p in layout['places']:
            if Place.query.filter_by(code=p['code']).first():
                continue
            location = Location.query.filter_by(code=p['location']).first()
            if not location:
                print(f"❌ Не найдена локация {p['location']} для места {p['code']}")
                continue
            db.session.add(Place(
                code=p['code'],
                name=p['name'],
                location_id=location.id,
                kind=p['kind'],
                mobile=p.get('mobile', False),
                price_per_hour=p['price_per_hour'],
                capacity=p.get('capacity', 1),
            ))
        db.session.commit()
        print(f"✓ Рабочие места: {Place.query.count()}")

        # 4. Services
        for s in layout.get('services', []):
            if not Service.query.filter_by(code=s['code']).first():
                db.session.add(Service(code=s['code'], name=s['name'], kind=s['kind']))
        db.session.commit()

        # 5. Tariffs
        for t in layout.get('tariffs', []):
            service = Service.query.filter_by(code=t['service_code']).first()
            if not service:
                continue
            exists = Tariff.query.filter_by(service_id=service.id, name=t['name']).first()
            if exists:
                continue
            db.session.add(Tariff(
                service_id=service.id,
                name=t['name'],
                price=t['price'],
                duration_hours=t.get('duration_hours'),
            ))
        db.session.commit()
        print(f"✓ Услуги/тарифы: {Service.query.count()}/{Tariff.query.count()}")

        # 6. Админ
        if User.query.filter_by(role='admin').count() == 0:
            admin = User(
                email='admin@coworking.com', username='Администратор',
                phone='+79990001122', role='admin', active=True,
            )
            admin.set_password('123456')
            db.session.add(admin)
            db.session.commit()
            print("✓ Админ создан (admin@coworking.com / 123456)")

        # 7. Менеджер ресепшена (для демо)
        if User.query.filter_by(role='manager').count() == 0:
            mgr = User(
                email='manager@coworking.com', username='Менеджер ресепшена',
                phone='+79990002233', role='manager', active=True,
            )
            mgr.set_password('123456')
            db.session.add(mgr)
            db.session.commit()
            print("✓ Менеджер создан (manager@coworking.com / 123456)")

        print("Тестовые данные успешно загружены!")
    except Exception as e:
        db.session.rollback()
        print(f"Ошибка при создании тестовых данных: {e}")
        import traceback
        traceback.print_exc()


def update_booking_statuses():
    try:
        now = datetime.now()
        bookings_to_complete = Booking.query.filter(
            Booking.status == 'active',
            db.or_(
                Booking.booking_date < now.date(),
                db.and_(
                    Booking.booking_date == now.date(),
                    Booking.end_time <= now.time(),
                ),
            ),
        ).all()
        for b in bookings_to_complete:
            b.status = 'completed'
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
