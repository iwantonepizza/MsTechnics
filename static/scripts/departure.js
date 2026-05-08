document.addEventListener("DOMContentLoaded", () => {
    const modalOverlay = document.getElementById("dellDeparture");
    const closeModalBtn = document.getElementById("closeModalBtn");
    const cancelModalBtn = document.getElementById("cancelModalBtn");
    const confirmDeleteBtn = document.getElementById("confirmDeleteBtn");
    const modalDepartureId = document.getElementById("modalDepartureId");


    let currentDepartureId = null;

    // Открытие модального окна
    document.querySelectorAll(".open-modal-btn").forEach(button => {
        button.addEventListener("click", () => {
            currentDepartureId = button.getAttribute("data-application-id");
            modalDepartureId.value = currentDepartureId; // Устанавливаем ID
            modalOverlay.style.display = "flex";
        });
    });

    // Закрытие модального окна
    closeModalBtn.addEventListener("click", () => {
        modalOverlay.style.display = "none";
    });

    cancelModalBtn.addEventListener("click", () => {
        modalOverlay.style.display = "none";
    });

    // Обработчик кнопки удаления
    confirmDeleteBtn.addEventListener("click", () => {
        fetch("{% url 'main_menu:delete_departure' %}", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": "{{ csrf_token }}", // CSRF-токен
            },
            body: JSON.stringify({
                departure_id: currentDepartureId
            }),
        })
            .then(response => {
                if (response.ok) {
                    return response.json();
                }
                throw new Error("Ошибка удаления");
            })
            .then(data => {
                alert(data.message); // Сообщение об успешном удалении
                modalOverlay.style.display = "none";
                location.reload(); // Обновляем страницу
            })
            .catch(error => {
                console.error("Ошибка:", error);
                alert("Не удалось удалить выезд. Попробуйте позже.");
            });
    });
});
