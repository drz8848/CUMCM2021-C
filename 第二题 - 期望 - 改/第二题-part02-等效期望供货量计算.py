import pandas as pd
import numpy as np

# 重新读取数据
df = pd.read_excel('期望供货量预测结果.xlsx', sheet_name=0)
df_clean = df.dropna(subset=['供应商ID']).copy()

# 换算系数
conversion_factors = {'A': 1 / 0.6, 'B': 1 / 0.66, 'C': 1 / 0.72}
week_columns = [col for col in df_clean.columns if '未来第' in col]

print("换算系数：")
for material, factor in conversion_factors.items():
    print(f"1{material} = {factor:.4f}产品")

# 重新计算等效供货量
df_equivalent = df_clean[['供应商ID', '材料分类']].copy()

for week in week_columns:
    # 使用向量化操作计算等效供货量
    mask_a = df_clean['材料分类'] == 'A'
    mask_b = df_clean['材料分类'] == 'B'
    mask_c = df_clean['材料分类'] == 'C'

    equivalent_col = f'等效_{week}'
    df_equivalent[equivalent_col] = 0

    df_equivalent.loc[mask_a, equivalent_col] = df_clean.loc[mask_a, week] * conversion_factors['A']
    df_equivalent.loc[mask_b, equivalent_col] = df_clean.loc[mask_b, week] * conversion_factors['B']
    df_equivalent.loc[mask_c, equivalent_col] = df_clean.loc[mask_c, week] * conversion_factors['C']

# 验证计算结果
print(f"\n第1周数据验证：")
for material in ['A', 'B', 'C']:
    mask = df_equivalent['材料分类'] == material
    raw_qty = df_clean.loc[mask, '未来第1周'].sum()
    converted_qty = df_equivalent.loc[mask, '等效_未来第1周'].sum()
    print(f"{material}材料: 原始数量 {raw_qty}, 等效产品数量 {converted_qty:.2f}")

# 计算各材料类型对等效供货量的贡献
material_contribution = {}
for material in ['A', 'B', 'C']:
    mask = df_equivalent['材料分类'] == material
    contribution = {}
    for week in week_columns:
        equivalent_col = f'等效_{week}'
        contribution[week] = df_equivalent.loc[mask, equivalent_col].sum()
    material_contribution[material] = contribution

print(f"\n各材料类型总贡献：")
total_by_material = {}
for material in ['A', 'B', 'C']:
    total = sum(material_contribution[material].values())
    total_by_material[material] = total
    print(f"{material}: {total:.2f}")

# 计算每周总等效供货量和过剩量
capacity = 28200
weekly_summary = []

for week in week_columns:
    equivalent_col = f'等效_{week}'
    total_equivalent = df_equivalent[equivalent_col].sum()
    surplus = total_equivalent - capacity

    weekly_summary.append({
        'week': int(week.replace('未来第', '').replace('周', '')),
        'total_equivalent': round(total_equivalent, 2),
        'surplus': round(surplus, 2),
        'a_contribution': round(material_contribution['A'][week], 2),
        'b_contribution': round(material_contribution['B'][week], 2),
        'c_contribution': round(material_contribution['C'][week], 2)
    })

print(f"\n前5周汇总：")
for summary in weekly_summary[:5]:
    print(f"第{summary['week']}周: 总等效供货量 {summary['total_equivalent']}, 过剩 {summary['surplus']}")

# 计算整体统计
total_surplus = sum([s['surplus'] for s in weekly_summary])
avg_surplus = total_surplus / len(weekly_summary)
max_surplus = max(weekly_summary, key=lambda x: x['surplus'])
min_surplus = min(weekly_summary, key=lambda x: x['surplus'])

print(f"\n整体统计：")
print(f"总过剩量: {total_surplus:.2f}")
print(f"平均每周过剩: {avg_surplus:.2f}")
print(f"过剩最多周: 第{max_surplus['week']}周 ({max_surplus['surplus']:.2f})")
print(f"过剩最少周: 第{min_surplus['week']}周 ({min_surplus['surplus']:.2f})")

print(f"\n数据处理完成，准备生成可视化报告...")

# 保存等效期望供货量到新的Excel文件
output_file = '等效期望供货量结果.xlsx'
df_equivalent.to_excel(output_file, index=False)
print(f"等效期望供货量已成功保存到 {output_file}")
