
import pandas as pd
import numpy as np

# 重新读取转运商数据
attachment2 = pd.read_excel('附件2.xlsx')
print("转运商损耗率数据:")
print(attachment2.head())
print(f"\n列名: {attachment2.columns.tolist()}")

# 计算每家转运商的平均损耗率
week_columns = [col for col in attachment2.columns if col.startswith('W')]
attachment2['平均损耗率'] = attachment2[week_columns].mean(axis=1)

print(f"\n各转运商平均损耗率:")
for idx, row in attachment2.iterrows():
    print(f"{row['转运商ID']}: {row['平均损耗率']:.4f}")

# 按平均损耗率排序
sorted_transporters = attachment2.sort_values('平均损耗率').reset_index(drop=True)
print(f"\n转运商按损耗率排序（从低到高）:")
for idx, row in sorted_transporters.iterrows():
    print(f"{row['转运商ID']}: {row['平均损耗率']:.4f}")

# 读取供应商期望供货量数据
expected_df = pd.read_excel('期望供货量预测结果.xlsx')
selected_supplier_ids = ['S229', 'S140', 'S361', 'S201', 'S108', 'S139', 'S151', 'S282', 'S340', 'S275', 'S329', 'S308', 'S330', 'S131', 'S395', 'S268', 'S356']

# 获取选择的供应商的期望供货量
selected_expected = expected_df[expected_df['供应商ID'].isin(selected_supplier_ids)].copy()
print(f"\n选择的供应商期望供货量概况:")
print(selected_expected[['供应商ID', '材料分类'] + [f'未来第{i}周' for i in range(1, 6)]].head())
