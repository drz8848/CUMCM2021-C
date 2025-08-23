import pandas as pd
import numpy as np

# 重新读取和处理数据
topsis_results = pd.read_excel('供应商TOPSIS评价结果.xlsx')
future_supply = pd.read_excel('供应商未来24周供货量预测.xlsx')
transporters = pd.read_excel('附件2.xlsx')

# 合并供应商数据
supplier_data = pd.merge(topsis_results, future_supply, on=['供应商ID', '材料分类'])

# 计算转运商平均损耗率
week_columns_trans = [col for col in transporters.columns if col.startswith('W')]
transporters['平均损耗率'] = transporters[week_columns_trans].mean(axis=1)
transporters_sorted = transporters.sort_values('平均损耗率')

print("=== 转运商平均损耗率 ===")
for _, row in transporters_sorted.iterrows():
    print(f"{row['转运商ID']}: {row['平均损耗率']:.4f}%")

# 生成订购方案（简化版）
week_columns_future = [f'W{i}' for i in range(241, 265)]
order_plan = supplier_data[['供应商ID', '材料分类'] + week_columns_future].copy()

# 生成转运方案（简化版）
transport_plan = supplier_data[['供应商ID', '材料分类']].copy()

# 为每周分配转运商（简化逻辑）
for week_col in week_columns_future:
    # 获取本周有供货的供应商
    weekly_suppliers = supplier_data[supplier_data[week_col] > 0].copy()
    weekly_suppliers = weekly_suppliers.sort_values(week_col, ascending=False)

    # 分配转运商
    transporter_idx = 0
    for _, row in weekly_suppliers.iterrows():
        supplier_id = row['供应商ID']
        transporter_id = transporters_sorted.iloc[transporter_idx % len(transporters_sorted)]['转运商ID']
        loss_rate = transporters_sorted.iloc[transporter_idx % len(transporters_sorted)]['平均损耗率'] / 100

        transport_plan.loc[transport_plan['供应商ID'] == supplier_id, f'{week_col}_转运商'] = transporter_id
        transport_plan.loc[transport_plan['供应商ID'] == supplier_id, f'{week_col}_损耗量'] = row[week_col] * loss_rate

        transporter_idx += 1

print(f"\n=== 方案生成完成 ===")
print(f"订购方案: {len(order_plan)}家供应商 × {len(week_columns_future)}周")
print(f"转运方案: {len(transport_plan)}家供应商 × {len(week_columns_future)}周")

# 保存方案数据
order_plan.to_excel('订购方案详细数据.xlsx', index=False)
transport_plan.to_excel('转运方案详细数据.xlsx', index=False)
print("方案数据已保存")

# 读取附件模板
print(f"\n=== 读取附件模板 ===")
attachment_a = pd.read_excel('附件A.xlsx', sheet_name='问题2的订购方案结果')
attachment_b = pd.read_excel('附件B.xlsx', sheet_name='问题2的转运方案结果')

print(f"附件A形状: {attachment_a.shape}")
print(f"附件B形状: {attachment_b.shape}")


