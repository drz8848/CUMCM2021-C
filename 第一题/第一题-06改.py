import pandas as pd
import numpy as np
import math

# 读取文件
excel_file = pd.ExcelFile("/豆包/附件1.xlsx")

# 1. 读取数据
order = excel_file.parse('企业的订货量（m³）')
supply = excel_file.parse('供应商的供货量（m³）')
print(order)
print(supply)

# 2. 提取供应商ID、周数据列、材料类型
supplier_ids = order["供应商ID"].values
weeks = order.columns[2:]  # W001到W240
type = order.columns[1]
n = len(order)  # 使用实际数据行数，避免索引越界
m = 4  # 4个指标

print(supplier_ids)
print(weeks)
print(type)