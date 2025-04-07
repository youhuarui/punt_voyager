// 页面加载完成后执行
document.addEventListener('DOMContentLoaded', function() {
    // 初始化单航段模拟界面
    initSingleVoyageSimulation();
    
    // 初始化多段中转模拟界面
    initMultiSegmentSimulation();
    
    // 初始化批量模拟界面
    initBatchSimulation();
});

// 单航段模拟相关函数
function initSingleVoyageSimulation() {
    // 获取DOM元素
    const simulateBtn = document.getElementById('singleSimulateBtn');
    const startPortSelect = document.getElementById('startPort');
    const endPortSelect = document.getElementById('endPort');
    const departureMonthSelect = document.getElementById('departureMonth');
    const shipSpeedInput = document.getElementById('shipSpeed');
    const windFactorMinInput = document.getElementById('windFactorMin');
    const windFactorMaxInput = document.getElementById('windFactorMax');
    const returnVoyageCheckbox = document.getElementById('returnVoyage');
    const resultSummary = document.getElementById('singleResultSummary');
    const chartCard = document.getElementById('singleChartCard');
    const mapCard = document.getElementById('singleMapCard');
    const downloadCSVBtn = document.getElementById('singleDownloadCSV');

    // 为模拟按钮添加点击事件
    simulateBtn.addEventListener('click', function() {
        // 检查输入
        if (startPortSelect.value === endPortSelect.value) {
            alert('起点和终点不能是同一个港口！');
            return;
        }
        
        // 检查风速因子范围
        if (parseFloat(windFactorMinInput.value) >= parseFloat(windFactorMaxInput.value)) {
            alert('风速最小影响系数必须小于最大影响系数！');
            return;
        }
        
        // 禁用按钮，显示加载状态
        simulateBtn.disabled = true;
        simulateBtn.innerHTML = '<span class="loading"></span> 模拟中...';
        
        // 获取表单数据
        const formData = {
            start_port: startPortSelect.value,
            end_port: endPortSelect.value,
            departure_month: departureMonthSelect.value,
            ship_speed: shipSpeedInput.value,
            wind_factor_min: windFactorMinInput.value,
            wind_factor_max: windFactorMaxInput.value,
            return_voyage: returnVoyageCheckbox.checked
        };
        
        // 发送AJAX请求
        fetch('/simulate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(formData)
        })
        .then(response => response.json())
        .then(data => {
            // 更新结果摘要
            document.getElementById('singleTotalDistance').textContent = `${Math.round(data.total_distance)} 公里`;
            document.getElementById('singleTotalDays').textContent = `${data.total_days} 天`;
            document.getElementById('singleOutboundDays').textContent = `${data.outbound_days} 天`;
            document.getElementById('singleWaitingDays').textContent = `${data.waiting_days} 天`;
            document.getElementById('singleReturnDays').textContent = `${data.return_days} 天`;
            
            // 显示图表
            document.getElementById('singleVoyageChart').src = `data:image/png;base64,${data.chart_data}`;
            
            // 显示地图
            document.getElementById('singleVoyageMap').innerHTML = data.map_html;
            
            // 显示线性航线图
            if (data.linear_chart_data) {
                document.getElementById('singleLinearChart').src = `data:image/png;base64,${data.linear_chart_data}`;
                document.getElementById('singleLinearChartCard').style.display = 'block';
            }
            
            // 填充每日航行日志表格
            const dailyData = parseCSV(data.csv_data);
            fillDailyLogTable('singleDailyLogTable', dailyData);
            
            // 存储CSV数据以供下载
            window.singleCsvData = data.csv_data;
            
            // 显示结果区域
            resultSummary.style.display = 'block';
            chartCard.style.display = 'block';
            mapCard.style.display = 'block';
            document.getElementById('singleDailyLogCard').style.display = 'block';
        })
        .catch(error => {
            console.error('Error:', error);
            alert('模拟请求失败，请重试！');
        })
        .finally(() => {
            // 恢复按钮状态
            simulateBtn.disabled = false;
            simulateBtn.innerHTML = '<i class="fas fa-play"></i> 开始模拟';
        });
    });
    
    // 为下载CSV按钮添加点击事件
    downloadCSVBtn.addEventListener('click', function() {
        downloadCSV(window.singleCsvData, 'punt_voyage_simulation.csv');
    });
    
    // 防止起点和终点选择相同的港口
    startPortSelect.addEventListener('change', function() {
        checkSamePort(startPortSelect, endPortSelect, simulateBtn);
    });
    
    endPortSelect.addEventListener('change', function() {
        checkSamePort(startPortSelect, endPortSelect, simulateBtn);
    });
}

