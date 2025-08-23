import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestRegressor
import json

# 读取数据
df_supply = pd.read_excel('附件1.xlsx', sheet_name='供应商的供货量（m³）')
df_order = pd.read_excel('附件1.xlsx', sheet_name='企业的订货量（m³）')

# 提取周数据列
weeks_columns = [col for col in df_supply.columns if col.startswith('W')]
num_weeks = len(weeks_columns)

print("开始构建预测模型...")


# 定义预测函数
def predict_supplier_demand(supplier_data, weeks_history, weeks_predict=24):
    """
    预测单个供应商未来的供货量
    """
    # 提取历史数据
    history = supplier_data[weeks_history].values.astype(float)

    # 计算基本统计特征
    non_zero_count = sum(history > 0)
    avg_supply = np.mean(history) if non_zero_count > 0 else 0
    recent_avg = np.mean(history[-12:]) if non_zero_count > 12 else avg_supply
    material = supplier_data['材料分类']

    # 根据不同情况采用不同预测策略
    if non_zero_count < 10:
        # 供货次数很少，使用基于材料分类的平均值
        material_avg = df_supply[df_supply['材料分类'] == material][weeks_history].mean().mean()
        predictions = [max(0, material_avg * 0.8) for _ in range(weeks_predict)]

    elif non_zero_count < 52:
        # 供货有一定规律但不稳定，使用移动平均
        predictions = []
        for i in range(weeks_predict):
            window_size = min(12, len(history))
            pred = np.mean(history[-window_size:])
            predictions.append(max(0, pred))
            # 更新历史用于下一次预测
            history = np.append(history, pred)

    else:
        # 供货相对稳定，使用指数平滑
        alpha = 0.3  # 平滑系数
        predictions = []
        last_value = history[-1]

        for i in range(weeks_predict):
            if i < len(history):
                pred = alpha * history[-i - 1] + (1 - alpha) * last_value
            else:
                pred = alpha * predictions[-1] + (1 - alpha) * last_value
            predictions.append(max(0, pred))
            last_value = pred

    return predictions


# 为所有供应商生成预测
print("正在为所有供应商生成未来24周的预测...")
all_predictions = []
sample_data = []

for idx, row in df_supply.iterrows():
    supplier_id = row['供应商ID']
    material = row['材料分类']

    # 生成预测
    predictions = predict_supplier_demand(row, weeks_columns)

    # 创建预测结果记录
    pred_record = {
        '供应商ID': supplier_id,
        '材料分类': material
    }

    # 添加历史数据（用于可视化）
    history_data = {}
    for i, week in enumerate(weeks_columns[-12:]):  # 取最近12周的历史数据
        history_data[week] = float(row[week])

    # 添加预测数据
    for i in range(24):
        pred_week = f"W{241 + i:03d}"
        pred_record[pred_week] = round(predictions[i], 2)

    all_predictions.append(pred_record)

    # 为HTML报告准备样例数据（前10个供应商）
    if idx < 10:
        sample_data.append({
            'supplier_id': supplier_id,
            'material': material,
            'history': history_data,
            'predictions': {f"W{241 + i:03d}": round(predictions[i], 2) for i in range(24)}
        })

print(f"预测完成！共为 {len(all_predictions)} 个供应商生成了未来24周的预测")

# 转换为DataFrame
df_predictions = pd.DataFrame(all_predictions)
print("\n预测结果样例:")
print(df_predictions[['供应商ID', '材料分类', 'W241', 'W242', 'W243', 'W252', 'W264']].head())

# 保存预测结果
df_predictions.to_excel('供应商未来24周供货量预测.xlsx', index=False)
print("\n预测结果已保存到 '供应商未来24周供货量预测.xlsx'")

# 统计预测结果
print("\n预测结果统计:")
prediction_weeks = [f"W{241 + i:03d}" for i in range(24)]
total_predicted = df_predictions[prediction_weeks].sum().sum()
print(f"未来24周总预测供货量: {total_predicted:.2f} m³")

for material in ['A', 'B', 'C']:
    material_pred = df_predictions[df_predictions['材料分类'] == material]
    material_total = material_pred[prediction_weeks].sum().sum()
    print(f"  材料 {material}: {material_total:.2f} m³ ({len(material_pred)} 个供应商)")

# 准备HTML可视化数据
html_data = {
    'sample_suppliers': sample_data,
    'summary': {
        'total_suppliers': len(df_supply),
        'total_predicted': round(total_predicted, 2),
        'material_A': round(df_predictions[df_predictions['材料分类'] == 'A'][prediction_weeks].sum().sum(), 2),
        'material_B': round(df_predictions[df_predictions['材料分类'] == 'B'][prediction_weeks].sum().sum(), 2),
        'material_C': round(df_predictions[df_predictions['材料分类'] == 'C'][prediction_weeks].sum().sum(), 2)
    }
}

print("\nHTML可视化数据准备完成")
