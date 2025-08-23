import pandas as pd
import numpy as np

# 重新读取数据
topsis_results = pd.read_excel('供应商TOPSIS评价结果.xlsx')
future_supply = pd.read_excel('供应商未来24周供货量预测.xlsx')

# 合并数据
supplier_data = pd.merge(topsis_results, future_supply, on=['供应商ID', '材料分类'])

# 生产参数
weekly_capacity = 28200  # 每周产能，立方米
material_coefficients = {'A': 0.6, 'B': 0.66, 'C': 0.72}
weeks = 24  # 计划周期

# 计算总产品需求
total_product_demand = weekly_capacity * weeks
print(f"未来24周总产品需求: {total_product_demand:,.0f} 立方米")

# 计算等效原材料需求（按最保守的C类计算）
equivalent_raw_material_demand = total_product_demand * material_coefficients['C']
print(f"等效原材料需求（按C类计算）: {equivalent_raw_material_demand:,.0f} 立方米")

# 计算每个供应商的未来24周总供货量
week_columns = [f'W{i}' for i in range(241, 265)]
supplier_data['总预测供货量'] = supplier_data[week_columns].sum(axis=1)


# 计算等效产能支撑
def calculate_equivalent_capacity(row):
    material_type = row['材料分类']
    total_supply = row['总预测供货量']
    return total_supply / material_coefficients[material_type]


supplier_data['等效产能支撑'] = supplier_data.apply(calculate_equivalent_capacity, axis=1)

# 按TOPSIS得分排序
supplier_data = supplier_data.sort_values('TOPSIS综合得分', ascending=False).reset_index(drop=True)

# 累计选择供应商，直到满足需求
cumulative_supply = 0
cumulative_capacity = 0
selected_suppliers = []
supplier_counts = []
cumulative_supplies = []
cumulative_capacities = []

for i, row in supplier_data.iterrows():
    cumulative_supply += row['总预测供货量']
    cumulative_capacity += row['等效产能支撑']

    supplier_counts.append(i + 1)
    cumulative_supplies.append(cumulative_supply)
    cumulative_capacities.append(cumulative_capacity)

    if cumulative_capacity >= total_product_demand:
        selected_suppliers = supplier_data.head(i + 1)
        break

print(f"\n至少需要选择 {len(selected_suppliers)} 家供应商才能满足生产需求")
print(f"这些供应商的总供货量: {cumulative_supply:,.0f} 立方米")
print(f"等效产能支撑: {cumulative_capacity:,.0f} 立方米产品")
print(f"需求产能: {total_product_demand:,.0f} 立方米产品")

# 显示选择的供应商信息
print(f"\n选择的前10家供应商:")
print(selected_suppliers[['供应商ID', '材料分类', 'TOPSIS综合得分', '总预测供货量', '等效产能支撑']].head(10))

# 分析材料类别分布
material_distribution = selected_suppliers['材料分类'].value_counts()
print(f"\n选择的供应商材料类别分布:")
print(material_distribution)

# 计算安全系数
safety_margin = (cumulative_capacity - total_product_demand) / total_product_demand * 100
print(f"\n产能安全边际: {safety_margin:.2f}%")

# 保存选择的供应商数据
selected_suppliers.to_excel('selected_suppliers.xlsx', index=False)
print(f"\n选择的供应商数据已保存到 selected_suppliers.xlsx")