// 解析CSV数据为数组对象
function parseCSV(csvData) {
    const lines = csvData.split('\n');
    const headers = lines[0].split(',');
    const result = [];
    
    for (let i = 1; i < lines.length; i++) {
        if (lines[i].trim() === '') continue;
        
        const values = lines[i].split(',');
        const entry = {};
        
        for (let j = 0; j < headers.length; j++) {
            entry[headers[j]] = values[j];
        }
        
        result.push(entry);
    }
    
    return result;
}

// 填充每日航行日志表格
function fillDailyLogTable(tableId, data) {
    const tbody = document.getElementById(tableId).getElementsByTagName('tbody')[0];
    tbody.innerHTML = ''; // 清空表格
    
    data.forEach(row => {
        const tr = document.createElement('tr');
        
        // 添加每一列
        tr.innerHTML = `
            <td>${row.Day}</td>
            <td>${row.Segment}</td>
            <td>${row.Direction}</td>
            <td>${parseFloat(row['Distance (km)']).toFixed(1)}</td>
            <td>${parseFloat(row['Accumulated (km)']).toFixed(1)}</td>
            <td>${row['Wind Effect']}</td>
        `;
        
        // 根据航段类型添加不同的样式
        if (row.Direction.includes('Waiting')) {
            tr.classList.add('table-warning');
        } else if (row.Direction.includes('Return')) {
            tr.classList.add('table-info');
        }
        
        tbody.appendChild(tr);
    });
}

