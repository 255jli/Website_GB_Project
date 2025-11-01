// Модуль для управления анимацией фона (звезды, пыль)
const BackgroundAnimator = {
    init() {
        this.stars = document.querySelectorAll('.stars, .stars2, .stars3');
        this.dust = document.querySelector('.space-dust');
        this.animate();
    },
    animate() {
        // Анимация уже реализована через CSS keyframes, JavaScript может управлять параметрами
        // Пример: изменение скорости анимации звезд при скролле
        window.addEventListener('scroll', () => {
            const scrollPosition = window.scrollY;
            this.stars.forEach((starLayer, index) => {
                // Простой эффект параллакса для демонстрации
                starLayer.style.transform = `translateY(${scrollPosition * (0.1 + index * 0.05)}px)`;
            });
        });
    }
};

// Модуль для анимации прокрутки
const ScrollAnimator = {
    init() {
        this.sections = document.querySelectorAll('section');
        this.observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('visible');
                }
            });
        }, { threshold: 0.1 });
        this.observeSections();
    },
    observeSections() {
        this.sections.forEach(section => {
            this.observer.observe(section);
        });
    }
};

// Модуль для управления анимацией чисел в статистике (если будет)
const NumberAnimator = {
    animateValue(element, start, end, duration) {
        let startTimestamp = null;
        const step = (timestamp) => {
            if (!startTimestamp) startTimestamp = timestamp;
            const progress = Math.min((timestamp - startTimestamp) / duration, 1);
            const currentValue = Math.floor(progress * (end - start) + start);
            element.textContent = currentValue;
            if (progress < 1) {
                window.requestAnimationFrame(step);
            }
        };
        window.requestAnimationFrame(step);
    },
    // Пример использования, если будут элементы статистики
    init() {
        // const statElements = document.querySelectorAll('.stat-number');
        // statElements.forEach(el => {
        //     const targetValue = parseInt(el.dataset.target);
        //     // Запускать анимацию при пересечении
        // });
    }
};

// Модуль для карусели слов
const TextCarousel = {
    words: [
        'общаются', 'вдохновляют', 'исследуют', 'создают', 'покоряют',
        'развлекают', 'мурлыкают', 'мечтают', 'путешествуют', 'открывают',
        'изучают', 'строят', 'играют', 'спят', 'охотятся', 'правят', 'следят'
    ],
    currentIndex: 0,
    element: null,
    init() {
        this.element = document.getElementById('word-carousel');
        if (this.element) {
            this.update();
            setInterval(() => {
                this.currentIndex = (this.currentIndex + 1) % this.words.length;
                this.update();
            }, 2500);
        }
    },
    update() {
        if (this.element) {
            this.element.textContent = this.words[this.currentIndex];
        }
    }
};

// Модуль для анимации прокрутки к якорям
const SmoothScroll = {
    init() {
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {
            anchor.addEventListener('click', (e) => {
                e.preventDefault();
                const targetId = anchor.getAttribute('href');
                const targetElement = document.querySelector(targetId);
                if (targetElement) {
                    targetElement.scrollIntoView({
                        behavior: 'smooth'
                    });
                }
            });
        });
    }
};

// Модуль для управления модальными окнами
const ModalManager = {
    init() {
        this.authModal = document.getElementById('authModal');
        this.loginForm = document.getElementById('loginForm');
        this.registerForm = document.getElementById('registerForm');
        this.closeButton = document.querySelector('.close-modal');

        this.closeButton?.addEventListener('click', () => this.close());
        window.addEventListener('click', (e) => {
            if (e.target === this.authModal) {
                this.close();
            }
        });
    },
    open(formType) {
        if (this.authModal) {
            this.authModal.style.display = 'flex';
            this.loginForm.style.display = 'none';
            this.registerForm.style.display = 'none';
            document.getElementById(`${formType}Form`).style.display = 'block';
        }
    },
    close() {
        if (this.authModal) {
            this.authModal.style.display = 'none';
        }
    }
};

// Модуль для управления формами (в реальном проекте расширяется)
const FormManager = {
    init() {
        // Пример добавления обработчиков форм
        // document.querySelectorAll('.cosmic-input').forEach(input => {
        //     input.addEventListener('input', this.validateInput);
        // });
    },
    validateInput(event) {
        // Логика валидации
    }
};

// Инициализация всех модулей при загрузке DOM
document.addEventListener('DOMContentLoaded', () => {
    BackgroundAnimator.init();
    ScrollAnimator.init();
    NumberAnimator.init();
    TextCarousel.init();
    SmoothScroll.init();
    ModalManager.init();
    FormManager.init();
});

// Глобальные функции для HTML (если требуются)
function showAuthModal(formType) {
    ModalManager.open(formType);
}

function closeAuthModal() {
    ModalManager.close();
}

function scrollToFeatures() {
    const featuresSection = document.getElementById('features');
    if (featuresSection) {
        featuresSection.scrollIntoView({ behavior: 'smooth' });
    }
}