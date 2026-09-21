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

// ---- CSRF helper: reads the token from the {% csrf_token %} hidden input you added after <body> ----
function getCSRFToken() {
    return document.querySelector('input[name="csrfmiddlewaretoken"]').value;
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
        document.getElementById("emailError").textContent = "Please enter a valid email address.";
        valid = false;
    }

    const passwordPattern = /^(?=.*[a-z])(?=.*[A-Z])(?=.*[!@#$%^&*(),.?":{}|<>_\-+=~`[\];'/\\]).{8,}$/;
    if (!passwordPattern.test(password.value)) {
        document.getElementById("passwordError").textContent =
            "Password must be at least 8 characters and include an uppercase letter, a lowercase letter, and a special character.";
        valid = false;
    } else if (password.value !== confirmPassword.value) {
        document.getElementById("passwordError").textContent = "Passwords do not match.";
        valid = false;
    }

    const mobilePattern = /^(010|011|012|015)[0-9]{8}$/;
    if (!mobilePattern.test(mobile_Number.value)) {
        document.getElementById("mobileError").textContent = "Enter a valid mobile number (e.g. 01012345678).";
        valid = false;
    }

    if (!valid) return;

    const form = document.getElementById("registerForm");
    const formData = new FormData(form);

    formData.set("email", email.value);
    formData.set("password1", password.value);
    formData.set("password2", confirmPassword.value);
    formData.set("mobile_number", mobile_Number.value);

    const firstName = form.querySelector('input[placeholder="Enter your first name"]');
    const lastName = form.querySelector('input[placeholder="Enter your last name"]');
    formData.set("first_name", firstName.value);
    formData.set("last_name", lastName.value);

    if (profilePicture.files[0]) {
        formData.set("profile_picture", profilePicture.files[0]);
    }

    try {
        console.log("mobile_number value:", mobile_Number.value);
        console.log("FormData mobile_number:", formData.get("mobile_number"));
        const response = await fetch("/api/register/", {
            method: "POST",
            headers: { "X-CSRFToken": getCSRFToken() },
            body: formData,
        });
        const result = await response.json();
        console.log("Register error:", result); // remove once confirmed working

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
        alert("Something went wrong. Please try again.");
    }
});

document.getElementById("loginForm").addEventListener("submit", async function(e) {
    e.preventDefault();

    const loginForm = this;
    const email = loginForm.querySelector('input[type="email"]').value;
    const password = document.getElementById("loginPassword").value;

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
        } else {
            alert(result.error);
        }
    } catch (err) {
        alert("Something went wrong. Please try again.");
    }
});