import math
import random
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import io
import base64
import folium
from folium import plugins
import pandas as pd
from flask import url_for
# 添加中文字体支持
from matplotlib.font_manager import FontProperties
# 尝试多种可能的方式解决中文显示问题
try:
    # 方法1：使用系统中可能存在的中文字体
    plt.rcParams['font.sans-serif'] = ['WenQuanYi Zen Hei', 'SimHei', 'Microsoft YaHei', 'SimSun', 'sans-serif']
    plt.rcParams['axes.unicode_minus'] = False
except:
    pass

# 港口数据字典
PORTS = {
    "Punt": {"lat": 11.5, "lng": 43.0, "type": "Punt Core Port"},
    "Adulis": {"lat": 15.3, "lng": 39.45, "type": "Red Sea Port of Eritrea"},
    "Berenike": {"lat": 23.9, "lng": 35.48, "type": "Egyptian New Kingdom Port"},
    "Marsa Alam": {"lat": 25.1, "lng": 34.88, "type": "Southern Egyptian Port"},
    "Quseir": {"lat": 26.1, "lng": 34.28, "type": "Middle Egyptian Port"},
    "Coptos": {"lat": 25.9, "lng": 32.78, "type": "Nile River City (Terminus)"},
    
    # 新增古埃及沿岸港口
    "Myos Hormos": {"lat": 27.3, "lng": 33.8, "type": "Egyptian Red Sea Trade Port"},
    "Philoteras": {"lat": 26.7, "lng": 34.0, "type": "Egyptian Trading Outpost"},
    "Leukos Limen": {"lat": 26.2, "lng": 34.25, "type": "Ancient Egyptian Harbor"},
    "Nechesia": {"lat": 24.7, "lng": 35.2, "type": "Southern Egyptian Trading Post"},
    "Suez": {"lat": 29.9, "lng": 32.5, "type": "Northern Red Sea Port"},
    
    # 新增索马里沿岸港口
    "Opone": {"lat": 10.4, "lng": 51.2, "type": "Somali Ancient Trading Hub"},
    "Malao": {"lat": 10.5, "lng": 45.0, "type": "Gulf of Aden Port"},
    "Mundus": {"lat": 11.35, "lng": 43.4, "type": "Ancient Somali Trading Post"},
    "Mosylon": {"lat": 11.28, "lng": 49.18, "type": "Northern Somali Port"},
    "Zeila": {"lat": 11.35, "lng": 43.47, "type": "Historic Horn of Africa Port"},
    "Berbera": {"lat": 10.42, "lng": 45.01, "type": "Major Somali Gulf Trading Center"}
}

# 红海区域风速数据 (单位: km/h)
WIND_SPEED_DATA = {
    # 月份: [最小风速, 最大风速, 季风主导方向(角度，0为北)]
    1: [15, 30, 45],    # 东北季风
    2: [15, 25, 45],    # 东北季风
    3: [10, 20, 90],    # 转换期
    4: [5, 15, 135],    # 转换期
    5: [10, 20, 225],   # 转换到西南
    6: [15, 30, 225],   # 西南季风
    7: [20, 35, 225],   # 西南季风强盛
    8: [25, 40, 225],   # 西南季风最强
    9: [20, 35, 225],   # 西南季风
    10: [10, 25, 180],  # 转换期
    11: [15, 30, 45],   # 东北季风开始
    12: [15, 35, 45],   # 东北季风
}

def haversine_distance(lat1, lon1, lat2, lon2):
    """
    使用Haversine公式计算两点间的地理距离（单位：公里）
    """
    # 将十进制度数转化为弧度
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    
    # Haversine公式
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    r = 6371  # 地球平均半径，单位：公里
    
    return c * r

def calculate_bearing(lat1, lon1, lat2, lon2):
    """
    计算两点间的方位角（单位：度，0为北）
    """
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    
    y = math.sin(lon2 - lon1) * math.cos(lat2)
    x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(lon2 - lon1)
    theta = math.atan2(y, x)
    
    bearing = (math.degrees(theta) + 360) % 360
    return bearing

