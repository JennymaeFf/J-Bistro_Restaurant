document.addEventListener("DOMContentLoaded", function () {
    const toastMessages = document.querySelectorAll(".toast-region .flash");

    toastMessages.forEach(function (toast) {
        window.setTimeout(function () {
            toast.classList.add("toast-hiding");
            window.setTimeout(function () {
                toast.remove();
            }, 300);
        }, 3000);
    });

    const deleteButtons = document.querySelectorAll(".confirm-delete");

    deleteButtons.forEach(function (button) {
        button.addEventListener("click", function (event) {
            const shouldDelete = window.confirm("Are you sure you want to delete this order?");
            if (!shouldDelete) {
                event.preventDefault();
            }
        });
    });

    const checkoutSlides = document.querySelectorAll(".checkout-carousel-slide");
    const checkoutDots = document.querySelectorAll(".checkout-carousel-dots span");
    const homeSlides = document.querySelectorAll(".home-carousel-slide");
    const homeDots = document.querySelectorAll(".home-carousel-dots span");

    if (checkoutSlides.length > 1) {
        let activeSlide = 0;

        window.setInterval(function () {
            checkoutSlides[activeSlide].classList.remove("active");
            if (checkoutDots[activeSlide]) {
                checkoutDots[activeSlide].classList.remove("active");
            }

            activeSlide = (activeSlide + 1) % checkoutSlides.length;

            checkoutSlides[activeSlide].classList.add("active");
            if (checkoutDots[activeSlide]) {
                checkoutDots[activeSlide].classList.add("active");
            }
        }, 3000);
    }

    if (homeSlides.length > 1) {
        let activeHomeSlide = 0;
        window.setInterval(function () {
            homeSlides[activeHomeSlide].classList.remove("active");
            if (homeDots[activeHomeSlide]) {
                homeDots[activeHomeSlide].classList.remove("active");
            }

            activeHomeSlide = (activeHomeSlide + 1) % homeSlides.length;
            homeSlides[activeHomeSlide].classList.add("active");
            if (homeDots[activeHomeSlide]) {
                homeDots[activeHomeSlide].classList.add("active");
            }
        }, 2000);
    }

    const checkoutForm = document.querySelector(".checkout-form");
    const paymentMethodInputs = document.querySelectorAll('input[name="payment_method"]');
    const gcashPanel = document.getElementById("gcashPaymentPanel");
    const bankPanel = document.getElementById("bankPaymentPanel");
    const gcashReference = document.getElementById("gcashReference");
    const bankReference = document.getElementById("bankReference");
    const paymentReferenceValue = document.getElementById("paymentReferenceValue");
    const bankRadios = document.querySelectorAll('input[name="payment_bank"]');
    const bankAccountPreview = document.getElementById("bankAccountPreview");
    const bankAccountName = document.getElementById("bankAccountName");
    const bankAccountNumber = document.getElementById("bankAccountNumber");
    const deliveryOptionInputs = document.querySelectorAll('input[name="delivery_option"]');
    const deliveryAddressInput = document.getElementById("deliveryAddress");

    function selectedDeliveryOption() {
        const selected = document.querySelector('input[name="delivery_option"]:checked');
        return selected ? selected.value : "Delivery";
    }

    function updateDeliveryOption() {
        const option = selectedDeliveryOption();
        const isDelivery = option === "Delivery";
        if (deliveryAddressInput) {
            deliveryAddressInput.required = isDelivery;
            deliveryAddressInput.placeholder = isDelivery
                ? "House no., street, barangay, city"
                : "Pickup selected (address optional)";
        }
    }

    function selectedPaymentMethod() {
        const selected = document.querySelector('input[name="payment_method"]:checked');
        return selected ? selected.value : "";
    }

    function updatePaymentDetails() {
        const method = selectedPaymentMethod();
        const isGcash = method === "GCash";
        const isBank = method === "Card";

        if (gcashPanel) gcashPanel.hidden = !isGcash;
        if (bankPanel) bankPanel.hidden = !isBank;

        if (gcashReference) {
            gcashReference.required = isGcash;
            if (!isGcash) gcashReference.value = "";
        }
        if (bankReference) {
            bankReference.required = isBank;
            if (!isBank) bankReference.value = "";
        }

        bankRadios.forEach(function (radio) {
            radio.required = isBank;
            radio.disabled = !isBank;
            if (!isBank) radio.checked = false;
        });

        if (!isBank && bankAccountPreview) {
            bankAccountPreview.hidden = true;
        }

        if (paymentReferenceValue) {
            paymentReferenceValue.value = isGcash && gcashReference
                ? gcashReference.value.trim()
                : isBank && bankReference
                    ? bankReference.value.trim()
                    : "";
        }
    }

    paymentMethodInputs.forEach(function (input) {
        input.addEventListener("change", updatePaymentDetails);
    });
    deliveryOptionInputs.forEach(function (input) {
        input.addEventListener("change", updateDeliveryOption);
    });

    [gcashReference, bankReference].forEach(function (input) {
        if (!input) return;
        input.addEventListener("input", updatePaymentDetails);
    });

    bankRadios.forEach(function (radio) {
        radio.addEventListener("change", function () {
            if (!bankAccountPreview || !bankAccountName || !bankAccountNumber) return;
            bankAccountName.textContent = radio.dataset.accountName || "J'Bistro Restaurant";
            bankAccountNumber.textContent = radio.dataset.accountNumber || "";
            bankAccountPreview.hidden = false;
        });
    });

    if (checkoutForm) {
        checkoutForm.addEventListener("submit", updatePaymentDetails);
        checkoutForm.addEventListener("submit", updateDeliveryOption);
        updatePaymentDetails();
        updateDeliveryOption();
    }

    const passwordToggleButtons = document.querySelectorAll(".password-toggle");

    passwordToggleButtons.forEach(function (button) {
        button.addEventListener("click", function () {
            const targetId = button.getAttribute("data-target");
            const target = document.getElementById(targetId);
            if (!target) return;

            const showPassword = target.type === "password";
            target.type = showPassword ? "text" : "password";
            button.setAttribute("aria-label", showPassword ? "Hide password" : "Show password");
            button.classList.toggle("is-visible", showPassword);
        });
    });

    const menuCards = document.querySelectorAll(".menu-item-card[data-id]");

    menuCards.forEach(function (card) {
        function openCardItem() {
            let sizes = null;
            try {
                sizes = card.dataset.sizes && card.dataset.sizes !== "null" ? JSON.parse(card.dataset.sizes) : null;
            } catch (error) {
                sizes = null;
            }

            openItemModal(
                card.dataset.id,
                card.dataset.name || "Menu Item",
                card.dataset.description || "",
                Number(card.dataset.price) || 0,
                card.dataset.category || "",
                sizes,
                card.dataset.image || "plogo.png",
                card.dataset.available !== "false"
            );
        }

        card.addEventListener("click", openCardItem);
        card.addEventListener("keydown", function (event) {
            if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                openCardItem();
            }
        });
    });

    const footerPanel = document.getElementById("footerMiniPanel");
    const footerPanelTitle = document.getElementById("footerMiniPanelTitle");
    const footerPanelBody = document.getElementById("footerMiniPanelBody");
    const footerPanelClose = document.getElementById("footerMiniPanelClose");
    const footerPanelTriggers = document.querySelectorAll(".footer-panel-trigger");

    function closeFooterPanel() {
        if (!footerPanel) return;
        footerPanel.hidden = true;
        footerPanel.classList.remove("is-visible");
    }

    footerPanelTriggers.forEach(function (trigger) {
        trigger.addEventListener("click", function () {
            if (!footerPanel || !footerPanelTitle || !footerPanelBody) return;

            footerPanelTitle.textContent = trigger.dataset.footerPanelTitle || "Details";
            footerPanelBody.textContent = trigger.dataset.footerPanelBody || "";
            footerPanel.hidden = false;

            window.requestAnimationFrame(function () {
                footerPanel.classList.add("is-visible");
            });
        });
    });

    if (footerPanelClose) {
        footerPanelClose.addEventListener("click", function (event) {
            event.preventDefault();
            event.stopPropagation();
            closeFooterPanel();
        });
    }

    if (footerPanel) {
        footerPanel.addEventListener("click", function (event) {
            if (event.target === footerPanel) {
                closeFooterPanel();
            }
        });
    }
});

