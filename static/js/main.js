document.addEventListener("DOMContentLoaded", function () {
    const deleteButtons = document.querySelectorAll(".confirm-delete");

    deleteButtons.forEach(function (button) {
        button.addEventListener("click", function (event) {
            const shouldDelete = window.confirm("Are you sure you want to delete this order?");
            if (!shouldDelete) {
                event.preventDefault();
            }
        });
    });
});
