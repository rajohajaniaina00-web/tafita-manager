
document.addEventListener("DOMContentLoaded", () => {
    const deleteForms = document.querySelectorAll(".delete-form");

    deleteForms.forEach((form) => {
        form.addEventListener("submit", (event) => {
            const memberName = form.dataset.memberName || "ce membre";

            const confirmed = window.confirm(
                `Voulez-vous vraiment supprimer ${memberName} ? Cette action est définitive.`
            );

            if (!confirmed) {
                event.preventDefault();
            }
        });
    });
});
