"use strict";

document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll("form.delete-form").forEach(function (form) {
        form.addEventListener("submit", function (event) {
            const memberName = (form.dataset.memberName || "").trim();

            const message = memberName
                ? `Confirmer la suppression du membre « ${memberName} » ? Cette action est définitive.`
                : "Confirmer la suppression de ce membre ? Cette action est définitive.";

            if (!window.confirm(message)) {
                event.preventDefault();
            }
        });
    });
});