def get_wind_effect(month, bearing, wind_factor_min=0.5, wind_factor_max=1.5):
    """
    根据月份和航行方向计算风对船速的影响
    
    参数:
    - month: 月份 (1-12)
    - bearing: 航行方位角 (0-360度，0为北)
    - wind_factor_min: 最小风速系数
    - wind_factor_max: 最大风速系数
    
    返回:
    - 风速影响系数 (0.5-1.5)
    """
    wind_min, wind_max, wind_direction = WIND_SPEED_DATA[month]
    
    # 计算航行方向与风向之间的夹角
    angle_diff = min(abs(bearing - wind_direction), 360 - abs(bearing - wind_direction))
    
    # 将夹角转换为风的影响系数
    # 0度表示顺风(最大加速)，180度表示逆风(最大减速)
    if angle_diff <= 45:  # 基本顺风
        wind_effect = wind_factor_max - (angle_diff / 45) * 0.3
    elif angle_diff <= 90:  # 侧风但偏顺风
        wind_effect = 1.2 - (angle_diff - 45) / 45 * 0.2
    elif angle_diff <= 135:  # 侧风但偏逆风
        wind_effect = 1.0 - (angle_diff - 90) / 45 * 0.3
    else:  # 基本逆风
        wind_effect = 0.7 - (angle_diff - 135) / 45 * 0.2
    
    # 加入随机因素，但保持在合理范围内
    random_factor = 1.0 + random.uniform(-0.1, 0.1)
    wind_effect *= random_factor
    
    # 确保风速因子在允许范围内
    wind_effect = max(wind_factor_min, min(wind_factor_max, wind_effect))
    
    return wind_effect

def calculate_waiting_time(departure_month, target_month_range, min_wait=30, max_wait=60):
    """
    计算需要等待季风转换的时间
    
    参数:
    - departure_month: 当前月份
    - target_month_range: 目标月份范围列表
    - min_wait/max_wait: 最小/最大等待天数
    """
    # 如果当前月份已经在目标月份范围内，仍需短暂等待
    if departure_month in target_month_range:
        return random.randint(15, 30)  # 一般需要半个月到一个月准备
    
    # 查找下一个目标月份
    closest_month = None
    min_distance = 12
    
    for month in target_month_range:
        # 计算当前月份到目标月份的距离
        if month >= departure_month:
            distance = month - departure_month
        else:
            distance = month + 12 - departure_month
            
        if distance < min_distance:
            min_distance = distance
            closest_month = month
    
    # 基础等待时间(月转天)
    wait_time = min_distance * 30
    
    # 确保等待时间不会低于一个月
    if wait_time < 30:
        wait_time = 30
    
    # 增加随机变化
    wait_time += random.randint(min_wait, max_wait)
    
    return wait_time

def simulate_voyage_segment(start_port, end_port, departure_month, ship_speed=60, 
                           wind_factor_min=0.5, wind_factor_max=1.5, 
                           is_waiting_at_port=True):
    """
    模拟单段航海旅程
    """
    # 计算总距离（千米）
    total_distance = haversine_distance(
        start_port["lat"], start_port["lng"],
        end_port["lat"], end_port["lng"]
    )
    
    # 计算航行方位角
    bearing = calculate_bearing(
        start_port["lat"], start_port["lng"],
        end_port["lat"], end_port["lng"]
    )
    
    # 初始化模拟数据
    current_month = departure_month
    days_passed = 0
    distance_traveled = 0
    daily_progress = []
    wind_effects = []
    
    # 航行直到到达目的地
    while distance_traveled < total_distance:
        # 获取当前月份的风速影响
        wind_effect = get_wind_effect(current_month, bearing, wind_factor_min, wind_factor_max)
        
        # 确保风效果至少有一些变化，避免所有值都是0
        wind_effect = max(wind_effect, 0.5)  # 最小风速影响不低于0.5
        
        # 计算今天的行进距离
        today_distance = ship_speed * wind_effect
        distance_traveled = min(distance_traveled + today_distance, total_distance)
        
        # 记录数据
        daily_progress.append(today_distance)  # 记录当天实际航行距离
        wind_effects.append(wind_effect)
        
        # 更新天数和月份
        days_passed += 1
        if days_passed % 30 == 0:
            current_month = current_month % 12 + 1
    
    # 计算到达的月份
    months_passed = days_passed // 30
    arrival_month = ((departure_month - 1 + months_passed) % 12) + 1
    
    # 等待合适的季风（如果需要）
    waiting_days = 0
    if is_waiting_at_port:
        # 确定理想的航行月份
        # 根据航行方向选择不同的月份
        # 如果是从北向南（方位角在135-225之间），选择西南季风月份（适合南下）
        if 135 <= bearing <= 225:
            # 西南季风月份，适合从北向南航行
            ideal_months = [6, 7, 8, 9]
        else:
            # 东北季风月份，适合从南向北航行
            ideal_months = [11, 12, 1, 2]
            
        # 计算需要等待的时间
        waiting_days = calculate_waiting_time(arrival_month, ideal_months)
        
        # 确保等待时间至少有值，更符合历史航海实际
        if waiting_days < 15 and arrival_month not in ideal_months:
            waiting_days = random.randint(15, 30)  # 至少等待半个月
    
    # 打印调试信息
    # print(f"从{start_port}到{end_port}，出发月份:{departure_month}，到达月份:{arrival_month}，航行天数:{days_passed}，等待天数:{waiting_days}")
    
    return {
        "distance": total_distance,
        "days": days_passed,
        "arrival_month": arrival_month,
        "waiting_days": waiting_days,
        "daily_progress": daily_progress,
        "wind_effects": wind_effects
    }

