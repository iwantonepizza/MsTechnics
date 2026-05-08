// Получаем все выпадающие меню
document.querySelectorAll('.dropdown-button').forEach(button => {
    button.addEventListener('click', () => {
        const dropdown = button.parentElement;

        // Закрыть другие открытые меню
        document.querySelectorAll('.dropdown').forEach(otherDropdown => {
            if (otherDropdown !== dropdown) {
                otherDropdown.classList.remove('active');
            }
        });

        // Переключить текущее меню
        dropdown.classList.toggle('active');
    });
});

// Закрытие меню при клике вне области
document.addEventListener('click', (e) => {
    if (!e.target.closest('.dropdown')) {
        document.querySelectorAll('.dropdown').forEach(dropdown => {
            dropdown.classList.remove('active');
        });
    }
});
