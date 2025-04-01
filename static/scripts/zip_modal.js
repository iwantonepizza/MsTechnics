document.addEventListener("DOMContentLoaded", () => {
    const modalOverlays = document.querySelectorAll(".overlay"); // Все модальные окна

    // Открытие модальных окон и передача данных в скрытое поле
    document.body.addEventListener("click", (e) => {
        if (e.target.classList.contains("action-button")) {
            const targetModalId = e.target.getAttribute("data-target");
            const applicationId = e.target.getAttribute("data-application-id"); // Получаем application ID


            const targetModal = document.getElementById(targetModalId);
            if (targetModal) {
                targetModal.style.display = "flex"; // Показываем модальное окно

                // Заполняем скрытое поле
                const hiddenApplicationID = targetModal.querySelector("input#application-id");
                if (hiddenApplicationID) {
                    hiddenApplicationID.value = applicationId; // Устанавливаем значение ID
                }
            }
        }
    });

    // Закрытие всех окон через кнопки "X" или фон
    document.body.addEventListener("click", (e) => {
        if (e.target.classList.contains("close-cross") || e.target.classList.contains("overlay")) {
            modalOverlays.forEach(modal => modal.style.display = "none");
        }
    });

    // Дополнительно: предотвращение отправки формы на кнопке "Отмена"
    document.body.addEventListener("click", (e) => {
        if (e.target.classList.contains("cancel")) {
            e.preventDefault(); // Предотвращаем действие по умолчанию
            const currentModal = e.target.closest(".overlay");
            if (currentModal) currentModal.style.display = "none"; // Закрываем окно
        }
    });
});


function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

