// === Глобальные утилиты ===
const Utils = {
    // Форматирование даты
    formatDate(dateString) {
        const date = new Date(dateString);
        const now = new Date();
        const diffMs = now - date;
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMs / 3600000);
        const diffDays = Math.floor(diffMs / 86400000);

        if (diffMins < 1) return 'только что';
        if (diffMins < 60) return `${diffMins} мин назад`;
        if (diffHours < 24) return `${diffHours} ч назад`;
        if (diffDays < 7) return `${diffDays} д назад`;
        
        return date.toLocaleDateString('ru-RU', {
            day: 'numeric',
            month: 'short',
            year: 'numeric'
        });
    },

    // Дебаунс
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },

    // Генерация случайного ID
    generateId() {
        return Math.random().toString(36).substr(2, 9);
    }
};

// === Управление темой ===
class ThemeManager {
    constructor() {
        this.themeToggle = document.getElementById('theme-toggle');
        this.themeIcon = this.themeToggle?.querySelector('.theme-icon');
        this.body = document.body;
        this.init();
    }

    init() {
        this.loadTheme();
        this.bindEvents();
    }

    loadTheme() {
        const savedTheme = localStorage.getItem('theme') || 'dark';
        this.setTheme(savedTheme);
    }

    setTheme(theme) {
        this.body.classList.remove('theme-dark', 'theme-light');
        this.body.classList.add(`theme-${theme}`);
        localStorage.setItem('theme', theme);
        this.updateThemeIcon(theme);
    }

    updateThemeIcon(theme) {
        if (this.themeIcon) {
            this.themeIcon.textContent = theme === 'dark' ? '🌙' : '☀️';
        }
    }

    toggleTheme() {
        const isDark = this.body.classList.contains('theme-dark');
        this.setTheme(isDark ? 'light' : 'dark');
    }

    bindEvents() {
        if (this.themeToggle) {
            this.themeToggle.addEventListener('click', () => this.toggleTheme());
        }
    }
}

// === Управление пользовательским меню ===
class UserMenuManager {
    constructor() {
        this.menuTrigger = document.getElementById('user-menu-trigger');
        this.menu = document.getElementById('user-menu');
        this.init();
    }

    init() {
        this.bindEvents();
        this.loadUserAvatar();
    }

    bindEvents() {
        if (this.menuTrigger && this.menu) {
            // Переключение меню
            this.menuTrigger.addEventListener('click', (e) => {
                e.stopPropagation();
                this.menu.classList.toggle('hidden');
            });

            // Закрытие меню при клике вне
            document.addEventListener('click', () => {
                this.menu.classList.add('hidden');
            });

            // Предотвращение закрытия при клике внутри меню
            this.menu.addEventListener('click', (e) => {
                e.stopPropagation();
            });
        }
    }

    loadUserAvatar() {
        const userAvatar = document.getElementById('user-avatar-img');
        if (userAvatar && window.current_user_id) {
            userAvatar.src = `/user/${window.current_user_id}/avatar?t=${Date.now()}`;
            userAvatar.onload = () => {
                userAvatar.style.display = 'block';
                userAvatar.nextElementSibling.style.display = 'none';
            };
            userAvatar.onerror = () => {
                userAvatar.style.display = 'none';
                userAvatar.nextElementSibling.style.display = 'flex';
            };
        }
    }
}

// === Генератор случайных котов ===
class CatGenerator {
    constructor() {
        this.catButton = document.getElementById('fetch-cat-btn');
        this.catImage = document.getElementById('random-cat-img');
        this.catPlaceholder = document.getElementById('cat-placeholder');
        this.catLoader = document.getElementById('cat-loader');
        this.catError = document.getElementById('cat-error');
        this.init();
    }

    init() {
        if (this.catButton) {
            this.catButton.addEventListener('click', () => this.fetchRandomCat());
        }
    }

    async fetchRandomCat() {
        if (!this.catButton || !this.catImage) return;
        const originalText = this.catButton.textContent;
        this.catButton.disabled = true;
        this.catButton.textContent = 'Загружаю...';
        this.catButton.classList.add('loading');
        if (this.catLoader) this.catLoader.style.display = 'flex';
        if (this.catPlaceholder) this.catPlaceholder.style.display = 'none';
        if (this.catError) this.catError.style.display = 'none';
        this.catImage.style.display = 'none';
        try {
            const response = await fetch('/random-cat');
            if (!response.ok) throw new Error();
            const data = await response.json();
            if (data.url) {
                this.catImage.src = data.url + '?t=' + Date.now();
                this.catImage.style.display = 'block';
                this.catImage.style.animation = 'fadeIn 0.5s ease-in';
            } else {
                if (this.catError) {
                    this.catError.textContent = 'Мяу, ошибка загрузки! Попробуй ещё.';
                    this.catError.style.display = 'block';
                }
                if (this.catPlaceholder) this.catPlaceholder.style.display = 'block';
            }
        } catch (error) {
            if (this.catError) {
                this.catError.textContent = 'Мяу, ошибка загрузки! Попробуй ещё.';
                this.catError.style.display = 'block';
            }
            if (this.catPlaceholder) this.catPlaceholder.style.display = 'block';
        } finally {
            this.catButton.disabled = false;
            this.catButton.textContent = originalText;
            this.catButton.classList.remove('loading');
            if (this.catLoader) this.catLoader.style.display = 'none';
        }
    }
}

// === Управление чатом ===
class ChatManager {
    constructor() {
        this.chatHistory = document.getElementById('chat-history');
        this.chatForm = document.getElementById('chat-form');
        this.messageInput = this.chatForm?.querySelector('input[name="message"]');
        this.init();
    }

