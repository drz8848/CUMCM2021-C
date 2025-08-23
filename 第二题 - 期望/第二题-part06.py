import pandas as pd
import numpy as np

# 读取附件A并填入订购方案
attachmentA = pd.read_excel('附件A.xlsx', sheet_name='问题2的订购方案结果')

# 找到供应商ID所在的行
supplier_id_row = None
for i, row in attachmentA.iterrows():
    if '供应商ID' in str(row.iloc[0]):
        supplier_id_row = i
        break

print(f"附件A供应商ID行索引: {supplier_id_row}")

# 创建供应商ID到行号的映射
supplier_to_row = {}
for i in range(supplier_id_row + 1, len(attachmentA)):
    supplier_id = str(attachmentA.iloc[i, 0])
    if supplier_id.startswith('S') and len(supplier_id) == 4:
        supplier_to_row[supplier_id] = i

print(f"附件A中找到的供应商数量: {len(supplier_to_row)}")

# 填入订购方案数据
for supplier_id in selected_supplier_ids:
    if supplier_id in supplier_to_row:
        row_idx = supplier_to_row[supplier_id]
        for week in range(1, 25):
            week_col_name = f'第{week:02d}周'
            # 找到对应的列索引
            col_idx = None
            for j, col_name in enumerate(attachmentA.columns):
                if str(col_name) == week_col_name:
                    col_idx = j
                    break

            if col_idx is not None:
                order_amount = order_plan.loc[supplier_id, week_col_name]
                if order_amount > 0:
                    attachmentA.iloc[row_idx, col_idx] = int(order_amount)
                else:
                    attachmentA.iloc[row_idx, col_idx] = None

print("附件A订购方案数据填入完成")

# 读取附件B并填入转运方案
attachmentB = pd.read_excel('附件B.xlsx', sheet_name='问题2的转运方案结果')

# 找到供应商ID所在的行
supplier_id_row_b = None
for i, row in attachmentB.iterrows():
    if '供应商ID' in str(row.iloc[0]):
        supplier_id_row_b = i
        break

print(f"附件B供应商ID行索引: {supplier_id_row_b}")

# 创建供应商ID到行号的映射
supplier_to_row_b = {}
for i in range(supplier_id_row_b + 1, len(attachmentB)):
    supplier_id = str(attachmentB.iloc[i, 0])
    if supplier_id.startswith('S') and len(supplier_id) == 4:
        supplier_to_row_b[supplier_id] = i

print(f"附件B中找到的供应商数量: {len(supplier_to_row_b)}")

# 填入转运方案数据
for supplier_id in selected_supplier_ids:
    if supplier_id in supplier_to_row_b:
        row_idx = supplier_to_row_b[supplier_id]
        for week in range(1, 25):
            week_col_name = f'第{week:02d}周'
            # 找到对应的列索引
            col_idx = None
            for j, col_name in enumerate(attachmentB.columns):
                if str(col_name) == week_col_name:
                    col_idx = j
                    break

            if col_idx is not None:
                transporter_info = transport_plan.loc[supplier_id, week_col_name]
                if transporter_info:
                    attachmentB.iloc[row_idx, col_idx] = transporter_info
                else:
                    attachmentB.iloc[row_idx, col_idx] = None

print("附件B转运方案数据填入完成")

# 保存修改后的文件
with pd.ExcelWriter('附件A.xlsx', engine='openpyxl') as writer:
    attachmentA.to_excel(writer, sheet_name='问题2的订购方案结果', index=False)

with pd.ExcelWriter('附件B.xlsx', engine='openpyxl') as writer:
    attachmentB.to_excel(writer, sheet_name='问题2的转运方案结果', index=False)

print("文件保存完成！")

# 验证数据填入情况
print(f"\n验证附件A数据填入:")
sample_supplier = selected_supplier_ids[0]
if sample_supplier in supplier_to_row:
    row_idx = supplier_to_row[sample_supplier]
    print(f"{sample_supplier}的订购数据:")
    for week in range(1, 6):
        week_col_name = f'第{week:02d}周'
        for j, col_name in enumerate(attachmentA.columns):
            if str(col_name) == week_col_name:
                print(f"  {week_col_name}: {attachmentA.iloc[row_idx, j]}")
                break

print(f"\n验证附件B数据填入:")
if sample_supplier in supplier_to_row_b:
    row_idx = supplier_to_row_b[sample_supplier]
    print(f"{sample_supplier}的转运数据:")
    for week in range(1, 6):
        week_col_name = f'第{week:02d}周'
        for j, col_name in enumerate(attachmentB.columns):
            if str(col_name) == week_col_name:
                print(f"  {week_col_name}: {attachmentB.iloc[row_idx, j]}")
                break