document.addEventListener('DOMContentLoaded', function() {
    const inputs = document.querySelectorAll('.wire-input');
    const saveButton = document.getElementById('save-button');
    const deleteButtons = document.querySelectorAll('.delete-photo-btn');
    const updateButtons = document.querySelectorAll('.update-photo-btn');
    let changes = new Map();

    // Отслеживание изменений в input (count)
    inputs.forEach(input => {
        input.addEventListener('input', function() {
            const wireId = this.dataset.wireId;
            const originalValue = parseInt(this.dataset.originalValue);
            const newValue = parseInt(this.value);

            if (newValue !== originalValue) {
                changes.set(wireId, newValue);
            } else {
                changes.delete(wireId);
            }
            saveButton.style.display = changes.size > 0 ? 'block' : 'none';
        });
    });

    // Сохранение изменений count
    saveButton.addEventListener('click', function() {
        if (changes.size === 0) return;

        let message = `Вы изменили ${changes.size} значений:\n`;
        changes.forEach((newValue, wireId) => {
            const original = document.querySelector(`input[data-wire-id="${wireId}"]`).dataset.originalValue;
            message += `Wire #${wireId}: ${original} → ${newValue}\n`;
        });
        message += "Сохранить изменения?";

        if (confirm(message)) {
            const updates = Array.from(changes.entries()).map(([id, value]) => `${id}:${value}`);
            fetch(window.updateWiresUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: 'updates[]=' + updates.join('&updates[]=')
            })
            .then(response => {
                if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
                return response.json();
            })
            .then(data => {
                if (data.status === 'success') {
                    changes.forEach((newValue, wireId) => {
                        const input = document.querySelector(`input[data-wire-id="${wireId}"]`);
                        if (input) input.dataset.originalValue = newValue;
                    });
                    changes.clear();
                    saveButton.style.display = 'none';
                    alert('Данные успешно обновлены!');
                } else {
                    alert('Ошибка: ' + data.message);
                }
            })
            .catch(error => alert('Ошибка при сохранении: ' + error));
        }
    });

    // Удаление фото
    deleteButtons.forEach(button => {
        button.addEventListener('click', function() {
            const wireId = this.dataset.wireId;
            if (confirm(`Удалить фото для Wire #${wireId}?`)) {
                fetch(window.deletePhotoUrl, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/x-www-form-urlencoded',
                        'X-CSRFToken': getCookie('csrftoken')
                    },
                    body: `wire_id=${wireId}`
                })
                .then(response => {
                    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
                    return response.json();
                })
                .then(data => {
                    if (data.status === 'success') {
                        const wireItem = document.querySelector(`.wire-item[data-wire-id="${wireId}"]`);
                        if (wireItem) {
                            const photoLink = wireItem.querySelector('.photo-link');
                            const deleteBtn = wireItem.querySelector('.delete-photo-btn');
                            if (photoLink) photoLink.remove(); // Удаляем ссылку
                            if (deleteBtn) deleteBtn.remove(); // Удаляем кнопку
                        }
                        alert('Фото удалено!');
                    } else {
                        alert('Ошибка: ' + data.message);
                    }
                })
                .catch(error => alert('Ошибка при удалении: ' + error));
            }
        });
    });

    // Обновление фото
    updateButtons.forEach(button => {
        button.addEventListener('click', function() {
            const wireId = this.dataset.wireId;
            const fileInput = document.querySelector(`.photo-upload[data-wire-id="${wireId}"]`);
            if (fileInput) {
                fileInput.click();

                fileInput.addEventListener('change', function() {
                    if (fileInput.files.length > 0) {
                        const formData = new FormData();
                        formData.append('wire_id', wireId);
                        formData.append('photo', fileInput.files[0]);

                        fetch(window.updatePhotoUrl, {
                            method: 'POST',
                            headers: {
                                'X-CSRFToken': getCookie('csrftoken')
                            },
                            body: formData
                        })
                        .then(response => {
                            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
                            return response.json();
                        })
                        .then(data => {
                            if (data.status === 'success') {
                                const wireItem = document.querySelector(`.wire-item[data-wire-id="${wireId}"]`);
                                if (wireItem) {
                                    // Обновляем или создаем ссылку на фото
                                    let photoLink = wireItem.querySelector('.photo-link');
                                    if (!photoLink) {
                                        photoLink = document.createElement('a');
                                        photoLink.className = 'photo-link';
                                        photoLink.target = '_blank';
                                        photoLink.textContent = 'Фото';
                                        wireItem.insertBefore(photoLink, wireItem.querySelector('.update-photo-btn'));
                                    }
                                    photoLink.href = data.photo_url; // Обновляем URL

                                    // Убеждаемся, что кнопка "Удалить" есть
                                    let deleteBtn = wireItem.querySelector('.delete-photo-btn');
                                    if (!deleteBtn) {
                                        deleteBtn = document.createElement('button');
                                        deleteBtn.className = 'delete-photo-btn';
                                        deleteBtn.textContent = 'Удалить фото';
                                        deleteBtn.dataset.wireId = wireId;
                                        wireItem.insertBefore(deleteBtn, wireItem.querySelector('.update-photo-btn'));
                                        // Привязываем обработчик к новой кнопке
                                        deleteBtn.addEventListener('click', function() {
                                            if (confirm(`Удалить фото для Wire #${wireId}?`)) {
                                                fetch(window.deletePhotoUrl, {
                                                    method: 'POST',
                                                    headers: {
                                                        'Content-Type': 'application/x-www-form-urlencoded',
                                                        'X-CSRFToken': getCookie('csrftoken')
                                                    },
                                                    body: `wire_id=${wireId}`
                                                })
                                                .then(res => {
                                                    if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
                                                    return res.json();
                                                })
                                                .then(d => {
                                                    if (d.status === 'success') {
                                                        const item = document.querySelector(`.wire-item[data-wire-id="${wireId}"]`);
                                                        if (item) {
                                                            const pl = item.querySelector('.photo-link');
                                                            const db = item.querySelector('.delete-photo-btn');
                                                            if (pl) pl.remove();
                                                            if (db) db.remove();
                                                        }
                                                        alert('Фото удалено!');
                                                    } else {
                                                        alert('Ошибка: ' + d.message);
                                                    }
                                                })
                                                .catch(err => alert('Ошибка при удалении: ' + err));
                                            }
                                        });
                                    }
                                }
                                alert('Фото обновлено!');
                                fileInput.value = ''; // Очищаем input
                            } else {
                                alert('Ошибка: ' + data.message);
                            }
                        })
                        .catch(error => alert('Ошибка при обновлении: ' + error));
                    }
                }, { once: true });
            }
        });
    });
});