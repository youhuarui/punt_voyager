from flask import Blueprint, render_template, request, jsonify
from app.voyage_simulator import (
    simulate_voyage_segment, simulate_multi_segment_voyage, 
    simulate_batch_voyages, PORTS
)
import json
import numpy as np

main = Blueprint('main', __name__)

@main.route('/')
def index():
    # 港口数据
    ports = [
        {"name": "Punt", "lat": 11.5, "lng": 43.0, "type": "蓬特核心港"},
        {"name": "Adulis", "lat": 15.3, "lng": 39.45, "type": "厄立特里亚红海港"},
        {"name": "Berenike", "lat": 23.9, "lng": 35.48, "type": "埃及新王国港"},
        {"name": "Marsa Alam", "lat": 25.1, "lng": 34.88, "type": "埃及南部港"},
        {"name": "Quseir", "lat": 26.1, "lng": 34.28, "type": "埃及中部港"},
        {"name": "Coptos", "lat": 25.9, "lng": 32.78, "type": "尼罗河港口城市（终点）"},
        
        # 新增古埃及沿岸港口
        {"name": "Myos Hormos", "lat": 27.3, "lng": 33.8, "type": "埃及红海贸易港"},
        {"name": "Philoteras", "lat": 26.7, "lng": 34.0, "type": "埃及贸易前哨站"},
        {"name": "Leukos Limen", "lat": 26.2, "lng": 34.25, "type": "古埃及港口"},
        {"name": "Nechesia", "lat": 24.7, "lng": 35.2, "type": "埃及南部贸易站"},
        {"name": "Suez", "lat": 29.9, "lng": 32.5, "type": "红海北部港口"},
        
        # 新增索马里沿岸港口
        {"name": "Opone", "lat": 10.4, "lng": 51.2, "type": "索马里古代贸易中心"},
        {"name": "Malao", "lat": 10.5, "lng": 45.0, "type": "亚丁湾港口"},
        {"name": "Mundus", "lat": 11.35, "lng": 43.4, "type": "索马里古代贸易站"},
        {"name": "Mosylon", "lat": 11.28, "lng": 49.18, "type": "索马里北部港口"},
        {"name": "Zeila", "lat": 11.35, "lng": 43.47, "type": "非洲之角历史港口"},
        {"name": "Berbera", "lat": 10.42, "lng": 45.01, "type": "索马里湾主要贸易中心"}
    ]
    return render_template('index.html', ports=ports)

@main.route('/simulate', methods=['POST'])
def simulate():
    data = request.get_json()
    
    # 新增支持多段中转路线
    if 'ports_sequence' in data:
        # 多段航行模式
        ports_sequence = data.get('ports_sequence')
        departure_month = int(data.get('departure_month'))
        ship_speed = float(data.get('ship_speed', 60))
        
        # 风速范围设置
        wind_factor_min = float(data.get('wind_factor_min', 0.5))
        wind_factor_max = float(data.get('wind_factor_max', 1.5))
        
        # 返航选项
        return_voyage = bool(data.get('return_voyage', False))
        
        # 调用多段模拟引擎
        simulation_results = simulate_multi_segment_voyage(
            ports_sequence, departure_month, ship_speed,
            wind_factor_min, wind_factor_max, return_voyage
        )
        
        return jsonify(simulation_results)
    
    elif 'simulation_mode' in data and data.get('simulation_mode') == 'batch':
        # 批量模拟模式
        start_port = data.get('start_port')
        end_port = data.get('end_port')
        
        # 月份范围
        months_range = data.get('months_range', list(range(1, 13)))
        if isinstance(months_range, str):
            months_range = [int(m) for m in months_range.split(',')]
        
        # 船速范围
        base_speed = float(data.get('ship_speed', 60))
        speed_variation = float(data.get('speed_variation', 10))
        speed_range = [base_speed - speed_variation, base_speed + speed_variation]
        
        # 风速系数范围
        wind_min = float(data.get('wind_factor_min', 0.5))
        wind_max = float(data.get('wind_factor_max', 1.5))
        wind_factor_range = [wind_min, wind_max]
        
        # 模拟次数
        num_simulations = int(data.get('num_simulations', 5))
        
        # 调用批量模拟引擎
        batch_results = simulate_batch_voyages(
            start_port, end_port, months_range, speed_range,
            wind_factor_range, num_simulations
        )
        
        return jsonify(batch_results)
    
    else:
        # 向下兼容：简单单航段模式
        start_port_name = data.get('start_port')
        end_port_name = data.get('end_port')
        departure_month = int(data.get('departure_month'))
        ship_speed = float(data.get('ship_speed', 60))
        
        # 风速范围设置
        wind_factor_min = float(data.get('wind_factor_min', 0.5))
        wind_factor_max = float(data.get('wind_factor_max', 1.5))
        
        # 返航选项
        return_voyage = bool(data.get('return_voyage', False))
        
        # 使用新的多段模拟，但只有一段（起点到终点）
        ports_sequence = [start_port_name, end_port_name]
        simulation_results = simulate_multi_segment_voyage(
            ports_sequence, departure_month, ship_speed,
            wind_factor_min, wind_factor_max, return_voyage
        )
        
        # 向下兼容格式处理
        compat_results = {
            "total_days": simulation_results["total_days"],
            "outbound_days": simulation_results["outbound_days"],
            "waiting_days": simulation_results["waiting_days"],
            "return_days": simulation_results.get("return_days", 0),
            "total_distance": simulation_results["total_distance"],
            "chart_data": simulation_results["chart_data"],
            "map_html": simulation_results["map_html"],
            "csv_data": simulation_results["csv_data"]
        }
        
        return jsonify(compat_results) 