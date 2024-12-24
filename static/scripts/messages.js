document.addEventListener("DOMContentLoaded", () => {
    const banners = document.querySelectorAll(".notification-banner");

    banners.forEach((banner) => {
        // Автоматическое скрытие через 5 секунд
        setTimeout(() => {
            hideBanner(banner);
        }, 5000);
    });
});

// Функция для скрытия сообщения
function hideBanner(banner) {
    banner.classList.add("hidden");
    setTimeout(() => {
        banner.remove(); // Удаляем сообщение после завершения анимации
    }, 500);
}

// Функция для закрытия через кнопку
function closeMessage(button) {
    const banner = button.closest(".notification-banner");
    hideBanner(banner);
}