def simulate_multi_segment_voyage(ports_sequence, departure_month, ship_speed=60,
                                 wind_factor_min=0.5, wind_factor_max=1.5, return_voyage=False):
    """
    模拟多段航行
    
    参数:
    - ports_sequence: 港口序列，如 ["Berenike", "Adulis", "Punt", "Adulis", "Berenike"]
    - departure_month: 出发月份
    - ship_speed: 基础船速
    - wind_factor_min/max: 风速影响系数范围
    - return_voyage: 是否计算返航路线
    """
    if len(ports_sequence) < 2:
        raise ValueError("至少需要两个港口才能模拟航行")
    
    total_results = {
        "total_distance": 0,
        "total_days": 0,
        "total_waiting_days": 0,
        "segments": [],
        "ports_visited": ports_sequence.copy(),
        "cumulative_days": [0],
        "cumulative_distances": [0],
        "segment_labels": []
    }
    
    current_month = departure_month
    current_day = 0
    cumulative_distance = 0
    
    # 处理出航航程
    for i in range(len(ports_sequence) - 1):
        start_port_name = ports_sequence[i]
        end_port_name = ports_sequence[i+1]
        
        start_port = PORTS[start_port_name]
        end_port = PORTS[end_port_name]
        
        # 是否为最后一段行程（决定是否等待季风）
        is_last_segment = (i == len(ports_sequence) - 2)
        
        # 计算航向角度
        bearing = calculate_bearing(
            start_port["lat"], start_port["lng"],
            end_port["lat"], end_port["lng"]
        )
        
        # 判断是否需要等待季风
        should_wait_for_monsoon = False
        
        # 1. 如果是返航模式的最后一段，必须等待合适季风
        if return_voyage and is_last_segment:
            # 总是在远端港口等待合适季风返航
            should_wait_for_monsoon = True
        else:
            # 2. 对于其他航段，根据航段长度和风向判断
            # 获取当前月份的风向和强度
            wind_min, wind_max, wind_direction = WIND_SPEED_DATA[current_month]
            
            # 计算风向和航向的夹角
            angle_diff = min(abs(bearing - wind_direction), 360 - abs(bearing - wind_direction))
            
            # 计算航段距离
            segment_distance = haversine_distance(
                start_port["lat"], start_port["lng"],
                end_port["lat"], end_port["lng"]
            )
            
            # 3. 如果是逆风且距离较长，需要等待季风
            # 注意：当航行距离较长（超过500km），且风向不利（逆风角度大于120度）时
            if angle_diff > 120 and segment_distance > 500:
                should_wait_for_monsoon = True
                
            # 4. 对于极其重要的航段，如果风向非常不利，即使距离短也会等待
            if angle_diff > 150 and wind_min > 20:  # 极强逆风
                should_wait_for_monsoon = True
        
        # 模拟这一段航程
        segment_result = simulate_voyage_segment(
            start_port, end_port, current_month, ship_speed,
            wind_factor_min, wind_factor_max, should_wait_for_monsoon
        )
        
        # 更新累计数据
        segment_result["start_port"] = start_port_name
        segment_result["end_port"] = end_port_name
        segment_result["start_day"] = current_day
        segment_result["direction"] = "outbound"  # 标记为出航
        
        total_results["segments"].append(segment_result)
        total_results["total_distance"] += segment_result["distance"]
        total_results["total_days"] += segment_result["days"]
        total_results["total_waiting_days"] += segment_result["waiting_days"]
        
        # 更新月份和天数，为下一段准备
        current_month = segment_result["arrival_month"]
        if segment_result["waiting_days"] > 0:
            current_month = (current_month + segment_result["waiting_days"] // 30) % 12
            if current_month == 0:
                current_month = 12
        
        # 更新累计天数和距离
        current_day += segment_result["days"]
        total_results["cumulative_days"].append(current_day)
        
        if segment_result["waiting_days"] > 0:
            current_day += segment_result["waiting_days"]
            total_results["cumulative_days"].append(current_day)
            total_results["segment_labels"].append(f"Voyage: {start_port_name} to {end_port_name}")
            total_results["segment_labels"].append(f"Waiting: {end_port_name}")
            
            # 在等待期间，距离不变
            cumulative_distance += segment_result["distance"]
            total_results["cumulative_distances"].append(cumulative_distance)
            total_results["cumulative_distances"].append(cumulative_distance)
        else:
            cumulative_distance += segment_result["distance"]
            total_results["cumulative_distances"].append(cumulative_distance)
            total_results["segment_labels"].append(f"Voyage: {start_port_name} to {end_port_name}")
    
    # 处理返航航程（如果启用）
    if return_voyage:
        # 创建返航港口序列（反转出航序列）
        return_ports = list(reversed(ports_sequence))
        
        # 存储返航前的总距离，用于统计
        outbound_total_distance = total_results["total_distance"]
        outbound_total_days = total_results["total_days"]
        outbound_waiting_days = total_results["total_waiting_days"]
        
        # 记录总段数和返航开始时间点
        outbound_segments_count = len(total_results["segments"])
        return_start_day = current_day
        return_start_distance = cumulative_distance
        
        # 处理返航多段航程
        for i in range(len(return_ports) - 1):
            start_port_name = return_ports[i]
            end_port_name = return_ports[i+1]
            
            start_port = PORTS[start_port_name]
            end_port = PORTS[end_port_name]
            
            # 不需要在返航过程中等待
            is_waiting = False
            
            # 模拟返航段航程
            segment_result = simulate_voyage_segment(
                start_port, end_port, current_month, ship_speed,
                wind_factor_min, wind_factor_max, is_waiting
            )
            
            # 更新累计数据
            segment_result["start_port"] = start_port_name
            segment_result["end_port"] = end_port_name
            segment_result["start_day"] = current_day
            segment_result["direction"] = "return"  # 标记为返航
            
            total_results["segments"].append(segment_result)
            total_results["total_distance"] += segment_result["distance"]
            total_results["total_days"] += segment_result["days"]
            
            # 更新月份和天数
            current_month = segment_result["arrival_month"]
            
            # 更新累计天数和距离
            current_day += segment_result["days"]
            total_results["cumulative_days"].append(current_day)
            
            cumulative_distance += segment_result["distance"]
            total_results["cumulative_distances"].append(cumulative_distance)
            total_results["segment_labels"].append(f"Return: {start_port_name} to {end_port_name}")
        
        # 添加返航统计数据
        total_results["return_distance"] = total_results["total_distance"] - outbound_total_distance
        total_results["return_days"] = total_results["total_days"] - outbound_total_days
        total_results["outbound_distance"] = outbound_total_distance
        total_results["outbound_days"] = outbound_total_days
        total_results["waiting_days"] = outbound_waiting_days
        total_results["has_return"] = True
        
        # 将港口访问列表更新为包含返航
        total_results["ports_visited"] = ports_sequence + return_ports[1:]
    else:
        # 没有返航的情况下，添加相关字段以保持一致性
        total_results["return_distance"] = 0
        total_results["return_days"] = 0
        total_results["outbound_distance"] = total_results["total_distance"]
        total_results["outbound_days"] = total_results["total_days"]
        total_results["waiting_days"] = total_results["total_waiting_days"]
        total_results["has_return"] = False
    
    # 生成图表和地图
    chart_data = generate_multi_segment_chart(total_results)
    map_html = generate_multi_segment_map(total_results)
    csv_data = generate_multi_segment_csv(total_results)
    
    # 添加到结果中
    total_results["chart_data"] = chart_data
    total_results["map_html"] = map_html
    total_results["csv_data"] = csv_data
    
    return total_results

def simulate_batch_voyages(start_port_name, end_port_name, months_range, speed_range, 
                          wind_factor_range=None, num_simulations=5):
    """
    批量模拟多次航行，比较不同参数下的结果
    
    参数:
    - start_port_name/end_port_name: 起始/终点港口
    - months_range: 月份范围列表，如 [6, 7, 8]
    - speed_range: 船速范围，如 [50, 70]
    - wind_factor_range: 风速系数范围，如 [0.6, 1.4]
    - num_simulations: 模拟次数
    """
    results = []
    
    # 设置默认风速系数范围
    if wind_factor_range is None:
        wind_factor_range = [0.5, 1.5]
    
    # 进行多次模拟
    for i in range(num_simulations):
        # 随机选择参数
        month = random.choice(months_range)
        speed = random.uniform(speed_range[0], speed_range[1])
        wind_min = wind_factor_range[0]
        wind_max = wind_factor_range[1]
        
        # 单段航行模拟（简单起点到终点）
        ports_sequence = [start_port_name, end_port_name]
        
        result = simulate_multi_segment_voyage(
            ports_sequence, month, speed, wind_min, wind_max
        )
        
        # 添加本次模拟的参数信息
        result["simulation_id"] = i + 1
        result["parameters"] = {
            "departure_month": month,
            "ship_speed": speed,
            "wind_factor_range": [wind_min, wind_max]
        }
        
        results.append(result)
    
    # 生成比较图表
    comparison_chart = generate_batch_comparison_chart(results)
    
    return {
        "simulations": results,
        "comparison_chart": comparison_chart
    }

def generate_multi_segment_chart(results):
    """
    为多段航行生成图表
    """
    plt.figure(figsize=(12, 7))
    
    # 提取数据
    days = results["cumulative_days"]
    distances = results["cumulative_distances"]
    labels = results["segment_labels"]
    
    # 绘制总航程曲线
    plt.plot(days, distances, 'k-', linewidth=1.5)
    
    # 颜色映射
    colors = ['b', 'g', 'r', 'c', 'm', 'y']
    return_colors = ['darkblue', 'darkgreen', 'darkred', 'darkcyan', 'darkmagenta', 'olive']
    
    # 绘制各段航程
    current_outbound_segment = 0
    current_return_segment = 0
    
    for i in range(len(days) - 1):
        segment_days = [days[i], days[i+1]]
        segment_distances = [distances[i], distances[i+1]]
        
        # 为航行、等待和返航使用不同颜色
        if "Waiting" in labels[i]:
            # 等待期为水平线，用红色表示
            plt.plot(segment_days, segment_distances, 'r-', linewidth=2.5, alpha=0.7)
            plt.text(days[i] + (days[i+1] - days[i])/2, distances[i], 
                    f"Waiting for Monsoon\n{days[i+1] - days[i]} Days", 
                    ha='center', va='bottom', color='r')
        elif "Return" in labels[i]:
            # 返航段用深色
            color_idx = current_return_segment % len(return_colors)
            plt.plot(segment_days, segment_distances, 
                    color=return_colors[color_idx], 
                    linestyle='--',  # 使用虚线表示返航
                    linewidth=2.5, 
                    alpha=0.8)
            
            # 在航段中间标注港口信息
            mid_day = days[i] + (days[i+1] - days[i])/2
            mid_distance = distances[i] + (distances[i+1] - distances[i])/2
            port_info = labels[i].replace("Return: ", "")
            plt.text(mid_day, mid_distance, port_info, 
                    ha='center', va='bottom', color=return_colors[color_idx],
                    bbox=dict(facecolor='white', alpha=0.7, boxstyle='round,pad=0.3'))
            
            current_return_segment += 1
        else:
            # 出航段用浅色
            color_idx = current_outbound_segment % len(colors)
            plt.plot(segment_days, segment_distances, 
                    color=colors[color_idx], 
                    linewidth=2.5, 
                    alpha=0.8)
            
            # 在航段中间标注港口信息
            mid_day = days[i] + (days[i+1] - days[i])/2
            mid_distance = distances[i] + (distances[i+1] - distances[i])/2
            port_info = labels[i].replace("Voyage: ", "")
            plt.text(mid_day, mid_distance, port_info, 
                    ha='center', va='bottom', color=colors[color_idx],
                    bbox=dict(facecolor='white', alpha=0.7, boxstyle='round,pad=0.3'))
            
            current_outbound_segment += 1
    
    # 标注起点和终点
    plt.scatter([days[0], days[-1]], [distances[0], distances[-1]], 
               c=['blue', 'green'], s=100, zorder=5)
    
    # 如果有返航，显示出航终点/返航起点
    if results.get("has_return", False):
        # 查找出航和返航的分界点
        return_start_idx = None
        for i, label in enumerate(labels):
            if "Return" in label:
                return_start_idx = i
                break
        
        if return_start_idx is not None:
            return_start_day = days[return_start_idx]
            return_start_distance = distances[return_start_idx]
            plt.scatter([return_start_day], [return_start_distance], 
                       c=['orange'], s=100, zorder=5)
            plt.text(return_start_day, return_start_distance, "Return Start", 
                    ha='right', va='bottom', color='orange')
    
    plt.text(days[0], distances[0], f"Start: {results['ports_visited'][0]}", 
            ha='right', va='bottom', color='blue')
    plt.text(days[-1], distances[-1], f"End: {results['ports_visited'][-1]}", 
            ha='left', va='bottom', color='green')
    
    # 添加标签和标题
    plt.xlabel('Voyage Days')
    plt.ylabel('Cumulative Distance (km)')
    
    if results.get("has_return", False):
        plt.title('Round Trip Distance-Time Chart')
    else:
        plt.title('Multi-Segment Voyage Distance-Time Chart')
    
    plt.grid(True, linestyle='--', alpha=0.7)
    
    # 添加总结信息
    if results.get("has_return", False):
        info_text = (f"Total Distance: {int(results['total_distance'])} km\n"
                    f"Outbound Distance: {int(results['outbound_distance'])} km\n"
                    f"Return Distance: {int(results['return_distance'])} km\n"
                    f"Outbound Days: {results['outbound_days']} days\n"
                    f"Waiting Days: {results['waiting_days']} days\n"
                    f"Return Days: {results['return_days']} days\n"
                    f"Total Days: {results['total_days'] + results['total_waiting_days']} days")
    else:
        info_text = (f"Total Distance: {int(results['total_distance'])} km\n"
                    f"Total Voyage Days: {results['total_days']} days\n"
                    f"Waiting Days: {results['total_waiting_days']} days\n"
                    f"Total Time: {results['total_days'] + results['total_waiting_days']} days")
    
    plt.annotate(info_text, xy=(0.02, 0.97), xycoords='axes fraction',
                bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="gray", alpha=0.8),
                ha='left', va='top')
    
    # 将图表转换为base64编码的图像
    img = io.BytesIO()
    plt.savefig(img, format='png', dpi=100)
    img.seek(0)
    chart_url = base64.b64encode(img.getvalue()).decode()
    plt.close()
    
    return chart_url

