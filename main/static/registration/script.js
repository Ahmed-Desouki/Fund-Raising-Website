// Translated messages come from register.html; fall back to English if missing
const T = Object.assign({
    show: "Show", hide: "Hide",
    pictureTooBig: "Profile picture must be smaller than 5MB.",
    invalidEmail: "Please enter a valid email address.",
    weakPassword: "Password must be at least 8 characters and include an uppercase letter, a lowercase letter, and a special character.",
    passwordsDontMatch: "Passwords do not match.",
    invalidMobile: "Enter a valid mobile number (e.g. 01012345678).",
    somethingWrong: "Something went wrong. Please try again.",
}, window.I18N || {});

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
            this.textContent = T.hide;
        } else {
            input.type = "password";
            this.textContent = T.show;
        }
    });
});

const profilePicture = document.getElementById("profilePicture");

profilePicture.addEventListener("change", function() {
    const file = this.files[0];

    if (!file) return;

    if (file.size > 5 * 1024 * 1024) {
        alert(T.pictureTooBig);
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

// ---- CSRF helper: reads the token from the {% csrf_token %} hidden input you added after <body> ----
function getCSRFToken() {
    // Prefer the cookie: it's rotated on every login/logout (even from another tab),
    // while the hidden input keeps the value from when this page was loaded
    const cookie = document.cookie.split("; ").find(c => c.startsWith("csrftoken="));
    return cookie ? decodeURIComponent(cookie.split("=")[1]) : document.querySelector('input[name="csrfmiddlewaretoken"]').value;
}

document.getElementById("registerForm").addEventListener("submit", async function(e) {
    e.preventDefault();

    const email = document.getElementById("email");
    const password = document.getElementById("password");
    const confirmPassword = document.getElementById("confirmPassword");
    const mobile_Number = document.getElementById("mobileNumber");

    document.getElementById("emailError").textContent = "";
    document.getElementById("passwordError").textContent = "";
    document.getElementById("mobileError").textContent = "";

    let valid = true;

    if (!email.validity.valid) {
        document.getElementById("emailError").textContent = T.invalidEmail;
        valid = false;
    }

    const passwordPattern = /^(?=.*[a-z])(?=.*[A-Z])(?=.*[!@#$%^&*(),.?":{}|<>_\-+=~`[\];'/\\]).{8,}$/;
    if (!passwordPattern.test(password.value)) {
        document.getElementById("passwordError").textContent = T.weakPassword;
        valid = false;
    } else if (password.value !== confirmPassword.value) {
        document.getElementById("passwordError").textContent = T.passwordsDontMatch;
        valid = false;
    }

    const mobilePattern = /^(010|011|012|015)[0-9]{8}$/;
    if (!mobilePattern.test(mobile_Number.value)) {
        document.getElementById("mobileError").textContent = T.invalidMobile;
        valid = false;
    }

    if (!valid) return;

    const form = document.getElementById("registerForm");
    const formData = new FormData(form);

    formData.set("email", email.value);
    formData.set("password1", password.value);
    formData.set("password2", confirmPassword.value);
    formData.set("mobile_number", mobile_Number.value);

    const firstName = document.getElementById("firstName");
    const lastName = document.getElementById("lastName");
    formData.set("first_name", firstName.value);
    formData.set("last_name", lastName.value);

    if (profilePicture.files[0]) {
        formData.set("profile_picture", profilePicture.files[0]);
    }

    // A double click used to send the form twice, creating the account twice and two emails
    const submitButton = form.querySelector('button[type="submit"]');
    if (submitButton.disabled) return;
    submitButton.disabled = true;

    try {
        const response = await fetch("/api/register/", {
            method: "POST",
            headers: { "X-CSRFToken": getCSRFToken() },
            body: formData,
        });
        const result = await response.json();

        if (result.success) {
            registerForm.reset();
            alert(result.message);
            loginPage.classList.remove("hidden");
            registerPage.classList.add("hidden");
        } else {
            if (result.errors.email) {
                document.getElementById("emailError").textContent = result.errors.email[0];
            }
            if (result.errors.mobile_number) {
                document.getElementById("mobileError").textContent = result.errors.mobile_number[0];
            }
            if (result.errors.password1) {
                document.getElementById("passwordError").textContent = result.errors.password1[0];
            } else if (result.errors.password2) {
                document.getElementById("passwordError").textContent = result.errors.password2[0];
            }
        }
    } catch (err) {
        alert(T.somethingWrong);
    } finally {
        submitButton.disabled = false;
    }
});

document.getElementById("loginForm").addEventListener("submit", async function(e) {
    e.preventDefault();

    const loginForm = this;
    const email = document.getElementById("loginEmail").value;
    const password = document.getElementById("loginPassword").value;

    const submitButton = loginForm.querySelector('button[type="submit"]');
    if (submitButton.disabled) return;
    submitButton.disabled = true;

    try {
        const response = await fetch("/api/login/", {
            method: "POST",
            headers: {
                "X-CSRFToken": getCSRFToken(),
                "Content-Type": "application/x-www-form-urlencoded",
            },
            body: new URLSearchParams({ email, password }),
        });
        const result = await response.json();

        if (result.success) {
            window.location.href = result.redirect_url;
            return;  // keep the button disabled while the next page loads
        } else {
            alert(result.error);
        }
    } catch (err) {
        alert(T.somethingWrong);
    }
    submitButton.disabled = false;
});