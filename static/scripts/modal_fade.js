document.addEventListener("DOMContentLoaded", () => {
    const modalOverlays = document.querySelectorAll(".overlay"); // Все модальные окна

    // Открытие модальных окон и передача данных в скрытое поле
    document.body.addEventListener("click", (e) => {
        if (e.target.classList.contains("head-button")) {
            const targetModalId = e.target.getAttribute("data-target");
            const applicationId = e.target.getAttribute("data-application-id"); // Получаем application ID
            const departureId = e.target.getAttribute("data-departure-id");
            const targetStep = e.target.getAttribute("data-next-application-step");
            const panelId = e.target.getAttribute("data-panel-id");
            const newCondition = e.target.getAttribute("data-new-condition");
            const cellId = e.target.getAttribute("data-cell-id");
            const displayId = e.target.getAttribute("data-display-id");

            console.log(11)

            console.log(displayId)

            const targetModal = document.getElementById(targetModalId);
            if (targetModal) {
                targetModal.style.display = "flex"; // Показываем модальное окно

                // Заполняем скрытое поле
                const hiddenApplicationID = targetModal.querySelector("input#application-id");
                if (hiddenApplicationID) {
                    hiddenApplicationID.value = applicationId; // Устанавливаем значение ID
                }
                const hiddenDepartureID = targetModal.querySelector("input#departure-id");
                if (hiddenDepartureID) {
                    hiddenDepartureID.value = departureId;
                }
                const hiddenTargetStep = targetModal.querySelector("input#target-step");
                if (hiddenTargetStep) {
                    hiddenTargetStep.value = targetStep;
                }
                const hiddenPanelId = targetModal.querySelector("input#target-panel-id");
                if (hiddenPanelId) {
                    hiddenPanelId.value = panelId;
                }
                const hiddenNewCondition = targetModal.querySelector("input#condition-new");
                if (hiddenNewCondition) {
                    hiddenNewCondition.value = newCondition;
                }
                const hiddenCellId = targetModal.querySelector("input#target-cell-id");
                if (hiddenCellId) {
                    hiddenCellId.value = cellId;
                }
                const hiddenDisplayId = targetModal.querySelector("input#target-display-id");
                if (hiddenDisplayId) {
                    hiddenDisplayId.value = displayId;
                }


                // Также обновляем текст заголовка
                /*                const modalTitle = targetModal.querySelector("#modalTitle");
                                if (modalTitle) {
                                    modalTitle.textContent = `Вы точно хотите удалить заявку ${applicationId}?`;
                                }*/
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
