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
});

// Modal functionality for menu items
let currentItem = null;

function openItemModal(id, name, description, price, category, sizes, image) {
    currentItem = { id, name, description, price, category, sizes, image };
    
    document.getElementById('modalImage').src = `/static/images/${image}`;
    document.getElementById('modalName').textContent = name;
    document.getElementById('modalDescription').textContent = description;
    document.getElementById('modalPrice').textContent = price.toFixed(2);
    document.getElementById('quantity').textContent = '1';
    
    const sizeSelector = document.getElementById('sizeSelector');
    if (category === 'beverages' && sizes) {
        sizeSelector.style.display = 'block';
        updatePriceForSize('small');
    } else {
        sizeSelector.style.display = 'none';
    }
    
    document.getElementById('itemModal').style.display = 'block';
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