def generate_batch_comparison_chart(results):
    """
    生成批量模拟的比较图表
    """
    plt.figure(figsize=(12, 8))
    
    # 创建两个子图
    gs = plt.GridSpec(2, 1, height_ratios=[2, 1])
    ax1 = plt.subplot(gs[0])
    ax2 = plt.subplot(gs[1])
    
    # 上方图表: 所有模拟的航程曲线
    colors = plt.cm.jet(np.linspace(0, 1, len(results)))
    
    for i, result in enumerate(results):
        # 提取数据
        days = result["cumulative_days"]
        distances = result["cumulative_distances"]
        month = result["parameters"]["departure_month"]
        speed = result["parameters"]["ship_speed"]
        
        # 绘制航程曲线
        label = f"模拟 #{i+1}: {month}月出发, {speed:.1f} km/day"
        ax1.plot(days, distances, '-', color=colors[i], linewidth=2, alpha=0.8, label=label)
    
    ax1.set_xlabel('天数')
    ax1.set_ylabel('累计距离 (km)')
    ax1.set_title('批量模拟航程比较')
    ax1.grid(True, linestyle='--', alpha=0.7)
    ax1.legend(loc='upper left', fontsize=8)
    
    # 下方图表: 总航行天数的条形图比较
    sim_ids = [f"#{r['simulation_id']}" for r in results]
    total_days = [r["total_days"] + r["total_waiting_days"] for r in results]
    voyage_days = [r["total_days"] for r in results]
    waiting_days = [r["total_waiting_days"] for r in results]
    
    width = 0.35
    ax2.bar(sim_ids, voyage_days, width, label='航行天数', color='skyblue')
    ax2.bar(sim_ids, waiting_days, width, bottom=voyage_days, label='等待天数', color='salmon')
    
    # 在柱状图顶部添加月份标签
    for i, result in enumerate(results):
        month = result["parameters"]["departure_month"]
        ax2.text(i, total_days[i] + 2, f"{month}月", ha='center')
    
    ax2.set_xlabel('模拟ID')
    ax2.set_ylabel('天数')
    ax2.set_title('总航行时间比较')
    ax2.legend()
    
    plt.tight_layout()
    
    # 将图表转换为base64编码的图像
    img = io.BytesIO()
    plt.savefig(img, format='png', dpi=100)
    img.seek(0)
    chart_url = base64.b64encode(img.getvalue()).decode()
    plt.close()
    
    return chart_url

