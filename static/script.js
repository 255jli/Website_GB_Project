// Карусель слов с улучшенной анимацией
const words = [
    'объединяет', 'вдохновляет', 'развивает', 'соединяет', 
    'обогащает', 'мотивирует', 'расширяет', 'преобразует',
    'созидает', 'интегрирует', 'оптимизирует', 'гармонизирует'
];

let currentIndex = 0;
const carouselElement = document.getElementById('word-carousel');

function animateTextChange() {
    const currentWord = words[currentIndex];
    const nextIndex = (currentIndex + 1) % words.length;
    const nextWord = words[nextIndex];
    
    // Эффект исчезновения с 3D трансформацией
    carouselElement.style.opacity = '0';
    carouselElement.style.transform = 'translateZ(-50px) rotateX(90deg)';
    carouselElement.style.filter = 'blur(10px)';
    
    setTimeout(() => {
        // Смена текста
        carouselElement.textContent = nextWord;
        
        // Эффект появления с 3D трансформацией
        carouselElement.style.opacity = '1';
        carouselElement.style.transform = 'translateZ(0) rotateX(0deg)';
        carouselElement.style.filter = 'blur(0)';
        
        currentIndex = nextIndex;
    }, 600);
}

// Запуск карусели
setInterval(animateTextChange, 2500);

// Анимация чисел статистики
function animateStats() {
    const statNumbers = document.querySelectorAll('.stat-number');
    
    statNumbers.forEach(stat => {
        const target = parseFloat(stat.getAttribute('data-target'));
        const duration = 2000;
        const step = target / (duration / 16);
        let current = 0;
        
        const timer = setInterval(() => {
            current += step;
            if (current >= target) {
                current = target;
                clearInterval(timer);
            }
            
            if (target % 1 === 0) {
                // Целое число
                stat.textContent = Math.floor(current);
            } else {
                // Дробное число
                stat.textContent = current.toFixed(1);
            }
        }, 16);
    });
}

// Запуск анимации статистики при скролле
const observerOptions = {
    threshold: 0.5,
    rootMargin: '0px 0px -100px 0px'
};

const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            animateStats();
            observer.unobserve(entry.target);
        }
    });
}, observerOptions);

// Наблюдаем за секцией статистики
const statsSection = document.querySelector('.stats-section');
if (statsSection) {
    observer.observe(statsSection);
}

// Параллакс эффект для звезд
window.addEventListener('scroll', () => {
    const scrolled = window.pageYOffset;
    const stars = document.querySelector('.stars');
    const stars2 = document.querySelector('.stars2');
    const stars3 = document.querySelector('.stars3');
    
    if (stars) stars.style.transform = `translateY(${scrolled * 0.3}px)`;
    if (stars2) stars2.style.transform = `translateY(${scrolled * 0.5}px)`;
    if (stars3) stars3.style.transform = `translateY(${scrolled * 0.7}px)`;
});

// Управление модальным окном авторизации
function showAuthModal(type) {
    const modal = document.getElementById('authModal');
    const loginForm = document.getElementById('loginForm');
    const registerForm = document.getElementById('registerForm');
    
    if (type === 'login') {
        loginForm.style.display = 'block';
        registerForm.style.display = 'none';
    } else {
        loginForm.style.display = 'none';
        registerForm.style.display = 'block';
    }
    
    modal.style.display = 'flex';
}

function closeAuthModal() {
    const modal = document.getElementById('authModal');
    modal.style.display = 'none';
}

// Закрытие модального окна при клике вне его
window.addEventListener('click', (event) => {
    const modal = document.getElementById('authModal');
    if (event.target === modal) {
        closeAuthModal();
    }
});

// Плавная прокрутка к секциям
function scrollToFeatures() {
    document.getElementById('features').scrollIntoView({ 
        behavior: 'smooth' 
    });
}

// Анимация появления элементов при скролле
const scrollObserverOptions = {
    threshold: 0.1,
    rootMargin: '0px 0px -50px 0px'
};

const scrollObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.style.opacity = '1';
            entry.target.style.transform = 'translateY(0)';
        }
    });
}, scrollObserverOptions);

// Наблюдаем за всеми карточками и секциями
document.querySelectorAll('.feature-card, .step-card, .benefit-item, .stat-item').forEach(element => {
    element.style.opacity = '0';
    element.style.transform = 'translateY(30px)';
    element.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
    scrollObserver.observe(element);
});

// Случайные вспышки звезд
function createRandomStarFlashes() {
    setInterval(() => {
        const flash = document.createElement('div');
        flash.style.position = 'fixed';
        flash.style.width = Math.random() * 3 + 1 + 'px';
        flash.style.height = flash.style.width;
        flash.style.background = 'white';
        flash.style.borderRadius = '50%';
        flash.style.left = Math.random() * 100 + 'vw';
        flash.style.top = Math.random() * 100 + 'vh';
        flash.style.boxShadow = '0 0 15px 3px white';
        flash.style.animation = 'starFlash 2s ease-out forwards';
        flash.style.zIndex = '-1';
        
        document.body.appendChild(flash);
        
        setTimeout(() => {
            if (flash.parentNode) {
                flash.remove();
            }
        }, 2000);
    }, 800);
}

// Добавляем CSS для анимации вспышек
const style = document.createElement('style');
style.textContent = `
    @keyframes starFlash {
        0% { opacity: 0; transform: scale(0); }
        50% { opacity: 1; transform: scale(2); }
        100% { opacity: 0; transform: scale(0.5); }
    }
`;
document.head.appendChild(style);

// Интерактивность для карточек
document.querySelectorAll('.feature-card, .step-card, .benefit-item').forEach(card => {
    card.addEventListener('mousemove', (e) => {
        const rect = card.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        
        const centerX = rect.width / 2;
        const centerY = rect.height / 2;
        
        const angleY = (x - centerX) / 20;
        const angleX = (centerY - y) / 20;
        
        card.style.transform = `perspective(1000px) rotateX(${angleX}deg) rotateY(${angleY}deg) scale3d(1.02, 1.02, 1.02)`;
    });
    
    card.addEventListener('mouseleave', () => {
        card.style.transform = 'perspective(1000px) rotateX(0) rotateY(0) scale3d(1, 1, 1)';
    });
});

// Запускаем эффекты при загрузке
document.addEventListener('DOMContentLoaded', () => {
    createRandomStarFlashes();
    
    // Консольное приветствие
    console.log(`
    🚀 Добро пожаловать в CosmoCats! 🚀

    Межгалактическая платформа для общения и взаимодействия

    "Соединяем сообщества через пространство и время"

    ⚡ Особенности:
    • Безопасная и быстрая связь
    • Интуитивный интерфейс
    • Глобальное сообщество
    • Инновационные технологии

    Присоединяйтесь к нашему сообществу! 🌟
    `);
});