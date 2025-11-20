document.addEventListener('DOMContentLoaded', () => {
    fetchStats();
    fetchBacktests();

    document.getElementById('refresh-btn').addEventListener('click', () => {
        fetchStats();
        fetchBacktests();
    });
});

async function fetchStats() {
    try {
        const response = await fetch('/api/stats');
        const data = await response.json();

        document.getElementById('total-backtests').textContent = data.total_backtests || 0;
        document.getElementById('unique-strategies').textContent = data.unique_strategies || 0;
        document.getElementById('avg-return').textContent = (data.avg_return || 0) + '%';
        document.getElementById('avg-sortino').textContent = data.avg_sortino || 0;
    } catch (error) {
        console.error('Error fetching stats:', error);
    }
}

async function fetchBacktests() {
    try {
        const response = await fetch('/api/backtests');
        const result = await response.json();
        const data = result.data || [];

        const tbody = document.querySelector('#backtest-table tbody');
        tbody.innerHTML = '';

        data.forEach(row => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${row['Strategy Name'] || 'Unknown'}</td>
                <td class="${getColorClass(row['Return %'])}">${formatNumber(row['Return %'])}%</td>
                <td>${formatNumber(row['Sharpe Ratio'])}</td>
                <td>${formatNumber(row['Sortino Ratio'])}</td>
                <td class="text-red">${formatNumber(row['Max Drawdown %'])}%</td>
                <td>${row['Trades'] || 0}</td>
                <td>${row['Time'] || '-'}</td>
            `;
            tbody.appendChild(tr);
        });
    } catch (error) {
        console.error('Error fetching backtests:', error);
    }
}

function formatNumber(num) {
    if (num === null || num === undefined) return '-';
    return parseFloat(num).toFixed(2);
}

function getColorClass(value) {
    if (!value) return '';
    return parseFloat(value) >= 0 ? 'text-green' : 'text-red';
}
