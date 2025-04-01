document.body.addEventListener("click", (e) => {
    if (e.target.classList.contains("open-modal")) {
        const modal = document.getElementById("universalModal");
        const modalContent = document.getElementById("modalContent");
        const modalBody = document.getElementById("modalBody");
        const apiUrl = e.target.getAttribute("data-api-url");

        modal.style.display = "flex";
        modalContent.innerHTML = `
            <div class="modal-header">
                <span>Загрузка информации с сервера</span>
                <span class="close-cross">&times;</span>
            </div>
            <div class="modal-body">
                <div class="loading-wrapper">
                    <div class="loading"></div>
                </div>
            </div>
            <div class="modal-footer">
                <button class="action-btn cancel" type="button" id="closeModalBtn">Отмена</button>
                <button class="action-btn submit-btn" type="button">Выполнить</button>
            </div>`;

        let params = {};
        for (let attr of e.target.attributes) {
            if (attr.name.startsWith("data-") && attr.name !== "data-api-url") {
                let key = attr.name.replace("data-", "").replace(/-/g, "_");
                params[key] = attr.value;
            }
        }

        const csrfToken = document.querySelector("input[name='csrfmiddlewaretoken']")?.value ||
            document.querySelector("meta[name='csrf-token']")?.getAttribute("content") || "";

        fetch(apiUrl, {
            method: "POST",
            headers: { "X-CSRFToken": csrfToken, "Content-Type": "application/json" },
            body: JSON.stringify(params)
        })
            .then(response => response.text())
            .then(html => {
                modalContent.innerHTML = html;
            })
            .catch(error => {
                modalBody.innerHTML = "<p>Ошибка загрузки</p>";
            });
    }

    // Делегирование событий для кнопки "Выполнить"
    if (e.target.classList.contains("submit-btn")) {
        const form = document.querySelector("#modalContent form"); // Ищем форму внутри модалки
        if (form) {
            form.submit();
        } else {
            console.error("Форма не найдена");
        }
    }

    // Закрытие окна
    if (e.target.classList.contains("close-cross") || e.target.classList.contains("overlay") || e.target.classList.contains("cancel")) {
        document.getElementById("universalModal").style.display = "none";
    }
});