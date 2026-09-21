// ---- Edit mode toggle ----
const editToggle = document.getElementById("editToggle");
const cancelEdit = document.getElementById("cancelEdit");
const formActions = document.getElementById("formActions");
const editableInputs = document.querySelectorAll(".ledger-value input:not([type='date']), .ledger-value input[type='date'], .ledger-value input[type='url']");

let originalValues = {};

function enterEditMode() {
    originalValues = {};
    editableInputs.forEach(input => {
        originalValues[input.name] = input.value;
        input.removeAttribute("readonly");
    });
    formActions.hidden = false;
    editToggle.hidden = true;
    editableInputs[0].focus();
}

function exitEditMode(restore) {
    editableInputs.forEach(input => {
        if (restore) input.value = originalValues[input.name];
        input.setAttribute("readonly", "true");
    });
    formActions.hidden = true;
    editToggle.hidden = false;
}

editToggle.addEventListener("click", enterEditMode);
cancelEdit.addEventListener("click", () => exitEditMode(true));

// ---- Avatar preview + upload ----
const avatarInput = document.getElementById("avatarInput");
const avatarPreview = document.getElementById("avatarPreview");
const avatarPlaceholder = document.getElementById("avatarPlaceholder");

avatarInput.addEventListener("change", function () {
    const file = this.files[0];
    if (!file) return;

    if (file.size > 5 * 1024 * 1024) {
        alert("Profile picture must be smaller than 5MB.");
        this.value = "";
        return;
    }

    const reader = new FileReader();
    reader.onload = function (e) {
        avatarPreview.src = e.target.result;
        avatarPreview.style.display = "block";
        if (avatarPlaceholder) avatarPlaceholder.style.display = "none";
    };
    reader.readAsDataURL(file);

    // A new photo was picked outside of "Edit profile" mode — submit immediately
    // so the change isn't lost, since the file input isn't gated by edit mode.
    document.getElementById("profileForm").submit();
});

// ---- Delete account modal ----
const deleteModal = document.getElementById("deleteModal");
const openDeleteModal = document.getElementById("openDeleteModal");
const cancelDelete = document.getElementById("cancelDelete");

openDeleteModal.addEventListener("click", () => { deleteModal.hidden = false; });
cancelDelete.addEventListener("click", () => { deleteModal.hidden = true; });
deleteModal.addEventListener("click", (e) => {
    if (e.target === deleteModal) deleteModal.hidden = true;
});