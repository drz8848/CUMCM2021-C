import pandas as pd
import numpy as np
import math

# 1. 读取数据（附件1的订货量和供货量分别存为order和supply）
# 注意：实际需根据Excel格式调整列名和路径
order = pd.read_excel("附件1.xlsx", sheet_name="企业的订货量（m³）")  # 列：供应商ID, 材料分类, W001...W240
supply = pd.read_excel("附件1.xlsx", sheet_name="供应商的供货量（m³）")


# 数据清洗函数：将非数值转换为NaN
def clean_numeric_data(value):
    if isinstance(value, str):
        # 移除可能的特殊字符
        value = value.strip().replace('=', '').replace(',', '')
        try:
            return float(value)
        except ValueError:
            return np.nan
    return value


# 2. 提取供应商ID和周数据列
supplier_ids = order["供应商ID"].values
weeks = order.columns[2:]  # W001到W240
n = len(supplier_ids)  # 402
m = 4  # 4个指标

# 3. 计算指标矩阵X (402×4)
X = np.zeros((n, m))
for i in range(n):
    try:
        # 提取第i个供应商的订货量和供货量，并进行清洗
        order_i = order.iloc[i, 2:].apply(clean_numeric_data).fillna(0).values.astype(float)
        supply_i = supply.iloc[i, 2:].apply(clean_numeric_data).fillna(0).values.astype(float)

        # 指标1：供货总量
        X[i, 0] = np.sum(supply_i)

        # 指标2：供货频率（有订货时的供货比例）
        order_nonzero = order_i > 0
        if np.sum(order_nonzero) == 0:
            X[i, 1] = 0  # 无订货记录
        else:
            supply_nonzero = (supply_i > 0) & order_nonzero
            X[i, 1] = np.sum(supply_nonzero) / np.sum(order_nonzero)

        # 指标3：供货稳定性（偏差倒数，避免除以0）
        diff = np.abs(supply_i - order_i)[order_nonzero]
        if len(diff) == 0:
            X[i, 2] = 0
        else:
            mean_diff = np.mean(diff)
            X[i, 2] = 1 / mean_diff if mean_diff != 0 else 1000  # 偏差为0时赋大值

        # 指标4：供货持续性（最长连续供货周数）
        consecutive = 0
        max_consec = 0
        for idx in range(len(weeks)):
            if order_nonzero[idx] and supply_i[idx] > 0:
                consecutive += 1
                max_consec = max(max_consec, consecutive)
            else:
                consecutive = 0
        X[i, 3] = max_consec
    except Exception as e:
        print(f"处理供应商 {supplier_ids[i]} 时出错: {str(e)}")
        # 为出错的供应商设置默认值
        X[i, :] = [0, 0, 0, 0]


# 4. 标准化（min-max）
def normalize(X):
    Z = np.zeros_like(X)
    for j in range(X.shape[1]):
        min_j = np.min(X[:, j])
        max_j = np.max(X[:, j])
        if max_j - min_j == 0:
            Z[:, j] = 0
        else:
            Z[:, j] = (X[:, j] - min_j) / (max_j - min_j)
    return Z


Z = normalize(X)


# 5. 熵权法计算权重
def entropy_weight(Z):
    n, m = Z.shape
    E = np.zeros(m)
    for j in range(m):
        # 处理可能的0值总和
        sum_z = np.sum(Z[:, j])
        if sum_z == 0:
            p = np.zeros(n)
        else:
            p = Z[:, j] / sum_z

        p = p[p > 0]  # 排除0值
        if len(p) > 0:
            E[j] = -np.sum(p * np.log(p)) / math.log(n)
        else:
            E[j] = 0
    # 处理可能的权重计算问题
    sum_1minE = np.sum(1 - E)
    if sum_1minE == 0:
        W = np.ones(m) / m  # 平均分配权重
    else:
        W = (1 - E) / sum_1minE
    return W


W = entropy_weight(Z)

# 6. 加权标准化矩阵
V = Z * W

# 7. 理想解和负理想解
A_plus = np.max(V, axis=0)
A_minus = np.min(V, axis=0)

# 8. 计算距离和接近度
D_plus = np.sqrt(np.sum((V - A_plus) ** 2, axis=1))
D_minus = np.sqrt(np.sum((V - A_minus) ** 2, axis=1))
# 处理可能的除以0问题
C = np.zeros_like(D_plus)
for i in range(len(C)):
    if D_plus[i] + D_minus[i] == 0:
        C[i] = 0
    else:
        C[i] = D_minus[i] / (D_plus[i] + D_minus[i])

# 9. 排序并选取前50家
result = pd.DataFrame({
    "供应商ID": supplier_ids,
    "接近度": C
}).sort_values(by="接近度", ascending=False)

top50 = result.head(50)
print(top50)
top50.to_excel("top50供应商.xlsx", index=False)
