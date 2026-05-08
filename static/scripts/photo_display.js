document.body.addEventListener("click", (e) => {
    // Открытие модального окна
    if (e.target.classList.contains("open-photo-modal")) {
        const displayId = e.target.getAttribute("data-display-id");
        const modal = document.getElementById("photoModal");
        const photoList = document.getElementById("photo-list");

        modal.style.display = "flex";
        document.getElementById("target-display-id").value = displayId;

        fetch(`${window.location.origin}/zip/get-display-photos/${displayId}/`)
            .then(response => response.json())
            .then(data => {
                if (data.photos.length === 0) {
                    photoList.innerHTML = "<p>Фото отсутствуют</p>";
                } else {
                    photoList.innerHTML = data.photos.map(photo => `
                        <div class="photo-item">

                            <a href="${photo.url}" target="_blank" title="${photo.name}" class="photo-link"><img src="${photo.url}" alt="${photo.name}" class="photo-img"></a>
                            <button class="delete-photo" data-photo-id="${photo.id}"></button>

                        </div>

                    `).join("");
                }
            });
    }


    // Удаление фото
    if (e.target.classList.contains("delete-photo")) {
        const photoId = e.target.getAttribute("data-photo-id");
        const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute("content");

        if (confirm("Вы уверены, что хотите удалить это фото?")) {
            fetch(`/zip/delete-photos/${photoId}/`, {
                method: "DELETE",
                headers: {
                    "X-CSRFToken": csrfToken,
                    "Content-Type": "application/json"
                }
            })
                .then(response => {
                    if (!response.ok) throw new Error('Ошибка удаления');
                    return response.json();
                })
                .then(() => {
                    e.target.closest(".photo-item").remove();
                })
                .catch(error => console.error('Ошибка:', error));
        }
    }
    document.getElementById("photo-input").addEventListener("change", function () {
        let fileCount = this.files.length;
        let fileLabel = document.getElementById("file-label");

        if (fileCount > 0) {
            fileLabel.textContent = `📸 Выбрано ${fileCount} ${fileCount === 1 ? 'фото' : 'фото'}`;
        } else {
            fileLabel.textContent = "📂 Загрузите одно или несколько фото";
        }
    });
    if (e.target.classList.contains("close-cross") || e.target.classList.contains("overlay") || e.target.classList.contains("cancel")) {
        document.getElementById("photoModal").style.display = "none";
    }
});

// Динамическая кнопка "Добавить фото"
const photoInput = document.getElementById("photo-input");
const form = document.getElementById("photo-upload-form");
let uploadButton = null;

photoInput.addEventListener("change", () => {
    if (photoInput.files.length > 0) {
        if (!uploadButton) {
            uploadButton = document.createElement("button");
            uploadButton.type = "submit";
            uploadButton.className = "head-button animate-on-appear"; // Добавляем класс для анимации
            uploadButton.textContent = "Добавить фото";
            form.appendChild(uploadButton);


        }
    } else if (uploadButton) {
        uploadButton.remove();
        uploadButton = null;
    }
});