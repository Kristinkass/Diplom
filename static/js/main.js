// Общие функции для всего сайта

document.addEventListener('DOMContentLoaded', function() {
    // Инициализация главной страницы
    if (document.querySelector('.stats')) {
        loadHomeStats();
    }

    // Настройка даты и времени для форм
    setupDateTimeInputs();

    // Обработка флеш-сообщений
    setupFlashMessages();
});

function loadHomeStats() {
    // Загрузка статистики для главной страницы
    fetch('/api/admin/stats')
        .then(response => {
            if (response.ok) {
                return response.json();
            }
            // Если нет доступа к API, показываем заглушки
            return {
                total_places: 12,
                active_users: 45,
                bookings_today: 8
            };
        })
        .then(data => {
            document.getElementById('total-places').textContent = data.total_places || 12;
            document.getElementById('active-users').textContent = data.total_users || 45;
            document.getElementById('bookings-today').textContent = data.today_bookings || 8;
        })
        .catch(error => {
            console.error('Error loading stats:', error);
            // Значения по умолчанию
            document.getElementById('total-places').textContent = 12;
            document.getElementById('active-users').textContent = 45;
            document.getElementById('bookings-today').textContent = 8;
        });
}

let selectedRating = 0;
let currentBookingId = null;

function openRating(bookingId) {
    currentBookingId = bookingId;
    document.getElementById('ratingModal').style.display = 'block';
}

function closeRating() {
    document.getElementById('ratingModal').style.display = 'none';
    selectedRating = 0;
    updateStars();
}

document.querySelectorAll('#stars span').forEach(star => {
    star.addEventListener('click', function () {
        selectedRating = this.dataset.value;
        updateStars();
    });
});

function updateStars() {
    document.querySelectorAll('#stars span').forEach(star => {
        star.classList.toggle('active', star.dataset.value <= selectedRating);
    });
}

function submitRating() {
    if (!selectedRating) {
        alert("Выберите оценку");
        return;
    }

    fetch('/api/submit_rating', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            booking_id: currentBookingId,
            rating: selectedRating
        })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            alert("Спасибо за оценку!");
            closeRating();
            location.reload();
        } else {
            alert(data.error);
        }
    });
}

function setupDateTimeInputs() {
    // Устанавливаем минимальную дату - сегодня
    const today = new Date().toISOString().split('T')[0];
    const timeInputs = document.querySelectorAll('input[type="datetime-local"]');

    timeInputs.forEach(input => {
        input.min = today + 'T00:00';

        // Установка значений по умолчанию
        if (input.id === 'start-time') {
            const now = new Date();
            now.setMinutes(now.getMinutes() + 30 - (now.getMinutes() % 30));
            input.value = now.toISOString().slice(0, 16);
        }

        if (input.id === 'end-time') {
            const endTime = new Date();
            endTime.setHours(endTime.getHours() + 2);
            endTime.setMinutes(endTime.getMinutes() - (endTime.getMinutes() % 30));
            input.value = endTime.toISOString().slice(0, 16);
        }
    });
}

function setupFlashMessages() {
    // Автоматическое скрытие флеш-сообщений через 5 секунд
    setTimeout(() => {
        const flashes = document.querySelectorAll('.flash');
        flashes.forEach(flash => {
            flash.style.opacity = '0';
            flash.style.transition = 'opacity 0.5s ease';
            setTimeout(() => flash.remove(), 500);
        });
    }, 5000);
}

// Вспомогательные функции
function formatDateTime(dateString) {
    const date = new Date(dateString);
    return date.toLocaleString('ru-RU', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function formatPrice(price) {
    return new Intl.NumberFormat('ru-RU', {
        style: 'currency',
        currency: 'RUB',
        minimumFractionDigits: 0
    }).format(price);
}

// Проверка авторизации
function checkAuth() {
    const authRequiredPaths = ['/map', '/dashboard', '/admin'];
    const currentPath = window.location.pathname;

    if (authRequiredPaths.some(path => currentPath.startsWith(path))) {
        // Проверяем наличие токена или сессии
        // В реальном приложении здесь была бы проверка JWT
        console.log('Auth check for:', currentPath);
    }
}