// 多段中转模拟相关函数
function initMultiSegmentSimulation() {
    const portsSequenceContainer = document.getElementById('portsSequenceContainer');
    const addPortBtn = document.getElementById('addPortBtn');
    const multiSimulateBtn = document.getElementById('multiSimulateBtn');
    const multiDepartureMonthSelect = document.getElementById('multiDepartureMonth');
    const multiShipSpeedInput = document.getElementById('multiShipSpeed');
    const multiWindFactorMinInput = document.getElementById('multiWindFactorMin');
    const multiWindFactorMaxInput = document.getElementById('multiWindFactorMax');
    const multiReturnVoyageCheckbox = document.getElementById('multiReturnVoyage');
    const multiResultSummary = document.getElementById('multiResultSummary');
    const multiChartCard = document.getElementById('multiChartCard');
    const multiMapCard = document.getElementById('multiMapCard');
    const multiDownloadCSVBtn = document.getElementById('multiDownloadCSV');
    
    // 添加最初的终点港口输入
    addPortInput(portsSequenceContainer, '终点');
    
    // 为添加中转点按钮添加点击事件
    addPortBtn.addEventListener('click', function() {
        // 获取当前所有港口输入
        const portInputs = portsSequenceContainer.querySelectorAll('.input-group');
        const lastInput = portInputs[portInputs.length - 1];
        
        // 修改最后一个输入的标签
        const label = lastInput.querySelector('.input-group-text');
        if (label.textContent === '终点') {
            label.textContent = '中转';
        }
        
        // 在最后添加新的终点输入
        addPortInput(portsSequenceContainer, '终点');
    });
    
    // 为模拟按钮添加点击事件
    multiSimulateBtn.addEventListener('click', function() {
        // 获取所有港口选择
        const portSelects = portsSequenceContainer.querySelectorAll('.port-select');
        const portsSequence = Array.from(portSelects).map(select => select.value);
        
        // 检查是否有连续相同的港口
        for (let i = 0; i < portsSequence.length - 1; i++) {
            if (portsSequence[i] === portsSequence[i + 1]) {
                alert('连续的港口不能相同！');
                return;
            }
        }
        
        // 检查风速因子范围
        if (parseFloat(multiWindFactorMinInput.value) >= parseFloat(multiWindFactorMaxInput.value)) {
            alert('风速最小影响系数必须小于最大影响系数！');
            return;
        }
        
        // 禁用按钮，显示加载状态
        multiSimulateBtn.disabled = true;
        multiSimulateBtn.innerHTML = '<span class="loading"></span> 模拟中...';
        
        // 准备数据
        const formData = {
            ports_sequence: portsSequence,
            departure_month: multiDepartureMonthSelect.value,
            ship_speed: multiShipSpeedInput.value,
            wind_factor_min: multiWindFactorMinInput.value,
            wind_factor_max: multiWindFactorMaxInput.value,
            return_voyage: multiReturnVoyageCheckbox.checked
        };
        
        // 发送请求
        fetch('/simulate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(formData)
        })
        .then(response => response.json())
        .then(data => {
            // 更新结果摘要
            document.getElementById('multiTotalDistance').textContent = `${Math.round(data.total_distance)} 公里`;
            document.getElementById('multiTotalDays').textContent = `${data.total_days} 天`;
            
            // 显示详细航行数据
            if (data.has_return) {
                // 返航相关数据
                document.getElementById('multiOutboundDistance').textContent = `${Math.round(data.outbound_distance)} 公里`;
                document.getElementById('multiReturnDistance').textContent = `${Math.round(data.return_distance)} 公里`;
                document.getElementById('multiOutboundDays').textContent = `${data.outbound_days} 天`;
                document.getElementById('multiReturnDays').textContent = `${data.return_days} 天`;
            } else {
                // 无返航时显示默认值
                document.getElementById('multiOutboundDistance').textContent = `${Math.round(data.total_distance)} 公里`;
                document.getElementById('multiReturnDistance').textContent = `0 公里`;
                document.getElementById('multiOutboundDays').textContent = `${data.total_days} 天`;
                document.getElementById('multiReturnDays').textContent = `0 天`;
            }
            
            document.getElementById('multiWaitingDays').textContent = `${data.waiting_days} 天`;
            document.getElementById('multiTotalTime').textContent = `${data.total_days + data.total_waiting_days} 天`;
            
            // 显示图表
            document.getElementById('multiVoyageChart').src = `data:image/png;base64,${data.chart_data}`;
            
            // 显示地图
            document.getElementById('multiVoyageMap').innerHTML = data.map_html;
            
            // 显示线性航线图
            if (data.linear_chart_data) {
                document.getElementById('multiLinearChart').src = `data:image/png;base64,${data.linear_chart_data}`;
                document.getElementById('multiLinearChartCard').style.display = 'block';
            }
            
            // 填充每日航行日志表格
            const multiDailyData = parseCSV(data.csv_data);
            fillDailyLogTable('multiDailyLogTable', multiDailyData);
            
            // 存储CSV数据以供下载
            window.multiCsvData = data.csv_data;
            
            // 显示结果区域
            multiResultSummary.style.display = 'block';
            multiChartCard.style.display = 'block';
            multiMapCard.style.display = 'block';
            document.getElementById('multiDailyLogCard').style.display = 'block';
        })
        .catch(error => {
            console.error('多段模拟请求失败:', error);
            alert('模拟失败，请检查控制台获取详细信息。');
        })
        .finally(() => {
            // 恢复按钮状态
            multiSimulateBtn.disabled = false;
            multiSimulateBtn.innerHTML = '<i class="fas fa-play"></i> 开始多段模拟';
        });
    });
    
    // 为下载CSV按钮添加点击事件
    multiDownloadCSVBtn.addEventListener('click', function() {
        downloadCSV(window.multiCsvData, 'multi_segment_voyage.csv');
    });
}