// Modal functionality for menu items
let currentItem = null;

function openItemModal(id, name, description, price, category, sizes, image, isAvailable = true) {
    const numericPrice = Number(price) || 0;
    const safeImage = image || 'plogo.png';
    currentItem = { id, name, description, price: numericPrice, category, sizes, image: safeImage, isAvailable };
    
    const modal = document.getElementById('itemModal');
    const modalImage = document.getElementById('modalImage');
    const modalName = document.getElementById('modalName');
    const modalDescription = document.getElementById('modalDescription');
    const modalPrice = document.getElementById('modalPrice');
    const quantityDisplay = document.getElementById('quantity');

    if (!modal || !modalImage || !modalName || !modalDescription || !modalPrice || !quantityDisplay) return;

    modalImage.src = `/static/images/${safeImage}`;
    modalName.textContent = name;
    modalDescription.textContent = description;
    modalPrice.textContent = numericPrice.toFixed(2);
    quantityDisplay.textContent = '1';

    const availability = document.getElementById('modalAvailability');
    const addButton = document.getElementById('modalAddButton');
    if (availability) {
        availability.textContent = isAvailable ? 'Available' : 'Out of Stock';
        availability.classList.toggle('available', isAvailable);
        availability.classList.toggle('unavailable', !isAvailable);
    }
    if (addButton) {
        addButton.disabled = !isAvailable;
        addButton.textContent = isAvailable ? 'Add to Cart' : 'Out of Stock';
    }
    
    const sizeSelector = document.getElementById('sizeSelector');
    if (category === 'beverages' && sizes) {
        sizeSelector.style.display = 'block';
        updatePriceForSize('small');
    } else {
        sizeSelector.style.display = 'none';
    }
    
    modal.style.display = 'block';
}

