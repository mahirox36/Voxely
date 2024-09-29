document.querySelector('.expandable-button').addEventListener('click', function() {
    this.classList.toggle('active');
    let subButtons = this.querySelector('.sub-buttons');
    subButtons.classList.toggle('show');});

document.querySelectorAll('.sub-button').forEach(button => {
    button.addEventListener('click', function(e) {
        let ripple = document.createElement('span');
        ripple.classList.add('ripple');
        this.appendChild(ripple);
        let x = e.clientX - e.target.offsetLeft;
        let y = e.clientY - e.target.offsetTop;
        ripple.style.left = `${x}px`;
        ripple.style.top = `${y}px`;
        setTimeout(() => {
            ripple.remove();
        }, 600);
    });
});