// 批量模拟相关函数
function initBatchSimulation() {
    const batchSimulateBtn = document.getElementById('batchSimulateBtn');
    const batchStartPortSelect = document.getElementById('batchStartPort');
    const batchEndPortSelect = document.getElementById('batchEndPort');
    const batchShipSpeedInput = document.getElementById('batchShipSpeed');
    const batchSpeedVariationInput = document.getElementById('batchSpeedVariation');
    const batchWindFactorMinInput = document.getElementById('batchWindFactorMin');
    const batchWindFactorMaxInput = document.getElementById('batchWindFactorMax');
    const numSimulationsInput = document.getElementById('numSimulations');
    const batchComparisonCard = document.getElementById('batchComparisonCard');
    const batchResultsCard = document.getElementById('batchResultsCard');
    const batchDownloadCSVBtn = document.getElementById('batchDownloadCSV');
    
    // 为模拟按钮添加点击事件
    batchSimulateBtn.addEventListener('click', function() {
        // 获取所有选中的月份
        const monthsRange = [];
        for (let i = 1; i <= 12; i++) {
            if (document.getElementById(`month${i}`).checked) {
                monthsRange.push(i);
            }
        }
        
        // 检查是否至少选择了一个月份
        if (monthsRange.length === 0) {
            alert('请至少选择一个模拟月份！');
            return;
        }
        
        // 检查起点和终点
        if (batchStartPortSelect.value === batchEndPortSelect.value) {
            alert('起点和终点不能是同一个港口！');
            return;
        }
        
        // 检查风速因子范围
        if (parseFloat(batchWindFactorMinInput.value) >= parseFloat(batchWindFactorMaxInput.value)) {
            alert('风速最小影响系数必须小于最大影响系数！');
            return;
        }
        
        // 禁用按钮，显示加载状态
        batchSimulateBtn.disabled = true;
        batchSimulateBtn.innerHTML = '<span class="loading"></span> 模拟中...';
        
        // 获取表单数据
        const formData = {
            simulation_mode: 'batch',
            start_port: batchStartPortSelect.value,
            end_port: batchEndPortSelect.value,
            months_range: monthsRange,
            ship_speed: batchShipSpeedInput.value,
            speed_variation: batchSpeedVariationInput.value,
            wind_factor_min: batchWindFactorMinInput.value,
            wind_factor_max: batchWindFactorMaxInput.value,
            num_simulations: numSimulationsInput.value
        };
        
        // 发送模拟请求
        fetch('/simulate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(formData)
        })
        .then(response => response.json())
        .then(data => {
            // 显示比较图表
            document.getElementById('batchComparisonChart').src = `data:image/png;base64,${data.comparison_chart}`;
            
            // 填充结果表格
            const resultsTable = document.getElementById('batchResultsTable').querySelector('tbody');
            resultsTable.innerHTML = '';
            
            // 存储CSV数据
            window.batchCsvData = [];
            
            // 处理每个模拟结果
            data.simulations.forEach(sim => {
                // 添加表格行
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>#${sim.simulation_id}</td>
                    <td>${sim.parameters.departure_month}月</td>
                    <td>${sim.parameters.ship_speed.toFixed(1)}</td>
                    <td>${sim.total_days}</td>
                    <td>${sim.total_waiting_days}</td>
                    <td>${sim.total_days + sim.total_waiting_days}</td>
                    <td>${Math.round(sim.total_distance)}</td>
                `;
                resultsTable.appendChild(row);
                
                // 存储CSV数据
                window.batchCsvData.push({
                    simulationId: sim.simulation_id,
                    csvData: sim.csv_data
                });
            });
            
            // 显示结果区域
            batchComparisonCard.style.display = 'block';
            batchResultsCard.style.display = 'block';
        })
        .catch(error => {
            console.error('批量模拟请求失败:', error);
            alert('模拟失败，请检查控制台获取详细信息。');
        })
        .finally(() => {
            // 恢复按钮状态
            batchSimulateBtn.disabled = false;
            batchSimulateBtn.innerHTML = '<i class="fas fa-play"></i> 开始批量模拟';
        });
    });
    
    // 为下载CSV按钮添加点击事件
    batchDownloadCSVBtn.addEventListener('click', function() {
        if (window.batchCsvData && window.batchCsvData.length > 0) {
            // 创建一个ZIP文件
            // 注意：这里使用现代浏览器的Blob API，不需要额外的库
            const zip = new JSZip();
            
            // 添加每个模拟的CSV文件
            window.batchCsvData.forEach(item => {
                zip.file(`simulation_${item.simulationId}.csv`, item.csvData);
            });
            
            // 生成ZIP文件并下载
            zip.generateAsync({type: "blob"})
            .then(function(content) {
                const url = URL.createObjectURL(content);
                const a = document.createElement('a');
                a.style.display = 'none';
                a.href = url;
                a.download = 'batch_simulation_results.zip';
                document.body.appendChild(a);
                a.click();
                URL.revokeObjectURL(url);
                document.body.removeChild(a);
            });
        }
    });
    
    // 防止起点和终点选择相同的港口
    batchStartPortSelect.addEventListener('change', function() {
        checkSamePort(batchStartPortSelect, batchEndPortSelect, batchSimulateBtn);
    });
    
    batchEndPortSelect.addEventListener('change', function() {
        checkSamePort(batchStartPortSelect, batchEndPortSelect, batchSimulateBtn);
    });
}

// 辅助函数

// 添加一个港口输入组件
function addPortInput(container, label) {
    const inputGroup = document.createElement('div');
    inputGroup.className = 'input-group mb-2';
    inputGroup.innerHTML = `
        <div class="input-group-prepend">
            <span class="input-group-text">${label}</span>
        </div>
        <select class="form-control port-select" required>
            ${document.getElementById('startPort').innerHTML}
        </select>
    `;
    
    // 如果不是起点，添加删除按钮
    if (label !== '起点') {
        const removeBtn = document.createElement('div');
        removeBtn.className = 'input-group-append';
        removeBtn.innerHTML = `
            <button class="btn btn-outline-danger" type="button" title="移除此港口">
                <i class="fas fa-times"></i>
            </button>
        `;
        removeBtn.querySelector('button').addEventListener('click', function() {
            container.removeChild(inputGroup);
            
            // 确保最后一个标签是"终点"
            const portInputs = container.querySelectorAll('.input-group');
            if (portInputs.length > 0) {
                const lastInput = portInputs[portInputs.length - 1];
                lastInput.querySelector('.input-group-text').textContent = '终点';
            }
        });
        inputGroup.appendChild(removeBtn);
    }
    
    container.appendChild(inputGroup);
}

// 检查起点终点是否相同
function checkSamePort(startSelect, endSelect, simulateBtn) {
    if (startSelect.value === endSelect.value) {
        simulateBtn.disabled = true;
        alert('起点和终点不能是同一个港口！');
    } else {
        simulateBtn.disabled = false;
    }
}

// 下载CSV文件
function downloadCSV(csvData, filename) {
    if (csvData) {
        // 创建Blob对象
        const blob = new Blob([csvData], { type: 'text/csv' });
        
        // 创建下载链接
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = url;
        a.download = filename;
        
        // 触发下载
        document.body.appendChild(a);
        a.click();
        
        // 清理
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
    }
}