def generate_multi_segment_map(results):
    """
    为多段航行生成地图
    """
    # 获取所有涉及的港口
    ports_sequence = results["ports_visited"]
    
    # 获取港口坐标
    port_coordinates = [(PORTS[port]["lat"], PORTS[port]["lng"]) for port in ports_sequence]
    
    # 计算地图中心
    center_lat = sum(coord[0] for coord in port_coordinates) / len(port_coordinates)
    center_lng = sum(coord[1] for coord in port_coordinates) / len(port_coordinates)
    
    # 创建地图
    m = folium.Map(location=[center_lat, center_lng], zoom_start=5)
    
    # 添加线性航线图（但不影响原地图生成功能）
    linear_chart = generate_linear_route_chart(results)
    results["linear_chart_data"] = linear_chart
    
    # 标记出航/返航的分界点
    has_return = results.get("has_return", False)
    return_start_idx = None
    
    if has_return:
        # 找到返航起始段索引
        for i, segment in enumerate(results["segments"]):
            if segment.get("direction") == "return":
                return_start_idx = i
                break
    
    # 添加港口标记
    visited_ports = set()  # 跟踪已经访问过的港口
    
    for i, port_name in enumerate(ports_sequence):
        # 如果港口已经添加过标记，则跳过
        if port_name in visited_ports:
            continue
        
        port = PORTS[port_name]
        visited_ports.add(port_name)
        
        # 确定港口角色（起点、终点、中转点、返航点）
        if i == 0:  # 起点
            icon_color = 'blue'
            popup_text = f'Start: {port_name} ({port["type"]})'
        elif i == len(ports_sequence) - 1:  # 终点
            icon_color = 'green'
            popup_text = f'End: {port_name} ({port["type"]})'
        elif has_return and port_name == ports_sequence[len(ports_sequence)//2]:  # 返航起点
            icon_color = 'orange'
            popup_text = f'Return Start: {port_name} ({port["type"]})'
        else:  # 中转港
            icon_color = 'gray'
            popup_text = f'Transit: {port_name} ({port["type"]})'
        
        folium.Marker(
            [port["lat"], port["lng"]],
            popup=popup_text,
            icon=folium.Icon(color=icon_color)
        ).add_to(m)
    
    # 颜色列表
    outbound_colors = ['blue', 'green', 'red', 'purple', 'darkblue', 'darkgreen']
    return_colors = ['orange', 'darkred', 'cadetblue', 'darkpurple', 'pink', 'lightred']
    
    # 添加航线
    for i, segment in enumerate(results["segments"]):
        start_port = PORTS[segment["start_port"]]
        end_port = PORTS[segment["end_port"]]
        
        # 根据方向选择颜色
        if segment.get("direction") == "return":
            color_list = return_colors
            segment_idx = i - return_start_idx if return_start_idx is not None else i
            line_style = 'dashed'
        else:
            color_list = outbound_colors
            segment_idx = i
            line_style = None
        
        # 为不同段使用不同颜色
        color = color_list[segment_idx % len(color_list)]
        
        # 线条宽度根据航程距离调整
        segment_distance = segment["distance"]
        weight = 2 + (segment_distance / 1000)  # 距离越远线条越粗
        
        # 添加航线
        folium.PolyLine(
            [(start_port["lat"], start_port["lng"]), (end_port["lat"], end_port["lng"])],
            color=color,
            weight=weight,
            opacity=0.8,
            popup=f'{segment["start_port"]} → {segment["end_port"]}: {int(segment_distance)} km',
            dash_array='5' if line_style == 'dashed' else None
        ).add_to(m)
    
    # 添加距离标注
    for i, segment in enumerate(results["segments"]):
        start_port = PORTS[segment["start_port"]]
        end_port = PORTS[segment["end_port"]]
        
        # 计算中点位置
        mid_lat = (start_port["lat"] + end_port["lat"]) / 2
        mid_lng = (start_port["lng"] + end_port["lng"]) / 2
        
        # 区分出航和返航的标签
        direction_label = "return" if segment.get("direction") == "return" else "outbound"
        
        # 添加距离和天数标注
        folium.Marker(
            [mid_lat, mid_lng],
            icon=folium.DivIcon(
                icon_size=(120, 40),
                icon_anchor=(60, 20),
                html=f'<div style="font-size: 10pt; color: black; background-color: white; '
                     f'border-radius: 4px; padding: 2px; opacity: 0.7;">'
                     f'{direction_label}: {int(segment["distance"])} km<br>{segment["days"]} 天</div>'
            )
        ).add_to(m)
    
    # 将地图转换为HTML
    map_html = m._repr_html_()
    
    return map_html

def generate_multi_segment_csv(results):
    """
    为多段航行生成CSV数据
    """
    # 创建数据框
    data = []
    current_day = 0
    accumulated_distance = 0
    
    # 处理每一段航程
    for i, segment in enumerate(results["segments"]):
        start_port = segment["start_port"]
        end_port = segment["end_port"]
        direction = segment.get("direction", "outbound")  # 默认为出航
        
        # 添加每日航行数据
        for day, distance in enumerate(segment["daily_progress"]):
            wind_effect = segment["wind_effects"][day] if day < len(segment["wind_effects"]) else 1.0
            accumulated_distance += distance
            
            data.append({
                'Day': current_day + day + 1,
                'Segment': i + 1,
                'Direction': f'{direction.capitalize()}: {start_port} to {end_port}',
                'Distance (km)': distance,
                'Accumulated (km)': accumulated_distance,
                'Wind Effect': round(wind_effect, 2)
            })
        
        current_day += segment["days"]
        
        # 如果有等待时间，添加等待数据
        if segment.get("waiting_days", 0) > 0:
            for wait_day in range(segment["waiting_days"]):
                data.append({
                    'Day': current_day + wait_day + 1,
                    'Segment': f'{i+1} (Waiting)',
                    'Direction': f'Waiting at {end_port}',
                    'Distance (km)': 0,
                    'Accumulated (km)': accumulated_distance,
                    'Wind Effect': 0
                })
            
            current_day += segment["waiting_days"]
    
    # 创建DataFrame并转换为CSV
    df = pd.DataFrame(data)
    csv_data = df.to_csv(index=False)
    
    return csv_data

def generate_linear_route_chart(results):
    """
    生成类似样例的简化线性航线图
    """
    plt.figure(figsize=(12, 8))
    
    # 获取所有港口
    ports_sequence = results["ports_visited"]
    total_distance = results["total_distance"]
    
    # 创建垂直线段连接的航线图
    y_positions = np.linspace(0, 100, len(ports_sequence))  # 垂直位置，自上而下
    x_positions = []
    
    # 获取每个港口的经度差别来决定X轴位置
    base_lng = PORTS[ports_sequence[0]]["lng"]
    for port_name in ports_sequence:
        lng_diff = PORTS[port_name]["lng"] - base_lng
        x_positions.append(lng_diff * 2)  # 放大差异
    
    # 绘制连接线
    plt.plot(x_positions, y_positions, 'b-', linewidth=2)
    
    # 添加港口点和标签
    for i, port_name in enumerate(ports_sequence):
        plt.scatter(x_positions[i], y_positions[i], c='blue', s=100, zorder=5)
        
        # 港口名称标签
        plt.text(x_positions[i], y_positions[i], 
                f"{port_name}", 
                ha='right', va='center', color='black', fontsize=10)
    
    # 添加距离和时间标记
    cumulative_distance = 0
    segment_days_total = 0
    
    for i in range(len(ports_sequence) - 1):
        # 计算这段距离
        start_port = PORTS[ports_sequence[i]]
        end_port = PORTS[ports_sequence[i+1]]
        
        segment_distance = haversine_distance(
            start_port["lat"], start_port["lng"],
            end_port["lat"], end_port["lng"]
        )
        
        # 获取航段天数
        segment_days = 0
        for segment in results["segments"]:
            if segment["start_port"] == ports_sequence[i] and segment["end_port"] == ports_sequence[i+1]:
                segment_days = segment["days"]
                break
        
        segment_days_total += segment_days
        cumulative_distance += segment_distance
        
        # 航段中点坐标
        mid_x = (x_positions[i] + x_positions[i+1]) / 2
        mid_y = (y_positions[i] + y_positions[i+1]) / 2
        
        # 标记距离和时间
        annotation_text = f"{int(segment_distance)}km\n~{segment_days}天"
        if segment["direction"] == "return":
            annotation_text += "\n(返航)"
            
        # 计算偏移以避免重叠
        offset_x = (i % 2) * 2 - 1  # 交替左右偏移
        
        plt.annotate(
            annotation_text,
            xy=(mid_x, mid_y),
            xytext=(mid_x + offset_x, mid_y),
            color='red',
            fontsize=9,
            arrowprops=dict(arrowstyle='->', color='red', lw=1)
        )
    
    # 添加标题
    if results.get("has_return", False):
        title = f"Ancient Maritime Route: {ports_sequence[0]} to {ports_sequence[len(ports_sequence)//2]} (Return Voyage)"
    else:
        title = f"Ancient Maritime Route: {ports_sequence[0]} to {ports_sequence[-1]}"
    
    plt.title(title, fontsize=14)
    
    # 添加航行总结
    info_text = (
        f"Legend:\n"
        f"- Blue Dots: Major ports along the Red Sea coast\n"
        f"- Blue Lines: Reconstructed sailing segments\n"
        f"- Red Text: Estimated segment distance, sailing time\n\n"
        f"Notes:\n"
        f"- Based on New Kingdom (ca. 1500 to 1000 BCE) Egyptian maritime records\n"
        f"- Sailing speed influenced by NE seasonal monsoon winds\n"
        f"- Total Distance: ~{int(total_distance)} km | Estimated Time: ~{segment_days_total} days"
    )
    
    plt.figtext(0.02, 0.02, info_text, wrap=True, fontsize=9)
    
    # 关闭坐标轴显示
    plt.axis('off')
    
    # 将图表转换为base64编码的图像
    img = io.BytesIO()
    plt.savefig(img, format='png', dpi=100, bbox_inches='tight')
    img.seek(0)
    chart_url = base64.b64encode(img.getvalue()).decode()
    plt.close()
    
    return chart_url 