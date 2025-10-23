/**
 * use to check the password input, if the new password is the same as the old password, then show the error message
 */
function checkOldPasswordMatch() {
    var oldPasswordInput = document.getElementById("old-password-input");
    var passwordInput = document.getElementById("password-input");
    var errorMessage = document.getElementById("password-input-error");

    if (oldPasswordInput && passwordInput) {
        var oldPassword = oldPasswordInput.value;
        var password = passwordInput.value;

        if (password === oldPassword) {
            passwordInput.classList.add("is-invalid");
            errorMessage.innerHTML = "New password cannot be the same as the old password.";
            passwordInput.setCustomValidity("New password cannot be the same as the old password.");
        } else {
            passwordInput.classList.remove("is-invalid");
            errorMessage.innerHTML = "";
            passwordInput.setCustomValidity("");
        }
    }
}

/**
 * Check if the confirm password matches the new password, and display an error message if they do not match.
 */
function checkPasswordMatch() {
    var passwordInput = document.getElementById("password-input");
    var confirmPasswordInput = document.getElementById("confirm-password-input");
    var errorMessage = document.getElementById("confirm-password-input-error");

    if (passwordInput && confirmPasswordInput) {
        var password = passwordInput.value;
        var confirmPassword = confirmPasswordInput.value;

        if (password !== confirmPassword) {
            confirmPasswordInput.classList.add("is-invalid");
            errorMessage.innerHTML = "Passwords do not match.";
            confirmPasswordInput.setCustomValidity("Passwords do not match.");
        } else {
            confirmPasswordInput.classList.remove("is-invalid");
            errorMessage.innerHTML = "";
            confirmPasswordInput.setCustomValidity("");
        }
    }
}

/**
 * Check if the password meets the required pattern.
 * @param id - the id of the password input field
 */
function pattern(id) {
    var passwordInput = document.getElementById(id);
    var password = passwordInput.value;
    var regex = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)[A-Za-z\d\W_]{8,20}$/;
    var errorMessage = document.getElementById(id + "-error");

    if (regex.test(password)) {
        passwordInput.classList.remove("is-invalid");
        passwordInput.setCustomValidity("");
        errorMessage.innerHTML = "";
    } else {
        passwordInput.classList.add("is-invalid");
        passwordInput.setCustomValidity("Password must be 8-20 characters long, contain at least one uppercase letter, one lowercase letter, and one number. ");
        errorMessage.innerHTML = "Password must be 8-20 characters long, contain at least one uppercase letter, one lowercase letter, and one number. ";
    }
}

// listen to input event on password fields
document.addEventListener("DOMContentLoaded", function () {
    var oldPasswordInput = document.getElementById("old-password-input");
    var passwordInput = document.getElementById("password-input");
    var confirmPasswordInput = document.getElementById("confirm-password-input");

    if (oldPasswordInput) {
        oldPasswordInput.addEventListener("input", function () {
            pattern("old-password-input");
        });
    }

    if (passwordInput) {
        passwordInput.addEventListener("input", function () {
            pattern("password-input");
            checkOldPasswordMatch();
            checkPasswordMatch();
        });
    }

    if (confirmPasswordInput) {
        confirmPasswordInput.addEventListener("input", function () {
            checkPasswordMatch();
        });
    }
});