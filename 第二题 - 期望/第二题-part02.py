
import pandas as pd
import numpy as np

# 重新加载数据
topsis_df = pd.read_excel('供应商TOPSIS评价结果.xlsx')
expected_df = pd.read_excel('期望供货量预测结果.xlsx')

# 计算每个供应商未来24周的总期望供货量
week_columns = [f'未来第{i}周' for i in range(1, 25)]
expected_df['总期望供货量'] = expected_df[week_columns].sum(axis=1)

# 合并TOPSIS评分和期望供货量数据
supplier_data = pd.merge(topsis_df, expected_df[['供应商ID', '总期望供货量'] + week_columns], on='供应商ID', how='left')

# 按TOPSIS评分排序
supplier_data = supplier_data.sort_values('TOPSIS综合得分', ascending=False).reset_index(drop=True)

# 计算等效材料系数
equivalent_coefficients = {'A': 1.6667, 'B': 1.5152, 'C': 1.3889}

# 计算每个供应商的等效期望供货量
supplier_data['等效期望供货量'] = supplier_data.apply(
    lambda row: row['总期望供货量'] * equivalent_coefficients[row['材料分类']], axis=1
)

# 计算累计等效供货量
supplier_data['累计等效供货量'] = supplier_data['等效期望供货量'].cumsum()

# 24周总需求
total_24week_demand = 28200 * 24  # 676800 立方米等效产品

print(f"24周等效材料总需求: {total_24week_demand:,.0f} 立方米（等效产品）")
print("\n供应商累计等效供货量分析:")

# 找到满足需求的最少供应商数量
cumulative_supply = 0
min_suppliers_needed = 0
for i, row in supplier_data.iterrows():
    cumulative_supply += row['等效期望供货量']
    if cumulative_supply >= total_24week_demand:
        min_suppliers_needed = i + 1
        break

print(f"\n满足24周需求所需的最少供应商数量: {min_suppliers_needed}")
print(f"这些供应商的累计等效供货量: {cumulative_supply:,.0f} 立方米（等效产品）")
print(f"超出需求: {cumulative_supply - total_24week_demand:,.0f} 立方米（等效产品）")

# 显示这些供应商的信息
selected_suppliers = supplier_data.head(min_suppliers_needed)
print(f"\n选择的{min_suppliers_needed}家供应商:")
print(selected_suppliers[['供应商ID', '材料分类', 'TOPSIS综合得分', '等效期望供货量', '累计等效供货量']].to_string(index=False))

# 分析材料分类分布
material_distribution = selected_suppliers['材料分类'].value_counts()
print(f"\n选择的供应商材料分类分布:")
for material, count in material_distribution.items():
    percentage = (count / min_suppliers_needed) * 100
    print(f"{material}类: {count}家 ({percentage:.1f}%)")
