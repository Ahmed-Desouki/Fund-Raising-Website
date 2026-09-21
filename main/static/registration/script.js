const registerPage = document.getElementById("registerPage");
const loginPage = document.getElementById("loginPage");

document.getElementById("loginLink").addEventListener("click", function(e) {
    e.preventDefault();
    registerPage.classList.add("hidden");
    loginPage.classList.remove("hidden");
});

document.getElementById("registerLink").addEventListener("click", function(e) {
    e.preventDefault();
    loginPage.classList.add("hidden");
    registerPage.classList.remove("hidden");
});

document.querySelectorAll(".show-password").forEach(button => {
    button.addEventListener("click", function() {
        const input = document.getElementById(this.dataset.target);

        if (input.type === "password") {
            input.type = "text";
            this.textContent = "Hide";
        } else {
            input.type = "password";
            this.textContent = "Show";
        }
    });
});

const profilePicture = document.getElementById("profilePicture");

profilePicture.addEventListener("change", function() {
    const file = this.files[0];

    if (!file) return;

    if (file.size > 5 * 1024 * 1024) {
        alert("Profile picture must be smaller than 5MB.");
        this.value = "";
        return;
    }

    const reader = new FileReader();

    reader.onload = function(e) {
        document.getElementById("profilePreview").src = e.target.result;
        document.getElementById("profilePreview").style.display = "block";
        document.getElementById("profileIcon").style.display = "none";
    };

    reader.readAsDataURL(file);
});

document.getElementById("registerForm").addEventListener("submit", function(e) {
    e.preventDefault();

    const email = document.getElementById("email");
    const password = document.getElementById("password");
    const confirmPassword = document.getElementById("confirmPassword");

    document.getElementById("emailError").textContent = "";
    document.getElementById("passwordError").textContent = "";

    let valid = true;

    if (!email.validity.valid) {
        document.getElementById("emailError").textContent = "Please enter a valid email address.";
        valid = false;
    }

    if (password.value.length < 8) {
        document.getElementById("passwordError").textContent = "Password must be at least 8 characters.";
        valid = false;
    }

    if (password.value !== confirmPassword.value) {
        document.getElementById("passwordError").textContent = "Passwords do not match.";
        valid = false;
    }

    if (valid) {
        alert("Account created successfully!");
    }
});

document.getElementById("loginForm").addEventListener("submit", function(e) {
    e.preventDefault();
    alert("Login submitted!");
});
