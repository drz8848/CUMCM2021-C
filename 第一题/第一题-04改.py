import pandas as pd
import numpy as np
import math

# ------------------------------------------------------------------------------
# 1. 基础参数定义（完全来自CUMCM2021-C.pdf）
# ------------------------------------------------------------------------------
# ABC类原材料单位产品消耗系数（文档1-5：每立方米产品需A类0.6m³、B类0.66m³、C类0.72m³）
CONSUMPTION_COEFF = {
    'A': 0.6,
    'B': 0.66,
    'C': 0.72
}
# 附件1数据结构（文档1-15、1-16：列=供应商名称+材料类别+240周数据）
WEEK_COLS = [f'W{str(i).zfill(3)}' for i in range(1, 241)]  # W001~W240（240周）
KEY_COLS = ['供应商名称', '材料类别']  # 核心标识列

# ------------------------------------------------------------------------------
# 2. 数据读取（适配附件1结构，文档1-15、1-16）
# ------------------------------------------------------------------------------
# 假设附件1.xlsx包含两个sheet："订货量"和"供货量"，列名与文档一致
# 注：实际使用时需确认Excel文件路径及sheet名称，确保与文档描述的"订货量/供货量数据结构"匹配
order_df = pd.read_excel("附件1.xlsx", sheet_name="企业的订货量（m³）")  # 订货量数据：供应商名称+材料类别+W001~W240
supply_df = pd.read_excel("附件1.xlsx", sheet_name="供应商的供货量（m³）")  # 供货量数据：供应商名称+材料类别+W001~W240

# 数据一致性校验（确保供应商顺序、材料类别完全匹配，文档隐含要求）
assert len(order_df) == len(supply_df) == 402, "供应商数量需为402家（文档1-9）"
assert (order_df[KEY_COLS] == supply_df[KEY_COLS]).all().all(), "订货量与供货量的供应商/材料类别需一一对应"

# ------------------------------------------------------------------------------
# 3. 指标计算（含ABC材料换算，核心为"等效产品支撑量"，文档1-5）
# ------------------------------------------------------------------------------
# 初始化指标矩阵：402家供应商 × 4个核心指标（均基于换算后的等效量）
n_suppliers = len(order_df)
indicators = np.zeros((n_suppliers, 4))  # 列：X1'(等效供货总量), X2(供货频率), X3'(等效稳定性), X4(持续性)
supplier_info = order_df[KEY_COLS].copy()  # 保存供应商名称和材料类别

for i in range(n_suppliers):
    # 提取第i家供应商的基础数据
    supplier_name = supplier_info.iloc[i, 0]
    material_type = supplier_info.iloc[i, 1]
    coeff = CONSUMPTION_COEFF[material_type]  # 对应材料的消耗系数（A/B/C）

    # 提取240周的订货量和供货量（文档1-15、1-16：数值0表示无订货/供货）
    weekly_order = order_df.iloc[i][WEEK_COLS].values.astype(float)  # 每周订货量（m³）
    weekly_supply = supply_df.iloc[i][WEEK_COLS].values.astype(float)  # 每周供货量（m³）

    # --------------------------
    # 指标1：等效供货总量（X1'）
    # 定义：240周总供货量换算为"可支撑的产品体积"（m³产品），越大越优（文档1-5逻辑）
    # --------------------------
    total_supply = np.sum(weekly_supply)
    X1_prime = total_supply / coeff  # 换算公式：等效支撑量=供货量÷消耗系数
    indicators[i, 0] = X1_prime

    # --------------------------
    # 指标2：供货频率（X2）
    # 定义：有订货记录的周中，"有效供货"（等效支撑量>0）的比例，越大越优（文档1-5生产保障逻辑）
    # --------------------------
    has_order_weeks = (weekly_order > 0)  # 有订货的周次（排除无订货的情况）
    n_order_weeks = np.sum(has_order_weeks)

    if n_order_weeks == 0:
        X2 = 0  # 无订货记录，频率为0
    else:
        # 有效供货周次：有订货且等效供货量>0（确保供货能实际支撑生产）
        effective_supply_weeks = (weekly_supply[has_order_weeks] / coeff) > 0
        X2 = np.sum(effective_supply_weeks) / n_order_weeks
    indicators[i, 1] = X2

    # --------------------------
    # 指标3：等效供货稳定性（X3'）
    # 定义：有订货周中，"等效供货量与等效订货量偏差"的倒数，偏差越小、X3'越大越优（文档1-5生产保障逻辑）
    # --------------------------
    if n_order_weeks == 0:
        X3_prime = 0  # 无订货记录，稳定性为0
    else:
        # 换算：等效订货量=订货量÷消耗系数，等效供货量=供货量÷消耗系数
        weekly_order_eq = weekly_order[has_order_weeks] / coeff
        weekly_supply_eq = weekly_supply[has_order_weeks] / coeff

        # 计算偏差均值（避免除以0）
        mean_deviation = np.mean(np.abs(weekly_supply_eq - weekly_order_eq))
        X3_prime = 1 / mean_deviation if mean_deviation != 0 else 1000  # 偏差为0时赋极大值
    indicators[i, 2] = X3_prime

    # --------------------------
    # 指标4：供货持续性（X4）
    # 定义：有订货周中，最长连续"有效供货"（等效支撑量>0）的周数，越长越优（文档1-5生产保障逻辑）
    # --------------------------
    max_consec_weeks = 0
    current_consec_weeks = 0

    for week_idx in range(len(WEEK_COLS)):
        # 仅判断"有订货"的周次
        if has_order_weeks[week_idx]:
            # 该周是否有效供货（等效支撑量>0）
            supply_eq = weekly_supply[week_idx] / coeff
            if supply_eq > 0:
                current_consec_weeks += 1
                max_consec_weeks = max(max_consec_weeks, current_consec_weeks)
            else:
                current_consec_weeks = 0
        else:
            current_consec_weeks = 0  # 无订货则中断连续计数
    X4 = max_consec_weeks
    indicators[i, 3] = X4