function closeItemModal() {
    document.getElementById('itemModal').style.display = 'none';
    currentItem = null;
}

function changeQuantity(delta) {
    const quantityElement = document.getElementById('quantity');
    let quantity = parseInt(quantityElement.textContent);
    quantity = Math.max(1, quantity + delta);
    quantityElement.textContent = quantity;
    
    if (currentItem && currentItem.category === 'beverages' && currentItem.sizes) {
        const selectedSize = document.querySelector('input[name="size"]:checked').value;
        updatePriceForSize(selectedSize);
    }
}

function updatePriceForSize(size) {
    if (currentItem && currentItem.sizes && currentItem.sizes[size]) {
        const quantity = parseInt(document.getElementById('quantity').textContent);
        const basePrice = currentItem.sizes[size];
        document.getElementById('modalPrice').textContent = (basePrice * quantity).toFixed(2);
    }
}

document.addEventListener('change', function(e) {
    if (e.target.name === 'size') {
        updatePriceForSize(e.target.value);
    }
});

function addToCart() {
    if (!currentItem) return;
    if (currentItem.isAvailable === false) return;
    
    const quantity = parseInt(document.getElementById('quantity').textContent);
    let size = null;
    let price = currentItem.price;
    
    if (currentItem.category === 'beverages' && currentItem.sizes) {
        size = document.querySelector('input[name="size"]:checked').value;
        price = currentItem.sizes[size];
    }
    
    // Create form and submit
    const form = document.createElement('form');
    form.method = 'POST';
    form.action = `/cart/add/${currentItem.id}`;
    
    const quantityInput = document.createElement('input');
    quantityInput.type = 'hidden';
    quantityInput.name = 'quantity';
    quantityInput.value = quantity;
    form.appendChild(quantityInput);
    
    if (size) {
        const sizeInput = document.createElement('input');
        sizeInput.type = 'hidden';
        sizeInput.name = 'size';
        sizeInput.value = size;
        form.appendChild(sizeInput);
        
        const priceInput = document.createElement('input');
        priceInput.type = 'hidden';
        priceInput.name = 'price';
        priceInput.value = price;
        form.appendChild(priceInput);
    }
    
    document.body.appendChild(form);
    form.submit();
    
    closeItemModal();
}

// Close modal when clicking outside
window.onclick = function(event) {
    const modal = document.getElementById('itemModal');
    if (event.target == modal) {
        closeItemModal();
    }
}
