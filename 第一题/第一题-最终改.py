import pandas as pd
import numpy as np

# 加载数据和计算指标
df_supply = pd.read_excel('附件1.xlsx', sheet_name='供应商的供货量（m³）')
df_order = pd.read_excel('附件1.xlsx', sheet_name='企业的订货量（m³）')
df_order_clean = df_order[df_order['供应商ID'].isin(df_supply['供应商ID'].unique())].copy()
week_columns = [col for col in df_supply.columns if col.startswith('W')]

# 创建结果数据框
results = pd.DataFrame()
results['供应商ID'] = df_supply['供应商ID']
results['材料分类'] = df_supply['材料分类']

# 计算所有8个指标
material_coefficients = {'A': 1/0.6, 'B': 1/0.66, 'C': 1/0.72}
results['材料系数'] = results['材料分类'].map(material_coefficients)
results['总供货量'] = df_supply[week_columns].sum(axis=1)
results['等效总供货量'] = results['总供货量'] * results['材料系数']
results['总预定量'] = df_order_clean[week_columns].sum(axis=1)
results['到货率'] = np.where(results['总预定量'] > 0, results['总供货量'] / results['总预定量'], 0)

# 平均供货强度
supply_weeks_count = (df_supply[week_columns] > 0).sum(axis=1)
results['平均供货强度'] = np.where(supply_weeks_count > 0, results['总供货量'] / supply_weeks_count, 0)

# 其他指标计算
supply_response_rates = []
supply_sufficiency_rates = []
cv_values = []
max_continuous_weeks = []

for i in range(len(df_supply)):
    supply_data = df_supply.iloc[i][week_columns].values
    order_data = df_order_clean.iloc[i][week_columns].values

    # 供货响应率
    has_order = order_data > 0
    has_supply_and_order = (supply_data > 0) & has_order
    total_order_weeks = np.sum(has_order)
    response_rate = np.sum(has_supply_and_order) / total_order_weeks if total_order_weeks > 0 else 0

    # 供货充足率
    sufficiency_ratios = []
    for j in range(len(week_columns)):
        if order_data[j] > 0:
            ratio = supply_data[j] / order_data[j]
            sufficiency_ratios.append(min(ratio, 2.0))
    sufficiency_rate = np.mean(sufficiency_ratios) if sufficiency_ratios else 0

    # 供货变异系数
    valid_supply = supply_data[supply_data > 0]
    cv = np.std(valid_supply) / np.mean(valid_supply) if len(valid_supply) >= 2 else 0

    # 供货持续性
    continuous_count = 0
    max_continuous = 0
    in_continuous = False
    for j in range(len(week_columns)):
        if has_order[j]:
            if supply_data[j] > 0:
                if in_continuous:
                    continuous_count += 1
                else:
                    continuous_count = 1
                    in_continuous = True
                max_continuous = max(max_continuous, continuous_count)
            else:
                in_continuous = False
                continuous_count = 0

    supply_response_rates.append(response_rate)
    supply_sufficiency_rates.append(sufficiency_rate)
    cv_values.append(cv)
    max_continuous_weeks.append(max_continuous)

results['供货响应率'] = supply_response_rates
results['供货充足率'] = supply_sufficiency_rates
results['供货变异系数'] = cv_values
results['供货持续性'] = max_continuous_weeks

# TOPSIS模型实现
topsis_indicators = ['等效总供货量', '总预定量', '到货率', '平均供货强度', '供货响应率', '供货充足率', '供货持续性',
                     '供货变异系数']
indicator_directions = ['positive', 'positive', 'positive', 'positive', 'positive', 'positive', 'positive', 'negative']

# 提取指标数据
X = results[topsis_indicators].values

# 数据标准化
n, m = X.shape
X_normalized = np.zeros((n, m))

for j in range(m):
    if indicator_directions[j] == 'positive':
        # 正向指标标准化
        X_normalized[:, j] = X[:, j] / np.sqrt(np.sum(X[:, j] ** 2))
    else:
        # 负向指标标准化：先正向化，再标准化
        # 正向化：max - x
        max_val = np.max(X[:, j])
        X_positive = max_val - X[:, j]
        X_normalized[:, j] = X_positive / np.sqrt(np.sum(X_positive ** 2))

# 确定理想解和负理想解
ideal_best = np.max(X_normalized, axis=0)
ideal_worst = np.min(X_normalized, axis=0)

# 计算距离
d_best = np.sqrt(np.sum((X_normalized - ideal_best) ** 2, axis=1))
d_worst = np.sqrt(np.sum((X_normalized - ideal_worst) ** 2, axis=1))

# 计算综合评价指数
closeness = d_worst / (d_best + d_worst)

# 添加到结果中
results['TOPSIS综合得分'] = closeness
results['排名'] = results['TOPSIS综合得分'].rank(ascending=False, method='min').astype(int)

# 显示排名前10的供应商
print("TOPSIS模型分析结果 - 排名前10的供应商:")
top_10 = results.sort_values('TOPSIS综合得分', ascending=False).head(10)
print(top_10[['供应商ID', '材料分类', 'TOPSIS综合得分', '排名']])

# 显示50家最重要供应商的统计信息
top_50 = results.sort_values('TOPSIS综合得分', ascending=False).head(50)
print(f"\n前50家最重要供应商材料分类分布:")
print(top_50['材料分类'].value_counts())

print(f"\n前50家供应商TOPSIS得分范围: {top_50['TOPSIS综合得分'].min():.4f} - {top_50['TOPSIS综合得分'].max():.4f}")
print(f"所有供应商TOPSIS得分范围: {results['TOPSIS综合得分'].min():.4f} - {results['TOPSIS综合得分'].max():.4f}")

# 保存结果到Excel文件
results_sorted = results.sort_values('TOPSIS综合得分', ascending=False)
results_sorted.to_excel('供应商TOPSIS评价结果.xlsx', index=False)
print(f"\n完整评价结果已保存到 '供应商TOPSIS评价结果.xlsx'")