    init() {
        if (this.chatHistory) {
            this.scrollToBottom();
            this.bindEvents();
        }
    }

    scrollToBottom() {
        if (this.chatHistory) {
            this.chatHistory.scrollTop = this.chatHistory.scrollHeight;
        }
    }

    bindEvents() {
        if (this.chatForm && this.messageInput) {
            // Автофокус на поле ввода
            setTimeout(() => {
                this.messageInput.focus();
            }, 100);

            // Отправка по Enter
            this.messageInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    if (this.messageInput.value.trim()) {
                        this.submitForm();
                    }
                }
            });

            // Авторазмер текстового поля
            this.messageInput.addEventListener('input', () => {
                this.adjustTextareaHeight();
            });
        }
    }

    adjustTextareaHeight() {
        if (this.messageInput.tagName === 'TEXTAREA') {
            this.messageInput.style.height = 'auto';
            this.messageInput.style.height = Math.min(this.messageInput.scrollHeight, 120) + 'px';
        }
    }

    submitForm() {
        if (!this.chatForm) return;

        const submitBtn = this.chatForm.querySelector('button[type="submit"]');
        const originalContent = submitBtn.innerHTML;

        // Блокируем форму
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<div class="loading-spinner"></div>';

        // Временно отключаем автофокус
        this.messageInput.blur();

        // Отправляем форму
        this.chatForm.requestSubmit();

        // Через 3 секунды разблокируем (на случай ошибки)
        setTimeout(() => {
            submitBtn.disabled = false;
            submitBtn.innerHTML = originalContent;
            this.messageInput.focus();
        }, 3000);
    }

    addMessage(role, content, isTemporary = false) {
        if (!this.chatHistory) return;

        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${role}-message ${isTemporary ? 'temporary' : ''}`;
        
        const avatar = role === 'user' ? '👤' : '🐱';
        const timestamp = new Date().toLocaleTimeString('ru-RU', {
            hour: '2-digit',
            minute: '2-digit'
        });

        messageDiv.innerHTML = `
            <div class="message-avatar">${avatar}</div>
            <div class="message-content">
                <div class="message-text">${content}</div>
                <div class="message-time">${timestamp}</div>
            </div>
        `;

        this.chatHistory.appendChild(messageDiv);
        this.scrollToBottom();

        if (isTemporary) {
            messageDiv.style.opacity = '0.7';
        }

        return messageDiv;
    }
}

// === Управление табами в профиле ===
class TabManager {
    constructor() {
        this.tabs = document.querySelectorAll('.nav-item[data-tab]');
        this.tabContents = document.querySelectorAll('.tab-content');
        this.init();
    }

    init() {
        this.bindEvents();
        
        // Активируем первый таб по умолчанию
        if (this.tabs.length > 0) {
            this.activateTab(this.tabs[0].getAttribute('data-tab'));
        }
    }

    bindEvents() {
        this.tabs.forEach(tab => {
            tab.addEventListener('click', (e) => {
                e.preventDefault();
                const tabId = tab.getAttribute('data-tab');
                this.activateTab(tabId);
            });
        });
    }

    activateTab(tabId) {
        // Деактивируем все табы
        this.tabs.forEach(tab => tab.classList.remove('active'));
        this.tabContents.forEach(content => content.classList.remove('active'));

        // Активируем выбранный таб
        const activeTab = document.querySelector(`.nav-item[data-tab="${tabId}"]`);
        const activeContent = document.getElementById(`${tabId}-tab`);

        if (activeTab && activeContent) {
            activeTab.classList.add('active');
            activeContent.classList.add('active');
        }
    }
}

// === Инициализация при загрузке страницы ===
document.addEventListener('DOMContentLoaded', () => {
    // Инициализация менеджеров
    new ThemeManager();
    new UserMenuManager();
    new CatGenerator();
    new ChatManager();
    
    // Инициализация табов только на странице профиля
    if (document.querySelector('.profile-nav')) {
        new TabManager();
    }

    // Дополнительные улучшения UX
    enhanceUX();
});

// === Дополнительные улучшения UX ===
function enhanceUX() {
    // Плавная прокрутка для якорей
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({ 
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });

    // Подтверждение выхода (без confirm)

    // Обработка изображений с запасным вариантом
    document.querySelectorAll('img').forEach(img => {
        img.addEventListener('error', function() {
            this.style.display = 'none';
            const fallback = this.nextElementSibling;
            if (fallback && fallback.classList.contains('avatar-fallback')) {
                fallback.style.display = 'flex';
            }
        });
    });

    // Анимация появления элементов при скролле
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
            }
        });
    }, observerOptions);

    // Наблюдаем за карточками и другими элементами
    document.querySelectorAll('.feature-card, .auth-card, .chat-item').forEach(el => {
        el.style.opacity = '0';
        el.style.transform = 'translateY(20px)';
        el.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
        observer.observe(el);
    });

    // Улучшение производительности при скролле
    let scrollTimer;
    window.addEventListener('scroll', () => {
        document.body.classList.add('scrolling');
        clearTimeout(scrollTimer);
        scrollTimer = setTimeout(() => {
            document.body.classList.remove('scrolling');
        }, 100);
    });
}

// === Глобальные обработчики ошибок ===
window.addEventListener('error', (e) => {
    console.error('Global error:', e.error);
});

window.addEventListener('unhandledrejection', (e) => {
    console.error('Unhandled promise rejection:', e.reason);
});

// Экспорт для использования в других модулях
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        Utils,
        ThemeManager,
        UserMenuManager,
        CatGenerator,
        ChatManager,
        TabManager
    };
}