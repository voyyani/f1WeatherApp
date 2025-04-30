document.addEventListener('DOMContentLoaded', () => {
    const analysisForm = document.getElementById('analysisForm');
    const resultsSection = document.getElementById('results');
    const plotImage = document.getElementById('plot');
    const tempCorrElement = document.getElementById('tempCorr');
    const rainCorrElement = document.getElementById('rainCorr');
    const errorElement = document.getElementById('error');

    const toggleLoadingState = (isLoading) => {
        const btn = analysisForm.querySelector('button');
        btn.disabled = isLoading;
        btn.classList.toggle('loading', isLoading);
    };

    const resetUI = () => {
        resultsSection.classList.remove('visible');
        plotImage.src = '';
        tempCorrElement.textContent = '-';
        rainCorrElement.textContent = '-';
        errorElement.textContent = '';
    };

    const displayError = (message) => {
        errorElement.textContent = message;
        errorElement.style.display = 'block';
        setTimeout(() => errorElement.style.display = 'none', 5000);
    };

    const handleFormSubmission = async (event) => {
        event.preventDefault();
        resetUI();
        toggleLoadingState(true);

        const formData = {
            year: parseInt(event.target.year.value),
            gp: event.target.gp.value.trim(),
            driver: event.target.driver.value.trim().toUpperCase(),
            session_type: event.target.session_type.value
        };

        try {
            if (!formData.year || formData.year < 1950 || formData.year > new Date().getFullYear()) {
                throw new Error('Invalid year (1950-current)');
            }
            if (!formData.gp) throw new Error('Grand Prix required');
            if (!formData.driver || formData.driver.length !== 3) throw new Error('3-letter driver code required');

            const response = await fetch('/analyze', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(formData)
            });

            const data = await response.json();
            if (!response.ok) throw new Error(data.error || 'Analysis failed');

            plotImage.src = `data:image/png;base64,${data.plot}`;
            tempCorrElement.textContent = data.temp_corr?.toFixed(2) || 'N/A';
            rainCorrElement.textContent = data.rain_corr?.toFixed(2) || 'N/A';
            resultsSection.classList.add('visible');
            resultsSection.scrollIntoView({ behavior: 'smooth' });

        } catch (error) {
            displayError(error.message);
            console.error('Error:', error);
        } finally {
            toggleLoadingState(false);
        }
    };

    analysisForm.addEventListener('submit', handleFormSubmission);
    
    // Input validations
    analysisForm.driver.addEventListener('input', (e) => {
        e.target.value = e.target.value.toUpperCase().replace(/[^A-Z]/g, '').slice(0, 3);
    });
    analysisForm.year.addEventListener('input', (e) => {
        e.target.value = e.target.value.replace(/\D/g, '').slice(0, 4);
    });
});