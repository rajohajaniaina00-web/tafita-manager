
const passwordInput = document.getElementById("password");
const togglePassword = document.getElementById("toggle-password");

if (passwordInput && togglePassword) {
    togglePassword.addEventListener("click", () => {
        const isHidden = passwordInput.type === "password";

        passwordInput.type = isHidden ? "text" : "password";
        togglePassword.textContent = isHidden ? "Masquer" : "Afficher";
        togglePassword.setAttribute(
            "aria-label",
            isHidden ? "Masquer le mot de passe" : "Afficher le mot de passe"
        );
    });
}
