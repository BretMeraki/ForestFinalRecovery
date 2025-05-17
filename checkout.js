document.addEventListener('DOMContentLoaded', () => {
    // Back button functionality
    const backButton = document.querySelector('.back-button');
    backButton.addEventListener('click', () => {
        window.history.back();
    });

    // Clickable sections
    const sections = ['shipping', 'delivery', 'payment', 'promos'];
    sections.forEach(section => {
        const element = document.querySelector(`.${section}`);
        element.addEventListener('click', () => {
            // Here you would typically navigate to the respective section's page
            console.log(`Navigating to ${section} section...`);
        });
    });

    // Place order button
    const placeOrderButton = document.querySelector('.place-order');
    placeOrderButton.addEventListener('click', () => {
        // Here you would typically handle the order placement
        console.log('Processing order...');
        
        // Example validation
        const shipping = document.querySelector('.shipping .placeholder');
        const payment = document.querySelector('.payment span');
        
        if (shipping.textContent === 'Add shipping address') {
            alert('Please add a shipping address before placing the order.');
            return;
        }
        
        if (payment.textContent === 'Add payment method') {
            alert('Please add a payment method before placing the order.');
            return;
        }
        
        // If validation passes, show confirmation
        alert('Order placed successfully!');
    });

    // Update time in status bar
    function updateTime() {
        const timeElement = document.querySelector('.time');
        const now = new Date();
        const hours = now.getHours().toString().padStart(2, '0');
        const minutes = now.getMinutes().toString().padStart(2, '0');
        timeElement.textContent = `${hours}:${minutes}`;
    }
    
    // Update time immediately and then every minute
    updateTime();
    setInterval(updateTime, 60000);

    // Calculate and update totals
    function updateTotals() {
        const prices = Array.from(document.querySelectorAll('.item .price'))
            .map(el => parseFloat(el.textContent.replace('$', '')));
        
        const subtotal = prices.reduce((sum, price) => sum + price, 0);
        const tax = subtotal * 0.1; // 10% tax rate
        const total = subtotal + tax;
        
        document.querySelector('.subtotal .amount').textContent = `$${subtotal.toFixed(2)}`;
        document.querySelector('.taxes .amount').textContent = `$${tax.toFixed(2)}`;
        document.querySelector('.total .amount').textContent = `$${total.toFixed(2)}`;
    }
    
    // Update totals on page load
    updateTotals();
}); 