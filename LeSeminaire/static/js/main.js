// main.js - Fonctionnalités JavaScript pour LeSéminaire[BOT]

document.addEventListener('DOMContentLoaded', function() {
    // Initialisation des tooltips Bootstrap
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Initialisation des popovers Bootstrap
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function(popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
    
    // Animation au défilement
    const animateElements = document.querySelectorAll('.animate-on-scroll');
    
    function checkIfInView() {
        const windowHeight = window.innerHeight;
        const windowTopPosition = window.scrollY;
        const windowBottomPosition = windowTopPosition + windowHeight;
        
        animateElements.forEach(function(element) {
            const elementHeight = element.offsetHeight;
            const elementTopPosition = element.offsetTop;
            const elementBottomPosition = elementTopPosition + elementHeight;
            
            // Vérifier si l'élément est visible
            if (
                (elementBottomPosition >= windowTopPosition) &&
                (elementTopPosition <= windowBottomPosition)
            ) {
                element.classList.add('animated');
            }
        });
    }
    
    // Vérifier au chargement et au défilement
    window.addEventListener('scroll', checkIfInView);
    window.addEventListener('resize', checkIfInView);
    window.addEventListener('load', checkIfInView);
    
    // Code pour les formulaires
    const forms = document.querySelectorAll('form');
    
    forms.forEach(function(form) {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            } else {
                // Si c'est le formulaire de contact
                if (form.id === 'contactForm') {
                    event.preventDefault();
                    
                    // Simulation d'envoi de formulaire
                    const submitButton = form.querySelector('button[type="submit"]');
                    const originalText = submitButton.innerHTML;
                    
                    submitButton.disabled = true;
                    submitButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Envoi en cours...';
                    
                    // Simuler un délai d'envoi
                    setTimeout(function() {
                        // Créer une alerte de succès
                        const alertDiv = document.createElement('div');
                        alertDiv.className = 'alert alert-success alert-dismissible fade show mt-3';
                        alertDiv.setAttribute('role', 'alert');
                        alertDiv.innerHTML = `
                            <strong>Message envoyé avec succès!</strong> Nous vous répondrons dans les plus brefs délais.
                            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                        `;
                        
                        // Insérer l'alerte après le formulaire
                        form.parentNode.insertBefore(alertDiv, form.nextSibling);
                        
                        // Réinitialiser le formulaire et le bouton
                        form.reset();
                        submitButton.disabled = false;
                        submitButton.innerHTML = originalText;
                        
                        // Faire disparaître l'alerte après 5 secondes
                        setTimeout(function() {
                            alertDiv.classList.remove('show');
                            setTimeout(function() {
                                alertDiv.remove();
                            }, 150);
                        }, 5000);
                    }, 1500);
                }
            }
            
            form.classList.add('was-validated');
        }, false);
    });
    
    // Fonction pour copier les commandes dans le presse-papier
    const copyButtons = document.querySelectorAll('.copy-command');
    
    copyButtons.forEach(function(button) {
        button.addEventListener('click', function() {
            const commandText = this.previousElementSibling.textContent;
            navigator.clipboard.writeText(commandText).then(function() {
                const originalTooltip = button.getAttribute('title');
                
                // Changer le tooltip
                button.setAttribute('title', 'Copié!');
                const tooltip = bootstrap.Tooltip.getInstance(button);
                if (tooltip) {
                    tooltip.dispose();
                }
                new bootstrap.Tooltip(button).show();
                
                // Restaurer le tooltip original
                setTimeout(function() {
                    button.setAttribute('title', originalTooltip);
                    const newTooltip = bootstrap.Tooltip.getInstance(button);
                    if (newTooltip) {
                        newTooltip.dispose();
                    }
                    new bootstrap.Tooltip(button);
                }, 1500);
            });
        });
    });
    
    // Gestion des accordéons
    const accordionLinks = document.querySelectorAll('.accordion-link');
    
    accordionLinks.forEach(function(link) {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            
            const targetId = this.getAttribute('data-target');
            const targetAccordion = document.querySelector(targetId);
            
            if (targetAccordion) {
                // Fermer tous les accordéons
                const accordionButtons = document.querySelectorAll('.accordion-button');
                accordionButtons.forEach(function(btn) {
                    if (!btn.classList.contains('collapsed')) {
                        btn.click();
                    }
                });
                
                // Ouvrir l'accordéon cible
                const targetButton = targetAccordion.querySelector('.accordion-button');
                if (targetButton.classList.contains('collapsed')) {
                    targetButton.click();
                }
                
                // Faire défiler jusqu'à l'accordéon
                targetAccordion.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
        });
    });
});