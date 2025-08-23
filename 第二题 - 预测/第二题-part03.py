import pandas as pd
import numpy as np

# 重新读取数据
topsis_results = pd.read_excel('供应商TOPSIS评价结果.xlsx')
future_supply = pd.read_excel('供应商未来24周供货量预测.xlsx')
transporters = pd.read_excel('附件2.xlsx')

# 生产参数
weekly_capacity = 28200  # 每周产能，立方米
material_coefficients = {'A': 0.6, 'B': 0.66, 'C': 0.72}
material_prices = {'A': 1.2, 'B': 1.1, 'C': 1.0}  # 相对价格，C类为基准
weeks = 24  # 计划周期

# 合并供应商数据
supplier_data = pd.merge(topsis_results, future_supply, on=['供应商ID', '材料分类'])

# 按价格和TOPSIS得分排序：C类优先（最便宜），然后B类，然后A类；同类中TOPSIS高的优先
supplier_data = supplier_data.sort_values(
    by=['材料分类', 'TOPSIS综合得分'],
    ascending=[False, False]  # C类优先，然后B类，然后A类；同类中TOPSIS高的优先
)

# 计算每周原材料需求和库存要求
min_weekly_raw = weekly_capacity * material_coefficients['A']  # A类最省
max_weekly_raw = weekly_capacity * material_coefficients['C']  # C类最费
min_inventory = 2 * max_weekly_raw  # 两周库存要求
safety_stock = 0.2 * max_weekly_raw  # 额外安全库存20%
initial_inventory = min_inventory + safety_stock  # 初始库存

print(f"每周原材料需求范围: {min_weekly_raw:.0f} - {max_weekly_raw:.0f} 立方米")
print(f"最小库存要求: {min_inventory:.0f} 立方米")
print(f"安全库存: {safety_stock:.0f} 立方米")
print(f"初始库存: {initial_inventory:.0f} 立方米")

# 初始化订购方案
week_columns = [f'W{i}' for i in range(241, 265)]
order_plan = pd.DataFrame()
order_plan['供应商ID'] = supplier_data['供应商ID']
order_plan['材料分类'] = supplier_data['材料分类']

# 初始化每周订购量为0
for week_col in week_columns:
    order_plan[week_col] = 0.0

# 动态库存管理模拟
inventory_level = initial_inventory
weekly_inventory = [inventory_level]
weekly_production = []
weekly_material_usage = {'A': [], 'B': [], 'C': []}

for week_idx, week_col in enumerate(week_columns, 1):
    print(f"\n第{week_idx}周:")

    # 获取本周各供应商的预测供货量
    weekly_supplies = supplier_data[week_col].copy()

    # 按材料分类汇总
    c_supply = supplier_data[supplier_data['材料分类'] == 'C'][week_col].sum()
    b_supply = supplier_data[supplier_data['材料分类'] == 'B'][week_col].sum()
    a_supply = supplier_data[supplier_data['材料分类'] == 'A'][week_col].sum()

    print(
        f"  预测供货: C类{int(c_supply)}m³, B类{int(b_supply)}m³, A类{int(a_supply)}m³, 总计{int(c_supply + b_supply + a_supply)}m³")

    # 计算基于现有库存和预测供货的最大可能生产量
    # 优先使用C类材料（最便宜），然后B类，然后A类
    available_c = c_supply + inventory_level * (
        c_supply / (c_supply + b_supply + a_supply) if c_supply + b_supply + a_supply > 0 else 0)
    available_b = b_supply + inventory_level * (
        b_supply / (c_supply + b_supply + a_supply) if c_supply + b_supply + a_supply > 0 else 0)
    available_a = a_supply + inventory_level * (
        a_supply / (c_supply + b_supply + a_supply) if c_supply + b_supply + a_supply > 0 else 0)

    max_product_from_c = available_c / material_coefficients['C']
    max_product_from_b = available_b / material_coefficients['B']
    max_product_from_a = available_a / material_coefficients['A']

    total_possible_product = max_product_from_c + max_product_from_b + max_product_from_a
    actual_product = min(total_possible_product, weekly_capacity)

    print(f"  最大可能生产: {int(total_possible_product)}m³, 实际生产: {int(actual_product)}m³")

    # 计算实际消耗的各类原材料
    remaining_product = actual_product

    # 优先使用C类
    c_usage = min(max_product_from_c, remaining_product) * material_coefficients['C']
    remaining_product -= c_usage / material_coefficients['C']

    # 然后使用B类
    b_usage = min(max_product_from_b, remaining_product) * material_coefficients['B']
    remaining_product -= b_usage / material_coefficients['B']

    # 最后使用A类
    a_usage = min(max_product_from_a, remaining_product) * material_coefficients['A']

    total_usage = c_usage + b_usage + a_usage

    print(f"  原材料消耗: C类{int(c_usage)}m³, B类{int(b_usage)}m³, A类{int(a_usage)}m³, 总计{int(total_usage)}m³")

    # 更新库存
    inventory_level += (c_supply + b_supply + a_supply) - total_usage

    print(f"  库存变化: +{int(c_supply + b_supply + a_supply)}m³ - {int(total_usage)}m³ = {int(inventory_level)}m³")

    # 记录数据
    weekly_inventory.append(inventory_level)
    weekly_production.append(actual_product)
    weekly_material_usage['C'].append(c_usage)
    weekly_material_usage['B'].append(b_usage)
    weekly_material_usage['A'].append(a_usage)

    # 制定订购计划：使用预测供货量作为订购量
    for i, supplier_id in enumerate(supplier_data['供应商ID']):
        order_plan.loc[order_plan['供应商ID'] == supplier_id, week_col] = supplier_data.iloc[i][week_col]

# 显示库存和生产统计
print(f"\n=== 库存和生产统计 ===")
print(f"初始库存: {int(weekly_inventory[0])}m³")
print(f"最终库存: {int(weekly_inventory[-1])}m³")
print(f"平均库存: {int(np.mean(weekly_inventory))}m³")
print(f"最低库存: {int(min(weekly_inventory))}m³")
print(f"最高库存: {int(max(weekly_inventory))}m³")
print(f"总生产量: {int(sum(weekly_production))}m³")
print(f"平均周产量: {int(np.mean(weekly_production))}m³")

# 材料使用统计
print(f"\n=== 材料使用统计 ===")
for material in ['C', 'B', 'A']:
    total_usage = sum(weekly_material_usage[material])
    avg_usage = np.mean(weekly_material_usage[material])
    print(f"{material}类材料: 总使用{int(total_usage)}m³, 平均周使用{int(avg_usage)}m³")

# 计算成本统计
total_cost = 0
for material in ['A', 'B', 'C']:
    material_usage = sum(weekly_material_usage[material])
    material_cost = material_usage * material_prices[material]
    total_cost += material_cost
    print(f"{material}类材料成本: {material_cost:.0f} (相对单位)")

print(f"总成本: {total_cost:.0f} (相对单位)")
print(f"单位产品成本: {total_cost / sum(weekly_production):.2f} (相对单位/立方米)")

print(f"\n订购方案已生成，包含{len(order_plan)}家供应商的24周订购计划")