# ------------------------------------------------------------------------------
# 4. TOPSIS模型实现（量化供应商重要性，文档1-9需求）
# ------------------------------------------------------------------------------
def topsis_evaluation(indicator_matrix):
    """
    输入：指标矩阵（n×m，n=供应商数，m=指标数）
    输出：各供应商的相对接近度（C_i，越大重要性越高）
    """
    n, m = indicator_matrix.shape

    # --------------------------
    # 步骤1：Min-Max标准化（消除量纲，正向指标适用）
    # --------------------------
    def min_max_normalize(col):
        col_min = np.min(col)
        col_max = np.max(col)
        if col_max - col_min == 0:
            return np.zeros_like(col)  # 指标无差异，标准化为0
        return (col - col_min) / (col_max - col_min)

    normalized_matrix = np.apply_along_axis(min_max_normalize, axis=0, arr=indicator_matrix)

    # --------------------------
    # 步骤2：熵权法赋权（客观权重，避免主观偏差）
    # --------------------------
    def entropy_weight(norm_matrix):
        entropy = np.zeros(m)
        for j in range(m):
            # 计算第j个指标的概率分布（排除0值，避免log(0)）
            p = norm_matrix[:, j] / np.sum(norm_matrix[:, j]) if np.sum(norm_matrix[:, j]) != 0 else np.zeros(n)
            p = p[p > 0]
            # 计算熵值（文档无指定权重方法，熵权法为常用客观方法）
            entropy[j] = -np.sum(p * np.log(p)) / math.log(n) if len(p) > 0 else 0
        # 计算权重（熵值越小，权重越大）
        weight = (1 - entropy) / np.sum(1 - entropy)
        return weight

    weights = entropy_weight(normalized_matrix)

    # --------------------------
    # 步骤3：构建加权标准化矩阵
    # --------------------------
    weighted_matrix = normalized_matrix * weights

    # --------------------------
    # 步骤4：确定理想解（A+）和负理想解（A-）
    # --------------------------
    ideal_solution = np.max(weighted_matrix, axis=0)  # 正向指标：理想解为各列最大值
    negative_ideal_solution = np.min(weighted_matrix, axis=0)  # 负理想解为各列最小值

    # --------------------------
    # 步骤5：计算距离（欧氏距离）
    # --------------------------
    distance_to_ideal = np.sqrt(np.sum((weighted_matrix - ideal_solution) ** 2, axis=1))  # D+
    distance_to_negative_ideal = np.sqrt(np.sum((weighted_matrix - negative_ideal_solution) ** 2, axis=1))  # D-

    # --------------------------
    # 步骤6：计算相对接近度（C_i）
    # --------------------------
    closeness = distance_to_negative_ideal / (distance_to_ideal + distance_to_negative_ideal)
    return closeness


# 执行TOPSIS评价，得到各供应商的相对接近度
supplier_closeness = topsis_evaluation(indicators)

# ------------------------------------------------------------------------------
# 5. 结果整理与输出（文档1-9要求：列表给出50家最重要供应商）
# ------------------------------------------------------------------------------
# 合并供应商信息、原始指标、接近度
result_df = supplier_info.copy()
result_df['等效供货总量（m³产品）'] = indicators[:, 0].round(2)
result_df['供货频率'] = indicators[:, 1].round(4)
result_df['等效供货稳定性'] = indicators[:, 2].round(4)
result_df['最长连续供货周数'] = indicators[:, 3].astype(int)
result_df['相对接近度（C_i）'] = supplier_closeness.round(6)

# 按接近度降序排序，选取前50家（文档1-9核心需求）
top50_suppliers = result_df.sort_values(by='相对接近度（C_i）', ascending=False).head(50).reset_index(drop=True)
top50_suppliers.insert(0, '排名', range(1, 51))  # 添加排名列

# 输出结果（论文需列表呈现，保存为Excel便于排版）
top50_suppliers.to_excel("第一题_50家重要供应商结果.xlsx", index=False, encoding='utf-8')

# 打印前10条结果预览
print("前10家最重要供应商预览：")
print(top50_suppliers.head(10).to_string(index=False))
print(f"\n完整50家供应商结果已保存至：第一题_50家重要供应商结果.xlsx")